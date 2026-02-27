#!/bin/bash
# Install dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip git curl

# Set Environment Variables
echo "APPLICATIONINSIGHTS_CONNECTION_STRING='InstrumentationKey=95f797ad-4627-475e-bbe2-50dbc8900f75;IngestionEndpoint=https://koreacentral-0.in.applicationinsights.azure.com/;LiveEndpoint=https://koreacentral.livediagnostics.monitor.azure.com/;ApplicationId=8fc705cc-8c1e-4ac4-978e-691dd4c38db4'" | sudo tee -a /etc/environment
export APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=95f797ad-4627-475e-bbe2-50dbc8900f75;IngestionEndpoint=https://koreacentral-0.in.applicationinsights.azure.com/;LiveEndpoint=https://koreacentral.livediagnostics.monitor.azure.com/;ApplicationId=8fc705cc-8c1e-4ac4-978e-691dd4c38db4"

# Clone the repository
sudo mkdir -p /home/azureuser/app
sudo chown -R azureuser:azureuser /home/azureuser/app
cd /home/azureuser/app
git clone https://github.com/logDoctor/dummy-for-test.git .
cd samples/python

# Setup Python environment using uv
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="\C:\Users\UserK/.local/bin:\"

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
