#!/bin/bash

# Define the .env file path
ENV_FILE_PATH="src/.env"

# Clear the contents of the .env file
> $ENV_FILE_PATH

echo "AZURE_SUBSCRIPTION_ID=$(azd env get-value AZURE_SUBSCRIPTION_ID 2>/dev/null)" >> $ENV_FILE_PATH
echo "AZURE_RESOURCE_GROUP=$(azd env get-value AZURE_RESOURCE_GROUP 2>/dev/null)" >> $ENV_FILE_PATH
echo "AZURE_LOCATION=$(azd env get-value AZURE_LOCATION 2>/dev/null)" >> $ENV_FILE_PATH
echo "AZURE_CONTAINER_REGISTRY_NAME=$(azd env get-value AZURE_CONTAINER_REGISTRY_NAME 2>/dev/null)" >> $ENV_FILE_PATH
echo "AZURE_APPLICATION_INSIGHTS_NAME=$(azd env get-value AZURE_APPLICATION_INSIGHTS_NAME 2>/dev/null)" >> $ENV_FILE_PATH
echo "AZURE_LOG_ANALYTICS_WORKSPACE_NAME=$(azd env get-value AZURE_LOG_ANALYTICS_WORKSPACE_NAME 2>/dev/null)" >> $ENV_FILE_PATH
echo "ENABLE_AZURE_MONITOR_TRACING=$(azd env get-value ENABLE_AZURE_MONITOR_TRACING 2>/dev/null)" >> $ENV_FILE_PATH
echo "AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED=$(azd env get-value AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED 2>/dev/null)" >> $ENV_FILE_PATH

exit 0