---
title: 为 AKS 群集部署和配置工作负载标识
description: 这篇 Azure Kubernetes 服务 (AKS) 文章介绍如何部署一个 Azure Kubernetes 服务群集，并为它配置 Microsoft Entra Workload ID。
author: tamram
ms.topic: article
ms.subservice: aks-security
ms.custom: devx-track-azurecli
ms.date: 05/28/2024
ms.author: tamram
---

# 在 Azure Kubernetes 服务 (AKS) 群集上部署和配置工作负荷标识

Azure Kubernetes 服务 (AKS) 是可用于快速部署和管理 Kubernetes 群集的托管式 Kubernetes 服务。 本文介绍如何：

* 使用 Azure CLI 部署一个包含 OpenID Connect 颁发者和 Microsoft Entra 工作负载 ID 的 AKS 群集。
* 创建 Microsoft Entra 工作负载 ID 和 Kubernetes 服务帐户。
* 为令牌联合配置托管标识。
* 部署工作负载并使用工作负载标识验证身份验证。
* （可选）向群集中的 Pod 授予访问 Azure Key Vault 中机密的权限。

本文假定你对 Kubernetes 概念有基本的了解。 有关详细信息，请参阅 [Azure Kubernetes 服务 (AKS) 的 Kubernetes 核心概念][kubernetes-concepts]。 如果你不熟悉 Microsoft Entra Workload ID，请参阅下面的[概述][workload-identity-overview]一文。

## 先决条件

* [!INCLUDE [quickstarts-free-trial-note](~/reusable-content/ce-skilling/azure/includes/quickstarts-free-trial-note.md)]
* 本文需要 2.47.0 或更高版本的 Azure CLI。 如果使用 Azure Cloud Shell，则最新版本已安装。
* 确保用于创建群集的标识具有合适的的最低权限。 有关 AKS 的访问和标识的详细信息，请参阅 [Azure Kubernetes 服务 (AKS) 的访问和标识选项][aks-identity-concepts]。
* 如果有多个 Azure 订阅，请使用 [az account set][az-account-set] 命令选择应在其中计收资源费用的相应订阅 ID。

> [!NOTE]
> 可以使用服务连接器自动配置某些步骤__。 另请参阅：[教程：使用工作负载标识通过服务连接器连接到 Azure Kubernetes 服务 (AKS) 中的 Azure 存储帐户][tutorial-python-aks-storage-workload-identity]。

## 创建资源组

[Azure 资源组][azure-resource-group]是用于部署和管理 Azure 资源的逻辑组。 创建资源组时，系统会提示你指定一个位置。 此位置是资源组元数据的存储位置，也是资源在 Azure 中运行的位置（如果你在创建资源期间未指定其他区域）。

通过调用 [az group create][az-group-create] 命令创建资源组。

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export RESOURCE_GROUP="myResourceGroup$RANDOM_ID"
export LOCATION="centralindia"
az group create --name "${RESOURCE_GROUP}" --location "${LOCATION}"
```

以下输出示例显示成功创建资源组：

结果：
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

## 创建 AKS 群集

使用带有 `--enable-oidc-issuer` 参数的 [az aks create][az-aks-create] 命令创建 AKS 群集，以启用 OIDC 颁发者。 以下示例会创建具有一个节点的群集：

```azurecli-interactive
export CLUSTER_NAME="myAKSCluster$RANDOM_ID"
az aks create \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity \
    --generate-ssh-keys
```

片刻之后，该命令将会完成，并返回有关群集的 JSON 格式信息。

> [!NOTE]
> 创建 AKS 群集时，会自动创建另一个资源组来存储 AKS 资源。 有关详细信息，请参阅[为何使用 AKS 创建两个资源组？][aks-two-resource-groups]。

## 更新现有的 AKS 群集

可以通过调用带有 `--enable-oidc-issuer` 和 `--enable-workload-identity` 参数的 [az aks update][az aks update] 命令更新 AKS 群集，以使用 OIDC 颁发者并启用工作负载标识。 以下示例更新现有群集：

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity
```

## 检索 OIDC 颁发者 URL

若要获取 OIDC 颁发者 URL 并将其保存到环境变量，请运行以下命令：

```azurecli-interactive
export AKS_OIDC_ISSUER="$(az aks show --name "${CLUSTER_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --query "oidcIssuerProfile.issuerUrl" \
    --output tsv)"
```

环境变量应包含类似于以下示例的证书颁发者 URL：

```output
https://eastus.oic.prod-aks.azure.com/00000000-0000-0000-0000-000000000000/11111111-1111-1111-1111-111111111111/
```

默认情况下，颁发者设置为使用基 URL `https://{region}.oic.prod-aks.azure.com/{tenant_id}/{uuid}`，其中 `{region}` 的值与部署 AKS 群集的位置相匹配。 值 `{uuid}` 表示 OIDC 密钥，它是为每个群集随机生成的不可变的 guid。

## 创建托管标识

调用 [az identity create][az-identity-create] 命令创建托管标识。

```azurecli-interactive
export SUBSCRIPTION="$(az account show --query id --output tsv)"
export USER_ASSIGNED_IDENTITY_NAME="myIdentity$RANDOM_ID"
az identity create \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --location "${LOCATION}" \
    --subscription "${SUBSCRIPTION}"
```

以下输出示例演示如何成功创建托管标识：

结果：
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

接下来，为托管标识客户端 ID 创建一个变量。

```azurecli-interactive
export USER_ASSIGNED_CLIENT_ID="$(az identity show \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --query 'clientId' \
    --output tsv)"
```

## 创建 Kubernetes 服务帐户

创建一个 Kubernetes 服务帐户，并使用在上一步创建的托管标识的客户端 ID 对其进行批注。 使用 [az aks get-credentials][az-aks-get-credentials] 命令，并替换群集名称和资源组名称的值。

```azurecli-interactive
az aks get-credentials --name "${CLUSTER_NAME}" --resource-group "${RESOURCE_GROUP}"
```

将以下多行输入复制粘贴到 Azure CLI 中。

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

成功创建工作负载标识后的输出如下所示：

```output
serviceaccount/workload-identity-sa created
```

## 创建联合标识凭据

调用 [az identity federated-credential create][az-identity-federated-credential-create] 命令在托管标识、服务帐户颁发者和使用者之间创建联合标识凭据。 有关 Microsoft Entra 中联合标识凭据的详细信息，请参阅 [Microsoft Entra ID 中的联合标识凭据概述][federated-identity-credential]。

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
> 联合标识凭据在添加后需要几秒钟的时间才能传播。 如果在添加联合标识凭据后立即发出令牌请求，则在刷新缓存之前，请求可能会失败。 若要避免此问题，可以在添加联合标识凭据后添加轻微的延迟。

## 部署应用程序

部署应用程序 Pod 时，清单应引用在**创建 Kubernetes 服务帐户**步骤中创建的服务帐户。 以下清单演示如何引用帐户，特别是 metadata\namespace 和 spec\serviceAccountName 属性____。 请确保为 `<image>` 指定映像，并为 `<containerName>` 指定容器名称：

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
> 确保使用工作负载标识的应用程序 Pod 在 Pod 规范中包含标签 `azure.workload.identity/use: "true"`。否则，Pod 在重启后将失败。

## 授予访问 Azure Key Vault 的权限

此步骤中的说明演示如何从 Pod 访问 Azure Key Vault 中的机密、密钥或证书。 本部分中的示例配置对工作负荷标识密钥保管库中机密的访问权限，但可以执行类似的步骤来配置对密钥或证书的访问。

以下示例演示如何使用 Azure 基于角色的访问控制 (Azure RBAC) 权限模型向 Pod 授予访问密钥保管库的权限。 有关 Azure Key Vault 的 Azure RBAC 权限模型的详细信息，请参阅[使用 Azure RBAC 授予应用程序访问 Azure Key Vault 的权限](/azure/key-vault/general/rbac-guide)。

1. 创建启用了清除保护功能和 RBAC 授权的新密钥保管库。 如果为清除保护功能和 RBAC 授权配置了现有密钥保管库，也可以使用它：

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

1. 将 RBAC [密钥保管库机密主管](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-officer)角色分配给自己，以便可以在新的密钥保管库中创建机密：

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

1. 在密钥保管库中创建机密：

    ```azurecli-interactive
    export KEYVAULT_SECRET_NAME="my-secret$RANDOM_ID"
    az keyvault secret set \
        --vault-name "${KEYVAULT_NAME}" \
        --name "${KEYVAULT_SECRET_NAME}" \
        --value "Hello\!"
    ```

1. 将[密钥保管库机密用户](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-user)角色分配给之前创建的用户分配的托管标识。 此步骤授予托管标识从密钥保管库读取机密的权限：

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

1. 为密钥保管库 URL 创建环境变量：

    ```azurecli-interactive
    export KEYVAULT_URL="$(az keyvault show \
        --resource-group ${RESOURCE_GROUP} \
        --name ${KEYVAULT_NAME} \
        --query properties.vaultUri \
        --output tsv)"
    ```

1. 部署引用上服务帐户和密钥保管库 URL 的 Pod：

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

若要检查 webhook 是否正确注入了所有属性，请使用 [kubectl describe][kubectl-describe] 命令：

```azurecli-interactive
kubectl describe pod sample-workload-identity-key-vault | grep "SECRET_NAME:"
```

如果成功，输出应类似于以下示例：

```output
      SECRET_NAME:                 ${KEYVAULT_SECRET_NAME}
```

若要验证 Pod 是否能够获取令牌和访问资源，请使用 kubectl logs 命令：

```azurecli-interactive
kubectl logs sample-workload-identity-key-vault
```

如果成功，输出应类似于以下示例：

```output
I0114 10:35:09.795900       1 main.go:63] "successfully got secret" secret="Hello\\!"
```

> [!IMPORTANT]
> Azure RBAC 角色分配可能需要最多十分钟的时间进行传播。 如果 Pod 无法访问机密，则可能需要等待角色分配传播。 有关详细信息，请参阅 [Azure RBAC 疑难解答](/azure/role-based-access-control/troubleshooting#)。

## 禁用工作负载标识

若要在已启用和配置的 AKS 群集上禁用 Microsoft Entra Workload ID，可以运行以下命令：

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --disable-workload-identity
```

## 后续步骤

在本文中，你部署了 Kubernetes 群集并将其配置为使用工作负荷标识，为应用程序工作负荷使用该凭据进行身份验证做好准备。 现在，你已准备好部署应用程序并将其配置为将工作负荷标识与最新版 [Azure 标识][azure-identity-libraries]客户端库配合使用。 如果无法重写应用程序以使用最新的客户端库版本，则可以[设置应用程序 Pod][workload-identity-migration]，以使用托管标识和工作负荷标识作为短期迁移解决方案进行身份验证。

[服务连接器](/azure/service-connector/overview)集成有助于简化 AKS 工作负载和 Azure 支持服务的连接配置。 它可以安全地处理身份验证和网络配置，并遵循用于连接到 Azure 服务的最佳做法。 有关详细信息，请参阅[在 AKS 中使用工作负载标识连接到 Azure OpenAI 服务](/azure/service-connector/tutorial-python-aks-openai-workload-identity)以及[服务连接器简介](https://azure.github.io/AKS/2024/05/23/service-connector-intro)。

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