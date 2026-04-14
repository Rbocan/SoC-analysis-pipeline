@description('Location for all resources')
param location string = resourceGroup().location

@description('Master password for PostgreSQL')
@secure()
param dbPassword string

@description('FastAPI JWT secret key (openssl rand -hex 32)')
@secure()
param secretKey string

@description('ACR image name, e.g. socdashboardacr.azurecr.io/soc-backend:latest')
param acrImageName string

@description('GitHub repository URL for Static Web Apps CI/CD')
param githubRepoUrl string

@description('GitHub branch to deploy')
param githubBranch string = 'main'

@description('GitHub personal access token for Static Web Apps')
@secure()
param githubToken string

// ── Variables ─────────────────────────────────────────────────────────────────

var acrName = 'socdashboardacr'
var containerAppEnvName = 'soc-container-env'
var containerAppName = 'soc-backend'
var postgresServerName = 'soc-dashboard-pg'
var redisName = 'soc-dashboard-redis'
var staticWebAppName = 'soc-dashboard-frontend'
var logWorkspaceName = 'soc-dashboard-logs'

// ── Log Analytics (required by Container Apps) ────────────────────────────────

resource logWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logWorkspaceName
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

// ── ACR ───────────────────────────────────────────────────────────────────────

// Production hardening: replace admin credentials with a user-assigned managed identity
// granted the AcrPull role on this registry to eliminate the stored static credential.
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: true }
}

// ── Container Apps Environment ────────────────────────────────────────────────

resource containerEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: containerAppEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logWorkspace.properties.customerId
        sharedKey: logWorkspace.listKeys().primarySharedKey
      }
    }
  }
}

// ── PostgreSQL Flexible Server ────────────────────────────────────────────────

resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-03-01-preview' = {
  name: postgresServerName
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    administratorLogin: 'soc'
    administratorLoginPassword: dbPassword
    version: '16'
    storage: { storageSizeGB: 32 }
    backup: { backupRetentionDays: 7, geoRedundantBackup: 'Disabled' }
    highAvailability: { mode: 'Disabled' }
  }
}

resource postgresDb 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-03-01-preview' = {
  parent: postgresServer
  name: 'soc_dashboard'
  properties: { charset: 'UTF8', collation: 'en_US.utf8' }
}

resource postgresFirewall 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-03-01-preview' = {
  parent: postgresServer
  name: 'allow-azure-services'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// ── Redis Cache ───────────────────────────────────────────────────────────────

resource redis 'Microsoft.Cache/redis@2023-08-01' = {
  name: redisName
  location: location
  properties: {
    sku: { name: 'Basic', family: 'C', capacity: 0 }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
  }
}

// ── Container App (Backend) ───────────────────────────────────────────────────

var dbUrl = 'postgresql+asyncpg://soc:${dbPassword}@${postgresServer.properties.fullyQualifiedDomainName}:5432/soc_dashboard?sslmode=require'
var redisUrl = 'rediss://:${redis.listKeys().primaryKey}@${redis.properties.hostName}:6380/0'

resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: containerAppName
  location: location
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
      }
      registries: [{
        server: acr.properties.loginServer
        username: acr.name
        passwordSecretRef: 'acr-password'
      }]
      secrets: [
        { name: 'acr-password', value: acr.listCredentials().passwords[0].value }
        { name: 'db-url', value: dbUrl }
        { name: 'redis-url', value: redisUrl }
        { name: 'secret-key', value: secretKey }
      ]
    }
    template: {
      containers: [{
        name: 'soc-backend'
        image: acrImageName
        resources: { cpu: json('0.25'), memory: '0.5Gi' }
        env: [
          { name: 'DATABASE_URL', secretRef: 'db-url' }
          { name: 'REDIS_URL', secretRef: 'redis-url' }
          { name: 'SECRET_KEY', secretRef: 'secret-key' }
          { name: 'ENVIRONMENT', value: 'production' }
          // Note: staticWebApp.properties.defaultHostname is populated only after the first
          // GitHub Actions build completes. On the initial deployment this may be empty.
          // Re-run the deployment or update this secret manually after the SWA hostname is confirmed.
          { name: 'CORS_ORIGINS', value: '[\"https://${staticWebApp.properties.defaultHostname}\"]' }
        ]
      }]
      scale: { minReplicas: 0, maxReplicas: 2 }
    }
  }
}

// ── Static Web App (Frontend) ─────────────────────────────────────────────────

resource staticWebApp 'Microsoft.Web/staticSites@2022-09-01' = {
  name: staticWebAppName
  location: 'eastus2'  // Static Web Apps has limited region availability
  sku: { name: 'Free', tier: 'Free' }
  properties: {
    repositoryUrl: githubRepoUrl
    branch: githubBranch
    repositoryToken: githubToken
    buildProperties: {
      appLocation: 'frontend'
      outputLocation: '.next'
    }
  }
}

resource staticWebAppSettings 'Microsoft.Web/staticSites/config@2022-09-01' = {
  parent: staticWebApp
  name: 'appsettings'
  properties: {
    NEXT_PUBLIC_API_URL: 'https://${containerApp.properties.configuration.ingress.fqdn}'
  }
}

// ── Outputs ───────────────────────────────────────────────────────────────────

output backendUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
output frontendUrl string = 'https://${staticWebApp.properties.defaultHostname}'
output acrLoginServer string = acr.properties.loginServer
output postgresHost string = postgresServer.properties.fullyQualifiedDomainName
