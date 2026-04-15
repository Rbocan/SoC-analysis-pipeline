# Azure Deployment — SoC Dashboard

Architecture: Azure Static Web Apps (frontend) + Container Apps (backend) + PostgreSQL Flexible Server + Redis Cache Basic C0

## Prerequisites

- Azure CLI: `brew install azure-cli` then `az login`
- Terraform >= 1.6: `brew install terraform`
- Docker running locally

## Steps

### 1. Create resource group

```bash
az group create --name soc-dashboard-rg --location eastus
```

### 2. Build and push Docker image to ACR

```bash
# Create ACR (one-time, must be globally unique)
az acr create --resource-group soc-dashboard-rg \
  --name socdashboardacr --sku Basic

# Authenticate Docker
az acr login --name socdashboardacr

# Build and push
docker build -t soc-backend ../../backend
docker tag soc-backend socdashboardacr.azurecr.io/soc-backend:latest
docker push socdashboardacr.azurecr.io/soc-backend:latest
```

### 3. Deploy with Terraform

```bash
cd infra/azure
terraform init
terraform plan \
  -var="db_password=<strong-password>" \
  -var="secret_key=$(openssl rand -hex 32)" \
  -var="acr_image_name=socdashboardacr.azurecr.io/soc-backend:latest" \
  -var="github_repo_url=https://github.com/<yourname>/SoC-analysis-pipeline" \
  -var="github_token=<your-pat>"
terraform apply
```

### 4. Deploy with Bicep (alternative to Terraform)

**Key Vault prerequisite:** The `parameters.json` file uses Key Vault references for secrets.
Before deploying, ensure:
- A Key Vault exists with `enabledForTemplateDeployment: true`
- The deploying identity has `Microsoft.KeyVault/vaults/secrets/getSecret/action` on the vault
- Secrets `db-password`, `app-secret-key`, and `github-token` are stored in the vault

```bash
az deployment group create \
  --resource-group soc-dashboard-rg \
  --template-file main.bicep \
  --parameters @parameters.json
```

Replace `<subscription-id>` and `<vault-name>` placeholders in `parameters.json` before running.

### 5. Connect Static Web App to GitHub (Terraform only)

The `azurerm_static_site` resource does not manage GitHub Actions automatically.
After `terraform apply`:

1. Azure Portal → Static Web Apps → `soc-dashboard-frontend`
2. **Manage deployment token** → copy the token
3. In your GitHub repo, add secret: `AZURE_STATIC_WEB_APPS_API_TOKEN=<token>`
4. Add `.github/workflows/azure-static-web-apps.yml` (Azure generates this template in the portal)

The Bicep template handles this automatically via `repositoryToken`.

### 6. Update CORS after Static Web App deploys

The Container App's `CORS_ORIGINS` is set during `terraform apply`, but the Static Web App's
`defaultHostname` may not be populated on the first deployment. Additionally, `NEXT_PUBLIC_API_URL`
must be set on the Static Web App manually — the `azurerm_static_site` resource does not support
app settings via Terraform. After the first GitHub Actions build completes:

1. Note the backend URL: `terraform output backend_url`
2. Note the frontend URL: `terraform output frontend_url`
3. Set `NEXT_PUBLIC_API_URL` on the Static Web App:
   ```bash
   az staticwebapp appsettings set \
     --name soc-dashboard-frontend \
     --resource-group soc-dashboard-rg \
     --setting-names NEXT_PUBLIC_API_URL=https://<container-app-fqdn>
   ```
4. Update `CORS_ORIGINS` on the Container App:
   ```bash
   az containerapp update --name soc-backend \
     --resource-group soc-dashboard-rg \
     --set-env-vars CORS_ORIGINS='["https://<your-swa>.azurestaticapps.net"]'
   ```

## Cost (after 12-month free tier)

| Resource | Cost/mo |
|---|---|
| Container Apps (0.25 vCPU, 0–2 replicas) | ~$0–5 |
| PostgreSQL Flexible B_Standard_B1ms | ~$12 |
| Redis Cache Basic C0 | ~$16 |
| Static Web Apps Free | $0 |
| **Total** | **~$28–33/mo** |
