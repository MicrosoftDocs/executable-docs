---
title: 'Quickstart: Deploy a Postgres vector database' 
description: Setup a Postgres vector database and openai resources to run a RAG-LLM model.
ms.topic: quickstart 
ms.date: 09/06/2024 
author: aamini7 
ms.author: ariaamini
ms.custom: innovation-engine, linux-related-content 
---

## Introduction

In this doc, we go over how to host the infrastructure required to run a basic LLM model with RAG capabilities on Azure.

We first set up a Postgres database capable of storing vector embeddings for documents/knowledge files that we want to use to augment our queries. We then create an Azure OpenAI deployment capable of generating embeddings and answering questions using the latest 'gpt-4-turbo' model.

We then use a python script to fill our postgres database with embeddings from a sample "knowledge.txt" file containing information about an imaginary resource called 'Zytonium'. Once the database is filled with those embeddings, we use the same python script to answer any questions we have about 'Zytonium'. 

The script will search the database for relevant information for our query using an embeddings search and then augment our query with that relevant information before being sent our LLM to answer.

## Set up resource group

Set up a resource group with a random ID.

```bash
export RANDOM_ID="b795cc"
export RG_NAME="myPostgresResourceGroup$RANDOM_ID"
export REGION="centralus"

az group create \
    --name $RG_NAME \
    --location $REGION 
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
    --sku s0 
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

The chat bot uses a local file called "knowledge.txt" as the sample document to generate embeddings for and to store those embeddings in the newly created postgres database. Then any questions you ask will be augmented with context from the "knowledge.txt" after searching the document for the most relevant pieces of context using the embeddings. The "knowledge.txt" is about a fictional material called Zytonium.

You can view the full knowledge.txt and the code for the chatbot by looking in the "scenarios/PostgresRagLlmDemo" directory.

```bash
export ENDPOINT=$(az cognitiveservices account show --name $OPEN_AI_SERVICE_NAME --resource-group $RG_NAME | jq -r .properties.endpoint)
export API_KEY=$(az cognitiveservices account keys list --name $OPEN_AI_SERVICE_NAME --resource-group $RG_NAME | jq -r .key1)

cd ~/scenarios/PostgresRagLlmDemo
pip install -r requirements.txt
python chat.py --populate --api-key $API_KEY --endpoint $ENDPOINT --pguser $PGUSER --phhost $PGHOST --pgpassword $PGPASSWORD --pgdatabase $PGDATABASE
```

## Set up Web Interface

Create a simple web interface for the chatbot using Flask.

1. **Install Flask**

    ```bash
    pip install Flask
    ```

2. **Create `app.py`**

    Create a file named `app.py` in the `scenarios/PostgresRagLlmDemo` directory with the following content:

    ```python
    from flask import Flask, request, render_template
    import subprocess
    import os

    app = Flask(__name__)

    @app.route('/', methods=['GET'])
    def home():
        return render_template('index.html', response='')

    @app.route('/ask', methods=['POST'])
    def ask():
        question = request.form['question']
        result = subprocess.run([
            'python', 'chat.py',
            '--api-key', os.getenv('API_KEY'),
            '--endpoint', os.getenv('ENDPOINT'),
            '--pguser', os.getenv('PGUSER'),
            '--phhost', os.getenv('PGHOST'),
            '--pgpassword', os.getenv('PGPASSWORD'),
            '--pgdatabase', os.getenv('PGDATABASE'),
            '--question', question
        ], capture_output=True, text=True)
        response = result.stdout
        return render_template('index.html', response=response)

    if __name__ == '__main__':
        app.run(host='0.0.0.0', port=5000)
    ```

3. **Create `index.html`**

    Create a `templates` directory inside `scenarios/PostgresRagLlmDemo` and add an `index.html` file with the following content:

    ```html
    <!doctype html>
    <html lang="en">
      <head>
        <title>Chatbot Interface</title>
      </head>
      <body>
        <h1>Ask about Zytonium</h1>
        <form action="/ask" method="post">
          <input type="text" name="question" required>
          <button type="submit">Ask</button>
        </form>
        <pre>{{ response }}</pre>
      </body>
    </html>
    ```

4. **Run the Web Server**

    Ensure that all environment variables are exported and then run the Flask application:

    ```bash
    export API_KEY="$API_KEY"
    export ENDPOINT="$ENDPOINT"
    export PGUSER="$PGUSER"
    export PGHOST="$PGHOST"
    export PGPASSWORD="$PGPASSWORD"
    export PGDATABASE="$PGDATABASE"

    python app.py
    ```

    The web interface will be accessible at `http://localhost:5000`. You can ask questions about Zytonium through the browser.

## Next Steps

- Explore more features of [Azure Cognitive Search](https://learn.microsoft.com/azure/search/search-what-is-azure-search).
- Learn how to [use Azure OpenAI with your data](https://learn.microsoft.com/azure/cognitive-services/openai/use-your-data).
<!-- ## Run Chat bot

This final step initializes the chatbot in your terminal. You can ask it questions about Zytonium and it will use the embeddings in the postgres database to augment your query with relevant context before sending it to the LLM model.

```bash
echo "Ask the chatbot a question about Zytonium!"
```

```bash
python chat.py --api-key $API_KEY --endpoint $ENDPOINT --pguser $PGUSER --phhost $PGHOST --pgpassword $PGPASSWORD --pgdatabase $PGDATABASE
``` -->
