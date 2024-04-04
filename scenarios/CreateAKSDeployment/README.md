---
title: Deploy a Scalable & Secure Azure Kubernetes Service cluster using the Azure CLI
description: This tutorial where we will take you step by step in creating an Azure Kubernetes Web Application that is secured via https.
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine, linux-related content
---

# Quickstart: Deploy a Scalable & Secure Azure Kubernetes Service cluster using the Azure CLI

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262758)

Welcome to this tutorial where we will take you step by step in creating an Azure Kubernetes Web Application that is secured via https. This tutorial assumes you are logged into Azure CLI already and have selected a subscription to use with the CLI. It also assumes that you have Helm installed ([Instructions can be found here](https://helm.sh/docs/intro/install/)).

## Define Environment Variables

The first step in this tutorial is to define environment variables.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export SSL_EMAIL_ADDRESS="$(az account show --query user.name --output tsv)"
export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
```

## Create a resource group

A resource group is a container for related resources. All resources must be placed in a resource group. We will create one for this tutorial. The following command creates a resource group with the previously defined $MY_RESOURCE_GROUP_NAME and $REGION parameters.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Results:

<!-- expected_similarity=0.3 -->

```JSON
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myAKSResourceGroupxxxxxx",
  "location": "eastus",
  "managedBy": null,
  "name": "testResourceGroup",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Create AKS Cluster

Create an AKS cluster use the az aks create command. The following example creates a cluster named myAKSCluster with one node and enables a system-assigned managed identity. This will take a few minutes.

```bash
az aks create --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME  --enable-managed-identity --node-count 1 --generate-ssh-keys
```

## Connect to the cluster

To manage a Kubernetes cluster, use the Kubernetes command-line client, kubectl. kubectl is already installed if you use Azure Cloud Shell. To install kubectl locally, call the az aks install-cli command.

1. Install az aks CLI locally using the az aks install-cli command

   ```bash
   if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
   ```

2. Configure kubectl to connect to your Kubernetes cluster using the az aks get-credentials command. The following command:

   - Downloads credentials and configures the Kubernetes CLI to use them.
   - Uses ~/.kube/config, the default location for the Kubernetes configuration file. Specify a different location for your Kubernetes configuration file using --file argument.

   > [!WARNING]
   > This will overwrite any existing credentials with the same entry

   ```bash
   az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
   ```

3. Verify the connection to your cluster using the kubectl get command. This command returns a list of the cluster nodes.

   ```bash
   kubectl get nodes
   ```

## Deploy the Application

A Kubernetes manifest file defines a cluster's desired state, such as which container images to run.

In this quickstart, you will use a manifest to create all objects needed to run the Azure Vote application. This manifest includes two Kubernetes deployments:

- The sample Azure Vote Python applications.
- A Redis instance.

Two Kubernetes Services are also created:

- An internal service for the Redis instance.
- An external service to access the Azure Vote application from the internet.

Finally, an Ingress resource is created to route traffic to the Azure Vote application.

A test voting app YML file is already prepared. To deploy this app run the following command

```bash
kubectl apply -f aks-store-quickstart.yml
```

## Test The Application

Validate that the application is running by either visiting the public ip or the application url. The application url can be found by running the following command:

> [!Note]
> It often takes 2-3 minutes for the PODs to be created and the site to be reachable via HTTP

```bash
runtime="5 minute"
endtime=$(date -ud "$runtime" +%s)
while [[ $(date -u +%s) -le $endtime ]]
do
   STATUS=$(kubectl get pods -l app=store-front -o 'jsonpath={..status.conditions[?(@.type=="Ready")].status}')
   echo $STATUS
   if [ "$STATUS" == 'True' ]
   then
      export IP_ADDRESS=$(kubectl get service store-front --output 'jsonpath={..status.loadBalancer.ingress[0].ip}')
      echo "Service IP Address: $IP_ADDRESS"
      break
   else
      sleep 10
   fi
done
```

```bash
curl $IP_ADDRESS
```

Results:

<!-- expected_similarity=0.3 -->

```HTML
<!doctype html>
<html lang="">
   <head>
      <meta charset="utf-8">
      <meta http-equiv="X-UA-Compatible" content="IE=edge">
      <meta name="viewport" content="width=device-width,initial-scale=1">
      <link rel="icon" href="/favicon.ico">
      <title>store-front</title>
      <script defer="defer" src="/js/chunk-vendors.df69ae47.js"></script>
      <script defer="defer" src="/js/app.7e8cfbb2.js"></script>
      <link href="/css/app.a5dc49f6.css" rel="stylesheet">
   </head>
   <body>
      <div id="app"></div>
   </body>
</html>
```

## Next Steps

- [Azure Kubernetes Service Documentation](https://learn.microsoft.com/azure/aks/)
- [Create an Azure Container Registry](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-prepare-acr?tabs=azure-cli)
- [Scale your Applciation in AKS](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-scale?tabs=azure-cli)
- [Update your application in AKS](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-app-update?tabs=azure-cli)
