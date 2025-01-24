---
title: 'Tutorial: Implement RAG on Azure Cognitive Services with a Chat Interface'
description: Learn how to implement Retrieval-Augmented Generation (RAG) using Azure Cognitive Services, LangChain, ChromaDB, and Chainlit, and deploy it in Azure Container Apps.
ms.topic: tutorial
ms.date: 10/10/2023
author: GitHubCopilot
ms.author: GitHubCopilot
ms.custom: innovation-engine
---

# Tutorial: Create a RAG Chat App using Azure AI Search with OpenAI in Python

This tutorial guides you through the process of creating a Retrieval-Augmented Generation (RAG) Chat App using Azure AI Search with OpenAI in Python.

## Prerequisites

- An Azure account with an active subscription.
- Azure CLI installed on your local machine.
- Python 3.9 or higher installed on your local machine.
- Docker installed if you plan to containerize the application.

## Step 1: Create Azure Resources

1. **Set Environment Variables**

   ```bash
   export RANDOM_SUFFIX=$(openssl rand -hex 3)
   export RESOURCE_GROUP="myResourceGroup$RANDOM_SUFFIX"
   export LOCATION="westus2"
   ```

2. **Create a Resource Group**

   ```bash
   az group create --name $RESOURCE_GROUP --location $LOCATION
   ```

   Results:

   <!-- expected_similarity=0.3 -->

   ```JSON
   {
     "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myResourceGroupxxx",
     "location": "westus2",
     "managedBy": null,
     "name": "myResourceGroupxxx",
     "properties": {
       "provisioningState": "Succeeded"
     },
     "tags": null,
     "type": "Microsoft.Resources/resourceGroups"
   }
   ```

3. **Create an Azure Cognitive Search Service**

   ```bash
   export SEARCH_SERVICE_NAME="mySearchService$RANDOM_SUFFIX"
   az search service create \
     --name $SEARCH_SERVICE_NAME \
     --resource-group $RESOURCE_GROUP \
     --location $LOCATION \
     --sku basic
   ```

   Results:

   <!-- expected_similarity=0.3 -->

   ```JSON
   {
     "hostName": "mysearchservicexxx.search.windows.net",
     "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myResourceGroupxxx/providers/Microsoft.Search/searchServices/mySearchServicexxx",
     "location": "westus2",
     "name": "mySearchServicexxx",
     "properties": {
       "status": "running",
       "provisioningState": "succeeded",
       "replicaCount": 1,
       "partitionCount": 1,
       "sku": {
         "name": "basic"
       }
     },
     "type": "Microsoft.Search/searchServices"
   }
   ```

4. **Create an Azure OpenAI Service**

   ```bash
   export OPENAI_SERVICE_NAME="myOpenAIService$RANDOM_SUFFIX"
   az cognitiveservices account create \
     --name $OPENAI_SERVICE_NAME \
     --resource-group $RESOURCE_GROUP \
     --kind OpenAI \
     --sku S0 \
     --location $LOCATION \
     --custom-domain $OPENAI_SERVICE_NAME
   ```

## Step 2: Prepare the Data and Index

1. **Create a Sample Document**

   ```bash
   mkdir rag-chat-app
   cd rag-chat-app
   echo "Azure Cognitive Search enhances the experience of users by indexing and retrieving relevant data." > documents.txt
   ```

2. **Upload Documents to Azure Cognitive Search**

   ```bash
   az search service update \
     --name $SEARCH_SERVICE_NAME \
     --resource-group $RESOURCE_GROUP \
     --set properties.corsOptions.allowedOrigins="*"

   export SEARCH_ADMIN_KEY=$(az search admin-key show --resource-group $RESOURCE_GROUP --service-name $SEARCH_SERVICE_NAME --query primaryKey --output tsv)
   ```

   Create a Python script `upload_docs.py`:

   ```python
   import os
   from azure.core.credentials import AzureKeyCredential
   from azure.search.documents import SearchClient, SearchIndexClient
   from azure.search.documents.indexes.models import SearchIndex, SimpleField, edm

   search_service_endpoint = f"https://{os.environ['SEARCH_SERVICE_NAME']}.search.windows.net"
   admin_key = os.environ['SEARCH_ADMIN_KEY']

   index_name = "documents"

   index_client = SearchIndexClient(search_service_endpoint, AzureKeyCredential(admin_key))

   fields = [
       SimpleField(name="id", type=edm.String, key=True),
       SimpleField(name="content", type=edm.String, searchable=True)
   ]

   index = SearchIndex(name=index_name, fields=fields)

   index_client.create_or_update_index(index)

   search_client = SearchClient(search_service_endpoint, index_name, AzureKeyCredential(admin_key))

   documents = [
       {"id": "1", "content": open("documents.txt").read()}
   ]

   result = search_client.upload_documents(documents)
   print(f"Uploaded documents: {result}")
   ```

   Run the script:

   ```bash
   export SEARCH_SERVICE_NAME
   export SEARCH_ADMIN_KEY
   python3 upload_docs.py
   ```

## Step 3: Build the RAG Chat App

1. **Create a Virtual Environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install Dependencies**

   Create a `requirements.txt` file:

   ```plaintext
   azure-search-documents
   openai
   python-dotenv
   flask
   ```

   Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. **Create the `app.py` File**

   ```python
   import os
   from flask import Flask, request, jsonify
   from azure.core.credentials import AzureKeyCredential
   from azure.search.documents import SearchClient
   import openai

   app = Flask(__name__)

   search_service_endpoint = f"https://{os.environ['SEARCH_SERVICE_NAME']}.search.windows.net"
   index_name = "documents"
   search_client = SearchClient(search_service_endpoint, index_name, AzureKeyCredential(os.environ['SEARCH_ADMIN_KEY']))

   openai.api_type = "azure"
   openai.api_base = f"https://{os.environ['OPENAI_SERVICE_NAME']}.openai.azure.com/"
   openai.api_version = "2023-03-15-preview"
   openai.api_key = os.environ["OPENAI_API_KEY"]

   @app.route('/chat', methods=['POST'])
   def chat():
       user_question = request.json.get('question', '')

       results = search_client.search(user_question)
       context = " ".join([doc['content'] for doc in results])

       response = openai.Completion.create(
           engine="text-davinci-003",
           prompt=f"Answer the following question using the context below:\n\nContext: {context}\n\nQuestion: {user_question}\nAnswer:",
           max_tokens=150
       )

       answer = response.choices[0].text.strip()
       return jsonify({'answer': answer})

   if __name__ == '__main__':
       app.run(host='0.0.0.0', port=5000)
   ```

4. **Set Environment Variables**

   ```bash
   export SEARCH_SERVICE_NAME=$SEARCH_SERVICE_NAME
   export SEARCH_ADMIN_KEY=$SEARCH_ADMIN_KEY
   export OPENAI_SERVICE_NAME=$OPENAI_SERVICE_NAME
   export OPENAI_API_KEY="<Your Azure OpenAI Key>"
   ```

## Step 4: Test the Application Locally

Run the application:

```bash
python3 app.py
```

Results:

<!-- expected_similarity=0.3 -->

```log
 * Serving Flask app 'app'
 * Running on all addresses.
   WARNING: This is a development server. Do not use it in a production deployment.
 * Running on http://0.0.0.0:5000/ (Press CTRL+C to quit)
```

In another terminal, test the chat endpoint:

```bash
curl -X POST http://localhost:5000/chat -H "Content-Type: application/json" -d '{"question": "What does Azure Cognitive Search do?"}'
```

Results:

<!-- expected_similarity=0.3 -->

```JSON
{
  "answer": "Azure Cognitive Search indexes and retrieves relevant data to enhance user experiences."
}
```

## Step 5: (Optional) Containerize the Application

1. **Create a `Dockerfile`**

   ```dockerfile
   FROM python:3.9-slim

   WORKDIR /app

   COPY . /app

   RUN pip install --no-cache-dir -r requirements.txt

   EXPOSE 5000

   CMD ["python", "app.py"]
   ```

2. **Build the Docker Image**

   ```bash
   docker build -t rag-chat-app .
   ```

3. **Run the Docker Container**

   ```bash
   docker run -p 5000:5000 rag-chat-app
   ```

## Conclusion

You have successfully created a RAG Chat App using Azure AI Search with OpenAI in Python.