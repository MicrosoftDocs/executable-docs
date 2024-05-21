---
title: '빠른 시작: Azure CLI를 사용하여 Linux Virtual Machine 만들기'
description: 이 빠른 시작에서는 Azure CLI를 사용하여 Linux 가상 머신을 만드는 방법을 배웁니다.
author: ju-shim
ms.service: virtual-machines
ms.collection: linux
ms.topic: quickstart
ms.date: 03/11/2024
ms.author: jushiman
ms.custom: 'mvc, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# 빠른 시작: Azure에서 Azure CLI를 사용하여 Linux 가상 머신 만들기

**적용 대상:** :heavy_check_mark: Linux VM

[![Azure에 배포](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262692)

이 빠른 시작에서는 Azure CLI를 사용하여 Azure에서 Linux VM(가상 머신)을 배포하는 방법을 보여줍니다. Azure CLI는 명령줄 또는 스크립트를 통해 Azure 리소스를 만들고 관리하는 데 사용됩니다.

Azure 구독이 아직 없는 경우 시작하기 전에 [체험 계정](https://azure.microsoft.com/free/?WT.mc_id=A261C142F)을 만듭니다.

## Azure Cloud Shell 시작

Azure Cloud Shell은 이 문서의 단계를 실행하는 데 무료로 사용할 수 있는 대화형 셸입니다. 공용 Azure 도구가 사전 설치되어 계정에서 사용하도록 구성되어 있습니다. 

Cloud Shell을 열려면 코드 블록의 오른쪽 위 모서리에 있는 **사용해 보세요**를 선택하기만 하면 됩니다. 또한 [https://shell.azure.com/bash](https://shell.azure.com/bash)로 이동하여 별도의 브라우저 탭에서 Cloud Shell을 열 수도 있습니다. **복사**를 선택하여 코드 블록을 복사하여 Cloud Shell에 붙여넣고, **Enter**를 선택하여 실행합니다.

CLI를 로컬에서 설치하여 사용하려면, 빠른 시작에 Azure CLI 버전 2.0.30 이상이 필요합니다. `az --version`을 실행하여 버전을 찾습니다. 설치 또는 업그레이드해야 하는 경우 [Azure CLI 설치]( /cli/azure/install-azure-cli)를 참조하세요.

## 환경 변수 정의

첫 번째 단계는 환경 변수를 정의하는 것입니다. 환경 변수는 일반적으로 Linux에서 구성 데이터를 중앙 집중화하여 시스템의 일관성과 유지 관리를 개선하는 데 사용됩니다. 다음 환경 변수를 만들어 이 자습서의 뒷부분에서 만드는 리소스의 이름을 지정합니다.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
```

## CLI를 사용하여 Azure에 로그인

CLI를 사용하여 Azure에서 명령을 실행하려면 먼저 로그인해야 합니다. 명령을 사용하여 로그인합니다 `az login` .

## 리소스 그룹 만들기

리소스 그룹은 관련 리소스에 대한 컨테이너입니다. 모든 리소스는 리소스 그룹에 배치되어야 합니다. [az group create](/cli/azure/group) 명령은 이전에 정의된 $MY_RESOURCE_GROUP_NAME 및 $REGION 매개 변수를 사용하여 리소스 그룹을 만듭니다.

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

## 가상 머신 만들기

이 리소스 그룹에 VM을 만들려면 이 명령을 사용합니다 `vm create` . 

다음 예제에서는 VM을 만들고 사용자 계정을 추가합니다. 매개 `--generate-ssh-keys` 변수를 사용하면 CLI에서 사용 가능한 ssh 키를 찾습니다 `~/.ssh`. 해당 키가 발견되면 해당 키가 사용됩니다. 그렇지 않은 경우 생성되어 에 `~/.ssh`저장됩니다. 매개 변수는 `--public-ip-sku Standard` 공용 IP 주소를 통해 컴퓨터에 액세스할 수 있도록 합니다. 마지막으로, 최신 `Ubuntu 22.04` 이미지를 배포합니다.

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

VM과 지원 리소스를 만드는 데 몇 분이 걸립니다. 다음 예제 출력은 VM 만들기 작업이 완료되었음을 보여줍니다.

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

## Azure에서 Linux 가상 머신에 Azure AD 로그인 사용

다음 코드 예제에서는 Linux VM을 배포한 다음 확장을 설치하여 Linux VM에 Azure AD 로그인을 사용하도록 설정합니다. VM 확장은 Azure 가상 머신에서 배포 후 구성 및 Automation 작업을 제공하는 작은 애플리케이션입니다.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

## SSH를 위해 VM의 IP 주소 저장

다음 명령을 실행하여 VM의 IP 주소를 환경 변수로 저장합니다.

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

## VM에 대한 SSH

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Log in to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

이제 선택한 ssh 클라이언트에서 다음 명령의 출력을 실행하여 VM에 SSH할 수 있습니다.

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

## 다음 단계

* [가상 머신에 대해 알아보기](../index.yml)
* [Cloud-Init를 사용하여 첫 번째 부팅 시 Linux VM 초기화](tutorial-automate-vm-deployment.md)
* [사용자 지정 VM 이미지 만들기](tutorial-custom-images.md)
* [VM 부하 분산](../../load-balancer/quickstart-load-balancer-standard-public-cli.md)
