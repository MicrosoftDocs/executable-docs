---
title: 高可用性 PostgreSQL データベースを AKS にデプロイするためのインフラストラクチャを作成する
description: CloudNativePG オペレーターを使用して、高可用性 PostgreSQL データベースを AKS にデプロイするためのインフラストラクチャを作成します。
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# 高可用性 PostgreSQL データベースを AKS にデプロイするためのインフラストラクチャを作成する

この記事では、[CloudNativePG (CNPG)](https://cloudnative-pg.io/) オペレーターを使用して高可用性 PostgreSQL データベースを AKS にデプロイするために必要なインフラストラクチャを作成します。

## 開始する前に

* デプロイの概要を確認し、[Azure CLI を使用して高可用性 PostgreSQL データベースを AKS にデプロイする方法][postgresql-ha-deployment-overview]に関する記事にあるすべての前提条件を満たしていることを確認します。
* このガイド全体で使用する[環境変数を設定](#set-environment-variables)します。
* [必要な拡張機能をインストール](#install-required-extensions)します。

## 環境変数を設定する

このガイド全体で使用する次の環境変数を設定します。

```bash
export SUFFIX=$(cat /dev/urandom | LC_ALL=C tr -dc 'a-z0-9' | fold -w 8 | head -n 1)
export LOCAL_NAME="cnpg"
export TAGS="owner=user"
export RESOURCE_GROUP_NAME="rg-${LOCAL_NAME}-${SUFFIX}"
export PRIMARY_CLUSTER_REGION="westus3"
export AKS_PRIMARY_CLUSTER_NAME="aks-primary-${LOCAL_NAME}-${SUFFIX}"
export AKS_PRIMARY_MANAGED_RG_NAME="rg-${LOCAL_NAME}-primary-aksmanaged-${SUFFIX}"
export AKS_PRIMARY_CLUSTER_FED_CREDENTIAL_NAME="pg-primary-fedcred1-${LOCAL_NAME}-${SUFFIX}"
export AKS_PRIMARY_CLUSTER_PG_DNSPREFIX=$(echo $(echo "a$(openssl rand -hex 5 | cut -c1-11)"))
export AKS_UAMI_CLUSTER_IDENTITY_NAME="mi-aks-${LOCAL_NAME}-${SUFFIX}"
export AKS_CLUSTER_VERSION="1.29"
export PG_NAMESPACE="cnpg-database"
export PG_SYSTEM_NAMESPACE="cnpg-system"
export PG_PRIMARY_CLUSTER_NAME="pg-primary-${LOCAL_NAME}-${SUFFIX}"
export PG_PRIMARY_STORAGE_ACCOUNT_NAME="hacnpgpsa${SUFFIX}"
export PG_STORAGE_BACKUP_CONTAINER_NAME="backups"
export ENABLE_AZURE_PVC_UPDATES="true"
export MY_PUBLIC_CLIENT_IP=$(dig +short myip.opendns.com @resolver3.opendns.com)
```

## 必要な拡張機能をインストールする

`aks-preview`、`k8s-extension`、`amg` 拡張機能は、Kubernetes クラスターの管理と Azure リソースのクエリのためのより多くの機能を提供します。 次の [`az extension add`][az-extension-add] コマンドを使用して、これらの拡張機能をインストールします。

```bash
az extension add --upgrade --name aks-preview --yes --allow-preview true
az extension add --upgrade --name k8s-extension --yes --allow-preview false
az extension add --upgrade --name amg --yes --allow-preview false
```

kubectl を利用するための前提条件として、最初に [Krew][install-krew] をインストールし、その後に [CNPG プラグイン][cnpg-plugin]をインストールすることが重要です。 これにより、後続のコマンドを使用して PostgreSQL オペレーターを管理できるようになります。

```bash
(
  set -x; cd "$(mktemp -d)" &&
  OS="$(uname | tr '[:upper:]' '[:lower:]')" &&
  ARCH="$(uname -m | sed -e 's/x86_64/amd64/' -e 's/\(arm\)\(64\)\?.*/\1\2/' -e 's/aarch64$/arm64/')" &&
  KREW="krew-${OS}_${ARCH}" &&
  curl -fsSLO "https://github.com/kubernetes-sigs/krew/releases/latest/download/${KREW}.tar.gz" &&
  tar zxvf "${KREW}.tar.gz" &&
  ./"${KREW}" install krew
)

export PATH="${KREW_ROOT:-$HOME/.krew}/bin:$PATH"

kubectl krew install cnpg
```

## リソース グループを作成する

[`az group create`][az-group-create] コマンドを使用して、このガイドで作成するリソースを保持するためのリソース グループを作成します。

```bash
az group create \
    --name $RESOURCE_GROUP_NAME \
    --location $PRIMARY_CLUSTER_REGION \
    --tags $TAGS \
    --query 'properties.provisioningState' \
    --output tsv
```

## ユーザー割り当てマネージド ID を作成する

このセクションでは、ユーザー割り当てマネージド ID (UAMI) を作成します。これにより、CNPG PostgreSQL で AKS ワークロード ID を使用して Azure Blob Storage にアクセスできるようになります。 この構成を使用すると、シークレットを使用せずに、AKS 上の PostgreSQL クラスターを Azure Blob Storage に接続できます。

1. [`az identity create`][az-identity-create] コマンドを使用して、ユーザー割り当てマネージド ID を作成します。

    ```bash
    AKS_UAMI_WI_IDENTITY=$(az identity create \
        --name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --output json)
    ```

1. AKS ワークロード ID を有効にし、次のコマンドを使用して、このガイドで後ほど使用するサービス アカウントを生成します。

    ```bash
    export AKS_UAMI_WORKLOAD_OBJECTID=$( \
        echo "${AKS_UAMI_WI_IDENTITY}" | jq -r '.principalId')
    export AKS_UAMI_WORKLOAD_RESOURCEID=$( \
        echo "${AKS_UAMI_WI_IDENTITY}" | jq -r '.id')
    export AKS_UAMI_WORKLOAD_CLIENTID=$( \
        echo "${AKS_UAMI_WI_IDENTITY}" | jq -r '.clientId')

    echo "ObjectId: $AKS_UAMI_WORKLOAD_OBJECTID"
    echo "ResourceId: $AKS_UAMI_WORKLOAD_RESOURCEID"
    echo "ClientId: $AKS_UAMI_WORKLOAD_CLIENTID"
    ```

オブジェクト ID はクライアント ID (アプリケーション ID とも呼ばれます) の一意識別子であり、Entra ID テナント内の "アプリケーション" の種類のセキュリティ プリンシパルを一意に識別します。** リソース ID は、Azure でリソースを管理および検索するための一意識別子です。 これらの値は、AKS ワークロード ID を有効にするために必要です。

CNPG オペレーターによって *postgres* というサービス アカウントが自動的に生成されます。このガイドでは後ほどこれを使用して、PostgreSQL から Azure Storage への OAuth アクセスを有効にするフェデレーション資格情報を作成します。

## プライマリ リージョンにストレージ アカウントを作成する

1. [`az storage account create`][az-storage-account-create] コマンドを使用して、プライマリ リージョンに、PostgreSQL バックアップを格納するためのオブジェクト ストレージ アカウントを作成します。

    ```bash
    az storage account create \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --sku Standard_ZRS \
        --kind StorageV2 \
        --query 'provisioningState' \
        --output tsv
    ```

1. [`az storage container create`][az-storage-container-create] コマンドを使用して、先書きログ (WAL) と通常の PostgreSQL のオンデマンドおよびスケジュールされたバックアップを格納するためのストレージ コンテナーを作成します。

    ```bash
    az storage container create \
        --name $PG_STORAGE_BACKUP_CONTAINER_NAME \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --auth-mode login
    ```

    出力例:

    ```output
    {
        "created": true
    }
    ```

    > [!NOTE]
    > エラー メッセージ `The request may be blocked by network rules of storage account. Please check network rule set using 'az storage account show -n accountname --query networkRuleSet'. If you want to change the default action to apply when no rule matches, please use 'az storage account update'` が表示された場合。 Azure Blob Storage のユーザー アクセス許可を確認し、**必要**な場合は、次に示すコマンドを使用してロールを `Storage Blob Data Owner` に昇格した後、[`az storage container create`][az-storage-container-create] コマンドを再試行してください。

    ```bash
    az role assignment list --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID --output table

    export USER_ID=$(az ad signed-in-user show --query id --output tsv)

    export STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID=$(az storage account show \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "id" \
        --output tsv)

    az role assignment create \
        --assignee-object-id $USER_ID \
        --assignee-principal-type User \
        --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID \
        --role "Storage Blob Data Owner" \
        --output tsv
    ```

## RBAC をストレージ アカウントに割り当てる

バックアップを有効にするには、PostgreSQL クラスターでオブジェクト ストアの読み取りと書き込みを行う必要があります。 AKS で実行されている PostgreSQL クラスターでは、CNPG オペレーターの構成パラメーター [`inheritFromAzureAD`][inherit-from-azuread] を使用してストレージ アカウントにアクセスするためにワークロード ID が使用されます。

1. [`az storage account show`][az-storage-account-show] コマンドを使用して、ストレージ アカウントのプライマリ リソース ID を取得します。

    ```bash
    export STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID=$(az storage account show \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "id" \
        --output tsv)

    echo $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID
    ````

1. [`az role assignment create`][az-role-assignment-create] コマンドを使用して、各 AKS クラスターのマネージド ID に関連付けられた UAMI のストレージ アカウント リソース ID スコープを持つオブジェクト ID に、Azure 組み込みロールの "Storage BLOB データ共同作成者" を割り当てます。

    ```bash
    az role assignment create \
        --role "Storage Blob Data Contributor" \
        --assignee-object-id $AKS_UAMI_WORKLOAD_OBJECTID \
        --assignee-principal-type ServicePrincipal \
        --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID \
        --query "id" \
        --output tsv
    ```

## 監視インフラストラクチャを設定する

このセクションでは、Azure Managed Grafana のインスタンス、Azure Monitor ワークスペース、Azure Monitor Log Analytics ワークスペースをデプロイして、PostgreSQL クラスターを監視できるようにします。 また、このガイドで後ほど AKS クラスターの作成プロセスで入力として使用するために、作成された監視インフラストラクチャへの参照も格納します。 このセクションは完了するまでに時間がかかる場合があります。

> [!NOTE]
> Azure Managed Grafana インスタンスと AKS クラスターは個別に課金されます。 価格の詳細については、「[Azure Managed Grafana の価格][azure-managed-grafana-pricing]」を参照してください。

1. [`az grafana create`][az-grafana-create] コマンドを使用して、Azure Managed Grafana インスタンスを作成します。

    ```bash
    export GRAFANA_PRIMARY="grafana-${LOCAL_NAME}-${SUFFIX}"

    export GRAFANA_RESOURCE_ID=$(az grafana create \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $GRAFANA_PRIMARY \
        --location $PRIMARY_CLUSTER_REGION \
        --zone-redundancy Enabled \
        --tags $TAGS \
        --query "id" \
        --output tsv)

    echo $GRAFANA_RESOURCE_ID
    ```

1. [`az monitor account create`][az-monitor-account-create] コマンドを使用して、Azure Monitor ワークスペースを作成します。

    ```bash
    export AMW_PRIMARY="amw-${LOCAL_NAME}-${SUFFIX}"

    export AMW_RESOURCE_ID=$(az monitor account create \
        --name $AMW_PRIMARY \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --tags $TAGS \
        --query "id" \
        --output tsv)

    echo $AMW_RESOURCE_ID
    ```

1. [`az monitor log-analytics workspace create`][az-monitor-log-analytics-workspace-create] コマンドを使用して、Azure Monitor Log Analytics ワークスペースを作成します。

    ```bash
    export ALA_PRIMARY="ala-${LOCAL_NAME}-${SUFFIX}"

    export ALA_RESOURCE_ID=$(az monitor log-analytics workspace create \
        --resource-group $RESOURCE_GROUP_NAME \
        --workspace-name $ALA_PRIMARY \
        --location $PRIMARY_CLUSTER_REGION \
        --query "id" \
        --output tsv)

    echo $ALA_RESOURCE_ID
    ```

## PostgreSQL クラスターをホストする AKS クラスターを作成する

このセクションでは、システム ノード プールを使用して複数リージョンの AKS クラスターを作成します。 AKS クラスターは、PostgreSQL クラスターのプライマリ レプリカと、2 つのスタンバイ レプリカをホストします。スタンバイ レプリカはそれぞれ異なる可用性ゾーンに配置してゾーン冗長を有効にします。

また、PostgreSQL クラスターをホストするために、ユーザー ノード プールを AKS クラスターに追加します。 個別のノード プールを使用すると、PostgreSQL に使用される Azure VM SKU を制御でき、AKS システム プールでパフォーマンスとコストを最適化できます。 このガイドで後ほど CNPG オペレーターをデプロイするときにノードの選択で参照できるように、ユーザー ノード プールにラベルを適用します。 このセクションは完了するまでに時間がかかる場合があります。

1. [`az aks create`][az-aks-create] コマンドを使用して、AKS クラスターを作成します。

    ```bash
    export SYSTEM_NODE_POOL_VMSKU="standard_d2s_v3"
    export USER_NODE_POOL_NAME="postgres"
    export USER_NODE_POOL_VMSKU="standard_d4s_v3"
    
    az aks create \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --tags $TAGS \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --generate-ssh-keys \
        --node-resource-group $AKS_PRIMARY_MANAGED_RG_NAME \
        --enable-managed-identity \
        --assign-identity $AKS_UAMI_WORKLOAD_RESOURCEID \
        --network-plugin azure \
        --network-plugin-mode overlay \
        --network-dataplane cilium \
        --nodepool-name systempool \
        --enable-oidc-issuer \
        --enable-workload-identity \
        --enable-cluster-autoscaler \
        --min-count 2 \
        --max-count 3 \
        --node-vm-size $SYSTEM_NODE_POOL_VMSKU \
        --enable-azure-monitor-metrics \
        --azure-monitor-workspace-resource-id $AMW_RESOURCE_ID \
        --grafana-resource-id $GRAFANA_RESOURCE_ID \
        --api-server-authorized-ip-ranges $MY_PUBLIC_CLIENT_IP \
        --tier standard \
        --kubernetes-version $AKS_CLUSTER_VERSION \
        --zones 1 2 3 \
        --output table
    ```

2. [`az aks nodepool add`][az-aks-node-pool-add] コマンドを使用して、ユーザー ノード プールを AKS クラスターに追加します。

    ```bash
    az aks nodepool add \
        --resource-group $RESOURCE_GROUP_NAME \
        --cluster-name $AKS_PRIMARY_CLUSTER_NAME \
        --name $USER_NODE_POOL_NAME \
        --enable-cluster-autoscaler \
        --min-count 3 \
        --max-count 6 \
        --node-vm-size $USER_NODE_POOL_VMSKU \
        --zones 1 2 3 \
        --labels workload=postgres \
        --output table
    ```

> [!NOTE]
> AKS ノード プールを追加するときにエラー メッセージ `"(OperationNotAllowed) Operation is not allowed: Another operation (Updating) is in progress, please wait for it to finish before starting a new operation."` が表示される場合は、AKS クラスターの操作が完了するまで数分待ってから `az aks nodepool add` コマンドを実行してください。

## AKS クラスターに接続し、名前空間を作成する

このセクションでは、AKS クラスターの資格情報を取得します。これは、クラスターの認証とクラスターとの対話を可能にするキーとして機能します。 接続したら、2 つの名前空間を作成します。1 つは CNPG コントローラー マネージャー サービス用で、もう 1 つは、PostgreSQL クラスターとその関連サービス用です。

1. [`az aks get-credentials`][az-aks-get-credentials] コマンドを使用して、AKS クラスターの資格情報を取得します。

    ```bash
    az aks get-credentials \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --output none
     ```

2. [`kubectl create namespace`][kubectl-create-namespace] コマンドを使用して、CNPG コントローラー マネージャー サービス用と PostgreSQL クラスターとその関連サービス用の名前空間を作成します。

    ```bash
    kubectl create namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    kubectl create namespace $PG_SYSTEM_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## 監視インフラストラクチャを更新する

Managed Prometheus と Azure Managed Grafana 用の Azure Monitor ワークスペースは、メトリックと視覚化のために、クラスターの作成プロセス中に AKS クラスターに自動的にリンクされます。 このセクションでは、AKS Container insights を使用してログ収集を有効にし、Managed Prometheus がメトリックをスクレイピングし、Container insights がログを取り込んでいることを確認します。

1. [`az aks enable-addons`][az-aks-enable-addons] コマンドを使用して、AKS クラスターで Container insights の監視を有効にします。

    ```bash
    az aks enable-addons \
        --addon monitoring \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --workspace-resource-id $ALA_RESOURCE_ID \
        --output table
    ```

2. [`kubectl get`][kubectl-get] コマンドと [`az aks show`][az-aks-show] コマンドを使用して DaemonSet を調べ、Managed Prometheus がメトリックをスクレイピングし、Container insights が AKS クラスターからログを取り込んでいることを確認します。

    ```bash
    kubectl get ds ama-metrics-node \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace=kube-system

    kubectl get ds ama-logs \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace=kube-system

    az aks show \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --query addonProfiles
    ```

    出力は次の例の出力のようになります。合計 "6 つ" のノード (システム ノード プール用に 3 つ、PostgreSQL ノード プール用に 3 つ) があり、Container insights は `"enabled": true` を示しています。**

    ```output
    NAME               DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR
    ama-metrics-node   6         6         6       6            6           <none>       

    NAME               DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR
    ama-logs           6         6         6       6            6           <none>       

    {
      "omsagent": {
        "config": {
          "logAnalyticsWorkspaceResourceID": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-cnpg-9vbin3p8/providers/Microsoft.OperationalInsights/workspaces/ala-cnpg-9vbin3p8",
          "useAADAuth": "true"
        },
        "enabled": true,
        "identity": null
      }
    }
    ```

## PostgreSQL クラスターのイングレス用のパブリック静的 IP を作成する

PostgreSQL クラスターのデプロイを検証し、*psql* や *PgAdmin* などのクライアント PostgreSQL ツールを使用するには、プライマリ レプリカと読み取り専用レプリカをイングレスに公開する必要があります。 このセクションでは、Azure パブリック IP リソースを作成します。後でこれを Azure Load Balancer に提供して、クエリ用の PostgreSQL エンドポイントを公開します。

1. [`az aks show`][az-aks-show] コマンドを使用して、AKS クラスター ノード リソース グループの名前を取得します。

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME=$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query nodeResourceGroup \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME
    ```

2. [`az network public-ip create`][az-network-public-ip-create] コマンドを使用して、パブリック IP アドレスを作成します。

    ```bash
    export AKS_PRIMARY_CLUSTER_PUBLICIP_NAME="$AKS_PRIMARY_CLUSTER_NAME-pip"

    az network public-ip create \
        --resource-group $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --name $AKS_PRIMARY_CLUSTER_PUBLICIP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --sku Standard \
        --zone 1 2 3 \
        --allocation-method static \
        --output table
    ```

3. [`az network public-ip show`][az-network-public-ip-show] コマンドを使用して、新しく作成されたパブリック IP アドレスを取得します。

    ```bash
    export AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS=$(az network public-ip show \
        --resource-group $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --name $AKS_PRIMARY_CLUSTER_PUBLICIP_NAME \
        --query ipAddress \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS
    ```

4. [`az group show`][az-group-show] コマンドを使用して、ノード リソース グループのリソース ID を取得します。

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE=$(az group show --name \
        $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --query id \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE
    ```

5. [`az role assignment create`][az-role-assignment-create] コマンドを使用し、ノード リソース グループのスコープを使用して UAMI オブジェクト ID に "ネットワーク共同作成者" ロールを割り当てます。

    ```bash
    az role assignment create \
        --assignee-object-id ${AKS_UAMI_WORKLOAD_OBJECTID} \
        --assignee-principal-type ServicePrincipal \
        --role "Network Contributor" \
        --scope ${AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE}
    ```

## CNPG オペレーターを AKS クラスターにインストールする

このセクションでは、Helm または YAML マニフェストを使用して、CNPG オペレーターを AKS クラスターにインストールします。

### [Helm](#tab/helm)

1. [`helm repo add`][helm-repo-add] コマンドを使用して、CNPG Helm リポジトリを追加します。

    ```bash
    helm repo add cnpg https://cloudnative-pg.github.io/charts
    ```

2. CNPG Helm リポジトリをアップグレードし、`--install` フラグを指定した [`helm upgrade`][helm-upgrade] コマンドを使用して、AKS クラスターにインストールします。

    ```bash
    helm upgrade --install cnpg \
        --namespace $PG_SYSTEM_NAMESPACE \
        --create-namespace \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME \
        cnpg/cloudnative-pg
    ```

3. [`kubectl get`][kubectl-get] コマンドを使用して、AKS クラスターにオペレーターがインストールされていることを確認します。

    ```bash
    kubectl get deployment \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-cloudnative-pg
    ```

### [YAML](#tab/yaml)

1. [`kubectl apply`][kubectl-apply] コマンドを使用して、CNPG オペレーターを AKS クラスターにインストールします。

    ```bash
    kubectl apply --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE \
        --server-side -f \
        https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.23/releases/cnpg-1.23.1.yaml
    ```

2. [`kubectl get`][kubectl-get] コマンドを使用して、AKS クラスターにオペレーターがインストールされていることを確認します。

    ```bash
    kubectl get deployment \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-controller-manager \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

---

## 次のステップ

> [!div class="nextstepaction"]
> [高可用性 PostgreSQL データベースを AKS クラスターにデプロイする][deploy-postgresql]

## 共同作成者

*この記事は Microsoft によって管理されています。これはもともと次の共同作成者によって書かれました*:

* Ken Kilty | プリンシパル TPM
* Russell de Pina | プリンシパル TPM
* Adrian Joian | シニア カスタマー エンジニア
* Jenny Hayes | シニア コンテンツ開発者
* Carol Smith | シニア コンテンツ開発者
* Erin Schaffer |コンテンツ開発者 2

<!-- LINKS -->
[az-identity-create]: /cli/azure/identity#az-identity-create
[az-grafana-create]: /cli/azure/grafana#az-grafana-create
[postgresql-ha-deployment-overview]: ./postgresql-ha-overview.md
[az-extension-add]: /cli/azure/extension#az_extension_add
[az-group-create]: /cli/azure/group#az_group_create
[az-storage-account-create]: /cli/azure/storage/account#az_storage_account_create
[az-storage-container-create]: /cli/azure/storage/container#az_storage_container_create
[inherit-from-azuread]: https://cloudnative-pg.io/documentation/1.23/appendixes/object_stores/#azure-blob-storage
[az-storage-account-show]: /cli/azure/storage/account#az_storage_account_show
[az-role-assignment-create]: /cli/azure/role/assignment#az_role_assignment_create
[az-monitor-account-create]: /cli/azure/monitor/account#az_monitor_account_create
[az-monitor-log-analytics-workspace-create]: /cli/azure/monitor/log-analytics/workspace#az_monitor_log_analytics_workspace_create
[azure-managed-grafana-pricing]: https://azure.microsoft.com/pricing/details/managed-grafana/
[az-aks-create]: /cli/azure/aks#az_aks_create
[az-aks-node-pool-add]: /cli/azure/aks/nodepool#az_aks_nodepool_add
[az-aks-get-credentials]: /cli/azure/aks#az_aks_get_credentials
[kubectl-create-namespace]: https://kubernetes.io/docs/reference/kubectl/generated/kubectl_create/kubectl_create_namespace/
[az-aks-enable-addons]: /cli/azure/aks#az_aks_enable_addons
[kubectl-get]: https://kubernetes.io/docs/reference/kubectl/generated/kubectl_get/
[az-aks-show]: /cli/azure/aks#az_aks_show
[az-network-public-ip-create]: /cli/azure/network/public-ip#az_network_public_ip_create
[az-network-public-ip-show]: /cli/azure/network/public-ip#az_network_public_ip_show
[az-group-show]: /cli/azure/group#az_group_show
[helm-repo-add]: https://helm.sh/docs/helm/helm_repo_add/
[helm-upgrade]: https://helm.sh/docs/helm/helm_upgrade/
[kubectl-apply]: https://kubernetes.io/docs/reference/kubectl/generated/kubectl_apply/
[deploy-postgresql]: ./deploy-postgresql-ha.md
[install-krew]: https://krew.sigs.k8s.io/
[cnpg-plugin]: https://cloudnative-pg.io/documentation/current/kubectl-plugin/#using-krew
