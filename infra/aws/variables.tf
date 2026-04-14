variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "db_password" {
  description = "Master password for RDS PostgreSQL"
  type        = string
  sensitive   = true
}

variable "secret_key" {
  description = "FastAPI JWT secret key (generate: openssl rand -hex 32)"
  type        = string
  sensitive   = true
}

variable "ecr_image_uri" {
  description = "Full ECR image URI, e.g. 123456789.dkr.ecr.us-east-1.amazonaws.com/soc-backend:latest"
  type        = string
}

variable "github_repo_url" {
  description = "GitHub repository URL for Amplify, e.g. https://github.com/yourname/SoC-analysis-pipeline"
  type        = string
}

variable "github_token" {
  description = "GitHub personal access token for Amplify CI/CD (needs repo scope)"
  type        = string
  sensitive   = true
}
