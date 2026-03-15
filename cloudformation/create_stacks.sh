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

create_stack() {
    local SERVICE_NAME=$1
    local TEMPLATE_NAME=${2:-$SERVICE_NAME}

    # パラメータファイル名からリージョン名を自動取得
    local PARAM_FILE=$(ls ./templates/${TEMPLATE_NAME}/${ENV_TYPE}-*-parameters.json 2>/dev/null | head -1)
    local REGION_NAME=$(basename "$PARAM_FILE" .json)
    REGION_NAME=${REGION_NAME#${ENV_TYPE}-}
    REGION_NAME=${REGION_NAME%-parameters}
    local AWS_REGION=$(resolve_region "$REGION_NAME")

    aws cloudformation create-stack \
        --stack-name ${SYSTEM_NAME}-${ENV_TYPE}-${SERVICE_NAME} \
        --template-body file://./templates/${TEMPLATE_NAME}/${TEMPLATE_NAME}.yml \
        --cli-input-json file://${PARAM_FILE} \
        --profile ${PROFILE} \
        --region ${AWS_REGION}

    aws cloudformation wait stack-create-complete \
        --stack-name ${SYSTEM_NAME}-${ENV_TYPE}-${SERVICE_NAME} \
        --profile ${PROFILE} \
        --region ${AWS_REGION}

}

push_initial_images() {
    local ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --profile ${PROFILE})
    local AWS_REGION=us-west-2
    local REGISTRY=${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

    echo "ECR ログイン"
    aws ecr get-login-password --region ${AWS_REGION} --profile ${PROFILE} | \
        docker login --username AWS --password-stdin ${REGISTRY}

    local REPOS=("${SYSTEM_NAME}-${ENV_TYPE}-search-api" "${SYSTEM_NAME}-${ENV_TYPE}-build-index")
    local DOCKERFILES=("application/core/rag_search_api/Dockerfile" "application/core/build_rag_index/Dockerfile")
    local PROJECT_ROOT=$(cd "$(dirname $0)/.."; pwd)

    for i in 0 1; do
        local REPO=${REPOS[$i]}
        local IMAGE_URI=${REGISTRY}/${REPO}:latest

        echo "初期イメージをビルド・プッシュ: ${REPO}"
        docker build --provenance=false -f ${PROJECT_ROOT}/${DOCKERFILES[$i]} -t ${IMAGE_URI} ${PROJECT_ROOT}
        docker push ${IMAGE_URI}
    done

    echo "初期イメージプッシュ完了"
}

create_s3_directories() {
    local ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --profile ${PROFILE})
    local BUCKET_NAME=${SYSTEM_NAME}-${ENV_TYPE}-rag-data-${ACCOUNT_ID}

    echo "S3 ディレクトリを作成: ${BUCKET_NAME}"

    aws s3api put-object --bucket ${BUCKET_NAME} --key documents/ --profile ${PROFILE}
    aws s3api put-object --bucket ${BUCKET_NAME} --key processed/ --profile ${PROFILE}

    echo "S3 ディレクトリ作成完了: documents/, processed/"
}

#####################################
# 構築対象リソース
#####################################
# create_stack s3
# create_s3_directories
# create_stack iam-role
# create_stack ecr
# push_initial_images
# create_stack lambda
# create_stack apigateway
# create_stack eventbridge
# create_stack codebuild
# create_stack codepipeline

exit 0
