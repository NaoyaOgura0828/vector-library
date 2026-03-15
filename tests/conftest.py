"""テスト共通フィクスチャ。"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest


@pytest.fixture(autouse=True)
def _set_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """テスト用環境変数を設定する。"""
    monkeypatch.setenv("S3_BUCKET_NAME", "test-rag-bucket")
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    monkeypatch.setenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")


@pytest.fixture
def sample_metadata() -> dict:
    """テスト用メタデータを生成する。"""
    return {
        "chunks": [
            {
                "chunk_id": "test.pdf#p1#c0",
                "text": "これはテスト用のテキストです。",
                "source": "test.pdf",
                "page": 1,
                "chunk_index": 0,
            },
            {
                "chunk_id": "test.pdf#p1#c1",
                "text": "FAISS を使ったベクトル検索の例です。",
                "source": "test.pdf",
                "page": 1,
                "chunk_index": 1,
            },
            {
                "chunk_id": "test.pdf#p2#c0",
                "text": "AWS Lambda でサーバーレスに動作します。",
                "source": "test.pdf",
                "page": 2,
                "chunk_index": 0,
            },
        ],
        "embedding_model": "all-MiniLM-L6-v2",
        "dimension": 384,
        "total_chunks": 3,
        "created_at": "2026-01-01T00:00:00+00:00",
    }


@pytest.fixture
def tmp_cache_dir() -> Path:
    """テスト用キャッシュディレクトリを生成する。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
