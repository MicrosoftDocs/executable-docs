---
title: Краткое руководство. Создание виртуальной машины Linux с помощью Azure CLI
description: 'Из этого краткого руководства вы узнаете, как с помощью Azure CLI создать виртуальную машину Linux.'
author: ju-shim
ms.service: virtual-machines
ms.collection: linux
ms.topic: quickstart
ms.date: 03/11/2024
ms.author: jushiman
ms.custom: 'mvc, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Краткое руководство. Создание виртуальной машины Linux с помощью Azure CLI в Azure

**Применимо к:** :heavy_check_mark: виртуальным машинам Linux

[![Развертывание в Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262692)

В этом кратком руководстве показано, как с помощью Azure CLI развернуть в Azure виртуальную машину Linux. Azure CLI используется для создания ресурсов Azure и управления ими с помощью командной строки или скриптов.

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
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Результаты.

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

## Создание виртуальной машины

Чтобы создать виртуальную машину в этой группе ресурсов, используйте `vm create` команду. 

В следующем примере создается виртуальная машина и добавляется учетная запись пользователя. Параметр `--generate-ssh-keys` приводит к тому, что интерфейс командной строки ищет доступный ключ SSH в `~/.ssh`. Если он найден, используется этот ключ. Если нет, он создается и хранится в `~/.ssh`. Параметр `--public-ip-sku Standard` гарантирует, что компьютер доступен через общедоступный IP-адрес. Наконец, мы развернем последний `Ubuntu 22.04` образ.

Все остальные значения настраиваются с помощью переменных среды.

```bash
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
az vm create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_VM_NAME \
    --image $MY_VM_IMAGE \
    --admin-username $MY_USERNAME \
    --assign-identity \
    --generate-ssh-keys \
    --public-ip-sku Standard
```

Создание виртуальной машины и вспомогательных ресурсов занимает несколько минут. В следующем примере выходных данных показано, что виртуальная машина успешно создана.

Результаты.
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

## Включение входа Azure AD для виртуальной машины Linux в Azure

В следующем примере кода развертывается виртуальная машина Linux, а затем устанавливается расширение для включения входа Azure AD для виртуальной машины Linux. Расширения виртуальных машин — это небольшие приложения, которые выполняют задачи настройки и автоматизации после развертывания виртуальных машин Azure.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

## Хранение IP-адреса виртуальной машины для SSH

Выполните следующую команду, чтобы сохранить IP-адрес виртуальной машины в качестве переменной среды:

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

## SSH в виртуальной машине

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Log in to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

Теперь вы можете выполнить SSH-подключение к виртуальной машине, выполнив следующую команду в выбранном клиенте SSH:

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

## Next Steps

* [Сведения о виртуальных машинах](../index.yml)
* [Использование Cloud-Init для инициализации виртуальной машины Linux при первой загрузке](tutorial-automate-vm-deployment.md)
* [Создание пользовательских образов виртуальной машины](tutorial-custom-images.md)
* [Виртуальные машины балансировки нагрузки](../../load-balancer/quickstart-load-balancer-standard-public-cli.md)