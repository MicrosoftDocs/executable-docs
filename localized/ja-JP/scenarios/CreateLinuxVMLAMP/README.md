---
title: Azure に LEMP スタックをインストールする
description: このチュートリアルでは、Azure に LEMP スタックをインストールする方法について説明します。
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Azure に LEMP スタックをインストールする

[![Azure に配置する](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateLinuxVMLAMP)


この記事では、NGINX Web サーバー、Azure MySQL フレキシブル サーバー、PHP (LEMP スタック) を Azure 上の Ubuntu Linux VM にデプロイする方法について説明します。 LEMP サーバーの動作を確認するために、WordPress サイトをインストールし、構成することもできます。 このチュートリアルで学習する内容は次のとおりです。

> [!div class="checklist"]

> * Linux Ubuntu VM を作成する
> * Web トラフィック用にポート 80 および 443 を開く
> * NGINX、Azure Flexible MySQL Server、PHP のインストールとセキュリティ保護
> * インストールと構成を確認する
> * WordPress のインストール

## 変数宣言

最初に、LEMP ワークロードの構成に役立ついくつかの変数を定義します。

```bash
export NETWORK_PREFIX="$(($RANDOM % 254 + 1))"
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myLEMPResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_VM_USERNAME="azureadmin"
export MY_VM_SIZE='Standard_DS2_v2'
export MY_VM_IMAGE='Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest'
export MY_PUBLIC_IP_NAME="myPublicIP$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
export MY_NSG_NAME="myNSG$RANDOM_ID"
export MY_NSG_SSH_RULE="Allow-Access$RANDOM_ID"
export MY_VM_NIC_NAME="myVMNic$RANDOM_ID"
export MY_VNET_NAME="myVNet$RANDOM_ID"
export MY_VNET_PREFIX="10.$NETWORK_PREFIX.0.0/22"
export MY_SN_NAME="mySN$RANDOM_ID"
export MY_SN_PREFIX="10.$NETWORK_PREFIX.0.0/24"
export MY_MYSQL_DB_NAME="mydb$RANDOM_ID"
export MY_MYSQL_ADMIN_USERNAME="dbadmin$RANDOM_ID"
export MY_MYSQL_ADMIN_PW="$(openssl rand -base64 32)"
export MY_MYSQL_SN_NAME="myMySQLSN$RANDOM_ID"
export MY_WP_ADMIN_PW="$(openssl rand -base64 32)"
export MY_WP_ADMIN_USER="wpcliadmin"
export MY_AZURE_USER=$(az account show --query user.name --output tsv)
export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
```

<!--```bash
export MY_AZURE_USER_ID=$(az ad user list --filter "mail eq '$MY_AZURE_USER'" --query "[0].id" -o tsv)
```-->

## RG を作成する

[az group create](https://learn.microsoft.com/cli/azure/group#az-group-create) コマンドを使用して、リソース グループを作成します。 Azure リソース グループとは、Azure リソースのデプロイと管理に使用する論理コンテナーです。
次の例では、`eastus` の場所に `$MY_RESOURCE_GROUP_NAME` という名前のリソース グループを作成します。

```bash
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION -o JSON
```

結果:

<!-- expected_similarity=0.3 -->
```JSON
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myLEMPResourceGroupxxxxxx",
  "location": "eastus",
  "managedBy": null,
  "name": "myLEMPResourceGroupxxxxxx",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## LEMP ネットワークの設定

## Azure Virtual Network の作成

仮想ネットワークは、Azure 内のプライベート ネットワークの基本的な構成ブロックです。 Azure Virtual Network では、VM などの Azure リソースが、相互に、およびインターネットと安全に通信することができます。
[az network vnet create](https://learn.microsoft.com/cli/azure/network/vnet#az-network-vnet-create) を使用して、`$MY_VNET_NAME` という名前の仮想ネットワークを、`$MY_SN_NAME` という名前のサブネットを指定して、`$MY_RESOURCE_GROUP_NAME` リソース グループに作成します。

```bash
az network vnet create \
    --name $MY_VNET_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefixes $MY_SN_PREFIX -o JSON
```

結果:

<!-- expected_similarity=0.3 -->
```JSON
{
  "newVNet": {
    "addressSpace": {
      "addressPrefixes": [
        "10.19.0.0/22"
      ]
    },
    "enableDdosProtection": false,
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myLEMPResourceGroupxxxxxx/providers/Microsoft.Network/virtualNetworks/myVNetxxxxxx",
    "location": "eastus",
    "name": "myVNetxxxxxx",
    "provisioningState": "Succeeded",
    "resourceGroup": "myLEMPResourceGroupxxxxxx",
    "subnets": [
      {
        "addressPrefix": "10.19.0.0/24",
        "delegations": [],
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myLEMPResourceGroupxxxxxx/providers/Microsoft.Network/virtualNetworks/myVNetxxxxxx/subnets/mySNxxxxxx",
        "name": "mySNxxxxxx",
        "privateEndpointNetworkPolicies": "Disabled",
        "privateLinkServiceNetworkPolicies": "Enabled",
        "provisioningState": "Succeeded",
        "resourceGroup": "myLEMPResourceGroupxxxxxx",
        "type": "Microsoft.Network/virtualNetworks/subnets"
      }
    ],
    "type": "Microsoft.Network/virtualNetworks",
    "virtualNetworkPeerings": []
  }
}
```

## Azure パブリック IP を作成する

[az network public-ip create](https://learn.microsoft.com/cli/azure/network/public-ip#az-network-public-ip-create) を使用して、`$MY_RESOURCE_GROUP_NAME` に `MY_PUBLIC_IP_NAME` という Standard ゾーン冗長パブリック IPv4 アドレスを作成します。

>[!NOTE]
>以下のゾーンのオプションは、[Availability Zones](https://learn.microsoft.com/azure/reliability/availability-zones-service-support) が利用できるリージョンでのみ有効な選択です。

```bash
az network public-ip create \
    --name $MY_PUBLIC_IP_NAME \
    --location $REGION \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --dns-name $MY_DNS_LABEL \
    --sku Standard \
    --allocation-method static \
    --version IPv4 \
    --zone 1 2 3 -o JSON
```

結果:

<!-- expected_similarity=0.3 -->
```JSON
{
  "publicIp": {
    "ddosSettings": {
      "protectionMode": "VirtualNetworkInherited"
    },
    "dnsSettings": {
      "domainNameLabel": "mydnslabelxxxxxx",
      "fqdn": "mydnslabelxxxxxx.eastus.cloudapp.azure.com"
    },
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myLEMPResourceGroupxxxxxx/providers/Microsoft.Network/publicIPAddresses/myPublicIPxxxxxx",
    "idleTimeoutInMinutes": 4,
    "ipTags": [],
    "location": "eastus",
    "name": "myPublicIPxxxxxx",
    "provisioningState": "Succeeded",
    "publicIPAddressVersion": "IPv4",
    "publicIPAllocationMethod": "Static",
    "resourceGroup": "myLEMPResourceGroupxxxxxx",
    "sku": {
      "name": "Standard",
      "tier": "Regional"
    },
    "type": "Microsoft.Network/publicIPAddresses",
    "zones": [
      "1",
      "2",
      "3"
    ]
  }
}
```

## Azure ネットワーク セキュリティ グループを作成する

ネットワーク セキュリティ グループのセキュリティ規則を使用して、仮想ネットワーク サブネットとネットワーク インターフェイスに出入りできるネットワーク トラフィックの種類をフィルター処理できます。 ネットワーク セキュリティ グループの詳細については、[ネットワーク セキュリティ グループの概要](https://learn.microsoft.com/azure/virtual-network/network-security-groups-overview)に関するページを参照してください。

```bash
az network nsg create \
    --name $MY_NSG_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION -o JSON
```

結果:

<!-- expected_similarity=0.3 -->
```JSON
{
  "NewNSG": {
    "defaultSecurityRules":
      {
        "access": "Allow",
        "description": "Allow inbound traffic from all VMs in VNET",
        "destinationAddressPrefix": "VirtualNetwork",
        "destinationAddressPrefixes": [],
        "destinationPortRange": "*",
        "destinationPortRanges": [],
        "direction": "Inbound",
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myLEMPResourceGroup104/providers/Microsoft.Network/networkSecurityGroups/protect-vms/defaultSecurityRules/AllowVnetInBound",
        "name": "AllowVnetInBound",
        "priority": 65000,
        "protocol": "*",
        "provisioningState": "Succeeded",
        "resourceGroup": "myLEMPResourceGroup104",
        "sourceAddressPrefix": "VirtualNetwork",
        "sourceAddressPrefixes": [],
        "sourcePortRange": "*",
        "sourcePortRanges": [],
        "type": "Microsoft.Network/networkSecurityGroups/defaultSecurityRules"
      },
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myLEMPResourceGroup104/providers/Microsoft.Network/networkSecurityGroups/protect-vms",
    "location": "eastus",
    "name": "protect-vms",
    "provisioningState": "Succeeded",
    "resourceGroup": "myLEMPResourceGroup104",
    "securityRules": [],
    "type": "Microsoft.Network/networkSecurityGroups"
  }
}
```

## Azure ネットワーク セキュリティ グループ規則を作成する

SSH に対してポート 22、HTTP と HTTPS に対してはそれぞれポート 80、ポート 443 上で仮想マシンへの接続を許可する規則を作成します。 追加の規則を作成すれば、アウトバウンド接続に対してすべてのポートを許可することができます。 [az network nsg rule create](https://learn.microsoft.com/cli/azure/network/nsg/rule#az-network-nsg-rule-create) を使って、ネットワーク セキュリティ グループ規則を作成します。

```bash
az network nsg rule create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --nsg-name $MY_NSG_NAME \
    --name $MY_NSG_SSH_RULE \
    --access Allow \
    --protocol Tcp \
    --direction Inbound \
    --priority 100 \
    --source-address-prefix '*' \
    --source-port-range '*' \
    --destination-address-prefix '*' \
    --destination-port-range 22 80 443 -o JSON
```

結果:

<!-- expected_similarity=0.3 -->
```JSON
{
  "access": "Allow",
  "destinationAddressPrefix": "*",
  "destinationAddressPrefixes": [],
  "destinationPortRanges": [
    "22",
    "80",
    "443"
  ],
  "direction": "Inbound",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myLEMPResourceGroupxxxxxx/providers/Microsoft.Network/networkSecurityGroups/myNSGNamexxxxxx/securityRules/Allow-Accessxxxxxx",
  "name": "Allow-Accessxxxxxx",
  "priority": 100,
  "protocol": "Tcp",
  "provisioningState": "Succeeded",
  "resourceGroup": "myLEMPResourceGroupxxxxxx",
  "sourceAddressPrefix": "*",
  "sourceAddressPrefixes": [],
  "sourcePortRange": "*",
  "sourcePortRanges": [],
  "type": "Microsoft.Network/networkSecurityGroups/securityRules"
}
```

## Azure ネットワーク インターフェイスを作成する

仮想マシンのネットワーク インターフェイスを作成するには、[az network nic create](https://learn.microsoft.com/cli/azure/network/nic#az-network-nic-create)を使用します。 以前に作成したパブリック IP アドレスと NSG は、NIC に関連付けられています。 ネットワーク インターフェイスは、前に作成した仮想ネットワークに接続されています。

```bash
az network nic create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_VM_NIC_NAME \
    --location $REGION \
    --ip-forwarding false \
    --subnet $MY_SN_NAME \
    --vnet-name $MY_VNET_NAME \
    --network-security-group $MY_NSG_NAME \
    --public-ip-address $MY_PUBLIC_IP_NAME -o JSON
```

結果:

<!-- expected_similarity=0.3 -->
```JSON
{
  "NewNIC": {
    "auxiliaryMode": "None",
    "auxiliarySku": "None",
    "disableTcpStateTracking": false,
    "dnsSettings": {
      "appliedDnsServers": [],
      "dnsServers": []
    },
    "enableAcceleratedNetworking": false,
    "enableIPForwarding": false,
    "hostedWorkloads": [],
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myLEMPResourceGroupxxxxxx/providers/Microsoft.Network/networkInterfaces/myVMNicNamexxxxxx",
    "ipConfigurations": [
      {
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myLEMPResourceGroupxxxxxx/providers/Microsoft.Network/networkInterfaces/myVMNicNamexxxxxx/ipConfigurations/ipconfig1",
        "name": "ipconfig1",
        "primary": true,
        "privateIPAddress": "10.19.0.4",
        "privateIPAddressVersion": "IPv4",
        "privateIPAllocationMethod": "Dynamic",
        "provisioningState": "Succeeded",
        "resourceGroup": "myLEMPResourceGroupxxxxxx",
        "subnet": {
          "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myLEMPResourceGroupxxxxxx/providers/Microsoft.Network/virtualNetworks/myVNetxxxxxx/subnets/mySNxxxxxx",
          "resourceGroup": "myLEMPResourceGroupxxxxxx"
        },
        "type": "Microsoft.Network/networkInterfaces/ipConfigurations"
      }
    ],
    "location": "eastus",
    "name": "myVMNicNamexxxxxx",
    "networkSecurityGroup": {
      "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myLEMPResourceGroupxxxxxx/providers/Microsoft.Network/networkSecurityGroups/myNSGNamexxxxxx",
      "resourceGroup": "myLEMPResourceGroupxxxxxx"
    },
    "nicType": "Standard",
    "provisioningState": "Succeeded",
    "resourceGroup": "myLEMPResourceGroupxxxxxx",
    "tapConfigurations": [],
    "type": "Microsoft.Network/networkInterfaces",
    "vnetEncryptionSupported": false
  }
}
```

## cloud-init の概要

cloud-Init は、Linux VM を初回起動時にカスタマイズするために広く使用されているアプローチです。 cloud-init を使って、パッケージをインストールしてファイルを書き込んだり、ユーザーとセキュリティを構成したりすることができます。 初回起動処理中に cloud-init が実行されるので、構成を適用するために追加の手順や必要なエージェントはありません。

cloud-init はディストリビューション全体でも有効です。 たとえば、パッケージをインストールするときに apt-get install や yum install は使用しません。 代わりに、cloud-init ではインストールするパッケージの一覧をユーザーが定義できます。 cloud-init によって、選択したディストリビューションに対してネイティブのパッケージ管理ツールが自動的に使用されます。

Microsoft ではパートナーと協力して、パートナーから Azure に提供されたイメージに cloud-init を含めて、使用できるようにしています。 ディストリビューションごとの cloud-init のサポートに関する詳しい情報については、[Azure での VM に対する cloud-init のサポート](https://learn.microsoft.com/azure/virtual-machines/linux/using-cloud-init)に関する記事を参照してください。

### cloud-init 構成ファイルを作成する

実際の cloud-init を確認するには、LEMP スタックをインストールし、SSL 証明書を使用してセキュリティで保護されたシンプルな Wordpress アプリを実行する VM を作成します。 次の cloud-init 構成によって、必要なパッケージのインストール、Wordpress Web サイトの作成、Web サイトの初期化と起動が行われます。

```bash
cat << EOF > cloud-init.txt
#cloud-config

# Install, update, and upgrade packages
package_upgrade: true
package_update: true
package_reboot_if_require: true

# Install packages
packages:
  - vim
  - certbot
  - python3-certbot-nginx
  - bash-completion
  - nginx
  - mysql-client
  - php
  - php-cli
  - php-bcmath
  - php-curl
  - php-imagick
  - php-intl
  - php-json
  - php-mbstring
  - php-mysql
  - php-gd
  - php-xml
  - php-xmlrpc
  - php-zip
  - php-fpm

write_files:
  - owner: www-data:www-data
    path: /etc/nginx/sites-available/default.conf
    content: |
        server {
            listen 80 default_server;
            listen [::]:80 default_server;
            root /var/www/html;
            server_name $FQDN;
        }

write_files:
  - owner: www-data:www-data
    path: /etc/nginx/sites-available/$FQDN.conf
    content: |
        upstream php {
            server unix:/run/php/php8.1-fpm.sock;
        }
        server {
            listen 443 ssl http2;
            listen [::]:443 ssl http2;

            server_name $FQDN;

            ssl_certificate /etc/letsencrypt/live/$FQDN/fullchain.pem;
            ssl_certificate_key /etc/letsencrypt/live/$FQDN/privkey.pem;

            root /var/www/$FQDN;
            index index.php;

            location / {
                try_files \$uri \$uri/ /index.php?\$args;
            }
            location ~ \.php$ {
                include fastcgi_params;
                fastcgi_intercept_errors on;
                fastcgi_pass php;
                fastcgi_param  SCRIPT_FILENAME \$document_root\$fastcgi_script_name;
            }
            location ~* \.(js|css|png|jpg|jpeg|gif|ico)$ {
                    expires max;
                    log_not_found off;
            }
            location = /favicon.ico {
                    log_not_found off;
                    access_log off;
            }

            location = /robots.txt {
                    allow all;
                    log_not_found off;
                    access_log off;
            }
        }
        server {
            listen 80;
            listen [::]:80;
            server_name $FQDN;
            return 301 https://$FQDN\$request_uri;
        }

runcmd:
  - sed -i 's/;cgi.fix_pathinfo.*/cgi.fix_pathinfo = 1/' /etc/php/8.1/fpm/php.ini
  - sed -i 's/^max_execution_time \= .*/max_execution_time \= 300/g' /etc/php/8.1/fpm/php.ini
  - sed -i 's/^upload_max_filesize \= .*/upload_max_filesize \= 64M/g' /etc/php/8.1/fpm/php.ini
  - sed -i 's/^post_max_size \= .*/post_max_size \= 64M/g' /etc/php/8.1/fpm/php.ini
  - systemctl restart php8.1-fpm
  - systemctl restart nginx
  - certbot --nginx certonly --non-interactive --agree-tos -d $FQDN -m dummy@dummy.com --redirect
  - ln -s /etc/nginx/sites-available/$FQDN.conf /etc/nginx/sites-enabled/
  - rm /etc/nginx/sites-enabled/default
  - systemctl restart nginx
  - curl --url https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar --output /tmp/wp-cli.phar
  - mv /tmp/wp-cli.phar /usr/local/bin/wp
  - chmod +x /usr/local/bin/wp
  - wp cli update
  - mkdir -m 0755 -p /var/www/$FQDN
  - chown -R azureadmin:www-data /var/www/$FQDN
  - sudo -u azureadmin -i -- wp core download --path=/var/www/$FQDN
  - sudo -u azureadmin -i -- wp config create --dbhost=$MY_MYSQL_DB_NAME.mysql.database.azure.com --dbname=wp001 --dbuser=$MY_MYSQL_ADMIN_USERNAME --dbpass="$MY_MYSQL_ADMIN_PW" --path=/var/www/$FQDN
  - sudo -u azureadmin -i -- wp core install --url=$FQDN --title="Azure hosted blog" --admin_user=$MY_WP_ADMIN_USER --admin_password="$MY_WP_ADMIN_PW" --admin_email=$MY_AZURE_USER --path=/var/www/$FQDN 
  - sudo -u azureadmin -i -- wp plugin update --all --path=/var/www/$FQDN
  - chmod 600 /var/www/$FQDN/wp-config.php
  - mkdir -p -m 0775 /var/www/$FQDN/wp-content/uploads
  - chgrp www-data /var/www/$FQDN/wp-content/uploads
EOF
```

## Azure MySQL フレキシブル サーバー向け Azure プライベート DNS ゾーンを作成する

Azure プライベート DNS ゾーンの統合により、現在の VNET 内、またはそのプライベート DNS ゾーンがリンクされたリージョン内のピアリングされた VNET のプライベート DNS を解決できます。 [az network private-dns zone create](https://learn.microsoft.com/cli/azure/network/private-dns/zone#az-network-private-dns-zone-create) を使用して、プライベート DNS ゾーンを作成します。

```bash
az network private-dns zone create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_DNS_LABEL.private.mysql.database.azure.com -o JSON
```

結果:

<!-- expected_similarity=0.3 -->
```JSON
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myLEMPResourceGroupxxxxxx/providers/Microsoft.Network/privateDnsZones/mydnslabelxxxxxx.private.mysql.database.azure.com",
  "location": "global",
  "maxNumberOfRecordSets": 25000,
  "maxNumberOfVirtualNetworkLinks": 1000,
  "maxNumberOfVirtualNetworkLinksWithRegistration": 100,
  "name": "mydnslabelxxxxxx.private.mysql.database.azure.com",
  "numberOfRecordSets": 1,
  "numberOfVirtualNetworkLinks": 0,
  "numberOfVirtualNetworkLinksWithRegistration": 0,
  "provisioningState": "Succeeded",
  "resourceGroup": "myLEMPResourceGroupxxxxxx",
  "tags": null,
  "type": "Microsoft.Network/privateDnsZones"
}
```

## Azure Database for MySQL - フレキシブル サーバーを作成する

Azure Database for MySQL - フレキシブル サーバーは、高可用性 MySQL サーバーをクラウドで実行、管理、スケーリングするために使用できる管理サービスです。 [az mysql flexible-server create](https://learn.microsoft.com/cli/azure/mysql/flexible-server#az-mysql-flexible-server-create) コマンドを使用して、フレキシブル サーバーを作成します。 1 つのサーバーに複数のデータベースを含めることができます。 次のコマンドでは、サービスの既定値と Azure CLI のローカル環境からの変数値を使用してサーバーを作成します。

```bash
az mysql flexible-server create \
    --admin-password $MY_MYSQL_ADMIN_PW \
    --admin-user $MY_MYSQL_ADMIN_USERNAME \
    --auto-scale-iops Disabled \
    --high-availability Disabled \
    --iops 500 \
    --location $REGION \
    --name $MY_MYSQL_DB_NAME \
    --database-name wp001 \
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
```JSON
{
  "databaseName": "wp001",
  "host": "mydbxxxxxx.mysql.database.azure.com",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myLEMPResourceGroupxxxxxx/providers/Microsoft.DBforMySQL/flexibleServers/mydbxxxxxx",
  "location": "East US",
  "resourceGroup": "myLEMPResourceGroupxxxxxx",
  "skuname": "Standard_B2s",
  "subnetId": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myLEMPResourceGroupxxxxxx/providers/Microsoft.Network/virtualNetworks/myVNetxxxxxx/subnets/myMySQLSNxxxxxx",
  "username": "dbadminxxxxxx",
  "version": "8.0.21"
}
```

```bash
echo "Your MySQL user $MY_MYSQL_ADMIN_USERNAME password is: $MY_WP_ADMIN_PW"
```

作成されたサーバーには、次の属性があります。

* サーバー名、管理者ユーザー名、管理者パスワード、リソース グループ名、場所は、クラウド シェルのローカル コンテキスト環境で既に指定されており、リソース グループや他の Azure コンポーネントと同じ場所に作成されます。
* 残りのサーバー構成のサービスの既定値: コンピューティング レベル (バースト可能)、コンピューティング サイズ/SKU (Standard_B2s)、バックアップの保持期間 (7 日間)、および MySQL のバージョン (8.0.21)
* 既定の接続方法は、リンクされた仮想ネットワークと自動生成されたサブネットを使用するプライベート アクセス (VNet 統合) です。

> [!NOTE]
> サーバーの作成後に接続方法を変更することはできません。 たとえば、作成中に `Private access (VNet Integration)` を選択した場合は、作成後に `Public access (allowed IP addresses)` に変更することはできません。 VNet 統合を使用してサーバーに安全にアクセスするには、プライベート アクセスを指定してサーバーを作成することを強くお勧めします。 プライベート アクセスの詳細については、[概念に関する記事](https://learn.microsoft.com/azure/mysql/flexible-server/concepts-networking-vnet)を参照してください。

既定値を変更したい場合は、Azure CLI の[リファレンス ドキュメント](https://learn.microsoft.com/cli/azure//mysql/flexible-server)で、構成可能な CLI パラメーターの完全な一覧を参照してください。

## Azure Database for MySQL の確認 - フレキシブル サーバー状態

Azure Database for MySQL - フレキシブル サーバーとサポート リソースの作成には数分かかります。

```bash
runtime="10 minute";
endtime=$(date -ud "$runtime" +%s);
while [[ $(date -u +%s) -le $endtime ]]; do
  STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv);
  echo $STATUS;
  if [ "$STATUS" == 'Ready' ]; then
    break;
  else
    sleep 10;
  fi;
done
```

## Azure Database for MySQL - フレキシブル サーバーでサーバー パラメーターを構成する

サーバー パラメーターを使用して Azure Database for MySQL - フレキシブル サーバー構成を管理できます。 このサーバー パラメーターは、サーバーの作成時に既定値と推奨値を使用して構成されます。

サーバー パラメータの詳細を表示する サーバーの特定のパラメーターに関する詳細を表示するには、[az mysql flexible-server parameter show](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter) コマンドを実行します。

### Wordpress 統合のために Azure Database for MySQL - フレキシブル サーバー SSL 接続パラメーターを無効にする

サーバー パラメーター値を変更する 特定のサーバー パラメーターの値を変更することもできます。これによって MySQL サーバー エンジンの基盤となる構成値が更新されます。 サーバー パラメーターを更新するには、[az mysql flexible-server parameter set](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set) コマンドを使用します。

```bash
az mysql flexible-server parameter set \
    -g $MY_RESOURCE_GROUP_NAME \
    -s $MY_MYSQL_DB_NAME \
    -n require_secure_transport -v "OFF" -o JSON
```

結果:

<!-- expected_similarity=0.3 -->
```JSON
{
  "allowedValues": "ON,OFF",
  "currentValue": "OFF",
  "dataType": "Enumeration",
  "defaultValue": "ON",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myLEMPResourceGroupxxxxxx/providers/Microsoft.DBforMySQL/flexibleServers/mydbxxxxxx/configurations/require_secure_transport",
  "isConfigPendingRestart": "False",
  "isDynamicConfig": "True",
  "isReadOnly": "False",
  "name": "require_secure_transport",
  "resourceGroup": "myLEMPResourceGroupxxxxxx",
  "source": "user-override",
  "systemData": null,
  "type": "Microsoft.DBforMySQL/flexibleServers/configurations",
  "value": "OFF"
}
```

## Azure Linux 仮想マシンを作成する

次の例では、`$MY_VM_NAME` という名前の VM を作成し、既定のキーの場所にまだ SSH キーが存在しない場合は SSH キーを作成します。 このコマンドは、管理者ユーザー名として `$MY_VM_USERNAME` も設定します。
Azure の Linux 仮想マシンのセキュリティを強化するために、Azure Active Directory の認証と統合できます。 コア認証プラットフォームと証明機関として Azure AD を使用して、Azure AD および OpenSSH 証明書ベースの認証によって Linux VM に SSH 接続できるようになりました。 この機能により、組織は、Azure ロールベースのアクセス制御ポリシーと条件付きアクセス ポリシーを使用して、VM へのアクセスを管理できます。

[az vm create](https://learn.microsoft.com/cli/azure/vm#az-vm-create) コマンドで VM を作成します。

```bash
az vm create \
    --name $MY_VM_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --admin-username $MY_VM_USERNAME \
    --authentication-type ssh \
    --assign-identity \
    --image $MY_VM_IMAGE \
    --location $REGION \
    --nic-delete-option Delete \
    --os-disk-caching ReadOnly \
    --os-disk-delete-option Delete \
    --os-disk-size-gb 30 \
    --size $MY_VM_SIZE \
    --generate-ssh-keys \
    --storage-sku Premium_LRS \
    --nics $MY_VM_NIC_NAME \
    --custom-data cloud-init.txt -o JSON
```

結果:

<!-- expected_similarity=0.3 -->
```JSON
{
  "fqdns": "mydnslabelxxxxxx.eastus.cloudapp.azure.com",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myLEMPResourceGroupxxxxxx/providers/Microsoft.Compute/virtualMachines/myVMNamexxxxxx",
  "identity": {
    "principalId": "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy",
    "tenantId": "zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz",
    "type": "SystemAssigned",
    "userAssignedIdentities": null
  },
  "location": "eastus",
  "macAddress": "60-45-BD-D8-1D-84",
  "powerState": "VM running",
  "privateIpAddress": "10.19.0.4",
  "resourceGroup": "myLEMPResourceGroupxxxxxx",
  "zones": ""
}
```

## Azure Linux 仮想マシンの状態を確認する

VM とサポートするリソースを作成するには数分かかります。 VM に拡張機能が正常にインストールされると、provisioningState 値に Succeeded が表示されます。 拡張機能をインストールするには、VM に実行中の [VM エージェント](https://learn.microsoft.com/azure/virtual-machines/extensions/agent-linux)が必要です。

```bash
runtime="5 minute";
endtime=$(date -ud "$runtime" +%s);
while [[ $(date -u +%s) -le $endtime ]]; do 
    STATUS=$(ssh -o StrictHostKeyChecking=no $MY_VM_USERNAME@$FQDN "cloud-init status --wait"); 
    echo $STATUS; 
    if [[ "$STATUS" == *'status: done'* ]]; then 
        break; 
    else 
        sleep 10;
    fi;
done
```

<!--
## Assign Azure AD RBAC for Azure AD login for Linux Virtual Machine

The below command uses [az role assignment create](https://learn.microsoft.com/cli/azure/role/assignment#az-role-assignment-create) to assign the `Virtual Machine Administrator Login` role to the VM for your current Azure user.

```bash
export MY_RESOURCE_GROUP_ID=$(az group show --resource-group $MY_RESOURCE_GROUP_NAME --query id -o tsv)

az role assignment create \
    --role "Virtual Machine Administrator Login" \
    --assignee $MY_AZURE_USER_ID \
    --scope $MY_RESOURCE_GROUP_ID -o JSON
```


Results:
<!-- expected_similarity=0.3
```JSON
{
  "condition": null,
  "conditionVersion": null,
  "createdBy": null,
  "createdOn": "2023-09-04T09:29:16.895907+00:00",
  "delegatedManagedIdentityResourceId": null,
  "description": null,
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myLEMPResourceGroupxxxxxx/providers/Microsoft.Authorization/roleAssignments/yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy",
  "name": "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy",
  "principalId": "zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz",
  "principalType": "User",
  "resourceGroup": "myLEMPResourceGroupxxxxxx",
  "roleDefinitionId": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/providers/Microsoft.Authorization/roleDefinitions/zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz",
  "scope": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myLEMPResourceGroupxxxxxx",
  "type": "Microsoft.Authorization/roleAssignments",
  "updatedBy": "wwwwwwww-wwww-wwww-wwww-wwwwwwwwwwww",
  "updatedOn": "2023-09-04T09:29:17.237445+00:00"
}
```
-->

<!-- 
## Export the SSH configuration for use with SSH clients that support OpenSSH

Login to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:

```bash
az ssh config --file ~/.ssh/azure-config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

## Azure 内の Linux 仮想マシンに対して Azure AD ログインを有効にする

次の例では、拡張機能をインストールして、Linux VM に対して Azure AD ログインを有効にします。 VM 拡張機能は、Azure 仮想マシンでのデプロイ後の構成と自動タスクを提供する小さなアプリケーションです。

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME -o JSON
```

結果:

<!-- expected_similarity=0.3 -->
```JSON
{
  "autoUpgradeMinorVersion": true,
  "enableAutomaticUpgrade": null,
  "forceUpdateTag": null,
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myLEMPResourceGroupxxxxxx/providers/Microsoft.Compute/virtualMachines/myVMNamexxxxxx/extensions/AADSSHLoginForLinux",
  "instanceView": null,
  "location": "eastus",
  "name": "AADSSHLoginForLinux",
  "protectedSettings": null,
  "protectedSettingsFromKeyVault": null,
  "provisioningState": "Succeeded",
  "publisher": "Microsoft.Azure.ActiveDirectory",
  "resourceGroup": "myLEMPResourceGroupxxxxxx",
  "settings": null,
  "suppressFailures": null,
  "tags": null,
  "type": "Microsoft.Compute/virtualMachines/extensions",
  "typeHandlerVersion": "1.0",
  "typePropertiesType": "AADSSHLoginForLinux"
}
```

## WordPress Web サイトの確認と閲覧

[WordPress](https://www.wordpress.org)は、Web サイト、ブログ、その他のアプリケーションの作成において、Web の 40% 以上で使用されているオープンソースのコンテンツ管理システム (CMS) です。 WordPress は、いくつかの異なる Azure サービス ([AKS](https://learn.microsoft.com/azure/mysql/flexible-server/tutorial-deploy-wordpress-on-aks)、Virtual Machines、App Service) で実行できます。 Azure の WordPress オプションの完全な一覧については、[Azure Marketplace の WordPress](https://azuremarketplace.microsoft.com/marketplace/apps?page=1&search=wordpress) に関するページを参照してください。

ここで行う WordPress のセットアップは、概念実証だけを目的としています。 推奨されるセキュリティ設定で運用環境に最新の WordPress をインストールする場合は、[WordPress のドキュメント](https://codex.wordpress.org/Main_Page)をご覧ください。

アプリケーションの URL に curl を実行して、アプリケーションが実行されていることを確認します。

```bash
runtime="5 minute";
endtime=$(date -ud "$runtime" +%s);
while [[ $(date -u +%s) -le $endtime ]]; do
    if curl -I -s -f $FQDN > /dev/null ; then 
        curl -L -s -f $FQDN 2> /dev/null | head -n 9
        break
    else 
        sleep 10
    fi;
done
```

結果:

<!-- expected_similarity=0.3 -->
```HTML
<!DOCTYPE html>
<html lang="en-US">
<head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name='robots' content='max-image-preview:large' />
<title>Azure hosted blog</title>
<link rel="alternate" type="application/rss+xml" title="Azure hosted blog &raquo; Feed" href="https://mydnslabelxxxxxx.eastus.cloudapp.azure.com/?feed=rss2" />
<link rel="alternate" type="application/rss+xml" title="Azure hosted blog &raquo; Comments Feed" href="https://mydnslabelxxxxxx.eastus.cloudapp.azure.com/?feed=comments-rss2" />
```

```bash
echo "You can now visit your web server at https://$FQDN"
```
