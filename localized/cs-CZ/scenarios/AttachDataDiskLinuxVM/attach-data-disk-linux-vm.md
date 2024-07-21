---
title: 'Rychlý start: Vytvoření virtuálního počítače s Ubuntu pomocí Azure CLI a připojení datového disku Azure'
description: 'V tomto rychlém startu se dozvíte, jak pomocí Azure CLI vytvořit virtuální počítač s Ubuntu Linuxem.'
author: ajoian
ms.service: virtual-machines
ms.collection: linux
ms.topic: quickstart
ms.date: 07/10/2024
ms.author: ajoian
ms.custom: 'mvc, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Rychlý start: Vytvoření virtuálního počítače s Ubuntu pomocí Azure CLI a připojení datového disku Azure

V tomto rychlém startu se dozvíte, jak pomocí Azure CLI nasadit virtuální počítač s Ubuntu Linuxem v Azure a připojit k němu datový disk Azure. Azure CLI slouží k vytváření a správě prostředků Azure prostřednictvím příkazového řádku nebo skriptů.

Pokud ještě nemáte předplatné Azure, vytvořte si napřed [bezplatný účet](https://azure.microsoft.com/free/?WT.mc_id=A261C142F).

## Spuštění služby Azure Cloud Shell

Azure Cloud Shell je bezplatné interaktivní prostředí, které můžete použít k provedení kroků v tomto článku. Má předinstalované obecné nástroje Azure, které jsou nakonfigurované pro použití s vaším účtem.

Pokud chcete otevřít Cloud Shell, vyberte položku **Vyzkoušet** v pravém horním rohu bloku kódu. Cloud Shell můžete otevřít také na samostatné kartě prohlížeče tak, že přejdete na [https://shell.azure.com/bash](https://shell.azure.com/bash). Výběrem **možnosti Kopírovat** zkopírujte bloky kódu, vložte ho do Cloud Shellu a stisknutím **klávesy Enter** ho spusťte.

Pokud dáváte přednost místní instalaci a používání rozhraní příkazového řádku, musíte mít Azure CLI verze 2.0.30 nebo novější. Verzi zjistíte spuštěním příkazu `az --version`. Pokud potřebujete instalaci nebo upgrade, přečtěte si téma [Instalace Azure CLI]( /cli/azure/install-azure-cli).

## Přihlášení k Azure pomocí rozhraní příkazového řádku

Abyste mohli spouštět příkazy v Azure pomocí rozhraní příkazového řádku, musíte se nejdřív přihlásit. Přihlaste se pomocí `az login` příkazu.

## Vytvoření skupiny zdrojů

Skupina prostředků je kontejner pro související prostředky. Všechny prostředky musí být umístěné ve skupině prostředků. Příkaz [az group create](/cli/azure/group) vytvoří skupinu prostředků s dříve definovanými parametry $MY_RESOURCE_GROUP_NAME a $REGION.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="LinuxRG-$RANDOM_ID"
export REGION="australiaeast"
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION -o JSON
```

Výsledky:

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

## Vytvoření virtuálního počítače Azure s Linuxem s datovým diskem

Následující první příklad vytvoří virtuální počítač s názvem `$MY_VM_NAME` a vytvoří klíče SSH, pokud ještě neexistují ve výchozím umístění klíče a vytvoří datový disk jako lun0.

Pokud chcete zlepšit zabezpečení virtuálních počítačů s Linuxem v Azure, můžete provést integraci s ověřováním Azure Active Directory. Teď můžete azure AD používat jako základní ověřovací platformu. SSH můžete do virtuálního počítače s Linuxem použít také ověřování založené na certifikátech Azure AD a OpenSSH. Tato funkce umožňuje organizacím spravovat přístup k virtuálním počítačům pomocí řízení přístupu na základě role Azure a zásad podmíněného přístupu.

Vytvořte virtuální počítač pomocí příkazu [az vm create](/cli/azure/vm#az-vm-create).

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

Výsledky:

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

## Povolení přihlášení Azure AD pro virtuální počítač s Linuxem v Azure

Následující příklad kódu nasadí virtuální počítač s Linuxem a pak nainstaluje rozšíření, které povolí přihlášení Azure AD pro virtuální počítač s Linuxem. Rozšíření virtuálních počítačů jsou malé aplikace, které poskytují úlohy konfigurace a automatizace po nasazení na virtuálních počítačích Azure.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME -o JSON
```

Výsledky:

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

V tomto scénáři bude náš první datový disk naformátovaný a připojený pomocí následujícího příkazu:

```bash
export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo parted -s -a optimal -- /dev/disk/azure/scsi1/lun0 mklabel gpt mkpart primary xfs 0% 100%"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo partprobe -s /dev/disk/azure/scsi1/lun0"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkfs.xfs /dev/disk/azure/scsi1/lun0-part1"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkdir -v /datadisk01"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mount -v /dev/disk/azure/scsi1/lun0-part1 /datadisk01"
```

Výsledky:

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

V oderu aktualizovat soubor /etc/fstab můžete použít následující příkaz a připojit logickou jednotku LUN1 pomocí jedinečného identifikátoru (UUID) společně s možností zahodit připojení:

```bash
ssh $MY_VM_USERNAME@$FQDN -- \
    'echo UUID=$(sudo blkid -s UUID -o value /dev/disk/azure/scsi1/lun0-part1) /datadisk01 xfs defaults,discard 0 0 | sudo tee -a /etc/fstab'
```

Výsledky:

<!-- expected_similarity=0.3 -->
```text
UUID=1095e29c-07db-47ec-8b19-1ffcaf4f5628 /datadisk01 xfs defaults,discard 0 0
```

## Připojení nového disku k virtuálnímu počítači

Pokud chcete na virtuálním počítači přidat nový prázdný datový disk, použijte [příkaz az vm disk attach](/cli/azure/vm/disk) s parametrem `--new` . Pokud je váš virtuální počítač v zóně dostupnosti, disk se automaticky vytvoří ve stejné zóně jako virtuální počítač. Další informace najdete v tématu [Přehled Zóny dostupnosti](../../availability-zones/az-overview.md). Následující příklad vytvoří disk s názvem *$LUN 2_NAME* , který má velikost 50 Gb:

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

V tomto druhém možném scénáři bude lun1 náš datový disk, následující příklad ukazuje, jak formátovat a připojit datový disk.

```bash
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo parted -s -a optimal -- /dev/disk/azure/scsi1/lun1 mklabel gpt mkpart primary xfs 0% 100%"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo partprobe -s /dev/disk/azure/scsi1/lun1"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkfs.xfs /dev/disk/azure/scsi1/lun1-part1"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkdir -v /datadisk02"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mount -v /dev/disk/azure/scsi1/lun1-part1 /datadisk02"
```

Výsledky:

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

V oderu aktualizovat soubor /etc/fstab můžete použít následující příkaz a připojit logickou jednotku LUN1 pomocí jedinečného identifikátoru (UUID) společně s možností zahodit připojení:

```bash
ssh $MY_VM_USERNAME@$FQDN -- \
    'echo "UUID=$(sudo blkid -s UUID -o value /dev/disk/azure/scsi1/lun1-part1) /datadisk02 xfs defaults,discard 0 0" | sudo tee -a /etc/fstab'
```

Výsledky:

<!-- expected_similarity=0.3 -->
```text
UUID=0b1629d5-0cd5-41fd-9050-b2ed7e3f1028 /datadisk02 xfs defaults,discard 0 0
```

## Připojení existujícího datového disku k virtuálnímu počítači

Nakonec třetí scénář spočívá v připojení existujícího disku k virtuálnímu počítači. Pomocí příkazu az vm disk attach[ s `--disk` parametrem můžete ](/cli/azure/vm/disk)k virtuálnímu počítači připojit existující disk. Následující příklad připojí existující disk s názvem *myDataDisk* k virtuálnímu počítači s názvem *myVM*:

Nejprve začnete vytvořením nového disku:

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

Výsledky:

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

Pak můžete disk připojit k virtuálnímu počítači:

```bash
LUN2_ID=$(az disk show --resource-group $MY_RESOURCE_GROUP_NAME --name $LUN2_NAME --query 'id' -o tsv)

az vm disk attach \
    --vm-name $MY_VM_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --disks $LUN2_ID \
    --sku PremiumV2_LRS \
    --lun 2
```

V tomto třetím scénáři bude lun2 náš datový disk, následující příklad ukazuje, jak formátovat a připojit datový disk.

```bash
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo parted -s -a optimal -- /dev/disk/azure/scsi1/lun2 mklabel gpt mkpart primary xfs 0% 100%"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo partprobe -s /dev/disk/azure/scsi1/lun2"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkfs.xfs /dev/disk/azure/scsi1/lun2-part1"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkdir -v /datadisk03"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mount -v /dev/disk/azure/scsi1/lun2-part1 /datadisk03"
```

Výsledky:

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

V oderu aktualizovat soubor /etc/fstab můžete použít následující příkaz a připojit logickou jednotku LUN1 pomocí jedinečného identifikátoru (UUID) společně s možností zahodit připojení:

```bash
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- \
    'echo "UUID=$(sudo blkid -s UUID -o value /dev/disk/azure/scsi1/lun2-part1) /datadisk03 xfs defaults,discard 0 0" | sudo tee -a /etc/fstab'
```

Výsledky:

<!-- expected_similarity=0.3 -->
```text
UUID=4b54ed3b-2f5e-4fe7-b0e5-c40da6e3b8a8 /datadisk03 xfs defaults,discard 0 0
```

## Kontrola všech připojených lunů

K ověření přípojných bodů můžete použít následující příkaz:

```bash
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- mount | egrep '(datadisk)'
```

Výsledky:

<!-- expected_similarity=0.3 -->
```text
/dev/sdc1 on /datadisk01 type xfs (rw,relatime)
/dev/sdd1 on /datadisk02 type xfs (rw,relatime)
/dev/sde1 on /datadisk03 type xfs (rw,relatime)
```

## Připojení SSH k virtuálnímu počítači

Do virtuálního počítače teď můžete SSH připojit spuštěním následujícího příkazu ve zvoleném klientovi ssh:

```bash
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN
```

## Další kroky

* [Další informace o virtuálních počítačích](../index.yml)
* [Použití Cloud-Init k inicializaci virtuálního počítače s Linuxem při prvním spuštění](tutorial-automate-vm-deployment.md)
* [Vytváření vlastních imagí virtuálních počítačů](tutorial-custom-images.md)
* [Vyrovnávání zatížení virtuálních počítačů](../../load-balancer/quickstart-load-balancer-standard-public-cli.md)
