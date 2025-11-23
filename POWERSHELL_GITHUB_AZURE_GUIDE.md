# ABACUS v2.1 - PowerShell GitHub & Azure Deployment Guide

## 🎯 Complete Step-by-Step Guide for Windows PowerShell

**Your GitHub Repository:** `https://github.com/GBOGEB/ABACUS.git`

---

## PART 1: GitHub Sync (Pull → Commit → Push)

### Step 1: Commit Local Changes First

```powershell
# Check what needs to be committed
git status --short

# Add the deployment package
git add ABACUS_V21_DEPLOYMENT_PACKAGE/
git add ABACUS_V21_DEPLOYMENT_COMPLETE_SUMMARY.md
git add ABACUS_V21_REALISTIC_DEPLOYMENT_ROADMAP.md
git add github_azure_deployment_helper.py

# Commit with message
git commit -m "Add ABACUS v2.1 deployment package with Azure integration"
```

### Step 2: Pull Latest Changes from GitHub

```powershell
# Fetch latest changes
git fetch origin

# Pull with merge strategy (safer than rebase)
git pull origin main --no-rebase

# If there are conflicts, Git will tell you which files
# Edit those files, then:
git add <conflicted-files>
git commit -m "Merge remote changes"
```

### Step 3: Push Your Changes to GitHub

```powershell
# Push to GitHub
git push origin main

# If push is rejected (remote has changes you don't have):
git pull origin main --no-rebase
git push origin main
```

---

## PART 2: Azure Deployment Options

### Option A: Azure Container Instances (Simplest - Recommended)

#### Prerequisites:
```powershell
# Install Azure CLI (if not installed)
winget install -e --id Microsoft.AzureCLI

# Or download from: https://aka.ms/installazurecliwindows

# Install Docker Desktop (if not installed)
# Download from: https://www.docker.com/products/docker-desktop
```

#### Deployment Steps:

```powershell
# 1. Login to Azure
az login

# 2. Set your subscription (if you have multiple)
az account list --output table
az account set --subscription "<your-subscription-id>"

# 3. Create resource group
az group create `
  --name abacus-v21-rg `
  --location westeurope

# 4. Create Azure Container Registry
az acr create `
  --resource-group abacus-v21-rg `
  --name abacusv21registry `
  --sku Basic `
  --admin-enabled true

# 5. Build and push image directly to Azure
cd ABACUS_V21_DEPLOYMENT_PACKAGE
az acr build `
  --registry abacusv21registry `
  --image abacus-v21:latest `
  --file Dockerfile `
  .

# 6. Get ACR password
$ACR_PASSWORD = az acr credential show `
  --name abacusv21registry `
  --query "passwords[0].value" `
  --output tsv

# 7. Deploy to Azure Container Instances
az container create `
  --resource-group abacus-v21-rg `
  --name abacus-v21 `
  --image abacusv21registry.azurecr.io/abacus-v21:latest `
  --cpu 1 `
  --memory 1.5 `
  --registry-login-server abacusv21registry.azurecr.io `
  --registry-username abacusv21registry `
  --registry-password $ACR_PASSWORD `
  --dns-name-label abacus-v21-app `
  --ports 8000 `
  --environment-variables `
    ENVIRONMENT=production `
    LOG_LEVEL=INFO

# 8. Get the URL
Write-Host "✅ Deployment complete!"
Write-Host "🌐 Access your app at: http://abacus-v21-app.westeurope.azurecontainer.io:8000"

# 9. View logs
az container logs --resource-group abacus-v21-rg --name abacus-v21

# 10. Check status
az container show `
  --resource-group abacus-v21-rg `
  --name abacus-v21 `
  --query "{Status:instanceView.state, IP:ipAddress.ip, FQDN:ipAddress.fqdn}" `
  --output table
```

---

### Option B: Azure App Service (More Features)

```powershell
# 1. Login to Azure
az login

# 2. Create resource group (if not already created)
az group create `
  --name abacus-v21-rg `
  --location westeurope

# 3. Create App Service Plan
az appservice plan create `
  --name abacus-v21-plan `
  --resource-group abacus-v21-rg `
  --is-linux `
  --sku B1

# 4. Create Web App
az webapp create `
  --resource-group abacus-v21-rg `
  --plan abacus-v21-plan `
  --name abacus-v21-webapp `
  --deployment-container-image-name abacusv21registry.azurecr.io/abacus-v21:latest

# 5. Configure container registry credentials
az webapp config container set `
  --name abacus-v21-webapp `
  --resource-group abacus-v21-rg `
  --docker-custom-image-name abacusv21registry.azurecr.io/abacus-v21:latest `
  --docker-registry-server-url https://abacusv21registry.azurecr.io `
  --docker-registry-server-user abacusv21registry `
  --docker-registry-server-password $ACR_PASSWORD

# 6. Enable continuous deployment
az webapp deployment container config `
  --name abacus-v21-webapp `
  --resource-group abacus-v21-rg `
  --enable-cd true

# 7. Get the URL
Write-Host "✅ Deployment complete!"
Write-Host "🌐 Access your app at: https://abacus-v21-webapp.azurewebsites.net"

# 8. View logs
az webapp log tail `
  --name abacus-v21-webapp `
  --resource-group abacus-v21-rg
```

---

### Option C: Local Docker Testing (Before Azure)

```powershell
# 1. Navigate to deployment package
cd ABACUS_V21_DEPLOYMENT_PACKAGE

# 2. Build Docker image
docker build -t abacus-v21:local .

# 3. Run container locally
docker run -d `
  --name abacus-v21-local `
  -p 8000:8000 `
  -e ENVIRONMENT=development `
  abacus-v21:local

# 4. Check if running
docker ps

# 5. View logs
docker logs abacus-v21-local

# 6. Test the application
Start-Process "http://localhost:8000"

# 7. Stop container
docker stop abacus-v21-local

# 8. Remove container
docker rm abacus-v21-local
```

---

## PART 3: GitHub Actions Automated Deployment

### Step 1: Set up Azure Service Principal

```powershell
# Get your subscription ID
$SUBSCRIPTION_ID = az account show --query id --output tsv

# Create service principal
az ad sp create-for-rbac `
  --name "abacus-v21-github-sp" `
  --role contributor `
  --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/abacus-v21-rg `
  --sdk-auth

# Copy the JSON output - you'll need it for GitHub Secrets
```

### Step 2: Add GitHub Secrets

1. Go to: `https://github.com/GBOGEB/ABACUS/settings/secrets/actions`
2. Click "New repository secret"
3. Add these secrets:

| Secret Name | Value |
|-------------|-------|
| `AZURE_CREDENTIALS` | JSON output from service principal creation |
| `ACR_PASSWORD` | Password from `az acr credential show --name abacusv21registry` |
| `AZURE_SUBSCRIPTION_ID` | Your Azure subscription ID |

### Step 3: Create GitHub Actions Workflow

The workflow file is already in: `.github/workflows/azure-deploy.yml`

```powershell
# Commit and push the workflow
git add .github/workflows/azure-deploy.yml
git commit -m "Add Azure deployment workflow"
git push origin main

# The workflow will automatically run on every push to main
```

### Step 4: Monitor Deployment

1. Go to: `https://github.com/GBOGEB/ABACUS/actions`
2. Click on the latest workflow run
3. Watch the deployment progress

---

## PART 4: Monitoring & Management

### View Application Logs

```powershell
# Container Instances
az container logs --resource-group abacus-v21-rg --name abacus-v21 --follow

# App Service
az webapp log tail --name abacus-v21-webapp --resource-group abacus-v21-rg
```

### Check Resource Status

```powershell
# List all resources in resource group
az resource list --resource-group abacus-v21-rg --output table

# Get container status
az container show `
  --resource-group abacus-v21-rg `
  --name abacus-v21 `
  --query "{Status:instanceView.state, IP:ipAddress.ip}" `
  --output table
```

### Update Deployment

```powershell
# Rebuild and redeploy
cd ABACUS_V21_DEPLOYMENT_PACKAGE
az acr build --registry abacusv21registry --image abacus-v21:latest .

# Restart container
az container restart --resource-group abacus-v21-rg --name abacus-v21
```

### Clean Up Resources

```powershell
# Delete everything (when done testing)
az group delete --name abacus-v21-rg --yes --no-wait

# Or delete specific resources
az container delete --resource-group abacus-v21-rg --name abacus-v21 --yes
az acr delete --resource-group abacus-v21-rg --name abacusv21registry --yes
```

---

## PART 5: Troubleshooting

### Issue: Git push rejected

```powershell
# Solution: Pull first, then push
git pull origin main --no-rebase
git push origin main
```

### Issue: Azure CLI not found

```powershell
# Solution: Install Azure CLI
winget install -e --id Microsoft.AzureCLI

# Or download from: https://aka.ms/installazurecliwindows
# Restart PowerShell after installation
```

### Issue: Docker not found

```powershell
# Solution: Install Docker Desktop
# Download from: https://www.docker.com/products/docker-desktop
# Restart computer after installation
```

### Issue: Container won't start

```powershell
# Check logs
az container logs --resource-group abacus-v21-rg --name abacus-v21

# Check events
az container show `
  --resource-group abacus-v21-rg `
  --name abacus-v21 `
  --query "instanceView.events" `
  --output table
```

### Issue: Can't access application

```powershell
# Check if container is running
az container show `
  --resource-group abacus-v21-rg `
  --name abacus-v21 `
  --query "{Status:instanceView.state, FQDN:ipAddress.fqdn, Port:ipAddress.ports[0].port}" `
  --output table

# Check firewall/network settings
# Make sure port 8000 is accessible
```

---

## Quick Reference Commands

```powershell
# GitHub Sync
git status
git add .
git commit -m "message"
git pull origin main --no-rebase
git push origin main

# Azure Login
az login
az account list --output table
az account set --subscription "<subscription-id>"

# Deploy to Azure
cd ABACUS_V21_DEPLOYMENT_PACKAGE
az acr build --registry abacusv21registry --image abacus-v21:latest .
az container restart --resource-group abacus-v21-rg --name abacus-v21

# View Logs
az container logs --resource-group abacus-v21-rg --name abacus-v21 --follow

# Check Status
az container show --resource-group abacus-v21-rg --name abacus-v21 --query "instanceView.state"
```

---

## 📞 Support Resources

- **Azure CLI Documentation**: https://docs.microsoft.com/cli/azure/
- **Azure Container Instances**: https://docs.microsoft.com/azure/container-instances/
- **Docker Documentation**: https://docs.docker.com/
- **GitHub Actions**: https://docs.github.com/actions

---

## ✅ Success Checklist

- [ ] Local changes committed
- [ ] Pulled latest from GitHub
- [ ] Pushed to GitHub successfully
- [ ] Azure CLI installed
- [ ] Docker installed (if using local testing)
- [ ] Logged into Azure
- [ ] Resource group created
- [ ] Container registry created
- [ ] Image built and pushed
- [ ] Container deployed
- [ ] Application accessible via URL
- [ ] Logs showing no errors
- [ ] GitHub Actions configured (optional)
- [ ] Monitoring set up (optional)

---

**Generated:** 2024-11-23 23:48
**Repository:** https://github.com/GBOGEB/ABACUS.git
**Resource Group:** abacus-v21-rg
**Location:** westeurope
