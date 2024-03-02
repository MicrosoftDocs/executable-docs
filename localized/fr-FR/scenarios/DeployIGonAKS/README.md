---
title: "Déployez Inspektor\_Gadget dans un cluster Azure\_Kubernetes\_Service"
description: "Ce tutoriel montre comment déployer Inspektor\_Gadget dans un cluster AKS"
author: josebl
ms.author: josebl
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Démarrage rapide : déployer Inspektor Gadget dans un cluster Azure Kubernetes Service

Bienvenue dans ce tutoriel au cours duquel nous allons vous accompagner pas à pas dans le déploiement d’[Inspektor Gadget](https://www.inspektor-gadget.io/) dans un cluster Azure Kubernetes Service (AKS) à l’aide du plug-in kubectl : `gadget`. Ce tutoriel suppose que vous êtes déjà connecté à Azure CLI et que vous avez sélectionné un abonnement à utiliser avec l’interface CLI.

## Définissez des variables d’environnement

La première étape de ce tutoriel consiste à définir des variables d’environnement :

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myResourceGroup$RANDOM_ID"
export REGION="eastus"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
```

## Créer un groupe de ressources

Un groupe de ressources est un conteneur de ressources associées. Toutes les ressources doivent être placées dans un groupe de ressources. Nous en créons un pour ce tutoriel. La commande suivante crée un groupe de ressources avec les paramètres $MY_RESOURCE_GROUP_NAME et $REGION précédemment définis.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Résultats :

<!-- expected_similarity=0.3 -->
```JSON
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myResourceGroup210",
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

## Créer un cluster AKS

Créez un cluster AKS avec la commande az aks create.

Cette opération prendra quelques minutes.

```bash
az aks create \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --name $MY_AKS_CLUSTER_NAME \
  --location $REGION \
  --no-ssh-key
```

## Se connecter au cluster

Pour gérer un cluster Kubernetes, utilisez kubectl, le client de ligne de commande Kubernetes. Kubectl est déjà installé si vous utilisez Azure Cloud Shell.

1. Installez l’interface CLI az aks localement avec la commande az aks install-cli

    ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
    ```

2. Configurez kubectl pour vous connecter à votre cluster Kubernetes à l’aide de la commande aks get-credentials. La commande ci-après effectue les opérations suivantes :
    - Cette étape télécharge les informations d’identification et configure l’interface de ligne de commande Kubernetes pour leur utilisation.
    - Utilise ~/.kube/config, emplacement par défaut du fichier de configuration Kubernetes. Spécifiez un autre emplacement pour votre fichier de configuration Kubernetes à l’aide de l’argument --file.

    > [!WARNING]
    > Cela remplace toutes les informations d’identification existantes par la même entrée

    ```bash
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
    ```

3. Pour vérifier la connexion à votre cluster, exécutez la commande kubectl get. Cette commande renvoie la liste des nœuds de cluster.

    ```bash
    kubectl get nodes
    ```

## Installez Inspektor Gadget

L’installation d’Inspektor Gadget se compose de deux étapes :

1. Installation du plug-in kubectl dans le système de l’utilisateur.
2. Installation d’Inspektor Gadget dans le cluster.

    > [!NOTE]
    > Il existe des mécanismes supplémentaires pour le déploiement et l’utilisation d’Inspektor Gadget, chacun étant adapté à des cas d’usage et à des exigences spécifiques. L’utilisation du plug-in `kubectl gadget` couvre la plupart d’entre eux, mais pas tous. Par exemple, le déploiement d’Inspektor Gadget avec le plug-in `kubectl gadget` dépend de la disponibilité du serveur d’API Kubernetes. Par conséquent, si vous ne pouvez pas dépendre d’un tel composant, car sa disponibilité peut parfois être compromise, il est recommandé de ne pas utiliser le mécanisme de `kubectl gadget`déploiement. Veuillez consulter la [documentation ig](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/ig.md) pour savoir ce qu’il faut faire dans ce cas, et dans d’autres cas d’usage.

### Installation du plug-in kubectl : `gadget`

Installez la dernière version du plug-in kubectl à partir de la page des versions, décompressez et déplacez l’exécutable `kubectl-gadget` vers `$HOME/.local/bin` :

> [!NOTE]
> Si vous souhaitez l’installer à l’aide de [`krew`](https://sigs.k8s.io/krew) ou le compiler à partir des sources, veuillez suivre la documentation officielle : [installation de kubectl gadget](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-kubectl-gadget).

```bash
IG_VERSION=$(curl -s https://api.github.com/repos/inspektor-gadget/inspektor-gadget/releases/latest | jq -r .tag_name)
IG_ARCH=amd64
mkdir -p $HOME/.local/bin
export PATH=$PATH:$HOME/.local/bin
curl -sL https://github.com/inspektor-gadget/inspektor-gadget/releases/download/${IG_VERSION}/kubectl-gadget-linux-${IG_ARCH}-${IG_VERSION}.tar.gz  | tar -C $HOME/.local/bin -xzf - kubectl-gadget
```

Maintenant, vérifions l’installation en exécutant la commande `version` :

```bash
kubectl gadget version
```

La commande `version` affichera la version du client (plug-in kubectl gadget) et indiquera qu’elle n’est pas encore installée sur le serveur (le cluster) :

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: not installed$"-->
```text
Client version: vX.Y.Z
Server version: not installed
```

### Installation d’Inspektor Gadget dans le cluster

La commande suivante déploiera le DaemonSet :

> [!NOTE]
> Plusieurs options sont disponibles pour personnaliser le déploiement : utiliser une image conteneur spécifique, déployer sur des nœuds spécifiques et bien d’autres. Pour en savoir plus, consultez la documentation officielle : [installation dans le cluster](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-in-the-cluster).

```bash
kubectl gadget deploy
```

Maintenant, vérifions l’installation en exécutant à nouveau la commande `version` :

```bash
kubectl gadget version
```

Cette fois, le client et le serveur seront correctement installés :

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: v\d+\.\d+\.\d+$"-->
```text
Client version: vX.Y.Z
Server version: vX.Y.Z
```

Vous pouvez maintenant commencer à exécuter les gadgets :

```bash
kubectl gadget help
```

<!--
## Clean Up

### Undeploy Inspektor Gadget

```bash
kubectl gadget undeploy
```

### Clean up Azure resources

When no longer needed, you can use `az group delete` to remove the resource group, cluster, and all related resources as follows. The `--no-wait` parameter returns control to the prompt without waiting for the operation to complete. The `--yes` parameter confirms that you wish to delete the resources without an additional prompt to do so.

```bash
az group delete --name $MY_RESOURCE_GROUP_NAME --no-wait --yes
```
-->

## Étapes suivantes
- [Scénarios pratiques dans lesquels Inspektor Gadget peut vous aider](https://go.microsoft.com/fwlink/p/?linkid=2260402#use-cases)
- [Explorer les gadgets disponibles](https://go.microsoft.com/fwlink/p/?linkid=2260070)
- [Exécuter votre propre programme eBPF](https://go.microsoft.com/fwlink/p/?linkid=2259865)
