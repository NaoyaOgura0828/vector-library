"""PDF テキスト抽出モジュールのテスト。"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("S3_BUCKET_NAME", "test-rag-bucket")

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "application" / "core"))

from build_rag_index.exceptions import PDFExtractionError
from build_rag_index.pdf_extractor import (
    PageText,
    extract_pages_from_pdf,
)


class TestExtractPagesFromPdf:
    """extract_pages_from_pdf 関数のテスト。"""

    def test_invalid_pdf_raises_extraction_error(self, tmp_path: Path) -> None:
        """無効な PDF ファイルで PDFExtractionError が発生すること。"""
        # Arrange
        invalid_pdf = tmp_path / "invalid.pdf"
        invalid_pdf.write_text("not a pdf")

        # Act / Assert
        with pytest.raises(PDFExtractionError):
            extract_pages_from_pdf(invalid_pdf)

    def test_nonexistent_file_raises_extraction_error(self) -> None:
        """存在しないファイルで PDFExtractionError が発生すること。"""
        # Arrange
        nonexistent = Path("/tmp/nonexistent_test.pdf")

        # Act / Assert
        with pytest.raises(PDFExtractionError):
            extract_pages_from_pdf(nonexistent)

    @patch("build_rag_index.pdf_extractor.PdfReader")
    def test_extracts_text_from_pages(self, mock_reader_cls: MagicMock) -> None:
        """ページからテキストを正しく抽出すること。"""
        # Arrange
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "ページ1のテキスト"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "ページ2のテキスト"
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page1, mock_page2]
        mock_reader_cls.return_value = mock_reader

        # Act
        result = extract_pages_from_pdf(Path("test.pdf"))

        # Assert
        assert len(result) == 2
        assert result[0] == PageText(source="test.pdf", page=1, text="ページ1のテキスト")
        assert result[1] == PageText(source="test.pdf", page=2, text="ページ2のテキスト")

    @patch("build_rag_index.pdf_extractor.PdfReader")
    def test_skips_empty_pages(self, mock_reader_cls: MagicMock) -> None:
        """空ページをスキップすること。"""
        # Arrange
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "テキストあり"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = ""
        mock_page3 = MagicMock()
        mock_page3.extract_text.return_value = "   "
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page1, mock_page2, mock_page3]
        mock_reader_cls.return_value = mock_reader

        # Act
        result = extract_pages_from_pdf(Path("test.pdf"))

        # Assert
        assert len(result) == 1
        assert result[0].page == 1
