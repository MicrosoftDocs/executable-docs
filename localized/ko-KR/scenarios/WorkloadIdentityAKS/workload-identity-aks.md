---
title: 워크로드 ID를 사용하여 AKS 클러스터 배포 및 구성
description: 이 AKS(Azure Kubernetes Service) 문서에서는 Azure Kubernetes Service 클러스터를 배포하고 Microsoft Entra 워크로드 ID로 구성합니다.
author: tamram
ms.topic: article
ms.subservice: aks-security
ms.custom: devx-track-azurecli
ms.date: 05/28/2024
ms.author: tamram
---

# AKS(Azure Kubernetes Service) 클러스터에서 워크로드 ID 배포 및 구성

AKS(Azure Kubernetes Service)는 Kubernetes 클러스터를 빠르게 배포하고 관리할 수 있는 관리되는 Kubernetes 서비스입니다. 이 문서는 다음을 수행하는 방법을 보여줍니다.

* OpenID Connect 발급자와 Microsoft Entra 워크로드 ID가 포함된 Azure CLI를 사용하여 AKS 클러스터를 배포합니다.
* Microsoft Entra 워크로드 ID 및 Kubernetes 서비스 계정을 만듭니다.
* 토큰 페더레이션을 위한 관리 ID를 구성합니다.
* 워크로드를 배포하고 워크로드 ID를 사용하여 인증을 확인합니다.
* 필요에 따라 클러스터의 Pod에 Azure Key Vault의 비밀에 대한 액세스 권한을 부여합니다.

이 문서에서는 사용자가 Kubernetes 개념에 대한 기본적인 지식을 보유하고 있다고 가정합니다. 자세한 내용은 [AKS(Azure Kubernetes Service)의 Kubernetes 핵심 개념][kubernetes-concepts]을 참조하세요. Microsoft Entra 워크로드 ID에 익숙하지 않은 경우 다음 [개요][workload-identity-overview] 문서를 참조하세요.

## 필수 조건

* [!INCLUDE [quickstarts-free-trial-note](~/reusable-content/ce-skilling/azure/includes/quickstarts-free-trial-note.md)]
* 이 문서대로 하려면 Azure CLI 버전 2.47.0 이상이 필요합니다. Azure Cloud Shell을 사용하는 경우 최신 버전이 이미 설치되어 있습니다.
* 클러스터를 만드는 데 사용하는 ID에 적절한 최소 권한이 있는지 확인합니다. AKS의 액세스 및 ID에 대한 자세한 내용은 [AKS(Azure Kubernetes Service)에 대한 액세스 및 ID 옵션][aks-identity-concepts]을 참조하세요.
* Azure 구독이 여러 개인 경우 [az account set][az-account-set] 명령을 사용하여 리소스가 청구되어야 하는 적절한 구독 ID를 선택합니다.

> [!NOTE]
> _서비스 커넥터_를 사용하면 일부 단계를 자동으로 구성할 수 있습니다. 참조: [자습서: 워크로드 ID를 사용하여 서비스 커넥터를 사용하여 AKS(Azure Kubernetes Service)에서 Azure Storage 계정에 연결][tutorial-python-aks-storage-workload-identity].

## 리소스 그룹 만들기

[Azure 리소스 그룹][azure-resource-group]은 Azure 리소스가 배포되고 관리되는 논리 그룹입니다. 리소스 그룹을 만들 때 위치를 지정하라는 메시지가 표시됩니다. 이 위치는 리소스 그룹 메타데이터의 스토리지 위치이며 리소스를 만드는 중에 다른 지역을 지정하지 않은 경우 Azure에서 리소스가 실행되는 위치입니다.

[az group create][az-group-create] 명령을 호출하여 리소스 그룹을 만듭니다.

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export RESOURCE_GROUP="myResourceGroup$RANDOM_ID"
export LOCATION="centralindia"
az group create --name "${RESOURCE_GROUP}" --location "${LOCATION}"
```

다음 출력 예는 리소스 그룹의 성공적인 만들기를 보여 줍니다.

Results:
<!-- expected_similarity=0.3 -->
```json
{
  "id": "/subscriptions/<guid>/resourceGroups/myResourceGroup",
  "location": "eastus",
  "managedBy": null,
  "name": "myResourceGroup",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## AKS 클러스터 만들기

OIDC 발급자를 사용하도록 설정하려면 `--enable-oidc-issuer` 매개 변수와 함께 [az aks create][az-aks-create] 명령을 사용하여 AKS 클러스터를 만듭니다. 다음 예에서는 단일 노드가 있는 클러스터를 만듭니다.

```azurecli-interactive
export CLUSTER_NAME="myAKSCluster$RANDOM_ID"
az aks create \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity \
    --generate-ssh-keys
```

몇 분 후 명령이 완료되면 클러스터에 대한 JSON 형식 정보가 반환됩니다.

> [!NOTE]
> AKS 클러스터를 생성하면 AKS 리소스를 저장하는 두 번째 리소스 그룹이 자동으로 만들어집니다. 자세한 내용은 [AKS를 통해 두 개의 리소스 그룹이 생성되는 이유는 무엇인가요?][aks-two-resource-groups]를 참조하세요.

## 기존 AKS 클러스터 업데이트

`--enable-oidc-issuer` 및 `--enable-workload-identity` 매개 변수와 함께 [az aks update][az aks update] 명령을 호출하여 OIDC 발급자를 사용하고 워크로드 ID를 사용하도록 AKS 클러스터를 업데이트할 수 있습니다. 다음 예에서는 기존 클러스터를 업데이트합니다.

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity
```

## OIDC 발급자 URL 검색

OIDC 발급자 URL을 가져와 환경 변수에 저장하려면 다음 명령을 실행합니다.

```azurecli-interactive
export AKS_OIDC_ISSUER="$(az aks show --name "${CLUSTER_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --query "oidcIssuerProfile.issuerUrl" \
    --output tsv)"
```

환경 변수에는 다음 예와 유사한 발급자 URL이 포함되어야 합니다.

```output
https://eastus.oic.prod-aks.azure.com/00000000-0000-0000-0000-000000000000/11111111-1111-1111-1111-111111111111/
```

기본적으로 발급자는 기준 URL `https://{region}.oic.prod-aks.azure.com/{tenant_id}/{uuid}`를 사용하도록 설정됩니다. 여기서 `{region}`의 값은 AKS 클러스터가 배포된 위치와 일치합니다. 이 `{uuid}` 값은 변경이 불가능한 각 클러스터에 임의로 생성된 guid인 OIDC 키를 나타냅니다.

## 관리 ID 만들기

관리 ID를 만들려면 [az Identity create][az-identity-create] 명령을 호출합니다.

```azurecli-interactive
export SUBSCRIPTION="$(az account show --query id --output tsv)"
export USER_ASSIGNED_IDENTITY_NAME="myIdentity$RANDOM_ID"
az identity create \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --location "${LOCATION}" \
    --subscription "${SUBSCRIPTION}"
```

다음 출력 예제에서는 관리 ID를 성공적으로 만드는 방법을 보여줍니다.

Results:
<!-- expected_similarity=0.3 -->
```output
{
  "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourcegroups/myResourceGroupxxxxxx/providers/Microsoft.ManagedIdentity/userAssignedIdentities/myIdentityxxxxxx",
  "location": "centralindia",
  "name": "myIdentityxxxxxx",
  "principalId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "resourceGroup": "myResourceGroupxxxxxx",
  "systemData": null,
  "tags": {},
  "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "type": "Microsoft.ManagedIdentity/userAssignedIdentities"
}
```

다음으로 관리 ID의 클라이언트 ID에 대한 변수를 만듭니다.

```azurecli-interactive
export USER_ASSIGNED_CLIENT_ID="$(az identity show \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --query 'clientId' \
    --output tsv)"
```

## Kubernetes 서비스 계정 만들기

Kubernetes 서비스 계정을 만들고 이전 단계에서 만든 관리 ID의 클라이언트 ID로 주석을 답니다. [az aks get-credentials][az-aks-get-credentials] 명령을 사용하고 클러스터 이름과 리소스 그룹 이름의 값을 바꿉니다.

```azurecli-interactive
az aks get-credentials --name "${CLUSTER_NAME}" --resource-group "${RESOURCE_GROUP}"
```

Azure CLI에서 다음 여러 줄 입력을 복사하여 붙여넣습니다.

```azurecli-interactive
export SERVICE_ACCOUNT_NAMESPACE="default"
export SERVICE_ACCOUNT_NAME="workload-identity-sa$RANDOM_ID"
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  annotations:
    azure.workload.identity/client-id: "${USER_ASSIGNED_CLIENT_ID}"
  name: "${SERVICE_ACCOUNT_NAME}"
  namespace: "${SERVICE_ACCOUNT_NAMESPACE}"
EOF
```

다음 출력은 워크로드 ID의 성공적인 만들기를 보여 줍니다.

```output
serviceaccount/workload-identity-sa created
```

## 페더레이션된 ID 자격 증명 만들기

[az identity federated-credential create][az-identity-federated-credential-create] 명령을 호출하여 관리 ID, 서비스 계정 발급자 및 주체 간에 페더레이션 ID 자격 증명을 만듭니다. Microsoft Entra의 페더레이션된 ID 자격 증명에 대한 자세한 내용은 [Microsoft Entra ID의 페더레이션된 ID 자격 증명 개요][federated-identity-credential]를 참조하세요.

```azurecli-interactive
export FEDERATED_IDENTITY_CREDENTIAL_NAME="myFedIdentity$RANDOM_ID"
az identity federated-credential create \
    --name ${FEDERATED_IDENTITY_CREDENTIAL_NAME} \
    --identity-name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --issuer "${AKS_OIDC_ISSUER}" \
    --subject system:serviceaccount:"${SERVICE_ACCOUNT_NAMESPACE}":"${SERVICE_ACCOUNT_NAME}" \
    --audience api://AzureADTokenExchange
```

> [!NOTE]
> 페더레이션된 ID 자격 증명이 추가된 후 전파되는 데 몇 초 정도 걸립니다. 페더레이션된 ID 자격 증명을 추가한 직후 토큰 요청이 이루어지면 캐시가 새로 고쳐질 때까지 요청이 실패할 수 있습니다. 이 문제를 방지하려면 페더레이션 ID 자격 증명을 추가한 후 약간의 지연을 추가하면 됩니다.

## 응용 프로그램 배포

애플리케이션 Pod를 배포할 때 매니페스트는 **Kubernetes 서비스 계정 만들기** 단계에서 만든 서비스 계정을 참조해야 합니다. 다음 매니페스트는 계정, 특히 _메타데이터\namespace_ 및 _spec\serviceAccountName_ 속성을 참조하는 방법을 보여 줍니다. `<image>`에 이미지를 지정하고 `<containerName>`에 컨테이너 이름을 지정해야 합니다.

```bash
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: sample-workload-identity
  namespace: ${SERVICE_ACCOUNT_NAMESPACE}  # Replace with your namespace
  labels:
    azure.workload.identity/use: "true"  # Required. Only pods with this label can use workload identity.
spec:
  serviceAccountName: ${SERVICE_ACCOUNT_NAME}  # Replace with your service account name
  containers:
    - name: rabbitmq  # Replace with your container name
      image: mcr.microsoft.com/mirror/docker/library/rabbitmq:3.10-management-alpine  # Replace with your Docker image
      ports:
        - containerPort: 5672
          name: rabbitmq-amqp
        - containerPort: 15672
          name: rabbitmq-http
      env:
        - name: RABBITMQ_DEFAULT_USER
          value: "username"
        - name: RABBITMQ_DEFAULT_PASS
          value: "password"
      resources:
        requests:
          cpu: 10m
          memory: 128Mi
        limits:
          cpu: 250m
          memory: 256Mi
EOF
```

> [!IMPORTANT]
> 워크로드 ID를 사용하는 애플리케이션 Pod의 사양에 `azure.workload.identity/use: "true"` 레이블이 포함되어 있는지 확인합니다. 그렇지 않으면 Pod가 다시 시작된 후 실패합니다.

## Azure Key Vault에 액세스할 수 있는 권한 부여

이 단계의 지침에서는 Pod에서 Azure Key Vault에 있는 비밀, 키 또는 인증서에 액세스하는 방법을 보여 줍니다. 이 섹션의 예제에서는 워크로드 ID에 대한 키 자격 증명 모음의 비밀에 대한 액세스를 구성하지만 키 또는 인증서에 대한 액세스를 구성하는 유사한 단계를 수행할 수 있습니다.

다음 예에서는 Azure RBAC(Azure 역할 기반 액세스 제어) 권한 모델을 사용하여 Pod에 키 자격 증명 모음에 대한 액세스 권한을 부여하는 방법을 보여 줍니다. Azure Key Vault용 Azure RBAC 권한 모델에 대한 자세한 내용은 [Azure RBAC를 사용하여 애플리케이션에 Azure Key Vault에 액세스할 수 있는 권한 부여](/azure/key-vault/general/rbac-guide)를 참조하세요.

1. 제거 방지 및 RBAC 권한 부여가 사용하도록 설정된 키 자격 증명 모음을 만듭니다. 제거 방지 및 RBAC 권한 부여 모두에 대해 구성된 경우 기존 키 자격 증명 모음을 사용할 수도 있습니다.

    ```azurecli-interactive
    export KEYVAULT_NAME="keyvault-workload-id$RANDOM_ID"
    # Ensure the key vault name is between 3-24 characters
    if [ ${#KEYVAULT_NAME} -gt 24 ]; then
        KEYVAULT_NAME="${KEYVAULT_NAME:0:24}"
    fi
    az keyvault create \
        --name "${KEYVAULT_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --location "${LOCATION}" \
        --enable-purge-protection \
        --enable-rbac-authorization 
    ```

1. 새 키 자격 증명 모음에서 비밀을 만들 수 있도록 RBAC [키 자격 증명 모음 비밀 담당자](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-officer) 역할을 자신에게 할당합니다.

    ```azurecli-interactive
    export KEYVAULT_RESOURCE_ID=$(az keyvault show --resource-group "${KEYVAULT_RESOURCE_GROUP}" \
        --name "${KEYVAULT_NAME}" \
        --query id \
        --output tsv)

    export CALLER_OBJECT_ID=$(az ad signed-in-user show --query objectId -o tsv)

    az role assignment create --assignee "${CALLER_OBJECT_ID}" \
    --role "Key Vault Secrets Officer" \
    --scope "${KEYVAULT_RESOURCE_ID}"
    ```

1. 키 자격 증명 모음에서 비밀을 만듭니다.

    ```azurecli-interactive
    export KEYVAULT_SECRET_NAME="my-secret$RANDOM_ID"
    az keyvault secret set \
        --vault-name "${KEYVAULT_NAME}" \
        --name "${KEYVAULT_SECRET_NAME}" \
        --value "Hello\!"
    ```

1. 이전에 만든 사용자 할당 관리 ID에 [Key Vault 비밀 사용자](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-user) 역할을 할당합니다. 이 단계에서는 관리 ID에 키 자격 증명 모음에서 비밀을 읽을 수 있는 권한을 부여합니다.

    ```azurecli-interactive
    export IDENTITY_PRINCIPAL_ID=$(az identity show \
        --name "${USER_ASSIGNED_IDENTITY_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --query principalId \
        --output tsv)
    
    az role assignment create \
        --assignee-object-id "${IDENTITY_PRINCIPAL_ID}" \
        --role "Key Vault Secrets User" \
        --scope "${KEYVAULT_RESOURCE_ID}" \
        --assignee-principal-type ServicePrincipal
    ```

1. 키 자격 증명 모음 URL에 대한 환경 변수를 만듭니다.

    ```azurecli-interactive
    export KEYVAULT_URL="$(az keyvault show \
        --resource-group ${RESOURCE_GROUP} \
        --name ${KEYVAULT_NAME} \
        --query properties.vaultUri \
        --output tsv)"
    ```

1. 서비스 계정 및 키 자격 증명 모음 URL을 참조하는 Pod를 배포합니다.

    ```bash
    cat <<EOF | kubectl apply -f -
    apiVersion: v1
    kind: Pod
    metadata:
    name: sample-workload-identity-key-vault
    namespace: ${SERVICE_ACCOUNT_NAMESPACE}
    labels:
        azure.workload.identity/use: "true"
    spec:
    serviceAccountName: ${SERVICE_ACCOUNT_NAME}
    containers:
        - image: ghcr.io/azure/azure-workload-identity/msal-go
        name: oidc
        env:
            - name: KEYVAULT_URL
            value: ${KEYVAULT_URL}
            - name: SECRET_NAME
            value: ${KEYVAULT_SECRET_NAME}
    nodeSelector:
        kubernetes.io/os: linux
    EOF
    ```

모든 속성이 webhook에 의해 제대로 삽입되는지 여부를 확인하려면 [kubectl describe][kubectl-describe] 명령을 사용합니다.

```azurecli-interactive
kubectl describe pod sample-workload-identity-key-vault | grep "SECRET_NAME:"
```

성공하면 출력은 다음과 유사해야 합니다.

```output
      SECRET_NAME:                 ${KEYVAULT_SECRET_NAME}
```

Pod가 토큰을 가져와 리소스에 액세스할 수 있는지 확인하려면 kubectl logs 명령을 사용합니다.

```azurecli-interactive
kubectl logs sample-workload-identity-key-vault
```

성공하면 출력은 다음과 유사해야 합니다.

```output
I0114 10:35:09.795900       1 main.go:63] "successfully got secret" secret="Hello\\!"
```

> [!IMPORTANT]
> Azure RBAC 역할 할당이 전파되는 데 최대 10분이 걸릴 수 있습니다. Pod가 비밀에 액세스할 수 없는 경우 역할 할당이 전파될 때까지 기다려야 할 수 있습니다. 자세한 내용은 [Azure RBAC 문제 해결](/azure/role-based-access-control/troubleshooting#)을 참조하세요.

## 워크로드 ID 사용 중지

사용하도록 설정 및 구성된 AKS 클러스터에서 Microsoft Entra 워크로드 ID를 사용하지 않도록 설정하려면 다음 명령을 실행할 수 있습니다.

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --disable-workload-identity
```

## 다음 단계

이 문서에서는 Kubernetes 클러스터를 배포하고 애플리케이션 워크로드가 해당 자격 증명으로 인증하도록 준비하기 위해 워크로드 ID를 사용하도록 구성했습니다. 이제 애플리케이션을 배포하고 최신 버전의 [Azure ID][azure-identity-libraries] 클라이언트 라이브러리와 함께 워크로드 ID를 사용하도록 구성할 준비가 되었습니다. 최신 클라이언트 라이브러리 버전을 사용하도록 애플리케이션을 다시 작성할 수 없는 경우 [애플리케이션 Pod를 설정][workload-identity-migration]하여 단기 마이그레이션 솔루션으로 워크로드 ID가 있는 관리 ID를 사용하여 인증할 수 있습니다.

[서비스 커넥터](/azure/service-connector/overview) 통합은 AKS 워크로드와 Azure 지원 서비스에 대한 연결 구성을 간소화하는 데 도움이 됩니다. 인증 및 네트워크 구성을 안전하게 처리하고 Azure 서비스에 연결하기 위한 모범 사례를 따릅니다. 자세한 내용은 [워크로드 ID를 사용하여 AKS에서 Azure OpenAI Service에 연결](/azure/service-connector/tutorial-python-aks-openai-workload-identity) 및 [서비스 커넥터 소개](https://azure.github.io/AKS/2024/05/23/service-connector-intro)를 참조하세요.

<!-- EXTERNAL LINKS -->
[kubectl-describe]: https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#describe

<!-- INTERNAL LINKS -->
[kubernetes-concepts]: concepts-clusters-workloads.md
[workload-identity-overview]: workload-identity-overview.md
[azure-resource-group]: /azure/azure-resource-manager/management/overview
[az-group-create]: /cli/azure/group#az-group-create
[aks-identity-concepts]: concepts-identity.md
[federated-identity-credential]: /graph/api/resources/federatedidentitycredentials-overview
[tutorial-python-aks-storage-workload-identity]: /azure/service-connector/tutorial-python-aks-storage-workload-identity
[az-aks-create]: /cli/azure/aks#az-aks-create
[az aks update]: /cli/azure/aks#az-aks-update
[aks-two-resource-groups]: faq.yml
[az-account-set]: /cli/azure/account#az-account-set
[az-identity-create]: /cli/azure/identity#az-identity-create
[az-aks-get-credentials]: /cli/azure/aks#az-aks-get-credentials
[az-identity-federated-credential-create]: /cli/azure/identity/federated-credential#az-identity-federated-credential-create
[workload-identity-migration]: workload-identity-migrate-from-pod-identity.md
[azure-identity-libraries]: /azure/active-directory/develop/reference-v2-libraries