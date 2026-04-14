variable "resource_group" {
  description = "Azure resource group name (must exist before running)"
  type        = string
  default     = "soc-dashboard-rg"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "db_password" {
  description = "Master password for PostgreSQL Flexible Server"
  type        = string
  sensitive   = true
}

variable "secret_key" {
  description = "FastAPI JWT secret key (generate: openssl rand -hex 32)"
  type        = string
  sensitive   = true
}

variable "acr_image_name" {
  description = "Full ACR image name, e.g. socdashboardacr.azurecr.io/soc-backend:latest"
  type        = string
}

variable "github_repo_url" {
  description = "GitHub repository URL for Static Web Apps"
  type        = string
}

variable "github_token" {
  description = "GitHub personal access token for Static Web Apps CI/CD"
  type        = string
  sensitive   = true
}
