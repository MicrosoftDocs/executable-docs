---
title: 'Quickstart: Deploy a Postgres vector database' 
description: Setup a Postgres vector database and openai resources to run a RAG-LLM model.
ms.topic: quickstart 
ms.date: 09/06/2024 
author: aamini7 
ms.author: ariaamini
ms.custom: innovation-engine, linux-related-content 
---

# Quickstart: Create a Linux virtual machine with the Azure CLI on Azure

**Applies to:** :heavy_check_mark: Linux VMs

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262692)

This quickstart shows you how to use the Azure CLI to deploy a Linux virtual machine (VM) in Azure. The Azure CLI is used to create and manage Azure resources via either the command line or scripts.

If you don't have an Azure subscription, create a [free account](https://azure.microsoft.com/free/?WT.mc_id=A261C142F) before you begin.

## Launch Azure Cloud Shell

The Azure Cloud Shell is a free interactive shell that you can use to run the steps in this article. It has common Azure tools preinstalled and configured to use with your account. 

To open the Cloud Shell, just select **Try it** from the upper right corner of a code block. You can also open Cloud Shell in a separate browser tab by going to [https://shell.azure.com/bash](https://shell.azure.com/bash). Select **Copy** to copy the blocks of code, paste it into the Cloud Shell, and select **Enter** to run it.

If you prefer to install and use the CLI locally, this quickstart requires Azure CLI version 2.0.30 or later. Run `az --version` to find the version. If you need to install or upgrade, see [Install Azure CLI]( /cli/azure/install-azure-cli).

## Log in to Azure using the CLI

In order to run commands in Azure using the CLI, you need to log in first. Log in using the `az login` command.

## Set up resource group

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export RG_NAME="myPostgresResourceGroup$RANDOM_ID"
export REGION="centralus"

az group create \
    --name $RG_NAME \
    --location $REGION \
    --subscription $SUBSCRIPTION_ID
```

## Create Database

```bash
export POSTGRES_SERVER_NAME="mydb$RANDOM_ID"
export PGHOST="${POSTGRES_SERVER_NAME}.postgres.database.azure.com"
export PGUSER="dbadmin$RANDOM_ID"
export PGPORT=5432
export PGDATABASE="azure-ai-demo"
export PGPASSWORD="$(openssl rand -base64 32)"

az postgres flexible-server create \
    --admin-password $PGPASSWORD \
    --admin-user $PGUSER \
    --location $REGION \
    --name $POSTGRES_SERVER_NAME \
    --database-name $PGDATABASE \
    --resource-group $RG_NAME \
    --sku-name Standard_B2s \
    --storage-auto-grow Disabled \
    --storage-size 32 \
    --tier Burstable \
    --version 16 \
    --yes -o JSON \
    --public-access 0.0.0.0

az postgres flexible-server parameter set \
    --resource-group $RG_NAME \
    --subscription $SUBSCRIPTION_ID \
    --server-name $POSTGRES_SERVER_NAME \
    --name azure.extensions --value vector

psql -c "CREATE EXTENSION IF NOT EXISTS vector;"

psql \
    -c "CREATE TABLE embeddings(id int PRIMARY KEY, data text, embedding vector(1536));" \
    -c "CREATE INDEX ON embeddings USING hnsw (embedding vector_ip_ops);"
```

## Set up OpenAI resource

```bash
export OPEN_AI_SERVICE_NAME="openai-service-$RANDOM_ID"
export EMBEDDING_MODEL="text-embedding-ada-002"
export CHAT_MODEL="gpt-4-turbo-2024-04-09"

az cognitiveservices account create \
    --name $OPEN_AI_SERVICE_NAME \
    --resource-group $RG_NAME \
    --location $REGION \
    --kind OpenAI \
    --sku s0 \
    --subscription $SUBSCRIPTION_ID

az cognitiveservices account deployment create \
    --name $OPEN_AI_SERVICE_NAME \
    --resource-group  $RG_NAME \
    --deployment-name $EMBEDDING_MODEL \
    --model-name $EMBEDDING_MODEL \
    --model-version "1"  \
    --model-format OpenAI \
    --sku-capacity "1" \
    --sku-name "Standard"

az cognitiveservices account deployment create \
    --name $OPEN_AI_SERVICE_NAME \
    --resource-group  $RG_NAME \
    --deployment-name $CHAT_MODEL \
    --model-name $CHAT_MODEL \
    --model-version "0125-Preview" \
    --model-format OpenAI \
    --sku-capacity "1" \
    --sku-name "Standard"
```

## Clone and run chatbot code

```bash
git clone https://github.com/aamini7/postgres-rag-llm-demo
pip install -r requirements
python chat.py --populate
```