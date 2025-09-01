targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the the environment which is used to generate a short unique hash used in all resources.')
param environmentName string

@description('Location for all resources')
param location string

@description('Id of the user or app to assign application roles')
param principalId string = ''

@description('The Azure resource group where new resources will be deployed')
param resourceGroupName string = ''

@description('The Azure Container Registry resource name. If omitted will be generated')
param containerRegistryName string = ''

@description('The log analytics workspace name. If omitted will be generated')
param logAnalyticsWorkspaceName string = ''

@description('The application insights resource name. If omitted will be generated')
param applicationInsightsName string = ''

@description('Use Application Insights for monitoring')
param useApplicationInsights bool = true

@description('Do we want to use the Azure Monitor tracing')
param enableAzureMonitorTracing bool = false

@description('Do we want to use the Azure Monitor tracing for GenAI content recording')
param azureTracingGenAIContentRecordingEnabled bool = false

param templateValidationMode bool = false

@description('Random seed to be used during generation of new resources suffixes.')
param seed string = newGuid()

var runnerPrincipalType = templateValidationMode? 'ServicePrincipal' : 'User'

var abbrs = loadJsonContent('./abbreviations.json')

var resourceToken = templateValidationMode? toLower(uniqueString(subscription().id, environmentName, location, seed)) :  toLower(uniqueString(subscription().id, environmentName, location))

var tags = { 'azd-env-name': environmentName }

// Organize resources in a resource group
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}${environmentName}'
  location: location
  tags: tags
}

var logAnalyticsWorkspaceResolvedName = !useApplicationInsights
  ? ''
  : !empty(logAnalyticsWorkspaceName)
      ? logAnalyticsWorkspaceName
      : '${abbrs.operationalInsightsWorkspaces}${resourceToken}'

// Log Analytics for monitoring
module logAnalytics 'core/monitor/loganalytics.bicep' = if (useApplicationInsights) {
  name: 'logAnalytics'
  scope: rg
  params: {
    location: location
    tags: tags
    name: logAnalyticsWorkspaceResolvedName
  }
}

// Application Insights for monitoring
module monitoring 'core/monitor/monitoring.bicep' = if (useApplicationInsights) {
  name: 'monitoring'
  scope: rg
  params: {
    location: location
    tags: tags
    logAnalyticsName: logAnalyticsWorkspaceResolvedName
    applicationInsightsName: !empty(applicationInsightsName) ? applicationInsightsName : '${abbrs.insightsComponents}${resourceToken}'
    enableDashboard: false
  }
  dependsOn: [
    logAnalytics
  ]
}

// Container registry for hosting images
module cr 'core/host/container-registry.bicep' = {
  name: 'container-registry'
  scope: rg
  params: {
    location: location
    tags: tags
    name: !empty(containerRegistryName) ? containerRegistryName : '${abbrs.containerRegistryRegistries}${resourceToken}'
  }
}

// Container Apps host for the API and frontend
module api 'core/host/container-apps.bicep' = {
  name: 'container-apps'
  scope: rg
  params: {
    name: 'app'
    location: location
    tags: tags
    applicationInsightsName: useApplicationInsights ? monitoring.outputs.applicationInsightsName : ''
    containerRegistryName: cr.outputs.name
    logAnalyticsWorkspaceName: useApplicationInsights ? logAnalytics.outputs.name : ''
    identityType: 'SystemAssigned'
    containerName: 'ai-agent-app'
    exists: false
    environmentVariables: [
      {
        name: 'AZURE_SUBSCRIPTION_ID'
        value: subscription().subscriptionId
      }
      {
        name: 'AZURE_RESOURCE_GROUP'
        value: rg.name
      }
      {
        name: 'AZURE_LOCATION'
        value: location
      }
      {
        name: 'ENABLE_AZURE_MONITOR_TRACING'
        value: string(enableAzureMonitorTracing)
      }
      {
        name: 'AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED'
        value: string(azureTracingGenAIContentRecordingEnabled)
      }
      {
        name: 'RUNNING_IN_PRODUCTION'
        value: 'true'
      }
    ]
  }
}

// Application Insights access for Container Apps
module appInsightsAccess 'core/security/appinsights-access.bicep' = if (useApplicationInsights) {
  name: 'appinsights-access'
  scope: rg
  params: {
    principalType: 'ServicePrincipal'
    appInsightsName: monitoring.outputs.applicationInsightsName
    principalId: api.outputs.SERVICE_API_IDENTITY_PRINCIPAL_ID
  }
  dependsOn: [
    monitoring
    api
  ]
}

// Outputs
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = cr.outputs.loginServer
output AZURE_CONTAINER_REGISTRY_NAME string = cr.outputs.name
output AZURE_CONTAINER_REGISTRY_RESOURCE_GROUP string = rg.name

output AZURE_RESOURCE_GROUP string = rg.name
output AZURE_LOCATION string = location

output SERVICE_API_IDENTITY_PRINCIPAL_ID string = api.outputs.SERVICE_API_IDENTITY_PRINCIPAL_ID
output SERVICE_API_NAME string = api.outputs.SERVICE_API_NAME
output SERVICE_API_URI string = api.outputs.SERVICE_API_URI

output AZURE_LOG_ANALYTICS_WORKSPACE_NAME string = useApplicationInsights ? logAnalytics.outputs.name : ''
output AZURE_APPLICATION_INSIGHTS_NAME string = useApplicationInsights ? monitoring.outputs.applicationInsightsName : ''
  scope: existingProjectRG
  params: {
    principalType: 'ServicePrincipal'
    principalId: api.outputs.SERVICE_API_IDENTITY_PRINCIPAL_ID
    roleDefinitionId: '64702f94-c441-49e6-a78b-ef80e0188fee' 
  }
}

//Container apps host and api
// Container apps host (including container registry)
module containerApps 'core/host/container-apps.bicep' = {
  name: 'container-apps'
  scope: rg
  params: {
    name: 'app'
    location: location
    containerRegistryName: '${abbrs.containerRegistryRegistries}${resourceToken}'
    tags: tags
    containerAppsEnvironmentName: 'containerapps-env-${resourceToken}'
    logAnalyticsWorkspaceName: empty(azureExistingAIProjectResourceId)
      ? ai!.outputs.logAnalyticsWorkspaceName
      : logAnalytics!.outputs.name
  }
}

// API app
module api 'api.bicep' = {
  name: 'api'
  scope: rg
  params: {
    name: 'ca-api-${resourceToken}'
    location: location
    tags: tags
    identityName: '${abbrs.managedIdentityUserAssignedIdentities}api-${resourceToken}'
    containerAppsEnvironmentName: containerApps.outputs.environmentName
    azureExistingAIProjectResourceId: projectResourceId
    containerRegistryName: containerApps.outputs.registryName
    agentDeploymentName: agentDeploymentName
    searchConnectionName: searchConnectionName
    aiSearchIndexName: aiSearchIndexName
    searchServiceEndpoint: searchServiceEndpoint
    embeddingDeploymentName: embeddingDeploymentName
    embeddingDeploymentDimensions: embeddingDeploymentDimensions
    agentName: agentName
    agentID: agentID
    enableAzureMonitorTracing: enableAzureMonitorTracing
    azureTracingGenAIContentRecordingEnabled: azureTracingGenAIContentRecordingEnabled
    projectEndpoint: projectEndpoint
  }
}



module userRoleAzureAIDeveloper 'core/security/role.bicep' = {
  name: 'user-role-azureai-developer'
  scope: rg
  params: {
    principalType: runnerPrincipalType
    principalId: principalId
    roleDefinitionId: '64702f94-c441-49e6-a78b-ef80e0188fee'
  }
}

module userCognitiveServicesUser  'core/security/role.bicep' = if (empty(azureExistingAIProjectResourceId)) {
  name: 'user-role-cognitive-services-user'
  scope: rg
  params: {
    principalType: runnerPrincipalType
    principalId: principalId
    roleDefinitionId: 'a97b65f3-24c7-4388-baec-2e87135dc908'
  }
}

module userAzureAIUser  'core/security/role.bicep' = if (empty(azureExistingAIProjectResourceId)) {
  name: 'user-role-azure-ai-user'
  scope: rg
  params: {
    principalType: runnerPrincipalType
    principalId: principalId
    roleDefinitionId: '53ca6127-db72-4b80-b1b0-d745d6d5456d'
  }
}

module backendCognitiveServicesUser  'core/security/role.bicep' = if (empty(azureExistingAIProjectResourceId)) {
  name: 'backend-role-cognitive-services-user'
  scope: rg
  params: {
    principalType: 'ServicePrincipal'
    principalId: api.outputs.SERVICE_API_IDENTITY_PRINCIPAL_ID
    roleDefinitionId: 'a97b65f3-24c7-4388-baec-2e87135dc908'
  }
}

module backendCognitiveServicesUser2  'core/security/role.bicep' = if (!empty(azureExistingAIProjectResourceId)) {
  name: 'backend-role-cognitive-services-user2'
  scope: existingProjectRG
  params: {
    principalType: 'ServicePrincipal'
    principalId: api.outputs.SERVICE_API_IDENTITY_PRINCIPAL_ID
    roleDefinitionId: 'a97b65f3-24c7-4388-baec-2e87135dc908'
  }
}


module backendRoleSearchIndexDataContributorRG 'core/security/role.bicep' = if (useSearchService) {
  name: 'backend-role-azure-index-data-contributor-rg'
  scope: rg
  params: {
    principalType: 'ServicePrincipal'
    principalId: api.outputs.SERVICE_API_IDENTITY_PRINCIPAL_ID
    roleDefinitionId: '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
  }
}

module backendRoleSearchIndexDataReaderRG 'core/security/role.bicep' = if (useSearchService) {
  name: 'backend-role-azure-index-data-reader-rg'
  scope: rg
  params: {
    principalType: 'ServicePrincipal'
    principalId: api.outputs.SERVICE_API_IDENTITY_PRINCIPAL_ID
    roleDefinitionId: '1407120a-92aa-4202-b7e9-c0e197c71c8f'
  }
}

module backendRoleSearchServiceContributorRG 'core/security/role.bicep' = if (useSearchService) {
  name: 'backend-role-azure-search-service-contributor-rg'
  scope: rg
  params: {
    principalType: 'ServicePrincipal'
    principalId: api.outputs.SERVICE_API_IDENTITY_PRINCIPAL_ID
    roleDefinitionId: '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
  }
}

module userRoleSearchIndexDataContributorRG 'core/security/role.bicep' = if (useSearchService) {
  name: 'user-role-azure-index-data-contributor-rg'
  scope: rg
  params: {
    principalType: runnerPrincipalType
    principalId: principalId
    roleDefinitionId: '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
  }
}

module userRoleSearchIndexDataReaderRG 'core/security/role.bicep' = if (useSearchService) {
  name: 'user-role-azure-index-data-reader-rg'
  scope: rg
  params: {
    principalType: runnerPrincipalType
    principalId: principalId
    roleDefinitionId: '1407120a-92aa-4202-b7e9-c0e197c71c8f'
  }
}

module userRoleSearchServiceContributorRG 'core/security/role.bicep' = if (useSearchService) {
  name: 'user-role-azure-search-service-contributor-rg'
  scope: rg
  params: {
    principalType: runnerPrincipalType
    principalId: principalId
    roleDefinitionId: '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
  }
}

module backendRoleAzureAIDeveloperRG 'core/security/role.bicep' = {
  name: 'backend-role-azureai-developer-rg'
  scope: rg
  params: {
    principalType: 'ServicePrincipal'
    principalId: api.outputs.SERVICE_API_IDENTITY_PRINCIPAL_ID
    roleDefinitionId: '64702f94-c441-49e6-a78b-ef80e0188fee'
  }
}

output AZURE_RESOURCE_GROUP string = rg.name

// Outputs required for local development server
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_EXISTING_AIPROJECT_RESOURCE_ID string = projectResourceId
output AZURE_AI_AGENT_DEPLOYMENT_NAME string = agentDeploymentName
output AZURE_AI_SEARCH_CONNECTION_NAME string = searchConnectionName
output AZURE_AI_EMBED_DEPLOYMENT_NAME string = embeddingDeploymentName
output AZURE_AI_SEARCH_INDEX_NAME string = aiSearchIndexName
output AZURE_AI_SEARCH_ENDPOINT string = searchServiceEndpoint
output AZURE_AI_EMBED_DIMENSIONS string = embeddingDeploymentDimensions
output AZURE_AI_AGENT_NAME string = agentName
output AZURE_EXISTING_AGENT_ID string = agentID
output AZURE_EXISTING_AIPROJECT_ENDPOINT string = projectEndpoint
output ENABLE_AZURE_MONITOR_TRACING bool = enableAzureMonitorTracing
output AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED bool = azureTracingGenAIContentRecordingEnabled

// Outputs required by azd for ACA
output AZURE_CONTAINER_ENVIRONMENT_NAME string = containerApps.outputs.environmentName
output SERVICE_API_IDENTITY_PRINCIPAL_ID string = api.outputs.SERVICE_API_IDENTITY_PRINCIPAL_ID
output SERVICE_API_NAME string = api.outputs.SERVICE_API_NAME
output SERVICE_API_URI string = api.outputs.SERVICE_API_URI
output SERVICE_API_ENDPOINTS array = ['${api.outputs.SERVICE_API_URI}']
output SEARCH_CONNECTION_ID string = ''
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerApps.outputs.registryLoginServer
