# Getting Started with AI Agents Using Existing Azure Resources

A web-based chat application with an AI agent that uses your existing Azure OpenAI, Cosmos DB, and Blob Storage resources.

<div style="text-align:center;">

[**SOLUTION OVERVIEW**](#solution-overview) \| [**GETTING STARTED**](#getting-started) \| [**LOCAL DEVELOPMENT**](#local-development) \| [**OTHER FEATURES**](#other-features) \| [**RESOURCE CLEAN-UP**](#resource-clean-up) \| [**GUIDANCE**](#guidance) \| [**TROUBLESHOOTING**](./docs/troubleshooting.md)

</div>

## Solution Overview

This solution deploys a web-based chat application with an AI agent running in Azure Container Apps that uses your existing Azure resources.

The agent uses direct Azure OpenAI integration for chat completion, Azure Blob Storage for file uploads and knowledge base, and Azure Cosmos DB for conversation history and metadata storage. The solution also includes built-in monitoring capabilities with Azure Application Insights.

This solution only provisions Azure Container Apps and Container Registry - you bring your own Azure OpenAI, Cosmos DB, and Blob Storage resources.

Instructions are provided for deployment through GitHub Codespaces, VS Code Dev Containers, and your local development environment.

### Solution Architecture

The app code runs in Azure Container Apps to process user input and generate responses. It integrates directly with your existing Azure resources:

- **Azure OpenAI** - For chat completions and embeddings
- **Azure Cosmos DB** - For conversation history and file metadata
- **Azure Blob Storage** - For file uploads and knowledge base
- **Azure Container Apps** - For hosting the application
- **Azure Application Insights** - For monitoring and tracing (optional)

### Key Features

- **Knowledge Retrieval**<br/>
The AI agent uses RAG (Retrieval-Augmented Generation) with embeddings stored in Cosmos DB to retrieve knowledge from uploaded files.

- **Direct Azure OpenAI Integration**<br/>
Uses the official Azure OpenAI Python SDK for chat completions and embeddings, supporting any Azure OpenAI deployment.

- **Built-in Monitoring and Tracing**<br/>
Optional integration with Azure Monitor and Application Insights for tracing and logging.

- **Flexible Deployment Options**<br/>
The solution supports deployment through GitHub Codespaces, VS Code Dev Containers, or local environments.

- **Simple Configuration**<br/>
Uses environment variables to connect to your existing Azure resources - no complex setup required.

- **File Upload Support**<br/>
Upload documents that are automatically processed and indexed for knowledge retrieval during conversations.

<br/>

Here is a screenshot showing the chatting web application with requests and responses between the system and the user:

![Screenshot of chatting web application showing requests and responses between agent and the user.](docs/images/webapp_screenshot.png)

## Getting Started

### Prerequisites

Before deploying this solution, you need to have the following Azure resources already provisioned:

1. **Azure OpenAI Service** with a deployed model (e.g., GPT-4, GPT-4o-mini)
2. **Azure Cosmos DB** account
3. **Azure Blob Storage** account

### Quick Start

| [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Azure-Samples/get-started-with-ai-agents) | [![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/Azure-Samples/get-started-with-ai-agents) |
|---|---|

1. **Set up environment variables** - Copy `.env.template` to `.env` and fill in your Azure resource details:
   ```bash
   cp .env.template .env
   # Edit .env with your Azure resource information
   ```

2. **Deploy the application**:
   ```bash
   azd up
   ```

3. **Follow the prompts** to select your Azure subscription and region for Container Apps deployment

4. **Wait for deployment** to complete (2-5 minutes) - you'll get a web app URL when finished

### Environment Variables Setup

The `.env.template` file contains all required environment variables. Here's what you need to configure:

```bash
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Azure Blob Storage Configuration  
AZURE_STORAGE_ACCOUNT_NAME=yourstorageaccount
AZURE_STORAGE_ACCOUNT_KEY=your-storage-key
AZURE_STORAGE_CONTAINER_NAME=knowledge-base

# Azure Cosmos DB Configuration
AZURE_COSMOSDB_ENDPOINT=https://your-cosmosdb.documents.azure.com:443/
AZURE_COSMOSDB_KEY=your-cosmosdb-key
AZURE_COSMOSDB_DATABASE_NAME=ai-agent-db
AZURE_COSMOSDB_CONTAINER_NAME=conversations
```

For detailed deployment options and troubleshooting, see the [full deployment guide](./docs/deployment.md).
**After deployment, try uploading documents and asking questions to test your agent.**

## Local Development

For developers who want to run the application locally or customize the agent:

- **[Local Development Guide](./docs/local_development.md)** - Set up a local development environment, customize the frontend (starting with AgentPreview.tsx), modify agent instructions and tools, and use evaluation to improve your code.

This guide covers:
- Environment setup and prerequisites
- Running the development server locally
- Frontend customization and backend communication
- Agent instructions and tools modification
- File management and agent recreation
- Using agent evaluation for code improvement

## Other Features
Once you have the agents and the web app working, you are encouraged to try one of the following:

- **[Tracing and Monitoring](./docs/other_features.md#tracing-and-monitoring)** - View console logs in Azure portal and App Insights tracing in Azure AI Foundry for debugging and performance monitoring.

- **[Agent Evaluation](./docs/other_features.md#agent-evaluation)** - Evaluate your agent's performance and quality using built-in evaluators for local development, continuous monitoring, and CI/CD integration.

- **[AI Red Teaming Agent](./docs/other_features.md#ai-red-teaming-agent)** - Run automated security and safety scans on your agent solution to check your risk posture before production deployment.

## Resource Clean-up

To prevent incurring unnecessary charges, it's important to clean up your Azure resources after completing your work with the application.

- **When to Clean Up:**
  - After you have finished testing or demonstrating the application.
  - If the application is no longer needed or you have transitioned to a different project or environment.
  - When you have completed development and are ready to decommission the application.

- **Deleting Resources:**
  To delete all associated resources and shut down the application, execute the following command:
  
    ```bash
    azd down
    ```

    Please note that this process may take up to 20 minutes to complete.

⚠️ Alternatively, you can delete the resource group directly from the Azure Portal to clean up resources.

## Guidance

### Costs

Pricing varies per region and usage, so it isn't possible to predict exact costs for your usage.
The majority of the Azure resources used in this infrastructure are on usage-based pricing tiers.

You can try the [Azure pricing calculator](https://azure.microsoft.com/pricing/calculator) for the resources:

- **Azure AI Foundry**: Free tier. [Pricing](https://azure.microsoft.com/pricing/details/ai-studio/)  
- **Azure Storage Account**: Standard tier, LRS. Pricing is based on storage and operations. [Pricing](https://azure.microsoft.com/pricing/details/storage/blobs/)  
- **Azure AI Services**: S0 tier, defaults to gpt-4o-mini. Pricing is based on token count. [Pricing](https://azure.microsoft.com/pricing/details/cognitive-services/)  
- **Azure Container App**: Consumption tier with 0.5 CPU, 1GiB memory/storage. Pricing is based on resource allocation, and each month allows for a certain amount of free usage. [Pricing](https://azure.microsoft.com/pricing/details/container-apps/)  
- **Log analytics**: Pay-as-you-go tier. Costs based on data ingested. [Pricing](https://azure.microsoft.com/pricing/details/monitor/)  
- **Agent Evaluations**: Incurs the cost of your provided model deployment used for local evaluations.  
- **AI Red Teaming Agent**: Leverages Azure AI Risk and Safety Evaluations to assess attack success from the automated AI red teaming scan. Users are billed based on the consumption of Risk and Safety Evaluations as listed in [our Azure pricing page](https://azure.microsoft.com/pricing/details/ai-foundry/). Click on the tab labeled “Complete AI Toolchain” to view the pricing details.

⚠️ To avoid unnecessary costs, remember to take down your app if it's no longer in use,
either by deleting the resource group in the Portal or running `azd down`.

### Security guidelines

This template also uses [Managed Identity](https://learn.microsoft.com/entra/identity/managed-identities-azure-resources/overview) for local development and deployment.

To ensure continued best practices in your own repository, we recommend that anyone creating solutions based on our templates ensure that the [Github secret scanning](https://docs.github.com/code-security/secret-scanning/about-secret-scanning) setting is enabled.

You may want to consider additional security measures, such as:

- Enabling Microsoft Defender for Cloud to [secure your Azure resources](https://learn.microsoft.com/azure/defender-for-cloud/).
- Protecting the Azure Container Apps instance with a [firewall](https://learn.microsoft.com/azure/container-apps/waf-app-gateway) and/or [Virtual Network](https://learn.microsoft.com/azure/container-apps/networking?tabs=workload-profiles-env%2Cazure-cli).

> **Important Security Notice** <br/>
This template, the application code and configuration it contains, has been built to showcase Microsoft Azure specific services and tools. We strongly advise our customers not to make this code part of their production environments without implementing or enabling additional security features.  <br/><br/>
For a more comprehensive list of best practices and security recommendations for Intelligent Applications, [visit our official documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/).

### Resources

This template only provisions Azure Container Apps and uses your existing resources:

| Resource | Description | Required/Optional |
|----------|-------------|-------------------|
| [Azure OpenAI Service](https://learn.microsoft.com/azure/ai-services/openai/) | **Required (Existing)** - Your existing Azure OpenAI service with deployed models for chat completions and embeddings |
| [Azure Cosmos DB](https://learn.microsoft.com/azure/cosmos-db/) | **Required (Existing)** - Your existing Cosmos DB account for storing conversation history and file metadata |
| [Azure Blob Storage](https://learn.microsoft.com/azure/storage/blobs/) | **Required (Existing)** - Your existing storage account for file uploads and knowledge base |
| [Azure Container Apps](https://learn.microsoft.com/azure/container-apps/) | **Provisioned** - Hosts and scales the web application with serverless containers |
| [Azure Container Registry](https://learn.microsoft.com/azure/container-registry/) | **Provisioned** - Stores and manages container images for deployment |
| [Application Insights](https://learn.microsoft.com/azure/azure-monitor/app/app-insights-overview) | **Optional (Provisioned)** - Provides application performance monitoring and logging |
| [Log Analytics Workspace](https://learn.microsoft.com/azure/azure-monitor/logs/log-analytics-workspace-overview) | **Optional (Provisioned)** - Collects and analyzes telemetry data for monitoring |

## Troubleshooting

For solutions to common deployment, container app, and agent issues, see the [Troubleshooting Guide](./docs/troubleshooting.md).


## Disclaimers

To the extent that the Software includes components or code used in or derived from Microsoft products or services, including without limitation Microsoft Azure Services (collectively, “Microsoft Products and Services”), you must also comply with the Product Terms applicable to such Microsoft Products and Services. You acknowledge and agree that the license governing the Software does not grant you a license or other right to use Microsoft Products and Services. Nothing in the license or this ReadMe file will serve to supersede, amend, terminate or modify any terms in the Product Terms for any Microsoft Products and Services.

You must also comply with all domestic and international export laws and regulations that apply to the Software, which include restrictions on destinations, end users, and end use. For further information on export restrictions, visit <https://aka.ms/exporting>.

You acknowledge that the Software and Microsoft Products and Services (1) are not designed, intended or made available as a medical device(s), and (2) are not designed or intended to be a substitute for professional medical advice, diagnosis, treatment, or judgment and should not be used to replace or as a substitute for professional medical advice, diagnosis, treatment, or judgment. Customer is solely responsible for displaying and/or obtaining appropriate consents, warnings, disclaimers, and acknowledgements to end users of Customer’s implementation of the Online Services.

You acknowledge the Software is not subject to SOC 1 and SOC 2 compliance audits. No Microsoft technology, nor any of its component technologies, including the Software, is intended or made available as a substitute for the professional advice, opinion, or judgement of a certified financial services professional. Do not use the Software to replace, substitute, or provide professional financial advice or judgment.  

BY ACCESSING OR USING THE SOFTWARE, YOU ACKNOWLEDGE THAT THE SOFTWARE IS NOT DESIGNED OR INTENDED TO SUPPORT ANY USE IN WHICH A SERVICE INTERRUPTION, DEFECT, ERROR, OR OTHER FAILURE OF THE SOFTWARE COULD RESULT IN THE DEATH OR SERIOUS BODILY INJURY OF ANY PERSON OR IN PHYSICAL OR ENVIRONMENTAL DAMAGE (COLLECTIVELY, “HIGH-RISK USE”), AND THAT YOU WILL ENSURE THAT, IN THE EVENT OF ANY INTERRUPTION, DEFECT, ERROR, OR OTHER FAILURE OF THE SOFTWARE, THE SAFETY OF PEOPLE, PROPERTY, AND THE ENVIRONMENT ARE NOT REDUCED BELOW A LEVEL THAT IS REASONABLY, APPROPRIATE, AND LEGAL, WHETHER IN GENERAL OR IN A SPECIFIC INDUSTRY. BY ACCESSING THE SOFTWARE, YOU FURTHER ACKNOWLEDGE THAT YOUR HIGH-RISK USE OF THE SOFTWARE IS AT YOUR OWN RISK.
