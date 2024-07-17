---
title: 'チュートリアル: Azure CLI を使用して WordPress を AKS クラスターにデプロイする'
description: Azure Database for MySQL - フレキシブル サーバーを使用して、WordPress をすばやく構築し、AKS にデプロイする方法について説明します。
ms.service: mysql
ms.subservice: flexible-server
author: mksuni
ms.author: sumuth
ms.topic: tutorial
ms.date: 3/20/2024
ms.custom: 'vc, devx-track-azurecli, innovation-engine, linux-related-content'
---

# チュートリアル:Azure Database for MySQL - フレキシブル サーバーを使用して WordPress アプリを AKS にデプロイする

[!INCLUDE[applies-to-mysql-flexible-server](../includes/applies-to-mysql-flexible-server.md)]

[![Azure に配置する](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262843)

このチュートリアルでは、Azure CLI を使用して、Azure Database for MySQL フレキシブル サーバーで Azure Kubernetes Service (AKS) クラスターに、HTTPS 経由でセキュリティ保護されたスケーラブルな WordPress アプリケーションをデプロイします。
**[AKS](../../aks/intro-kubernetes.md)** は、クラスターをすばやくデプロイして管理できるマネージド Kubernetes サービスです。 **[Azure Database for MySQL フレキシブル サーバー](overview.md)** は、データベース管理機能と構成設定のよりきめ細かな制御と柔軟性を提供するように設計されたフル マネージド データベース サービスです。

> [!NOTE]
> このチュートリアルでは、Kubernetes の概念、WordPress、MySQL に関する基礎知識があることを前提としています。

[!INCLUDE [flexible-server-free-trial-note](../includes/flexible-server-free-trial-note.md)]

## 前提条件 

作業を開始する前に、Azure CLI にログインし、CLI で使用するサブスクリプションを選択していることを確認してください。 [Helm がインストールされている](https://helm.sh/docs/intro/install/)ことを確かめてください。

> [!NOTE]
> このチュートリアルのコマンドを Azure Cloud Shell ではなくローカルで実行している場合は、管理者としてコマンドを実行します。

## リソース グループを作成する

Azure リソース グループは、Azure リソースが展開され管理される論理グループです。 すべてのリソースをリソース グループに配置する必要があります。 次のコマンドでは、前に定義した `$MY_RESOURCE_GROUP_NAME` と `$REGION` パラメータを使用してリソース グループを作成します。

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myWordPressAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION
```

結果:
<!-- expected_similarity=0.3 -->
```json
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX",
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

> [!NOTE]
> リソース グループの場所は、リソース グループのメタデータが保存される場所です。 また、リソースの作成時に別のリージョンを指定しない場合に、Azure でリソースが実行される場所でもあります。

## 仮想ネットワークとサブネットの作成

仮想ネットワークは、Azure 内のプライベート ネットワークの基本的な構成ブロックです。 Azure Virtual Network では、VM などの Azure リソースが、相互に、およびインターネットと安全に通信することができます。

```bash
export NETWORK_PREFIX="$(($RANDOM % 253 + 1))"
export MY_VNET_PREFIX="10.$NETWORK_PREFIX.0.0/16"
export MY_SN_PREFIX="10.$NETWORK_PREFIX.0.0/22"
export MY_VNET_NAME="myVNet$RANDOM_ID"
export MY_SN_NAME="mySN$RANDOM_ID"
az network vnet create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --name $MY_VNET_NAME \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefixes $MY_SN_PREFIX
```

結果:
<!-- expected_similarity=0.3 -->
```json
{
  "newVNet": {
    "addressSpace": {
      "addressPrefixes": [
        "10.210.0.0/16"
      ]
    },
    "enableDdosProtection": false,
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/myWordPressAKSResourceGroupXXX/providers/Microsoft.Network/virtualNetworks/myVNetXXX",
    "location": "eastus",
    "name": "myVNet210",
    "provisioningState": "Succeeded",
    "resourceGroup": "myWordPressAKSResourceGroupXXX",
    "subnets": [
      {
        "addressPrefix": "10.210.0.0/22",
        "delegations": [],
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/myWordPressAKSResourceGroupXXX/providers/Microsoft.Network/virtualNetworks/myVNetXXX/subnets/mySNXXX",
        "name": "mySN210",
        "privateEndpointNetworkPolicies": "Disabled",
        "privateLinkServiceNetworkPolicies": "Enabled",
        "provisioningState": "Succeeded",
        "resourceGroup": "myWordPressAKSResourceGroupXXX",
        "type": "Microsoft.Network/virtualNetworks/subnets"
      }
    ],
    "type": "Microsoft.Network/virtualNetworks",
    "virtualNetworkPeerings": []
  }
}
```

## Azure Database for MySQL フレキシブル サーバー インスタンスを作成する

Azure Database for MySQL フレキシブル サーバーは、高可用性 MySQL サーバーをクラウド内で実行、管理、スケーリングするために使用することができる管理サービスです。 [az mysql flexible-server create](/cli/azure/mysql/flexible-server) コマンドを使用して、Azure Database for MySQL フレキシブル サーバー インスタンスを作成します。 1 つのサーバーに複数のデータベースを含めることができます。 次のコマンドでは、サービスの既定値と Azure CLI のローカル コンテキストからの変数値を使用してサーバーを作成します。

```bash
export MY_MYSQL_ADMIN_USERNAME="dbadmin$RANDOM_ID"
export MY_WP_ADMIN_PW="$(openssl rand -base64 32)"
echo "Your MySQL user $MY_MYSQL_ADMIN_USERNAME password is: $MY_WP_ADMIN_PW" 
```

```bash
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
export MY_MYSQL_DB_NAME="mydb$RANDOM_ID"
export MY_MYSQL_ADMIN_PW="$(openssl rand -base64 32)"
export MY_MYSQL_SN_NAME="myMySQLSN$RANDOM_ID"
az mysql flexible-server create \
    --admin-password $MY_MYSQL_ADMIN_PW \
    --admin-user $MY_MYSQL_ADMIN_USERNAME \
    --auto-scale-iops Disabled \
    --high-availability Disabled \
    --iops 500 \
    --location $REGION \
    --name $MY_MYSQL_DB_NAME \
    --database-name wordpress \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --sku-name Standard_B2s \
    --storage-auto-grow Disabled \
    --storage-size 20 \
    --subnet $MY_MYSQL_SN_NAME \
    --private-dns-zone $MY_DNS_LABEL.private.mysql.database.azure.com \
    --tier Burstable \
    --version 8.0.21 \
    --vnet $MY_VNET_NAME \
    --yes -o JSON
```

結果:
<!-- expected_similarity=0.3 -->
```json
{
  "databaseName": "wordpress",
  "host": "mydbxxx.mysql.database.azure.com",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX/providers/Microsoft.DBforMySQL/flexibleServers/mydbXXX",
  "location": "East US",
  "resourceGroup": "myWordPressAKSResourceGroupXXX",
  "skuname": "Standard_B2s",
  "subnetId": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX/providers/Microsoft.Network/virtualNetworks/myVNetXXX/subnets/myMySQLSNXXX",
  "username": "dbadminxxx",
  "version": "8.0.21"
}
```

作成されたサーバーには、次の属性があります。

- サーバーが最初にプロビジョニングされたときに、新しい空のデータベースが作成されます。
- サーバー名、管理者ユーザー名、管理者パスワード、リソース グループ名、場所は、クラウド シェルのローカル コンテキスト環境で既に指定されており、リソース グループや他の Azure コンポーネントと同じ場所にあります。
- 残りのサーバー構成のサービスの既定値は、コンピューティング レベル (Burstable)、コンピューティング サイズ/SKU (Standard_B2s)、バックアップの保持期間 (7 日間)、および MySQL のバージョン (8.0.21) です。
- 既定の接続方法は、リンクされた仮想ネットワークと自動生成されたサブネットを使うプライベート アクセス (仮想ネットワーク統合) です。

> [!NOTE]
> サーバーの作成後に接続方法を変更することはできません。 たとえば、作成中に `Private access (VNet Integration)` を選択した場合は、作成後に `Public access (allowed IP addresses)` に変更することはできません。 VNet 統合を使用してサーバーに安全にアクセスするには、プライベート アクセスを指定してサーバーを作成することを強くお勧めします。 プライベート アクセスの詳細については、[概念に関する記事](./concepts-networking-vnet.md)を参照してください。

既定値を変更したい場合は、Azure CLI の[リファレンス ドキュメント](/cli/azure//mysql/flexible-server)で、構成可能なすべての CLI パラメーターの一覧を参照してください。

## Azure Database for MySQL の確認 - フレキシブル サーバー状態

Azure Database for MySQL - フレキシブル サーバーとサポート リソースの作成には数分かかります。

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## Azure Database for MySQL - フレキシブル サーバーでサーバー パラメーターを構成する

サーバー パラメーターを使用して Azure Database for MySQL - フレキシブル サーバー構成を管理できます。 このサーバー パラメーターは、サーバーの作成時に既定値と推奨値を使用して構成されます。

サーバーの特定のパラメーターに関する詳細を表示するには、[az mysql flexible-server parameter show](/cli/azure/mysql/flexible-server/parameter) コマンドを実行します。

### WordPress 統合のために Azure Database for MySQL - フレキシブル サーバー SSL 接続パラメーターを無効にする

特定のサーバー パラメータの値を変更し、MySQL サーバー エンジンの基になる構成値を更新することもできます。 サーバー パラメーターを更新するには、[az mysql flexible-server parameter set](/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set) コマンドを使用します。

```bash
az mysql flexible-server parameter set \
    -g $MY_RESOURCE_GROUP_NAME \
    -s $MY_MYSQL_DB_NAME \
    -n require_secure_transport -v "OFF" -o JSON
```

結果:
<!-- expected_similarity=0.3 -->
```json
{
  "allowedValues": "ON,OFF",
  "currentValue": "OFF",
  "dataType": "Enumeration",
  "defaultValue": "ON",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX/providers/Microsoft.DBforMySQL/flexibleServers/mydbXXX/configurations/require_secure_transport",
  "isConfigPendingRestart": "False",
  "isDynamicConfig": "True",
  "isReadOnly": "False",
  "name": "require_secure_transport",
  "resourceGroup": "myWordPressAKSResourceGroupXXX",
  "source": "user-override",
  "systemData": null,
  "type": "Microsoft.DBforMySQL/flexibleServers/configurations",
  "value": "OFF"
}
```

## AKS クラスターの作成

Container Insights で AKS クラスターを作成するには、**--enable-addons** 監視パラメータを指定して [az aks create](/cli/azure/aks#az-aks-create) コマンドを使用します。 次の例では、**myAKSCluster** という名前の自動スケールの可用性ゾーンが有効なクラスターを作成します。

この操作には数分かかります。

```bash
export MY_SN_ID=$(az network vnet subnet list --resource-group $MY_RESOURCE_GROUP_NAME --vnet-name $MY_VNET_NAME --query "[0].id" --output tsv)
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"

az aks create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_AKS_CLUSTER_NAME \
    --auto-upgrade-channel stable \
    --enable-cluster-autoscaler \
    --enable-addons monitoring \
    --location $REGION \
    --node-count 1 \
    --min-count 1 \
    --max-count 3 \
    --network-plugin azure \
    --network-policy azure \
    --vnet-subnet-id $MY_SN_ID \
    --no-ssh-key \
    --node-vm-size Standard_DS2_v2 \
    --service-cidr 10.255.0.0/24 \
    --dns-service-ip 10.255.0.10 \
    --zones 1 2 3
```
> [!NOTE]
> AKS クラスターを作成すると、AKS リソースを保存するための 2 つ目のリソース グループが自動的に作成されます。 「[AKS と一緒にリソース グループが 2 つ作成されるのはなぜでしょうか?](../../aks/faq.md#why-are-two-resource-groups-created-with-aks)」を参照してください。

## クラスターに接続する

Kubernetes クラスターを管理するには、Kubernetes のコマンドライン クライアントである [kubectl](https://kubernetes.io/docs/reference/kubectl/overview/) を使用します。 Azure Cloud Shell を使用している場合、`kubectl` は既にインストールされています。 次の例では、[az aks install-cli](/cli/azure/aks#az-aks-install-cli) コマンドを使用して、`kubectl` をローカルにインストールします。 

 ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
```

次に、[az aks get-credentials](/cli/azure/aks#az-aks-get-credentials) コマンドを使用して、Kubernetes クラスターに接続するように `kubectl` を構成します。 このコマンドは、資格情報をダウンロードし、それを使用するように Kubernetes CLI を構成します。 このコマンドでは、`~/.kube/config` ([Kubernetes 構成ファイル](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/)の既定の場所) が使用されます。 **--file** 引数を使用して、Kubernetes 構成ファイルの別の場所を指定できます。

> [!WARNING]
> このコマンドにより、同じエントリを使用して既存の資格情報が上書きされます。

```bash
az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
```

クラスターへの接続を確認するには、クラスター ノードの一覧を返す [kubectl get]( https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#get) コマンドを使用します。

```bash
kubectl get nodes
```

## NGINX イングレス コントローラーをインストールする

イングレス コントローラーに、静的なパブリック IP アドレスを構成できます。 イングレス コントローラーが削除されても、静的パブリック IP アドレスはそのまま残ります。 AKS クラスターを削除した場合、IP アドレスは "残りません"。
イングレス コントローラーをアップグレードする場合、割り当てられるロード バランサーをイングレス コントローラー サービスに認識させるために、Helm リリースにパラメーターを渡す必要があります。 HTTPS 証明書を正しく動作させるには、DNS 名ラベルを使用して、イングレス コントローラーの IP アドレスの完全修飾ドメイン名 (FQDN) を構成します。 FQDN は次の形式に従う必要があります: $MY_DNS_LABEL。AZURE_REGION_NAME.cloudapp.azure.com。

```bash
export MY_PUBLIC_IP_NAME="myPublicIP$RANDOM_ID"
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

次に、ingress-nginx Helm リポジトリを追加し、ローカルの Helm Chart リポジトリ キャッシュを更新し、Helm を使用して ingress-nginx アドオンをインストールします。 最初にイングレス コントローラーをデプロイするときに、または後で、**--set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"="<DNS_LABEL>"** パラメーターで DNS ラベルを設定できます。 この例では、**--set controller.service.loadBalancerIP="<STATIC_IP>" パラメーター**で前の手順で作成した独自のパブリック IP アドレスを指定します。

```bash
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    helm repo update
    helm upgrade --install --cleanup-on-fail --atomic ingress-nginx ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --create-namespace \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"=$MY_DNS_LABEL \
        --set controller.service.loadBalancerIP=$MY_STATIC_IP \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
        --wait --timeout 10m0s
```

## カスタム ドメインへの HTTPS 終了の追加

チュートリアルのこの時点で、NGINX をイングレス コントローラーとして使用した AKS Web アプリと、アプリケーションへのアクセスに使用できるカスタム ドメインがあります。 次の手順は、ユーザーが https 経由で安全にアプリケーションにアクセスできるように、ドメインに SSL 証明書を追加することです。

### Cert Manager を設定する

HTTPS を追加するには、Cert Manager を使用します。 Cert Manager は、Kubernetes デプロイの SSL 証明書を取得および管理するためのオープン ソース ツールです。 Cert Manager により、一般的なパブリック発行者とプライベート発行者から証明書が取得され、証明書が有効で最新であることが確かめられ、証明書の有効期限が切れる前に構成された時刻に更新が試行されます。

1. cert-manager をインストールするには、最初にそれを実行する名前空間を作成する必要があります。 このチュートリアルでは、cert-manager を cert-manager 名前空間にインストールします。 cert-manager は別の名前空間で実行できますが、配置マニフェストを変更する必要があります。

    ```bash
    kubectl create namespace cert-manager
    ```

2. これで、cert-manager をインストールできるようになりました。 すべてのリソースは、1 つの YAML マニフェスト ファイルに含まれます。 次のコマンドを使用してマニフェスト ファイルをインストールします。

    ```bash
    kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
    ```

3. 次のコマンドを実行して、`certmanager.k8s.io/disable-validation: "true"` ラベルを cert-manager 名前空間に追加します。 これにより、cert-manager が TLS をブートストラップするために必要なシステム リソースを独自の名前空間に作成できるようになります。

    ```bash
    kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
    ```

## Helm Charts を介して証明書を取得する

Helm は、Kubernetes クラスターへのアプリケーションやサービスの作成、パッケージ化、構成、デプロイを自動化するための Kubernetes デプロイ ツールです。

cert-manager では、Kubernetes への第一級のインストール方法として Helm チャートが提供されます。

1. Jetstack Helm リポジトリを追加します。 このリポジトリは、cert-manager チャートの唯一のサポート ソースです。 インターネット上には他にもミラーやコピーがありますが、それらは非公式なものであり、セキュリティ上のリスクがある可能性があります。

    ```bash
    helm repo add jetstack https://charts.jetstack.io
    ```

2. ローカルの Helm Chart リポジトリ キャッシュを更新します。

    ```bash
    helm repo update
    ```

3. Helm を使用して Cert-Manager アドオンをインストールします。

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. 証明書の発行者 YAML ファイルを適用します。 ClusterIssuers は、証明書署名要求を許可することで署名付き証明書を生成できる証明機関 (CA) を表す Kubernetes リソースです。 すべての cert-manager 証明書は、要求の許可を試行する準備の整った参照発行者が必要です。 `cluster-issuer-prod.yml file` で発行者を見つけることができます。

    ```bash
    export SSL_EMAIL_ADDRESS="$(az account show --query user.name --output tsv)"
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## カスタム ストレージ クラスを作成する

既定のストレージ クラスは最も一般的なシナリオに適合しますが、すべてに適合するわけではありません。 場合によっては、独自のストレージ クラスを独自のパラメーターを使用してカスタマイズすることもできます。 たとえば、次のマニフェストを使用して、ファイル共有の **mountOptions** を構成します。
Kubernetes でマウントされたファイル共有の場合、**fileMode** と **dirMode** の既定値は **0755** です。 ストレージ クラス オブジェクトでは、さまざまなマウント オプションを指定できます。

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## WordPress を AKS クラスターにデプロイする

このチュートリアルでは、Bitnami によって構築された WordPress 用の既存の Helm チャートを使用しています。 Bitnami Helm チャートではローカル MariaDB がデータベースとして使用されるため、Azure Database for MySQL でアプリを使うには、これらの値をオーバーライドする必要があります。 `helm-wp-aks-values.yaml` ファイルの値とカスタム設定をオーバーライドできます。

1. Wordpress Bitnami Helm リポジトリを追加します。

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. ローカルの Helm Chart リポジトリ キャッシュを更新します。

    ```bash
    helm repo update
    ```

3. Helm を使用して Wordpress ワークロードをインストールします。

    ```bash
    export MY_MYSQL_HOSTNAME="$MY_MYSQL_DB_NAME.mysql.database.azure.com"
    export MY_WP_ADMIN_USER="wpcliadmin"
    export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
    helm upgrade --install --cleanup-on-fail \
        --wait --timeout 10m0s \
        --namespace wordpress \
        --create-namespace \
        --set wordpressUsername="$MY_WP_ADMIN_USER" \
        --set wordpressPassword="$MY_WP_ADMIN_PW" \
        --set wordpressEmail="$SSL_EMAIL_ADDRESS" \
        --set externalDatabase.host="$MY_MYSQL_HOSTNAME" \
        --set externalDatabase.user="$MY_MYSQL_ADMIN_USERNAME" \
        --set externalDatabase.password="$MY_MYSQL_ADMIN_PW" \
        --set ingress.hostname="$FQDN" \
        --values helm-wp-aks-values.yaml \
        wordpress bitnami/wordpress
    ```

結果:
<!-- expected_similarity=0.3 -->
```text
Release "wordpress" does not exist. Installing it now.
NAME: wordpress
LAST DEPLOYED: Tue Oct 24 16:19:35 2023
NAMESPACE: wordpress
STATUS: deployed
REVISION: 1
TEST SUITE: None
NOTES:
CHART NAME: wordpress
CHART VERSION: 18.0.8
APP VERSION: 6.3.2

** Please be patient while the chart is being deployed **

Your WordPress site can be accessed through the following DNS name from within your cluster:

    wordpress.wordpress.svc.cluster.local (port 80)

To access your WordPress site from outside the cluster follow the steps below:

1. Get the WordPress URL and associate WordPress hostname to your cluster external IP:

   export CLUSTER_IP=$(minikube ip) # On Minikube. Use: `kubectl cluster-info` on others K8s clusters
   echo "WordPress URL: https://mydnslabelxxx.eastus.cloudapp.azure.com/"
   echo "$CLUSTER_IP  mydnslabelxxx.eastus.cloudapp.azure.com" | sudo tee -a /etc/hosts
    export CLUSTER_IP=$(minikube ip) # On Minikube. Use: `kubectl cluster-info` on others K8s clusters
    echo "WordPress URL: https://mydnslabelxxx.eastus.cloudapp.azure.com/"
    echo "$CLUSTER_IP  mydnslabelxxx.eastus.cloudapp.azure.com" | sudo tee -a /etc/hosts

2. Open a browser and access WordPress using the obtained URL.

3. Login with the following credentials below to see your blog:

    echo Username: wpcliadmin
    echo Password: $(kubectl get secret --namespace wordpress wordpress -o jsonpath="{.data.wordpress-password}" | base64 -d)
```

## HTTPS 経由でセキュリティ保護された AKS デプロイを参照する

次のコマンドを実行して、アプリケーションの HTTPS エンドポイントを取得します。

> [!NOTE]
> 多くの場合、SSL 証明書が反映されるまでに 2 分から 3 分かかり、すべての WordPress POD レプリカが準備され、サイトが https 経由で完全に到達できるようになるまでに約 5 分かかります。

```bash
runtime="5 minute"
endtime=$(date -ud "$runtime" +%s)
while [[ $(date -u +%s) -le $endtime ]]; do
    export DEPLOYMENT_REPLICAS=$(kubectl -n wordpress get deployment wordpress -o=jsonpath='{.status.availableReplicas}');
    echo Current number of replicas "$DEPLOYMENT_REPLICAS/3";
    if [ "$DEPLOYMENT_REPLICAS" = "3" ]; then
        break;
    else
        sleep 10;
    fi;
done
```

次のコマンドを使用して、WordPress コンテンツが正しく配信されていることを確認します。

```bash
if curl -I -s -f https://$FQDN > /dev/null ; then 
    curl -L -s -f https://$FQDN 2> /dev/null | head -n 9
else 
    exit 1
fi;
```

結果:
<!-- expected_similarity=0.3 -->
```HTML
{
<!DOCTYPE html>
<html lang="en-US">
<head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name='robots' content='max-image-preview:large' />
<title>WordPress on AKS</title>
<link rel="alternate" type="application/rss+xml" title="WordPress on AKS &raquo; Feed" href="https://mydnslabelxxx.eastus.cloudapp.azure.com/feed/" />
<link rel="alternate" type="application/rss+xml" title="WordPress on AKS &raquo; Comments Feed" href="https://mydnslabelxxx.eastus.cloudapp.azure.com/comments/feed/" />
}
```

次の URL を使用して Web サイトにアクセスします。

```bash
echo "You can now visit your web server at https://$FQDN"
```

## リソースをクリーンアップする (省略可能)

Azure の課金を回避するには、不要なリソースをクリーンアップする必要があります。 クラスターが不要になったら、[az group delete](/cli/azure/group#az-group-delete) コマンドを使用して、リソース グループ、コンテナー サービス、およびすべての関連リソースを削除します。 

> [!NOTE]
> クラスターを削除したとき、AKS クラスターで使用される Microsoft Entra サービス プリンシパルは削除されません。 サービス プリンシパルを削除する手順については、[AKS のサービス プリンシパルに関する考慮事項と削除](../../aks/kubernetes-service-principal.md#other-considerations)に関するページを参照してください。 マネージド ID を使用した場合、ID はプラットフォームによって管理されるので、削除する必要はありません。

## 次のステップ

- AKS クラスターの [Kubernetes Web ダッシュボードにアクセスする](../../aks/kubernetes-dashboard.md)方法を学習する
- [クラスターをスケーリングする](../../aks/tutorial-kubernetes-scale.md)方法を学習する
- [Azure Database for MySQL フレキシブル サーバー インスタンス](./quickstart-create-server-cli.md)の管理方法について学習する
- データベース サーバーの[サーバー パラメータを構成する](./how-to-configure-server-parameters-cli.md)方法を学習する
