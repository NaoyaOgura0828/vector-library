"""テキストチャンク分割モジュール。"""

import logging
from dataclasses import dataclass

from build_rag_index.pdf_extractor import PageText

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50


@dataclass(frozen=True)
class TextChunk:
    """テキストチャンク。

    Attributes:
        chunk_id: チャンク ID（{source}#p{page}#c{chunk} 形式）。
        text: チャンクテキスト。
        source: 元ファイル名。
        page: ページ番号。
        chunk_index: チャンクインデックス。
    """

    chunk_id: str
    text: str
    source: str
    page: int
    chunk_index: int


def split_pages_into_chunks(
    pages: list[PageText],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[TextChunk]:
    """ページテキストをチャンクに分割する。

    Args:
        pages: ページテキストのリスト。
        chunk_size: チャンクの最大文字数。
        chunk_overlap: チャンク間のオーバーラップ文字数。

    Returns:
        テキストチャンクのリスト。
    """
    chunks: list[TextChunk] = []

    for page in pages:
        page_chunks = _split_text(page.text, chunk_size, chunk_overlap)

        for chunk_index, chunk_text in enumerate(page_chunks):
            chunk_id = f"{page.source}#p{page.page}#c{chunk_index}"
            chunks.append(
                TextChunk(
                    chunk_id=chunk_id,
                    text=chunk_text,
                    source=page.source,
                    page=page.page,
                    chunk_index=chunk_index,
                )
            )

    logger.info("チャンク分割完了: %d ページ → %d チャンク", len(pages), len(chunks))

    return chunks


def _split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """テキストを固定サイズのチャンクに分割する。

    Args:
        text: 分割対象テキスト。
        chunk_size: チャンクの最大文字数。
        chunk_overlap: チャンク間のオーバーラップ文字数。

    Returns:
        チャンクテキストのリスト。
    """
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    step = chunk_size - chunk_overlap

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += step

    return chunks
