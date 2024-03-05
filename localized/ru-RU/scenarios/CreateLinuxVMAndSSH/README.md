---
title: Создание виртуальной машины Linux и SSH в Azure
description: 'В этом руководстве показано, как создать виртуальную машину Linux и SSH в Azure.'
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Создание виртуальной машины Linux и SSH в Azure

[![Развертывание в Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateLinuxVMAndSSH)


## Определение переменных среды

Первым шагом в этом руководстве является определение переменных среды.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
```

# Вход в Azure с помощью интерфейса командной строки

Чтобы выполнить команды в Azure с помощью интерфейса командной строки, необходимо войти в систему. Это делается, очень просто, хотя `az login` команда:

# Создание или изменение группы ресурсов

Группа ресурсов — это контейнер для связанных ресурсов. Все ресурсы должны быть помещены в группу ресурсов. Мы создадим его для этого руководства. Следующая команда создает группу ресурсов с ранее определенными параметрами $MY_RESOURCE_GROUP_NAME и $REGION.

```bash
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

Чтобы создать виртуальную машину в этой группе ресурсов, необходимо выполнить простую команду, здесь мы предоставили `--generate-ssh-keys` флаг, это приведет к тому, что CLI будет искать автоматический ключ `~/.ssh`SSH, если он будет найден, в противном случае он будет создан и сохранен в `~/.ssh`. Мы также предоставляем `--public-ip-sku Standard` флаг, чтобы убедиться, что компьютер доступен через общедоступный IP-адрес. Наконец, мы развертываем последний `Ubuntu 22.04` образ. 

Все остальные значения настраиваются с помощью переменных среды.

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

### Включение входа Azure AD для виртуальной машины Linux в Azure

В следующем примере развернута виртуальная машина Linux, а затем устанавливается расширение для включения входа Azure AD для виртуальной машины Linux. Расширения виртуальных машин — это небольшие приложения, которые выполняют задачи настройки и автоматизации после развертывания виртуальных машин Azure.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

# Хранение IP-адреса виртуальной машины для SSH
Выполните следующую команду, чтобы получить IP-адрес виртуальной машины и сохранить ее в качестве переменной среды.

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

# SSH в виртуальную машину

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Login to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

Теперь вы можете выполнить SSH-подключение к виртуальной машине, выполнив следующую команду в выбранном клиенте SSH.

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

# Next Steps

* [Документация по виртуальным машинам](https://learn.microsoft.com/azure/virtual-machines/)
* [Использование Cloud-Init для инициализации виртуальной машины Linux при первой загрузке](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-automate-vm-deployment)
* [Создание пользовательских образов виртуальной машины](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-custom-images)
* [Виртуальные машины балансировки нагрузки](https://learn.microsoft.com/azure/load-balancer/quickstart-load-balancer-standard-public-cli)
