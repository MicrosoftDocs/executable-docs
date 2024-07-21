---
title: 'Rövid útmutató: Ubuntu virtuális gép létrehozása és Azure Data Disk csatolása az Azure CLI használatával'
description: 'Ebben a rövid útmutatóban megtudhatja, hogyan hozhat létre Ubuntu Linux rendszerű virtuális gépet az Azure CLI használatával'
author: ajoian
ms.service: virtual-machines
ms.collection: linux
ms.topic: quickstart
ms.date: 07/10/2024
ms.author: ajoian
ms.custom: 'mvc, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Rövid útmutató: Ubuntu virtuális gép létrehozása és Azure Data Disk csatolása az Azure CLI használatával

Ez a rövid útmutató bemutatja, hogyan helyezhet üzembe Ubuntu Linux rendszerű virtuális gépet (VM-et) az Azure CLI használatával, és hogyan csatolhat Azure Data Disket a virtuális géphez. Az Azure CLI használatával azure-erőforrások hozhatók létre és kezelhetők parancssoron vagy szkripteken keresztül.

Ha még nincs Azure-előfizetése, kezdés előtt hozzon létre egy [ingyenes fiókot](https://azure.microsoft.com/free/?WT.mc_id=A261C142F).

## Az Azure Cloud Shell elindítása

Az Azure Cloud Shell egy olyan ingyenes interaktív kezelőfelület, amelyet a jelen cikkben található lépések futtatására használhat. A fiókjával való használat érdekében a gyakran használt Azure-eszközök már előre telepítve és konfigurálva vannak rajta.

A Cloud Shell megnyitásához válassza a **Kipróbálás** lehetőséget egy kódblokk jobb felső sarkában. A Cloud Shellt külön böngészőlapon is megnyithatja a következő lépéssel [https://shell.azure.com/bash](https://shell.azure.com/bash): Válassza **a Másolás** lehetőséget a kódblokkok másolásához, illessze be a Cloud Shellbe, majd az Enter** gombra kattintva **futtassa.

Ha a parancssori felület helyi telepítését és használatát választja, akkor ehhez a rövid útmutatóhoz az Azure CLI 2.0.30-es vagy újabb verziójára lesz szükség. A verzió azonosításához futtassa a következőt: `az --version`. Ha telepíteni vagy frissíteni szeretne: [Az Azure CLI telepítése]( /cli/azure/install-azure-cli).

## Bejelentkezés az Azure-ba a parancssori felület használatával

Ahhoz, hogy parancsokat futtasson az Azure-ban a parancssori felület használatával, először be kell jelentkeznie. Jelentkezzen be a `az login` parancs használatával.

## Erőforráscsoport létrehozása

Az erőforráscsoportok a kapcsolódó erőforrások tárolói. Minden erőforrást egy erőforráscsoportba kell helyezni. Az [az group create](/cli/azure/group) parancs létrehoz egy erőforráscsoportot a korábban definiált $MY_RESOURCE_GROUP_NAME és $REGION paraméterekkel.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="LinuxRG-$RANDOM_ID"
export REGION="australiaeast"
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION -o JSON
```

Eredmények:

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

## Azure Linux rendszerű virtuális gép létrehozása adatlemezzel

Az alábbi első példa létrehoz egy elnevezett `$MY_VM_NAME` virtuális gépet, és SSH-kulcsokat hoz létre, ha még nem léteznek alapértelmezett kulcshelyen, és lun0-ként hoz létre adatlemezt.

Az Azure-beli Linux rendszerű virtuális gépek biztonságának javítása érdekében integrálható az Azure Active Directory-hitelesítéssel. Mostantól az Azure AD-t használhatja alapszintű hitelesítési platformként. Az Azure AD és az OpenSSH tanúsítványalapú hitelesítéssel SSH-t is használhat a Linux rendszerű virtuális gépre. Ez a funkció lehetővé teszi a szervezetek számára, hogy azure-beli szerepköralapú hozzáférés-vezérlési és feltételes hozzáférési szabályzatokkal kezeljék a virtuális gépekhez való hozzáférést.

Hozzon létre egy virtuális gépet az [az vm create](/cli/azure/vm#az-vm-create) paranccsal.

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

Eredmények:

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

## Azure AD-bejelentkezés engedélyezése Linux rendszerű virtuális gépekhez az Azure-ban

Az alábbi példakód egy Linux rendszerű virtuális gépet helyez üzembe, majd telepíti a bővítményt, hogy engedélyezze az Azure AD-bejelentkezést linuxos virtuális gépeken. A virtuálisgép-bővítmények olyan kis alkalmazások, amelyek üzembe helyezés utáni konfigurációs és automatizálási feladatokat biztosítanak az Azure-beli virtuális gépeken.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME -o JSON
```

Eredmények:

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

Ebben a forgatókönyvben az első adatlemez lun0 formátuma és csatlakoztatása az alábbi paranccsal történik:

```bash
export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo parted -s -a optimal -- /dev/disk/azure/scsi1/lun0 mklabel gpt mkpart primary xfs 0% 100%"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo partprobe -s /dev/disk/azure/scsi1/lun0"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkfs.xfs /dev/disk/azure/scsi1/lun0-part1"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkdir -v /datadisk01"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mount -v /dev/disk/azure/scsi1/lun0-part1 /datadisk01"
```

Eredmények:

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

Az oderben a /etc/fstab fájl frissítéséhez használhatja a következő parancsot, és csatlakoztathatja a LUN1-et az egyedi azonosító (UUID) használatával az elvetett csatlakoztatási beállítással együtt:

```bash
ssh $MY_VM_USERNAME@$FQDN -- \
    'echo UUID=$(sudo blkid -s UUID -o value /dev/disk/azure/scsi1/lun0-part1) /datadisk01 xfs defaults,discard 0 0 | sudo tee -a /etc/fstab'
```

Eredmények:

<!-- expected_similarity=0.3 -->
```text
UUID=1095e29c-07db-47ec-8b19-1ffcaf4f5628 /datadisk01 xfs defaults,discard 0 0
```

## Új lemez csatolása virtuális géphez

Ha új, üres adatlemezt szeretne hozzáadni a virtuális géphez, használja az [az vm disk attach](/cli/azure/vm/disk) parancsot a `--new` paraméterrel. Ha a virtuális gép rendelkezésre állási zónában van, a rendszer automatikusan a virtuális géppel azonos zónában hozza létre a lemezt. További információ: [A rendelkezésre állási zónák](../../availability-zones/az-overview.md) áttekintése. Az alábbi példa egy 50 Gb méretű $LUN 2_NAME* nevű *lemezt hoz létre:

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

Ebben a második lehetséges forgatókönyvben a LUN1 lesz az adatlemezünk, az alábbi példa az adatlemez formázását és csatlakoztatását mutatja be.

```bash
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo parted -s -a optimal -- /dev/disk/azure/scsi1/lun1 mklabel gpt mkpart primary xfs 0% 100%"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo partprobe -s /dev/disk/azure/scsi1/lun1"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkfs.xfs /dev/disk/azure/scsi1/lun1-part1"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkdir -v /datadisk02"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mount -v /dev/disk/azure/scsi1/lun1-part1 /datadisk02"
```

Eredmények:

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

Az oderben a /etc/fstab fájl frissítéséhez használhatja a következő parancsot, és csatlakoztathatja a LUN1-et az egyedi azonosító (UUID) használatával az elvetett csatlakoztatási beállítással együtt:

```bash
ssh $MY_VM_USERNAME@$FQDN -- \
    'echo "UUID=$(sudo blkid -s UUID -o value /dev/disk/azure/scsi1/lun1-part1) /datadisk02 xfs defaults,discard 0 0" | sudo tee -a /etc/fstab'
```

Eredmények:

<!-- expected_similarity=0.3 -->
```text
UUID=0b1629d5-0cd5-41fd-9050-b2ed7e3f1028 /datadisk02 xfs defaults,discard 0 0
```

## Meglévő adatlemez csatolása virtuális géphez

Végül a harmadik forgatókönyv az, hogy egy meglévő lemezt csatol egy virtuális géphez. Az az vm disk attach[ paranccsal a `--disk` paraméterrel csatolhat ](/cli/azure/vm/disk)egy meglévő lemezt egy virtuális géphez. Az alábbi példa egy myDataDisk nevű *meglévő lemezt csatol egy myVM* nevű *virtuális géphez*:

Első lépésként hozzon létre egy új lemezt:

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

Eredmények:

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

Ezután csatolhatja a lemezt a virtuális géphez:

```bash
LUN2_ID=$(az disk show --resource-group $MY_RESOURCE_GROUP_NAME --name $LUN2_NAME --query 'id' -o tsv)

az vm disk attach \
    --vm-name $MY_VM_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --disks $LUN2_ID \
    --sku PremiumV2_LRS \
    --lun 2
```

Ebben a harmadik forgatókönyvben a LUN2 lesz az adatlemezünk, az alábbi példa az adatlemez formázását és csatlakoztatását mutatja be.

```bash
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo parted -s -a optimal -- /dev/disk/azure/scsi1/lun2 mklabel gpt mkpart primary xfs 0% 100%"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo partprobe -s /dev/disk/azure/scsi1/lun2"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkfs.xfs /dev/disk/azure/scsi1/lun2-part1"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkdir -v /datadisk03"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mount -v /dev/disk/azure/scsi1/lun2-part1 /datadisk03"
```

Eredmények:

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

Az oderben a /etc/fstab fájl frissítéséhez használhatja a következő parancsot, és csatlakoztathatja a LUN1-et az egyedi azonosító (UUID) használatával az elvetett csatlakoztatási beállítással együtt:

```bash
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- \
    'echo "UUID=$(sudo blkid -s UUID -o value /dev/disk/azure/scsi1/lun2-part1) /datadisk03 xfs defaults,discard 0 0" | sudo tee -a /etc/fstab'
```

Eredmények:

<!-- expected_similarity=0.3 -->
```text
UUID=4b54ed3b-2f5e-4fe7-b0e5-c40da6e3b8a8 /datadisk03 xfs defaults,discard 0 0
```

## Az összes csatlakoztatott LUN ellenőrzése

A csatlakoztatási pontok ellenőrzéséhez használja a következő parancsot:

```bash
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- mount | egrep '(datadisk)'
```

Eredmények:

<!-- expected_similarity=0.3 -->
```text
/dev/sdc1 on /datadisk01 type xfs (rw,relatime)
/dev/sdd1 on /datadisk02 type xfs (rw,relatime)
/dev/sde1 on /datadisk03 type xfs (rw,relatime)
```

## SSH a virtuális gépre

Most már SSH-t is be tud illeszteni a virtuális gépbe, ha a következő parancsot futtatja a választott ssh-ügyfélen:

```bash
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN
```

## Következő lépések

* [Tudnivalók a virtuális gépekről](../index.yml)
* [Linux rendszerű virtuális gép inicializálása a Cloud-Init használatával az első rendszerindításkor](tutorial-automate-vm-deployment.md)
* [Egyéni virtuálisgép-rendszerképek létrehozása](tutorial-custom-images.md)
* [Virtuális gépek terheléselosztása](../../load-balancer/quickstart-load-balancer-standard-public-cli.md)
