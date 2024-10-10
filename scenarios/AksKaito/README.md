---
title: Deploy an AI model on Azure Kubernetes Service (AKS) with the AI toolchain operator (preview)
description: Learn how to enable the AI toolchain operator add-on on Azure Kubernetes Service (AKS) to simplify OSS AI model management and deployment.
ms.topic: article
ms.custom: azure-kubernetes-service, devx-track-azurecli
ms.date: 02/28/2024
author: schaffererin
ms.author: schaffererin

---

## Quickstart: Create a Linux virtual machine with the Azure CLI on Azure

**Applies to:** :heavy_check_mark: Linux VMs

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262692)

This quickstart shows you how to use the Azure CLI to deploy a Linux virtual machine (VM) in Azure. The Azure CLI is used to create and manage Azure resources via either the command line or scripts.

If you don't have an Azure subscription, create a [free account](https://azure.microsoft.com/free/?WT.mc_id=A261C142F) before you begin.

## Deploy an AI model on Azure Kubernetes Service (AKS) with the AI toolchain operator (preview)

The AI toolchain operator (KAITO) is a managed add-on for AKS that simplifies the experience of running OSS AI models on your AKS clusters. The AI toolchain operator automatically provisions the necessary GPU nodes and sets up the associated inference server as an endpoint server to your AI models. Using this add-on reduces your onboarding time and enables you to focus on AI model usage and development rather than infrastructure setup.

This article shows you how to enable the AI toolchain operator add-on and deploy an AI model on AKS.

[!INCLUDE [preview features callout](~/reusable-content/ce-skilling/azure/includes/aks/includes/preview/preview-callout.md)]

## Before you begin

* This article assumes a basic understanding of Kubernetes concepts. For more information, see [Kubernetes core concepts for AKS](./concepts-clusters-workloads.md).
* For ***all hosted model inference images*** and recommended infrastructure setup, see the [KAITO GitHub repository](https://github.com/Azure/kaito).
* The AI toolchain operator add-on currently supports KAITO version **v0.1.0**, please make a note of this in considering your choice of model from the KAITO model repository.

## Prerequisites

* If you don't have an Azure subscription, create a [free account](https://azure.microsoft.com/free/?WT.mc_id=A261C142F) before you begin.
  * If you have multiple Azure subscriptions, make sure you select the correct subscription in which the resources will be created and charged using the [az account set](https://learn.microsoft.com/en-us/cli/azure/account?view=azure-cli-latest#az-account-set) command.

    > [!NOTE]
    > The subscription you use must have GPU VM quota.

* Azure CLI version 2.47.0 or later installed and configured. Run `az --version` to find the version. If you need to install or upgrade, see [Install Azure CLI](/cli/azure/install-azure-cli).
* The Kubernetes command-line client, kubectl, installed and configured. For more information, see [Install kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/).
* [Install the Azure CLI AKS preview extension](#install-the-azure-cli-preview-extension).
* [Register the AI toolchain operator add-on feature flag](#register-the-ai-toolchain-operator-add-on-feature-flag).

## Set up resource group

Set up a resource group with a random ID. Create an Azure resource group using the [az group create](https://learn.microsoft.com/en-us/cli/azure/group?view=azure-cli-latest#az-group-create) command.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export AZURE_RESOURCE_GROUP="myKaitoResourceGroup$RANDOM_ID"
export REGION="centralus"
export CLUSTER_NAME="myClusterName$RANDOM_ID"

az group create \
    --name $AZURE_RESOURCE_GROUP \
    --location $REGION \
```

## Install the Azure CLI preview extension

Install the Azure CLI preview extension using the [az extension add](https://learn.microsoft.com/en-us/cli/azure/extension?view=azure-cli-latest#az-extension-add) command. Then update the extension to make sure you have the latest version using the [az extension update](https://learn.microsoft.com/en-us/cli/azure/extension?view=azure-cli-latest#az-extension-update) command.

```bash
az extension add --name aks-preview
az extension update --name aks-preview
```

## Register the AI toolchain operator add-on feature flag

Register the AIToolchainOperatorPreview feature flag using the az feature register command.
It takes a few minutes for the registration to complete.

```bash
az feature register --namespace "Microsoft.ContainerService" --name "AIToolchainOperatorPreview"
```

## Verify the AI toolchain operator add-on registration

Verify the registration using the [az feature show](https://learn.microsoft.com/en-us/cli/azure/feature?view=azure-cli-latest#az-feature-show) command.

```bash
while true; do
    status=$(az feature show --namespace "Microsoft.ContainerService" --name "AIToolchainOperatorPreview" --query "properties.state" -o tsv)
    if [ "$status" == "Registered" ]; then
        break
    else
        sleep 15
    fi
done
```

## Create an AKS cluster with the AI toolchain operator add-on enabled

Create an AKS cluster with the AI toolchain operator add-on enabled using the [az aks create](https://learn.microsoft.com/en-us/cli/azure/aks?view=azure-cli-latest#az-aks-create) command with the `--enable-ai-toolchain-operator` and `--enable-oidc-issuer` flags.

> [!NOTE]
> AKS creates a managed identity once you enable the AI toolchain operator add-on. The managed identity is used to create GPU node pools in the managed AKS cluster. Proper permissions need to be set for it manually following the steps introduced in the following sections.
>
> AI toolchain operator enablement requires the enablement of OIDC issuer.

```bash
az aks create --location ${REGION} \
    --resource-group ${AZURE_RESOURCE_GROUP} \
    --name ${CLUSTER_NAME} \
    --enable-oidc-issuer \
    --node-os-upgrade-channel SecurityPatch \
    --auto-upgrade-channel stable \
    --enable-ai-toolchain-operator \
    --generate-ssh-keys \
    --k8s-support-plan KubernetesOfficial
```

## Connect to your cluster

Configure `kubectl` to connect to your cluster using the [az aks get-credentials](https://learn.microsoft.com/en-us/cli/azure/aks?view=azure-cli-latest#az-aks-get-credentials) command.

```bash
az aks get-credentials --resource-group ${AZURE_RESOURCE_GROUP} --name ${CLUSTER_NAME}
```

Verify the connection to your cluster using the `kubectl get` command.

```bash
kubectl get nodes
```

## Export environment variables

Export environment variables for the MC resource group, KAITO identity, and AKS OIDC Issuer URL using the following commands:

```bash
export MC_RESOURCE_GROUP=$(az aks show --resource-group ${AZURE_RESOURCE_GROUP} \
    --name ${CLUSTER_NAME} \
    --query nodeResourceGroup \
    -o tsv)

export KAITO_IDENTITY_NAME="ai-toolchain-operator-${CLUSTER_NAME}"

export AKS_OIDC_ISSUER=$(az aks show --resource-group "${AZURE_RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --query "oidcIssuerProfile.issuerUrl" \
    -o tsv)
```

## Establish a federated identity credential

Create the federated identity credential between the managed identity, AKS OIDC issuer, and subject using the [az identity federated-credential create](https://learn.microsoft.com/en-us/cli/azure/identity/federated-credential?view=azure-cli-latest) command.

```bash
az identity federated-credential create --name "kaito-federated-identity" \
    --identity-name "${KAITO_IDENTITY_NAME}" \
    -g "${MC_RESOURCE_GROUP}" \
    --issuer "${AKS_OIDC_ISSUER}" \
    --subject system:serviceaccount:"kube-system:kaito-gpu-provisioner" \
    --audience api://AzureADTokenExchange
```

## Verify that your deployment is running

Restart the KAITO GPU provisioner deployment on your pods using the `kubectl rollout restart` command:

```bash
kubectl rollout restart deployment/kaito-gpu-provisioner -n kube-system
```

## Deploy a default hosted AI model

Deploy the Falcon 7B-instruct model from the KAITO model repository using the `kubectl apply` command.

```bash
kubectl apply -f https://raw.githubusercontent.com/Azure/kaito/main/examples/inference/kaito_workspace_falcon_7b-instruct.yaml
```

## Ask a question

Verify deployment done: `kubectl get workspace workspace-falcon-7b-instruct -w`.
Store IP: `export SERVICE_IP=$(kubectl get svc workspace-falcon-7b-instruct -o jsonpath='{.spec.clusterIP}')`.
Ask question: `kubectl run -it --rm --restart=Never curl --image=curlimages/curl -- curl -X POST http://$SERVICE_IP/chat -H "accept: application/json" -H "Content-Type: application/json" -d "{\"prompt\":\"YOUR QUESTION HERE\"}"`

```bash
echo "See last step for details on how to ask questions to the model.
```

## Next steps

For more inference model options, see the [KAITO GitHub repository](https://github.com/Azure/kaito).
