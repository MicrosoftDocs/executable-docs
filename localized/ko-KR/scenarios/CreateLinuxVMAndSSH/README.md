---
title: Azure에서 Linux VM 및 SSH 만들기
description: 이 자습서에서는 Azure에서 Linux VM 및 SSH를 만드는 방법을 보여줍니다.
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Azure에서 Linux VM 및 SSH 만들기

[![Azure에 배포](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateLinuxVMAndSSH)


## 환경 변수 정의

이 자습서의 첫 번째 단계는 환경 변수를 정의하는 것입니다.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
```

# CLI를 사용하여 Azure에 로그인

CLI를 사용하여 Azure에 대해 명령을 실행하려면 로그인해야 합니다. 이 작업은 명령을 통해 매우 간단하게 수행됩니다.`az login`

# 리소스 그룹 만들기

리소스 그룹은 관련 리소스에 대한 컨테이너입니다. 모든 리소스는 리소스 그룹에 배치해야 합니다. 이 자습서에 대해 만들겠습니다. 다음 명령은 이전에 정의된 $MY_RESOURCE_GROUP_NAME 및 $REGION 매개 변수를 사용하여 리소스 그룹을 만듭니다.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Results:

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

## Virtual Machine 만들기

이 리소스 그룹에서 VM을 만들려면 간단한 명령을 실행해야 합니다. 여기서는 플래그를 제공 `--generate-ssh-keys` 했으므로 CLI에서 avialable ssh 키를 `~/.ssh`찾습니다. VM이 사용되는 경우 CLI가 생성되고 저장 `~/.ssh`됩니다. 또한 공용 IP를 `--public-ip-sku Standard` 통해 컴퓨터에 액세스할 수 있도록 플래그를 제공합니다. 마지막으로, 최신 `Ubuntu 22.04` 이미지를 배포하고 있습니다. 

다른 모든 값은 환경 변수를 사용하여 구성됩니다.

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

Results:

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

### Azure에서 Linux Virtual Machine에 Azure AD 로그인 사용

다음 예제에서는 Linux VM을 배포한 다음, Linux VM에 Azure AD 로그인을 사용하도록 설정하는 확장을 설치합니다. VM 확장은 Azure 가상 머신에서 배포 후 구성 및 Automation 작업을 제공하는 작은 애플리케이션입니다.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

# SSH를 위해 VM의 IP 주소 저장
다음 명령을 실행하여 VM의 IP 주소를 가져와 환경 변수로 저장합니다.

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

# VM으로 SSH

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Login to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

이제 선택한 ssh 클라이언트에서 다음 명령의 출력을 실행하여 VM에 SSH할 수 있습니다.

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

# 다음 단계

* [VM 설명서](https://learn.microsoft.com/azure/virtual-machines/)
* [Cloud-Init를 사용하여 첫 번째 부팅 시 Linux VM 초기화](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-automate-vm-deployment)
* [사용자 지정 VM 이미지 만들기](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-custom-images)
* [VM 부하 분산](https://learn.microsoft.com/azure/load-balancer/quickstart-load-balancer-standard-public-cli)
