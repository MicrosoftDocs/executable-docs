---
title: Deploy an AI model on Azure Kubernetes Service (AKS) with the AI toolchain operator (preview)
description: Learn how to enable the AI toolchain operator add-on on Azure Kubernetes Service (AKS) to simplify OSS AI model management and deployment.
ms.topic: article
ms.custom: azure-kubernetes-service, devx-track-azurecli
ms.date: 02/28/2024
author: schaffererin
ms.author: schaffererin
---

## Deploy an AI model on Azure Kubernetes Service (AKS) with the AI toolchain operator (preview)


The AI toolchain operator (KAITO) is a managed add-on for AKS that simplifies the experience of running OSS AI models on your AKS clusters. The AI toolchain operator automatically provisions the necessary GPU nodes and sets up the associated inference server as an endpoint server to your AI models. Using this add-on reduces your onboarding time and enables you to focus on AI model usage and development rather than infrastructure setup.

This article shows you how to enable the AI toolchain operator add-on and deploy an AI model on AKS.

[!INCLUDE [preview features callout](~/reusable-content/ce-skilling/azure/includes/aks/includes/preview/preview-callout.md)]



## Before you start this step


* This article assumes a basic understanding of Kubernetes concepts. For more information, see [Kubernetes core concepts for AKS](./concepts-clusters-workloads.md).
* For ***all hosted model inference images*** and recommended infrastructure setup, see the [KAITO GitHub repository](https://github.com/Azure/kaito).
* The AI toolchain operator add-on currently supports KAITO version **v0.1.0**, please make a note of this in considering your choice of model from the KAITO model repository.



## Prerequisites


* If you don't have an Azure subscription, create a [free account](https://azure.microsoft.com/free/?WT.mc_id=A261C142F) before you begin.
  * If you have multiple Azure subscriptions, make sure you select the correct subscription in which the resources will be created and charged using the [az account set](https://learn.microsoft.com/en-us/cli/azure/account?view=azure-cli-latest#az-account-set) command.

    > [!NOTE]
    > The subscription you use must have GPU VM quota.

* Azure CLI version 2.47.0 or later installed and configured. Run azure-cli                         2.65.0 *

core                              2.65.0 *
telemetry                          1.1.0

Extensions:
ai-examples                        0.2.5
ml                                2.30.1
ssh                                2.0.5

Dependencies:
msal                              1.31.0
azure-mgmt-resource               23.1.1

Python location '/usr/bin/python3.9'
Extensions directory '/home/pj/.azure/cliextensions'
Extensions system directory '/usr/lib/python3.9/site-packages/azure-cli-extensions'

Python (Linux) 3.9.19 (main, Aug 23 2024, 00:07:48) 
[GCC 11.2.0]

Legal docs and information: aka.ms/AzureCliLegal to find the version. If you need to install or upgrade, see [Install Azure CLI](/cli/azure/install-azure-cli).
* The Kubernetes command-line client, kubectl, installed and configured. For more information, see [Install kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/).
* [Install the Azure CLI AKS preview extension](#install-the-azure-cli-preview-extension).
* [Register the AI toolchain operator add-on feature flag](#register-the-ai-toolchain-operator-add-on-feature-flag).



## Set up resource group


Set up a resource group with a random ID. Create an Azure resource group using the [az group create](https://learn.microsoft.com/en-us/cli/azure/group?view=azure-cli-latest#az-group-create) command.




```bash
export RANDOM_ID=c0d453
export AZURE_RESOURCE_GROUP=myKaitoResourceGroup
export REGION=centralus
export CLUSTER_NAME=myClusterName

az group create     --name      --location  
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
az feature register --namespace Microsoft.ContainerService --name AIToolchainOperatorPreview
```

## Verify the AI toolchain operator add-on registration


Verify the registration using the [az feature show](https://learn.microsoft.com/en-us/cli/azure/feature?view=azure-cli-latest#az-feature-show) command.




```bash
while true; do
    status=NotRegistered
    if [  == Registered ]; then
        break
    else
        sleep 15
    fi
done
```

## Create an AKS cluster with the AI toolchain operator add-on enabled


Create an AKS cluster with the AI toolchain operator add-on enabled using the [az aks create](https://learn.microsoft.com/en-us/cli/azure/aks?view=azure-cli-latest#az-aks-create) command with the  and  flags.




```bash
--enable-ai-toolchain-operator

--enable-oidc-issuer

az aks create --location      --resource-group      --name      --enable-oidc-issuer     --node-os-upgrade-channel SecurityPatch     --auto-upgrade-channel stable     --enable-ai-toolchain-operator     --generate-ssh-keys     --k8s-support-plan KubernetesOfficial
```

## Connect to your cluster


Configure kubectl controls the Kubernetes cluster manager.

 Find more information at: https://kubernetes.io/docs/reference/kubectl/

Basic Commands (Beginner):
  create          Create a resource from a file or from stdin
  expose          Take a replication controller, service, deployment or pod and expose it as a new Kubernetes service
  run             Run a particular image on the cluster
  set             Set specific features on objects

Basic Commands (Intermediate):
  explain         Get documentation for a resource
  get             Display one or many resources
  edit            Edit a resource on the server
  delete          Delete resources by file names, stdin, resources and names, or by resources and label selector

Deploy Commands:
  rollout         Manage the rollout of a resource
  scale           Set a new size for a deployment, replica set, or replication controller
  autoscale       Auto-scale a deployment, replica set, stateful set, or replication controller

Cluster Management Commands:
  certificate     Modify certificate resources
  cluster-info    Display cluster information
  top             Display resource (CPU/memory) usage
  cordon          Mark node as unschedulable
  uncordon        Mark node as schedulable
  drain           Drain node in preparation for maintenance
  taint           Update the taints on one or more nodes

Troubleshooting and Debugging Commands:
  describe        Show details of a specific resource or group of resources
  logs            Print the logs for a container in a pod
  attach          Attach to a running container
  exec            Execute a command in a container
  port-forward    Forward one or more local ports to a pod
  proxy           Run a proxy to the Kubernetes API server
  cp              Copy files and directories to and from containers
  auth            Inspect authorization
  debug           Create debugging sessions for troubleshooting workloads and nodes
  events          List events

Advanced Commands:
  diff            Diff the live version against a would-be applied version
  apply           Apply a configuration to a resource by file name or stdin
  patch           Update fields of a resource
  replace         Replace a resource by file name or stdin
  wait            Experimental: Wait for a specific condition on one or many resources
  kustomize       Build a kustomization target from a directory or URL

Settings Commands:
  label           Update the labels on a resource
  annotate        Update the annotations on a resource
  completion      Output shell completion code for the specified shell (bash, zsh, fish, or powershell)

Subcommands provided by plugins:

Other Commands:
  api-resources   Print the supported API resources on the server
  api-versions    Print the supported API versions on the server, in the form of "group/version"
  config          Modify kubeconfig files
  plugin          Provides utilities for interacting with plugins
  version         Print the client and server version information

Usage:
  kubectl [flags] [options]

Use "kubectl <command> --help" for more information about a given command.
Use "kubectl options" for a list of global command-line options (applies to all commands). to connect to your cluster using the [az aks get-credentials](https://learn.microsoft.com/en-us/cli/azure/aks?view=azure-cli-latest#az-aks-get-credentials) command.




```bash
kubectl

az aks get-credentials --resource-group  --name 
```

## Establish a federated identity credential


Create the federated identity credential between the managed identity, AKS OIDC issuer, and subject using the [az identity federated-credential create](https://learn.microsoft.com/en-us/cli/azure/identity/federated-credential?view=azure-cli-latest) command.




```bash
export MC_RESOURCE_GROUP=
export KAITO_IDENTITY_NAME=ai-toolchain-operator-
export AKS_OIDC_ISSUER=

az identity federated-credential create --name kaito-federated-identity     --identity-name      -g      --issuer      --subject system:serviceaccount:kube-system:kaito-gpu-provisioner     --audience api://AzureADTokenExchange
```

## Verify that your deployment is running


Restart the KAITO GPU provisioner deployment on your pods using the  command:




```bash
kubectl rollout restart

kubectl rollout restart deployment/kaito-gpu-provisioner -n kube-system
```

## Deploy a default hosted AI model


Deploy the Falcon 7B-instruct model from the KAITO model repository using the  command.




```bash
kubectl apply

kubectl apply -f https://raw.githubusercontent.com/Azure/kaito/main/examples/inference/kaito_workspace_falcon_7b-instruct.yaml
```

## Ask a question


Verify deployment done: .
Store IP: .
Ask question: 




```bash
kubectl get workspace workspace-falcon-7b-instruct -w

export SERVICE_IP=

kubectl run -it --rm --restart=Never curl --image=curlimages/curl -- curl -X POST http:///chat -H accept: application/json -H Content-Type: application/json -d {"prompt":"YOUR QUESTION HERE"}

echo See last step for details on how to ask questions to the model.
```

## Next steps


For more inference model options, see the [KAITO GitHub repository](https://github.com/Azure/kaito).




