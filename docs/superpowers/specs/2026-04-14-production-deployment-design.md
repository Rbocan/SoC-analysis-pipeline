# Production Deployment Design
**Date:** 2026-04-14  
**Status:** Approved  
**Goal:** Deploy the SoC Analysis Pipeline as a publicly accessible portfolio demo, with documented AWS and Azure alternatives as multi-cloud reference material.

---

## 1. Context

The SoC Analysis Pipeline is a full-stack application consisting of four services:

| Service | Technology |
|---|---|
| Frontend | Next.js 15 + React 19 |
| Backend | FastAPI + Polars + DuckDB |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |

Both production Dockerfiles are already in place. The `docker-compose.yml` remains the local development setup and is not modified.

---

## 2. Chosen Deployment: Vercel + Render

**Selected for:** demo/portfolio use. Cold starts are acceptable. Target cost: $0.

### 2.1 Architecture

```
GitHub repo
├── frontend/  ──► Vercel
│                   • Auto-detects Next.js (no Dockerfile used)
│                   • Env: NEXT_PUBLIC_API_URL=https://<app>.onrender.com
│
└── backend/   ──► Render Blueprint (render.yaml)
                    • soc-backend   — web service (backend/Dockerfile)
                    • soc-db        — managed PostgreSQL (free)
                    • soc-redis     — managed Redis (free)
```

### 2.2 Cold Start Behavior

Render free web services spin down after 15 minutes of inactivity. The first request after idle wakes the service — expect a 30–60 second delay. Subsequent requests are fast.

Supabase (not used here) has a similar pause behavior on the free tier.

### 2.3 Code Changes

#### Auto-seed on first startup (`backend/app/main.py`)

Extend the existing `lifespan` startup block to auto-seed the database and Parquet data if not yet present. The seed is idempotent — safe to run on every redeploy.

```python
# After create_all and load_products_config in lifespan startup:
import pathlib
from app.seed import create_admin, generate_data

await create_admin()                               # no-op if admin exists
parquet_dir = pathlib.Path("/data/parquet")
if not any(parquet_dir.glob("*.parquet")):
    generate_data()                                # ~1–2 min, blocks startup once
```

`generate_data()` is synchronous (Polars/NumPy CPU work). It runs in the lifespan before the server accepts requests, so no requests are served until seeding is complete. This is intentional — the app is not usable until data exists.

> **Note on ephemeral storage:** Render free tier has no persistent disk. Parquet files and PDF reports are lost on redeploy. This is acceptable for a demo — synthetic data regenerates automatically on each cold start via the auto-seed above.

#### New `render.yaml` (repo root)

Declares the Render Blueprint. All three services are provisioned together from one file.

```yaml
services:
  - type: web
    name: soc-backend
    runtime: docker
    dockerfilePath: ./backend/Dockerfile
    dockerContext: ./backend
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: soc-db
          property: connectionString
      - key: REDIS_URL
        fromService:
          name: soc-redis
          type: redis
          property: connectionString
      - key: SECRET_KEY
        generateValue: true
      - key: ENVIRONMENT
        value: production
      - key: CORS_ORIGINS
        sync: false   # set manually in Render dashboard after Vercel URL is known

databases:
  - name: soc-db
    databaseName: soc_dashboard
    user: soc
    plan: free

services:
  - type: redis
    name: soc-redis
    plan: free
    maxmemoryPolicy: noeviction
```

> **CORS setup:** After the Vercel deploy, add the Vercel URL to `CORS_ORIGINS` in the Render backend's environment variables. Format: `["https://<project>.vercel.app"]`.

### 2.4 Deployment Steps

1. Merge `render.yaml` and the `main.py` auto-seed change to `main`.
2. **Render:** Dashboard → *New Blueprint* → connect GitHub repo → select `render.yaml` → deploy. Render provisions the DB, Redis, and backend automatically.
3. **Vercel:** Dashboard → *New Project* → connect GitHub repo → set root directory to `frontend/` → add env var `NEXT_PUBLIC_API_URL=https://<soc-backend>.onrender.com` → deploy.
4. First backend start auto-seeds (~1–2 min). Render's health check holds traffic until the service is ready.
5. App is live at `https://<project>.vercel.app`.

### 2.5 Cost

| Resource | Free tier limit |
|---|---|
| Vercel | Unlimited hobby deploys |
| Render web service | 750 hrs/mo (enough for one service) |
| Render PostgreSQL | Free — **expires after 90 days**, then $7/mo |
| Render Redis | Free, 25MB max |

**Action at 90 days:** Re-create the free PostgreSQL instance and re-seed, or upgrade to the $7/mo paid plan.

---

## 3. AWS Alternative

### 3.1 Architecture

```
GitHub repo
├── frontend/  ──► AWS Amplify
│                   • Native Next.js support, SSR via Lambda
│                   • Auto-deploys from GitHub
│
└── backend/   ──► App Runner (Docker image from ECR)
                    ├── RDS PostgreSQL db.t3.micro
                    └── ElastiCache Serverless Redis
```

**Why App Runner over ECS Fargate:** App Runner is fully managed — no VPC, no task definitions, no load balancer config. Point it at a container image and it handles scaling, TLS, and health checks. Fargate gives more control but significant extra setup for a demo.

### 3.2 Cost

| Resource | Free tier | After free tier |
|---|---|---|
| AWS Amplify | 1,000 build minutes/mo, 5GB storage | ~$0.01/build minute |
| App Runner | 1M requests/mo free | ~$0.064/vCPU-hr |
| RDS db.t3.micro | 750 hrs/mo, 20GB — **12 months** | ~$15/mo |
| ElastiCache Serverless | No free tier | ~$0.008/GB-hr (~$6/mo minimum) |
| **Total after free tier** | | **~$20–25/mo** |

**Redis cost note:** ElastiCache has no free tier. For a portfolio demo, options are: (a) pay ~$6/mo, (b) run a self-managed Redis in App Runner as a sidecar, or (c) make Redis optional via feature flags and remove it from the demo deployment.

### 3.3 Deployment Guide

#### Prerequisites
- AWS account with CLI configured (`aws configure`)
- Docker installed locally
- ECR repository created: `aws ecr create-repository --repository-name soc-backend`

#### Steps

1. **Build and push Docker image to ECR:**
   ```bash
   aws ecr get-login-password --region us-east-1 | \
     docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
   docker build -t soc-backend ./backend
   docker tag soc-backend:latest <account>.dkr.ecr.us-east-1.amazonaws.com/soc-backend:latest
   docker push <account>.dkr.ecr.us-east-1.amazonaws.com/soc-backend:latest
   ```

2. **Provision infrastructure** (see IaC section below).

3. **Deploy App Runner service:**
   - Source: ECR image URI from step 1
   - Port: 8000
   - Environment variables: `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `ENVIRONMENT=production`, `CORS_ORIGINS`

4. **Deploy Amplify frontend:**
   - Connect GitHub repo in Amplify Console
   - Set root directory: `frontend/`
   - Add env var: `NEXT_PUBLIC_API_URL=https://<apprunner-url>`
   - Build command: `npm run build`

5. Set `CORS_ORIGINS` in App Runner to include the Amplify URL.

### 3.4 IaC: CloudFormation (`infra/aws/cloudformation.yaml`)

Provisions: VPC, RDS instance, ElastiCache cluster, App Runner service, Amplify app, IAM roles, and parameter store entries for secrets.

Key resources:
- `AWS::RDS::DBInstance` — PostgreSQL 16, db.t3.micro, 20GB gp2
- `AWS::ElastiCache::ServerlessCache` — Redis, minimum capacity unit
- `AWS::AppRunner::Service` — references ECR image, injects env vars from SSM Parameter Store
- `AWS::Amplify::App` — connected to GitHub, Next.js build settings

Full template: `infra/aws/cloudformation.yaml`

### 3.5 IaC: Terraform (`infra/aws/main.tf`)

Uses the `hashicorp/aws` provider. Modules:
- `modules/networking` — VPC, subnets, security groups
- `modules/database` — RDS PostgreSQL
- `modules/cache` — ElastiCache Serverless
- `modules/app-runner` — App Runner service + ECR repo
- `modules/amplify` — Amplify app + branch

```bash
cd infra/aws
terraform init
terraform plan -var="account_id=<your-account-id>"
terraform apply
```

Full configuration: `infra/aws/main.tf`, `infra/aws/variables.tf`, `infra/aws/outputs.tf`

---

## 4. Azure Alternative

### 4.1 Architecture

```
GitHub repo
├── frontend/  ──► Azure Static Web Apps
│                   • Free tier, Next.js hybrid rendering supported
│                   • Auto-deploys from GitHub via Actions
│
└── backend/   ──► Azure Container Apps
                    ├── Azure Database for PostgreSQL Flexible Server
                    └── Azure Cache for Redis Basic C0
```

**Why Container Apps over AKS:** Container Apps is the Azure equivalent of App Runner — serverless, no cluster management. AKS is Kubernetes and overkill for a single-container demo.

### 4.2 Cost

| Resource | Free tier | After free tier |
|---|---|---|
| Azure Static Web Apps | Free tier (100GB bandwidth) | $9/mo Standard |
| Container Apps | 180,000 vCPU-sec/mo free | ~$0.000024/vCPU-sec |
| PostgreSQL Flexible Server | 750 hrs/mo — **12 months** | ~$12–25/mo (size-dependent) |
| Azure Cache for Redis Basic C0 | No free tier | ~$16/mo |
| **Total after free tier** | | **~$28–40/mo** |

**Redis cost note:** Same constraint as AWS — no free tier. Same mitigation options apply.

### 4.3 Deployment Guide

#### Prerequisites
- Azure account with CLI configured (`az login`)
- Resource group created: `az group create --name soc-dashboard-rg --location eastus`

#### Steps

1. **Build and push Docker image to ACR:**
   ```bash
   az acr create --resource-group soc-dashboard-rg --name socdashboardacr --sku Basic
   az acr login --name socdashboardacr
   docker build -t soc-backend ./backend
   docker tag soc-backend socdashboardacr.azurecr.io/soc-backend:latest
   docker push socdashboardacr.azurecr.io/soc-backend:latest
   ```

2. **Provision infrastructure** (see IaC section below).

3. **Deploy Container Apps:**
   - Image: ACR image URI from step 1
   - Ingress: external, port 8000
   - Environment variables: `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `ENVIRONMENT=production`, `CORS_ORIGINS`

4. **Deploy Static Web Apps:**
   - Connect GitHub repo in Azure Portal
   - App location: `frontend/`
   - Output location: `.next`
   - Add app setting: `NEXT_PUBLIC_API_URL=https://<container-apps-url>`

5. Set `CORS_ORIGINS` in Container Apps to include the Static Web Apps URL.

### 4.4 IaC: Bicep (`infra/azure/main.bicep`)

Provisions: Container Apps environment, Container App, PostgreSQL Flexible Server, Redis Cache, Static Web App, ACR, and Key Vault for secrets.

Key resources:
- `Microsoft.DBforPostgreSQL/flexibleServers` — PostgreSQL 16, Burstable B1ms
- `Microsoft.Cache/redis` — Basic C0, 250MB
- `Microsoft.App/containerApps` — references ACR image, mounts Key Vault secrets as env vars
- `Microsoft.Web/staticSites` — connected to GitHub

```bash
cd infra/azure
az deployment group create \
  --resource-group soc-dashboard-rg \
  --template-file main.bicep \
  --parameters acrName=socdashboardacr
```

Full template: `infra/azure/main.bicep`, `infra/azure/parameters.json`

### 4.5 IaC: Terraform (`infra/azure/main.tf`)

Uses the `hashicorp/azurerm` provider. Mirrors the AWS Terraform structure:
- `modules/networking` — VNet, subnets, NSGs
- `modules/database` — PostgreSQL Flexible Server
- `modules/cache` — Redis Cache
- `modules/container-apps` — Container Apps environment + app + ACR
- `modules/static-web-app` — Static Web App + GitHub integration

```bash
cd infra/azure
terraform init
terraform plan -var="resource_group=soc-dashboard-rg"
terraform apply
```

Full configuration: `infra/azure/main.tf`, `infra/azure/variables.tf`, `infra/azure/outputs.tf`

---

## 5. Comparison Table

| | Vercel + Render | AWS | Azure |
|---|---|---|---|
| **Cost (demo)** | $0 | $0 (12mo free tier) | $0 (12mo free tier) |
| **Cost (ongoing)** | $0–7/mo* | ~$20–25/mo | ~$28–40/mo |
| **Cold starts** | Yes (Render free) | No (App Runner min instances) | No (Container Apps min replicas) |
| **Free Redis** | Yes (Render) | No | No |
| **Free DB duration** | 90 days | 12 months | 12 months |
| **Setup complexity** | Low | Medium | Medium |
| **IaC** | render.yaml | CloudFormation + Terraform | Bicep + Terraform |
| **Frontend DX** | Excellent (Vercel = Next.js creator) | Good (Amplify) | Good (Static Web Apps) |
| **Best for** | Portfolio demo | AWS-native orgs | Azure-native orgs / Microsoft shops |

*$7/mo after Render free PostgreSQL expires at 90 days.

---

## 6. Repository Structure (after implementation)

```
/
├── render.yaml                          # Render Blueprint (primary deployment)
├── backend/
│   └── app/
│       └── main.py                      # Modified: auto-seed in lifespan
├── frontend/                            # No changes
├── infra/
│   ├── aws/
│   │   ├── cloudformation.yaml
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── azure/
│       ├── main.bicep
│       ├── parameters.json
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-04-14-production-deployment-design.md
```

---

## 7. Implementation Phases

| Phase | Deliverable | Files touched |
|---|---|---|
| 1 | Working live URL (Vercel + Render) | `render.yaml`, `backend/app/main.py` |
| 2 | AWS docs + IaC | `infra/aws/cloudformation.yaml`, `infra/aws/main.tf` + vars/outputs |
| 3 | Azure docs + IaC | `infra/azure/main.bicep`, `infra/azure/parameters.json`, `infra/azure/main.tf` + vars/outputs |
