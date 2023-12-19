---
title: Skapa en NGINX-webbserver som skyddas via HTTPS
description: Den här självstudien visar hur du skapar en NGINX-webbserver som skyddas via HTTPS.
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Skapa en NGINX-webbserver som skyddas via HTTPS

För att skydda webbservrar, TLS (Transport Layer Security), tidigare kallat Secure Sockets Layer (SSL), kan certifikat användas för att kryptera webbtrafik. Dessa TLS/SSL-certifikat kan lagras i Azure Key Vault och tillåta säkra distributioner av certifikat till virtuella Linux-datorer i Azure. I den här självstudiekursen får du lära du dig att:

> [!div class="checklist"]

> * Konfigurera och skydda Azure-nätverk
> * Skapa ett Azure Key Vault
> * Generera eller ladda upp ett certifikat till Key Vault
> * Skapa en virtuell dator och installera NGINX-webbservern
> * Mata in certifikatet i den virtuella datorn och konfigurera NGINX med en TLS-bindning

Om du väljer att installera och använda CLI lokalt kräver den här självstudien att du kör Azure CLI version 2.0.30 eller senare. Kör `az --version` för att hitta versionen. Om du behöver installera eller uppgradera kan du läsa [Installera Azure CLI]( https://learn.microsoft.com//cli/azure/install-azure-cli ).

## Variabeldeklaration

Lista över alla miljövariabler som du behöver för att köra den här självstudien:

```bash
export NETWORK_PREFIX="$(($RANDOM % 254 + 1))"
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myResourceGroup$RANDOM_ID"
export MY_KEY_VAULT="mykeyvault$RANDOM_ID"
export MY_CERT_NAME="nginxcert$RANDOM_ID"
export REGION="eastus"
export MY_VM_NAME="myVMName$RANDOM_ID"
export MY_VM_ID_NAME="myVMIDName$RANDOM_ID"
export MY_VM_IMAGE='Ubuntu2204'
export MY_VM_USERNAME="azureuser"
export MY_VM_SIZE='Standard_DS2_v2'
export MY_VNET_NAME="myVNet$RANDOM_ID"
export MY_VM_NIC_NAME="myVMNicName$RANDOM_ID"
export MY_NSG_SSH_RULE="Allow-Access$RANDOM_ID"
export MY_VM_NIC_NAME="myVMNicName$RANDOM_ID"
export MY_VNET_PREFIX="10.$NETWORK_PREFIX.0.0/16"
export MY_SN_NAME="mySN$RANDOM_ID"
export MY_SN_PREFIX="10.$NETWORK_PREFIX.0.0/24"
export MY_PUBLIC_IP_NAME="myPublicIP$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
export MY_NSG_NAME="myNSGName$RANDOM_ID"
export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
```

## Skapa en resursgrupp

Innan du kan skapa en säker virtuell Linux-dator skapar du en resursgrupp med az group create. I följande exempel skapas en resursgrupp som är lika med innehållet i variabeln *MY_RESOURCE_GROUP_NAME* på den plats som anges av variabelinnehållsREGIONEN**:

```bash
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION -o JSON
```

Resultat:

<!-- expected_similarity=0.3 -->
```JSON
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myResourceGroupb1404f",
  "location": "eastus",
  "managedBy": null,
  "name": "myResourceGroupb1404f",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Konfigurera vm-nätverk

Använd az network vnet create för att skapa ett virtuellt nätverk med namnet *$MY_VNET_NAME* med ett undernät med namnet *$MY_SN_NAME*i *resursgruppen $MY_RESOURCE_GROUP_NAME*.

```bash
az network vnet create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_VNET_NAME \
    --location $REGION \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefix $MY_SN_PREFIX -o JSON
```

Resultat:

<!-- expected_similarity=0.3 -->
```JSON
{
  "newVNet": {
    "addressSpace": {
      "addressPrefixes": [
        "10.168.0.0/16"
      ]
    },
    "bgpCommunities": null,
    "ddosProtectionPlan": null,
    "dhcpOptions": {
      "dnsServers": []
    },
    "enableDdosProtection": false,
    "enableVmProtection": null,
    "encryption": null,
    "extendedLocation": null,
    "flowTimeoutInMinutes": null,
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myResourceGroupb1404f/providers/Microsoft.Network/virtualNetworks/myVNetb1404f",
    "ipAllocations": null,
    "location": "eastus",
    "name": "myVNetb1404f",
    "provisioningState": "Succeeded",
    "resourceGroup": "myResourceGroupb1404f",
    "subnets": [
      {
        "addressPrefix": "10.168.0.0/24",
        "addressPrefixes": null,
        "applicationGatewayIpConfigurations": null,
        "delegations": [],
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myResourceGroupb1404f/providers/Microsoft.Network/virtualNetworks/myVNetb1404f/subnets/mySNb1404f",
        "ipAllocations": null,
        "ipConfigurationProfiles": null,
        "ipConfigurations": null,
        "name": "mySNb1404f",
        "natGateway": null,
        "networkSecurityGroup": null,
        "privateEndpointNetworkPolicies": "Disabled",
        "privateEndpoints": null,
        "privateLinkServiceNetworkPolicies": "Enabled",
        "provisioningState": "Succeeded",
        "purpose": null,
        "resourceGroup": "myResourceGroupb1404f",
        "resourceNavigationLinks": null,
        "routeTable": null,
        "serviceAssociationLinks": null,
        "serviceEndpointPolicies": null,
        "serviceEndpoints": null,
        "type": "Microsoft.Network/virtualNetworks/subnets"
      }
    ],
    "tags": {},
    "type": "Microsoft.Network/virtualNetworks",
    "virtualNetworkPeerings": []
  }
}
```

Använd az network public-ip create för att skapa en offentlig IPv4-standardadress med namnet *$MY_PUBLIC_IP_NAME* i *$MY_RESOURCE_GROUP_NAME*.

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

Resultat:

<!-- expected_similarity=0.3 -->
```JSON
{
  "publicIp": {
    "ddosSettings": null,
    "deleteOption": null,
    "dnsSettings": {
      "domainNameLabel": "mydnslabelb1404f",
      "fqdn": "mydnslabelb1404f.eastus.cloudapp.azure.com",
      "reverseFqdn": null
    },
    "extendedLocation": null,
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myResourceGroupb1404f/providers/Microsoft.Network/publicIPAddresses/myPublicIPb1404f",
    "idleTimeoutInMinutes": 4,
    "ipAddress": "20.88.178.210",
    "ipConfiguration": null,
    "ipTags": [],
    "linkedPublicIpAddress": null,
    "location": "eastus",
    "migrationPhase": null,
    "name": "myPublicIPb1404f",
    "natGateway": null,
    "provisioningState": "Succeeded",
    "publicIpAddressVersion": "IPv4",
    "publicIpAllocationMethod": "Static",
    "publicIpPrefix": null,
    "resourceGroup": "myResourceGroupb1404f",
    "servicePublicIpAddress": null,
    "sku": {
      "name": "Standard",
      "tier": "Regional"
    },
    "tags": null,
    "type": "Microsoft.Network/publicIPAddresses",
    "zones": [
      "1",
      "2",
      "3"
    ]
  }
}
```

Med säkerhetsregler i nätverkssäkerhetsgrupper kan du filtrera vilken typ av nätverkstrafik som kan flöda in i och ut ur virtuella nätverk, undernät och nätverksgränssnitt. Mer information om nätverkssäkerhetsgrupper finns i [Översikt över](https://learn.microsoft.com/azure/virtual-network/network-security-groups-overview) nätverkssäkerhetsgrupp.

```bash
az network nsg create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_NSG_NAME \
    --location $REGION -o JSON
```

Resultat:

<!-- expected_similarity=0.3 -->
```JSON
{
  "NewNSG": {
    "defaultSecurityRules": [
      {
        "access": "Allow",
        "description": "Allow inbound traffic from all VMs in VNET",
        "destinationAddressPrefix": "VirtualNetwork",
        "destinationAddressPrefixes": [],
        "destinationPortRange": "*",
        "destinationPortRanges": [],
        "direction": "Inbound",
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myResourceGroupb1404f/providers/Microsoft.Network/networkSecurityGroups/myNSGNameb1404f/defaultSecurityRules/AllowVnetInBound",
        "name": "AllowVnetInBound",
        "priority": 65000,
        "protocol": "*",
        "provisioningState": "Succeeded",
        "resourceGroup": "myResourceGroupb1404f",
        "sourceAddressPrefix": "VirtualNetwork",
        "sourceAddressPrefixes": [],
        "sourcePortRange": "*",
        "sourcePortRanges": [],
        "type": "Microsoft.Network/networkSecurityGroups/defaultSecurityRules"
      }
    ],
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myResourceGroupb1404f/providers/Microsoft.Network/networkSecurityGroups/myNSGNameb1404f",
    "location": "eastus",
    "name": "myNSGNameb1404f",
    "provisioningState": "Succeeded",
    "resourceGroup": "myResourceGroupb1404f",
    "securityRules": [],
    "type": "Microsoft.Network/networkSecurityGroups"
  }
}
```

Öppna portarna 22 (SSH), 80 (HTTP) och 443 (HTTPS) för att tillåta SSH- och webbtrafik

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

Resultat:

<!-- expected_similarity=0.3 -->
```JSON
{
  "access": "Allow",
  "description": null,
  "destinationAddressPrefix": "*",
  "destinationAddressPrefixes": [],
  "destinationApplicationSecurityGroups": null,
  "destinationPortRange": null,
  "destinationPortRanges": [
    "22",
    "80",
    "443"
  ],
  "direction": "Inbound",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myResourceGroupb1404f/providers/Microsoft.Network/networkSecurityGroups/myNSGNameb1404f/securityRules/MY_NSG_SSH_RULE",
  "name": "MY_NSG_SSH_RULE",
  "priority": 100,
  "protocol": "Tcp",
  "provisioningState": "Succeeded",
  "resourceGroup": "myResourceGroupb1404f",
  "sourceAddressPrefix": "*",
  "sourceAddressPrefixes": [],
  "sourceApplicationSecurityGroups": null,
  "sourcePortRange": "*",
  "sourcePortRanges": [],
  "type": "Microsoft.Network/networkSecurityGroups/securityRules"
}
```

Och slutligen skapa nätverkskort (NIC):

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

Resultat:

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
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myResourceGroupb1404f/providers/Microsoft.Network/networkInterfaces/myVMNicNameb1404f",
    "ipConfigurations": [
      {
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myResourceGroupb1404f/providers/Microsoft.Network/networkInterfaces/myVMNicNameb1404f/ipConfigurations/ipconfig1",
        "name": "ipconfig1",
        "primary": true,
        "privateIPAddress": "10.168.0.4",
        "privateIPAddressVersion": "IPv4",
        "privateIPAllocationMethod": "Dynamic",
        "provisioningState": "Succeeded",
        "resourceGroup": "myResourceGroupb1404f",
        "subnet": {
          "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myResourceGroupb1404f/providers/Microsoft.Network/virtualNetworks/myVNetb1404f/subnets/mySNb1404f",
          "resourceGroup": "myResourceGroupb1404f"
        },
        "type": "Microsoft.Network/networkInterfaces/ipConfigurations"
      }
    ],
    "location": "eastus",
    "name": "myVMNicNameb1404f",
    "networkSecurityGroup": {
      "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myResourceGroupb1404f/providers/Microsoft.Network/networkSecurityGroups/myNSGNameb1404f",
      "resourceGroup": "myResourceGroupb1404f"
    },
    "nicType": "Standard",
    "provisioningState": "Succeeded",
    "resourceGroup": "myResourceGroupb1404f",
    "tapConfigurations": [],
    "type": "Microsoft.Network/networkInterfaces",
    "vnetEncryptionSupported": false
  }
}
```

## Generera ett certifikat och lagra det i Azure Key Vault

Azure Key Vault skyddar krypteringsnycklar och hemligheter, som certifikat och lösenord. Key Vault förenklar certifikathanteringen och låter dig behålla kontrollen över nycklar som kommer åt certifikaten. Du kan skapa ett självsignerat certifikat i Key Vault eller ladda upp ett befintligt, betrott certifikat som du redan äger. I den här självstudien ska vi skapa självsignerade certifikat i Key Vault och sedan mata in dessa certifikat i en virtuell dator som körs. Den här processen garanterar att de mest uppdaterade certifikaten är installerade på en webbserver under distributionen.

I följande exempel skapas ett Azure Key Vault med namnet *$MY_KEY_VAULT* i den valda regionen *$REGION* med en kvarhållningsprincip på 7 dagar. Det innebär att när en hemlighet, nyckel, certifikat eller nyckelvalv har tagits bort förblir den återställningsbar under en konfigurerbar period på 7 till 90 kalenderdagar.

```bash
az keyvault create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_KEY_VAULT \
    --location $REGION \
    --retention-days 7\
    --enabled-for-deployment true -o JSON
```

Resultat:

<!-- expected_similarity=0.3 -->
```JSON
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myResourceGroupb1404f/providers/Microsoft.KeyVault/vaults/myKeyVaultb1404f",
  "location": "eastus",
  "name": "myKeyVaultb1404f",
  "properties": {
    "accessPolicies": [
      {
        "applicationId": null,
        "permissions": {
          "certificates": [
            "all"
          ],
          "keys": [
            "all"
          ],
          "secrets": [
            "all"
          ],
          "storage": [
            "all"
          ]
        },
        "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
      }
    ],
    "createMode": null,
    "enablePurgeProtection": null,
    "enableRbacAuthorization": null,
    "enableSoftDelete": true,
    "enabledForDeployment": true,
    "enabledForDiskEncryption": null,
    "enabledForTemplateDeployment": null,
    "hsmPoolResourceId": null,
    "networkAcls": null,
    "privateEndpointConnections": null,
    "provisioningState": "Succeeded",
    "publicNetworkAccess": "Enabled",
    "sku": {
      "family": "A",
      "name": "standard"
    },
    "softDeleteRetentionInDays": 7,
    "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "vaultUri": "https://mykeyvaultb1404f.vault.azure.net/"
  },
  "resourceGroup": "myResourceGroupb1404f",
  "systemData": {
    "createdAt": "2023-09-18T12:25:55.208000+00:00",
    "createdBy": "example@microsoft.com",
    "createdByType": "User",
    "lastModifiedAt": "2023-09-18T12:25:55.208000+00:00",
    "lastModifiedBy": "example@microsoft.com",
    "lastModifiedByType": "User"
  },
  "tags": {},
  "type": "Microsoft.KeyVault/vaults"
}
```

## Skapa ett certifikat och lagra i Azure Key Vault

Nu ska vi generera ett självsignerat certifikat med az keyvault certificate create som använder standardprincipen för certifikat:

```bash
az keyvault certificate create \
    --vault-name $MY_KEY_VAULT \
    --name $MY_CERT_NAME \
    --policy "$(az keyvault certificate get-default-policy)" -o JSON
```

Resultat:

<!-- expected_similarity=0.3 -->
```JSON
{
  "cancellationRequested": false,
  "csr": "MIICr...",
  "error": null,
  "id": "https://mykeyvault67a7ba.vault.azure.net/certificates/nginxcert67a7ba/pending",
  "issuerParameters": {
    "certificateTransparency": null,
    "certificateType": null,
    "name": "Self"
  },
  "name": "nginxcert67a7ba",
  "status": "completed",
  "statusDetails": null,
  "target": "https://mykeyvault67a7ba.vault.azure.net/certificates/nginxcert67a7ba"
}
```

Slutligen måste vi förbereda certifikatet så att det kan användas under processen för att skapa virtuella datorer. För att göra det måste vi hämta ID:t för certifikatet med az keyvault secret list-versions och konvertera certifikatet med az vm secret format. Följande exempel tilldelar kommandonas resultat till variabler, vilket gör dem enklare att använda i nästa steg:

```bash
az identity create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_VM_ID_NAME -o JSON
```

Resultat:

<!-- expected_similarity=0.3 -->
```JSON
{
  "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourcegroups/myResourceGroupb1404f/providers/Microsoft.ManagedIdentity/userAssignedIdentities/myVMIDNameb1404f",
  "location": "eastus",
  "name": "myVMIDNameb1404f",
  "principalId": "e09ebfce-97f0-4aff-9abd-415ebd6f915c",
  "resourceGroup": "myResourceGroupb1404f",
  "tags": {},
  "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "type": "Microsoft.ManagedIdentity/userAssignedIdentities"
}
```

```bash
MY_VM_PRINCIPALID=$(az identity show --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_ID_NAME --query principalId -o tsv)

az keyvault set-policy \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_KEY_VAULT \
    --object-id $MY_VM_PRINCIPALID \
    --secret-permissions get list \
    --certificate-permissions get list -o JSON
```

Resultat:

<!-- expected_similarity=0.3 -->
```JSON
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myResourceGroupb1404f/providers/Microsoft.KeyVault/vaults/myKeyVaultb1404f",
  "location": "eastus",
  "name": "myKeyVaultb1404f",
  "properties": {
    "accessPolicies": [
      {
        "applicationId": null,
        "objectId": "ceeb4e98-5831-4d9f-b8ba-2ee14b3cdf80",
        "permissions": {
          "certificates": [
            "all"
          ],
          "keys": [
            "all"
          ],
          "secrets": [
            "all"
          ],
          "storage": [
            "all"
          ]
        },
        "tenantId": "bd7153ee-d085-4a28-a928-2f0ef402f076"
      },
      {
        "applicationId": null,
        "objectId": "e09ebfce-97f0-4aff-9abd-415ebd6f915c",
        "permissions": {
          "certificates": [
            "list",
            "get"
          ],
          "keys": null,
          "secrets": [
            "list",
            "get"
          ],
          "storage": null
        },
        "tenantId": "bd7153ee-d085-4a28-a928-2f0ef402f076"
      }
    ],
    "createMode": null,
    "enablePurgeProtection": null,
    "enableRbacAuthorization": null,
    "enableSoftDelete": true,
    "enabledForDeployment": true,
    "enabledForDiskEncryption": null,
    "enabledForTemplateDeployment": null,
    "hsmPoolResourceId": null,
    "networkAcls": null,
    "privateEndpointConnections": null,
    "provisioningState": "Succeeded",
    "publicNetworkAccess": "Enabled",
    "sku": {
      "family": "A",
      "name": "standard"
    },
    "softDeleteRetentionInDays": 7,
    "tenantId": "bd7153ee-d085-4a28-a928-2f0ef402f076",
    "vaultUri": "https://mykeyvaultb1404f.vault.azure.net/"
  },
  "resourceGroup": "myResourceGroupb1404f",
  "systemData": {
    "createdAt": "2023-09-18T12:25:55.208000+00:00",
    "createdBy": "ajoian@microsoft.com",
    "createdByType": "User",
    "lastModifiedAt": "2023-09-18T12:48:08.966000+00:00",
    "lastModifiedBy": "ajoian@microsoft.com",
    "lastModifiedByType": "User"
  },
  "tags": {},
  "type": "Microsoft.KeyVault/vaults"
}
```

## Skapa den virtuella datorn

Skapa nu en virtuell dator med az vm create. Använd parametern --custom-data för att skicka in cloud-init-konfigurationsfilen med namnet *cloud-init-nginx.txt*.
Cloud-init är ett vanligt sätt att anpassa en virtuell Linux-dator när den startas för första gången. Du kan använda cloud-init till att installera paket och skriva filer eller för att konfigurera användare och säkerhet. Eftersom cloud-init körs under den inledande startprocessen finns det inga extra steg eller nödvändiga agenter för att tillämpa konfigurationen.
När du skapar en virtuella dator lagras certifikat och nycklar i den skyddade katalogen /var/lib/waagent/. I det här exemplet installerar och konfigurerar vi NGINX-webbservern.

```bash
cat > cloud-init-nginx.txt <<EOF
#cloud-config

# Install, update, and upgrade packages
package_upgrade: true
package_update: true
package_reboot_if_require: true

# Install packages
packages:
  - nginx

write_files:
  - owner: www-data:www-data
  - path: /etc/nginx/sites-available/secure-server
    content: |
      server {
        server_name $FQDN;
        listen 443 ssl http2;
        ssl_certificate /etc/nginx/ssl/${MY_CERT_NAME}.crt;
        ssl_certificate_key /etc/nginx/ssl/${MY_CERT_NAME}.key;
      }
      server {
            listen 80;
            server_name $FQDN;
            return 301 https://$FQDN\$request_uri;
      }

  - owner: root:root
    path: /root/convert_akv_cert.sh
    permissions: "0750"
    content: |
        #!/bin/bash
        runtime="10 minute"; endtime=\$(date -ud "\$runtime" +%s); 
        while [[ \$(date -u +%s) -le \$endtime ]]; do
          if [[ ! -f /etc/nginx/ssl/${MY_KEY_VAULT}.${MY_CERT_NAME} ]]
            then
                sleep 5;
            else
                break;
          fi;
        done
        # Split the file in two (cert and key)
        echo "Creating .key file with private key..."
        openssl rsa -outform pem -in /etc/nginx/ssl/${MY_KEY_VAULT}.${MY_CERT_NAME} -out /etc/nginx/ssl/${MY_CERT_NAME}.key
        echo "Creating .crt file with certificate..."
        openssl x509 -outform pem -in /etc/nginx/ssl/${MY_KEY_VAULT}.${MY_CERT_NAME} -out /etc/nginx/ssl/${MY_CERT_NAME}.crt
runcmd:
  - mkdir /etc/nginx/ssl
  - ln -s /etc/nginx/sites-available/secure-server /etc/nginx/sites-enabled/
  - rm /etc/nginx/sites-enabled/default
  - bash /root/convert_akv_cert.sh
  - (crontab -l 2>/dev/null; echo "0 * * * * /root/convert_akv_cert.sh && service nginx reload") | crontab -
  - service nginx restart
EOF
```

I följande exempel skapas en virtuell dator med namnet *myVMName$UNIQUE_POSTFIX*:

```bash
MY_VM_ID=$(az identity show --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_ID_NAME --query id -o tsv)

az vm create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_VM_NAME \
    --image $MY_VM_IMAGE \
    --admin-username $MY_VM_USERNAME \
    --generate-ssh-keys \
    --assign-identity $MY_VM_ID \
    --size $MY_VM_SIZE \
    --custom-data cloud-init-nginx.txt \
    --nics $MY_VM_NIC_NAME
```

Resultat:

<!-- expected_similarity=0.3 -->
```JSON
{
  "fqdns": "mydnslabel67a7ba.eastus.cloudapp.azure.com",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myResourceGroup67a7ba/providers/Microsoft.Compute/virtualMachines/myVMName67a7ba",
  "identity": {
    "systemAssignedIdentity": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "userAssignedIdentities": {
      "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourcegroups/myResourceGroup67a7ba/providers/Microsoft.ManagedIdentity/userAssignedIdentities/myVMIDName67a7ba": {
        "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "principalId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
      }
    }
  },
  "location": "eastus",
  "macAddress": "60-45-BD-D3-B5-29",
  "powerState": "VM running",
  "privateIpAddress": "10.56.0.4",
  "publicIpAddress": "20.231.118.239",
  "resourceGroup": "myResourceGroup67a7ba",
  "zones": ""
}
```

## Distribuera AKV-tillägget för den virtuella datorn $vm_name för att hämta certifikatet $cert_name från AKV $akv_name..."

```bash
MY_CERT_ID=$(az keyvault certificate show --vault-name $MY_KEY_VAULT --name $MY_CERT_NAME --query sid -o tsv)
MY_VM_CLIENTID=$(az identity show --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_ID_NAME --query clientId -o tsv)
MY_AKV_EXT_SETTINGS="{\"secretsManagementSettings\":{\"pollingIntervalInS\":\"3600\",\"requireInitialSync\":"true",\"certificateStoreLocation\":\"/etc/nginx/ssl/\",\"observedCertificates\":[\"$MY_CERT_ID\"]},\"authenticationSettings\":{\"msiClientId\":\"${MY_VM_CLIENTID}\"}}"

az vm extension set \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME \
    -n "KeyVaultForLinux" \
    --publisher Microsoft.Azure.KeyVault \
    --version 2.0 \
    --enable-auto-upgrade true \
    --settings $MY_AKV_EXT_SETTINGS -o JSON
```

Resultat:

<!-- expected_similarity=0.3 -->
```JSON
{
  "autoUpgradeMinorVersion": true,
  "enableAutomaticUpgrade": true,
  "forceUpdateTag": null,
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myResourceGroup67a7ba/providers/Microsoft.Compute/virtualMachines/myVMName67a7ba/extensions/KeyVaultForLinux",
  "instanceView": null,
  "location": "eastus",
  "name": "KeyVaultForLinux",
  "protectedSettings": null,
  "protectedSettingsFromKeyVault": null,
  "provisioningState": "Succeeded",
  "publisher": "Microsoft.Azure.KeyVault",
  "resourceGroup": "myResourceGroup67a7ba",
  "settings": {
    "secretsManagementSettings": {
      "certificateStoreLocation": "/etc/nginx/ssl",
      "observedCertificates": [
        "https://mykeyvault67a7ba.vault.azure.net/secrets/nginxcert67a7ba/aac9b30a90c04fc58bc230ae15b1148f"
      ],
      "pollingIntervalInS": "3600"
    }
  },
  "suppressFailures": null,
  "tags": null,
  "type": "Microsoft.Compute/virtualMachines/extensions",
  "typeHandlerVersion": "2.0",
  "typePropertiesType": "KeyVaultForLinux"
}
```

## Aktivera Azure AD-inloggning för en virtuell Linux-dator i Azure

I följande exempel distribueras en virtuell dator och tillägget installeras för att aktivera Azure AD-inloggning för en virtuell Linux-dator. VM-tillägg är små program som tillhandahåller konfigurations- och automatiseringsuppgifter efter distributionen på virtuella Azure-datorer.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME -o JSON
```

Resultat:

<!-- expected_similarity=0.3 -->
```JSON
{
  "autoUpgradeMinorVersion": true,
  "enableAutomaticUpgrade": null,
  "forceUpdateTag": null,
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myResourceGroupfa636b/providers/Microsoft.Compute/virtualMachines/myVMNamefa636b/extensions/AADSSHLoginForLinux",
  "instanceView": null,
  "location": "eastus",
  "name": "AADSSHLoginForLinux",
  "protectedSettings": null,
  "protectedSettingsFromKeyVault": null,
  "provisioningState": "Succeeded",
  "publisher": "Microsoft.Azure.ActiveDirectory",
  "resourceGroup": "myResourceGroupfa636b",
  "settings": null,
  "suppressFailures": null,
  "tags": null,
  "type": "Microsoft.Compute/virtualMachines/extensions",
  "typeHandlerVersion": "1.0",
  "typePropertiesType": "AADSSHLoginForLinux"
}
```

## Bläddra på din säkra webbplats

Kontrollera att programmet körs genom att gå till program-URL:en:

```bash
curl --max-time 120 -k "https://$FQDN"
```

Resultat:

<!-- expected_similarity=0.3 -->
```html
<!DOCTYPE html>
<html>
<head>
<title>Welcome to nginx!</title>
<style>
    body {
        width: 35em;
        margin: 0 auto;
        font-family: Tahoma, Verdana, Arial, sans-serif;
    }
</style>
</head>
<body>
<h1>Welcome to nginx!</h1>
<p>If you see this page, the nginx web server is successfully installed and
working. Further configuration is required.</p>

<p>For online documentation and support please refer to
<a href="http://nginx.org/">nginx.org</a>.<br/>
Commercial support is available at
<a href="http://nginx.com/">nginx.com</a>.</p>

<p><em>Thank you for using nginx.</em></p>
</body>
</html>
```
