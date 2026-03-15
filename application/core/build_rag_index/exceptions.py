"""インデックスビルド用例外クラス。"""


class AppError(Exception):
    """アプリケーション基底例外。"""

    def __init__(
        self,
        message: str,
        error_code: str,
        context: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.context = context or {}


class PDFExtractionError(AppError):
    """PDF テキスト抽出エラー。"""

    def __init__(self, message: str = "PDF からのテキスト抽出に失敗しました", **kwargs: object) -> None:
        super().__init__(message=message, error_code="PDF_EXTRACTION_ERROR", **kwargs)
