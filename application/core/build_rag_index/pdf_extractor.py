"""PDF テキスト抽出モジュール。"""

import logging
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from build_rag_index.exceptions import PDFExtractionError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PageText:
    """抽出されたページテキスト。

    Attributes:
        source: PDF ファイル名。
        page: ページ番号（1始まり）。
        text: 抽出されたテキスト。
    """

    source: str
    page: int
    text: str


def extract_pages_from_pdf(pdf_path: Path) -> list[PageText]:
    """PDF ファイルからページごとのテキストを抽出する。

    Args:
        pdf_path: PDF ファイルパス。

    Returns:
        ページテキストのリスト。

    Raises:
        PDFExtractionError: PDF の読み込みに失敗した場合。
    """
    try:
        reader = PdfReader(str(pdf_path))
    except Exception as e:
        raise PDFExtractionError(
            message=f"PDF の読み込みに失敗しました: {pdf_path}",
            context={"pdf_path": str(pdf_path), "error": str(e)},
        ) from e

    pages: list[PageText] = []
    source = pdf_path.name

    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if text and text.strip():
            pages.append(PageText(source=source, page=page_num, text=text.strip()))

    logger.info(
        "PDF テキスト抽出完了: %s (%d ページ中 %d ページにテキストあり)",
        source,
        len(reader.pages),
        len(pages),
    )

    return pages
