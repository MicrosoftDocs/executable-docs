---
title: 'Create and manage Azure OpenAI Service deployments with the Azure CLI'
titleSuffix: Azure OpenAI
description: Learn how to use the Azure CLI to create an Azure OpenAI resource and manage deployments with the Azure OpenAI Service.
#services: cognitive-services
manager: nitinme
ms.author: colinmixon
ms.service: azure-ai-openai
ms.custom: devx-track-azurecli, linux-related-content,innovation-engine
ms.topic: include
ms.date: 07/11/2024
---

## Prerequisites

- An Azure subscription. <a href="https://azure.microsoft.com/free/ai-services" target="_blank">Create one for free</a>.
- Access granted to Azure OpenAI in the desired Azure subscription.
- Access permissions to [create Azure OpenAI resources and to deploy models](../how-to/role-based-access-control.md).
- The Azure CLI. For more information, see [How to install the Azure CLI](/cli/azure/install-azure-cli).

> [!NOTE]
> Currently, you must submit an application to access Azure OpenAI Service. To apply for access, complete [this form](https://aka.ms/oai/access). If you need assistance, open an issue on this repository to contact Microsoft.

## Sign in to the Azure CLI

[Sign in](/cli/azure/authenticate-azure-cli) to the Azure CLI or select **Open Cloudshell** in the following steps.

## Create an Azure resource group

To create an Azure OpenAI resource, you need an Azure resource group. When you create a new resource through the Azure CLI, you can also create a new resource group or instruct Azure to use an existing group. The following example shows how to create a new resource group named _$MY_RESOURCE_GROUP_NAME_ with the [az group create](/cli/azure/group?view=azure-cli-latest&preserve-view=true#az-group-create) command. The resource group is created in the East US region as defined by the enviornment variable _$REGION_. 

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myAOAIResourceGroup$RANDOM_ID"
export REGION="eastus"
export TAGS="owner=user"

az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION --tags $TAGS
```

Results:
<!-- expected_similarity=0.7 -->
```JSON
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myAOAIResourceGroupxxxxxx",
  "location": "eastus",
  "managedBy": null,
  "name": "myAIResourceGroupxxxxxx",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": {
    "owner": "user"
  },
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Create a resource

Use the [az cognitiveservices account create](/cli/azure/cognitiveservices/account?view=azure-cli-latest&preserve-view=true#az-cognitiveservices-account-create) command to create an Azure OpenAI resource in the resource group. In the following example, you create a resource named _$MY_OPENAI_RESOURCE_NAME_ in the _$MY_RESOURCE_GROUP_NAME_ resource group. When you try the example, update the environment variables to use your desired values for the resource group and resource name.

```bash
export MY_OPENAI_RESOURCE_NAME="myOAIResource$RANDOM_ID"
az cognitiveservices account create \
--name $MY_OPENAI_RESOURCE_NAME \
--resource-group $MY_RESOURCE_GROUP_NAME \
--location $REGION \
--kind OpenAI \
--sku s0 \
```
Results:
<!-- expected_similarity=0.7 -->
```JSON
{
  "etag": "\"xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\"",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myAOAIResourceGroupxxxxxx/providers/Microsoft.CognitiveServices/accounts/myOAIResourcexxxxxx",
  "identity": null,
  "kind": "OpenAI",
  "location": "eastus",
  "name": "myOAIResourcexxxxxx",
  "properties": {
    "abusePenalty": null,
    "allowedFqdnList": null,
    "apiProperties": null,
    "callRateLimit": {
      "count": null,
      "renewalPeriod": null,
      "rules": [
        {
          "count": 30.0,
          "dynamicThrottlingEnabled": null,
          "key": "openai.dalle.post",
          "matchPatterns": [
            {
              "method": "POST",
              "path": "dalle/*"
            },
            {
              "method": "POST",
              "path": "openai/images/*"
            }
          ],
          "minCount": null,
          "renewalPeriod": 1.0
        },
        {
          "count": 30.0,
          "dynamicThrottlingEnabled": null,
          "key": "openai.dalle.other",
          "matchPatterns": [
            {
              "method": "*",
              "path": "dalle/*"
            },
            {
              "method": "*",
              "path": "openai/operations/images/*"
            }
          ],
          "minCount": null,
          "renewalPeriod": 1.0
        },
        {
          "count": 30.0,
          "dynamicThrottlingEnabled": null,
          "key": "openai",
          "matchPatterns": [
            {
              "method": "*",
              "path": "openai/*"
            }
          ],
          "minCount": null,
          "renewalPeriod": 1.0
        },
        {
          "count": 30.0,
          "dynamicThrottlingEnabled": null,
          "key": "default",
          "matchPatterns": [
            {
              "method": "*",
              "path": "*"
            }
          ],
          "minCount": null,
          "renewalPeriod": 1.0
        }
      ]
    },
    "capabilities": [
      {
        "name": "VirtualNetworks",
        "value": null
      },
      {
        "name": "CustomerManagedKey",
        "value": null
      },
      {
        "name": "MaxFineTuneCount",
        "value": "100"
      },
      {
        "name": "MaxRunningFineTuneCount",
        "value": "1"
      },
      {
        "name": "MaxUserFileCount",
        "value": "50"
      },
      {
        "name": "MaxTrainingFileSize",
        "value": "512000000"
      },
      {
        "name": "MaxUserFileImportDurationInHours",
        "value": "1"
      },
      {
        "name": "MaxFineTuneJobDurationInHours",
        "value": "720"
      },
      {
        "name": "TrustedServices",
        "value": "Microsoft.CognitiveServices,Microsoft.MachineLearningServices,Microsoft.Search"
      }
    ],
    "commitmentPlanAssociations": null,
    "customSubDomainName": null,
    "dateCreated": "xxxx-xx-xxxxx:xx:xx.xxxxxxxx",
    "deletionDate": null,
    "disableLocalAuth": null,
    "dynamicThrottlingEnabled": null,
    "encryption": null,
    "endpoint": "https://eastus.api.cognitive.microsoft.com/",
    "endpoints": {
      "OpenAI Dall-E API": "https://eastus.api.cognitive.microsoft.com/",
      "OpenAI Language Model Instance API": "https://eastus.api.cognitive.microsoft.com/",
      "OpenAI Model Scaleset API": "https://eastus.api.cognitive.microsoft.com/",
      "OpenAI Whisper API": "https://eastus.api.cognitive.microsoft.com/"
    },
    "internalId": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "isMigrated": false,
    "locations": null,
    "migrationToken": null,
    "networkAcls": null,
    "privateEndpointConnections": [],
    "provisioningState": "Succeeded",
    "publicNetworkAccess": "Enabled",
    "quotaLimit": null,
    "restore": null,
    "restrictOutboundNetworkAccess": null,
    "scheduledPurgeDate": null,
    "skuChangeInfo": null,
    "userOwnedStorage": null
  },
  "resourceGroup": "myAOAIResourceGroupxxxxxx",
  "sku": {
    "capacity": null,
    "family": null,
    "name": "S0",
    "size": null,
    "tier": null
  },
  "systemData": {
    "createdAt": "xxxx-xx-xxxxx:xx:xx.xxxxxxxx",
    "createdBy": "yyyyyyyyyyyyyyyyyyyyyyyy",
    "createdByType": "User",
    "lastModifiedAt": "xxxx-xx-xxxxx:xx:xx.xxxxxx+xx:xx",
    "lastModifiedBy": "yyyyyyyyyyyyyyyyyyyyyyyy",
    "lastModifiedByType": "User"
  },
  "tags": null,
  "type": "Microsoft.CognitiveServices/accounts"
}
```

## Retrieve information about the resource

After you create the resource, you can use different commands to find useful information about your Azure OpenAI Service instance. The following examples demonstrate how to retrieve the REST API endpoint base URL and the access keys for the new resource.

### Get the endpoint URL

Use the [az cognitiveservices account show](/cli/azure/cognitiveservices/account?view=azure-cli-latest&preserve-view=true#az-cognitiveservices-account-show) command to retrieve the REST API endpoint base URL for the resource. In this example, we direct the command output through the [jq](https://jqlang.github.io/jq/) JSON processor to locate the `.properties.endpoint` value.

When you try the example, update the environment variables to use your values for the resource group _$MY_RESOURCE_GROUP_NAME_ and resource _$MY_OPENAI_RESOURCE_NAME_.

```bash
az cognitiveservices account show \
--name $MY_OPENAI_RESOURCE_NAME \
--resource-group $MY_RESOURCE_GROUP_NAME \
| jq -r .properties.endpoint
```

### Get the primary API key

To retrieve the access keys for the resource, use the [az cognitiveservices account keys list](/cli/azure/cognitiveservices/account?view=azure-cli-latest&preserve-view=true#az-cognitiveservices-account-keys-list) command. In this example, we direct the command output through the [jq](https://jqlang.github.io/jq/) JSON processor to locate the `.key1` value.

When you try the example, update the environment variables to use your values for the resource group and resource.

```bash
az cognitiveservices account keys list \
--name $MY_OPENAI_RESOURCE_NAME \
--resource-group $MY_RESOURCE_GROUP_NAME \
| jq -r .key1
```

## Deploy a model

To deploy a model, use the [az cognitiveservices account deployment create](/cli/azure/cognitiveservices/account/deployment?view=azure-cli-latest&preserve-view=true#az-cognitiveservices-account-deployment-create) command. In the following example, you deploy an instance of the `text-embedding-ada-002` model and give it the name _$MY_MODEL_NAME_. When you try the example, update the variables to use your values for the resource group and resource. You don't need to change the `model-version`, `model-format` or `sku-capacity`, and `sku-name` values.

```bash
export MY_MODEL_NAME="myModel$RANDOM_ID"
az cognitiveservices account deployment create \
--name $MY_OPENAI_RESOURCE_NAME \
--resource-group $MY_RESOURCE_GROUP_NAME \
--deployment-name $MY_MODEL_NAME \
--model-name text-embedding-ada-002 \
--model-version "2"  \
--model-format OpenAI \
--sku-capacity "1" \
--sku-name "Standard"
```

`--sku-name` accepts the following deployment types: `Standard`, `GlobalStandard`, and `ProvisionedManaged`.  Learn more about [deployment type options](../how-to/deployment-types.md).


> [!IMPORTANT]
> When you access the model via the API, you need to refer to the deployment name rather than the underlying model name in API calls, which is one of the [key differences](../how-to/switching-endpoints.yml) between OpenAI and Azure OpenAI. OpenAI only requires the model name. Azure OpenAI always requires deployment name, even when using the model parameter. In our docs, we often have examples where deployment names are represented as identical to model names to help indicate which model works with a particular API endpoint. Ultimately your deployment names can follow whatever naming convention is best for your use case.

Results:
<!-- expected_similarity=0.7 -->
```JSON
{
  "etag": "\"xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\"",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myAOAIResourceGroupxxxxxx/providers/Microsoft.CognitiveServices/accounts/myOAIResourcexxxxxx/deployments/myModelxxxxxx",
  "name": "myModelxxxxxx",
  "properties": {
    "callRateLimit": null,
    "capabilities": {
      "embeddings": "true",
      "embeddingsMaxInputs": "1"
    },
    "model": {
      "callRateLimit": null,
      "format": "OpenAI",
      "name": "text-embedding-ada-002",
      "source": null,
      "version": "1"
    },
    "provisioningState": "Succeeded",
    "raiPolicyName": null,
    "rateLimits": [
      {
        "count": 1.0,
        "dynamicThrottlingEnabled": null,
        "key": "request",
        "matchPatterns": null,
        "minCount": null,
        "renewalPeriod": 10.0
      },
      {
        "count": 1000.0,
        "dynamicThrottlingEnabled": null,
        "key": "token",
        "matchPatterns": null,
        "minCount": null,
        "renewalPeriod": 60.0
      }
    ],
    "scaleSettings": null,
    "versionUpgradeOption": "OnceNewDefaultVersionAvailable"
  },
  "resourceGroup": "myAOAIResourceGroupxxxxxx",
  "sku": {
    "capacity": 1,
    "family": null,
    "name": "Standard",
    "size": null,
    "tier": null
  },
  "systemData": {
    "createdAt": "xxxx-xx-xxxxx:xx:xx.xxxxxx+xx:xx",
    "createdBy": "yyyyyyyyyyyyyyyyyyyyyyyy",
    "createdByType": "User",
    "lastModifiedAt": "xxxx-xx-xxxxx:xx:xx.xxxxxx+xx:xx",
    "lastModifiedBy": "yyyyyyyyyyyyyyyyyyyyyyyy",
    "lastModifiedByType": "User"
  },
  "type": "Microsoft.CognitiveServices/accounts/deployments"
}
```
## Delete a model from your resource

You can delete any model deployed from your resource with the [az cognitiveservices account deployment delete](/cli/azure/cognitiveservices/account/deployment?view=azure-cli-latest&preserve-view=true#az-cognitiveservices-account-deployment-delete) command. 