---
title: ワークロード ID を使用して AKS クラスターをデプロイして構成する
description: この Azure Kubernetes Service (AKS) の記事では、Azure Kubernetes Service クラスターをデプロイし、Microsoft Entra ワークロード ID を使用して構成します。
author: tamram
ms.topic: article
ms.subservice: aks-security
ms.custom: devx-track-azurecli
ms.date: 05/28/2024
ms.author: tamram
---

# Azure Kubernetes Service (AKS) クラスターでワークロード ID をデプロイして構成する

Azure Kubernetes Service (AKS) は、クラスターをすばやくデプロイおよび管理することができる、マネージド Kubernetes サービスです。 この記事では、次の方法について説明します:

* OpenID Connect 発行者と Microsoft Entra ワークロード ID を含む Azure CLI を使用して AKS クラスターをデプロイします。
* Microsoft Entra ワークロード ID と Kubernetes サービス アカウントを作成します。
* トークンのフェデレーション用にマネージド ID を構成する。
* ワークロードをデプロイし、ワークロード ID を使用して認証を確認します。
* 必要に応じて、クラスター内のポッドに Azure Key Vault 内のシークレットへのアクセス権を付与します。

この記事では、Kubernetes の基本的な概念を理解していることを前提としています。 詳細については、「[Azure Kubernetes Services (AKS) における Kubernetes の中心概念][kubernetes-concepts]」を参照してください。 Microsoft Entra ワークロード ID に慣れていない場合は、次の「[概要][workload-identity-overview]」の記事を参照してください。

## 前提条件

* [!INCLUDE [quickstarts-free-trial-note](~/reusable-content/ce-skilling/azure/includes/quickstarts-free-trial-note.md)]
* この記事では、Azure CLI のバージョン 2.47.0 以降が必要です。 Azure Cloud Shell を使用している場合は、最新バージョンが既にインストールされています。
* クラスターの作成に使用している ID に、適切な最小限のアクセス許可が与えられていることを確認します。 AKS のアクセスと ID の情報については、「[Azure Kubernetes Service (AKS) でのアクセスと ID オプション][aks-identity-concepts]」を参照してください。
* 複数の Azure サブスクリプションをお持ちの場合は、[az account set][az-account-set] コマンドを使用して、リソースが課金の対象となる適切なサブスクリプション ID を選択してください。

> [!NOTE]
> 一部の手順を自動的に構成するのに役立てるために、_Service Connector_ を使用できます。 「[チュートリアル: ワークロード ID を使用して Service Connector で Azure Kubernetes Service (AKS) の Azure ストレージ アカウントに接続する][tutorial-python-aks-storage-workload-identity]」も参照してください。

## リソース グループを作成する

[Azure リソース グループ][azure-resource-group]は、Azure リソースが展開され管理される論理グループです。 リソース グループを作成する際は、場所の指定を求めるプロンプトが表示されます。 この場所は、リソース グループのメタデータが格納される場所です。また、リソースの作成時に別のリージョンを指定しない場合は、Azure でリソースが実行される場所でもあります。

[az group create][az-group-create] コマンドを呼び出してリソース グループを作成します。

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export RESOURCE_GROUP="myResourceGroup$RANDOM_ID"
export LOCATION="centralindia"
az group create --name "${RESOURCE_GROUP}" --location "${LOCATION}"
```

次の出力例は、リソース グループの正常な作成を示しています。

結果:
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

## AKS クラスターを作成する

OIDC 発行者を有効にするには、[az aks create][az-aks-create] コマンドと `--enable-oidc-issuer` パラメーターを使って、AKS クラスターを作成します。 次の例では、1 つのノードを含むクラスターを作成します。

```azurecli-interactive
export CLUSTER_NAME="myAKSCluster$RANDOM_ID"
az aks create \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity \
    --generate-ssh-keys
```

数分後、コマンドが完了し、クラスターに関する情報が JSON 形式で返されます。

> [!NOTE]
> AKS クラスターを作成すると、AKS リソースを保存するための 2 つ目のリソース グループが自動的に作成されます。 詳細については、「[AKS と一緒にリソース グループが 2 つ作成されるのはなぜでしょうか?][aks-two-resource-groups]」を参照してください。

## 既存の AKS クラスターを更新する

OIDC 発行者を使用し、ワークロード ID を有効にするには、[az aks update][az aks update] コマンドを `--enable-oidc-issuer` および `--enable-workload-identity` パラメーターと一緒に使って呼び出し、AKS クラスターを更新できます。 次の例では、既存のクラスターを更新しています。

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity
```

## OIDC 発行者 URL を取得する

OIDC 発行者 URL を取得し、環境変数に保存するには、次のコマンドを実行します。

```azurecli-interactive
export AKS_OIDC_ISSUER="$(az aks show --name "${CLUSTER_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --query "oidcIssuerProfile.issuerUrl" \
    --output tsv)"
```

環境変数には、次の例のような発行者 URL が含まれている必要があります。

```output
https://eastus.oic.prod-aks.azure.com/00000000-0000-0000-0000-000000000000/11111111-1111-1111-1111-111111111111/
```

既定では、発行者はベース URL `https://{region}.oic.prod-aks.azure.com/{tenant_id}/{uuid}` を使用するように設定されています。ここで `{region}` の値は、AKS クラスターがデプロイされている場所と一致します。 値 `{uuid}` は、不変であるクラスターごとにランダムに生成される guid である OIDC キーを表します。

## マネージド ID の作成

[[az identity 作成]][az-identity-create] コマンドを呼び出して、マネージド ID を作成します。

```azurecli-interactive
export SUBSCRIPTION="$(az account show --query id --output tsv)"
export USER_ASSIGNED_IDENTITY_NAME="myIdentity$RANDOM_ID"
az identity create \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --location "${LOCATION}" \
    --subscription "${SUBSCRIPTION}"
```

次の出力例は、マネージド ID の正常な作成を示しています。

結果:
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

次に、マネージド ID のクライアント ID の変数を作成します。

```azurecli-interactive
export USER_ASSIGNED_CLIENT_ID="$(az identity show \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --query 'clientId' \
    --output tsv)"
```

## Kubernetes サービス アカウントを作成する

Kubernetes サービス アカウントを作成し、前の手順で作成したマネージド ID のクライアント ID で注釈を付けます。 [az aks バージョン変更資格情報][az-aks-get-credentials] コマンドを使用してクラスター名とリソース グループ名の既定値を置き換えます。

```azurecli-interactive
az aks get-credentials --name "${CLUSTER_NAME}" --resource-group "${RESOURCE_GROUP}"
```

次の複数行入力をコピーして Azure CLI に貼り付けます。

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

次の出力は、ワークロード ID の正常な作成を示しています。

```output
serviceaccount/workload-identity-sa created
```

## フェデレーション ID 資格情報を作成する

[az identity federated-credential create][az-identity-federated-credential-create] コマンドを呼び出して、マネージド ID、サービス アカウント発行者、サブジェクトの間にフェデレーション ID 資格情報を作成します。 Microsoft Entra のフェデレーション ID 資格情報の詳細については、[Microsoft Entra ID でのフェデレーション ID 資格情報の概要][federated-identity-credential]に関する記事を参照してください。

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
> フェデレーション ID 資格情報が追加された後に反映されるまでに数秒かかります。 フェデレーション ID 資格情報を追加した直後にトークン要求が行われると、キャッシュが更新されるまでの間、要求が失敗する可能性があります。 このイシューを回避するには、フェデレーション ID 資格情報を追加した後に若干の遅延を追加できます。

## アプリケーションをデプロイする

アプリケーション ポッドをデプロイする場合、マニフェストは、「**Kubernetes サービス アカウントの作成**」の手順で作成されたサービス アカウントを参照する必要があります。 次のマニフェストは、アカウント、具体的には _metadata\namespace_ プロパティと _spec\serviceAccountName_ プロパティを参照する方法を示しています。 `<image>` のイメージと、`<containerName>` のコンテナー名を指定してください。

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
> ワークロード ID を使用するアプリケーション ポッドのポッド仕様に、ラベル `azure.workload.identity/use: "true"` が含まれるようにします。それ以外の場合、ポッドは再起動後に失敗します。

## Azure Key Vault にアクセスするための権限を付与する

この手順の手順では、ポッドから Azure Key Vault 内のシークレット、キー、または証明書にアクセスする方法を示します。 このセクションの例では、ワークロード ID のキー コンテナー内のシークレットへのアクセスを構成しますが、同様の手順を実行してキーまたは証明書へのアクセスを構成できます。

次の例は、Azure ロールベースのアクセス制御 (Azure RBAC) アクセス許可モデルを使用して、ポッドにキー コンテナーへのアクセスを許可する方法を示しています。 Azure Key Vault の Azure RBAC アクセス許可モデルの詳細については、「[Azure RBAC を使用して Azure キー コンテナーへのアクセス許可をアプリケーションに付与する](/azure/key-vault/general/rbac-guide)」を参照してください。

1. 消去保護と RBAC 承認が有効になっているキー コンテナーを作成します。 既存のキー コンテナーが消去保護と RBAC 承認の両方に対して構成されている場合は、それを使用することもできます。

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

1. 新しいキー コンテナーにシークレットを作成できるように、RBAC [Key Vault Secrets Officer](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-officer) ロールを自分に割り当てます。

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

1. キー コンテナーにシークレットを作成します。

    ```azurecli-interactive
    export KEYVAULT_SECRET_NAME="my-secret$RANDOM_ID"
    az keyvault secret set \
        --vault-name "${KEYVAULT_NAME}" \
        --name "${KEYVAULT_SECRET_NAME}" \
        --value "Hello\!"
    ```

1. [Key Vault Secrets User](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-user) ロールを、前に作成したユーザー割り当てマネージド ID に割り当てます。 この手順では、キー コンテナーからシークレットを読み取るアクセス許可をマネージド ID に付与します。

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

1. キー コンテナー URL の環境変数を作成します。

    ```azurecli-interactive
    export KEYVAULT_URL="$(az keyvault show \
        --resource-group ${RESOURCE_GROUP} \
        --name ${KEYVAULT_NAME} \
        --query properties.vaultUri \
        --output tsv)"
    ```

1. サービス アカウントと Key Vault URL を参照するポッドをデプロイします。

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

すべてのプロパティが webhook によって正しく挿入されているかどうかを確認するには、 [kubectl describe][kubectl-describe] コマンドを使用します：

```azurecli-interactive
kubectl describe pod sample-workload-identity-key-vault | grep "SECRET_NAME:"
```

成功すると、出力は次のようになります。

```output
      SECRET_NAME:                 ${KEYVAULT_SECRET_NAME}
```

ポッドがトークンを取得し、リソースにアクセスできることを確認するには、kubectl ログ コマンドを使用します。

```azurecli-interactive
kubectl logs sample-workload-identity-key-vault
```

成功すると、出力は次のようになります。

```output
I0114 10:35:09.795900       1 main.go:63] "successfully got secret" secret="Hello\\!"
```

> [!IMPORTANT]
> Azure RBAC ロールの割り当ては、反映されるまでに最大 10 分かかる場合があります。 ポッドがシークレットにアクセスできない場合は、ロールの割り当てが反映されるまで待つ必要があります。 詳細については、「[Azure RBAC のトラブルシューティング](/azure/role-based-access-control/troubleshooting#)」を参照してください。

## ワークロード ID を無効にする

AKS クラスターで有効にされ、構成されている Microsoft Entra ワークロード ID を無効にするには、次のコマンドを実行します:

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --disable-workload-identity
```

## 次のステップ

この記事では、Kubernetes クラスターをデプロイし、アプリケーション ワークロードでその資格情報による認証を行うための準備としてワークロード ID を使用するように構成しました。 これで、アプリケーションをデプロイし、最新バージョンの [Azure ID][azure-identity-libraries] クライアント ライブラリでワークロード ID を使用するように構成する準備ができました。 最新のクライアント ライブラリ バージョンを使用するようにアプリケーションを書き換えることができない場合は、ワークロード ID を短期的な移行ソリューションとして使ってマネージド ID を使用して認証するように、[アプリケーション ポッドを設定][workload-identity-migration]できます。

[サービス コネクタ](/azure/service-connector/overview)統合は、AKS ワークロードと Azure バッキング サービスの接続構成を簡素化するのに役立ちます。 認証とネットワーク構成を安全に処理し、ベスト プラクティスに従って Azure サービスに接続することができます。 詳細については、「[ワークロード ID を使用して AKS の Azure OpenAI Service に接続する](/azure/service-connector/tutorial-python-aks-openai-workload-identity)」と「[サービス コネクタの概要](https://azure.github.io/AKS/2024/05/23/service-connector-intro)」を参照してください。

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