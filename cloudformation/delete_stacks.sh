#!/bin/bash

cd $(dirname $0)

# システム名定義
SYSTEM_NAME=vl

# プロファイル定義
PROFILE=Sandbox

# リージョン名 → AWSリージョンコード変換
resolve_region() {
    case "$1" in
        oregon)   echo "us-west-2" ;;
        virginia) echo "us-east-1" ;;
        tokyo)    echo "ap-northeast-1" ;;
    esac
}

# 引数チェック
if [ -z "$1" ]; then
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

# AWS SSO認証
echo "AWS SSOにログインします..."
aws sso login --profile ${PROFILE}
if [ $? -ne 0 ]; then
    echo "エラー: AWS SSOログインに失敗しました。"
    exit 1
fi

# 実行確認
echo "------------------------------------------------------------------------------------------------------------------------------------------------------"
read -p "${SYSTEM_NAME}-${ENV_TYPE} の全リソースを削除します。実行してよろしいですか？ (Y/n) " yn

case ${yn} in
[yY])
    echo '削除を開始します。'

    delete_stack() {
        local SERVICE_NAME=$1
        local TEMPLATE_NAME=${2:-$SERVICE_NAME}

        # パラメータファイル名からリージョン名を自動取得
        local PARAM_FILE=$(ls ./templates/${TEMPLATE_NAME}/${ENV_TYPE}-*-parameters.json 2>/dev/null | head -1)
        local REGION_NAME=$(basename "$PARAM_FILE" .json)
        REGION_NAME=${REGION_NAME#${ENV_TYPE}-}
        REGION_NAME=${REGION_NAME%-parameters}
        local AWS_REGION=$(resolve_region "$REGION_NAME")

        aws cloudformation delete-stack \
            --stack-name ${SYSTEM_NAME}-${ENV_TYPE}-${SERVICE_NAME} \
            --profile ${PROFILE} \
            --region ${AWS_REGION}

        aws cloudformation wait stack-delete-complete \
            --stack-name ${SYSTEM_NAME}-${ENV_TYPE}-${SERVICE_NAME} \
            --profile ${PROFILE} \
            --region ${AWS_REGION}

    }

    #####################################
    # 削除対象リソース - 作成の逆順
    #####################################
    # delete_stack codepipeline
    # delete_stack codebuild
    # delete_stack eventbridge
    # delete_stack apigateway
    # delete_stack lambda
    # delete_stack ecr
    # delete_stack iam-role
    # delete_stack s3

    echo '削除が完了しました。'
    ;;
*)
    echo '中止しました。'
    ;;
esac

exit 0
