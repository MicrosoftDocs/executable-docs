---
title: 使用工作負載身分識別來部署和設定 AKS 叢集
description: 在本 Azure Kubernetes Service (AKS) 文章中，您會部署 Azure Kubernetes Service 叢集，並使用 Microsoft Entra 工作負載識別碼進行設定。
author: tamram
ms.topic: article
ms.subservice: aks-security
ms.custom: devx-track-azurecli
ms.date: 05/28/2024
ms.author: tamram
---

# 在 Azure Kubernetes Service (AKS) 叢集上部署和設定工作負載身分識別

Azure Kubernetes Service (AKS) 是受控 Kubernetes 服務，可讓您快速部署及管理 Kubernetes 叢集。 本文章說明如何：

* 使用 Azure CLI 與 OpenID Connect 簽發者和 Microsoft Entra 工作負載 ID 來部署 AKS 叢集。
* 建立 Microsoft Entra 工作負載識別碼和 Kube 服務帳戶。
* 設定權杖同盟的受控識別。
* 部署工作負載，並使用工作負載身分識別驗證。
* 選擇性地向叢集中的 Pod 授與 Azure 金鑰保存庫中秘密的存取權。

本文假設您對 Kubernetes 概念有基本瞭解。 如需詳細資訊，請參閱 [Azure Kubernetes Services (AKS) 的 Kubernetes 核心概念][kubernetes-concepts]。 如果您不熟悉 Microsoft Entra 工作負載識別碼，則請參閱下列[概觀][workload-identity-overview]文章。

## 必要條件

* [!INCLUDE [quickstarts-free-trial-note](~/reusable-content/ce-skilling/azure/includes/quickstarts-free-trial-note.md)]
* 本文必須使用 Azure CLI 2.47.0 版或更新版本。 如果您是使用 Azure Cloud Shell，就已安裝最新版本。
* 確保您用來建立叢集的身分識別擁有適當的最低權限。 如需 AKS 存取和身分識別的詳細資訊，請參閱 [Azure Kubernetes Service (AKS) 的存取與身分識別選項][aks-identity-concepts]。
* 如果您有多個 Azure 訂用帳戶，請使用 [az account set][az-account-set] 命令來選取應對資源計費的適當訂用帳戶識別碼。

> [!NOTE]
> 您可以使用「服務連接器」__ 來協助您自動設定某些步驟。 另請參閱：[教學課程：使用工作負載身分識別以服務連接器連線到 Azure Kubernetes Service (AKS) 中的 Azure 儲存體帳戶][tutorial-python-aks-storage-workload-identity]。

## 建立資源群組

[Azure 資源群組][azure-resource-group]是部署及管理 Azure 資源所在的邏輯群組。 建立資源群組時，系統會提示您指定位置。 此位置是資源群組中繼資料的儲存位置，如果未在資源建立期間指定另一個區域，此位置也會是您在 Azure 中執行資源的位置。

呼叫 [az group create][az-group-create] 命令來建立資源群組：

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export RESOURCE_GROUP="myResourceGroup$RANDOM_ID"
export LOCATION="centralindia"
az group create --name "${RESOURCE_GROUP}" --location "${LOCATION}"
```

下列輸出範例顯示資源群組建立成功：

結果：
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

## 建立 AKS 叢集

使用 [az aks create][az-aks-create] 命令搭配 `--enable-oidc-issuer` 參數來建立 AKS 叢集，以啟用 OIDC 簽發者。 下列範例會建立具有單一節點的叢集：

```azurecli-interactive
export CLUSTER_NAME="myAKSCluster$RANDOM_ID"
az aks create \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity \
    --generate-ssh-keys
```

幾分鐘後，命令會完成並傳回關於叢集的 JSON 格式資訊。

> [!NOTE]
> 建立 AKS 叢集時，系統會自動建立第二個資源群組來儲存 AKS 資源。 如需詳細資訊，請參閱[為何會使用 AKS 建立兩個資源群組？][aks-two-resource-groups]。

## 更新現有的 AKS 叢集

您可以呼叫 [az aks update][az aks update] 命令搭配 `--enable-oidc-issuer` 和 `--enable-workload-identity` 參數，將 AKS 叢集更新為使用 OIDC 簽發者並啟用工作負載身分識別。 下列範例會更新現有叢集：

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity
```

## 擷取 OIDC 簽發者 URL

若要取得 OIDC 簽發者 URL 並將其儲存至環境變數，請執行下列命令：

```azurecli-interactive
export AKS_OIDC_ISSUER="$(az aks show --name "${CLUSTER_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --query "oidcIssuerProfile.issuerUrl" \
    --output tsv)"
```

環境變數應包含與下列範例類似的簽發者 URL：

```output
https://eastus.oic.prod-aks.azure.com/00000000-0000-0000-0000-000000000000/11111111-1111-1111-1111-111111111111/
```

根據預設，簽發者會設定為使用基底 URL `https://{region}.oic.prod-aks.azure.com/{tenant_id}/{uuid}`，其中 `{region}` 的值會符合作為 AKS 叢集部署目的地的位置。 值 `{uuid}` 代表 OIDC 金鑰，這是為每個叢集隨機產生的 GUID，是不可變的。

## 建立受控識別

呼叫 [az identity create][az-identity-create] 命令來建立受控識別。

```azurecli-interactive
export SUBSCRIPTION="$(az account show --query id --output tsv)"
export USER_ASSIGNED_IDENTITY_NAME="myIdentity$RANDOM_ID"
az identity create \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --location "${LOCATION}" \
    --subscription "${SUBSCRIPTION}"
```

下列輸出範例顯示成功建立受控識別：

結果：
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

接下來，為受控識別的用戶端識別碼建立變數。

```azurecli-interactive
export USER_ASSIGNED_CLIENT_ID="$(az identity show \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --query 'clientId' \
    --output tsv)"
```

## 建立 Kubernetes 服務帳戶

建立 Kubernetes 服務帳戶，並使用在上一個步驟中建立之受控識別的用戶端識別碼加以標註。 使用 [az aks get-credentials][az-aks-get-credentials] 命令，並取代叢集名稱和資源群組名稱的值。

```azurecli-interactive
az aks get-credentials --name "${CLUSTER_NAME}" --resource-group "${RESOURCE_GROUP}"
```

在 Azure CLI 中複製並貼上下列多行輸入。

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

下列輸出顯示工作負載身分識別建立成功：

```output
serviceaccount/workload-identity-sa created
```

## 建立同盟身分識別認證

呼叫 [az identity federated-credential create][az-identity-federated-credential-create] 命令，在受控識別、服務帳戶簽發者與主體之間建立同盟身分識別認證。 如需 Microsoft Entra 中同盟身分識別認證的詳細資訊，請參閱 [Microsoft Entra ID 中的同盟身分識別認證概觀][federated-identity-credential]。

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
> 同盟身分識別認證在新增後，需要幾秒鐘的時間來散佈。 如果在新增同盟身分識別認證後立即提出權杖要求，在快取重新整理之前，要求可能會失敗。 若要避免此問題，您可以在新增同盟身分識別認證之後稍待片刻，再提出權杖要求。

## 部署應用程式

當您部署應用程式 Pod 時，資訊清單應該參考**建立 Kubernetes 服務帳戶**步驟中所建立的服務帳戶。 下列資訊清單顯示如何參考帳戶，特別是 metadata\namespace__ 和 spec\serviceAccountName__ 屬性。 請務必為 `<image>` 指定映像，並為 `<containerName>` 指定容器名稱：

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
> 請確定使用工作負載身分識別的應用程式 Pod 有在 Pod 規格中納入標籤 `azure.workload.identity/use: "true"`。否則，Pod 會於重新啟動後失敗。

## 授與存取 Azure Key Vault 的權限

此步驟中的指示會示範如何從 Pod 存取 Azure 金鑰保存庫中的秘密、金鑰或憑證。 本節中的範例會設定工作負載身分識別密鑰保存庫中秘密的存取權，但您可以執行類似的步驟來設定密鑰或憑證的存取權。

下列範例會示範如何使用 Azure 角色型存取控制 (Azure RBAC) 權限模型，向 Pod 授與金鑰保存庫的存取權。 如需 Azure Key Vault 的 Azure RBAC 權限模型詳細資訊，請參閱[使用 Azure RBAC 向應用程式授與存取 Azure 金鑰保存庫的權限](/azure/key-vault/general/rbac-guide)。

1. 建立已啟用清除保護和 RBAC 授權的金鑰保存庫。 如果現有的金鑰保存庫已針對清除保護和 RBAC 授權進行設定，您也可以使用現有的金鑰保存庫：

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

1. 向自己指派 RBAC 的 [Key Vault 祕密長](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-officer)角色，以便您可以在新的金鑰保存庫中建立秘密：

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

1. 在金鑰保存庫中建立秘密：

    ```azurecli-interactive
    export KEYVAULT_SECRET_NAME="my-secret$RANDOM_ID"
    az keyvault secret set \
        --vault-name "${KEYVAULT_NAME}" \
        --name "${KEYVAULT_SECRET_NAME}" \
        --value "Hello\!"
    ```

1. 向您先前建立的使用者指派的受控識別指派 [Key Vault 秘密使用者](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-user)角色。 此步驟會向受控識別提供從金鑰保存庫讀取秘密的權限：

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

1. 為金鑰儲存庫 URL 建立環境變數：

    ```azurecli-interactive
    export KEYVAULT_URL="$(az keyvault show \
        --resource-group ${RESOURCE_GROUP} \
        --name ${KEYVAULT_NAME} \
        --query properties.vaultUri \
        --output tsv)"
    ```

1. 部署會參考服務帳戶和金鑰保存庫 URL 的 Pod：

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

若要檢查 Webhook 是否已正確插入所有屬性，請使用 [kubectl describe][kubectl-describe] 命令：

```azurecli-interactive
kubectl describe pod sample-workload-identity-key-vault | grep "SECRET_NAME:"
```

如果成功，則輸出應該與下列輸出類似：

```output
      SECRET_NAME:                 ${KEYVAULT_SECRET_NAME}
```

若要確認 Pod 能夠取得權杖並存取資源，請使用 kubectl logs 命令：

```azurecli-interactive
kubectl logs sample-workload-identity-key-vault
```

如果成功，則輸出應該與下列輸出類似：

```output
I0114 10:35:09.795900       1 main.go:63] "successfully got secret" secret="Hello\\!"
```

> [!IMPORTANT]
> Azure RBAC 角色指派最多需要十分鐘來散佈。 如果 Pod 無法存取秘密，您可能需要等候角色指派散佈開來。 如需詳細資訊，請參閱[針對 Azure RBAC 進行疑難排解](/azure/role-based-access-control/troubleshooting#)。

## 停用工作負載身分識別

若要在已啟用並設定 Microsoft Entra 工作負載識別碼的 AKS 叢集上將其停用，您可以執行下列命令：

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --disable-workload-identity
```

## 下一步

在本文中，您已部署 Kubernetes 叢集，並將其設定為使用工作負載身分識別來準備應用程式工作負載，以使用該認證進行驗證。 現在您已準備好部署應用程式，並將其設定為使用工作負載身分識別搭配最新版的 [Azure 身分識別][azure-identity-libraries]用戶端程式庫。 如果您無法將應用程式重寫為使用最新的用戶端程式庫版本，您可以[設定應用程式 Pod][workload-identity-migration]，以使用受控識別搭配工作負載身分識別進行驗證，作為短期移轉解決方案。

[服務連接器](/azure/service-connector/overview)整合可協助簡化 AKS 工作負載和 Azure 備份服務的連線設定。 其會安全地處理驗證和網路設定，並遵循連線至 Azure 服務的最佳做法。 如需詳細資訊，請參閱[使用工作負載身分識別連線到 AKS 中的 Azure OpenAI 服務](/azure/service-connector/tutorial-python-aks-openai-workload-identity)和[服務連接器簡介](https://azure.github.io/AKS/2024/05/23/service-connector-intro)。

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