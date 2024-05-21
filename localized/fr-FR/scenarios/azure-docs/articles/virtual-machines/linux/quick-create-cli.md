---
title: 'Démarrage rapide : utiliser l’interface Azure CLI pour créer une machine virtuelle Linux'
description: 'Dans ce guide de démarrage rapide, vous allez apprendre à utiliser Azure CLI pour créer une machine virtuelle Linux'
author: ju-shim
ms.service: virtual-machines
ms.collection: linux
ms.topic: quickstart
ms.date: 03/11/2024
ms.author: jushiman
ms.custom: 'mvc, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Démarrage rapide : Créer une machine virtuelle Linux avec Azure CLI sur Azure

**S’applique à :** :heavy_check_mark : machines virtuelles Linux

[![Déployer dans Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262692)

Ce démarrage rapide explique comment utiliser Azure CLI pour déployer dans Azure une machine virtuelle Linux. L’interface Azure CLI permet de créer et gérer des ressources Azure par le biais de la ligne de commande ou de scripts.

Si vous n’avez pas d’abonnement Azure, créez un [compte gratuit](https://azure.microsoft.com/free/?WT.mc_id=A261C142F) avant de commencer.

## Lancement d’Azure Cloud Shell

Azure Cloud Shell est un interpréteur de commandes interactif et gratuit que vous pouvez utiliser pour exécuter les étapes de cet article. Il contient des outils Azure courants préinstallés et configurés pour être utilisés avec votre compte. 

Pour ouvrir Cloud Shell, sélectionnez simplement **Essayer** en haut à droite d’un bloc de code. Vous pouvez également ouvrir Cloud Shell dans un onglet distinct du navigateur en accédant à [https://shell.azure.com/bash](https://shell.azure.com/bash). Sélectionnez **Copier** pour copier les blocs de code, collez-les dans Cloud Shell et sélectionnez **Entrée** pour les exécuter.

Si vous préférez installer et utiliser l’interface de ligne de commande en local, ce démarrage rapide nécessite au minimum la version 2.0.30 d’Azure CLI. Exécutez `az --version` pour trouver la version. Si vous devez installer ou mettre à niveau, voir [Installer Azure CLI]( /cli/azure/install-azure-cli).

## Définissez des variables d’environnement

La première étape consiste à définir les variables d’environnement. Les variables d’environnement sont couramment utilisées dans Linux pour centraliser les données de configuration afin d’améliorer la cohérence et la maintenance du système. Créez les variables d’environnement suivantes pour spécifier les noms des ressources que vous créez plus loin dans ce tutoriel :

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
```

## Se connecter à Azure en tirant parti de l’interface CLI

Pour exécuter des commandes sur Azure en utilisant l’interface CLI, vous devez d’abord vous connecter. Connectez-vous à l’aide de la commande `az login`.

## Créer un groupe de ressources

Un groupe de ressources est un conteneur de ressources associées. Toutes les ressources doivent être placées dans un groupe de ressources. La commande [az group create](/cli/azure/group) crée un groupe de ressources avec les paramètres $MY_RESOURCE_GROUP_NAME et $REGION précédemment définis.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Résultats :

<!-- expected_similarity=0.3 -->
```json
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMResourceGroup",
  "location": "eastus",
  "managedBy": null,
  "name": "myVMResourceGroup",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Créer la machine virtuelle

Pour créer une machine virtuelle dans ce groupe de ressources, utilisez la commande `vm create`. 

L’exemple suivant crée une machine virtuelle et ajoute un compte d’utilisateur. Le paramètre `--generate-ssh-keys` fait en sorte que le CLI recherche une clé ssh disponible dans `~/.ssh`. Si une clé est trouvée, cette clé est utilisée. Sinon, une clé est générée et stockée dans `~/.ssh`. Le paramètre `--public-ip-sku Standard` garantit que l’ordinateur est accessible via une adresse IP publique. Enfin, nous déployons l’image `Ubuntu 22.04` la plus récente.

Toutes les autres valeurs sont configurées à l’aide de variables d’environnement.

```bash
az vm create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_VM_NAME \
    --image $MY_VM_IMAGE \
    --admin-username $MY_USERNAME \
    --assign-identity \
    --generate-ssh-keys \
    --public-ip-sku Standard
```

La création de la machine virtuelle et des ressources de support ne nécessite que quelques minutes. L’exemple de sortie suivant illustre la réussite de l’opération de création d’une machine virtuelle.

Résultats :
<!-- expected_similarity=0.3 -->
```json
{
  "fqdns": "",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMResourceGroup/providers/Microsoft.Compute/virtualMachines/myVM",
  "location": "eastus",
  "macAddress": "00-0D-3A-10-4F-70",
  "powerState": "VM running",
  "privateIpAddress": "10.0.0.4",
  "publicIpAddress": "52.147.208.85",
  "resourceGroup": "myVMResourceGroup",
  "zones": ""
}
```

## Activer la connexion Azure AD pour une machine virtuelle Linux dans Azure

Le code suivant déploie une machine virtuelle Linux, puis installe l’extension pour permettre la connexion Azure AD pour une machine virtuelle Linux. Les extensions de machine virtuelle sont de petites applications permettant d’exécuter des tâches de configuration et d’automatisation post-déploiement sur des machines virtuelles Azure.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

## Stocker l’adresse IP d’une machine virtuelle pour une connexion SSH

Exécutez la commande suivante pour stocker l’adresse IP de la machine virtuelle en tant que variable d’environnement :

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

## Connectez-vous avec SSH à la machine virtuelle

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Log in to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

Vous pouvez maintenant établir une connexion SSH à la machine virtuelle en exécutant la sortie de la commande suivante dans le client SSH de votre choix :

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

## Étapes suivantes

* [Découvrir les machines virtuelles](../index.yml)
* [Utiliser Cloud-Init pour initialiser une machine virtuelle Linux lors du premier démarrage](tutorial-automate-vm-deployment.md)
* [Créer des images de machine virtuelle personnalisées](tutorial-custom-images.md)
* [Équilibrer la charge des machines virtuelles](../../load-balancer/quickstart-load-balancer-standard-public-cli.md)
