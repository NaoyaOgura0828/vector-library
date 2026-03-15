"""FAISS 検索モジュールのテスト。"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import faiss
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "application" / "core"))

from rag_search_api.config import SearchConfig
from rag_search_api.searcher import FaissSearcher, SearchResult


@pytest.fixture
def search_config(tmp_cache_dir: Path) -> SearchConfig:
    """テスト用検索設定を生成する。"""
    return SearchConfig(
        aws_region="us-west-2",
        s3_bucket_name="test-bucket",
        embedding_model_name="all-MiniLM-L6-v2",
        s3_index_key="processed/index.faiss",
        s3_metadata_key="processed/metadata.json",
        index_cache_dir=str(tmp_cache_dir),
    )


@pytest.fixture
def faiss_index_and_metadata(
    tmp_cache_dir: Path,
    sample_metadata: dict,
) -> tuple[Path, Path]:
    """テスト用 FAISS インデックスとメタデータファイルを作成する。"""
    dimension = 384
    n_vectors = len(sample_metadata["chunks"])
    vectors = np.random.rand(n_vectors, dimension).astype(np.float32)
    faiss.normalize_L2(vectors)

    index = faiss.IndexFlatIP(dimension)
    index.add(vectors)

    index_path = tmp_cache_dir / "index.faiss"
    faiss.write_index(index, str(index_path))

    metadata_path = tmp_cache_dir / "metadata.json"
    metadata_path.write_text(
        json.dumps(sample_metadata, ensure_ascii=False),
        encoding="utf-8",
    )

    return index_path, metadata_path


class TestFaissSearcher:
    """FaissSearcher クラスのテスト。"""

    def test_load_index_from_cache(
        self,
        search_config: SearchConfig,
        faiss_index_and_metadata: tuple[Path, Path],
    ) -> None:
        """キャッシュからインデックスを読み込めること。"""
        # Arrange
        searcher = FaissSearcher(config=search_config)

        # Act (キャッシュにファイルが存在するので S3 からダウンロードしない)
        searcher.load_index()

        # Assert
        assert searcher._index is not None
        assert searcher._index.ntotal == 3
        assert searcher._metadata is not None
        assert len(searcher._metadata["chunks"]) == 3

    @patch("rag_search_api.searcher.boto3")
    def test_load_index_downloads_from_s3(
        self,
        mock_boto3: MagicMock,
        search_config: SearchConfig,
        sample_metadata: dict,
        tmp_cache_dir: Path,
    ) -> None:
        """キャッシュがない場合に S3 からダウンロードすること。"""
        # Arrange
        dimension = 384
        vectors = np.random.rand(3, dimension).astype(np.float32)
        faiss.normalize_L2(vectors)
        index = faiss.IndexFlatIP(dimension)
        index.add(vectors)

        def mock_download(bucket: str, key: str, path: str) -> None:
            if key.endswith(".faiss"):
                faiss.write_index(index, path)
            elif key.endswith(".json"):
                Path(path).write_text(
                    json.dumps(sample_metadata, ensure_ascii=False),
                    encoding="utf-8",
                )

        mock_s3 = MagicMock()
        mock_s3.download_file.side_effect = mock_download
        mock_boto3.client.return_value = mock_s3

        # 空のキャッシュディレクトリを使用
        empty_cache = tmp_cache_dir / "empty"
        empty_cache.mkdir()
        config = SearchConfig(
            aws_region="us-west-2",
            s3_bucket_name="test-bucket",
            embedding_model_name="all-MiniLM-L6-v2",
            s3_index_key="processed/index.faiss",
            s3_metadata_key="processed/metadata.json",
            index_cache_dir=str(empty_cache),
        )
        searcher = FaissSearcher(config=config)

        # Act
        searcher.load_index()

        # Assert
        assert mock_s3.download_file.call_count == 2
        assert searcher._index is not None
        assert searcher._index.ntotal == 3

    def test_search_returns_results(
        self,
        search_config: SearchConfig,
        faiss_index_and_metadata: tuple[Path, Path],
    ) -> None:
        """検索結果が正しく返されること。"""
        # Arrange
        searcher = FaissSearcher(config=search_config)
        searcher.load_index()

        dimension = 384
        mock_model = MagicMock()
        query_vector = np.random.rand(1, dimension).astype(np.float32)
        faiss.normalize_L2(query_vector)
        mock_model.encode.return_value = query_vector
        searcher._model = mock_model

        # Act
        results = searcher.search("テストクエリ", top_k=2)

        # Assert
        assert len(results) <= 2
        assert all(isinstance(r, SearchResult) for r in results)
        assert all(r.score >= 0 for r in results)

    def test_clear_cache(
        self,
        search_config: SearchConfig,
        faiss_index_and_metadata: tuple[Path, Path],
    ) -> None:
        """キャッシュクリアでインデックスが解放されること。"""
        # Arrange
        searcher = FaissSearcher(config=search_config)
        searcher.load_index()

        # Act
        searcher.clear_cache()

        # Assert
        assert searcher._index is None
        assert searcher._metadata is None
