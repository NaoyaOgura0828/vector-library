"""Lambda ハンドラーのテスト。"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# モジュールレベルの初期化で環境変数が必要なため、import 前に設定する
os.environ.setdefault("S3_BUCKET_NAME", "test-rag-bucket")
os.environ.setdefault("AWS_REGION", "us-west-2")

# Lambda コンテナ内では rag_search_api として import されるため、
# テスト時はモジュールパスを追加する
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "application" / "core"))

from rag_search_api.handler import _error_response, _parse_body, lambda_handler


class TestParseBody:
    """_parse_body 関数のテスト。"""

    def test_json_string_body(self) -> None:
        """JSON 文字列の body を正しく解析すること。"""
        # Arrange
        event = {"body": '{"query": "テスト"}'}

        # Act
        result = _parse_body(event)

        # Assert
        assert result == {"query": "テスト"}

    def test_dict_body(self) -> None:
        """辞書型の body をそのまま返すこと。"""
        # Arrange
        event = {"body": {"query": "テスト"}}

        # Act
        result = _parse_body(event)

        # Assert
        assert result == {"query": "テスト"}

    def test_empty_body_returns_empty_dict(self) -> None:
        """空の body で空辞書を返すこと。"""
        # Arrange
        event = {"body": ""}

        # Act
        result = _parse_body(event)

        # Assert
        assert result == {}

    def test_missing_body_returns_empty_dict(self) -> None:
        """body キーがない場合に空辞書を返すこと。"""
        # Arrange
        event = {}

        # Act
        result = _parse_body(event)

        # Assert
        assert result == {}


class TestErrorResponse:
    """_error_response 関数のテスト。"""

    def test_error_response_format(self) -> None:
        """エラーレスポンスが統一フォーマットであること。"""
        # Arrange / Act
        response = _error_response(
            status_code=400,
            error_code="VALIDATION_ERROR",
            message="テストエラー",
            request_id="req-123",
        )

        # Assert
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert body["error"]["message"] == "テストエラー"
        assert body["error"]["request_id"] == "req-123"


class TestLambdaHandler:
    """lambda_handler 関数のテスト。"""

    def test_missing_query_returns_400(self) -> None:
        """query パラメータがない場合に 400 を返すこと。"""
        # Arrange
        event = {"body": "{}"}
        context = MagicMock()
        context.aws_request_id = "req-test-001"

        # Act
        response = lambda_handler(event, context)

        # Assert
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_empty_query_returns_400(self) -> None:
        """空の query で 400 を返すこと。"""
        # Arrange
        event = {"body": '{"query": ""}'}
        context = MagicMock()
        context.aws_request_id = "req-test-002"

        # Act
        response = lambda_handler(event, context)

        # Assert
        assert response["statusCode"] == 400

    @patch("rag_search_api.handler.searcher")
    def test_successful_search(self, mock_searcher: MagicMock) -> None:
        """正常な検索で 200 を返すこと。"""
        # Arrange
        from rag_search_api.searcher import SearchResult

        mock_searcher.search.return_value = [
            SearchResult(
                chunk_id="test.pdf#p1#c0",
                text="テスト結果",
                source="test.pdf",
                page=1,
                chunk_index=0,
                score=0.95,
            )
        ]
        event = {"body": '{"query": "テストクエリ", "top_k": 3}'}
        context = MagicMock()
        context.aws_request_id = "req-test-003"

        # Act
        response = lambda_handler(event, context)

        # Assert
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["data"]["total"] == 1
        assert body["data"]["results"][0]["chunk_id"] == "test.pdf#p1#c0"
        assert body["data"]["results"][0]["score"] == 0.95

    @patch("rag_search_api.handler.searcher")
    def test_top_k_clamped_to_max(self, mock_searcher: MagicMock) -> None:
        """top_k が max_top_k を超える場合にクランプされること。"""
        # Arrange
        mock_searcher.search.return_value = []
        event = {"body": '{"query": "テスト", "top_k": 100}'}
        context = MagicMock()
        context.aws_request_id = "req-test-004"

        # Act
        response = lambda_handler(event, context)

        # Assert
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["data"]["top_k"] == 20  # max_top_k
