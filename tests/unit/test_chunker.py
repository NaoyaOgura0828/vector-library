"""チャンク分割モジュールのテスト。"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("S3_BUCKET_NAME", "test-rag-bucket")

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "application" / "core"))

from build_rag_index.chunker import (
    TextChunk,
    _split_text,
    split_pages_into_chunks,
)
from build_rag_index.pdf_extractor import PageText


class TestSplitText:
    """_split_text 関数のテスト。"""

    def test_short_text_returns_single_chunk(self) -> None:
        """チャンクサイズ以下のテキストは分割されないこと。"""
        # Arrange
        text = "短いテキスト"

        # Act
        result = _split_text(text, chunk_size=500, chunk_overlap=50)

        # Assert
        assert len(result) == 1
        assert result[0] == text

    def test_long_text_splits_into_multiple_chunks(self) -> None:
        """チャンクサイズを超えるテキストが複数チャンクに分割されること。"""
        # Arrange
        text = "あ" * 1000

        # Act
        result = _split_text(text, chunk_size=500, chunk_overlap=50)

        # Assert
        assert len(result) >= 2
        assert len(result[0]) == 500

    def test_overlap_between_chunks(self) -> None:
        """チャンク間にオーバーラップが存在すること。"""
        # Arrange
        text = "0123456789" * 20  # 200文字

        # Act
        result = _split_text(text, chunk_size=100, chunk_overlap=20)

        # Assert
        assert len(result) >= 2
        # 最初のチャンクの末尾と次のチャンクの先頭が重複している
        overlap = result[0][-20:]
        assert result[1].startswith(overlap)

    def test_empty_text_returns_single_empty_list(self) -> None:
        """空テキストは空リストを返すこと。"""
        # Arrange / Act
        result = _split_text("", chunk_size=500, chunk_overlap=50)

        # Assert
        assert result == [""]


class TestSplitPagesIntoChunks:
    """split_pages_into_chunks 関数のテスト。"""

    def test_single_page_single_chunk(self) -> None:
        """1ページ・チャンクサイズ以下の場合、1チャンクになること。"""
        # Arrange
        pages = [PageText(source="test.pdf", page=1, text="テストテキスト")]

        # Act
        chunks = split_pages_into_chunks(pages, chunk_size=500)

        # Assert
        assert len(chunks) == 1
        assert chunks[0].chunk_id == "test.pdf#p1#c0"
        assert chunks[0].source == "test.pdf"
        assert chunks[0].page == 1
        assert chunks[0].chunk_index == 0

    def test_chunk_id_format(self) -> None:
        """チャンク ID が {source}#p{page}#c{chunk} 形式であること。"""
        # Arrange
        pages = [
            PageText(source="doc.pdf", page=3, text="あ" * 1000),
        ]

        # Act
        chunks = split_pages_into_chunks(pages, chunk_size=500, chunk_overlap=50)

        # Assert
        assert chunks[0].chunk_id == "doc.pdf#p3#c0"
        assert chunks[1].chunk_id == "doc.pdf#p3#c1"

    def test_multiple_pages_creates_chunks_per_page(self) -> None:
        """複数ページから各ページのチャンクが生成されること。"""
        # Arrange
        pages = [
            PageText(source="test.pdf", page=1, text="ページ1"),
            PageText(source="test.pdf", page=2, text="ページ2"),
        ]

        # Act
        chunks = split_pages_into_chunks(pages, chunk_size=500)

        # Assert
        assert len(chunks) == 2
        assert chunks[0].page == 1
        assert chunks[1].page == 2

    def test_empty_pages_returns_empty_list(self) -> None:
        """空リストを渡すと空リストを返すこと。"""
        # Arrange / Act
        chunks = split_pages_into_chunks([])

        # Assert
        assert chunks == []
