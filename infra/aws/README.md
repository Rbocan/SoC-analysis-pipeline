# AWS Deployment — SoC Dashboard

Architecture: AWS Amplify (frontend) + App Runner (backend) + RDS PostgreSQL + ElastiCache Redis

## Prerequisites

- AWS CLI configured: `aws configure`
- Terraform >= 1.6: `brew install terraform`
- Docker running locally

## Steps

### 1. Build and push Docker image to ECR

```bash
# Create ECR repo (one-time)
aws ecr create-repository --repository-name soc-backend --region us-east-1

# Authenticate Docker with ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com

# Build and push
docker build -t soc-backend ../../backend
docker tag soc-backend:latest \
  $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com/soc-backend:latest
docker push \
  $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com/soc-backend:latest
```

### 2. Deploy with Terraform

```bash
cd infra/aws
terraform init
terraform plan \
  -var="db_password=<strong-password>" \
  -var="secret_key=$(openssl rand -hex 32)" \
  -var="ecr_image_uri=<account>.dkr.ecr.us-east-1.amazonaws.com/soc-backend:latest" \
  -var="github_repo_url=https://github.com/<yourname>/SoC-analysis-pipeline"
terraform apply   # review plan, then type 'yes'
```

### 3. Deploy with CloudFormation (alternative to Terraform)

```bash
aws cloudformation deploy \
  --template-file cloudformation.yaml \
  --stack-name soc-dashboard \
  --parameter-overrides \
      DBPassword=<strong-password> \
      SecretKey=$(openssl rand -hex 32) \
      ECRImageURI=<account>.dkr.ecr.us-east-1.amazonaws.com/soc-backend:latest \
      GitHubRepoURL=https://github.com/<yourname>/SoC-analysis-pipeline \
  --capabilities CAPABILITY_NAMED_IAM
```

## Cost (after 12-month free tier)

| Resource | Cost/mo |
|---|---|
| App Runner (0.25 vCPU / 0.5 GB) | ~$5–10 |
| RDS db.t3.micro | ~$15 |
| ElastiCache cache.t3.micro | ~$14 |
| Amplify | ~$0–1 |
| **Total** | **~$35–40/mo** |
