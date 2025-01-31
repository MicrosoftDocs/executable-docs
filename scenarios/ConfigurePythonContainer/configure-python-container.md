---
title: 'Quickstart: Configure a Linux Python app in Azure App Service'
description: Learn how to configure a Linux Python app in Azure App Service, including setting Python versions and customizing build automation.
ms.topic: quickstart
ms.date: 10/07/2023
author: msangapu
ms.author: msangapu
ms.custom: innovation-engine, devx-track-python, devx-track-azurecli, linux-related-content
---

# Quickstart: Configure a Linux Python app in Azure App Service

In this quickstart, you'll learn how to configure a Python app deployed on Azure App Service using the Azure CLI. This includes setting and checking the Python version, listing the supported Python versions for App Service, and customizing build automation during deployment.

## Prerequisites

Ensure you have the following:

- An Azure subscription.
- [Azure CLI installed](https://learn.microsoft.com/cli/azure/install-azure-cli) locally or access to [Azure Cloud Shell](https://ms.portal.azure.com/#cloudshell/).
- Permissions to manage resources in your Azure subscription.

## Step 1: Create necessary resources

The following commands create the required resources: a resource group, an App Service plan, and an App Service instance. **Random suffixes are included for resource names to avoid conflicts.**

### Create a resource group

```bash
export RANDOM_SUFFIX=$(openssl rand -hex 3)
export REGION="centralindia"
export RESOURCE_GROUP="MyResourceGroup$RANDOM_SUFFIX"
az group create --name $RESOURCE_GROUP --location $REGION
```

Results:

<!-- expected_similarity=0.3 -->

```json
{
    "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyResourceGroupxxx",
    "location": "centralindia",
    "managedBy": null,
    "name": "MyResourceGroupxxx",
    "properties": {
        "provisioningState": "Succeeded"
    },
    "tags": null,
    "type": "Microsoft.Resources/resourceGroups"
}
```

### Create an App Service plan

```bash
export APP_SERVICE_PLAN="MyAppServicePlan$RANDOM_SUFFIX"
az appservice plan create --name $APP_SERVICE_PLAN --resource-group $RESOURCE_GROUP --sku FREE --is-linux
```

Results:

<!-- expected_similarity=0.3 -->

```json
{
    "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyResourceGroupxxx/providers/Microsoft.Web/serverfarms/MyAppServicePlanxxx",
    "location": "centralindia",
    "name": "MyAppServicePlanxxx",
    "sku": {
        "name": "F1",
        "tier": "Free",
        "size": "F1",
        "family": "F",
        "capacity": 1
    },
    "reserved": true
}
```

### Create an App Service instance

```bash
export APP_NAME="MyPythonApp$RANDOM_SUFFIX"
export RUNTIME="PYTHON|3.10"
az webapp create --resource-group $RESOURCE_GROUP --plan $APP_SERVICE_PLAN --name $APP_NAME --runtime $RUNTIME
```

Results:

<!-- expected_similarity=0.3 -->

```json
{
    "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyResourceGroupxxx/providers/Microsoft.Web/sites/MyPythonAppxxx",
    "name": "MyPythonAppxxx",
    "state": "Running",
    "defaultHostName": "MyPythonAppxxx.azurewebsites.net"
}
```

## Step 2: Show the current Python version

The following command retrieves the Python runtime version currently used by your Azure App Service.

```bash
az webapp config show --resource-group $RESOURCE_GROUP --name $APP_NAME --query linuxFxVersion -o jsonc
```

Results:

<!-- expected_similarity=0.3 -->

```jsonc
"PYTHON|3.10"
```

## Step 3: Set the desired Python version

Update your Azure App Service instance to use a specific Python version. Replace the desired Python version (e.g., "PYTHON|3.11") as needed.

```bash
export DESIRED_PYTHON_VERSION="PYTHON|3.11"
az webapp config set --resource-group $RESOURCE_GROUP --name $APP_NAME --linux-fx-version $DESIRED_PYTHON_VERSION
```

Verify the updated Python version:

```bash
az webapp config show --resource-group $RESOURCE_GROUP --name $APP_NAME --query linuxFxVersion -o jsonc
```

Results:

<!-- expected_similarity=0.3 -->

```jsonc
"PYTHON|3.11"
```

## Step 4: List all supported Python runtime versions

Use the following command to view all Python versions supported by Azure App Service on Linux.

```bash
az webapp list-runtimes --os linux --query "[?contains(@, 'PYTHON')]" -o jsonc
```

Results:

<!-- expected_similarity=0.3 -->

```jsonc
[
    "PYTHON|3.7",
    "PYTHON|3.8",
    "PYTHON|3.9",
    "PYTHON|3.10",
    "PYTHON|3.11"
]
```

## Step 5: Customize build automation

Azure App Service automates the Python app-building process during deployment. These steps demonstrate how to configure or modify its behavior.

### Enable build automation

The following command configures App Service to run the build process during deployment by setting the `SCM_DO_BUILD_DURING_DEPLOYMENT` variable to `1`.

```bash
az webapp config appsettings set --resource-group $RESOURCE_GROUP --name $APP_NAME --settings SCM_DO_BUILD_DURING_DEPLOYMENT="1"
```

## Step 6: Add application settings

App settings in Azure App Service act as environment variables within your app. Below, we add and verify a sample setting.

### Add a new App Service environment variable

For example, set a `DATABASE_SERVER` variable for your app as shown below:

```bash
export DATABASE_SERVER="https://mydatabase.example"
az webapp config appsettings set --resource-group $RESOURCE_GROUP --name $APP_NAME --settings DATABASE_SERVER=$DATABASE_SERVER
```

### Verify the setting

```bash
az webapp config appsettings list --resource-group $RESOURCE_GROUP --name $APP_NAME --query "[?name=='DATABASE_SERVER']" -o jsonc
```

Results:

<!-- expected_similarity=0.3 -->

```jsonc
[
    {
        "name": "DATABASE_SERVER",
        "slotSetting": false,
        "value": "https://mydatabase.example"
    }
]
```