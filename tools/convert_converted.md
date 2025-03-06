---
title: 'How-to: Create and deploy an Azure OpenAI Service resource'
titleSuffix: Azure OpenAI
description: Learn how to get started with Azure OpenAI Service and create your first resource and deploy your first model in the Azure CLI or the Azure portal.
#services: cognitive-services
manager: nitinme
ms.service: azure-ai-openai
ms.custom: devx-track-azurecli, build-2023, build-2023-dataai, devx-track-azurepowershell, innovation-engine
ms.topic: how-to
ms.date: 01/31/2025
zone_pivot_groups: openai-create-resource
author: mrbullwinkle
ms.author: mbullwin
recommendations: false
---

# Create and deploy an Azure OpenAI Service resource

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2303211)

This article describes how to get started with Azure OpenAI Service and provides step-by-step instructions to create a resource and deploy a model. You can create resources in Azure in several different ways:

- The [Azure portal](https://portal.azure.com/?microsoft_azure_marketplace_ItemHideKey=microsoft_openai_tip#create/Microsoft.CognitiveServicesOpenAI)
- The REST APIs, the Azure CLI, PowerShell, or client libraries
- Azure Resource Manager (ARM) templates

In this article, you review examples for creating and deploying resources in the Azure portal and with the Azure CLI.

## Prerequisites

- An Azure subscription. <a href="https://azure.microsoft.com/free/ai-services" target="_blank">Create one for free</a>.
- Access permissions to [create Azure OpenAI resources and to deploy models](../how-to/role-based-access-control.md).
- The Azure CLI. For more information, see [How to install the Azure CLI](/cli/azure/install-azure-cli).

## Create an Azure resource group

To create an Azure OpenAI resource, you need an Azure resource group. When you create a new resource through the Azure CLI, you can also create a new resource group or instruct Azure to use an existing group. The following example shows how to create a new resource group named OAIResourceGroup with the az group create command. The resource group is created in the East US location.

```azurecli
export RANDOM_SUFFIX=$(openssl rand -hex 3)
export REGION="eastus"
export OAI_RESOURCE_GROUP="OAIResourceGroup$RANDOM_SUFFIX"
az group create --name $OAI_RESOURCE_GROUP --location $REGION
```

Results: 

<!-- expected_similarity=0.3 -->

```JSON
{
  "id": "/subscriptions/xxxxx/resourceGroups/OAIResourceGroupxxxxx",
  "location": "eastus",
  "managedBy": null,
  "name": "OAIResourceGroupxxxxx",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Create a resource

Use the az cognitiveservices account create command to create an Azure OpenAI resource in the resource group. In the following example, you create a resource named MyOpenAIResource in the OAI_RESOURCE_GROUP resource group. When you try the example, update the code to use your desired values for the resource group and resource name.

```azurecli
export OPENAI_RESOURCE_NAME="MyOpenAIResource$RANDOM_SUFFIX"
az cognitiveservices account create \
--name $OPENAI_RESOURCE_NAME \
--resource-group $OAI_RESOURCE_GROUP \
--location $REGION \
--kind OpenAI \
--sku s0
```

Results: 

<!-- expected_similarity=0.3 -->

```JSON
{
  "id": "/subscriptions/xxxxx/resourceGroups/OAIResourceGroupxxxxx/providers/Microsoft.CognitiveServices/accounts/MyOpenAIResourcexxxxx",
  "kind": "OpenAI",
  "location": "eastus",
  "name": "MyOpenAIResourcexxxxx",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "sku": {
    "name": "s0"
  },
  "type": "Microsoft.CognitiveServices/accounts"
}
```

## Retrieve information about the resource

After you create the resource, you can use different commands to find useful information about your Azure OpenAI Service instance. The following examples demonstrate how to retrieve the REST API endpoint base URL and the access keys for the new resource.

### Get the endpoint URL

Use the az cognitiveservices account show command to retrieve the REST API endpoint base URL for the resource. In this example, we direct the command output through the jq JSON processor to locate the .properties.endpoint value.

When you try the example, update the code to use your values for the resource group and resource.

```azurecli
az cognitiveservices account show \
--name $OPENAI_RESOURCE_NAME \
--resource-group $OAI_RESOURCE_GROUP \
| jq -r .properties.endpoint
```

Results: 

<!-- expected_similarity=0.3 -->

```text
https://openaiendpointxxxxx.cognitiveservices.azure.com/
```

### Get the primary API key

To retrieve the access keys for the resource, use the az cognitiveservices account keys list command. In this example, we direct the command output through the jq JSON processor to locate the .key1 value.

When you try the example, update the code to use your values for the resource group and resource.

```azurecli
az cognitiveservices account keys list \
--name $OPENAI_RESOURCE_NAME \
--resource-group $OAI_RESOURCE_GROUP \
| jq -r .key1
```

Results: 

<!-- expected_similarity=0.3 -->

```text
xxxxxxxxxxxxxxxxxxxxxx
```

## Deploy a model

To deploy a model, use the az cognitiveservices account deployment create command. In the following example, you deploy an instance of the text-embedding-ada-002 model and give it the name MyModel. When you try the example, update the code to use your values for the resource group and resource. You don't need to change the model-version, model-format, sku-capacity, or sku-name values.

```azurecli
export MODEL_DEPLOYMENT_NAME="MyModel"
az cognitiveservices account deployment create \
--name $OPENAI_RESOURCE_NAME \
--resource-group $OAI_RESOURCE_GROUP \
--deployment-name $MODEL_DEPLOYMENT_NAME \
--model-name text-embedding-ada-002 \
--model-version "1"  \
--model-format OpenAI \
--sku-capacity "1" \
--sku-name "Standard"
```

Results: 

<!-- expected_similarity=0.3 -->

```JSON
{
  "deploymentName": "MyModel",
  "provisioningState": "Succeeded"
}
```

> [!IMPORTANT]
> When you access the model via the API, you need to refer to the deployment name rather than the underlying model name in API calls, which is one of the [key differences](../how-to/switching-endpoints.yml) between OpenAI and Azure OpenAI. OpenAI only requires the model name. Azure OpenAI always requires deployment name, even when using the model parameter. In our docs, we often have examples where deployment names are represented as identical to model names to help indicate which model works with a particular API endpoint. Ultimately your deployment names can follow whatever naming convention is best for your use case.

## Delete a model from your resource

You can delete any model deployed from your resource with the az cognitiveservices account deployment delete command. In the following example, the original document provided instructions to delete a model named MyModel. When you try the example, update the code to use your values for the resource group, resource, and deployed model.

(Note: The deletion code block has been removed from this Exec Doc as deletion commands are not executed automatically in Exec Docs.)

## Delete a resource

If you want to clean up after these exercises, you can remove your Azure OpenAI resource by deleting the resource through the Azure CLI. You can also delete the resource group. If you choose to delete the resource group, all resources contained in the group are also deleted.

To remove the resource group and its associated resources, the original document provided a command example. Be sure to update the example code to use your values for the resource group and resource.

(Note: The deletion code block has been removed from this Exec Doc as deletion commands are not executed automatically in Exec Docs.)

## Next steps

- [Get started with the Azure OpenAI security building block](/azure/developer/ai/get-started-securing-your-ai-app?tabs=github-codespaces&pivots=python)
- Make API calls and generate text with [Azure OpenAI Service quickstarts](../quickstart.md).
- Learn more about the [Azure OpenAI Service models](../concepts/models.md).
- For information on pricing visit the [Azure OpenAI pricing page](https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/)