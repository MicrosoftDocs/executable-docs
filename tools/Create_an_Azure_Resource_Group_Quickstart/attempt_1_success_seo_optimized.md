---
title: 'Quickstart: Create an Azure Resource Group'
description: 'Create an Azure Resource Group with Azure CLI using environment variables and a unique random suffix. Follow this guide and verify your results now!'
ms.topic: quickstart
ms.date: 10/06/2023
author: chatgpt
ms.author: chatgpt
ms.custom: innovation-engine, azure-cli, quickstart
---

# Create an Azure Resource Group

In this Exec Doc, you'll learn how to efficiently create an Azure Resource Group using the Azure CLI. By leveraging environment variables to manage configuration settings and incorporating a unique random suffix into the resource group name, this guide ensures each deployment is distinct and easy to verify. Follow along to manage your Azure configurations effectively and confirm your results in the specified region.

## Step 1: Declare Environment Variables and Create the Resource Group

In this section, we export the environment variables required for creating the resource group. We set the region to "WestUS2", generate a random suffix to append to the resource group name, and finally execute the command to create the resource group.

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