FROM public.ecr.aws/lambda/python:3.14

# uv をインストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR ${LAMBDA_TASK_ROOT}

# 依存定義ファイルを先にコピー（Docker layer cache 最適化）
COPY pyproject.toml uv.lock ./

# 本番依存のみインストール（lockファイルベースで再現可能）
RUN uv sync --frozen --no-dev --no-editable

# 埋め込みモデルを事前ダウンロード
RUN uv run --frozen --no-dev python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY application/core/rag_search_api/ ${LAMBDA_TASK_ROOT}/rag_search_api/

CMD ["rag_search_api.handler.lambda_handler"]
