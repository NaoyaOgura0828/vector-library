"""FAISS ベクトル検索モジュール。"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import boto3
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from rag_search_api.config import SearchConfig

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """検索結果。"""

    chunk_id: str
    text: str
    source: str
    page: int
    chunk_index: int
    score: float


@dataclass
class FaissSearcher:
    """FAISS を使用したベクトル検索。

    S3 からインデックスとメタデータを読み込み、
    コサイン類似度ベースの検索を実行する。

    Attributes:
        config: 検索設定。
    """

    config: SearchConfig
    _index: faiss.Index | None = field(default=None, init=False, repr=False)
    _metadata: dict[str, Any] | None = field(default=None, init=False, repr=False)
    _model: SentenceTransformer | None = field(default=None, init=False, repr=False)

    @property
    def model(self) -> SentenceTransformer:
        """埋め込みモデルを遅延ロードする。"""
        if self._model is None:
            logger.info("埋め込みモデルをロード中: %s", self.config.embedding_model_name)
            self._model = SentenceTransformer(self.config.embedding_model_name)
        return self._model

    def load_index(self) -> None:
        """S3 から FAISS インデックスとメタデータを読み込む。

        /tmp にキャッシュし、2回目以降はキャッシュから読み込む。
        """
        cache_dir = Path(self.config.index_cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)

        index_path = cache_dir / "index.faiss"
        metadata_path = cache_dir / "metadata.json"

        s3 = boto3.client("s3", region_name=self.config.aws_region)

        if not index_path.exists():
            logger.info(
                "S3 からインデックスをダウンロード: s3://%s/%s",
                self.config.s3_bucket_name,
                self.config.s3_index_key,
            )
            s3.download_file(
                self.config.s3_bucket_name,
                self.config.s3_index_key,
                str(index_path),
            )

        if not metadata_path.exists():
            logger.info(
                "S3 からメタデータをダウンロード: s3://%s/%s",
                self.config.s3_bucket_name,
                self.config.s3_metadata_key,
            )
            s3.download_file(
                self.config.s3_bucket_name,
                self.config.s3_metadata_key,
                str(metadata_path),
            )

        self._index = faiss.read_index(str(index_path))
        with metadata_path.open("r", encoding="utf-8") as f:
            self._metadata = json.load(f)

        logger.info(
            "インデックスをロード完了: %d ベクトル",
            self._index.ntotal,
        )

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """クエリテキストでベクトル検索を実行する。

        Args:
            query: 検索クエリテキスト。
            top_k: 返却する上位件数。

        Returns:
            スコア降順の検索結果リスト。
        """
        if self._index is None or self._metadata is None:
            self.load_index()

        query_vector = self.model.encode([query], normalize_embeddings=True)
        query_vector = np.array(query_vector, dtype=np.float32)

        scores, indices = self._index.search(query_vector, top_k)

        results: list[SearchResult] = []
        chunks = self._metadata["chunks"]

        for score, idx in zip(scores[0], indices[0], strict=True):
            if idx == -1:
                continue
            chunk = chunks[idx]
            results.append(
                SearchResult(
                    chunk_id=chunk["chunk_id"],
                    text=chunk["text"],
                    source=chunk["source"],
                    page=chunk["page"],
                    chunk_index=chunk["chunk_index"],
                    score=float(score),
                )
            )

        return results

    def clear_cache(self) -> None:
        """キャッシュをクリアする。"""
        self._index = None
        self._metadata = None
        cache_dir = Path(self.config.index_cache_dir)
        for f in cache_dir.iterdir():
            f.unlink()
        logger.info("インデックスキャッシュをクリアしました")
