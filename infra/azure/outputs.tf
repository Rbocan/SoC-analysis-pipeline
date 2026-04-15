output "backend_url" {
  description = "Container App backend URL"
  value       = "https://${azurerm_container_app.backend.latest_revision_fqdn}"
}

output "frontend_url" {
  description = "Static Web App frontend URL"
  value       = "https://${azurerm_static_site.frontend.default_host_name}"
}

output "acr_login_server" {
  description = "ACR login server for docker push"
  value       = azurerm_container_registry.main.login_server
}

output "postgres_host" {
  description = "PostgreSQL FQDN (for debugging)"
  value       = azurerm_postgresql_flexible_server.main.fqdn
  sensitive   = true
}

output "redis_host" {
  description = "Redis hostname (for debugging)"
  value       = azurerm_redis_cache.main.hostname
  sensitive   = true
}
