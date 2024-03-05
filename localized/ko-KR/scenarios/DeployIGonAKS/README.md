---
title: Azure Kubernetes Service 클러스터에 Inspektor 가젯 배포
description: 이 자습서에서는 AKS 클러스터에 Inspektor 가젯을 배포하는 방법을 보여 줍니다.
author: josebl
ms.author: josebl
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# 빠른 시작: Azure Kubernetes Service 클러스터에 Inspektor 가젯 배포

kubectl 플러그 인`gadget`을 사용하여 AKS(Azure Kubernetes Service) 클러스터에 Inspektor 가젯[을 배포하는 ](https://www.inspektor-gadget.io/)단계를 단계별로 수행하는 이 자습서를 시작합니다. 이 자습서에서는 사용자가 이미 Azure CLI에 로그인하고 CLI와 함께 사용할 구독을 선택했다고 가정합니다.

## 환경 변수 정의

이 자습서의 첫 번째 단계는 환경 변수를 정의하는 것입니다.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myResourceGroup$RANDOM_ID"
export REGION="eastus"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
```

## 리소스 그룹 만들기

리소스 그룹은 관련 리소스에 대한 컨테이너입니다. 모든 리소스는 리소스 그룹에 배치해야 합니다. 이 자습서에 대해 만들겠습니다. 다음 명령은 이전에 정의된 $MY_RESOURCE_GROUP_NAME 및 $REGION 매개 변수를 사용하여 리소스 그룹을 만듭니다.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Results:

<!-- expected_similarity=0.3 -->
```JSON
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myResourceGroup210",
  "location": "eastus",
  "managedBy": null,
  "name": "testResourceGroup",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## AKS 클러스터 만들기

az aks create 명령을 사용하여 AKS 클러스터를 만듭니다.

이 작업은 몇 분 정도 걸립니다.

```bash
az aks create \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --name $MY_AKS_CLUSTER_NAME \
  --location $REGION \
  --no-ssh-key
```

## 클러스터에 연결

Kubernetes 클러스터를 관리하려면 Kubernetes 명령줄 클라이언트인 kubectl을 사용합니다. Azure Cloud Shell을 사용하는 경우 kubectl이 이미 설치되어 있습니다.

1. az aks install-cli 명령을 사용하여 az aks CLI를 로컬로 설치

    ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
    ```

2. az aks get-credentials 명령을 사용하여 Kubernetes 클러스터에 연결하도록 kubectl을 구성합니다. 다음 명령은 아래와 같은 작업을 수행합니다.
    - 자격 증명을 다운로드하고 이를 사용하도록 Kubernetes CLI를 구성합니다.
    - Kubernetes 구성 파일의 기본 위치인 ~/.kube/config를 사용합니다. --file 인수를 사용하여 Kubernetes 구성 파일의 다른 위치를 지정합니다.

    > [!WARNING]
    > 이렇게 하면 동일한 항목으로 기존 자격 증명을 덮어쓰게 됩니다.

    ```bash
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
    ```

3. kubectl get 명령을 사용하여 클러스터에 대한 연결을 확인합니다. 이 명령은 클러스터 노드 목록을 반환합니다.

    ```bash
    kubectl get nodes
    ```

## Inspektor 가젯 설치

Inspektor 가젯 설치는 다음 두 단계로 구성됩니다.

1. 사용자 시스템에 kubectl 플러그 인을 설치합니다.
2. 클러스터에 Inspektor 가젯 설치

    > [!NOTE]
    > 각각 특정 사용 사례 및 요구 사항에 맞게 조정된 Inspektor 가젯을 배포하고 활용하기 위한 추가 메커니즘이 있습니다. 플러그 인을 `kubectl gadget` 사용하면 많은 항목이 포함되지만 전부는 아닙니다. 예를 들어 플러그 인을 사용하여 Inspektor 가젯 `kubectl gadget` 을 배포하는 것은 Kubernetes API 서버의 가용성에 따라 달라집니다. 따라서 가용성이 손상될 수 있으므로 이러한 구성 요소에 의존할 수 없는 경우 배포 메커니즘을 `kubectl gadget`사용하지 않는 것이 좋습니다. ig 설명서를[ 검사 ](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/ig.md)해당 작업 및 기타 사용 사례를 확인하세요.

### kubectl 플러그 인 설치: `gadget`

릴리스 페이지에서 kubectl 플러그 인의 최신 버전을 설치하고 압축을 풀고 실행 파일을 다음으로 `$HOME/.local/bin`이동합니다`kubectl-gadget`.

> [!NOTE]
> 원본을 사용하여 [`krew`](https://sigs.k8s.io/krew) 설치하거나 소스에서 컴파일하려면 kubectl 가젯[ 설치와 같은 공식 설명서를 ](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-kubectl-gadget)따르세요.

```bash
IG_VERSION=$(curl -s https://api.github.com/repos/inspektor-gadget/inspektor-gadget/releases/latest | jq -r .tag_name)
IG_ARCH=amd64
mkdir -p $HOME/.local/bin
export PATH=$PATH:$HOME/.local/bin
curl -sL https://github.com/inspektor-gadget/inspektor-gadget/releases/download/${IG_VERSION}/kubectl-gadget-linux-${IG_ARCH}-${IG_VERSION}.tar.gz  | tar -C $HOME/.local/bin -xzf - kubectl-gadget
```

이제 다음 명령을 실행하여 설치를 확인해 보겠습니다.`version`

```bash
kubectl gadget version
```

이 `version` 명령은 클라이언트 버전(kubectl 가젯 플러그 인)을 표시하고 서버(클러스터)에 아직 설치되지 않은 것을 표시합니다.

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: not installed$"-->
```text
Client version: vX.Y.Z
Server version: not installed
```

### 클러스터에 Inspektor 가젯 설치

다음 명령은 DaemonSet을 배포합니다.

> [!NOTE]
> 배포를 사용자 지정하는 데 사용할 수 있는 몇 가지 옵션은 특정 컨테이너 이미지 사용, 특정 노드에 배포 및 기타 많은 옵션입니다. 이 모든 것을 알고 있으려면 공식 설명서[(클러스터](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-in-the-cluster)에 설치)를 검사.

```bash
kubectl gadget deploy
```

이제 명령을 다시 실행하여 설치를 `version` 확인해 보겠습니다.

```bash
kubectl gadget version
```

이번에는 클라이언트와 서버가 올바르게 설치됩니다.

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: v\d+\.\d+\.\d+$"-->
```text
Client version: vX.Y.Z
Server version: vX.Y.Z
```

이제 가젯 실행을 시작할 수 있습니다.

```bash
kubectl gadget help
```

<!--
## Clean Up

### Undeploy Inspektor Gadget

```bash
kubectl gadget undeploy
```

### Clean up Azure resources

When no longer needed, you can use `az group delete` to remove the resource group, cluster, and all related resources as follows. The `--no-wait` parameter returns control to the prompt without waiting for the operation to complete. The `--yes` parameter confirms that you wish to delete the resources without an additional prompt to do so.

```bash
az group delete --name $MY_RESOURCE_GROUP_NAME --no-wait --yes
```
-->

## 다음 단계
- [Inspektor 가젯이 도움이 될 수 있는 실제 시나리오](https://go.microsoft.com/fwlink/p/?linkid=2260402#use-cases)
- [사용 가능한 가젯 살펴보기](https://go.microsoft.com/fwlink/p/?linkid=2260070)
- [고유한 eBPF 프로그램 실행](https://go.microsoft.com/fwlink/p/?linkid=2259865)
