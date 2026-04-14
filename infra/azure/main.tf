terraform {
  required_version = ">= 1.6"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.90"
    }
  }
}

provider "azurerm" {
  features {}
}

# ── Data ───────────────────────────────────────────────────────────────────────

data "azurerm_resource_group" "main" {
  name = var.resource_group
}

# ── Log Analytics ──────────────────────────────────────────────────────────────

resource "azurerm_log_analytics_workspace" "main" {
  name                = "soc-dashboard-logs"
  location            = data.azurerm_resource_group.main.location
  resource_group_name = data.azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

# ── ACR ────────────────────────────────────────────────────────────────────────

# Production hardening: replace admin credentials with a user-assigned managed identity
# granted the AcrPull role on this registry to eliminate the stored static credential.
resource "azurerm_container_registry" "main" {
  name                = "socdashboardacr"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = data.azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = true
}

# ── Container Apps Environment ─────────────────────────────────────────────────

resource "azurerm_container_app_environment" "main" {
  name                       = "soc-container-env"
  location                   = data.azurerm_resource_group.main.location
  resource_group_name        = data.azurerm_resource_group.main.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
}

# ── PostgreSQL Flexible Server ─────────────────────────────────────────────────

resource "azurerm_postgresql_flexible_server" "main" {
  name                   = "soc-dashboard-pg"
  resource_group_name    = data.azurerm_resource_group.main.name
  location               = data.azurerm_resource_group.main.location
  version                = "16"
  administrator_login    = "soc"
  administrator_password = var.db_password
  sku_name               = "B_Standard_B1ms"
  storage_mb             = 32768
  backup_retention_days  = 7
  geo_redundant_backup_enabled = false
}

resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = "soc_dashboard"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure" {
  name             = "allow-azure-services"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# ── Redis Cache ─────────────────────────────────────────────────────────────────

resource "azurerm_redis_cache" "main" {
  name                = "soc-dashboard-redis"
  location            = data.azurerm_resource_group.main.location
  resource_group_name = data.azurerm_resource_group.main.name
  capacity            = 0
  family              = "C"
  sku_name            = "Basic"
  enable_non_ssl_port = false
  minimum_tls_version = "1.2"
}

# ── Container App ──────────────────────────────────────────────────────────────

resource "azurerm_container_app" "backend" {
  name                         = "soc-backend"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = data.azurerm_resource_group.main.name
  revision_mode                = "Single"

  registry {
    server               = azurerm_container_registry.main.login_server
    username             = azurerm_container_registry.main.admin_username
    password_secret_name = "acr-password"
  }

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.main.admin_password
  }
  secret {
    name  = "database-url"
    value = "postgresql+asyncpg://soc:${var.db_password}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/soc_dashboard?sslmode=require"
  }
  secret {
    name  = "redis-url"
    value = "rediss://:${azurerm_redis_cache.main.primary_access_key}@${azurerm_redis_cache.main.hostname}:6380/0"
  }
  secret {
    name  = "secret-key"
    value = var.secret_key
  }

  template {
    min_replicas = 0
    max_replicas = 2

    container {
      name   = "soc-backend"
      image  = var.acr_image_name
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }
      env {
        name        = "REDIS_URL"
        secret_name = "redis-url"
      }
      env {
        name        = "SECRET_KEY"
        secret_name = "secret-key"
      }
      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
      # Note: azurerm_static_site does not expose defaultHostname until after provisioning.
      # After first apply, update CORS_ORIGINS with the actual Static Web App hostname.
      env {
        name  = "CORS_ORIGINS"
        value = "[\"https://${azurerm_static_site.frontend.default_host_name}\"]"
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "auto"
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
}

# ── Static Web App ─────────────────────────────────────────────────────────────

resource "azurerm_static_site" "frontend" {
  name                = "soc-dashboard-frontend"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = "eastus2"  # Static Web Apps has limited region availability
  sku_tier            = "Free"
  sku_size            = "Free"
}

# Note: azurerm_static_site does not directly manage GitHub integration via Terraform.
# After apply, connect the GitHub repo manually in the Azure Portal:
# Static Web Apps → soc-dashboard-frontend → Manage deployment token
# Then add the token as a GitHub Actions secret in your repo.
