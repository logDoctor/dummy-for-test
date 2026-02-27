# Master Setup Script for Azure Multi-Language Telemetry System
# Fixed version using --custom-data for reliable deployment in PowerShell.

$RGName = "telemetry-verify-rg"
$Location = "koreacentral"
$WorkspaceName = "verify-law-01"
$AppInsightsName = "verify-ai-01"
$VMName = "TelemetryHostVM"

Write-Host "--- 1. Creating Resource Group ---" -ForegroundColor Cyan
az group create --name $RGName --location $Location

Write-Host "--- 2. Creating Log Analytics Workspace ---" -ForegroundColor Cyan
az monitor log-analytics workspace create --resource-group $RGName --workspace-name $WorkspaceName

Write-Host "--- 3. Creating Application Insights (Workspace-based) ---" -ForegroundColor Cyan
az monitor app-insights component create --app $AppInsightsName --location $Location --resource-group $RGName --workspace $WorkspaceName

Write-Host "--- 4. Fetching Connection String ---" -ForegroundColor Cyan
$ConnStr = az monitor app-insights component show --app $AppInsightsName --resource-group $RGName --query connectionString --output tsv
$AI_ID = az monitor app-insights component show --app $AppInsightsName --resource-group $RGName --query id --output tsv

Write-Host "Connection String: $ConnStr"

Write-Host "--- 5. Generating Cloud-Init Script ---" -ForegroundColor Cyan
$CloudInitContent = @"
#!/bin/bash
# Install Multi-Language Runtimes
sudo apt-get update
sudo apt-get install -y python3-pip nodejs npm openjdk-17-jre-headless git curl

# Set Global Connection String
echo "APPLICATIONINSIGHTS_CONNECTION_STRING='$ConnStr'" | sudo tee -a /etc/environment
export APPLICATIONINSIGHTS_CONNECTION_STRING="$ConnStr"

# Clone & Run Samples
sudo mkdir -p /home/azureuser/app
sudo chown -R azureuser:azureuser /home/azureuser/app
cd /home/azureuser/app
git clone https://github.com/logDoctor/dummy-for-test.git .

# 1. Run Python (using uv)
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="\$HOME/.local/bin:\$PATH"
cd /home/azureuser/app/samples/python
nohup \$HOME/.local/bin/uv run --with-requirements requirements.txt uvicorn fastapi_app:app --host 0.0.0.0 --port 80 > python_app.log 2>&1 &

# 2. Run Node.js
cd /home/azureuser/app/samples/nodejs
npm install
nohup node express_app.js > node_app.log 2>&1 &

# Automated Traffic Generation (for 5 minutes)
sleep 20
for i in {1..30}; do
    curl -s http://localhost/ > /dev/null
    curl -s http://localhost/error > /dev/null
    sleep 10
done
"@

$CloudInitContent | Set-Content -Path cloud-init-final.sh

Write-Host "--- 6. Creating VM with Managed Identity & Cloud-Init ---" -ForegroundColor Cyan
az vm create `
    --resource-group $RGName `
    --name $VMName `
    --image Ubuntu2204 `
    --size Standard_B1s `
    --admin-username azureuser `
    --generate-ssh-keys `
    --assign-identity `
    --public-ip-sku Standard `
    --custom-data cloud-init-final.sh

# Get the Principal ID of the VM's Managed Identity
$PrincipalID = az vm identity show --name $VMName --resource-group $RGName --query principalId --output tsv

Write-Host "--- 7. Assigning Monitoring Roles to VM Identity ---" -ForegroundColor Cyan
az role assignment create --assignee $PrincipalID --role "Monitoring Metrics Publisher" --scope $AI_ID

Write-Host "`n--- SETUP COMPLETE ---" -ForegroundColor Green
Write-Host "로그 수집을 위해 트래픽을 자동 생성 중입니다."
Write-Host "약 5-10분 후 Azure Portal에서 'Logs' 또는 'Transaction Search'를 확인하세요."
