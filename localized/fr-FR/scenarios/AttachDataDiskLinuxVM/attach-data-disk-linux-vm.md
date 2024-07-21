---
title: 'Démarrage rapide : Utiliser Azure CLI pour créer une machine virtuelle Ubuntu et attacher un disque de données Azure'
description: 'Dans ce guide de démarrage rapide, vous allez apprendre à utiliser Azure CLI pour créer une machine virtuelle Ubuntu Linux'
author: ajoian
ms.service: virtual-machines
ms.collection: linux
ms.topic: quickstart
ms.date: 07/10/2024
ms.author: ajoian
ms.custom: 'mvc, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Démarrage rapide : Utiliser Azure CLI pour créer une machine virtuelle Ubuntu et attacher un disque de données Azure

Ce guide de démarrage rapide vous montre comment utiliser Azure CLI pour déployer une machine virtuelle Linux Ubuntu dans Azure et attacher un disque de données Azure à la machine virtuelle. L’interface Azure CLI permet de créer et gérer des ressources Azure par le biais de la ligne de commande ou de scripts.

Si vous n’avez pas d’abonnement Azure, créez un [compte gratuit](https://azure.microsoft.com/free/?WT.mc_id=A261C142F) avant de commencer.

## Lancement d’Azure Cloud Shell

Azure Cloud Shell est un interpréteur de commandes interactif et gratuit que vous pouvez utiliser pour exécuter les étapes de cet article. Il contient des outils Azure courants préinstallés et configurés pour être utilisés avec votre compte.

Pour ouvrir Cloud Shell, sélectionnez simplement **Essayer** en haut à droite d’un bloc de code. Vous pouvez également ouvrir Cloud Shell dans un onglet distinct du navigateur en accédant à [https://shell.azure.com/bash](https://shell.azure.com/bash). Sélectionnez **Copier** pour copier les blocs de code, collez-les dans Cloud Shell et sélectionnez **Entrée** pour les exécuter.

Si vous préférez installer et utiliser l’interface de ligne de commande en local, ce démarrage rapide nécessite au minimum la version 2.0.30 d’Azure CLI. Exécutez `az --version` pour trouver la version. Si vous devez installer ou mettre à niveau, voir [Installer Azure CLI]( /cli/azure/install-azure-cli).

## Se connecter à Azure en tirant parti de l’interface CLI

Pour exécuter des commandes sur Azure en utilisant l’interface CLI, vous devez d’abord vous connecter. Connectez-vous à l’aide de la commande `az login`.

## Créer un groupe de ressources

Un groupe de ressources est un conteneur de ressources associées. Toutes les ressources doivent être placées dans un groupe de ressources. La commande [az group create](/cli/azure/group) crée un groupe de ressources avec les paramètres $MY_RESOURCE_GROUP_NAME et $REGION précédemment définis.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="LinuxRG-$RANDOM_ID"
export REGION="australiaeast"
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION -o JSON
```

Résultats :

<!-- expected_similarity=0.3 -->
```json
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/LinuxRG-xxxxxx",
  "location": "australiaeast",
  "managedBy": null,
  "name": "LinuxRG-xxxxxx",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Créer une machine virtuelle Linux Azure avec un disque de données

Le premier exemple suivant crée une machine virtuelle nommée `$MY_VM_NAME` et crée des clés SSH si elles n’existent pas déjà dans un emplacement de clé par défaut et crée un disque de données en tant que LUN0.

Pour améliorer la sécurité des machines virtuelles Linux dans Azure, vous pouvez intégrer l’authentification Azure Active Directory. Vous pouvez désormais utiliser Azure AD comme plateforme d’authentification principale. Vous pouvez également vous connecter en SSH à la machine virtuelle Linux à l'aide d'Azure AD et de l'authentification basée sur les certificats OpenSSH. Cette fonctionnalité permet aux organisations de gérer l’accès aux machines virtuelles avec le contrôle d’accès en fonction du rôle Azure et les stratégies d’accès conditionnel.

Créez une machine virtuelle avec la commande [az vm create](/cli/azure/vm#az-vm-create).

```bash
export ZONE="1"
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_VM_USERNAME="azureadmin"
export MY_VM_SIZE='Standard_D2s_v3'
export MY_VM_IMAGE='Canonical:ubuntu-24_04-lts:server:latest'
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
az vm create \
    --name $MY_VM_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --admin-username $MY_VM_USERNAME \
    --authentication-type ssh \
    --assign-identity \
    --image $MY_VM_IMAGE \
    --nsg-rule SSH \
    --public-ip-address-allocation static \
    --public-ip-address-dns-name $MY_DNS_LABEL \
    --public-ip-sku Standard \
    --nic-delete-option Delete \
    --accelerated-networking true \
    --storage-sku os=Premium_LRS 0=Premium_LRS \
    --os-disk-caching ReadWrite \
    --os-disk-delete-option Delete \
    --os-disk-size-gb 30 \
    --data-disk-caching ReadOnly \
    --data-disk-sizes-gb 128 \
    --data-disk-delete-option Detach \
    --size $MY_VM_SIZE \
    --generate-ssh-keys \
    --zone $ZONE -o JSON
```

Résultats :

<!-- expected_similarity=0.3 -->
```JSON
{
  "fqdns": "mydnslabelxxxxxx.australiaeast.cloudapp.azure.com",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/LinuxRG-a36f5d/providers/Microsoft.Compute/virtualMachines/myVMa36f5d",
  "identity": {
    "systemAssignedIdentity": "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy",
    "userAssignedIdentities": {}
  },
  "location": "australiaeast",
  "macAddress": "7C-1E-52-22-D8-72",
  "powerState": "VM running",
  "privateIpAddress": "10.0.0.4",
  "publicIpAddress": "xx.xx.xx.xx",
  "resourceGroup": "LinuxRG-a36f5d",
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
    --vm-name $MY_VM_NAME -o JSON
```

Résultats :

<!-- expected_similarity=0.3 -->
```JSON
{
  "autoUpgradeMinorVersion": true,
  "enableAutomaticUpgrade": null,
  "forceUpdateTag": null,
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/LinuxRG-a36f5d/providers/Microsoft.Compute/virtualMachines/myVMa36f5d/extensions/AADSSHLoginForLinux",
  "instanceView": null,
  "location": "australiaeast",
  "name": "AADSSHLoginForLinux",
  "protectedSettings": null,
  "protectedSettingsFromKeyVault": null,
  "provisionAfterExtensions": null,
  "provisioningState": "Succeeded",
  "publisher": "Microsoft.Azure.ActiveDirectory",
  "resourceGroup": "LinuxRG-a36f5d",
  "settings": null,
  "suppressFailures": null,
  "tags": null,
  "type": "Microsoft.Compute/virtualMachines/extensions",
  "typeHandlerVersion": "1.0",
  "typePropertiesType": "AADSSHLoginForLinux"
}
```

Dans ce scénario, le LUN0 de notre premier disque de données va être mis en forme et monté à l’aide de la commande ci-dessous :

```bash
export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo parted -s -a optimal -- /dev/disk/azure/scsi1/lun0 mklabel gpt mkpart primary xfs 0% 100%"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo partprobe -s /dev/disk/azure/scsi1/lun0"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkfs.xfs /dev/disk/azure/scsi1/lun0-part1"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkdir -v /datadisk01"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mount -v /dev/disk/azure/scsi1/lun0-part1 /datadisk01"
```

Résultats :

<!-- expected_similarity=0.3 -->
```text
/dev/sdc: gpt partitions 1
mke2fs 1.47.0 (5-Feb-2023)
Discarding device blocks: done
Creating filesystem with 33553920 4k blocks and 8388608 inodes
Filesystem UUID: 1095e29c-07db-47ec-8b19-1ffcaf4f5628
Superblock backups stored on blocks:
        32768, 98304, 163840, 229376, 294912, 819200, 884736, 1605632, 2654208,
        4096000, 7962624, 11239424, 20480000, 23887872

Allocating group tables: done
Writing inode tables: done
Creating journal (131072 blocks): done
Writing superblocks and filesystem accounting information: done

mkdir: created directory '/datadisk01'
mount: /dev/sdc1 mounted on /datadisk01.
```

Dans oder pour mettre à jour le fichier /etc/fstab, vous pouvez utiliser la commande suivante et monter le LUN1 à l’aide de son identificateur unique (UUID) avec l’option de montage ignorer :

```bash
ssh $MY_VM_USERNAME@$FQDN -- \
    'echo UUID=$(sudo blkid -s UUID -o value /dev/disk/azure/scsi1/lun0-part1) /datadisk01 xfs defaults,discard 0 0 | sudo tee -a /etc/fstab'
```

Résultats :

<!-- expected_similarity=0.3 -->
```text
UUID=1095e29c-07db-47ec-8b19-1ffcaf4f5628 /datadisk01 xfs defaults,discard 0 0
```

## Attacher un nouveau disque à une machine virtuelle

Si vous souhaitez ajouter un nouveau disque vide sur votre machine virtuelle, utilisez la commande [az vm disk attach](/cli/azure/vm/disk) avec le paramètre `--new`. Si votre machine virtuelle est dans une Zone de disponibilité, le disque est automatiquement créé dans la même zone que la machine virtuelle. Pour plus d'informations, consultez [Vue d’ensemble des zones de disponibilité](../../availability-zones/az-overview.md). L’exemple suivant crée un disque nommé *$LUN 2_NAME* de taille de 50 Go :

```bash
export LUN1_NAME="ZRS-$RANDOM_ID"
az vm disk attach \
    --new \
    --vm-name $MY_VM_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $LUN1_NAME \
    --sku Premium_ZRS \
    --caching None \
    --lun 1 \
    --size-gb 50
```

Dans ce deuxième scénario possible, le LUN1 va être notre disque de données, l’exemple suivant montre comment mettre en forme et monter le disque de données.

```bash
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo parted -s -a optimal -- /dev/disk/azure/scsi1/lun1 mklabel gpt mkpart primary xfs 0% 100%"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo partprobe -s /dev/disk/azure/scsi1/lun1"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkfs.xfs /dev/disk/azure/scsi1/lun1-part1"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkdir -v /datadisk02"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mount -v /dev/disk/azure/scsi1/lun1-part1 /datadisk02"
```

Résultats :

<!-- expected_similarity=0.3 -->
```text
/dev/sdd: gpt partitions 1
mke2fs 1.47.0 (5-Feb-2023)
Discarding device blocks: done
Creating filesystem with 13106688 4k blocks and 3276800 inodes
Filesystem UUID: 6e8ad233-5664-4f75-8ec6-3aa34f228868
Superblock backups stored on blocks:
        32768, 98304, 163840, 229376, 294912, 819200, 884736, 1605632, 2654208,
        4096000, 7962624, 11239424

Allocating group tables: done
Writing inode tables: done
Creating journal (65536 blocks): done
Writing superblocks and filesystem accounting information: done

mkdir: created directory '/datadisk02'
mount: /dev/sdd1 mounted on /datadisk02.
```

Dans oder pour mettre à jour le fichier /etc/fstab, vous pouvez utiliser la commande suivante et monter le LUN1 à l’aide de son identificateur unique (UUID) avec l’option de montage ignorer :

```bash
ssh $MY_VM_USERNAME@$FQDN -- \
    'echo "UUID=$(sudo blkid -s UUID -o value /dev/disk/azure/scsi1/lun1-part1) /datadisk02 xfs defaults,discard 0 0" | sudo tee -a /etc/fstab'
```

Résultats :

<!-- expected_similarity=0.3 -->
```text
UUID=0b1629d5-0cd5-41fd-9050-b2ed7e3f1028 /datadisk02 xfs defaults,discard 0 0
```

## Ajouter un disque de données existant à une machine virtuelle

Enfin, le troisième scénario consiste à attacher un disque existant à une machine virtuelle. Vous pouvez utiliser la [commande az vm disk attach](/cli/azure/vm/disk) avec le `--disk` paramètre pour attacher un disque existant à une machine virtuelle. L’exemple suivant attache un disque existant nommé *myDataDisk* à une machine virtuelle nommée *myVM* :

Commencez par créer un disque :

```bash
export LUN2_NAME="PSSDV2-$RANDOM_ID"
az disk create \
    --name $LUN2_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --size-gb 128 \
    --disk-iops-read-write 3000 \
    --disk-mbps-read-write 125 \
    --sku PremiumV2_LRS \
    --zone $ZONE \
    --performance-plus false \
    --public-network-access Disabled -o JSON
```

Résultats :

<!-- expected_similarity=0.3 -->
```JSON
{
  "encryptionSettingsCollection": null,
  "extendedLocation": null,
  "hyperVGeneration": null,
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/LinuxRG-e4c4b4/providers/Microsoft.Compute/disks/LUN2-e4c4b4",
  "lastOwnershipUpdateTime": null,
  "location": "australiaeast",
  "managedBy": null,
  "managedByExtended": null,
  "maxShares": 1,
  "name": "LUN2-e4c4b4",
  "networkAccessPolicy": "AllowAll",
  "optimizedForFrequentAttach": null,
  "osType": null,
  "propertyUpdatesInProgress": null,
  "provisioningState": "Succeeded",
  "publicNetworkAccess": "Disabled",
  "purchasePlan": null,
  "resourceGroup": "LinuxRG-e4c4b4",
  "securityProfile": null,
  "shareInfo": null,
  "sku": {
    "name": "PremiumV2_LRS",
    "tier": "Premium"
  }
}
```

Vous pouvez ensuite attacher le disque à la machine virtuelle :

```bash
LUN2_ID=$(az disk show --resource-group $MY_RESOURCE_GROUP_NAME --name $LUN2_NAME --query 'id' -o tsv)

az vm disk attach \
    --vm-name $MY_VM_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --disks $LUN2_ID \
    --sku PremiumV2_LRS \
    --lun 2
```

Dans ce troisième scénario, le LUN2 va être notre disque de données, l’exemple suivant montre comment mettre en forme et monter le disque de données.

```bash
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo parted -s -a optimal -- /dev/disk/azure/scsi1/lun2 mklabel gpt mkpart primary xfs 0% 100%"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo partprobe -s /dev/disk/azure/scsi1/lun2"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkfs.xfs /dev/disk/azure/scsi1/lun2-part1"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkdir -v /datadisk03"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mount -v /dev/disk/azure/scsi1/lun2-part1 /datadisk03"
```

Résultats :

<!-- expected_similarity=0.3 -->
```text
/dev/sde: gpt partitions 1
mke2fs 1.47.0 (5-Feb-2023)
Creating filesystem with 33553920 4k blocks and 8388608 inodes
Filesystem UUID: 0e0a110e-7d30-4235-ac4d-8ee59641e7c7
Superblock backups stored on blocks:
        32768, 98304, 163840, 229376, 294912, 819200, 884736, 1605632, 2654208,
        4096000, 7962624, 11239424, 20480000, 23887872

Allocating group tables: done
Writing inode tables: done
Creating journal (131072 blocks): done
Writing superblocks and filesystem accounting information: done

mkdir: created directory '/datadisk03'
mount: /dev/sde1 mounted on /datadisk03.
```

Dans oder pour mettre à jour le fichier /etc/fstab, vous pouvez utiliser la commande suivante et monter le LUN1 à l’aide de son identificateur unique (UUID) avec l’option de montage ignorer :

```bash
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- \
    'echo "UUID=$(sudo blkid -s UUID -o value /dev/disk/azure/scsi1/lun2-part1) /datadisk03 xfs defaults,discard 0 0" | sudo tee -a /etc/fstab'
```

Résultats :

<!-- expected_similarity=0.3 -->
```text
UUID=4b54ed3b-2f5e-4fe7-b0e5-c40da6e3b8a8 /datadisk03 xfs defaults,discard 0 0
```

## Vérifier tous les numéros d’unité logique montés

Pour vérifier les points de montage, vous pouvez utiliser la commande suivante :

```bash
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- mount | egrep '(datadisk)'
```

Résultats :

<!-- expected_similarity=0.3 -->
```text
/dev/sdc1 on /datadisk01 type xfs (rw,relatime)
/dev/sdd1 on /datadisk02 type xfs (rw,relatime)
/dev/sde1 on /datadisk03 type xfs (rw,relatime)
```

## Connectez-vous avec SSH à la machine virtuelle

Vous pouvez maintenant connecter SSH à la machine virtuelle en exécutant la commande suivante dans votre client ssh de votre choix :

```bash
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN
```

## Étapes suivantes

* [Découvrir les machines virtuelles](../index.yml)
* [Utiliser Cloud-Init pour initialiser une machine virtuelle Linux lors du premier démarrage](tutorial-automate-vm-deployment.md)
* [Créer des images de machine virtuelle personnalisées](tutorial-custom-images.md)
* [Équilibrer la charge des machines virtuelles](../../load-balancer/quickstart-load-balancer-standard-public-cli.md)
