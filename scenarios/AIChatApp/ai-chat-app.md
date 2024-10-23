# Create an Azure OpenAI, LangChain, ChromaDB, and Chainlit Chat App in Container Apps

This guide will walk you through the steps to create an Azure OpenAI, LangChain, ChromaDB, and Chainlit Chat App in Azure Container Apps.

## Prerequisites

- An Azure account with an active subscription.
- Azure CLI installed on your local machine.
- Docker installed on your local machine.

## Step 1: Create an Azure OpenAI Service

1. **Create a Resource Group**:
    ```azurecli-interactive
    az group create --name myResourceGroup --location eastus
    ```

2. **Create an Azure OpenAI Service**:
    ```azurecli-interactive
    az cognitiveservices account create \
        --name myOpenAIService \
        --resource-group myResourceGroup \
        --kind OpenAI \
        --sku S0 \
        --location eastus \
        --yes
    ```

## Step 2: Set Up LangChain and ChromaDB

1. **Create a Dockerfile**:
    Create a `Dockerfile` to set up LangChain and ChromaDB.

    ```dockerfile
    # Use an official Python runtime as a parent image
    FROM python:3.9-slim

    # Set the working directory in the container
    WORKDIR /app

    # Copy the current directory contents into the container at /app
    COPY . /app

    # Install any needed packages specified in requirements.txt
    RUN pip install --no-cache-dir -r requirements.txt

    # Make port 80 available to the world outside this container
    EXPOSE 80

    # Define environment variable
    ENV NAME World

    # Run app.py when the container launches
    CMD ["python", "app.py"]
    ```

2. **Create a `requirements.txt` file**:
    List the dependencies for LangChain and ChromaDB.

    ```plaintext
    langchain
    chromadb
    chainlit
    azure-openai
    ```

3. **Create an `app.py` file**:
    Set up a basic Chainlit app using LangChain and ChromaDB.

    ```python
    from langchain import LangChain
    from chromadb import ChromaDB
    from chainlit import Chainlit

    # Initialize LangChain
    langchain = LangChain()

    # Initialize ChromaDB
    chromadb = ChromaDB()

    # Initialize Chainlit
    chainlit = Chainlit(langchain, chromadb)

    # Define a simple chat endpoint
    @chainlit.route('/chat', methods=['POST'])
    def chat():
        user_input = request.json.get('input')
        response = chainlit.chat(user_input)
        return jsonify({'response': response})

    if __name__ == '__main__':
        chainlit.run(host='0.0.0.0', port=80)
    ```

## Step 3: Build and Push the Docker Image

1. **Build the Docker Image**:
    ```bash
    docker build -t mychainlitapp .
    ```

2. **Push the Docker Image to Azure Container Registry**:
    ```azurecli-interactive
    az acr create --resource-group myResourceGroup --name myContainerRegistry --sku Basic
    az acr login --name myContainerRegistry
    docker tag mychainlitapp mycontainerregistry.azurecr.io/mychainlitapp:v1
    docker push mycontainerregistry.azurecr.io/mychainlitapp:v1
    ```

## Step 4: Deploy to Azure Container Apps

1. **Create a Container App Environment**:
    ```azurecli-interactive
    az containerapp env create --name myContainerAppEnv --resource-group myResourceGroup --location eastus
    ```

2. **Deploy the Container App**:
    ```azurecli-interactive
    az containerapp create \
        --name myChainlitApp \
        --resource-group myResourceGroup \
        --environment myContainerAppEnv \
        --image mycontainerregistry.azurecr.io/mychainlitapp:v1 \
        --target-port 80 \
        --ingress 'external' \
        --cpu 0.5 --memory 1.0Gi
    ```

## Step 5: Test the Deployment

1. **Get the URL of the Container App**:
    ```azurecli-interactive
    az containerapp show --name myChainlitApp --resource-group myResourceGroup --query properties.configuration.ingress.fqdn
    ```

2. **Test the Chat App**:
    Open the URL in your browser and interact with your Chainlit chat app.

By following these steps, you will have successfully created and deployed an Azure OpenAI, LangChain, ChromaDB, and Chainlit Chat App in Azure Container Apps.