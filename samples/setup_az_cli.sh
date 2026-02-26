#!/bin/bash

# =================================================================
# Azure Application Insights - Dynamic Setup via Azure CLI
# =================================================================

# 1. 인자 확인
if [ "$#" -ne 2 ]; then
    echo "사용법: $0 <리소스_이름> <리소스_그룹>"
    echo "예시: $0 my-app-insights my-resource-group"
    exit 1
fi

AI_NAME=$1
RG_NAME=$2

echo "🔍 Azure 리소스 정보를 가져오는 중..."

# 2. Azure CLI 설치 확인 및 설치
if ! command -v az &> /dev/null; then
    echo "⚙️ Azure CLI가 없습니다. 설치를 시작합니다..."
    curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
fi

# 3. Azure 로그인 확인 (관리 ID 사용)
echo "🔑 Azure에 로그인 중 (Managed Identity)..."
az login --identity &> /dev/null
if [ $? -ne 0 ]; then
    echo "❌ 로그인 실패! VM에 Managed Identity가 활성화되어 있고 권한이 있는지 확인하세요."
    exit 1
fi

# 4. Connection String 획득
echo "📡 Connection String을 가져오는 중..."
CONN_STR=$(az monitor app-insights component show --app "$AI_NAME" --resource-group "$RG_NAME" --query connectionString --output tsv)

if [ -z "$CONN_STR" ]; then
    echo "❌ 연결 문자열을 가져오지 못했습니다. 이름과 그룹명을 확인하세요."
    exit 1
fi

echo "✅ 성공적으로 가져왔습니다!"

# 5. 환경 변수 설정 및 실행 예시
export APPLICATIONINSIGHTS_CONNECTION_STRING=$CONN_STR

echo "🚀 애플리케이션을 실행합니다..."
# 예: python3 app.py 또는 node app.js
# 여기에 실제 실행 명령어를 넣으세요.
# python3 samples/python/fastapi_app.py
