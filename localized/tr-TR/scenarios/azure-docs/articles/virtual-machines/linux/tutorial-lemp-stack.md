---
title: Öğretici - VM'de WordPress kullanarak LEMP yığını dağıtma
description: 'Bu öğreticide, Azure''da bir Linux sanal makinesine LEMP yığınını ve WordPress''i yüklemeyi öğreneceksiniz.'
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

# Öğretici: Azure Linux VM'sinde LEMP yığını yükleme

**Şunlar için geçerlidir:** :heavy_check_mark: Linux VM'leri

[![Azure’a dağıtın](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateLinuxVMLAMP)

Bu makalede, Azure'da Ubuntu Linux VM'sinde NGINX web sunucusu, Azure MySQL Esnek Sunucusu ve PHP (LEMP yığını) dağıtma adımları anlatılmaktadır. LEMP sunucusunu çalışır halde görmek için, isteğe bağlı olarak bir WordPress sitesi yükleyip yapılandırabilirsiniz. Bu öğreticide şunların nasıl yapıldığını öğrenirsiniz:

> [!div class="checklist"]
>
> * Ubuntu sanal makinesi oluşturma
> * Web trafiği için 80 ve 443 bağlantı noktalarını açma
> * NGINX, Azure Esnek MySQL Sunucusu ve PHP Yükleme ve Güvenliğini Sağlama
> * Yükleme ve yapılandırmayı doğrulama
> * WordPress'i yükleme Bu kurulum hızlı testler veya kavram kanıtı içindir. Bir üretim ortamına yönelik öneriler de dahil olmak üzere LEMP yığını hakkında daha fazla bilgi için Ubuntu belgelerine [bakın](https://help.ubuntu.com/community/ApacheMySQLPHP).

Bu öğreticide Azure Cloud Shell[ içindeki ](../../cloud-shell/overview.md)CLI sürekli olarak en son sürüme güncelleştirilmektedir. Cloud Shell'i açmak için herhangi bir kod bloğunun üst kısmından Deneyin'i** seçin**.

CLI'yi yerel olarak yükleyip kullanmayı seçerseniz, bu öğretici için Azure CLI 2.0.30 veya sonraki bir sürümünü kullanmanız gerekir. komutunu çalıştırarak `az --version` sürümü bulun. Yüklemeniz veya yükseltmeniz gerekirse, bkz. [Azure CLI yükleme]( /cli/azure/install-azure-cli).

## Değişken bildirimi

öncelikle LEMP iş yükünün yapılandırmasına yardımcı olacak birkaç değişken tanımlamamız gerekir.

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

## Kaynak grubu oluşturma

[az group create](/cli/azure/group#az-group-create) komutuyla bir kaynak grubu oluşturun. Azure kaynak grubu, Azure kaynaklarının dağıtıldığı ve yönetildiği bir mantıksal kapsayıcıdır.
Aşağıdaki örnek `eastus` konumunda `$MY_RESOURCE_GROUP_NAME` adlı bir kaynak grubu oluşturur.

```bash
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION -o JSON
```

Sonuçlar:

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

## LEMP ağını ayarlama

## Azure Sanal Ağı oluşturun

Sanal ağ, Azure'daki özel ağlar için temel yapı taşıdır. Azure Sanal Ağ, VM'ler gibi Azure kaynaklarının birbirleriyle ve İnternet ile güvenli bir şekilde iletişim kurmasını sağlar.
Kaynak grubunda adlı `$MY_SN_NAME` `$MY_RESOURCE_GROUP_NAME` alt ağ ile adlı `$MY_VNET_NAME` bir sanal ağ oluşturmak için az network vnet create[ komutunu kullanın](/cli/azure/network/vnet#az-network-vnet-create).

```bash
az network vnet create \
    --name $MY_VNET_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefixes $MY_SN_PREFIX -o JSON
```

Sonuçlar:

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

## Azure Genel IP'si oluşturma

içinde adlı `$MY_RESOURCE_GROUP_NAME``MY_PUBLIC_IP_NAME` standart bir alanlar arası yedekli genel IPv4 adresi oluşturmak için az network public-ip create[ komutunu kullanın](/cli/azure/network/public-ip#az-network-public-ip-create).

>[!NOTE]
>Bölgeler için aşağıdaki seçenekler yalnızca Kullanılabilirlik Alanları[ olan ](../../reliability/availability-zones-service-support.md)bölgelerde geçerli seçimlerdir.
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

Sonuçlar:

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

## Azure Ağ Güvenlik Grubu oluşturma

Ağ güvenlik gruplarındaki güvenlik kuralları, sanal ağ alt ağlarında ve ağ arabirimlerinde içeri ve dışarı akabilecek ağ trafiği türünü filtrelemenize olanak tanır. Ağ güvenlik grupları hakkında daha fazla bilgi edinmek için bkz [. Ağ güvenlik grubuna genel bakış](../../virtual-network/network-security-groups-overview.md).

```bash
az network nsg create \
    --name $MY_NSG_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION -o JSON
```

Sonuçlar:

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

## Azure Ağ Güvenlik Grubu kuralları oluşturma

SSH için 22 numaralı bağlantı noktasında ve HTTP ve HTTPS için 80, 443 numaralı bağlantı noktalarında sanal makineye bağlantılara izin veren bir kural oluşturun. Giden bağlantılar için tüm bağlantı noktalarına izin vermek için ek bir kural oluşturulur. Ağ güvenlik grubu kuralı oluşturmak için az network nsg rule create[ komutunu kullanın](/cli/azure/network/nsg/rule#az-network-nsg-rule-create).

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

Sonuçlar:

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

## Azure Ağ Arabirimi oluşturma

[Az network nic create](/cli/azure/network/nic#az-network-nic-create) komutunu kullanarak sanal makine için ağ arabirimi oluşturun. Genel IP adresleri ve daha önce oluşturulan NSG, NIC ile ilişkilendirilir. Ağ arabirimi, daha önce oluşturduğunuz sanal ağa eklenir.

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

Sonuçlar:

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
## Cloud-init genel bakış

Cloud-init, Linux VM’sini ilk kez önyüklendiğinde özelleştirmeyi sağlayan, sık kullanılan bir yaklaşımdır. cloud-init’i paket yükleme, dosyalara yazma ve kullanıcılar ile güvenliği yapılandırma işlemleri için kullanabilirsiniz. Cloud-init ilk önyükleme işlemi sırasında çalıştırıldığından, yapılandırmanıza uygulamak için başka bir adım veya gerekli aracı yoktur.

Cloud-init, dağıtımlar arasında da çalışır. Örneğin, bir paket yüklemek için apt-get install veya yum install kullanmazsınız. Bunun yerine, yüklenecek paketlerin listesini tanımlayabilirsiniz. Cloud-init, seçtiğiniz dağıtım için yerel paket yönetim aracını otomatik olarak kullanır.

İş ortaklarımızla birlikte çalışarak cloud-init'i dahil ediyoruz ve Azure'a sundukları görüntülerde çalışıyoruz. Her dağıtım için cloud-init desteği hakkında ayrıntılı bilgi için bkz [. Azure'da](./using-cloud-init.md) VM'ler için cloud-init desteği.

### cloud-init yapılandırma dosyası oluşturma

Cloud-init'i çalışırken görmek için, BIR LEMP yığını yükleyen ve SSL sertifikasıyla güvenliği sağlanan basit bir Wordpress uygulaması çalıştıran bir VM oluşturun. Aşağıdaki cloud-init yapılandırması gerekli paketleri yükler, Wordpress web sitesini oluşturur, ardından web sitesini başlatır ve başlatır.

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

## Azure MySQL Esnek Sunucusu için Azure Özel DNS Bölgesi oluşturma

Azure Özel DNS Bölgesi tümleştirmesi, geçerli sanal ağ içindeki özel DNS'yi veya özel DNS Bölgesinin bağlı olduğu bölge içinde eşlenmiş herhangi bir sanal ağı çözümlemenize olanak tanır. Özel DNS bölgesini oluşturmak için az network private-dns zone create[ komutunu kullanın](/cli/azure/network/private-dns/zone#az-network-private-dns-zone-create).

```bash
az network private-dns zone create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_DNS_LABEL.private.mysql.database.azure.com -o JSON
```

Sonuçlar:

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

## MySQL için Azure Veritabanı Oluşturma - Esnek Sunucu

MySQL için Azure Veritabanı - Esnek Sunucu, bulutta yüksek oranda kullanılabilir MySQL sunucularını çalıştırmak, yönetmek ve ölçeklendirmek için kullanabileceğiniz bir yönetilen hizmettir. az mysql flexible-server create komutuyla [esnek bir sunucu oluşturun](../../mysql/flexible-server/quickstart-create-server-cli.md#create-an-azure-database-for-mysql-flexible-server) . Bir sunucu birden çok veritabanı içerebilir. Aşağıdaki komut, Azure CLI'nızın yerel ortamındaki hizmet varsayılanlarını ve değişken değerlerini kullanarak bir sunucu oluşturur:

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

Sonuçlar:

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

Oluşturulan sunucu aşağıdaki özniteliklere sahiptir:

* Sunucu adı, yönetici kullanıcı adı, yönetici parolası, kaynak grubu adı, konum, bulut kabuğunun yerel bağlam ortamında zaten belirtilmiştir. Bunlar, kaynak grubunuzla ve diğer Azure bileşenleriyle aynı konumda oluşturulur.
* Kalan sunucu yapılandırmaları için hizmet varsayılanları: işlem katmanı (Serileştirilebilir), işlem boyutu/SKU (Standard_B2s), yedekleme saklama süresi (7 gün) ve MySQL sürümü (8.0.21)
* Varsayılan bağlantı yöntemi, bağlı bir sanal ağ ve otomatik olarak oluşturulan bir alt ağ ile Özel erişim (VNet Tümleştirmesi) yöntemidir.

> [!NOTE]
> Sunucu oluşturulduktan sonra bağlantı yöntemi değiştirilemez. Örneğin, oluşturma sırasında seçtiyseniz `Private access (VNet Integration)` , oluşturma sonrasında olarak `Public access (allowed IP addresses)` değiştiremezsiniz. Sanal Ağ Tümleştirmesi'ni kullanarak sunucunuza güvenli bir şekilde erişmek için Özel erişimli bir sunucu oluşturmanızı kesinlikle öneririz. Kavramlar makalesinde [](../../mysql/flexible-server/concepts-networking-vnet.md)Özel erişim hakkında daha fazla bilgi edinin.
Varsayılan değerleri değiştirmek isterseniz, yapılandırılabilir CLI parametrelerinin tam listesi için Azure CLI [başvuru belgelerine bakın](../../mysql/flexible-server/quickstart-create-server-cli.md) .

## MySQL için Azure Veritabanı - Esnek Sunucu durumunu denetleyin

MySQL için Azure Veritabanı Esnek Sunucu ve destekleyici kaynakların oluşturulması birkaç dakika sürer.

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

## MySQL için Azure Veritabanı - Esnek Sunucuda sunucu parametrelerini yapılandırma

Sunucu parametrelerini kullanarak MySQL için Azure Veritabanı - Esnek Sunucu yapılandırmasını yönetebilirsiniz. Sunucu parametreleri, sunucuyu oluşturduğunuzda varsayılan ve önerilen değerle yapılandırılır.

Sunucu parametresi ayrıntılarını göster:

Sunucunun [belirli bir parametresi hakkındaki ayrıntıları göstermek için az mysql flexible-server parameter show](../../mysql/flexible-server/how-to-configure-server-parameters-cli.md) komutunu çalıştırın.

## wordpress tümleştirmesi için MySQL için Azure Veritabanı - Esnek Sunucu SSL bağlantı parametresini devre dışı bırakma

Sunucu parametresi değerini değiştirme:

Ayrıca, MySQL sunucu altyapısı için temel yapılandırma değerini güncelleştiren belirli bir sunucu parametresinin değerini de değiştirebilirsiniz. Sunucu parametresini güncelleştirmek için az mysql flexible-server parameter set[ komutunu kullanın](../../mysql/flexible-server/how-to-configure-server-parameters-cli.md#modify-a-server-parameter-value).

```bash
az mysql flexible-server parameter set \
    -g $MY_RESOURCE_GROUP_NAME \
    -s $MY_MYSQL_DB_NAME \
    -n require_secure_transport -v "OFF" -o JSON
```

Sonuçlar:

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

## Azure Linux Sanal Makinesi oluşturma

Aşağıdaki örnek adlı `$MY_VM_NAME` bir VM oluşturur ve varsayılan anahtar konumunda yoksa SSH anahtarları oluşturur. Komut, yönetici kullanıcı adı olarak da ayarlanır `$MY_VM_USERNAME` .

Azure'da Linux sanal makinelerinin güvenliğini geliştirmek için Azure Active Directory kimlik doğrulamasıyla tümleştirebilirsiniz. Artık Azure AD'i çekirdek kimlik doğrulama platformu olarak kullanabilirsiniz. Ayrıca Azure AD ve OpenSSH sertifika tabanlı kimlik doğrulamasını kullanarak Linux VM'ye SSH de ekleyebilirsiniz. Bu işlevsellik, kuruluşların Azure rol tabanlı erişim denetimi ve Koşullu Erişim ilkeleriyle VM'lere erişimi yönetmesine olanak tanır.

[az vm create](/cli/azure/vm#az-vm-create) komutuyla bir sanal makine oluşturun.

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

Sonuçlar:

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

## Azure Linux Sanal Makinesi durumunu denetleme

VM’yi ve destekleyici kaynakları oluşturmak birkaç dakika sürer. Uzantı VM'ye başarıyla yüklendiğinde Succeeded değerinin provisioningState değeri görüntülenir. Uzantıyı yüklemek için VM'nin çalışan [bir VM aracısı](../extensions/agent-linux.md) olmalıdır.

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

## Azure'da Linux Sanal Makinesi için Azure AD oturum açma özelliğini etkinleştirme

Aşağıda, Linux VM için Azure AD oturum açma özelliğini etkinleştirmek için uzantı yüklenir. VM uzantıları, Azure sanal makinelerinde dağıtım sonrası yapılandırma ve otomasyon görevleri sağlayan küçük uygulamalardır.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME -o JSON
```

Sonuçlar:

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

## WordPress web sitenizi kontrol edin ve göz atın

[WordPress](https://www.wordpress.org), web sitelerinin, blogların ve diğer uygulamaların oluşturulması için web'in %40'ının üzerinde kullanılan bir açık kaynak içerik yönetim sistemidir (CMS). WordPress birkaç farklı Azure hizmetinde çalıştırılabilir: [AKS](../../mysql/flexible-server/tutorial-deploy-wordpress-on-aks.md), Sanal Makineler ve App Service. Azure'da WordPress seçeneklerinin tam listesi için bkz[. Azure Market](https://azuremarketplace.microsoft.com/marketplace/apps?page=1&search=wordpress) üzerinde WordPress.

Bu WordPress kurulumu yalnızca kavram kanıtı amaçlıdır. En güncel WordPress sürümünü önerilen güvenlik ayarlarıyla üretim ortamına yüklemek için bkz. [WordPress belgeleri](https://codex.wordpress.org/Main_Page).

Uygulama URL'sini kıvrarak uygulamanın çalıştığını doğrulayın:

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

Sonuçlar:

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
