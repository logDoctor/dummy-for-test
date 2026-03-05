# Azure Deployment Quick Start Prompt

Copy and paste the following prompt into a new conversation to quickly deploy the Log Doctor dummy project to Azure:

---

**Task: Deploy Log Doctor Dummy Infrastructure & Python API**

I have a repository `github.com/logDoctor/dummy-for-test`. I want you to deploy the infrastructure and the Python application to Azure.

**Context & Requirements:**
1.  **Repository**: `https://github.com/logDoctor/dummy-for-test.git`
2.  **Deployment Script**: Use the `deploy_az_vm.sh` script in the root directory.
    - This script creates a Resource Group (`rg-logdoctor-test`), Log Analytics Workspace, Application Insights, and an Ubuntu VM.
    - It uses `cloud-init` to set up the Python environment (FastAPI) and inject the Application Insights connection string.
3.  **Pre-requisites**:
    - Ensure `az login` is done and the correct subscription is selected.
    - Ensure an SSH key (e.g., `~/.ssh/id_rsa.pub` or similar) is available for `az vm create` (the script uses `--generate-ssh-keys`).
4.  **Verification**:
    - Once the script finishes, wait ~2 minutes for `cloud-init` to complete inside the VM.
    - Verify the API is running by calling `http://<VM_IP>:8000/api/health`.
    - Confirm the `APPLICATIONINSIGHTS_CONNECTION_STRING` is correctly injected by checking the application logs or environment variables on the VM.
    - Trigger telemetry by calling `/api/logs` and `/api/error`.

**Execution Plan:**
1.  Check the current environment and files.
2.  Run `bash deploy_az_vm.sh`.
3.  Monitor the output for the VM IP address.
4.  Perform the verification steps mentioned above.
5.  Report the final application URL and status.

---
