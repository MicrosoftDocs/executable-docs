---
title: 'Quickstart: Create an Azure Resource Group'
description: 'Create an Azure Resource Group with Azure CLI using environment variables and a unique random suffix. Verify execution with the Innovation Engine—start building your Azure infrastructure today.'
ms.topic: quickstart
ms.date: 10/06/2023
author: chatgpt
ms.author: chatgpt
ms.custom: innovation-engine, azure-cli, quickstart
---

# Create an Azure Resource Group

In this Exec Doc, you will learn how to create an Azure Resource Group using Azure CLI. The resource group name will include a dynamically generated random suffix to ensure uniqueness for each deployment. In addition, environment variables are used to manage settings such as the region and resource group name, streamlining your configuration process.

## Step 1: Declare Environment Variables and Create the Resource Group

In this section, we export the environment variables required for creating the resource group. The region is set to "WestUS2", a random suffix is generated and appended to the resource group name, and the command to create the resource group is executed.

```azurecli
export REGION="WestUS2"
export RANDOM_SUFFIX=$(openssl rand -hex 3)
export MY_RESOURCE_GROUP_NAME="MyResourceGroup"
az group create --name "$MY_RESOURCE_GROUP_NAME$RANDOM_SUFFIX" --location $REGION
```

Results:

<!-- expected_similarity=0.3 -->

```JSON
{
    "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyResourceGroupxxxxxx",
    "location": "WestUS2",
    "managedBy": null,
    "name": "MyResourceGroupxxxxxx",
    "properties": {
        "provisioningState": "Succeeded"
    },
    "tags": null,
    "type": "Microsoft.Resources/resourceGroups"
}
```

In the output above, the subscription ID and the resource group name have been redacted to protect sensitive information. The resource group was successfully created in the specified region "WestUS2".