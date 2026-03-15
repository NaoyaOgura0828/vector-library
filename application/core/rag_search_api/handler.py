"""Lambda ハンドラー。

API Gateway からのリクエストを受け取り、FAISS ベクトル検索を実行する。
"""

import json
import logging
from dataclasses import asdict
from typing import Any

from rag_search_api.config import SearchConfig
from rag_search_api.searcher import FaissSearcher

logger = logging.getLogger()

config = SearchConfig()
logging.basicConfig(level=getattr(logging, config.log_level))

searcher = FaissSearcher(config=config)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda エントリーポイント。

    Args:
        event: API Gateway イベント。
        context: Lambda コンテキスト。

    Returns:
        API Gateway レスポンス。
    """
    request_id = ""
    if context and hasattr(context, "aws_request_id"):
        request_id = context.aws_request_id

    logger.info(json.dumps({"message": "リクエスト受信", "request_id": request_id}))

    try:
        body = _parse_body(event)
        query = body.get("query", "")
        top_k = body.get("top_k", config.default_top_k)

        if not query or not isinstance(query, str):
            return _error_response(
                status_code=400,
                error_code="VALIDATION_ERROR",
                message="query は必須の文字列パラメータです",
                request_id=request_id,
            )

        if not isinstance(top_k, int) or top_k < 1:
            top_k = config.default_top_k
        top_k = min(top_k, config.max_top_k)

        results = searcher.search(query=query, top_k=top_k)

        response_body = {
            "data": {
                "query": query,
                "top_k": top_k,
                "total": len(results),
                "results": [asdict(r) for r in results],
            },
            "request_id": request_id,
        }

        logger.info(
            json.dumps({
                "message": "検索完了",
                "request_id": request_id,
                "query": query,
                "total_results": len(results),
            })
        )

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "X-Request-Id": request_id,
            },
            "body": json.dumps(response_body, ensure_ascii=False),
        }

    except Exception:
        logger.exception("予期しないエラーが発生しました")
        return _error_response(
            status_code=500,
            error_code="INTERNAL_ERROR",
            message="内部エラーが発生しました",
            request_id=request_id,
        )


def _parse_body(event: dict[str, Any]) -> dict[str, Any]:
    """イベントからリクエストボディを解析する。

    Args:
        event: API Gateway イベント。

    Returns:
        解析されたリクエストボディ。
    """
    body = event.get("body", "{}")
    if isinstance(body, str):
        return json.loads(body) if body else {}
    return body if isinstance(body, dict) else {}


def _error_response(
    status_code: int,
    error_code: str,
    message: str,
    request_id: str,
) -> dict[str, Any]:
    """エラーレスポンスを生成する。

    Args:
        status_code: HTTP ステータスコード。
        error_code: エラーコード。
        message: エラーメッセージ。
        request_id: リクエスト ID。

    Returns:
        API Gateway レスポンス。
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "X-Request-Id": request_id,
        },
        "body": json.dumps(
            {
                "error": {
                    "code": error_code,
                    "message": message,
                    "request_id": request_id,
                }
            },
            ensure_ascii=False,
        ),
    }
