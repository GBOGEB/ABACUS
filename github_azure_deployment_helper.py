#!/usr/bin/env python3
"""
ABACUS v2.1 - GitHub Sync & Azure Deployment Helper
Handles bidirectional GitHub sync and Azure cloud deployment
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

class GitHubAzureDeploymentHelper:
    def __init__(self):
        self.project_root = Path.cwd()
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "steps": [],
            "status": "in_progress"
        }
    
    def log(self, message: str, status: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{status}] {message}")
        self.results["steps"].append({
            "timestamp": timestamp,
            "status": status,
            "message": message
        })
    
    def run_command(self, cmd: List[str], check: bool = False) -> tuple:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=check,
                encoding='utf-8',
                errors='replace'
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            return e.returncode, e.stdout, e.stderr
        except Exception as e:
            return -1, "", str(e)
    
    def check_git_remote(self) -> Optional[str]:
        code, stdout, stderr = self.run_command(["git", "remote", "-v"])
        if code == 0 and stdout:
            lines = stdout.strip().split('\n')
            for line in lines:
                if 'origin' in line and '(fetch)' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        return parts[1]
        return None
    
    def sync_with_github_pull(self):
        self.log("=" * 80, "INFO")
        self.log("STEP 1: PULL LATEST CHANGES FROM GITHUB", "INFO")
        self.log("=" * 80, "INFO")
        
        remote = self.check_git_remote()
        if not remote:
            self.log("No remote repository configured", "WARNING")
            self.log("Run: git remote add origin <your-github-repo-url>", "INFO")
            return False
        
        self.log(f"Remote repository: {remote}", "SUCCESS")
        
        self.log("Fetching latest changes from GitHub...", "INFO")
        code, stdout, stderr = self.run_command(["git", "fetch", "origin"])
        if code != 0:
            self.log(f"Fetch failed: {stderr}", "ERROR")
            return False
        
        self.log("Checking current branch...", "INFO")
        code, stdout, stderr = self.run_command(["git", "branch", "--show-current"])
        current_branch = stdout.strip() if code == 0 else "main"
        self.log(f"Current branch: {current_branch}", "INFO")
        
        self.log("Pulling changes with rebase strategy...", "INFO")
        code, stdout, stderr = self.run_command([
            "git", "pull", "--rebase", "origin", current_branch
        ])
        
        if code != 0:
            if "conflict" in stderr.lower() or "conflict" in stdout.lower():
                self.log("MERGE CONFLICTS DETECTED!", "WARNING")
                self.log("Conflicts need manual resolution:", "WARNING")
                self.log(stdout + stderr, "INFO")
                self.log("\nTo resolve conflicts:", "INFO")
                self.log("1. Edit conflicted files", "INFO")
                self.log("2. Run: git add <resolved-files>", "INFO")
                self.log("3. Run: git rebase --continue", "INFO")
                return False
            else:
                self.log(f"Pull failed: {stderr}", "ERROR")
                return False
        
        self.log("Successfully pulled latest changes from GitHub", "SUCCESS")
        return True
    
    def prepare_local_changes(self):
        self.log("=" * 80, "INFO")
        self.log("STEP 2: PREPARE LOCAL CHANGES FOR PUSH", "INFO")
        self.log("=" * 80, "INFO")
        
        self.log("Checking for local changes...", "INFO")
        code, stdout, stderr = self.run_command(["git", "status", "--short"])
        
        if not stdout.strip():
            self.log("No local changes to commit", "INFO")
            return True
        
        changes = stdout.strip().split('\n')
        self.log(f"Found {len(changes)} changed files", "INFO")
        
        self.log("Adding ABACUS deployment files...", "INFO")
        files_to_add = [
            "ABACUS_V21_DEPLOYMENT_PACKAGE/",
            "ABACUS_V21_DEPLOYMENT_COMPLETE_SUMMARY.md",
            "ABACUS_V21_REALISTIC_DEPLOYMENT_ROADMAP.md",
            "abacus_v21_*.py"
        ]
        
        for pattern in files_to_add:
            code, stdout, stderr = self.run_command(["git", "add", pattern])
            if code == 0:
                self.log(f"Added: {pattern}", "SUCCESS")
        
        self.log("Creating commit...", "INFO")
        commit_msg = f"ABACUS v2.1 Deployment Package - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        code, stdout, stderr = self.run_command([
            "git", "commit", "-m", commit_msg
        ])
        
        if code == 0:
            self.log(f"Commit created: {commit_msg}", "SUCCESS")
            return True
        elif "nothing to commit" in stdout or "nothing to commit" in stderr:
            self.log("No changes to commit", "INFO")
            return True
        else:
            self.log(f"Commit failed: {stderr}", "ERROR")
            return False
    
    def push_to_github(self):
        self.log("=" * 80, "INFO")
        self.log("STEP 3: PUSH CHANGES TO GITHUB", "INFO")
        self.log("=" * 80, "INFO")
        
        code, stdout, stderr = self.run_command(["git", "branch", "--show-current"])
        current_branch = stdout.strip() if code == 0 else "main"
        
        self.log(f"Pushing to origin/{current_branch}...", "INFO")
        code, stdout, stderr = self.run_command([
            "git", "push", "origin", current_branch
        ])
        
        if code != 0:
            if "rejected" in stderr.lower():
                self.log("Push rejected - remote has changes you don't have", "WARNING")
                self.log("Run this script again to pull and merge", "INFO")
                return False
            else:
                self.log(f"Push failed: {stderr}", "ERROR")
                return False
        
        self.log("Successfully pushed to GitHub!", "SUCCESS")
        return True
    
    def generate_azure_deployment_script(self):
        self.log("=" * 80, "INFO")
        self.log("STEP 4: GENERATE AZURE DEPLOYMENT SCRIPTS", "INFO")
        self.log("=" * 80, "INFO")
        
        azure_script = """#!/usr/bin/env python3
\"\"\"
ABACUS v2.1 - Azure Cloud Deployment Script
Deploys ABACUS to Azure Container Instances or Azure App Service
\"\"\"

import os
import sys
import json
import subprocess
from datetime import datetime

class AzureDeployer:
    def __init__(self):
        self.resource_group = "abacus-v21-rg"
        self.location = "westeurope"
        self.app_name = "abacus-v21"
        self.container_registry = "abacusv21registry"
    
    def check_azure_cli(self):
        try:
            result = subprocess.run(
                ["az", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"✅ Azure CLI found: {result.stdout.split()[0]}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Azure CLI not found")
            print("Install from: https://docs.microsoft.com/cli/azure/install-azure-cli")
            return False
    
    def login_azure(self):
        print("\\n🔐 Logging into Azure...")
        result = subprocess.run(["az", "login"], check=False)
        return result.returncode == 0
    
    def create_resource_group(self):
        print(f"\\n📦 Creating resource group: {self.resource_group}")
        cmd = [
            "az", "group", "create",
            "--name", self.resource_group,
            "--location", self.location
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Resource group created in {self.location}")
            return True
        else:
            print(f"⚠️  Resource group may already exist: {result.stderr}")
            return True
    
    def create_container_registry(self):
        print(f"\\n🐳 Creating Azure Container Registry: {self.container_registry}")
        cmd = [
            "az", "acr", "create",
            "--resource-group", self.resource_group,
            "--name", self.container_registry,
            "--sku", "Basic",
            "--admin-enabled", "true"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Container registry created")
            return True
        else:
            print(f"⚠️  Registry may already exist: {result.stderr}")
            return True
    
    def build_and_push_image(self):
        print("\\n🏗️  Building and pushing Docker image to Azure...")
        
        # Build image locally
        print("Building Docker image...")
        build_cmd = [
            "docker", "build",
            "-t", f"{self.container_registry}.azurecr.io/abacus-v21:latest",
            "ABACUS_V21_DEPLOYMENT_PACKAGE/"
        ]
        result = subprocess.run(build_cmd)
        if result.returncode != 0:
            print("❌ Docker build failed")
            return False
        
        # Login to ACR
        print("Logging into Azure Container Registry...")
        login_cmd = ["az", "acr", "login", "--name", self.container_registry]
        result = subprocess.run(login_cmd)
        if result.returncode != 0:
            print("❌ ACR login failed")
            return False
        
        # Push image
        print("Pushing image to ACR...")
        push_cmd = [
            "docker", "push",
            f"{self.container_registry}.azurecr.io/abacus-v21:latest"
        ]
        result = subprocess.run(push_cmd)
        if result.returncode == 0:
            print("✅ Image pushed to Azure Container Registry")
            return True
        else:
            print("❌ Image push failed")
            return False
    
    def deploy_to_container_instances(self):
        print("\\n🚀 Deploying to Azure Container Instances...")
        
        # Get ACR credentials
        creds_cmd = [
            "az", "acr", "credential", "show",
            "--name", self.container_registry,
            "--query", "passwords[0].value",
            "-o", "tsv"
        ]
        result = subprocess.run(creds_cmd, capture_output=True, text=True)
        acr_password = result.stdout.strip()
        
        # Deploy container
        deploy_cmd = [
            "az", "container", "create",
            "--resource-group", self.resource_group,
            "--name", self.app_name,
            "--image", f"{self.container_registry}.azurecr.io/abacus-v21:latest",
            "--cpu", "1",
            "--memory", "1.5",
            "--registry-login-server", f"{self.container_registry}.azurecr.io",
            "--registry-username", self.container_registry,
            "--registry-password", acr_password,
            "--dns-name-label", self.app_name,
            "--ports", "8000"
        ]
        
        result = subprocess.run(deploy_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Deployed to Azure Container Instances")
            print(f"\\n🌐 Access your app at: http://{self.app_name}.{self.location}.azurecontainer.io:8000")
            return True
        else:
            print(f"❌ Deployment failed: {result.stderr}")
            return False
    
    def deploy_to_app_service(self):
        print("\\n🚀 Deploying to Azure App Service...")
        
        # Create App Service Plan
        print("Creating App Service Plan...")
        plan_cmd = [
            "az", "appservice", "plan", "create",
            "--name", f"{self.app_name}-plan",
            "--resource-group", self.resource_group,
            "--is-linux",
            "--sku", "B1"
        ]
        subprocess.run(plan_cmd)
        
        # Create Web App
        print("Creating Web App...")
        webapp_cmd = [
            "az", "webapp", "create",
            "--resource-group", self.resource_group,
            "--plan", f"{self.app_name}-plan",
            "--name", self.app_name,
            "--deployment-container-image-name", f"{self.container_registry}.azurecr.io/abacus-v21:latest"
        ]
        
        result = subprocess.run(webapp_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Deployed to Azure App Service")
            print(f"\\n🌐 Access your app at: https://{self.app_name}.azurewebsites.net")
            return True
        else:
            print(f"❌ Deployment failed: {result.stderr}")
            return False
    
    def run(self, deployment_type="container-instances"):
        print("╔══════════════════════════════════════════════════════════════════════════════╗")
        print("║              ABACUS v2.1 - Azure Cloud Deployment                           ║")
        print("╚══════════════════════════════════════════════════════════════════════════════╝\\n")
        
        if not self.check_azure_cli():
            return False
        
        if not self.login_azure():
            print("❌ Azure login failed")
            return False
        
        if not self.create_resource_group():
            return False
        
        if not self.create_container_registry():
            return False
        
        if not self.build_and_push_image():
            return False
        
        if deployment_type == "app-service":
            return self.deploy_to_app_service()
        else:
            return self.deploy_to_container_instances()

if __name__ == "__main__":
    deployer = AzureDeployer()
    
    print("\\nChoose deployment type:")
    print("1. Azure Container Instances (faster, simpler)")
    print("2. Azure App Service (more features)")
    
    choice = input("\\nEnter choice (1 or 2): ").strip()
    
    deployment_type = "app-service" if choice == "2" else "container-instances"
    
    success = deployer.run(deployment_type)
    
    if success:
        print("\\n✅ Deployment completed successfully!")
    else:
        print("\\n❌ Deployment failed. Check errors above.")
"""
        
        azure_script_path = self.project_root / "ABACUS_V21_DEPLOYMENT_PACKAGE" / "azure_deployment.py"
        with open(azure_script_path, 'w', encoding='utf-8') as f:
            f.write(azure_script)
        
        os.chmod(azure_script_path, 0o755)
        self.log(f"Created: {azure_script_path}", "SUCCESS")
        
        return True
    
    def generate_github_actions_azure_workflow(self):
        workflow = """name: Deploy to Azure

on:
  push:
    branches: [ main ]
  workflow_dispatch:

env:
  AZURE_WEBAPP_NAME: abacus-v21
  AZURE_RESOURCE_GROUP: abacus-v21-rg

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Login to Azure
      uses: azure/login@v1
      with:
        creds: ${{ secrets.AZURE_CREDENTIALS }}
        
    - name: Build Docker image
      run: |
        docker build -t abacus-v21:${{ github.sha }} ABACUS_V21_DEPLOYMENT_PACKAGE/
        
    - name: Push to Azure Container Registry
      run: |
        az acr login --name abacusv21registry
        docker tag abacus-v21:${{ github.sha }} abacusv21registry.azurecr.io/abacus-v21:latest
        docker push abacusv21registry.azurecr.io/abacus-v21:latest
        
    - name: Deploy to Azure Container Instances
      run: |
        az container create \\
          --resource-group ${{ env.AZURE_RESOURCE_GROUP }} \\
          --name ${{ env.AZURE_WEBAPP_NAME }} \\
          --image abacusv21registry.azurecr.io/abacus-v21:latest \\
          --cpu 1 --memory 1.5 \\
          --registry-login-server abacusv21registry.azurecr.io \\
          --registry-username abacusv21registry \\
          --registry-password ${{ secrets.ACR_PASSWORD }} \\
          --dns-name-label ${{ env.AZURE_WEBAPP_NAME }} \\
          --ports 8000
          
    - name: Deployment summary
      run: |
        echo "✅ Deployed to Azure!"
        echo "🌐 URL: http://${{ env.AZURE_WEBAPP_NAME }}.westeurope.azurecontainer.io:8000"
"""
        
        workflow_path = self.project_root / "ABACUS_V21_DEPLOYMENT_PACKAGE" / ".github" / "workflows" / "azure-deploy.yml"
        workflow_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(workflow_path, 'w', encoding='utf-8') as f:
            f.write(workflow)
        
        self.log(f"Created: {workflow_path}", "SUCCESS")
        return True
    
    def generate_instructions(self):
        instructions = """
╔══════════════════════════════════════════════════════════════════════════════╗
║           ABACUS v2.1 - GitHub Sync & Azure Deployment Guide                ║
╚══════════════════════════════════════════════════════════════════════════════╝

📋 GITHUB SYNC COMPLETED

✅ What was done:
   1. Pulled latest changes from GitHub
   2. Merged with local changes
   3. Committed new deployment package
   4. Pushed to GitHub

═══════════════════════════════════════════════════════════════════════════════

🚀 AZURE DEPLOYMENT OPTIONS

OPTION 1: Manual Azure Deployment (Recommended for first time)
───────────────────────────────────────────────────────────────────────────────

Step 1: Install Azure CLI (if not installed)
   Windows: https://aka.ms/installazurecliwindows
   Or run: winget install -e --id Microsoft.AzureCLI

Step 2: Run the deployment script
   python ABACUS_V21_DEPLOYMENT_PACKAGE/azure_deployment.py

Step 3: Follow the prompts
   - Choose deployment type (Container Instances or App Service)
   - Script will handle everything automatically

═══════════════════════════════════════════════════════════════════════════════

OPTION 2: Automated GitHub Actions Deployment
───────────────────────────────────────────────────────────────────────────────

Step 1: Set up Azure Service Principal
   az ad sp create-for-rbac --name "abacus-v21-sp" \\
     --role contributor \\
     --scopes /subscriptions/{subscription-id}/resourceGroups/abacus-v21-rg \\
     --sdk-auth

Step 2: Add GitHub Secrets
   Go to: GitHub repo → Settings → Secrets → Actions
   
   Add these secrets:
   - AZURE_CREDENTIALS: (output from Step 1)
   - ACR_PASSWORD: (from Azure Container Registry)

Step 3: Push to GitHub
   The workflow will automatically deploy on every push to main branch

═══════════════════════════════════════════════════════════════════════════════

OPTION 3: Quick Azure Container Instances Deployment
───────────────────────────────────────────────────────────────────────────────

# Login to Azure
az login

# Create resource group
az group create --name abacus-v21-rg --location westeurope

# Create container registry
az acr create --resource-group abacus-v21-rg \\
  --name abacusv21registry --sku Basic --admin-enabled true

# Build and push image
cd ABACUS_V21_DEPLOYMENT_PACKAGE
az acr build --registry abacusv21registry --image abacus-v21:latest .

# Deploy container
az container create --resource-group abacus-v21-rg \\
  --name abacus-v21 \\
  --image abacusv21registry.azurecr.io/abacus-v21:latest \\
  --cpu 1 --memory 1.5 \\
  --registry-login-server abacusv21registry.azurecr.io \\
  --registry-username abacusv21registry \\
  --registry-password $(az acr credential show --name abacusv21registry --query "passwords[0].value" -o tsv) \\
  --dns-name-label abacus-v21 \\
  --ports 8000

# Get URL
echo "Access at: http://abacus-v21.westeurope.azurecontainer.io:8000"

═══════════════════════════════════════════════════════════════════════════════

📊 MONITORING YOUR DEPLOYMENT

After deployment, access:
- Application: http://abacus-v21.westeurope.azurecontainer.io:8000
- Azure Portal: https://portal.azure.com
- Resource Group: abacus-v21-rg

View logs:
az container logs --resource-group abacus-v21-rg --name abacus-v21

═══════════════════════════════════════════════════════════════════════════════

🔧 TROUBLESHOOTING

Issue: Azure CLI not found
Solution: Install from https://aka.ms/installazurecliwindows

Issue: Docker not found
Solution: Install Docker Desktop from https://docker.com

Issue: Authentication failed
Solution: Run 'az login' and follow browser prompts

Issue: Resource already exists
Solution: Delete existing resources or use different names

═══════════════════════════════════════════════════════════════════════════════

📞 NEXT STEPS

1. ✅ GitHub sync completed
2. ⏳ Choose Azure deployment option above
3. ⏳ Run deployment
4. ⏳ Verify application is running
5. ⏳ Set up monitoring and alerts

═══════════════════════════════════════════════════════════════════════════════

For detailed documentation, see:
- ABACUS_V21_DEPLOYMENT_COMPLETE_SUMMARY.md
- ABACUS_V21_REALISTIC_DEPLOYMENT_ROADMAP.md
- ABACUS_V21_DEPLOYMENT_PACKAGE/DEPLOYMENT_GUIDE.md

═══════════════════════════════════════════════════════════════════════════════
"""
        
        instructions_file = self.project_root / "GITHUB_AZURE_DEPLOYMENT_INSTRUCTIONS.txt"
        with open(instructions_file, 'w', encoding='utf-8') as f:
            f.write(instructions)
        
        print(instructions)
        self.log(f"Instructions saved to: {instructions_file}", "SUCCESS")
    
    def save_report(self):
        report_file = self.project_root / "GITHUB_SYNC_REPORT.json"
        self.results["status"] = "completed"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2)
        
        self.log(f"Report saved: {report_file}", "SUCCESS")
    
    def run(self):
        print("╔══════════════════════════════════════════════════════════════════════════════╗")
        print("║        ABACUS v2.1 - GitHub Sync & Azure Deployment Helper                 ║")
        print("╚══════════════════════════════════════════════════════════════════════════════╝\n")
        
        # Step 1: Pull from GitHub
        if not self.sync_with_github_pull():
            self.log("GitHub pull failed or has conflicts - resolve manually", "WARNING")
            return False
        
        # Step 2: Prepare local changes
        if not self.prepare_local_changes():
            self.log("Failed to prepare local changes", "ERROR")
            return False
        
        # Step 3: Push to GitHub
        if not self.push_to_github():
            self.log("Failed to push to GitHub", "ERROR")
            return False
        
        # Step 4: Generate Azure deployment scripts
        self.generate_azure_deployment_script()
        self.generate_github_actions_azure_workflow()
        
        # Step 5: Generate instructions
        self.generate_instructions()
        
        # Step 6: Save report
        self.save_report()
        
        print("\n✅ GitHub sync and Azure deployment preparation completed!")
        print("📖 See GITHUB_AZURE_DEPLOYMENT_INSTRUCTIONS.txt for next steps")
        
        return True

if __name__ == "__main__":
    helper = GitHubAzureDeploymentHelper()
    helper.run()
