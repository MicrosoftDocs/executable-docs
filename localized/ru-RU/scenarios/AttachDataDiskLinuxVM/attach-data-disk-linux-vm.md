---
title: Краткое руководство. Создание виртуальной машины Ubuntu и подключение диска данных Azure с помощью Azure CLI
description: 'Из этого краткого руководства вы узнаете, как использовать Azure CLI для создания виртуальной машины Ubuntu Linux'
author: ajoian
ms.service: virtual-machines
ms.collection: linux
ms.topic: quickstart
ms.date: 07/10/2024
ms.author: ajoian
ms.custom: 'mvc, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Краткое руководство. Создание виртуальной машины Ubuntu и подключение диска данных Azure с помощью Azure CLI

В этом кратком руководстве показано, как использовать Azure CLI для развертывания виртуальной машины Ubuntu Linux в Azure и подключения диска данных Azure к виртуальной машине. Azure CLI используется для создания ресурсов Azure и управления ими с помощью командной строки или скриптов.

Если у вас нет подписки Azure, создайте [бесплатную учетную запись](https://azure.microsoft.com/free/?WT.mc_id=A261C142F), прежде чем приступить к работе.

## Запуск Azure Cloud Shell

Azure Cloud Shell — это бесплатная интерактивная оболочка, с помощью которой можно выполнять действия, описанные в этой статье. Она включает предварительно установленные общие инструменты Azure и настроена для использования с вашей учетной записью.

Чтобы открыть Cloud Shell, просто выберите **Попробовать** в правом верхнем углу блока кода. Кроме того, Cloud Shell можно открыть в отдельной вкладке браузера. Для этого перейдите на страницу [https://shell.azure.com/bash](https://shell.azure.com/bash). Нажмите кнопку **Копировать**, чтобы скопировать блоки кода. Вставьте код в Cloud Shell и нажмите клавишу **ВВОД**, чтобы выполнить его.

Если вы решили установить и использовать CLI локально, для выполнения инструкций из этого руководства вам потребуется Azure CLI 2.0.30 или более поздней версии. Чтобы узнать версию, выполните команду `az --version`. Если вам необходимо выполнить установку или обновление, см. статью [Установка Azure CLI 2.0]( /cli/azure/install-azure-cli).

## Вход в Azure с помощью интерфейса командной строки

Чтобы выполнить команды в Azure с помощью интерфейса командной строки, сначала необходимо войти в систему. Войдите с помощью `az login` команды.

## Создание или изменение группы ресурсов

Группа ресурсов — это контейнер для связанных ресурсов. Все ресурсы должны быть помещены в группу ресурсов. Команда [az group create](/cli/azure/group) создает группу ресурсов с ранее определенными параметрами $MY_RESOURCE_GROUP_NAME и $REGION.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="LinuxRG-$RANDOM_ID"
export REGION="australiaeast"
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION -o JSON
```

Результаты.

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

## Создание виртуальной машины Linux Azure с диском данных

В следующем примере создается виртуальная машина с именем `$MY_VM_NAME` и создаются ключи SSH, если они еще не существуют в расположении ключа по умолчанию и создают диск данных в виде LUN0.

Чтобы повысить безопасность виртуальных машин Linux в Azure, можно интегрировать с проверкой подлинности Azure Active Directory. Теперь вы можете использовать Azure AD в качестве основной платформы проверки подлинности. Вы также можете использовать SSH на виртуальной машине Linux с помощью проверки подлинности на основе сертификатов Azure AD и OpenSSH. Эта функция позволяет организациям управлять доступом к виртуальным машинам с помощью политик управления доступом на основе ролей и условного доступа.

Создайте виртуальную машину с помощью команды [az vm create](/cli/azure/vm#az-vm-create).

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

Результаты.

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

## Включение входа Azure AD для виртуальной машины Linux в Azure

В следующем примере кода развертывается виртуальная машина Linux, а затем устанавливается расширение для включения входа Azure AD для виртуальной машины Linux. Расширения виртуальных машин — это небольшие приложения, которые выполняют задачи настройки и автоматизации после развертывания виртуальных машин Azure.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME -o JSON
```

Результаты.

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

В этом сценарии первый диск данных LUN0 будет отформатирован и подключен с помощью следующей команды:

```bash
export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo parted -s -a optimal -- /dev/disk/azure/scsi1/lun0 mklabel gpt mkpart primary xfs 0% 100%"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo partprobe -s /dev/disk/azure/scsi1/lun0"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkfs.xfs /dev/disk/azure/scsi1/lun0-part1"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkdir -v /datadisk01"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mount -v /dev/disk/azure/scsi1/lun0-part1 /datadisk01"
```

Результаты.

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

В oder для обновления файла /etc/fstab можно использовать следующую команду и подключить LUN1 с помощью уникального идентификатора (UUID) вместе с параметром отмены подключения:

```bash
ssh $MY_VM_USERNAME@$FQDN -- \
    'echo UUID=$(sudo blkid -s UUID -o value /dev/disk/azure/scsi1/lun0-part1) /datadisk01 xfs defaults,discard 0 0 | sudo tee -a /etc/fstab'
```

Результаты.

<!-- expected_similarity=0.3 -->
```text
UUID=1095e29c-07db-47ec-8b19-1ffcaf4f5628 /datadisk01 xfs defaults,discard 0 0
```

## Подключение нового диска к виртуальной машине

Если вам нужен новый пустой диск с данными в виртуальной машине, то используйте команду [az vm disk attach](/cli/azure/vm/disk) с параметром `--new`. Если виртуальная машина находится в зоне доступности, то диск автоматически создается в одной зоне с виртуальной машиной. Дополнительные сведения см. в статье [Общие сведения о зонах доступности в Azure (предварительная версия)](../../availability-zones/az-overview.md). В следующем примере создается диск с именем *$LUN 2_NAME* , размером 50 ГБ:

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

В этом втором сценарии luN1 будет нашим диском данных, в следующем примере показано, как отформатировать и подключить диск данных.

```bash
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo parted -s -a optimal -- /dev/disk/azure/scsi1/lun1 mklabel gpt mkpart primary xfs 0% 100%"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo partprobe -s /dev/disk/azure/scsi1/lun1"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkfs.xfs /dev/disk/azure/scsi1/lun1-part1"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkdir -v /datadisk02"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mount -v /dev/disk/azure/scsi1/lun1-part1 /datadisk02"
```

Результаты.

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

В oder для обновления файла /etc/fstab можно использовать следующую команду и подключить LUN1 с помощью уникального идентификатора (UUID) вместе с параметром отмены подключения:

```bash
ssh $MY_VM_USERNAME@$FQDN -- \
    'echo "UUID=$(sudo blkid -s UUID -o value /dev/disk/azure/scsi1/lun1-part1) /datadisk02 xfs defaults,discard 0 0" | sudo tee -a /etc/fstab'
```

Результаты.

<!-- expected_similarity=0.3 -->
```text
UUID=0b1629d5-0cd5-41fd-9050-b2ed7e3f1028 /datadisk02 xfs defaults,discard 0 0
```

## Подключение существующего диска данных к виртуальной машине

Наконец, третий сценарий — подключение существующего диска к виртуальной машине. Команду az vm disk attach[ можно использовать ](/cli/azure/vm/disk)с параметром `--disk` для подключения существующего диска к виртуальной машине. В следующем примере подключается существующий диск с именем myDataDisk* к виртуальной машине с именем **myVM*:

Сначала можно начать с создания нового диска:

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

Результаты.

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

Затем вы можете подключить диск к виртуальной машине:

```bash
LUN2_ID=$(az disk show --resource-group $MY_RESOURCE_GROUP_NAME --name $LUN2_NAME --query 'id' -o tsv)

az vm disk attach \
    --vm-name $MY_VM_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --disks $LUN2_ID \
    --sku PremiumV2_LRS \
    --lun 2
```

В этом третьем сценарии LUN2 будет нашим диском данных, в следующем примере показано, как отформатировать и подключить диск данных.

```bash
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo parted -s -a optimal -- /dev/disk/azure/scsi1/lun2 mklabel gpt mkpart primary xfs 0% 100%"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo partprobe -s /dev/disk/azure/scsi1/lun2"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkfs.xfs /dev/disk/azure/scsi1/lun2-part1"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mkdir -v /datadisk03"
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- "sudo mount -v /dev/disk/azure/scsi1/lun2-part1 /datadisk03"
```

Результаты.

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

В oder для обновления файла /etc/fstab можно использовать следующую команду и подключить LUN1 с помощью уникального идентификатора (UUID) вместе с параметром отмены подключения:

```bash
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- \
    'echo "UUID=$(sudo blkid -s UUID -o value /dev/disk/azure/scsi1/lun2-part1) /datadisk03 xfs defaults,discard 0 0" | sudo tee -a /etc/fstab'
```

Результаты.

<!-- expected_similarity=0.3 -->
```text
UUID=4b54ed3b-2f5e-4fe7-b0e5-c40da6e3b8a8 /datadisk03 xfs defaults,discard 0 0
```

## Проверьте все подключенные LUN

Чтобы проверить точки подключения, можно использовать следующую команду:

```bash
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN -- mount | egrep '(datadisk)'
```

Результаты.

<!-- expected_similarity=0.3 -->
```text
/dev/sdc1 on /datadisk01 type xfs (rw,relatime)
/dev/sdd1 on /datadisk02 type xfs (rw,relatime)
/dev/sde1 on /datadisk03 type xfs (rw,relatime)
```

## SSH в виртуальной машине

Теперь вы можете выполнить SSH-подключение к виртуальной машине, выполнив следующую команду в выбранном клиенте SSH:

```bash
ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN
```

## Next Steps

* [Сведения о виртуальных машинах](../index.yml)
* [Использование Cloud-Init для инициализации виртуальной машины Linux при первой загрузке](tutorial-automate-vm-deployment.md)
* [Создание пользовательских образов виртуальной машины](tutorial-custom-images.md)
* [Виртуальные машины балансировки нагрузки](../../load-balancer/quickstart-load-balancer-standard-public-cli.md)
