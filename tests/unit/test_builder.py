"""インデックスビルダーのテスト。"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("S3_BUCKET_NAME", "test-rag-bucket")

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "application" / "core"))

from build_rag_index.builder import (
    _download_pdfs,
    _extract_and_chunk,
)
from build_rag_index.config import IndexConfig
from build_rag_index.pdf_extractor import PageText


@pytest.fixture
def index_config() -> IndexConfig:
    """テスト用インデックスビルド設定を生成する。"""
    return IndexConfig(
        aws_region="us-west-2",
        s3_bucket_name="test-bucket",
        s3_documents_prefix="documents/",
        s3_index_key="processed/index.faiss",
        s3_metadata_key="processed/metadata.json",
    )


class TestDownloadPdfs:
    """_download_pdfs 関数のテスト。"""

    def test_downloads_pdf_files(self, index_config: IndexConfig, tmp_path: Path) -> None:
        """PDF ファイルをダウンロードすること。"""
        # Arrange
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "documents/test1.pdf"},
                {"Key": "documents/test2.pdf"},
                {"Key": "documents/readme.txt"},
            ]
        }

        def mock_download(bucket: str, key: str, path: str) -> None:
            Path(path).write_bytes(b"dummy pdf content")

        mock_s3.download_file.side_effect = mock_download

        # Act
        result = _download_pdfs(mock_s3, index_config, tmp_path)

        # Assert
        assert len(result) == 2
        assert mock_s3.download_file.call_count == 2

    def test_no_pdfs_returns_empty_list(self, index_config: IndexConfig, tmp_path: Path) -> None:
        """PDF がない場合に空リストを返すこと。"""
        # Arrange
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {"Contents": []}

        # Act
        result = _download_pdfs(mock_s3, index_config, tmp_path)

        # Assert
        assert result == []

    def test_empty_response_returns_empty_list(
        self, index_config: IndexConfig, tmp_path: Path
    ) -> None:
        """S3 レスポンスに Contents がない場合に空リストを返すこと。"""
        # Arrange
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {}

        # Act
        result = _download_pdfs(mock_s3, index_config, tmp_path)

        # Assert
        assert result == []


class TestExtractAndChunk:
    """_extract_and_chunk 関数のテスト。"""

    @patch("build_rag_index.builder.split_pages_into_chunks")
    @patch("build_rag_index.builder.extract_pages_from_pdf")
    def test_processes_multiple_pdfs(
        self,
        mock_extract: MagicMock,
        mock_split: MagicMock,
    ) -> None:
        """複数 PDF を正しく処理すること。"""
        # Arrange
        mock_extract.return_value = [PageText(source="test.pdf", page=1, text="テスト")]
        mock_split.return_value = []

        # Act
        _extract_and_chunk([Path("test1.pdf"), Path("test2.pdf")])

        # Assert
        assert mock_extract.call_count == 2
        assert mock_split.call_count == 2

    @patch("build_rag_index.builder.split_pages_into_chunks")
    @patch("build_rag_index.builder.extract_pages_from_pdf")
    def test_empty_pdf_list(
        self,
        mock_extract: MagicMock,
        mock_split: MagicMock,
    ) -> None:
        """空の PDF リストで空チャンクリストを返すこと。"""
        # Arrange / Act
        result = _extract_and_chunk([])

        # Assert
        assert result == []
        mock_extract.assert_not_called()
