#!/bin/bash

# =================================================================
# Azure 인프라 리소스 프로비저닝 및 OpenTelemetry 백엔드 앱 자동 배포 스크립트
# =================================================================
set -e

# 1. 변수 설정
RG_NAME="rg-logdoctor-test"
LOCATION="koreacentral"
LAW_NAME="law-logdoctor-test"
AI_NAME="ai-logdoctor-test"
VM_NAME="vm-logdoctor-test"
VM_USER="azureuser"

echo "================================================================="
echo "🚀 1. 리소스 그룹 생성 ($RG_NAME)"
echo "================================================================="
az group create --name "$RG_NAME" --location "$LOCATION" -o none
echo "✅ 완료"

echo "================================================================="
echo "🚀 2. Log Analytics Workspace 생성 ($LAW_NAME)"
echo "================================================================="
az monitor log-analytics workspace create --resource-group "$RG_NAME" --workspace-name "$LAW_NAME" --location "$LOCATION" -o none
# Workspace Resource ID 획득 (App Insights 연결용)
LAW_ID=$(az monitor log-analytics workspace show --resource-group "$RG_NAME" --workspace-name "$LAW_NAME" --query id -o tsv)
echo "✅ 완료 (LAW_ID: $LAW_ID)"

echo "================================================================="
echo "🚀 3. Application Insights 생성 ($AI_NAME) [Workspace-based]"
echo "================================================================="
az monitor app-insights component create --app "$AI_NAME" --location "$LOCATION" --kind web \
    --resource-group "$RG_NAME" --application-type web --workspace "$LAW_ID" -o none

# 연결 문자열 (Connection String) 추출
CONN_STR=$(az monitor app-insights component show --app "$AI_NAME" --resource-group "$RG_NAME" --query connectionString -o tsv)
echo "✅ 완료 (Connection String 획득 성공!)"

echo "================================================================="
echo "🚀 4. 가상머신(VM) 초기화 스크립트 (cloud-init) 생성"
echo "================================================================="
cat <<EOF > cloud-init.sh
#!/bin/bash
# Update packages and install python/git
apt-get update
apt-get install -y python3-pip git

# Clone repo
cd /home/$VM_USER
git clone https://github.com/logDoctor/dummy-for-test.git
chown -R $VM_USER:$VM_USER dummy-for-test

# Install dependencies
cd /home/$VM_USER/dummy-for-test/samples/python
pip3 install -r requirements.txt

# Run app in background
export APPLICATIONINSIGHTS_CONNECTION_STRING="$CONN_STR"
sudo -u $VM_USER bash -c "export APPLICATIONINSIGHTS_CONNECTION_STRING='$CONN_STR'; nohup python3 fastapi_app.py > /home/$VM_USER/app.log 2>&1 &"
EOF
echo "✅ cloud-init.sh 생성 완료"

echo "================================================================="
echo "🚀 5. Ubuntu 가상 머신(VM) 생성 ($VM_NAME)"
echo "이 작업은 몇 분 정도 걸릴 수 있습니다..."
echo "================================================================="
az vm create \
  --resource-group "$RG_NAME" \
  --name "$VM_NAME" \
  --image Ubuntu2204 \
  --size Standard_B1s \
  --admin-username "$VM_USER" \
  --generate-ssh-keys \
  --custom-data ./cloud-init.sh \
  --public-ip-sku Standard
echo "✅ VM 생성 완료"

echo "================================================================="
echo "🚀 6. 방화벽(NSG) 8000 포트 개방"
echo "================================================================="
az vm open-port --port 8000 --resource-group "$RG_NAME" --name "$VM_NAME" -o none

# VM의 공인 IP 가져오기
VM_IP=$(az vm show -d -g "$RG_NAME" -n "$VM_NAME" --query publicIps -o tsv)
echo "✅ 방화벽 개방 완료"

echo "================================================================="
echo "🎉 모든 배포가 완료되었습니다!"
echo "================================================================="
echo "- 1. 애플리케이션 주소: http://$VM_IP:8000"
echo "   (VM 부팅 후 cloud-init 스크립트가 실행될 때까지 1~2분 정도 추가 소요될 수 있습니다)"
echo "- 2. 로그 확인 주소: http://$VM_IP:8000/logs"
echo "- 3. 에러 발생 주소: http://$VM_IP:8000/error"
echo "위 엔드포인트를 호출한 뒤, Azure Portal의 '$AI_NAME(Application Insights)'와 '$LAW_NAME(LAW)'에서 실시간 트레이스를 확인할 수 있습니다."

# 임시 생성 파일 삭제
rm cloud-init.sh
