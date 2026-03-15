"""FAISS インデックスビルダー。

S3 上の PDF ドキュメントからテキストを抽出し、
FAISS インデックスとメタデータを生成して S3 にアップロードする。
"""

import json
import logging
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from build_rag_index.chunker import TextChunk, split_pages_into_chunks
from build_rag_index.config import IndexConfig
from build_rag_index.pdf_extractor import extract_pages_from_pdf

logger = logging.getLogger(__name__)


def build_index(config: IndexConfig | None = None) -> dict[str, Any]:
    """FAISS インデックスをビルドする。

    1. S3 から PDF をダウンロード
    2. テキスト抽出・チャンク分割
    3. 埋め込みベクトル生成
    4. FAISS インデックス作成
    5. S3 にアップロード

    Args:
        config: インデックスビルド設定。None の場合は環境変数から読み込む。

    Returns:
        ビルド結果の辞書。
    """
    if config is None:
        config = IndexConfig()

    logging.basicConfig(level=getattr(logging, config.log_level))

    s3 = boto3.client("s3", region_name=config.aws_region)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        pdf_paths = _download_pdfs(s3, config, tmp_path)
        if not pdf_paths:
            logger.warning("処理対象の PDF が見つかりませんでした")
            return {"total_chunks": 0}

        all_chunks = _extract_and_chunk(pdf_paths)
        if not all_chunks:
            logger.warning("抽出されたテキストチャンクがありません")
            return {"total_chunks": 0}

        index, metadata = _build_faiss_index(all_chunks, config)

        _upload_index(s3, config, index, metadata, tmp_path)

    logger.info("インデックスビルド完了")
    return {"total_chunks": len(all_chunks)}


def _download_pdfs(
    s3: object,
    config: IndexConfig,
    download_dir: Path,
) -> list[Path]:
    """S3 から PDF ファイルをダウンロードする。

    Args:
        s3: S3 クライアント。
        config: インデックスビルド設定。
        download_dir: ダウンロード先ディレクトリ。

    Returns:
        ダウンロードした PDF ファイルパスのリスト。
    """
    response = s3.list_objects_v2(
        Bucket=config.s3_bucket_name,
        Prefix=config.s3_documents_prefix,
    )

    pdf_paths: list[Path] = []
    for obj in response.get("Contents", []):
        key = obj["Key"]
        if not key.lower().endswith(".pdf"):
            continue

        filename = Path(key).name
        local_path = download_dir / filename
        s3.download_file(config.s3_bucket_name, key, str(local_path))
        pdf_paths.append(local_path)
        logger.info("PDF ダウンロード: %s", key)

    logger.info("PDF ダウンロード完了: %d ファイル", len(pdf_paths))
    return pdf_paths


def _extract_and_chunk(pdf_paths: list[Path]) -> list[TextChunk]:
    """PDF からテキストを抽出しチャンクに分割する。

    Args:
        pdf_paths: PDF ファイルパスのリスト。

    Returns:
        テキストチャンクのリスト。
    """
    all_chunks: list[TextChunk] = []

    for pdf_path in pdf_paths:
        pages = extract_pages_from_pdf(pdf_path)
        chunks = split_pages_into_chunks(pages)
        all_chunks.extend(chunks)

    logger.info("全チャンク数: %d", len(all_chunks))
    return all_chunks


def _build_faiss_index(
    chunks: list[TextChunk],
    config: IndexConfig,
) -> tuple[faiss.Index, dict]:
    """FAISS インデックスを構築する。

    IndexFlatIP + normalize で cosine similarity を実現する。

    Args:
        chunks: テキストチャンクのリスト。
        config: インデックスビルド設定。

    Returns:
        FAISS インデックスとメタデータの辞書のタプル。
    """
    logger.info("埋め込みモデルをロード中: %s", config.embedding_model_name)
    model = SentenceTransformer(config.embedding_model_name)

    texts = [chunk.text for chunk in chunks]
    logger.info("埋め込みベクトルを生成中: %d テキスト", len(texts))
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    embeddings = np.array(embeddings, dtype=np.float32)

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    metadata = {
        "chunks": [asdict(chunk) for chunk in chunks],
        "embedding_model": config.embedding_model_name,
        "dimension": dimension,
        "total_chunks": len(chunks),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(
        "FAISS インデックス構築完了: %d ベクトル (次元数: %d)",
        index.ntotal,
        dimension,
    )

    return index, metadata


def _upload_index(
    s3: object,
    config: IndexConfig,
    index: faiss.Index,
    metadata: dict,
    tmp_dir: Path,
) -> None:
    """FAISS インデックスとメタデータを S3 にアップロードする。

    Args:
        s3: S3 クライアント。
        config: インデックスビルド設定。
        index: FAISS インデックス。
        metadata: メタデータ辞書。
        tmp_dir: 一時ディレクトリ。
    """
    index_path = tmp_dir / "index.faiss"
    faiss.write_index(index, str(index_path))
    s3.upload_file(str(index_path), config.s3_bucket_name, config.s3_index_key)
    logger.info("インデックスをアップロード: s3://%s/%s", config.s3_bucket_name, config.s3_index_key)

    metadata_path = tmp_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    s3.upload_file(str(metadata_path), config.s3_bucket_name, config.s3_metadata_key)
    logger.info(
        "メタデータをアップロード: s3://%s/%s", config.s3_bucket_name, config.s3_metadata_key
    )
