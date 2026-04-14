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

# github_token is not consumed by any Terraform resource — azurerm_static_site does not
# support GitHub integration via the provider. It is declared here for parity with the
# Bicep template (which does use it). Pass it to the manual GitHub connection step in
# the README instead. Terraform will emit an "unused variable" warning; this is expected.
variable "github_token" {
  description = "GitHub personal access token for Static Web Apps CI/CD (used in README manual step, not by Terraform)"
  type        = string
  sensitive   = true
  default     = ""
}
