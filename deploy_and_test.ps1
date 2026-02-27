$RGName = "dummy-test-rg"
$Location = "koreacentral"
$WorkspaceName = "dummy-workspace"
$AppInsightsName = "dummy-app-insights"
$VMName = "dummyTestVM"

Write-Host "1. Creating Resource Group..."
az group create --name $RGName --location $Location

Write-Host "2. Creating Log Analytics Workspace..."
az monitor log-analytics workspace create --resource-group $RGName --workspace-name $WorkspaceName

Write-Host "3. Creating Application Insights..."
az monitor app-insights component create --app $AppInsightsName --location $Location --resource-group $RGName --workspace $WorkspaceName

Write-Host "4. Fetching Connection String..."
$ConnStr = az monitor app-insights component show --app $AppInsightsName --resource-group $RGName --query connectionString --output tsv

Write-Host "Connection String Retrieved."

Write-Host "5. Generating Cloud-Init Script..."
$CloudInitContent = @"
#!/bin/bash
# Install dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip git curl

# Set Environment Variables
echo "APPLICATIONINSIGHTS_CONNECTION_STRING='$ConnStr'" | sudo tee -a /etc/environment
export APPLICATIONINSIGHTS_CONNECTION_STRING="$ConnStr"

# Clone the repository
sudo mkdir -p /home/azureuser/app
sudo chown -R azureuser:azureuser /home/azureuser/app
cd /home/azureuser/app
git clone https://github.com/logDoctor/dummy-for-test.git .
cd samples/python

# Setup Python environment using uv
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="\$HOME/.local/bin:\$PATH"

# Run application in the background using uv
nohup uv run --with-requirements requirements.txt uvicorn fastapi_app:app --host 0.0.0.0 --port 80 > app.log 2>&1 &


# Wait for application to be ready
sleep 10

# Generate automated traffic for 10 minutes to populate Log Analytics Workspace
for i in {1..60}; do
    curl -s http://localhost/ > /dev/null
    curl -s http://localhost/error > /dev/null
    sleep 10
done

# Kill application after traffic generation
pkill uvicorn
"@

Set-Content -Path cloud-init-test.sh -Value $CloudInitContent

Write-Host "6. Creating Virtual Machine (This may take a few minutes)..."
az vm create `
    --resource-group $RGName `
    --name $VMName `
    --image Ubuntu2204 `
    --size Standard_B2s `
    --admin-username azureuser `
    --generate-ssh-keys `
    --public-ip-sku Standard `
    --custom-data cloud-init-test.sh

Write-Host "Deployment Complete! The VM is now cloning the repo and generating logs in the background."
Write-Host "Please wait a few minutes, then check $WorkspaceName or $AppInsightsName in the Azure Portal."
