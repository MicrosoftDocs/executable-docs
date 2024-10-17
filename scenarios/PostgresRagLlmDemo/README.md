---
title: 'Quickstart: Deploy a Postgres vector database' 
description: Setup a Postgres vector database and openai resources to run a RAG-LLM model.
ms.topic: quickstart 
ms.date: 09/06/2024 
author: aamini7 
ms.author: ariaamini
ms.custom: innovation-engine, linux-related-content 
---

## Set up resource group

Set up a resource group with a random ID.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export RG_NAME="myPostgresResourceGroup$RANDOM_ID"
export REGION="centralus"

az group create \
    --name $RG_NAME \
    --location $REGION \
```

## Create OpenAI resources

Create the openai resource

```bash
export OPEN_AI_SERVICE_NAME="openai-service-$RANDOM_ID"
export EMBEDDING_MODEL="text-embedding-ada-002"
export CHAT_MODEL="gpt-4-turbo-2024-04-09"

az cognitiveservices account create \
    --name $OPEN_AI_SERVICE_NAME \
    --resource-group $RG_NAME \
    --location westus \
    --kind OpenAI \
    --sku s0 \
```

## Create OpenAI deployments

```bash
export EMBEDDING_MODEL="text-embedding-ada-002"
export CHAT_MODEL="gpt-4"

az cognitiveservices account deployment create \
    --name $OPEN_AI_SERVICE_NAME \
    --resource-group  $RG_NAME \
    --deployment-name $EMBEDDING_MODEL \
    --model-name $EMBEDDING_MODEL \
    --model-version "2"  \
    --model-format OpenAI \
    --sku-capacity "1" \
    --sku-name "Standard"

az cognitiveservices account deployment create \
    --name $OPEN_AI_SERVICE_NAME \
    --resource-group  $RG_NAME \
    --deployment-name $CHAT_MODEL \
    --model-name $CHAT_MODEL \
    --model-version "turbo-2024-04-09" \
    --model-format OpenAI \
    --sku-capacity "1" \
    --sku-name "Standard"
```

## Create Database

Create an Azure postgres database.

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
```

## Enable postgres vector extension

Set up the vector extension for postgres to allow storing vectors/embeddings.

```bash
az postgres flexible-server parameter set \
    --resource-group $RG_NAME \
    --server-name $POSTGRES_SERVER_NAME \
    --name azure.extensions --value vector

psql -c "CREATE EXTENSION IF NOT EXISTS vector;"

psql \
    -c "CREATE TABLE embeddings(id int PRIMARY KEY, data text, embedding vector(1536));" \
    -c "CREATE INDEX ON embeddings USING hnsw (embedding vector_ip_ops);"
```

## Populate with data from knowledge file

The chat bot uses a local file called "knowledge.txt" as the sample document to generate embeddings for
and to store those embeddings in the newly created postgres database. Then any questions you ask will
be augmented with context from the "knowledge.txt" after searching the document for the most relevant
pieces of context using the embeddings. The "knowledge.txt" is about a fictional material called Zytonium.
You can view the full knowledge.txt and the code for the chatbot by looking in the "scenarios/PostgresRagLlmDemo" directory.

```bash
export ENDPOINT=$(az cognitiveservices account show --name $OPEN_AI_SERVICE_NAME --resource-group $RG_NAME | jq -r .properties.endpoint)
export API_KEY=$(az cognitiveservices account keys list --name $OPEN_AI_SERVICE_NAME --resource-group $RG_NAME | jq -r .key1)

cd ~/scenarios/PostgresRagLlmDemo
pip install -r requirements.txt
python chat.py --populate --api-key $API_KEY --endpoint $ENDPOINT --pguser $PGUSER --phhost $PGHOST --pgpassword $PGPASSWORD --pgdatabase $PGDATABASE
```

## Run Chat bot

This final step prints out the command you can copy/paste into the terminal to run the chatbot. `cd ~/scenarios/PostgresRagLlmDemo && python chat.py --api-key $API_KEY --endpoint $ENDPOINT --pguser $PGUSER --phhost $PGHOST --pgpassword $PGPASSWORD --pgdatabase $PGDATABASE`

```bash
echo "
To run the chatbot, see the last step for more info.
"
```
