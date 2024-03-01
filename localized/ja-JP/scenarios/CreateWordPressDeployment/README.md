---
title: AKS にスケーラブルで安全な WordPress インスタンスをデプロイする
description: このチュートリアルでは、CLI を使用して AKS にスケーラブルで安全な WordPress インスタンスをデプロイする方法について説明します
author: adrian.joian
ms.author: adrian.joian
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# クイック スタート: AKS にスケーラブルで安全な WordPress インスタンスをデプロイする

https を介してセキュリティで保護された Azure Kubernetes Web アプリケーションを作成する手順を説明するこのチュートリアルをご覧ください。 このチュートリアルは、既に Azure CLI にログインしており、CLI で使用するサブスクリプションが選択されていることを前提としています。 また、Helm がインストールされていることを前提としています ([手順はこちら](https://helm.sh/docs/intro/install/))。

## 環境変数を定義する

このチュートリアルの最初の手順は、環境変数を定義することです。

```bash
export SSL_EMAIL_ADDRESS="$(az account show --query user.name --output tsv)"
export NETWORK_PREFIX="$(($RANDOM % 253 + 1))"
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myWordPressAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_PUBLIC_IP_NAME="myPublicIP$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
export MY_VNET_NAME="myVNet$RANDOM_ID"
export MY_VNET_PREFIX="10.$NETWORK_PREFIX.0.0/16"
export MY_SN_NAME="mySN$RANDOM_ID"
export MY_SN_PREFIX="10.$NETWORK_PREFIX.0.0/22"
export MY_MYSQL_DB_NAME="mydb$RANDOM_ID"
export MY_MYSQL_ADMIN_USERNAME="dbadmin$RANDOM_ID"
export MY_MYSQL_ADMIN_PW="$(openssl rand -base64 32)"
export MY_MYSQL_SN_NAME="myMySQLSN$RANDOM_ID"
export MY_MYSQL_HOSTNAME="$MY_MYSQL_DB_NAME.mysql.database.azure.com"
export MY_WP_ADMIN_PW="$(openssl rand -base64 32)"
export MY_WP_ADMIN_USER="wpcliadmin"
export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
```

## リソース グループの作成

リソース グループとは、関連リソース用のコンテナーです。 すべてのリソースをリソース グループに配置する必要があります。 このチュートリアルに必要なものを作成します。 次のコマンドは、事前定義済みの $MY_RESOURCE_GROUP_NAME パラメーターと $REGION パラメーターを使用してリソース グループを作成します。

```bash
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

## 仮想ネットワークとサブネットの作成

仮想ネットワークは、Azure 内のプライベート ネットワークの基本的な構成ブロックです。 Azure Virtual Network では、VM などの Azure リソースが、相互に、およびインターネットと安全に通信することができます。

```bash
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

## Azure Database for MySQL - フレキシブル サーバーを作成する

Azure Database for MySQL - フレキシブル サーバーは、高可用性 MySQL サーバーをクラウドで実行、管理、スケーリングするために使用できる管理サービスです。 [az mysql flexible-server create](https://learn.microsoft.com/cli/azure/mysql/flexible-server#az-mysql-flexible-server-create) コマンドを使用して、フレキシブル サーバーを作成します。 1 つのサーバーに複数のデータベースを含めることができます。 次のコマンドでは、サービスの既定値と Azure CLI のローカル環境からの変数値を使用してサーバーを作成します。

```bash
echo "Your MySQL user $MY_MYSQL_ADMIN_USERNAME password is: $MY_WP_ADMIN_PW" 
```

```bash
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

- サーバー名、管理者ユーザー名、管理者パスワード、リソース グループ名、場所は、クラウド シェルのローカル コンテキスト環境で既に指定されており、リソース グループや他の Azure コンポーネントと同じ場所に作成されます。
- 残りのサーバー構成のサービスの既定値: コンピューティング レベル (バースト可能)、コンピューティング サイズ/SKU (Standard_B2s)、バックアップの保持期間 (7 日間)、および MySQL のバージョン (8.0.21)
- 既定の接続方法は、リンクされた仮想ネットワークと自動生成されたサブネットを使用するプライベート アクセス (VNet 統合) です。

> [!NOTE]
> サーバーの作成後に接続方法を変更することはできません。 たとえば、作成中に `Private access (VNet Integration)` を選択した場合は、作成後に `Public access (allowed IP addresses)` に変更することはできません。 VNet 統合を使用してサーバーに安全にアクセスするには、プライベート アクセスを指定してサーバーを作成することを強くお勧めします。 プライベート アクセスの詳細については、[概念に関する記事](https://learn.microsoft.com/azure/mysql/flexible-server/concepts-networking-vnet)を参照してください。

既定値を変更したい場合は、Azure CLI の[リファレンス ドキュメント](https://learn.microsoft.com/cli/azure//mysql/flexible-server)で、構成可能な CLI パラメーターの完全な一覧を参照してください。

## Azure Database for MySQL の確認 - フレキシブル サーバー状態

Azure Database for MySQL - フレキシブル サーバーとサポート リソースの作成には数分かかります。

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## Azure Database for MySQL - フレキシブル サーバーでサーバー パラメーターを構成する

サーバー パラメーターを使用して Azure Database for MySQL - フレキシブル サーバー構成を管理できます。 このサーバー パラメーターは、サーバーの作成時に既定値と推奨値を使用して構成されます。

サーバー パラメータの詳細を表示する サーバーの特定のパラメーターに関する詳細を表示するには、[az mysql flexible-server parameter show](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter) コマンドを実行します。

### WordPress 統合のために Azure Database for MySQL - フレキシブル サーバー SSL 接続パラメーターを無効にする

特定のサーバー パラメーターの値を変更することもできます。これによって MySQL サーバー エンジンの基盤となる構成値が更新されます。 サーバー パラメーターを更新するには、[az mysql flexible-server parameter set](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set) コマンドを使用します。

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

## AKS クラスターを作成

az aks create コマンドを、Container insights を有効にする --enable-addons monitoring パラメーターと共に使用して、AKS クラスターを作成します。 次の例では、myAKSCluster という名前の自動スケールの可用性ゾーンが有効なクラスターを作成します:

この処理には数分かかります

```bash
export MY_SN_ID=$(az network vnet subnet list --resource-group $MY_RESOURCE_GROUP_NAME --vnet-name $MY_VNET_NAME --query "[0].id" --output tsv)

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

## クラスターに接続する

Kubernetes クラスターを管理するには、Kubernetes のコマンドライン クライアントである kubectl を使います。 Azure Cloud Shell を使用している場合、kubectl は既にインストールされています。

1. az aks install-cli コマンドを使用して az aks CLI をローカルにインストールする

    ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
    ```

2. az aks get-credentials コマンドを使用して、Kubernetes クラスターに接続するように kubectl を構成します。 次のコマンドで、以下を行います。

    - 資格情報をダウンロードし、それを使用するように Kubernetes CLI を構成します。
    - ~/.kube/config (Kubernetes 構成ファイルの既定の場所) を使用します。 Kubernetes 構成ファイルに対して別の場所を指定するには、--file 引数を使用します。

    > [!WARNING]
    > これにより、同じエントリを使用して既存の資格情報が上書きされます

    ```bash
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
    ```

3. kubectl get コマンドを使用して、ご利用のクラスターへの接続を確認します。 このコマンドでは、クラスター ノードの一覧が返されます。

    ```bash
    kubectl get nodes
    ```

## NGINX イングレス コントローラーをインストールする

イングレス コントローラーに、静的なパブリック IP アドレスを構成できます。 イングレス コントローラーが削除されても、静的パブリック IP アドレスはそのまま残ります。 AKS クラスターを削除した場合、IP アドレスは "残りません"。
イングレス コントローラーをアップグレードする場合、割り当てられるロード バランサーをイングレス コントローラー サービスに認識させるために、Helm リリースにパラメーターを渡す必要があります。 HTTPS 証明書が正しく機能するように、DNS ラベルを使って、イングレス コントローラーの IP アドレス用に FQDN を構成します。
FQDN は次の形式に従う必要があります: $MY_DNS_LABEL。AZURE_REGION_NAME.cloudapp.azure.com。

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

--set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"="<DNS_LABEL>" パラメータを追加します。 DNS ラベルは、イングレス コントローラーを最初にデプロイするときに設定することも、後で構成することもできます。 --set controller.service.loadBalancerIP="STATIC_IP" パラメーターを追加します。 前の手順で作成された独自のパブリック IP アドレスを指定します。

1. ingress-nginx Helm リポジトリを追加する

    ```bash
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    ```

2. ローカルの Helm Chart リポジトリ キャッシュを更新する

    ```bash
    helm repo update
    ```

3. 次を実行して、Helm 経由で ingress-nginx アドオンをインストールします:

    ```bash
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

## Cert Manager を設定する

HTTPS を追加するには、Cert Manager を使用します。 Cert Manager は、Kubernetes デプロイ用の SSL 証明書の取得と管理に使用されるオープン ソース ツールです。 Cert Manager は、一般的なパブリック発行元やプライベート発行元など、さまざまな発行元から証明書を取得し、証明書が有効で最新であることを保証します。これにより、証明書の期限が切れる前に構成時点への更新が試行されます。

1. cert-manager をインストールするには、最初にそれを実行する名前空間を作成する必要があります。 このチュートリアルでは、cert-manager を cert-manager 名前空間にインストールします。 配置マニフェストに変更を加える必要がありますが、別の名前空間で cert-manager を実行できます。

    ```bash
    kubectl create namespace cert-manager
    ```

2. これで、cert-manager をインストールできるようになりました。 すべてのリソースは、1 つの YAML マニフェスト ファイルに含まれます。 これは、次のコマンドを実行してインストールできます。

    ```bash
    kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
    ```

3. 次のコマンドを実行して、certmanager.k8s.io/disable-validation: "true "ラベルを cert-manager 名前空間に追加します。 これにより、cert-manager が TLS をブートストラップするために必要なシステム リソースを独自の名前空間に作成できるようになります。

    ```bash
    kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
    ```

## Helm Charts を介して証明書を取得する

Helm は、Kubernetes クラスターへのアプリケーションやサービスの作成、パッケージ化、構成、デプロイを自動化するための Kubernetes デプロイ ツールです。

cert-manager では、Kubernetes への第一級のインストール方法として Helm チャートが提供されます。

1. Jetstack Helm リポジトリを追加する

    このリポジトリは、cert-manager チャートの唯一のサポート ソースです。 インターネット上には他にもいくつかのミラーやコピーがありますが、それらはすべて非公式なものであり、セキュリティ上のリスクがあります。

    ```bash
    helm repo add jetstack https://charts.jetstack.io
    ```

2. ローカルの Helm Chart リポジトリ キャッシュを更新する

    ```bash
    helm repo update
    ```

3. 次のコマンドを実行して、Helm を介して Cert-Manager アドオンをインストールします:

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. 証明書の発行者 YAML ファイルを適用する

    ClusterIssuers は、証明書署名要求を許可することで署名付き証明書を生成できる証明機関 (CA) を表す Kubernetes リソースです。 すべての cert-manager 証明書は、要求の許可を試行する準備の整った参照発行者が必要です。
    使用する発行者は `cluster-issuer-prod.yml file` で確認できます

    ```bash
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## カスタム ストレージ クラスを作成する

既定のストレージ クラスは最も一般的なシナリオに適合しますが、すべてに適合するわけではありません。 場合によっては、独自のストレージ クラスを独自のパラメーターを使用してカスタマイズすることもできます。 たとえば、次のマニフェストを使用して、ファイル共有の mountOptions を構成します。
Kubernetes でマウントされたファイル共有の場合、fileMode と dirMode の既定値は 0755 です。 ストレージ クラス オブジェクトでは、さまざまなマウント オプションを指定できます。

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## WordPress を AKS クラスターにデプロイする

このドキュメントでは、Bitnami によって構築された WordPress 用の既存の Helm グラフを使用しています。 たとえば、Bitnami Helm グラフではローカル MariaDB がデータベースとして使用されるため、Azure Database for MySQL でアプリを使用するには、これらの値をオーバーライドする必要があります。 すべてのオーバーライド値 値をオーバーライドでき、カスタム設定はファイル `helm-wp-aks-values.yaml` にあります

1. Wordpress Bitnami Helm リポジトリを追加する

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. ローカルの Helm Chart リポジトリ キャッシュを更新する

    ```bash
    helm repo update
    ```

3. 次を実行して、Helm を使用して Wordpress ワークロードをインストールします:

    ```bash
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

## HTTPS を介してセキュリティで保護された AKS デプロイの閲覧

次のコマンドを実行して、アプリケーションの HTTPS エンドポイントを取得します。

> [!NOTE]
> 多くの場合、SSL 証明書がプロポゲートされるまでに 2 - 3 分かかり、すべての WordPress POD レプリカが準備され、サイトが https 経由で完全に到達できるようになるまでに約 5 分かかります。

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

WordPress コンテンツが正しく配信されていることを確認します。

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

Web サイトには、以下の URL に従ってアクセスできます:

```bash
echo "You can now visit your web server at https://$FQDN"
```
