# RAG Chat App with Azure OpenAI and Azure AI Search

Welcome to this tutorial where we will take you step by step in deploying a Retrieval Augmented Generation (RAG) chat application that integrates Azure OpenAI Service and Azure AI Search to create a ChatGPT-like experience over indexed document data. The application enables you to interact with an AI-powered chatbot that retrieves relevant information from a document corpus before generating responses, improving accuracy and contextual relevance.

The solution is built in Python and leverages Azure-managed services for seamless deployment, scalability, and security. The infrastructure is provisioned with resources such as Azure Cognitive Services (OpenAI & Document Intelligence), Azure AI Search, Azure Storage, Log Analytics, Container Apps, and Identity Management.

This guide provides step-by-step instructions for setting up the required Azure services and configuring environment variables to deploy the chat application.

## Setup Environment Variables

The following commands configure environment variables for deploying resources in Azure. It retrieves the signed-in user's Azure AD principal ID, defines the Azure environment name, and sets up resource tagging information. Additionally, it generates a unique identifier for resource differentiation and specifies the Azure region and resource group name.

````bash
az account set --subscription $SUBSCRIPTION
export CLIENT_PRINCIPALID=$(az ad signed-in-user show --query "id" -o tsv)
export TENANT_ID=$(az account show --subscription $SUBSCRIPTION --query tenantId -o tsv) 
export LOGIN_ENDPOINT=$(az cloud show --query endpoints.activeDirectory -o tsv)
export RESOURCE_TOKEN=$(openssl rand -hex 3)
export LOCATION=$REGION
export RESOURCE_GROUP="myrg$RESOURCE_TOKEN"
export EXECDOC_ENV="myenv$RESOURCE_TOKEN"
export TAGS="execdoc-env-name=$EXECDOC_ENV"
````

## Create a resource group

The following command creats a resource group and stores required results.

````bash
az group create --name $RESOURCE_GROUP --location $LOCATION | tee temp.json
RG_OUTPUT=$(cat temp.json)
rm temp.json
export RESOURCE_GROUP_ID=$(jq -r '.id' <<< "$RG_OUTPUT")
````

## Set Default Configuration

The following command sets default values for the Azure CLI, specifying the resource group, region, and subscription ID. This ensures that subsequent az CLI commands use these defaults without requiring explicit parameters.

````bash
az configure --defaults group=$RESOURCE_GROUP location=$LOCATION subscription=$SUBSCRIPTION
az config set defaults.tenant=$TENANT_ID
az config set extension.dynamic_install_allow_preview=true
az config set extension.use_dynamic_install=yes_without_prompt
# to be changed 
````

## Create Log Analytics Workspace

The following command creates an Azure Log Analytics workspace. It uses the PerGB2018 pricing tier, sets a retention period of 30 days, and enables public network access for ingestion and query access. The command also applies specified tags and outputs the result in JSON format.

````bash
LOG_ANALYTICS_NAME="log-$RESOURCE_TOKEN"
PUBLIC_NETWORK_ACCESS="Enabled"
az monitor log-analytics workspace create \
  --name $LOG_ANALYTICS_NAME \
  --sku PerGB2018 \
  --retention-time 30 \
  --ingestion-access $PUBLIC_NETWORK_ACCESS \
  --query-access $PUBLIC_NETWORK_ACCESS \
  --tags $TAGS --output json | tee temp.json
LOG_ANALYTICS_OUTPUT=$(cat temp.json)
rm temp.json
export LOGANALYTICSWORKSPACEID=$(jq -r '.id' <<< "$LOG_ANALYTICS_OUTPUT")
export LOGANALYTICSWORKSPACECUSTOMERID=$(jq -r '.customerId' <<< "$LOG_ANALYTICS_OUTPUT")
export LOGANALYTICSWORKSPACENAME=$(jq -r '.name' <<< "$LOG_ANALYTICS_OUTPUT")
````

## Create Azure Application Insights

The following commands install or upgrade the Application Insights extension for Azure CLI and create an Application Insights component. The component is linked to an existing Log Analytics workspace and configured with public network access for ingestion and query access.

````bash
az extension add --upgrade -n application-insights
APPLICATION_INSIGHTS_NAME="appi-${RESOURCE_TOKEN}"
az monitor app-insights component create \
  --app $APPLICATION_INSIGHTS_NAME \
  --workspace $LOGANALYTICSWORKSPACEID \
  --ingestion-access $PUBLIC_NETWORK_ACCESS \
  --query-access $PUBLIC_NETWORK_ACCESS \
  --tags $TAGS --output json | tee temp.json
APPLICATION_INSIGHTS_OUTPUT=$(cat temp.json) 
rm temp.json
export APPLICATIONINSIGHTSCONNECTIONSTRING=$(jq -r '.connectionString' <<< "$APPLICATION_INSIGHTS_OUTPUT")
export APPLICATIONINSIGHTSID=$(jq -r '.id' <<< "$APPLICATION_INSIGHTS_OUTPUT")
export APPLICATIONINSIGHTSINSTRUMENTATIONKEY=$(jq -r '.instrumentationKey' <<< "$APPLICATION_INSIGHTS_OUTPUT")
export APPLICATIONINSIGHTSNAME=$(jq -r '.name' <<< "$APPLICATION_INSIGHTS_OUTPUT")
````

## Application Insights Dashboard

````bash
sed "s|{{SUBSCRIPTION_ID}}|$SUBSCRIPTION|g; \
    s|{{RESOURCE_GROUP_NAME}}|$RESOURCE_GROUP|g; \
    s|{{APPLICATIONINSIGHTS_NAME}}|$APPLICATIONINSIGHTSNAME|g" \
    v10.json > updated_dashboard_properties.json

export APPLICATIONINSIGHTS_DASHBOARD_NAME="dash-$RESOURCE_TOKEN"
az portal dashboard create \
  --input-path ./updated_dashboard_properties.json \
  --name $APPLICATIONINSIGHTS_DASHBOARD_NAME \
  --tags $TAGS

export APPLICATIONINSIGHTS_DASHBOARD_NAME="dash-$RESOURCE_TOKEN"
az portal dashboard create \
  --input-path ./v9.json \
  --name $APPLICATIONINSIGHTS_DASHBOARD_NAME \
  --tags $TAGS
````

## Create Managed Identity

The following command creates a Managed Identity. This identity can be assigned permissions to access Azure resources securely without needing explicit credentials.

````bash
export ACA_IDENTITY_NAME="${EXECDOC_ENV}-aca-identity"
az identity create \
  --name $ACA_IDENTITY_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION --output json | tee temp.json
ACA_IDENTITY_OUTPUT=$(cat temp.json) 
rm temp.json
export ACA_IDENTITY_ID=$(jq -r '.id' <<< "$ACA_IDENTITY_OUTPUT")
export PRINCIPALID=$(jq -r '.principalId' <<< "$ACA_IDENTITY_OUTPUT")
export CLIENTID=$(jq -r '.clientId' <<< "$ACA_IDENTITY_OUTPUT")
````

## Create Acure Container App Environment (ACR)

The following commands install or upgrade the Container Apps extension for Azure CLI and create an Azure Container Apps Environment. The environment is linked to a Log Analytics workspace for monitoring and is configured with a system-assigned managed identity.

````bash
CONTAINERAPPSENVIRONMENTNAME="${EXECDOC_ENV}-aca-env"
LOGANALYTICSWORKSPACEKEY=$(az monitor log-analytics workspace get-shared-keys \
  --name "$LOGANALYTICSWORKSPACENAME" | jq -r '.primarySharedKey')
az extension add --name containerapp --upgrade
az containerapp env create \
  --name "${EXECDOC_ENV}-aca-env" \
  --logs-workspace-id $LOGANALYTICSWORKSPACECUSTOMERID \
  --logs-workspace-key $LOGANALYTICSWORKSPACEKEY \
  --mi-system-assigned \
  --tags $TAGS --output json | tee temp.json
CONTAINERAPP_ENV_OUTPUT=$(cat temp.json) 
rm temp.json
export CONTAINERAPPENVDEFAULTDOMAIN=$(jq -r '.properties.defaultDomain' <<< "$CONTAINERAPP_ENV_OUTPUT")
export CONTAINERAPPENVNAME=$(jq -r '.name' <<< "$CONTAINERAPP_ENV_OUTPUT")
export CONTAINERAPPENVID=$(jq -r '.id' <<< "$CONTAINERAPP_ENV_OUTPUT")
````

## Create Azure Container Registry (ACR)

The following command creates an Azure Container Registry (ACR) with the Standard SKU. The registry is used to store and manage container images for deployment in Azure.

````bash
az acr create \
  --name "${EXECDOC_ENV//-/}acr" \
  --sku Standard \
  --tags $TAGS --output json | tee temp.json
ACR_CREATE_OUTPUT=$(cat temp.json) 
rm temp.json
export ACRLOGINSERVER=$(jq -r '.loginServer' <<< "$ACR_CREATE_OUTPUT")
export ACRNAME=$(jq -r '.name' <<< "$ACR_CREATE_OUTPUT")
export ACRID=$(jq -r '.id' <<< "$ACR_CREATE_OUTPUT")
````

## (COULD BE OPTIONAL) Assign ACR Pull Role to Managed Identity

The following commands give the managed identity permission to pull container images from Azure Container Registry (ACR). A ACR Pull role is assigned to the managed identity, allowing it to access and use container images stored in ACR.

````bash
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
ACR_PULL_ROLE_ID="/subscriptions/$SUBSCRIPTION_ID/providers/Microsoft.Authorization/roleDefinitions/7f951dda-4ed3-4680-a7ca-43fe172d538d"
az role assignment create \
  --assignee-object-id $PRINCIPALID \
  --role $ACR_PULL_ROLE_ID \
  --scope $ACRID \
  --assignee-principal-type ServicePrincipal
````

## Deploy a Backend Azure Container App

The following commands create an Azure Container App for the backend service. The app is deployed in a specified Container Apps environment with a user-assigned managed identity for secure access to resources. It is configured with an external ingress on port 8000, allowing traffic from the internet. The container image is pulled from Azure Container Registry (ACR) using the identity, and the app runs with 1 CPU and 2GB memory, scaling automatically between 1 to 10 replicas based on demand.

````bash
ACAWEB_NAME="capps-backend-$RESOURCE_TOKEN"
export BACKEND_TAGS="exec-env-name=$EXECDOC_ENV exec-service-name=backend"
az containerapp create \
  --name $ACAWEB_NAME \
  --user-assigned $ACA_IDENTITY_ID --environment $CONTAINERAPPENVID \
  --workload-profile-name "Consumption" --revisions-mode single \
  --ingress external --target-port 8000 --transport auto \
  --registry-identity $ACA_IDENTITY_ID --registry-server $ACRLOGINSERVER \
  --image 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest' \
  --container-name 'main' \
  --cpu 1 --memory 2Gi \
  --min-replicas 1 --max-replicas 10 \
  --tags $BACKEND_TAGS --output json | tee temp.json
ACA_WEB_OUTPUT=$(cat temp.json) 
rm temp.json
export ACAWEBDEFAULTDOMAIN=$CONTAINERAPPENVDEFAULTDOMAIN
export IMAGENAME="mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
export ACAWEBNAME=$(jq -r '.name' <<< "$ACA_WEB_OUTPUT")
export ACAWEBID=$(jq -r '.id' <<< "$ACA_WEB_OUTPUT")
export ACAURI=$(jq -r '.properties.configuration.ingress.fqdn' <<< "$ACA_WEB_OUTPUT")
````

## Enable CORS for Azure Container App

The following command enables CORS (Cross-Origin Resource Sharing) for the specified Azure Container App. It allows requests from Microsoft Azure portals (https://portal.azure.com and https://ms.portal.azure.com), ensuring secure interaction with Azure-managed services while restricting unauthorized cross-origin requests.

````bash
export ALLOWED_ORIGINS="https://portal.azure.com;https://ms.portal.azure.com"
az containerapp ingress cors enable \
    --name $ACAWEBNAME \
    --allowed-origins $ALLOWED_ORIGINS
````

## Create an Azure OpenAI Cognitive Services Account

The following commands create an Azure Cognitive Services account for OpenAI. The account is set to the S0 pricing tier, and configured with a custom domain.

````bash
export OPENAI_NAME="cog-${RESOURCE_TOKEN}"
az cognitiveservices account create \
  --name $OPENAI_NAME \
  --kind OpenAI \
  --sku S0 \
  --custom-domain $OPENAI_NAME \
  --tags $TAGS --output json | tee temp.json
OPENAI_OUTPUT=$(cat temp.json)
rm temp.json
````

## Deploy OpenAI GPT-3.5 Turbo Model

The following commands deploy the GPT-3.5 Turbo model to the previously created Azure Cognitive Services account. The model is set to the OpenAI format with version 0125 and is deployed under the name chat. It uses the Standard SKU and is allocated a capacity of 30 to handle requests efficiently.

````bash
az cognitiveservices account deployment create \
  --name $OPENAI_NAME \
  --model-format OpenAI \
  --model-name gpt-35-turbo \
  --model-version 0125 \
  --deployment-name chat \
  --sku-name Standard \
  --capacity 30 --output json | tee temp.json
OPENAICHAT_OUTPUT=$(cat temp.json) 
rm temp.json
````

## Deploy OpenAI Text Embedding Model

The following commands deploy the Text Embedding (Ada-002) model to the previously created Azure Cognitive Services account. The model is set to the OpenAI format with version 2 and is deployed under the name embedding. It uses the Standard SKU and is allocated a capacity of 30 to support embedding-related tasks efficiently.

````bash
az cognitiveservices account deployment create \
  --name $OPENAI_NAME \
  --model-format OpenAI \
  --model-name text-embedding-ada-002 \
  --model-version 2 \
  --deployment-name 'embedding' \
  --sku-name Standard \
  --capacity 30 --output json | tee temp.json
OPENAIEMBEDDING_OUTPUT=$(cat temp.json) 
rm temp.json
````

## Create an Azure Document Intelligence Account

The following commands create an Azure Cognitive Services account for Document Intelligence (Form Recognizer).  The account is set to the S0 pricing tier, and configured with a custom domain.

````bash
DOCUMENTINTELLIGENCE_NAME="cog-di-${RESOURCE_TOKEN}"
az cognitiveservices account create \
  --name $DOCUMENTINTELLIGENCE_NAME \
  --kind FormRecognizer \
  --sku S0 \
  --custom-domain $DOCUMENTINTELLIGENCE_NAME \
  --tags $TAGS --output json | tee temp.json
DOCUMENTINTELLIGENCE_OUTPUT=$(cat temp.json) 
rm temp.json
````

## Create an Azure AI Search Service

The following commands create an Azure AI Search service with a unique name. The service is set to the Basic SKU and configured with a system-assigned managed identity for secure access. Local authentication is disabled, and public network access is enabled. Additionally, semantic search is activated with the free tier.

````bash
SEARCHSERVICE_NAME="gptkb-$RESOURCE_TOKEN"
az search service create \
  --name "gptkb-$RESOURCE_TOKEN" \
  --sku basic \
  --identity-type SystemAssigned \
  --disable-local-auth true \
  --public-network-access enabled \
  --semantic-search free \
  --tags $TAGS --output json | tee temp.json
SEARCHSERVICE_OUTPUT=$(cat temp.json)
rm temp.json
export SEARCHSERVICEID=$(jq -r '.id' <<< "$SEARCHSERVICE_OUTPUT")
export SEARCHSERVICENAME=$(jq -r '.name' <<< "$SEARCHSERVICE_OUTPUT")
export SEARCHSERVICEENDPOINT="https://$SEARCHSERVICENAME.search.windows.net/"
export SEARCHSERVICEPRINCIPALID=$(jq -r '.identity.principalId' <<< "$SEARCHSERVICE_OUTPUT")
````

## Enable Diagnostic Logging for Azure AI Search

The following commands configure diagnostic settings for the Azure AI Search service. Logging for Operation Logs and All Metrics is enabled, allowing detailed monitoring and insights into service activity. The logs and metrics are sent to the specified Azure Log Analytics Workspace for centralized analysis.

````bash
az monitor diagnostic-settings create \
  --name "$SEARCHSERVICENAME-diagnostics" \
  --resource $SEARCHSERVICEID \
  --logs "[{category:"OperationLogs",enabled:true}]" \
  --metrics "[{category:"AllMetrics",enabled:true}]" \
  --workspace $LOGANALYTICSWORKSPACEID | tee temp.json
SEARCHDIAGNOSTIC_OUTPUT=$(cat temp.json)
rm temp.json
````

## Create an Azure Storage Account

The following commands create an Azure Storage Account. The storage account is set to StorageV2 with the Standard_LRS SKU for locally redundant storage. Public network access is enabled, while blob public access and shared key access are disabled for security. Cross-tenant replication is allowed, and the Hot access tier is selected for frequently accessed data. The storage account is secured with TLS 1.2 as the minimum version, enforces HTTPS-only traffic, and uses the Standard DNS endpoint type.

````bash
az storage account create \
  --name "st$RESOURCE_TOKEN" \
  --tags $TAGS \
  --kind "StorageV2" \
  --sku Standard_LRS \
  --public-network-access Enabled \
  --bypass AzureServices \
  --allow-blob-public-access false \
  --allow-shared-key-access false \
  --allow-cross-tenant-replication true \
  --access-tier Hot \
  --dns-endpoint-type Standard \
  --min-tls-version "TLS1_2" \
  --default-action Allow \
  --https-only true --output json | tee temp.json
STORAGE_OUTPUT=$(cat temp.json)
rm temp.json
export STORAGEID=$(jq -r '.id' <<< "$STORAGE_OUTPUT")
export STORAGENAME=$(jq -r '.name' <<< "$STORAGE_OUTPUT")
export STORAGEENDPOINTS=$(jq -r '.primaryEndpoints' <<< "$STORAGE_OUTPUT")
````

## Configure Blob Storage Delete Retention

The following command updates the blob service properties of the Azure Storage Account to enable delete retention. This ensures that deleted blobs are retained for 2 days before permanent removal, allowing for recovery if necessary.

````bash
az storage account blob-service-properties update \
  --account-name $STORAGENAME \
  --enable-delete-retention true \
  --delete-retention-days 2
````

## Create Storage Containers

The following commands create multiple storage containers within the Azure Storage Account. The containers are named "user-content" and "tokens", with public access disabled for security. Authentication is handled using Azure login credentials to ensure controlled access.

````bash
CONTAINERS=("content" "tokens")
for CONTAINER in "${CONTAINERS[@]}"; do
  az storage container create \
    --name "$CONTAINER" \
    --auth-mode login \
    --account-name $STORAGENAME \
    --public-access "off"
done
````

## Store key app env in env file

The following commands stores key app  variables to be used as environment variables in the backend Azure Container App (ACA). Configuring ACA with these variables, allows applications to manage secrets, configurations, API endpoints, and feature toggles without hardcoding them into the container image.

````bash
> ~/appenv.env
[ -n "$STORAGENAME" ] && echo "AZURE_STORAGE_ACCOUNT=$STORAGENAME " > ~/appenv.env
echo "AZURE_STORAGE_CONTAINER="content" " >> ~/appenv.env
echo "AZURE_SEARCH_INDEX="gptkbindex" " >> ~/appenv.env
[ -n "$SEARCHSERVICENAME" ] && echo "AZURE_SEARCH_SERVICE=$SEARCHSERVICENAME " >> ~/appenv.env
echo "AZURE_SEARCH_SEMANTIC_RANKER=free " >> ~/appenv.env
echo "AZURE_SEARCH_QUERY_LANGUAGE=en-us " >> ~/appenv.env
echo "AZURE_SEARCH_QUERY_SPELLER=lexicon " >> ~/appenv.env
[ -n "$APPLICATIONINSIGHTSCONNECTIONSTRING" ] && echo "APPLICATIONINSIGHTS_CONNECTION_STRING=$APPLICATIONINSIGHTSCONNECTIONSTRING " >> ~/appenv.env
echo "ENABLE_LANGUAGE_PICKER=false " >> ~/appenv.env
echo "USE_SPEECH_INPUT_BROWSER=false " >> ~/appenv.env
echo "USE_SPEECH_OUTPUT_BROWSER=false " >> ~/appenv.env
echo "USE_SPEECH_OUTPUT_AZURE=false " >> ~/appenv.env

# Chat history settings
echo "USE_CHAT_HISTORY_BROWSER=false " >> ~/appenv.env
echo "USE_CHAT_HISTORY_COSMOS=false " >> ~/appenv.env
echo "AZURE_CHAT_HISTORY_DATABASE=chat-database " >> ~/appenv.env
echo "AZURE_CHAT_HISTORY_CONTAINER=chat-history-v2 " >> ~/appenv.env
echo "AZURE_CHAT_HISTORY_VERSION=cosmosdb-v2 " >> ~/appenv.env

# Shared by all OpenAI deployments
echo "OPENAI_HOST=azure " >> ~/appenv.env
echo "AZURE_OPENAI_EMB_MODEL_NAME=text-embedding-ada-002 " >> ~/appenv.env
echo "AZURE_OPENAI_EMB_DIMENSIONS=1536" >> ~/appenv.env
echo "AZURE_OPENAI_CHATGPT_MODEL=gpt-35-turbo " >> ~/appenv.env
echo "AZURE_OPENAI_GPT4V_MODEL=gpt-4o " >> ~/appenv.env
# Specific to Azure OpenAI
[ -n "$OPENAI_NAME" ] && echo "AZURE_OPENAI_SERVICE=$OPENAI_NAME " >> ~/appenv.env
echo "AZURE_OPENAI_CHATGPT_DEPLOYMENT=chat " >> ~/appenv.env
echo "AZURE_OPENAI_EMB_DEPLOYMENT=embedding " >> ~/appenv.env
# Optional login and document level access control system
echo "AZURE_USE_AUTHENTICATION=false " >> ~/appenv.env
echo "AZURE_ENFORCE_ACCESS_CONTROL=false " >> ~/appenv.env
echo "AZURE_ENABLE_GLOBAL_DOCUMENT_ACCESS=false " >> ~/appenv.env
echo "AZURE_ENABLE_UNAUTHENTICATED_ACCESS=false " >> ~/appenv.env
echo "AZURE_AUTHENTICATION_ISSUER_URI=$LOGIN_ENDPOINT/$TENANT_ID/v2.0 " >> ~/appenv.env
[ -n "$TENANT_ID" ] && echo "AZURE_TENANT_ID=$TENANT_ID " >> ~/appenv.env
[ -n "$TENANT_ID" ] && echo "AZURE_AUTH_TENANT_ID=$TENANT_ID " >> ~/appenv.env
# CORS support, for frontends on other hosts
echo "ALLOWED_ORIGIN=$ALLOWED_ORIGINS " >> ~/appenv.env
echo "USE_VECTORS=true" >> ~/appenv.env
echo "USE_GPT4V=false " >> ~/appenv.env
echo "USE_USER_UPLOAD=false " >> ~/appenv.env
[ -n "$DOCUMENTINTELLIGENCE_NAME" ] && echo "AZURE_DOCUMENTINTELLIGENCE_SERVICE=$DOCUMENTINTELLIGENCE_NAME " >> ~/appenv.env
echo "USE_MEDIA_DESCRIBER_AZURE_CU=false " >> ~/appenv.env
echo "RUNNING_IN_PRODUCTION=true " >> ~/appenv.env

[ -n "$CLIENTID" ] && echo "AZURE_CLIENT_ID=$CLIENTID " >> ~/appenv.env
````

## Set Container app env vars

````bash
ENV_FILE="appenv.env"
ENV_VARS=$(<"$ENV_FILE")

az containerapp update \
  --name $ACAWEBNAME \
  --replace-env-vars $ENV_VARS
````

## Azure Environment Configuration Script

This Bash script initializes environment variables for an Azure-based deployment, including authentication, AI services, search indexing, chat history, and CORS settings. It writes all values to ~/output.env, ensuring consistent configuration across deployments.

````bash
# These settings control authentication, resource access, and security policies.
echo "AZURE_LOCATION=$LOCATION" > ~/output.env
echo "AZURE_TENANT_ID=$TENANT_ID" >> ~/output.env
echo "AZURE_SUBSCRIPTION_ID=$SUBSCRIPTION" >> ~/output.env
echo "AZURE_AUTH_TENANT_ID=$TENANT_ID" >> ~/output.env
echo "AZURE_RESOURCE_GROUP=$RESOURCE_GROUP" >> ~/output.env
echo "AZURE_USE_AUTHENTICATION=false" >> ~/output.env
echo "AZURE_ENFORCE_ACCESS_CONTROL=false" >> ~/output.env
echo "AZURE_ENABLE_GLOBAL_DOCUMENT_ACCESS=false" >> ~/output.env
echo "AZURE_ENABLE_UNAUTHENTICATED_ACCESS=false" >> ~/output.env

# Defines AI models and service deployments for OpenAI within Azure.
echo "OPENAI_HOST=azure" >> ~/output.env
echo "AZURE_OPENAI_EMB_MODEL_NAME=text-embedding-ada-002" >> ~/output.env
echo "AZURE_OPENAI_EMB_DIMENSIONS=1536" >> ~/output.env
echo "AZURE_OPENAI_CHATGPT_MODEL=gpt-35-turbo" >> ~/output.env
echo "AZURE_OPENAI_GPT4V_MODEL=gpt-4o" >> ~/output.env

# Specifies OpenAI service names, deployments, and assigned resource groups.
echo "AZURE_OPENAI_SERVICE=$OPENAI_NAME" >> ~/output.env
echo "AZURE_OPENAI_RESOURCE_GROUP=$RESOURCE_GROUP" >> ~/output.env
echo "AZURE_OPENAI_CHATGPT_DEPLOYMENT=chat" >> ~/output.env
echo "AZURE_OPENAI_EMB_DEPLOYMENT=embedding" >> ~/output.env

# Configures document intelligence for AI-based text extraction.
echo "AZURE_DOCUMENTINTELLIGENCE_SERVICE=$DOCUMENTINTELLIGENCE_NAME" >> ~/output.env
echo "AZURE_DOCUMENTINTELLIGENCE_RESOURCE_GROUP=$RESOURCE_GROUP" >> ~/output.env

# Sets up search indexing and query ranking for AI-driven search functionalities.
echo "AZURE_SEARCH_INDEX=gptkbindex" >> ~/output.env
echo "AZURE_SEARCH_SERVICE=$SEARCHSERVICENAME" >> ~/output.env
echo "AZURE_SEARCH_SERVICE_RESOURCE_GROUP=$RESOURCE_GROUP" >> ~/output.env
echo "AZURE_SEARCH_SEMANTIC_RANKER=free" >> ~/output.env
echo "AZURE_SEARCH_SERVICE_ASSIGNED_USERID=$SEARCHSERVICEPRINCIPALID" >> ~/output.env
echo "AZURE_SEARCH_QUERY_LANGUAGE=en-us" >> ~/output.env
echo "AZURE_SEARCH_QUERY_SPELLER=lexicon" >> ~/output.env

# Defines settings for storing and managing AI chat history.
echo "AZURE_CHAT_HISTORY_DATABASE=chat-database" >> ~/output.env
echo "AZURE_CHAT_HISTORY_CONTAINER=chat-history-v2" >> ~/output.env
echo "AZURE_CHAT_HISTORY_VERSION=cosmosdb-v2" >> ~/output.env
echo "USE_CHAT_HISTORY_BROWSER=false" >> ~/output.env
echo "USE_CHAT_HISTORY_COSMOS=false" >> ~/output.env

# Configures the storage account and associated container.
echo "AZURE_STORAGE_ACCOUNT=$STORAGENAME" >> ~/output.env
echo "AZURE_STORAGE_CONTAINER=content" >> ~/output.env
echo "AZURE_STORAGE_RESOURCE_GROUP=$RESOURCE_GROUP" >> ~/output.env
echo "AZURE_USERSTORAGE_CONTAINER=user-content" >> ~/output.env
echo "AZURE_USERSTORAGE_RESOURCE_GROUP=$RESOURCE_GROUP" >> ~/output.env

# Sets allowed origins to support cross-origin resource sharing (CORS).
echo "ALLOWED_ORIGIN=$ALLOWED_ORIGINS" >> ~/output.env

# Enables or disables optional AI features and settings.
echo "USE_VECTORS=true" >> ~/output.env
echo "USE_GPT4V=false" >> ~/output.env
echo "USE_USER_UPLOAD=false" >> ~/output.env
echo "USE_MEDIA_DESCRIBER_AZURE_CU=false" >> ~/output.env
echo "RUNNING_IN_PRODUCTION=true" >> ~/output.env
echo "AZURE_AI_PROJECT=false" >> ~/output.env

# Sets backend API URI and Azure Container Registry details.
echo "BACKEND_URI=$ACAURI" >> ~/output.env
echo "AZURE_CONTAINER_REGISTRY_ENDPOINT=$ACRLOGINSERVER" >> ~/output.env

# Enables logging and telemetry through Azure Application Insights.
echo "APPLICATIONINSIGHTS_CONNECTION_STRING=$APPLICATIONINSIGHTSCONNECTIONSTRING" >> ~/output.env

# Configures language picker and speech-to-text / text-to-speech options.
echo "ENABLE_LANGUAGE_PICKER=false" >> ~/output.env
echo "USE_SPEECH_INPUT_BROWSER=false" >> ~/output.env
echo "USE_SPEECH_OUTPUT_BROWSER=false" >> ~/output.env
echo "USE_SPEECH_OUTPUT_AZURE=false" >> ~/output.env
````

## Assign User Roles for Azure Resources

The following commands assign predefined Azure roles to the signed-in user, granting the necessary permissions to interact with various services. The roles include access to Cognitive Services (OpenAI, Speech, and general use), Storage Blob data, Storage Account management, and Search Service data and indexing. Each role is assigned to the user at the resource group level to ensure proper access control across all relevant resources.

````bash
USER_ROLES='{
  "Cognitive Services OpenAI User": "5e0bd9bd-7b93-4f28-af87-19fc36ad61bd",
  "Cognitive Services User": "a97b65f3-24c7-4388-baec-2e87135dc908",
  "Cognitive Services Speech User": "f2dc8367-1007-4938-bd23-fe263f013447",
  "Storage Blob Data Reader": "2a2b9908-6ea1-4ae2-8e65-a410df84e7d1",
  "Storage Blob Data Contributor": "ba92f5b4-2d11-453d-a403-e96b0029c9fe",
  "Storage Account Contributor": "b7e6dc6d-f1e8-4753-8033-0f276bb0955b",
  "Search Service Data Reader": "1407120a-92aa-4202-b7e9-c0e197c71c8f",
  "Search Service Contributor": "8ebe5a00-799e-43f5-93ac-243d3dce84a7",
  "Search Index Data Contributor": "7ca78c08-252a-4471-8644-bb5ff32d4ba0"
}'

echo "$USER_ROLES" | jq -r '.[]' | while read -r ROLE_ID; do

  az role assignment create \
    --role "$ROLE_ID" \
    --assignee-object-id "$CLIENT_PRINCIPALID" \
    --scope "$RESOURCE_GROUP_ID" \
    --assignee-principal-type User
done
````

## Assign Backend Service Roles

The following commands assign Azure roles to the backend service's managed identity, allowing it to access necessary resources. The roles grant permissions to use Cognitive Services (OpenAI and Speech), read data from Azure Storage Blob, and query the Azure AI Search service. These permissions ensure the backend can interact securely with Azure services within the resource group scope.

````bash
BACKEND_ROLES='{
  "Cognitive Services OpenAI User": "5e0bd9bd-7b93-4f28-af87-19fc36ad61bd",
  "Storage Blob Data Reader": "2a2b9908-6ea1-4ae2-8e65-a410df84e7d1",
  "Search Service Data Reader": "1407120a-92aa-4202-b7e9-c0e197c71c8f",
  "Cognitive Services Speech User": "f2dc8367-1007-4938-bd23-fe263f013447"
}'

echo "$BACKEND_ROLES" | jq -r '.[]' | while read -r ROLE_ID; do

  az role assignment create \
    --role "$ROLE_ID" \
    --assignee-object-id $PRINCIPALID \
    --scope "$RESOURCE_GROUP_ID" \
    --assignee-principal-type ServicePrincipal
done
````

## Load Python Env

````bash
git clone https://github.com/Azure-Samples/azure-search-openai-demo.git postprovision_scripts
az login --scope https://search.azure.com/.default https://cognitiveservices.azure.com/.default  --tenant $TENANT_ID

cp load_env_var.py postprovision_scripts/scripts/load_EXECDOC_ENV.py
cp load_env_var.py postprovision_scripts/app/backend/load_EXECDOC_ENV.py

python3 -m venv venv
source venv/bin/activate

find postprovision_scripts -type f -exec sed -i 's/AzureDeveloperCliCredential/AzureCliCredential/g' {} +

cd postprovision_scripts
./scripts/prepdocs.sh

cd app/frontend
npm install
npm run build
cd -

IMAGE_NAME="my-backend-image"             # Name of the Docker image
az acr build --registry "$ACRNAME" --image "$IMAGE_NAME:latest" backend

az containerapp update \
  --name "$ACAWEBNAME" \
  --resource-group "$RESOURCE_GROUP" \
  --image "$ACRNAME.azurecr.io/$IMAGE_NAME:latest" | tee temp.json
ACAUPDATE_OUTPUT=$(cat temp.json)
rm temp.json
export ACAURI="https://$(jq -r '.properties.configuration.ingress.fqdn' <<< "$ACAUPDATE_OUTPUT")"
echo "Deployment endpoint: $ACAURI"
````