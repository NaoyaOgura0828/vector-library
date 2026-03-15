#!/bin/bash

# vector-library MCP サーバーセットアップスクリプト
# Claude Code のグローバル（user スコープ）に MCP サーバーを登録する

set -euo pipefail

# システム定義
SYSTEM_NAME=vl
PROFILE=Sandbox
AWS_REGION=us-west-2

MCP_SERVER_NAME="vector-library"
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
MCP_SERVER_PATH="${SCRIPT_DIR}/mcp_server.py"

# 引数チェック
if [ -z "${1:-}" ]; then
    echo "エラー: 環境名を指定してください。"
    echo "使用方法: $0 <環境名>"
    echo "例: $0 dev"
    echo "    $0 prod"
    exit 1
fi

ENV_TYPE=$1

# 環境名バリデーション
if [ "$ENV_TYPE" != "dev" ] && [ "$ENV_TYPE" != "prod" ]; then
    echo "エラー: 環境名は dev または prod を指定してください。"
    exit 1
fi

echo "=== vector-library MCP サーバーセットアップ ==="
echo "環境: ${ENV_TYPE}"
echo ""

# Claude Code の存在確認
if ! command -v claude &> /dev/null; then
    echo "エラー: claude コマンドが見つかりません。"
    echo "Claude Code をインストールしてください: https://docs.anthropic.com/en/docs/claude-code"
    exit 1
fi

# uv の存在確認
if ! command -v uv &> /dev/null; then
    echo "エラー: uv コマンドが見つかりません。"
    echo "uv をインストールしてください: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

# AWS SSO 認証
echo "AWS SSO にログインします..."
aws sso login --profile ${PROFILE}
if [ $? -ne 0 ]; then
    echo "エラー: AWS SSO ログインに失敗しました。"
    exit 1
fi

# API Gateway エンドポイント URL を CloudFormation エクスポートから取得
echo "API Gateway エンドポイントを取得します..."
VL_API_ENDPOINT=$(aws cloudformation list-exports \
    --profile ${PROFILE} \
    --region ${AWS_REGION} \
    --query "Exports[?Name=='${SYSTEM_NAME}-${ENV_TYPE}-apigateway-endpoint'].Value" \
    --output text)

if [ -z "${VL_API_ENDPOINT}" ] || [ "${VL_API_ENDPOINT}" = "None" ]; then
    echo "エラー: API Gateway エンドポイントが見つかりません。"
    echo "CloudFormation スタック ${SYSTEM_NAME}-${ENV_TYPE}-apigateway がデプロイされているか確認してください。"
    exit 1
fi

echo "エンドポイント: ${VL_API_ENDPOINT}"

# API Key を AWS CLI で取得
echo "API Key を取得します..."
API_KEY_ID=$(aws apigateway get-rest-apis \
    --profile ${PROFILE} \
    --region ${AWS_REGION} \
    --query "items[?name=='${SYSTEM_NAME}-${ENV_TYPE}-apigateway-search'].id" \
    --output text)

if [ -z "${API_KEY_ID}" ] || [ "${API_KEY_ID}" = "None" ]; then
    echo "エラー: REST API が見つかりません。"
    exit 1
fi

VL_API_KEY=$(aws apigateway get-api-keys \
    --profile ${PROFILE} \
    --region ${AWS_REGION} \
    --name-query "${SYSTEM_NAME}-${ENV_TYPE}-apigateway-api-key" \
    --include-values \
    --query "items[0].value" \
    --output text)

if [ -z "${VL_API_KEY}" ] || [ "${VL_API_KEY}" = "None" ]; then
    echo "エラー: API Key が見つかりません。"
    echo "CloudFormation スタック ${SYSTEM_NAME}-${ENV_TYPE}-apigateway に API Key が設定されているか確認してください。"
    exit 1
fi

echo "API Key: 取得完了"

# 既存の MCP サーバーを削除（存在する場合）
if claude mcp list 2>/dev/null | grep -q "${MCP_SERVER_NAME}"; then
    echo "既存の ${MCP_SERVER_NAME} MCP サーバーを削除します..."
    claude mcp remove "${MCP_SERVER_NAME}" --scope user
fi

# MCP サーバーを user スコープ（グローバル）で登録
echo "MCP サーバーを登録します..."
claude mcp add-json --scope user "${MCP_SERVER_NAME}" "$(cat <<EOF
{
  "type": "stdio",
  "command": "uv",
  "args": ["run", "--with", "mcp[cli]", "python", "${MCP_SERVER_PATH}"],
  "env": {
    "VL_API_ENDPOINT": "${VL_API_ENDPOINT}",
    "VL_API_KEY": "${VL_API_KEY}"
  }
}
EOF
)"

echo ""
echo "=== セットアップ完了 ==="
echo ""
echo "MCP サーバー名: ${MCP_SERVER_NAME}"
echo "スコープ: user（全プロジェクトで利用可能）"
echo "エンドポイント: ${VL_API_ENDPOINT}"
echo ""
echo "確認コマンド:"
echo "  claude mcp list"
echo "  claude mcp get ${MCP_SERVER_NAME}"
echo ""
echo "Claude Code 内で以下のように利用できます:"
echo "  「vector-library の search ツールで '検索クエリ' を検索して」"
