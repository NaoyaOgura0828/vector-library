"""RAG 検索 API 設定。

Lambda コンテナ内で使用するため、application パッケージに依存しない独立した設定。
"""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SearchConfig:
    """検索 API 設定。"""

    aws_region: str = field(default_factory=lambda: os.environ.get("AWS_REGION", "us-west-2"))
    s3_bucket_name: str = field(default_factory=lambda: os.environ["S3_BUCKET_NAME"])
    embedding_model_name: str = field(
        default_factory=lambda: os.environ.get("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
    )
    s3_index_key: str = field(
        default_factory=lambda: os.environ.get("S3_INDEX_KEY", "processed/index.faiss")
    )
    s3_metadata_key: str = field(
        default_factory=lambda: os.environ.get("S3_METADATA_KEY", "processed/metadata.json")
    )
    log_level: str = field(default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO"))
    index_cache_dir: str = field(
        default_factory=lambda: os.environ.get("INDEX_CACHE_DIR", "/tmp/faiss_cache")
    )
    default_top_k: int = 5
    max_top_k: int = 20
