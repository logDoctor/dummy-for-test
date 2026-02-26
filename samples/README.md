# Azure Application Insights SDK Samples

이 저장소는 다양한 프로그래밍 언어와 프레임워크에서 Azure Application Insights SDK를 사용하는 샘플 코드를 제공합니다.

---

## 1. Python (FastAPI)
- **위치**: `samples/python/fastapi_app.py`
- **사용 SDK**: `azure-monitor-opentelemetry` (최신 권장 SDK)
- **실행 방법**:
  ```bash
  pip install fastapi uvicorn azure-monitor-opentelemetry
  python fastapi_app.py
  ```

## 2. Node.js (Express)
- **위치**: `samples/nodejs/express_app.js`
- **사용 SDK**: `applicationinsights`
- **실행 방법**:
  ```bash
  npm install express applicationinsights
  node express_app.js
  ```

## 3. C# (ASP.NET Core)
- **위치**: `samples/csharp/Program.cs`
- **사용 SDK**: `Microsoft.ApplicationInsights.AspNetCore`
- **실행 방법**:
  ```bash
  dotnet add package Microsoft.ApplicationInsights.AspNetCore
  dotnet run
  ```

## 4. Java (Spring Boot)
- **위치**: `samples/java/DemoApplication.java`
- **사용 SDK**: `applicationinsights-spring-boot-starter` 또는 `Java Agent` (권장)
- **실행 방법**:
  ```bash
  java -javaagent:applicationinsights-agent-3.x.x.jar -jar your-app.jar
  ```

## 5. Go (Gin)
- **위치**: `samples/go/go_app.go`
- **사용 SDK**: `github.com/microsoft/ApplicationInsights-Go`
- **실행 방법**:
  ```bash
  go get github.com/microsoft/ApplicationInsights-Go/appinsights
  go run go_app.go
  ```

## 6. JavaScript (Web/Frontend)
- **위치**: `samples/javascript_web/index.html`
- **사용 SDK**: `applicationinsights-web` (Snippet 방식)
- **사용 방법**:
  - `index.html` 내의 `connectionString`을 실제 값으로 수정 후 브라우저에서 열기


---

## Ubuntu 배포 가이드

각 언어별 런타임 설치 및 실행 방법입니다.

### 1. Python (FastAPI)
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv -y
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn azure-monitor-opentelemetry
python fastapi_app.py
```

### 2. Node.js (Express)
```bash
# NodeSource를 통한 최신 Node.js 설치
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
npm install express applicationinsights
node express_app.js
```

### 3. C# (ASP.NET Core)
```bash
# .NET 8 SDK 설치
sudo apt install -y dotnet-sdk-8.0
dotnet new web -o AppInsightsSample
cp path/to/Program.cs AppInsightsSample/
cd AppInsightsSample
dotnet add package Microsoft.ApplicationInsights.AspNetCore
dotnet run
```

### 4. Java (Spring Boot)
```bash
sudo apt install -y openjdk-17-jdk
# applicationinsights-agent 다운로드
wget https://github.com/microsoft/ApplicationInsights-Java/releases/download/3.4.10/applicationinsights-agent-3.4.10.jar
java -javaagent:applicationinsights-agent-3.4.10.jar -jar your-app.jar
```

### 5. Go (Gin)
```bash
sudo apt install -y golang-go
go mod init sample-app
go get github.com/microsoft/ApplicationInsights-Go/appinsights
go get github.com/gin-gonic/gin
go run go_app.go
```

---

## Azure VM 자동화 (Cloud-Init)

Azure VM을 생성할 때 '고급' 탭의 **사용자 데이터(User Data)** 섹션에 아래 스크립트를 넣으면, VM 생성과 동시에 자동으로 모든 환경이 구축됩니다.

### Python FastAPI 자동 구축 예시
```bash
#!/bin/bash
# 1. 패키지 업데이트 및 설치
sudo apt update
sudo apt install python3 python3-pip python3-venv -y

# 2. 소스 코드 가져오기 (예: Git Clone)
# git clone https://github.com/your-repo/app-insights-sample.git /home/azureuser/app
mkdir -p /home/azureuser/app
cd /home/azureuser/app

# 3. 가상환경 및 패키지 설정
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn azure-monitor-opentelemetry

# 4. 환경 변수 및 서비스 등록 (Systemd)
cat <<EOF | sudo tee /etc/systemd/system/fastapi_app.service
[Unit]
Description=FastAPI App Insights Sample
After=network.target

[Service]
User=azureuser
WorkingDirectory=/home/azureuser/app
ExecStart=/home/azureuser/app/venv/bin/uvicorn fastapi_app:app --host 0.0.0.0 --port 80
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 5. 서비스 시작
sudo systemctl daemon-reload
sudo systemctl enable fastapi_app
sudo systemctl start fastapi_app
```

> [!TIP]
> **Azure VM Extension**: Java나 .NET의 경우 Azure Portal에서 VM의 "SQL/애플리케이션 계측" 설정을 통해 코드 수정 없이도 에이전트를 자동으로 주입할 수 있는 기능을 지원합니다.

---

## Azure VM 생성 (SSH & Managed Identity)

아래 명령어는 Ubuntu 22.04 VM을 생성하면서 **SSH 키를 자동 생성**하고, App Insights 접근을 위한 **관리 ID(Identity)**도 한 번에 부여합니다.

```powershell
# VM 생성 (관리 ID 부여 및 80, 22번 포트 개방)
az vm create `
    --resource-group my-resource-group `
    --name myAppVM `
    --image Ubuntu2204 `
    --size Standard_B2s `
    --admin-username azureuser `
    --generate-ssh-keys `
    --assign-identity `
    --public-ip-sku Standard `
    --custom-data cloud-init.sh
```

### 0단계: cloud-init.sh 파일 작성 (로컬 PC)
VM 생성 명령어 실행 전, 같은 디렉토리에 아래 내용으로 `cloud-init.sh` 파일을 만듭니다:

```bash
#!/bin/bash
# Azure CLI 설치
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# 관리 ID로 로그인
az login --identity

# App Insights 정보 (실제 값으로 수정 필요)
AI_NAME="my-app-insights"
RG_NAME="my-resource-group"

# 연결 문자열 획득 및 전역 환경 변수 등록
CONN_STR=$(az monitor app-insights component show --app $AI_NAME --resource-group $RG_NAME --query connectionString --output tsv)
echo "APPLICATIONINSIGHTS_CONNECTION_STRING='$CONN_STR'" | sudo tee -a /etc/environment
```

---

> [!TIP]
> **VM 사이즈 추천**: 
> - Python/Node.js/Go: `Standard_B1s` (1GiB RAM)로 충분합니다.
> - **Java (Spring Boot)**: JVM의 메모리 소모를 고려하여 최소 **`Standard_B2s` (4GiB RAM)** 이상을 권장합니다.

### 생성 후 SSH 접속 방법
```bash
# VM 생성 완료 후 출력된 publicIpAddress를 사용하여 접속
ssh azureuser@<VM_공용_IP>
```

> [!IMPORTANT]
> `--assign-identity` 옵션을 통해 VM이 생성되면, 앞서 설명한 `az login --identity` 명령어를 바로 사용할 수 있는 상태가 됩니다.

---

## Azure 리소스 사전 생성 (az CLI)

자동화 스크립트를 돌리기 전, Azure에 로그를 쌓을 공간(Application Insights)이 없다면 아래 명령어로 미리 생성할 수 있습니다.

```bash
# 1. 리소스 그룹 생성
az group create --name my-resource-group --location koreacentral

# 2. Log Analytics 작업 영역 생성
az monitor log-analytics workspace create --resource-group my-resource-group --workspace-name my-workspace

# 3. Application Insights 리소스 생성 (PowerShell 버전)
az monitor app-insights component create `
    --app my-app-insights `
    --location koreacentral `
    --resource-group my-resource-group `
    --workspace my-workspace

# (Bash를 사용 중이라면 \ 를 그대로 사용하세요)
```

> [!TIP]
> PowerShell에서는 줄바꿈 기호로 `\` 대신 **`` ` ``(백틱, Tab 키 위)**을 사용해야 합니다.

> [!NOTE]
> 한국 지역 명칭은 `koreacentral` (중부) 또는 `koreasouth` (남부) 입니다.

---

## Azure CLI를 통한 연결 문자열 동적 자동 획득

`your-connection-string`을 직접 입력하지 않고, VM 실행 시점에 Azure CLI를 사용하여 Application Insights의 연결 문자열을 자동으로 가져오는 방법입니다.

### 1단계: VM에 시스템 할당 관리 ID 활성화
VM 생성 시 또는 생성 후 **제어(Identity)** 메뉴에서 '시스템 할당(System assigned)'을 **켬(On)**으로 설정합니다. 이후 해당 관리 ID에 Application Insights 리소스에 대한 **'Log Analytics Reader'** 또는 **'Reader'** 권한을 부여합니다.

### 2단계: Cloud-Init 스크립트 수정 (동적 획득)
아래 스크립트는 VM 내에서 Azure CLI로 로그인한 뒤, 리소스 이름을 통해 연결 문자열을 가져와 환경 변수로 설정합니다.

```bash
#!/bin/bash
# 1. Azure CLI 설치
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# 2. 관리 ID로 로그인 (비밀번호 없이 내부에서 인증)
az login --identity

# 3. Application Insights 연결 문자열 가져오기
# 리소스 이름과 리소스 그룹명을 실제 값으로 변경하세요.
AI_NAME="your-app-insights-name"
RG_NAME="your-resource-group"

CONN_STR=$(az monitor app-insights component show --app $AI_NAME --resource-group $RG_NAME --query connectionString --output tsv)

# 4. 앱 실행 시 환경 변수로 주입
export APPLICATIONINSIGHTS_CONNECTION_STRING=$CONN_STR
# (이후 앱 실행 로직...)
```

> [!IMPORTANT]
> 이 방식을 사용하면 코드가 담긴 스크립트에 보안 민감 정보를 직접 노출하지 않고도 안전하게 인프라 정보를 가져올 수 있습니다.

---

## 주요 기능
- **자동 계측 (Auto-instrumentation)**: HTTP 요청, 응답, 의존성 호출 등을 자동으로 기록합니다.
- **예외 추적**: `/error` 엔드포인트를 통해 에러가 App Insights에 어떻게 수집되는지 확인할 수 있습니다.
- **수동 텔레메트리**: `trackEvent` 등을 통해 커스텀 이벤트를 남기는 예시가 포함되어 있습니다.
