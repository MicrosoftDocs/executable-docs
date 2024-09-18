---
title: 'Quickstart: Deploy a Postgres vector database' 
description: Setup a Postgres vector database and openai resources to run a RAG-LLM model.
ms.topic: quickstart 
ms.date: 09/06/2024 
author: aamini7 
ms.author: ariaamini
ms.custom: innovation-engine, linux-related-content 
---

## Set up

```bash
export PGUSER="dbadminb8cec6"
export PGHOST="mydbb8cec6.postgres.database.azure.com"
export PGPASSWORD="UhBTK5NW7k7JovG+kjDBbhMQon6GN5qIoibgjrzjyXs="
export PGDATABASE="azure-ai-demo"

export RG_NAME="myPostgresResourceGroupb8cec6"

export ENDPOINT=$(az cognitiveservices account show --name $OPEN_AI_SERVICE_NAME --resource-group $RG_NAME | jq -r .properties.endpoint)
export API_KEY=$(az cognitiveservices account keys list --name $OPEN_AI_SERVICE_NAME --resource-group $RG_NAME | jq -r .key1)
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

Run the chat bot

```bash
echo "cd ~/scenarios/PostgresRagLlmDemo && python chat.py --api-key \$API_KEY --endpoint \$ENDPOINT --pguser \$PGUSER --phhost \$PGHOST --pgpassword \$PGPASSWORD --pgdatabase \$PGDATABASE"
```
