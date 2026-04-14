terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ── Data ───────────────────────────────────────────────────────────────────────

data "aws_availability_zones" "available" {
  state = "available"
}

# ── Networking ─────────────────────────────────────────────────────────────────

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = { Name = "soc-dashboard-vpc" }
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]
  tags = { Name = "soc-private-${count.index + 1}" }
}

# ── Security Groups ────────────────────────────────────────────────────────────

resource "aws_security_group" "app_runner" {
  name        = "soc-app-runner-sg"
  description = "App Runner VPC egress"
  vpc_id      = aws_vpc.main.id
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "rds" {
  name        = "soc-rds-sg"
  description = "RDS — allow PostgreSQL from App Runner"
  vpc_id      = aws_vpc.main.id
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app_runner.id]
  }
}

resource "aws_security_group" "redis" {
  name        = "soc-redis-sg"
  description = "ElastiCache — allow Redis from App Runner"
  vpc_id      = aws_vpc.main.id
  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.app_runner.id]
  }
}

# ── RDS PostgreSQL ─────────────────────────────────────────────────────────────

resource "aws_db_subnet_group" "main" {
  name       = "soc-dashboard-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_instance" "main" {
  identifier             = "soc-dashboard-db"
  engine                 = "postgres"
  engine_version         = "16.3"
  instance_class         = "db.t3.micro"
  allocated_storage      = 20
  storage_type           = "gp2"
  storage_encrypted      = true
  db_name                = "soc_dashboard"
  username               = "soc"
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  multi_az               = false
  publicly_accessible    = false
  backup_retention_period = 7
  skip_final_snapshot    = true
  deletion_protection    = false
}

# ── ElastiCache Redis ──────────────────────────────────────────────────────────

resource "aws_elasticache_subnet_group" "main" {
  name       = "soc-dashboard-redis-subnet-group"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_elasticache_cluster" "main" {
  cluster_id           = "soc-dashboard-redis"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis.id]
}

# ── ECR Repository ─────────────────────────────────────────────────────────────

resource "aws_ecr_repository" "backend" {
  name                 = "soc-backend"
  image_tag_mutability = "MUTABLE"

  # Stack deletion will fail if the repository contains images.
  # Empty it manually before running terraform destroy, or set lifecycle.prevent_destroy = true.
}

resource "aws_ecr_lifecycle_policy" "backend" {
  repository = aws_ecr_repository.backend.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 5 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}

# ── App Runner ─────────────────────────────────────────────────────────────────

resource "aws_apprunner_vpc_connector" "main" {
  vpc_connector_name = "soc-vpc-connector"
  subnets            = aws_subnet.private[*].id
  security_groups    = [aws_security_group.app_runner.id]
}

data "aws_iam_policy_document" "apprunner_access_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["build.apprunner.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "apprunner_access" {
  name               = "soc-apprunner-access-role"
  assume_role_policy = data.aws_iam_policy_document.apprunner_access_assume.json
  managed_policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
  ]
}

data "aws_iam_policy_document" "apprunner_instance_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["tasks.apprunner.amazonaws.com"]
    }
  }
}

# Intentionally has no attached policies for this demo.
# In production, attach at minimum CloudWatchLogsFullAccess for structured logging.
resource "aws_iam_role" "apprunner_instance" {
  name               = "soc-apprunner-instance-role"
  assume_role_policy = data.aws_iam_policy_document.apprunner_instance_assume.json
}

resource "aws_apprunner_service" "backend" {
  service_name = "soc-backend"

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_access.arn
    }
    auto_deployments_enabled = true
    image_repository {
      image_identifier      = var.ecr_image_uri
      image_repository_type = "ECR"
      image_configuration {
        port = "8000"
        # Production hardening: move secrets to AWS Secrets Manager and use
        # runtime_environment_secrets instead of runtime_environment_variables.
        runtime_environment_variables = {
          DATABASE_URL = "postgresql+asyncpg://soc:${var.db_password}@${aws_db_instance.main.address}:5432/soc_dashboard"
          REDIS_URL    = "redis://${aws_elasticache_cluster.main.cache_nodes[0].address}:6379/0"
          SECRET_KEY   = var.secret_key
          ENVIRONMENT  = "production"
          CORS_ORIGINS = "[\"https://main.${aws_amplify_app.frontend.default_domain}\"]"
        }
      }
    }
  }

  instance_configuration {
    cpu               = "256"
    memory            = "512"
    instance_role_arn = aws_iam_role.apprunner_instance.arn
  }

  network_configuration {
    egress_configuration {
      egress_type       = "VPC"
      vpc_connector_arn = aws_apprunner_vpc_connector.main.arn
    }
  }

  health_check_configuration {
    protocol = "HTTP"
    path     = "/api/health/"
  }
}

# ── Amplify Frontend ───────────────────────────────────────────────────────────

data "aws_iam_policy_document" "amplify_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["amplify.amazonaws.com"]
    }
  }
}

# AdministratorAccess-Amplify is broader than needed for pure hosting but is the
# narrowest AWS-managed policy available for Amplify.
resource "aws_iam_role" "amplify" {
  name               = "soc-amplify-role"
  assume_role_policy = data.aws_iam_policy_document.amplify_assume.json
  managed_policy_arns = [
    "arn:aws:iam::aws:policy/AdministratorAccess-Amplify"
  ]
}

resource "aws_amplify_app" "frontend" {
  name                 = "soc-dashboard"
  repository           = var.github_repo_url
  iam_service_role_arn = aws_iam_role.amplify.arn

  build_spec = <<-EOT
    version: 1
    applications:
      - appRoot: frontend
        frontend:
          phases:
            preBuild:
              commands: [npm ci]
            build:
              commands: [npm run build]
          artifacts:
            baseDirectory: .next
            files: ['**/*']
          cache:
            paths: ['node_modules/**/*']
  EOT

  environment_variables = {
    NEXT_PUBLIC_API_URL = "https://${aws_apprunner_service.backend.service_url}"
  }
}

resource "aws_amplify_branch" "main" {
  app_id            = aws_amplify_app.frontend.id
  branch_name       = "main"
  enable_auto_build = true
}
