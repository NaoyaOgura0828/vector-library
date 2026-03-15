.PHONY: help setup lint test build-search-api build-build-index build invoke-build-index clean

help: ## ヘルプを表示
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## 開発環境セットアップ
	@command -v uv >/dev/null 2>&1 || pip install uv
	uv sync --frozen
	@if [ ! -f .env ]; then cp .env.example .env && echo ".env ファイルを作成しました。値を設定してください。"; fi

lint: ## リント実行
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy application/

test: ## テスト実行
	uv run pytest --cov=application --cov-report=term-missing

build-search-api: ## search-api Docker イメージビルド
	docker build --provenance=false -f application/core/rag_search_api/Dockerfile -t vl-search-api:latest .

build-build-index: ## build-index Docker イメージビルド
	docker build --provenance=false -f application/core/build_rag_index/Dockerfile -t vl-build-index:latest .

build: build-search-api build-build-index ## 全 Docker イメージビルド

invoke-build-index: ## build-index Lambda を呼び出してインデックス構築
	aws lambda invoke \
		--function-name $${LAMBDA_BUILD_INDEX_NAME:-vl-dev-lambda-build-index} \
		--region $${AWS_REGION:-us-west-2} \
		--profile $${AWS_PROFILE:-default} \
		--cli-read-timeout 900 \
		--payload '{}' \
		/dev/stdout

clean: ## クリーンアップ
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov .coverage coverage.xml
