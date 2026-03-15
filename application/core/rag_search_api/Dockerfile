FROM public.ecr.aws/lambda/python:3.14

# uv をインストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR ${LAMBDA_TASK_ROOT}

# HuggingFace キャッシュをイメージ内の固定パスに設定（Lambda 実行ユーザーからも参照可能にする）
ENV HF_HOME=${LAMBDA_TASK_ROOT}/models

# 依存定義ファイルを先にコピー（Docker layer cache 最適化）
COPY pyproject.toml uv.lock ./

# 本番依存のみシステム Python にインストール（Lambda ランタイムから参照可能にする）
RUN uv export --frozen --no-dev --no-editable -o requirements.txt && \
    uv pip install --system -r requirements.txt && \
    rm requirements.txt

# 埋め込みモデルを事前ダウンロード（オフラインで利用可能にする）
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# 実行時は HuggingFace Hub へのアクセスを無効化（事前ダウンロード済みモデルのみ使用）
ENV HF_HUB_OFFLINE=1

COPY application/core/rag_search_api/ ${LAMBDA_TASK_ROOT}/rag_search_api/

CMD ["rag_search_api.handler.lambda_handler"]
