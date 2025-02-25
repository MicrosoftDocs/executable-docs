---
title: 'Quickstart: Create a Speech Services application on Azure'
description: Learn how to create a Speech Services application using Azure CLI. This will include creating a Speech service resource to support scenarios like speech-to-text and text-to-speech.
ms.topic: quickstart
ms.date: 10/07/2023
author: azure-voice-guru
ms.author: azurevoice
ms.custom: cognitive-services, azure-cli, innovation-engine
---

# Quickstart: Create a Speech Services application on Azure

In this quickstart, you will learn how to create a Speech Service resource using Azure CLI. This service enables scenarios such as speech-to-text, text-to-speech, and speech translation.

---

## Prerequisites

- Azure CLI installed and configured on your machine.
- Proper permissions to create resources in your Azure subscription.

---

## Step 1: Create a Resource Group

A resource group is a container that holds related resources for an Azure solution.

```bash
export RANDOM_SUFFIX=$(openssl rand -hex 3)
export REGION="westus2"
export RESOURCE_GROUP_NAME="SpeechAppGroup$RANDOM_SUFFIX"
az group create --name $RESOURCE_GROUP_NAME --location $REGION --output json
```

### Results:

<!-- expected_similarity=0.3 -->

```json
{
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/SpeechAppGroupxxx",
    "location": "westus2",
    "managedBy": null,
    "name": "SpeechAppGroupxxx",
    "properties": {
        "provisioningState": "Succeeded"
    },
    "tags": null,
    "type": "Microsoft.Resources/resourceGroups"
}
```

---

## Step 2: Create a Speech Service Resource

The Speech Service is part of Azure Cognitive Services and provides functionalities like speech-to-text, text-to-speech, and translation. You will create this resource within the resource group.

```bash
export SPEECH_SERVICE_NAME="MySpeechService$RANDOM_SUFFIX"
az cognitiveservices account create \
  --name $SPEECH_SERVICE_NAME \
  --resource-group $RESOURCE_GROUP_NAME \
  --kind SpeechServices \
  --sku S0 \
  --location $REGION \
  --yes \
  --output json
```

### Results:

<!-- expected_similarity=0.3 -->

```json
{
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/SpeechAppGroupxxx/providers/Microsoft.CognitiveServices/accounts/MySpeechServicexxx",
    "location": "westus2",
    "name": "MySpeechServicexxx",
    "properties": {
        "provisioningState": "Succeeded"
    },
    "sku": {
        "name": "S0"
    },
    "type": "Microsoft.CognitiveServices/accounts"
}
```

---

## Step 3: Ensure Resource Provisioning Completes

Ensure the Speech Service resource is fully provisioned before proceeding. A polling mechanism is implemented here to verify the provisioning state.

---

### Updated Polling with JSON Validation

```bash
export PROVISIONING_STATE=$(az cognitiveservices account show \
  --only-show-errors \
  --name $SPEECH_SERVICE_NAME \
  --resource-group $RESOURCE_GROUP_NAME \
  --query "properties.provisioningState" -o tsv 2>/dev/null || echo "Unknown")
echo "Current provisioning state: $PROVISIONING_STATE"
```

### Results:

<!-- expected_similarity=0.3 -->

```text
Current provisioning state: Succeeded
```

---

## Step 4: Retrieve Keys and Endpoint

You will need the keys and endpoint to use the Speech Service in your applications.

---

### Retrieve Keys

Fetch the keys for accessing the Speech Service.

```bash
KEYS_JSON=$(az cognitiveservices account keys list \
  --only-show-errors \
  --name $SPEECH_SERVICE_NAME \
  --resource-group $RESOURCE_GROUP_NAME \
  -o json 2>/dev/null)

if [ -z "$KEYS_JSON" ] || [ "$KEYS_JSON" == "null" ]; then
  echo "Error: Failed to retrieve keys. Verify the resource status in the Azure portal."
  exit 1
fi

export KEY1=$(echo "$KEYS_JSON" | jq -r '.key1')
export KEY2=$(echo "$KEYS_JSON" | jq -r '.key2')

if [ -z "$KEY1" ] || [ "$KEY2" == "null" ]; then
  echo "Error: Retrieved keys are empty or invalid. Inspect the resource settings."
  exit 1
fi

echo "Key1: Retrieved successfully"
echo "Key2: Retrieved successfully"
```

### Results:

<!-- expected_similarity=0.3 -->

```output
Key1: Retrieved successfully
Key2: Retrieved successfully
```

---

### Retrieve Endpoint

Fetch the endpoint for the Speech Service.

---

### Updated Endpoint Retrieval

```bash
ENDPOINT_JSON=$(az cognitiveservices account show \
  --name $SPEECH_SERVICE_NAME \
  --resource-group $RESOURCE_GROUP_NAME \
  -o json 2>/dev/null)

if echo "$ENDPOINT_JSON" | grep -q '"code": "404"'; then
  echo "Error: Resource not found. Verify the resource name, group, or region."
  exit 1
fi

export ENDPOINT=$(echo "$ENDPOINT_JSON" | jq -r '.properties.endpoint')
if [ -z "$ENDPOINT" ] || [ "$ENDPOINT" == "null" ]; then
  echo "Error: Failed to retrieve endpoint. Verify the resource status in the Azure portal."
  exit 1
fi

echo "Endpoint: $ENDPOINT"
```

### Results:

<!-- expected_similarity=0.3 -->

```text
https://xxxxxxxxxxxxxxxxxxxxx.cognitiveservices.azure.com/
```
