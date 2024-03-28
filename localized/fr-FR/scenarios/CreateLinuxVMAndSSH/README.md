---
title: Créer une machine virtuelle Linux et SSH sur Azure
description: Ce tutoriel montre comment créer une machine virtuelle Linux et SSH sur Azure.
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Créer une machine virtuelle Linux et SSH sur Azure

[![Déployer dans Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262692)


## Définissez des variables d’environnement

La première étape de ce tutoriel définit des variables d’environnement.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
```

# Connectez-vous à Azure à l’aide de l’interface CLI

Pour exécuter des commandes sur Azure à l’aide de l’interface CLI, vous devez vous connecter. Pour cela, utilisez tout simplement la commande `az login` :

# Créer un groupe de ressources

Un groupe de ressources est un conteneur de ressources associées. Toutes les ressources doivent être placées dans un groupe de ressources. Nous en créons un pour ce tutoriel. La commande suivante crée un groupe de ressources avec les paramètres $MY_RESOURCE_GROUP_NAME et $REGION précédemment définis.

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

Pour créer une machine virtuelle dans ce groupe de ressources, nous devons exécuter une commande simple. Ici nous avons fourni l’indicateur `--generate-ssh-keys`, après quoi l’interface CLI recherche une clé SSH disponible dans `~/.ssh`. Si une telle clé est trouvée, elle sera utilisée, sinon elle sera générée et stockée dans `~/.ssh`. Nous fournissons également l’indicateur `--public-ip-sku Standard` pour nous assurer que l’ordinateur est accessible via une adresse IP publique. Enfin, nous déployons la dernière image `Ubuntu 22.04`. 

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

### Activer la connexion Azure AD pour une machine virtuelle Linux dans Azure

L’exemple suivant déploie une machine virtuelle, puis installe l’extension pour permettre la connexion Azure AD pour une machine virtuelle Linux. Les extensions de machine virtuelle sont de petites applications permettant d’exécuter des tâches de configuration et d’automatisation post-déploiement sur des machines virtuelles Azure.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

# Stocker l’adresse IP de la machine virtuelle pour SSH
exécuter la commande suivante pour obtenir l’adresse IP de la machine virtuelle et la stocker en tant que variable d’environnement

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

# Se connecter en SSH dans la machine virtuelle

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Login to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

Vous pouvez maintenant vous connecter en SSH à la machine virtuelle en exécutant la sortie de la commande suivante dans le client ssh de votre choix

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

# Étapes suivantes

* [Documentation sur les machines virtuelles](https://learn.microsoft.com/azure/virtual-machines/)
* [Utiliser Cloud-Init pour initialiser une machine virtuelle Linux lors du premier démarrage](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-automate-vm-deployment)
* [Créer des images de machine virtuelle personnalisées](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-custom-images)
* [Équilibrer la charge des machines virtuelles](https://learn.microsoft.com/azure/load-balancer/quickstart-load-balancer-standard-public-cli)
