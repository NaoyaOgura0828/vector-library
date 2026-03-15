"""MCP Server for vector-library RAG Search API."""

import json
import os
import urllib.request
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("vector-library")

API_ENDPOINT = os.environ.get("VL_API_ENDPOINT", "")
API_KEY = os.environ.get("VL_API_KEY", "")


@mcp.tool()
def search(query: str, top_k: int = 5) -> dict[str, Any]:
    """RAG検索APIでドキュメントを検索する。

    S3に格納されたPDFドキュメントからFAISSベクトル検索で関連チャンクを返す。

    Args:
        query: 検索クエリテキスト
        top_k: 返却する上位件数（デフォルト: 5）
    """
    if not API_ENDPOINT:
        return {"error": "VL_API_ENDPOINT environment variable is not set"}
    if not API_KEY:
        return {"error": "VL_API_KEY environment variable is not set"}

    url = f"{API_ENDPOINT}/search"
    payload = json.dumps({"query": query, "top_k": top_k}).encode()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": API_KEY,
        },
        method="POST",
    )

    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


if __name__ == "__main__":
    mcp.run()
