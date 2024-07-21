---
title: 'Schnellstart: Verwenden der Azure CLI zum Erstellen eines virtuellen Ubuntu-Computers und Anfügen eines Azure-Datenträgers'
description: 'In dieser Schnellstartanleitung erfahren Sie, wie Sie die Azure CLI zum Erstellen eines virtuellen Ubuntu-Linux-Computers verwenden.'
author: ajoian
ms.service: virtual-machines
ms.collection: linux
ms.topic: quickstart
ms.date: 07/10/2024
ms.author: ajoian
ms.custom: 'mvc, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Schnellstart: Verwenden der Azure CLI zum Erstellen eines virtuellen Ubuntu-Computers und Anfügen eines Azure-Datenträgers

In dieser Schnellstartanleitung erfahren Sie, wie Sie die Azure CLI verwenden, um einen virtuellen Ubuntu-Linux-Computer (VM) in Azure bereitzustellen und einen Azure-Datenträger an den virtuellen Computer anzufügen. Die Azure-Befehlszeilenschnittstelle dient zum Erstellen und Verwalten von Azure-Ressourcen über die Befehlszeile oder mit Skripts.

Wenn Sie kein Azure-Abonnement besitzen, können Sie ein [kostenloses Konto](https://azure.microsoft.com/free/?WT.mc_id=A261C142F) erstellen, bevor Sie beginnen.

## Starten von Azure Cloud Shell

Azure Cloud Shell ist eine kostenlose interaktive Shell, mit der Sie die Schritte in diesem Artikel durchführen können. Sie verfügt über allgemeine vorinstallierte Tools und ist für die Verwendung mit Ihrem Konto konfiguriert.

Wählen Sie zum Öffnen von Cloud Shell oben rechts in einem Codeblock einfach die Option **Ausprobieren**. Sie können Cloud Shell auch auf einer separaten Browserregisterkarte öffnen, indem Sie zu [https://shell.azure.com/bash](https://shell.azure.com/bash) navigieren. Wählen Sie **Kopieren** aus, um die Codeblöcke zu kopieren. Fügen Sie die Blöcke anschließend in Cloud Shell ein, und wählen Sie **Eingabe**, um sie auszuführen.

Wenn Sie es vorziehen, die Befehlszeilenschnittstelle lokal zu installieren und zu verwenden, müssen Sie für diese Schnellstartanleitung mindestens Azure CLI-Version 2.0.30 verwenden. Führen Sie `az --version` aus, um die Version zu ermitteln. Informationen zum Durchführen einer Installation oder eines Upgrades finden Sie bei Bedarf unter [Installieren der Azure CLI]( /cli/azure/install-azure-cli).

## Melden Sie sich mit der CLI bei Azure an

Um Befehle in Azure mithilfe der CLI auszuführen, müssen Sie sich zuerst anmelden. Melden Sie sich mit dem Befehl `az login` an.

## Erstellen einer Ressourcengruppe

Eine Ressourcengruppe ist ein Container für zugehörige Ressourcen. Alle Ressourcen müssen in einer Ressourcengruppe platziert werden. Mit dem Befehl [az group create](/cli/azure/group) wird eine Ressourcengruppe mit den zuvor definierten Parametern $MY_RESOURCE_GROUP_NAME und $REGION erstellt.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="LinuxRG-$RANDOM_ID"
export REGION="australiaeast"
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION -o JSON
```

Ergebnisse:

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

## Erstellen eines virtuellen Azure Linux-Computers mit einem Datenträger

Im folgenden ersten Beispiel wird eine VM namens `$MY_VM_NAME` erstellt und SSH-Schlüssel erstellt, wenn sie noch nicht an einem Standardschlüsselspeicherort vorhanden sind und einen Datenträger als LUN0 erstellen.

Zur Verbesserung der Sicherheit von Linux-VMs in Azure können Sie die Integration in die Azure Active Directory-Authentifizierung durchführen. Sie können jetzt Azure AD als zentrale Authentifizierungsplattform verwenden. Sie können auch mithilfe von Azure AD und der zertifikatbasierten OpenSSH-Authentifizierung eine SSH-Verbindung mit einem virtuellen Linux-Computer herstellen. Mit dieser Funktion können Organisationen den Zugriff auf VMs mit der rollenbasierten Zugriffssteuerung (Role-Based Access Control, RBAC) von Azure und Richtlinien für bedingten Zugriff verwalten.

Erstellen Sie mit dem Befehl [az vm create](/cli/azure/vm#az-vm-create) einen virtuellen Computer.

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

Ergebnisse:

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

## Aktivieren der Azure AD-Anmeldung für eine Linux-VM in Azure

Im folgenden Codebeispiel wird eine Linux-VM bereitgestellt und dann die Erweiterung installiert, um die Azure AD-Anmeldung für eine Linux-VM zu aktivieren. VM-Erweiterungen sind kleine Anwendungen, die Konfigurations- und Automatisierungsaufgaben auf virtuellen Azure-Computern nach der Bereitstellung ermöglichen.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME -o JSON
```

Ergebnisse:

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

In diesem Szenario wird die LUN0 unser erster Datenträger mit dem folgenden Befehl formatiert und bereitgestellt:

```bash
export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo parted -s -a optimal -- /dev/disk/azure/scsi1/lun0 mklabel gpt mkpart primary xfs 0% 100%"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo partprobe -s /dev/disk/azure/scsi1/lun0"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkfs.xfs /dev/disk/azure/scsi1/lun0-part1"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkdir -v /datadisk01"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mount -v /dev/disk/azure/scsi1/lun0-part1 /datadisk01"
```

Ergebnisse:

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

Um die Datei "/etc/fstab" zu aktualisieren, können Sie den folgenden Befehl verwenden und die LUN1 mit dem eindeutigen Bezeichner (UUID) zusammen mit der Option "Mount verwerfen" bereitstellen:

```bash
ssh $MY_VM_USERNAME@$FQDN -- \
    'echo UUID=$(sudo blkid -s UUID -o value /dev/disk/azure/scsi1/lun0-part1) /datadisk01 xfs defaults,discard 0 0 | sudo tee -a /etc/fstab'
```

Ergebnisse:

<!-- expected_similarity=0.3 -->
```text
UUID=1095e29c-07db-47ec-8b19-1ffcaf4f5628 /datadisk01 xfs defaults,discard 0 0
```

## Anfügen eines neuen Datenträgers an einen virtuellen Computer

Wenn Sie einen neuen, leeren Datenträger für Ihren virtuellen Computer hinzufügen möchten, verwenden Sie den Befehl [az vm disk attach](/cli/azure/vm/disk) mit dem `--new`-Parameter. Wenn Ihr virtueller Computer in einer Verfügbarkeitszone ist, wird der Datenträger automatisch in derselben Zone wie der virtuelle Computer erstellt. Weitere Informationen finden Sie in der [Overview of Availability Zones (Übersicht über Verfügbarkeitszonen)](../../availability-zones/az-overview.md). Im folgenden Beispiel wird ein Datenträger mit dem Namen *$LUN 2_NAME* erstellt, der 50 GB groß ist:

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

In diesem zweiten möglichen Szenario wird die LUN1 unser Datenträger sein, das folgende Beispiel zeigt, wie sie den Datenträger formatieren und bereitstellen.

```bash
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo parted -s -a optimal -- /dev/disk/azure/scsi1/lun1 mklabel gpt mkpart primary xfs 0% 100%"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo partprobe -s /dev/disk/azure/scsi1/lun1"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkfs.xfs /dev/disk/azure/scsi1/lun1-part1"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkdir -v /datadisk02"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mount -v /dev/disk/azure/scsi1/lun1-part1 /datadisk02"
```

Ergebnisse:

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

Um die Datei "/etc/fstab" zu aktualisieren, können Sie den folgenden Befehl verwenden und die LUN1 mit dem eindeutigen Bezeichner (UUID) zusammen mit der Option "Mount verwerfen" bereitstellen:

```bash
ssh $MY_VM_USERNAME@$FQDN -- \
    'echo "UUID=$(sudo blkid -s UUID -o value /dev/disk/azure/scsi1/lun1-part1) /datadisk02 xfs defaults,discard 0 0" | sudo tee -a /etc/fstab'
```

Ergebnisse:

<!-- expected_similarity=0.3 -->
```text
UUID=0b1629d5-0cd5-41fd-9050-b2ed7e3f1028 /datadisk02 xfs defaults,discard 0 0
```

## Hinzufügen eines vorhandenen Datenträgers zu einem virtuellen Computer

Schließlich besteht das dritte Szenario darin, einen vorhandenen Datenträger an einen virtuellen Computer anzufügen. Sie können den [Befehl "az vm disk attach"](/cli/azure/vm/disk) mit dem `--disk` Parameter verwenden, um einen vorhandenen Datenträger an eine VM anzufügen. Im folgenden Beispiel wird ein vorhandener Datenträger mit dem Namen "myDataDisk *" an eine VM mit *dem Namen *"myVM*" angefügt:

Zunächst können Sie beginnen, indem Sie einen neuen Datenträger erstellen:

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

Ergebnisse:

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

Anschließend können Sie den Datenträger an die VM anfügen:

```bash
LUN2_ID=$(az disk show --resource-group $MY_RESOURCE_GROUP_NAME --name $LUN2_NAME --query 'id' -o tsv)

az vm disk attach \
    --vm-name $MY_VM_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --disks $LUN2_ID \
    --sku PremiumV2_LRS \
    --lun 2
```

In diesem dritten Szenario wird die LUN2 unser Datenträger sein, das folgende Beispiel zeigt, wie sie den Datenträger formatieren und bereitstellen.

```bash
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo parted -s -a optimal -- /dev/disk/azure/scsi1/lun2 mklabel gpt mkpart primary xfs 0% 100%"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo partprobe -s /dev/disk/azure/scsi1/lun2"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkfs.xfs /dev/disk/azure/scsi1/lun2-part1"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkdir -v /datadisk03"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mount -v /dev/disk/azure/scsi1/lun2-part1 /datadisk03"
```

Ergebnisse:

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

Um die Datei "/etc/fstab" zu aktualisieren, können Sie den folgenden Befehl verwenden und die LUN1 mit dem eindeutigen Bezeichner (UUID) zusammen mit der Option "Mount verwerfen" bereitstellen:

```bash
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- \
    'echo "UUID=$(sudo blkid -s UUID -o value /dev/disk/azure/scsi1/lun2-part1) /datadisk03 xfs defaults,discard 0 0" | sudo tee -a /etc/fstab'
```

Ergebnisse:

<!-- expected_similarity=0.3 -->
```text
UUID=4b54ed3b-2f5e-4fe7-b0e5-c40da6e3b8a8 /datadisk03 xfs defaults,discard 0 0
```

## Überprüfen aller bereitgestellten LUNs

Um die Bereitstellungspunkte zu überprüfen, können Sie den folgenden Befehl verwenden:

```bash
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- mount | egrep '(datadisk)'
```

Ergebnisse:

<!-- expected_similarity=0.3 -->
```text
/dev/sdc1 on /datadisk01 type xfs (rw,relatime)
/dev/sdd1 on /datadisk02 type xfs (rw,relatime)
/dev/sde1 on /datadisk03 type xfs (rw,relatime)
```

## Stellen Sie eine SSH-Verbindung mit der VM her.

Sie können nun SSH auf dem virtuellen Computer ausführen, indem Sie den folgenden Befehl in Ihrem ssh-Client der Wahl ausführen:

```bash
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN
```

## Nächste Schritte

* [Weitere Informationen zu VMs](../index.yml)
* [Verwenden von Cloud-Init zum Initialisieren einer Linux-VM beim ersten Start](tutorial-automate-vm-deployment.md)
* [Erstellen von benutzerdefinierten VM-Images](tutorial-custom-images.md)
* [Lastenausgleich für virtuelle Computer](../../load-balancer/quickstart-load-balancer-standard-public-cli.md)
