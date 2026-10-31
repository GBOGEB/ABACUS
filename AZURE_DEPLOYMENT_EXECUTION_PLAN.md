# 🚀 ABACUS v2.1 - Azure Deployment Execution Plan

## ✅ PHASE 0: GitHub Sync - COMPLETED!

**Status**: ✅ SUCCESS  
**Commit**: 568461a  
**Repository**: https://github.com/GBOGEB/ABACUS  
**Branch**: main (synced with origin/main)

All deployment files successfully pushed to GitHub!

---

## 📋 DEPLOYMENT PHASES OVERVIEW

```
Phase 1: Prerequisites & Setup (5-10 min)
    ↓
Phase 2: Azure Infrastructure (10-15 min)
    ↓
Phase 3: Container Build & Registry (15-20 min)
    ↓
Phase 4: Application Deployment (10-15 min)
    ↓
Phase 5: Verification & Testing (5-10 min)
    ↓
Phase 6: Monitoring Setup (Optional, 10-15 min)
```

**Total Estimated Time**: 45-85 minutes

---

## 🎯 PHASE 1: Prerequisites & Setup

### 1.1 Install Azure CLI

**Windows (PowerShell as Administrator):**
```powershell
winget install -e --id Microsoft.AzureCLI
```

**Alternative Download:**
https://aka.ms/installazurecliwindows

**Verify Installation:**
```powershell
az --version
```

### 1.2 Login to Azure

```powershell
az login
```

This will open a browser window for authentication.

### 1.3 Set Your Subscription

```powershell
# List available subscriptions
az account list --output table

# Set the subscription you want to use
az account set --subscription "YOUR_SUBSCRIPTION_NAME_OR_ID"

# Verify
az account show --output table
```

### 1.4 Install Docker Desktop (if not installed)

Download from: https://www.docker.com/products/docker-desktop/

**Verify:**
```powershell
docker --version
```

---

## 🏗️ PHASE 2: Azure Infrastructure Setup

### 2.1 Define Variables

```powershell
# Set your variables
$RESOURCE_GROUP = "abacus-rg"
$LOCATION = "westeurope"
$ACR_NAME = "abacusregistry$(Get-Random -Maximum 9999)"  # Must be globally unique
$CONTAINER_APP_ENV = "abacus-env"
$CONTAINER_APP_NAME = "abacus-app"
$IMAGE_NAME = "abacus"
$IMAGE_TAG = "v2.1"

# Display variables
Write-Host "Resource Group: $RESOURCE_GROUP" -ForegroundColor Cyan
Write-Host "Location: $LOCATION" -ForegroundColor Cyan
Write-Host "ACR Name: $ACR_NAME" -ForegroundColor Cyan
Write-Host "Container App: $CONTAINER_APP_NAME" -ForegroundColor Cyan
```

### 2.2 Create Resource Group

```powershell
az group create `
  --name $RESOURCE_GROUP `
  --location $LOCATION

# Verify
az group show --name $RESOURCE_GROUP --output table
```

### 2.3 Create Azure Container Registry (ACR)

```powershell
az acr create `
  --resource-group $RESOURCE_GROUP `
  --name $ACR_NAME `
  --sku Basic `
  --admin-enabled true

# Get ACR credentials (save these!)
az acr credential show --name $ACR_NAME --output table
```

**Expected Output:**
- Registry created successfully
- Admin username and passwords displayed

---

## 🐳 PHASE 3: Container Build & Registry

### 3.1 Navigate to Deployment Package

```powershell
cd ABACUS_V21_DEPLOYMENT_PACKAGE
```

### 3.2 Build and Push Image to ACR

**Option A: Build in Azure (Recommended)**
```powershell
az acr build `
  --registry $ACR_NAME `
  --image "${IMAGE_NAME}:${IMAGE_TAG}" `
  --file Dockerfile `
  .
```

**Option B: Build Locally and Push**
```powershell
# Login to ACR
az acr login --name $ACR_NAME

# Build image
docker build -t "${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG}" .

# Push image
docker push "${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG}"
```

### 3.3 Verify Image

```powershell
az acr repository list --name $ACR_NAME --output table
az acr repository show-tags --name $ACR_NAME --repository $IMAGE_NAME --output table
```

---

## 🚀 PHASE 4: Application Deployment

### 4.1 Create Container Apps Environment

```powershell
az containerapp env create `
  --name $CONTAINER_APP_ENV `
  --resource-group $RESOURCE_GROUP `
  --location $LOCATION
```

### 4.2 Deploy Container App

```powershell
az containerapp create `
  --name $CONTAINER_APP_NAME `
  --resource-group $RESOURCE_GROUP `
  --environment $CONTAINER_APP_ENV `
  --image "${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG}" `
  --target-port 8000 `
  --ingress external `
  --registry-server "${ACR_NAME}.azurecr.io" `
  --cpu 1.0 `
  --memory 2.0Gi `
  --min-replicas 1 `
  --max-replicas 3
```

### 4.3 Get Application URL

```powershell
$APP_URL = az containerapp show `
  --name $CONTAINER_APP_NAME `
  --resource-group $RESOURCE_GROUP `
  --query properties.configuration.ingress.fqdn `
  --output tsv

Write-Host "Application URL: https://$APP_URL" -ForegroundColor Green
```

---

## ✅ PHASE 5: Verification & Testing

### 5.1 Check Application Status

```powershell
az containerapp show `
  --name $CONTAINER_APP_NAME `
  --resource-group $RESOURCE_GROUP `
  --output table
```

### 5.2 View Application Logs

```powershell
az containerapp logs show `
  --name $CONTAINER_APP_NAME `
  --resource-group $RESOURCE_GROUP `
  --tail 50 `
  --follow
```

Press `Ctrl+C` to stop following logs.

### 5.3 Test Endpoints

```powershell
# Test health endpoint
curl "https://$APP_URL/health"

# Or use Invoke-WebRequest
Invoke-WebRequest -Uri "https://$APP_URL/health" -Method Get
```

### 5.4 Test API Endpoints

```powershell
# Test root endpoint
Invoke-WebRequest -Uri "https://$APP_URL/" -Method Get

# Test API documentation
Start-Process "https://$APP_URL/docs"
```

---

## 📊 PHASE 6: Monitoring Setup (Optional)

### 6.1 Enable Application Insights

```powershell
# Create Application Insights
az monitor app-insights component create `
  --app abacus-insights `
  --location $LOCATION `
  --resource-group $RESOURCE_GROUP `
  --application-type web

# Get instrumentation key
$INSTRUMENTATION_KEY = az monitor app-insights component show `
  --app abacus-insights `
  --resource-group $RESOURCE_GROUP `
  --query instrumentationKey `
  --output tsv

Write-Host "Instrumentation Key: $INSTRUMENTATION_KEY" -ForegroundColor Cyan
```

### 6.2 Update Container App with Monitoring

```powershell
az containerapp update `
  --name $CONTAINER_APP_NAME `
  --resource-group $RESOURCE_GROUP `
  --set-env-vars "APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=$INSTRUMENTATION_KEY"
```

### 6.3 Access Monitoring Dashboards

```powershell
# Open Azure Portal to Container App
az containerapp browse --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP

# View metrics
az monitor metrics list `
  --resource "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/$CONTAINER_APP_NAME" `
  --metric-names "Requests" `
  --output table
```

---

## 🔧 TROUBLESHOOTING

### Issue: ACR Build Fails

**Solution:**
```powershell
# Check ACR status
az acr check-health --name $ACR_NAME

# View build logs
az acr task logs --registry $ACR_NAME
```

### Issue: Container App Won't Start

**Solution:**
```powershell
# Check logs
az containerapp logs show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --tail 100

# Check revision status
az containerapp revision list --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --output table
```

### Issue: Can't Access Application URL

**Solution:**
```powershell
# Verify ingress is enabled
az containerapp ingress show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP

# Check if app is running
az containerapp replica list --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --output table
```

### Issue: Authentication Errors

**Solution:**
```powershell
# Re-login to Azure
az login

# Verify subscription
az account show

# Re-login to ACR
az acr login --name $ACR_NAME
```

---

## 🧹 CLEANUP (When Done Testing)

### Remove All Resources

```powershell
# Delete entire resource group (removes everything)
az group delete --name $RESOURCE_GROUP --yes --no-wait

# Verify deletion
az group list --output table
```

### Remove Specific Resources

```powershell
# Delete container app only
az containerapp delete --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --yes

# Delete ACR only
az acr delete --name $ACR_NAME --resource-group $RESOURCE_GROUP --yes
```

---

## 📝 QUICK REFERENCE COMMANDS

```powershell
# View all resources
az resource list --resource-group $RESOURCE_GROUP --output table

# Get app URL
az containerapp show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn -o tsv

# View logs
az containerapp logs show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --tail 50

# Scale app
az containerapp update --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --min-replicas 2 --max-replicas 5

# Update image
az containerapp update --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --image "${ACR_NAME}.azurecr.io/${IMAGE_NAME}:new-tag"
```

---

## 🎯 SUCCESS CRITERIA

✅ **Phase 1**: Azure CLI installed and logged in  
✅ **Phase 2**: Resource group and ACR created  
✅ **Phase 3**: Docker image built and pushed to ACR  
✅ **Phase 4**: Container app deployed and running  
✅ **Phase 5**: Application accessible via HTTPS URL  
✅ **Phase 6**: Monitoring enabled (optional)

---

## 📚 DOCUMENTATION LINKS

- **Azure Container Apps**: https://learn.microsoft.com/azure/container-apps/
- **Azure Container Registry**: https://learn.microsoft.com/azure/container-registry/
- **Azure CLI Reference**: https://learn.microsoft.com/cli/azure/
- **Docker Documentation**: https://docs.docker.com/

---

## 🆘 SUPPORT

If you encounter issues:

1. Check logs: `az containerapp logs show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --tail 100`
2. Verify resources: `az resource list --resource-group $RESOURCE_GROUP --output table`
3. Review Azure Portal: https://portal.azure.com
4. Check GitHub repository: https://github.com/GBOGEB/ABACUS

---

**Repository**: https://github.com/GBOGEB/ABACUS  
**Deployment Package**: `ABACUS_V21_DEPLOYMENT_PACKAGE/`  
**Status**: ✅ Ready for deployment!

🚀 **Start with Phase 1 and follow each phase in order!**
