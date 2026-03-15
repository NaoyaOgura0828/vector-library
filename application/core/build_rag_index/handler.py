"""Lambda ハンドラー。

手動実行または EventBridge からトリガーされ、
S3 上の PDF から FAISS インデックスを構築する。
"""

import json
import logging
from typing import Any

from build_rag_index.builder import build_index
from build_rag_index.config import IndexConfig

logger = logging.getLogger()

config = IndexConfig()
logging.basicConfig(level=getattr(logging, config.log_level))


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda エントリーポイント。

    Args:
        event: Lambda イベント。
        context: Lambda コンテキスト。

    Returns:
        実行結果レスポンス。
    """
    request_id = ""
    if context and hasattr(context, "aws_request_id"):
        request_id = context.aws_request_id

    logger.info(json.dumps({"message": "インデックスビルド開始", "request_id": request_id}))

    try:
        result = build_index(config=config)

        response_body = {
            "message": "インデックスビルド完了",
            "total_chunks": result["total_chunks"],
            "request_id": request_id,
        }

        logger.info(json.dumps({
            "message": "インデックスビルド完了",
            "request_id": request_id,
            "total_chunks": result["total_chunks"],
        }))

        return {
            "statusCode": 200,
            "body": json.dumps(response_body, ensure_ascii=False),
        }

    except Exception:
        logger.exception("インデックスビルド中にエラーが発生しました")
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "error": {
                        "code": "INDEX_BUILD_ERROR",
                        "message": "インデックスビルドに失敗しました",
                        "request_id": request_id,
                    }
                },
                ensure_ascii=False,
            ),
        }
