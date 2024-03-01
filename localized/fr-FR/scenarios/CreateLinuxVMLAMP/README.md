---
title: Installez une pile LEMP sur Azure
description: Ce tutoriel montre comment installer une pile LEMP sur Azure.
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Installez une pile LEMP sur Azure

[![Déployer dans Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/?Microsoft_Azure_CloudNative_clientoptimizations=false&feature.canmodifyextensions=true#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateLinuxVMLAMP)


Cet article vous guide à travers le déploiement d’un serveur web NGINX, de celui du serveur flexible Azure MySQL et de PHP (la pile LEMP) sur une machine virtuelle Ubuntu Linux dans Azure. Pour voir le serveur LEMP fonctionner, vous pouvez éventuellement installer et configurer un site WordPress. Ce didacticiel vous montre comment effectuer les opérations suivantes :

> [!div class="checklist"]

> * Créer une machine virtuelle Linux Ubuntu
> * Ouvrez les port 80 et 443 pour le trafic web
> * Installer et sécuriser NGINX, Azure Flexible MySQL Server et PHP
> * Vérifier l’installation et la configuration
> * Installer WordPress

## Déclaration de variable

Nous commencerons par définir quelques variables qui nous aideront à configurer la charge de travail LEMP.

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

## Créer un groupe de ressources

Créez un groupe de ressources avec la commande [az group create](https://learn.microsoft.com/cli/azure/group#az-group-create). Un groupe de ressources Azure est un conteneur logique dans lequel les ressources Azure sont déployées et gérées.
L’exemple suivant crée un groupe de ressources nommé `$MY_RESOURCE_GROUP_NAME` à l’emplacement `eastus`.

```bash
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION -o JSON
```

Résultats :

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

## Configurer la mise en réseau LEMP

## Créer un réseau virtuel Azure

Un réseau virtuel est l’élément de construction fondamental pour les réseaux privés dans Azure. Le réseau virtuel Microsoft Azure permet à des ressources Azure, comme des machines virtuelles, de communiquer de manière sécurisée entre elles et sur Internet.
Utilisez la commande [az network vnet create](https://learn.microsoft.com/cli/azure/network/vnet#az-network-vnet-create) pour créer un réseau virtuel nommé `$MY_VNET_NAME` avec un sous-réseau nommé `$MY_SN_NAME` au sein du groupe de ressources `$MY_RESOURCE_GROUP_NAME`.

```bash
az network vnet create \
    --name $MY_VNET_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefixes $MY_SN_PREFIX -o JSON
```

Résultats :

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

## Créer une IP publique Azure

Utilisez [az network public-ip create](https://learn.microsoft.com/cli/azure/network/public-ip#az-network-public-ip-create) pour créer une adresse IPv4 publique redondante interzone standard, nommée `MY_PUBLIC_IP_NAME` dans `$MY_RESOURCE_GROUP_NAME`.

>[!NOTE]
>Les sélections des options de zone ci-dessous sont valides uniquement dans les régions pourvues de [Zones de disponibilité Azure](https://learn.microsoft.com/azure/reliability/availability-zones-service-support).

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

Résultats :

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

## Créer un groupe de sécurité réseau Azure

Les règles de sécurité dans les groupes de sécurité réseau permettent de filtrer le type de trafic réseau qui peut circuler vers et depuis les interfaces réseau et les sous-réseaux de réseau virtuel. Pour en savoir plus sur les groupes de sécurité réseau, consultez [Vue d’ensemble du groupe de sécurité réseau](https://learn.microsoft.com/azure/virtual-network/network-security-groups-overview).

```bash
az network nsg create \
    --name $MY_NSG_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION -o JSON
```

Résultats :

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

## Créer des règles pour le groupe de sécurité réseau Azure

Vous allez créer une règle pour autoriser les connexions à la machine virtuelle sur le port 22 pour le protocole SSH et les ports 80 et 443 pour HTTP et HTTPS. Une règle supplémentaire est créée pour autoriser tous les ports pour les connexions sortantes. Utilisez [az network nsg rule create](https://learn.microsoft.com/cli/azure/network/nsg/rule#az-network-nsg-rule-create) pour créer une règle de groupe de sécurité réseau.

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

Résultats :

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

## Créer une interface réseau Azure

Vous allez utiliser la commande [az network nic create](https://learn.microsoft.com/cli/azure/network/nic#az-network-nic-create) pour créer l’interface réseau de la machine virtuelle. Les adresses IP publiques et le groupe de sécurité réseau créés précédemment sont associés à la carte d’interface réseau. L’interface réseau est jointe au réseau virtuel que vous avez créé précédemment.

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

Résultats :

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

## Présentation de cloud-init

Cloud-init est une méthode largement utilisée pour personnaliser une machine virtuelle Linux lors de son premier démarrage. Vous pouvez utiliser cloud-init pour installer des packages et écrire des fichiers, ou encore pour configurer des utilisateurs ou des paramètres de sécurité. Comme cloud-init s’exécute pendant le processus de démarrage initial, aucune autre étape ni aucun agent ne sont nécessaires pour appliquer votre configuration.

Cloud-init fonctionne aussi sur les différentes distributions. Par exemple, vous n’utilisez pas apt-get install ou yum install pour installer un package. Au lieu de cela, vous pouvez définir une liste des packages à installer, après quoi cloud-init se charge d’utiliser automatiquement l’outil de gestion de package natif correspondant à la distribution que vous sélectionnez.

Nous collaborons avec nos partenaires pour que cloud-init soit inclus et fonctionne dans les images qu’ils fournissent à Azure. Pour plus d’informations sur la prise en charge de cloud-init pour chaque distribution, consultez [Prise en charge de cloud-init pour les machines virtuelles dans Azure](https://learn.microsoft.com/azure/virtual-machines/linux/using-cloud-init).

### Créer un fichier de configuration cloud-init

Pour voir cloud-init en action, créez une VM qui installe une pile LEMP et exécute une simple application Wordpress sécurisée par un certificat SSL. La configuration cloud-init suivante installe les packages, crée une le site web Wordpress, puis initialise et démarre le site web.

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

## Créer une zone DNS privée Azure pour le serveur flexible Azure MySQL

L’intégration de zones DNS privées Azure permet de résoudre le DNS privé au sein du réseau virtuel actuel ou de tout réseau virtuel appairé dans la région où la zone DNS privée est liée. Vous utiliserez la commande [az network private-dns create](https://learn.microsoft.com/cli/azure/network/private-dns/zone#az-network-private-dns-zone-create) pour créer la zone DNS privée.

```bash
az network private-dns zone create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_DNS_LABEL.private.mysql.database.azure.com -o JSON
```

Résultats :

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

## Créer un serveur flexible Azure Database pour MySQL

Azure Database pour MySQL - Serveur flexible est un service managé qui vous permet d’exécuter, de gérer et de mettre à l’échelle des serveurs MySQL hautement disponibles dans le cloud. Créez un serveur flexible avec la commande [az mysql flexible-server create](https://learn.microsoft.com/cli/azure/mysql/flexible-server#az-mysql-flexible-server-create). Un serveur peut contenir plusieurs bases de données. La commande suivante crée un serveur en utilisant les valeurs par défaut du service et les valeurs variables issues de l’environnement local de votre interface Azure CLI :

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

Résultats :

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

Le serveur créé possède les attributs suivants :

* Le nom du serveur, le nom d'utilisateur de l'administrateur, le mot de passe de l'administrateur, le nom du groupe de ressources et l'emplacement sont déjà spécifiés dans l'environnement contextuel local du cloud shell et seront créés au même endroit que votre groupe de ressources et les autres composants Azure.
* Valeurs par défaut du service pour les configurations restantes : Niveau de calcul (burstable), Taille de calcul/SKU (Standard_B2s), Période de rétention des sauvegardes (7 jours) et Version de MySQL (8.0.21)
* La méthode de connectivité par défaut est Accès privé (intégration au réseau virtuel), avec un réseau virtuel lié et un sous-réseau généré automatiquement.

> [!NOTE]
> Une fois le serveur créé, la méthode de connectivité ne peut pas être modifiée. Par exemple, si vous avez sélectionné `Private access (VNet Integration)` pendant la création, vous ne pouvez pas passer à `Public access (allowed IP addresses)` après la création. Nous vous recommandons vivement de sélectionner l'Accès privé lors de la création d'un serveur afin de pouvoir y accéder en toute sécurité à l'aide de l'intégration au réseau virtuel. Pour en savoir plus sur l'accès privé, consultez l'[article consacré aux concepts](https://learn.microsoft.com/azure/mysql/flexible-server/concepts-networking-vnet).

Si vous souhaitez changer des valeurs par défaut, reportez-vous à la [documentation de référence](https://learn.microsoft.com/cli/azure//mysql/flexible-server) d’Azure CLI pour obtenir la liste complète des paramètres CLI configurables.

## Vérifiez Azure Database pour MySQL : état du serveur flexible

La création de Azure Database pour MySQL : serveur flexibile et des ressources correspondantes ne prend que quelques minutes.

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

## Configurer les paramètres de serveur dans Azure Database pour MySQL : serveur flexibile

Vous pouvez gérer la configuration d’Azure Database pour MySQL - Serveur flexible à l’aide des paramètres de serveur. Les paramètres de serveur sont configurés avec la valeur par défaut et la valeur recommandée lors de la création du serveur.

Afficher les détails d’un paramètre de serveur Pour afficher les détails d’un paramètre particulier pour un serveur, exécutez la commande [az mysql flexible-server parameter show](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter).

### Désactiver Azure Database pour MySQL : paramètre de connexion SSL du serveur flexible pour l'intégration de Wordpress

Modifier la valeur d’un paramètre de serveur Vous pouvez également modifier la valeur d’un paramètre de serveur, ce qui a pour effet de mettre à jour la valeur de configuration sous-jacente du moteur du serveur MySQL. Pour mettre à jour le paramètre de serveur, utilisez la commande [az mysql flexible-server parameter set](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set).

```bash
az mysql flexible-server parameter set \
    -g $MY_RESOURCE_GROUP_NAME \
    -s $MY_MYSQL_DB_NAME \
    -n require_secure_transport -v "OFF" -o JSON
```

Résultats :

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

## Créer une machine virtuelle Azure Linux

L’exemple suivant crée une machine virtuelle nommée `$MY_VM_NAME` et crée des clés SSH si elles n’existent pas déjà dans un emplacement de clé par défaut. La commande définit aussi `$MY_VM_USERNAME` comme nom d’utilisateur administrateur.
Pour améliorer la sécurité des machines virtuelles Linux dans Azure, vous pouvez intégrer l’authentification Azure Active Directory. Vous pouvez désormais utiliser Azure AD comme plateforme d’authentification principale et autorité de certification pour établir une connexion SSH à une machine virtuelle Linux à l’aide d’Azure AD et de l’authentification par certificat OpenSSH. Cette fonctionnalité permet aux organisations de gérer l’accès aux machines virtuelles avec le contrôle d’accès en fonction du rôle Azure et les stratégies d’accès conditionnel.

Créez une machine virtuelle avec la commande [az vm create](https://learn.microsoft.com/cli/azure/vm#az-vm-create).

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

Résultats :

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

## Vérification de l’état de la machine virtuelle Azure Linux

La création de la machine virtuelle et des ressources de support ne prend que quelques minutes. La valeur provisioningState défini sur Succeeded apparaît lorsque l’extension est installée sur la machine virtuelle. La machine virtuelle doit avoir un [agent de machine virtuelle](https://learn.microsoft.com/azure/virtual-machines/extensions/agent-linux) en cours d’exécution pour installer l’extension.

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

## Activer la connexion Azure AD pour une machine virtuelle Linux dans Azure

L’exemple suivant installe l’extension pour permettre la connexion Azure AD pour une machine virtuelle Linux. Les extensions de machine virtuelle sont de petites applications permettant d’exécuter des tâches de configuration et d’automatisation post-déploiement sur des machines virtuelles Azure.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME -o JSON
```

Résultats :

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

## Vérifier et parcourir votre site web WordPress

[WordPress](https://www.wordpress.org) est un système de gestion de contenu (CMS) open source utilisé par plus de 40 % du Web pour créer des sites web, des blogs et d’autres applications. WordPress peut être exécuté sur plusieurs services Azure différents : [AKS](https://learn.microsoft.com/azure/mysql/flexible-server/tutorial-deploy-wordpress-on-aks), des machines virtuelles et App Service. Pour obtenir la liste complète des options WordPress sur Azure, consultez [WordPress sur la Place de marché Azure](https://azuremarketplace.microsoft.com/marketplace/apps?page=1&search=wordpress).

Ce programme d’installation de WordPress est destiné uniquement à la preuve de concept. Pour installer la dernière version de WordPress en production avec les paramètres de sécurité recommandés, consultez la [documentation de WordPress](https://codex.wordpress.org/Main_Page).

Vérifiez que l’application est en cours d’exécution en affichant l’URL de l’application :

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

Résultats :

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
