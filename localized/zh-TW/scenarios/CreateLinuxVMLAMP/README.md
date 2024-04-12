---
title: 教學課程 - 在 VM 上使用 WordPress 部署 LEMP 堆棧
description: 在本教學課程中，您將瞭解如何在 Azure 中的 Linux 虛擬機上安裝 LEMP 堆疊和 WordPress。
author: chasecrum
ms.collection: linux
ms.service: virtual-machines
ms.devlang: azurecli
ms.custom: 'innovation-engine, linux-related-content, devx-track-azurecli'
ms.topic: tutorial
ms.date: 2/29/2024
ms.author: chasecrum
ms.reviewer: jushim
---

# 教學課程：在 Azure Linux VM 上安裝 LEMP 堆棧

**適用於：：** heavy_check_mark：Linux VM

[![部署至 Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateLinuxVMLAMP)

本文將逐步引導您如何在 Azure 中的 Ubuntu Linux VM 上部署 NGINX Web 伺服器、Azure MySQL 彈性伺服器和 PHP （LEMP 堆棧）。 若要查看 LEMP 伺服器運作情形，您可以選擇性地安裝及設定 WordPress 網站。 在本教學課程中，您將了解如何：

> [!div class="checklist"]
>
> * 建立 Ubuntu VM
> * 開啟網路流量的埠 80 和 443
> * 安裝和保護 NGINX、Azure 彈性 MySQL 伺服器和 PHP
> * 驗證安裝和設定
> * 安裝 WordPress 此設定適用於快速測試或概念證明。 如需 LEMP 堆疊的詳細資訊，包括生產環境的建議，請參閱 [Ubuntu 檔](https://help.ubuntu.com/community/ApacheMySQLPHP)。

本教學課程會使用 [Azure Cloud Shell](../../cloud-shell/overview.md) 內的 CLI，這會不斷更新至最新版本。 若要開啟 Cloud Shell，請選取任何程式碼區塊頂端的 [試試看]****。

如果您選擇在本機安裝和使用 CLI，本教學課程會要求您執行 Azure CLI 2.0.30 版或更新版本。 執行 命令來 `az --version` 尋找版本。 如果您需要安裝或升級，請參閱[安裝 Azure CLI]( /cli/azure/install-azure-cli)。

## 變數宣告

首先，我們需要定義幾個變數，以協助設定 LEMP 工作負載。

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

<!--
```bash
export MY_AZURE_USER_ID=$(az ad user list --filter "mail eq '$MY_AZURE_USER'" --query "[0].id" -o tsv)
```
-->

## 建立資源群組

使用 [az group create](/cli/azure/group#az-group-create) 命令來建立資源群組。 Azure 資源群組是在其中部署與管理 Azure 資源的邏輯容器。
下列範例會在 `eastus` 位置建立名為 `$MY_RESOURCE_GROUP_NAME` 的資源群組。

```bash
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION -o JSON
```

結果：

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

## 設定 LEMP 網路功能

## 建立 Azure 虛擬網路

虛擬網路是 Azure 中私人網路的基礎建置區塊。 Azure 虛擬網路可讓 Azure 資源 (例如 VM) 彼此安全地通訊，以及與網際網路安全地通訊。
使用 [az network vnet create 建立](/cli/azure/network/vnet#az-network-vnet-create) 名為 `$MY_VNET_NAME` 的虛擬網路，並在資源群組中建立名為 `$MY_SN_NAME` 的 `$MY_RESOURCE_GROUP_NAME` 子網。

```bash
az network vnet create \
    --name $MY_VNET_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefixes $MY_SN_PREFIX -o JSON
```

結果：

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

## 建立 Azure 公用 IP

使用 [az network public-ip create](/cli/azure/network/public-ip#az-network-public-ip-create) 建立名為 `MY_PUBLIC_IP_NAME` `$MY_RESOURCE_GROUP_NAME`的標準區域備援公用 IPv4 位址。

>[!NOTE]
>下列區域選項只有在具有 [可用性區域](../../reliability/availability-zones-service-support.md) 的區域中才有效選取。
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

結果：

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

## 建立 Azure 網路安全組

網路安全性群組中的安全性規則能讓您篩選可在虛擬網路子網路及網路介面中流入和流出的網路流量類型。 若要深入了解網路安全性群組，請參閱[網路安全性群組概觀](../../virtual-network/network-security-groups-overview.md)。

```bash
az network nsg create \
    --name $MY_NSG_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION -o JSON
```

結果：

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

## 建立 Azure 網路安全組規則

建立規則以允許連線到埠 22 上的虛擬機，以用於 SSH 和 HTTPS 的埠 80、443。 系統會建立額外的規則，以允許所有連接埠進行輸出連線。 使用 [az network nsg rule create](/cli/azure/network/nsg/rule#az-network-nsg-rule-create) 來建立網路安全性群組規則。

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

結果：

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

## 建立 Azure 網路介面

使用 [az network nic create](/cli/azure/network/nic#az-network-nic-create) 來建立虛擬機器的網路介面。 先前建立的公用 IP 位址和 NSG 會與 NIC 相關聯。 網路介面會附加至您先前建立的虛擬網路。

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

結果：

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
## Cloud-Init 概觀

Cloud-init (英文) 是在 Linux VM 初次開機時，廣泛用來自訂它們的方法。 您可以使用 cloud-init 來安裝封裝和寫入檔案，或者設定使用者和安全性。 當 cloud-init 在初始開機程式期間執行時，沒有任何其他步驟或必要的代理程式可套用至您的設定。

Cloud-init 也適用於散發套件。 例如，您不使用 apt-get install 或 yum install 來安裝套件。 您可以改為定義要安裝的套件清單。 Cloud-init 會針對您選取的散發套件自動使用原生的套件管理工具。

我們正與我們的合作夥伴合作，以包含 cloud-init 並處理他們提供給 Azure 的映像。 如需每個發佈的 cloud-init 支援詳細資訊，請參閱 [Azure中 VM 的 cloud-init 支援](./using-cloud-init.md)。

### 建立 Cloud-init 組態檔

若要查看 cloud-init 運作情形，請建立一個 VM 來安裝 LEMP 堆疊，並執行使用 SSL 憑證保護的簡單 Wordpress 應用程式。 下列 cloud-init 組態會安裝必要的套件、建立 Wordpress 網站，然後初始化並啟動網站。

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

## 建立適用於 Azure MySQL 彈性伺服器的 Azure 私用 DNS 區域

Azure 私用 DNS 區域整合可讓您解析目前 VNET 內的私人 DNS，或連結私人 DNS 區域的任何區域內對等互連 VNET。 使用 [az network private-dns zone create](/cli/azure/network/private-dns/zone#az-network-private-dns-zone-create) 建立私人 DNS 區域。

```bash
az network private-dns zone create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_DNS_LABEL.private.mysql.database.azure.com -o JSON
```

結果：

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

## 建立 適用於 MySQL 的 Azure 資料庫 - 彈性伺服器

適用於 MySQL 的 Azure 資料庫 - 彈性伺服器是受控服務，可用來在雲端中執行、管理及調整高可用性 MySQL 伺服器。 使用 [az mysql flexible-server create](../../mysql/flexible-server/quickstart-create-server-cli.md#create-an-azure-database-for-mysql-flexible-server) 命令建立彈性伺服器。 伺服器可以包含多個資料庫。 下列命令會使用 Azure CLI 本機環境的服務預設值和變數值來建立伺服器：

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

結果：

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

建立的伺服器具有下列屬性：

* 已在 Cloud Shell 的本機內容環境中指定伺服器名稱、管理員使用者名稱、系統管理員密碼、資源組名、位置。 它們會建立在與您的資源群組和其他 Azure 元件相同的位置。
* 其餘伺服器組態的服務預設值：計算層（高載）、計算大小/SKU（Standard_B2s）、備份保留期間（7 天），以及 MySQL 版本（8.0.21）
* 默認的連線方法是私人存取（VNet 整合）與鏈接的虛擬網路和自動產生的子網。

> [!NOTE]
> 建立伺服器之後，無法變更連線方法。 例如，如果您在建立期間選取 `Private access (VNet Integration)` ，則無法在建立之後變更為 `Public access (allowed IP addresses)` 。 強烈建議建立具有私人存取權的伺服器，以使用 VNet 整合安全地存取您的伺服器。 在概念文章[中](../../mysql/flexible-server/concepts-networking-vnet.md)深入瞭解私人存取。
如果您想要變更任何預設值，請參閱 Azure CLI [參考檔](../../mysql/flexible-server/quickstart-create-server-cli.md) ，以取得可設定 CLI 參數的完整清單。

## 檢查 適用於 MySQL 的 Azure 資料庫 - 彈性伺服器狀態

建立 適用於 MySQL 的 Azure 資料庫 - 彈性伺服器和支持資源需要幾分鐘的時間。

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

## 在 適用於 MySQL 的 Azure 資料庫 中設定伺服器參數 - 彈性伺服器

您可以使用伺服器參數來管理 適用於 MySQL 的 Azure 資料庫 - 彈性伺服器設定。 當您建立伺服器時，伺服器參數會設定為預設值和建議值。

顯示伺服器參數詳細資料：

[執行 az mysql flexible-server parameter show](../../mysql/flexible-server/how-to-configure-server-parameters-cli.md) 命令，以顯示伺服器任何特定參數的詳細數據。

## 停用 適用於 MySQL 的 Azure 資料庫 - Wordpress 整合的彈性伺服器 SSL 連線參數

變更伺服器參數值：

您也可以修改特定伺服器參數的值，以更新 MySQL 伺服器引擎的基礎組態值。 若要更新伺服器參數，請使用 [az mysql flexible-server parameter set](../../mysql/flexible-server/how-to-configure-server-parameters-cli.md#modify-a-server-parameter-value) 命令。

```bash
az mysql flexible-server parameter set \
    -g $MY_RESOURCE_GROUP_NAME \
    -s $MY_MYSQL_DB_NAME \
    -n require_secure_transport -v "OFF" -o JSON
```

結果：

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

## 建立 Azure Linux 虛擬機

下列範例會建立名為 `$MY_VM_NAME` 的 VM，並建立 SSH 金鑰 (如果它們不存在於預設金鑰位置)。 此命令也會設定 `$MY_VM_USERNAME` 為系統管理員用戶名稱。

若要改善 Azure 中 Linux 虛擬機的安全性，您可以與 Azure Active Directory 驗證整合。 現在您可以使用 Azure AD 作為核心驗證平臺。 您也可以使用 Azure AD 和 OpenSSH 憑證型驗證，透過 SSH 連線到 Linux VM。 此功能可讓組織使用 Azure 角色型存取控制和條件式存取原則來管理 VM 的存取權。

使用 [az vm create](/cli/azure/vm#az-vm-create) 命令來建立 VM。

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

結果：

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

## 檢查 Azure Linux 虛擬機狀態

建立虛擬機器和支援資源需要幾分鐘的時間。 在 VM 上成功安裝擴充功能時，[成功] 的 provisioningState 值隨即出現。 VM 必須有執行 [中的 VM 代理程式](../extensions/agent-linux.md) 才能安裝擴充功能。

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
<!-- expected_similarity=0.3 -->
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


<!--
## Export the SSH configuration for use with SSH clients that support OpenSSH
Login to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:
```bash
az ssh config --file ~/.ssh/azure-config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

## 在 Azure 中啟用 Linux 虛擬機的 Azure AD 登入

下列會安裝擴充功能，以啟用Linux VM的 Azure AD 登入。 VM 擴充功能是小型應用程式，可在 Azure 虛擬機上提供部署後設定和自動化工作。

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME -o JSON
```

結果：

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

## 檢查並流覽您的 WordPress 網站

[WordPress](https://www.wordpress.org) 是一種 開放原始碼 內容管理系統（CMS），由超過 40% 的網站、部落格和其他應用程式使用。 WordPress 可以在幾個不同的 Azure 服務上執行：[AKS](../../mysql/flexible-server/tutorial-deploy-wordpress-on-aks.md)、虛擬機器 和 App Service。 如需 Azure 上 WordPress 選項的完整清單，請參閱 [Azure Marketplace](https://azuremarketplace.microsoft.com/marketplace/apps?page=1&search=wordpress) 上的 WordPress。

此 WordPress 設定只適用於概念證明。 若要在生產環境中使用建議的安全性設定安裝最新的 WordPress，請參閱 [WordPress 文件](https://codex.wordpress.org/Main_Page)。

藉由捲曲應用程式 URL 來驗證應用程式是否正在執行：

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

結果：

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