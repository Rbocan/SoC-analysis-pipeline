output "backend_url" {
  description = "App Runner backend URL"
  value       = "https://${aws_apprunner_service.backend.service_url}"
}

output "frontend_url" {
  description = "Amplify frontend URL"
  value       = "https://main.${aws_amplify_app.frontend.default_domain}"
}

output "ecr_repository_url" {
  description = "ECR repository URL for pushing images"
  value       = aws_ecr_repository.backend.repository_url
}

output "database_endpoint" {
  description = "RDS endpoint (for debugging)"
  value       = aws_db_instance.main.address
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache endpoint (for debugging)"
  value       = aws_elasticache_cluster.main.cache_nodes[0].address
  sensitive   = true
}
