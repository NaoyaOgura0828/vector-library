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

exec_change_set() {
    local SERVICE_NAME=$1
    local TEMPLATE_NAME=${2:-$SERVICE_NAME}

    # パラメータファイル名からリージョン名を自動取得
    local PARAM_FILE=$(ls ./templates/${TEMPLATE_NAME}/${ENV_TYPE}-*-parameters.json 2>/dev/null | head -1)
    local REGION_NAME=$(basename "$PARAM_FILE" .json)
    REGION_NAME=${REGION_NAME#${ENV_TYPE}-}
    REGION_NAME=${REGION_NAME%-parameters}
    local AWS_REGION=$(resolve_region "$REGION_NAME")

    echo "------------------------------------------------------------------------------------------------------------------------------------------------------"
    echo "変更セット: ${SYSTEM_NAME}-${ENV_TYPE}-${SERVICE_NAME}-change-setを作成します。"

    # 変更セット作成
    aws cloudformation create-change-set \
        --stack-name ${SYSTEM_NAME}-${ENV_TYPE}-${SERVICE_NAME} \
        --change-set-name ${SYSTEM_NAME}-${ENV_TYPE}-${SERVICE_NAME}-change-set \
        --template-body file://./templates/${TEMPLATE_NAME}/${TEMPLATE_NAME}.yml \
        --cli-input-json file://${PARAM_FILE} \
        --profile ${PROFILE} \
        --region ${AWS_REGION}

    # 変更セット作成完了待ち
    aws cloudformation wait change-set-create-complete \
        --stack-name ${SYSTEM_NAME}-${ENV_TYPE}-${SERVICE_NAME} \
        --change-set-name ${SYSTEM_NAME}-${ENV_TYPE}-${SERVICE_NAME}-change-set \
        --profile ${PROFILE} \
        --region ${AWS_REGION}

    # Status取得
    CHANGE_SET_STATUS=$(aws cloudformation describe-change-set \
        --stack-name ${SYSTEM_NAME}-${ENV_TYPE}-${SERVICE_NAME} \
        --change-set-name ${SYSTEM_NAME}-${ENV_TYPE}-${SERVICE_NAME}-change-set \
        --query 'Status' \
        --output text \
        --profile ${PROFILE} \
        --region ${AWS_REGION})

    # 作成失敗時の処理
    if [ "$CHANGE_SET_STATUS" = "FAILED" ]; then
        echo "変更セットの作成に失敗しました。"
        echo "変更セット: ${SYSTEM_NAME}-${ENV_TYPE}-${SERVICE_NAME}-change-setを削除します。"

        aws cloudformation delete-change-set \
            --stack-name ${SYSTEM_NAME}-${ENV_TYPE}-${SERVICE_NAME} \
            --change-set-name ${SYSTEM_NAME}-${ENV_TYPE}-${SERVICE_NAME}-change-set \
            --profile ${PROFILE} \
            --region ${AWS_REGION}

        echo "変更セット: ${SYSTEM_NAME}-${ENV_TYPE}-${SERVICE_NAME}-change-setを削除しました。"
        return 1
    fi

    # 変更セット詳細表示
    DESCRIBE_CHANGE_SET=$(aws cloudformation describe-change-set \
        --stack-name ${SYSTEM_NAME}-${ENV_TYPE}-${SERVICE_NAME} \
        --change-set-name ${SYSTEM_NAME}-${ENV_TYPE}-${SERVICE_NAME}-change-set \
        --query 'Changes[*].[ResourceChange.Action, ResourceChange.LogicalResourceId, ResourceChange.PhysicalResourceId, ResourceChange.ResourceType, ResourceChange.Replacement]' \
        --output json \
        --profile ${PROFILE} \
        --region ${AWS_REGION})

    echo "変更セット: ${SYSTEM_NAME}-${ENV_TYPE}-${SERVICE_NAME}-change-set"
    echo "$DESCRIBE_CHANGE_SET" | jq -r '.[] | "--------------------------------------------------\nアクション: \(.[0])\n論理ID: \(.[1])\n物理ID: \(.[2])\nリソースタイプ: \(.[3])\n置換: \(.[4])"'
    echo "--------------------------------------------------"

    # 実行確認
    read -p "変更セット: ${SYSTEM_NAME}-${ENV_TYPE}-${SERVICE_NAME}-change-setを実行してよろしいですか？ (Y/n) " yn

    case ${yn} in
    [yY])
        echo "変更セットを実行します。"

        aws cloudformation execute-change-set \
            --stack-name ${SYSTEM_NAME}-${ENV_TYPE}-${SERVICE_NAME} \
            --change-set-name ${SYSTEM_NAME}-${ENV_TYPE}-${SERVICE_NAME}-change-set \
            --profile ${PROFILE} \
            --region ${AWS_REGION}

        aws cloudformation wait stack-update-complete \
            --stack-name ${SYSTEM_NAME}-${ENV_TYPE}-${SERVICE_NAME} \
            --profile ${PROFILE} \
            --region ${AWS_REGION}

        echo "${SYSTEM_NAME}-${ENV_TYPE}-${SERVICE_NAME}のUpdateが完了しました。"
        ;;
    *)
        echo "変更セットの実行を中止しました。"

        aws cloudformation delete-change-set \
            --stack-name ${SYSTEM_NAME}-${ENV_TYPE}-${SERVICE_NAME} \
            --change-set-name ${SYSTEM_NAME}-${ENV_TYPE}-${SERVICE_NAME}-change-set \
            --profile ${PROFILE} \
            --region ${AWS_REGION}

        echo "変更セット: ${SYSTEM_NAME}-${ENV_TYPE}-${SERVICE_NAME}-change-setを削除しました。"
        ;;
    esac

}

#####################################
# 変更対象リソース
#####################################
# exec_change_set s3
# exec_change_set iam-role
# exec_change_set ecr
# exec_change_set lambda
# exec_change_set apigateway
# exec_change_set eventbridge
# exec_change_set codebuild
# exec_change_set codepipeline

exit 0
