---
title: Tworzenie serwera internetowego NGINX zabezpieczonego za pośrednictwem protokołu HTTPS
description: 'W tym samouczku pokazano, jak utworzyć serwer sieci Web NGINX zabezpieczony za pośrednictwem protokołu HTTPS.'
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Tworzenie serwera internetowego NGINX zabezpieczonego za pośrednictwem protokołu HTTPS

Aby zabezpieczyć serwery internetowe, certyfikat Transport Layer Security (TLS), wcześniej znany jako Secure Sockets Layer (SSL), może służyć do szyfrowania ruchu internetowego. Te certyfikaty TLS/SSL można przechowywać w usłudze Azure Key Vault i zezwalać na bezpieczne wdrożenia certyfikatów na maszynach wirtualnych z systemem Linux na platformie Azure. Ten samouczek zawiera informacje na temat wykonywania następujących czynności:

> [!div class="checklist"]

> * Konfigurowanie i zabezpieczanie sieci platformy Azure
> * Tworzenie usługi Azure Key Vault
> * Generowanie lub przekazywanie certyfikatu do usługi Key Vault
> * Tworzenie maszyny wirtualnej i instalowanie serwera sieci Web NGINX
> * Wstrzykiwanie certyfikatu do maszyny wirtualnej i konfigurowanie serwera NGINX przy użyciu powiązania TLS

Jeśli zdecydujesz się zainstalować interfejs wiersza polecenia i korzystać z niego lokalnie, ten samouczek będzie wymagał interfejsu wiersza polecenia platformy Azure w wersji 2.0.30 lub nowszej. Uruchom polecenie `az --version`, aby dowiedzieć się, jaka wersja jest używana. Jeśli konieczna będzie instalacja lub uaktualnienie, zobacz [Instalowanie interfejsu wiersza polecenia platformy Azure]( https://learn.microsoft.com//cli/azure/install-azure-cli ).

## Deklaracja zmiennej

Lista wszystkich zmiennych środowiskowych, które należy wykonać w tym samouczku:

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

## Tworzenie grupy zasobów

Przed utworzeniem bezpiecznej maszyny wirtualnej z systemem Linux utwórz grupę zasobów za pomocą polecenia az group create. Poniższy przykład tworzy grupę zasobów równą zawartości zmiennej *MY_RESOURCE_GROUP_NAME* w lokalizacji określonej przez region zawartości ** zmiennej:

```bash
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION -o JSON
```

Wyniki:

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

## Konfigurowanie sieci maszyn wirtualnych

Użyj polecenia az network vnet create, aby utworzyć sieć wirtualną o nazwie $MY_VNET_NAME z podsiecią o nazwie **$MY_SN_NAME*w *grupie zasobów $MY_RESOURCE_GROUP_NAME*.*

```bash
az network vnet create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_VNET_NAME \
    --location $REGION \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefix $MY_SN_PREFIX -o JSON
```

Wyniki:

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

Użyj polecenia az network public-ip create, aby utworzyć strefowo nadmiarowy publiczny adres IPv4 o nazwie *$MY_PUBLIC_IP_NAME* w *$MY_RESOURCE_GROUP_NAME*.

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

Wyniki:

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

Reguły zabezpieczeń w sieciowych grupach zabezpieczeń umożliwiają filtrowanie typu ruchu sieciowego, który może wchodzić do podsieci sieci wirtualnej i interfejsów sieciowych oraz z nich wychodzić. Aby dowiedzieć się więcej o sieciowych grupach zabezpieczeń, zobacz [Omówienie](https://learn.microsoft.com/azure/virtual-network/network-security-groups-overview) sieciowej grupy zabezpieczeń.

```bash
az network nsg create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_NSG_NAME \
    --location $REGION -o JSON
```

Wyniki:

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

Otwieranie portów 22 (SSH), 80 (HTTP) i 443 (HTTPS) w celu zezwolenia na ruch SSH i sieci Web

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

Wyniki:

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

Na koniec utwórz kartę interfejsu sieciowego (NIC):

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

Wyniki:

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

## Generowanie certyfikatu i przechowywanie go w usłudze Azure Key Vault

Usługa Azure Key Vault chroni klucze kryptograficzne i klucze tajne, takie jak certyfikaty lub hasła. Usługa Key Vault pomaga uprościć proces zarządzania certyfikatami i pozwala zachować kontrolę nad kluczami, które uzyskują dostęp do tych certyfikatów. Możesz utworzyć certyfikat z podpisem własnym wewnątrz usługi Key Vault lub przekazać istniejący zaufany certyfikat, który już posiadasz. W tym samouczku utworzymy certyfikaty z podpisem własnym w usłudze Key Vault, a następnie wprowadzimy te certyfikaty do uruchomionej maszyny wirtualnej. Ten proces zapewnia, że podczas wdrażania na serwerze sieci Web zostaną zainstalowane najbardziej aktualne certyfikaty.

Poniższy przykład tworzy usługę Azure Key Vault o nazwie *$MY_KEY_VAULT* w wybranym regionie *$REGION* z zasadami przechowywania 7 dni. Oznacza to, że po usunięciu wpisu tajnego, klucza, certyfikatu lub magazynu kluczy można go odzyskać przez konfigurowalny okres od 7 do 90 dni kalendarzowych.

```bash
az keyvault create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_KEY_VAULT \
    --location $REGION \
    --retention-days 7\
    --enabled-for-deployment true -o JSON
```

Wyniki:

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

## Tworzenie certyfikatu i magazynu w usłudze Azure Key Vault

Teraz wygenerujmy certyfikat z podpisem własnym za pomocą polecenia az keyvault certificate create, który używa domyślnych zasad certyfikatu:

```bash
az keyvault certificate create \
    --vault-name $MY_KEY_VAULT \
    --name $MY_CERT_NAME \
    --policy "$(az keyvault certificate get-default-policy)" -o JSON
```

Wyniki:

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

Na koniec musimy przygotować certyfikat, aby można go było użyć podczas procesu tworzenia maszyny wirtualnej. W tym celu musimy uzyskać identyfikator certyfikatu za pomocą polecenia az keyvault secret list-versions i przekonwertować certyfikat za pomocą formatu az vm secret format. W poniższym przykładzie przypisano dane wyjściowe tych poleceń do zmiennych w celu łatwiejszego użycia w następnych krokach:

```bash
az identity create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_VM_ID_NAME -o JSON
```

Wyniki:

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

Wyniki:

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

## Tworzenie maszyny wirtualnej

Utwórz maszynę wirtualną za pomocą polecenia az vm create. Użyj parametru --custom-data, aby przekazać plik konfiguracji cloud-init o nazwie *cloud-init-nginx.txt*.
Cloud-init to powszechnie używana metoda dostosowywania maszyny wirtualnej z systemem Linux podczas jej pierwszego rozruchu. Za pomocą pakietu cloud-init można instalować pakiety i zapisywać pliki lub konfigurować użytkowników i zabezpieczenia. Ponieważ program cloud-init jest uruchamiany podczas początkowego procesu rozruchu, nie ma dodatkowych kroków ani agentów wymaganych do zastosowania konfiguracji.
Podczas tworzenia maszyny wirtualnej certyfikaty i klucze są przechowywane w chronionym katalogu /var/lib/agentawaagent/. W tym przykładzie instalujemy i konfigurujemy serwer internetowy NGINX.

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

Poniższy przykład tworzy maszynę wirtualną o nazwie *myVMName$UNIQUE_POSTFIX*:

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

Wyniki:

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

## Wdrażanie rozszerzenia AKV dla maszyny wirtualnej $vm_name w celu pobrania nazwy $cert_certyfikatu z $akv_name usługi AKV..."

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

Wyniki:

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

## Włączanie logowania usługi Azure AD dla maszyny wirtualnej z systemem Linux na platformie Azure

Poniższy przykład umożliwia wdrożenie maszyny wirtualnej, a następnie zainstalowanie rozszerzenia w celu włączenia logowania do usługi Azure AD dla maszyny wirtualnej z systemem Linux. Rozszerzenia maszyn wirtualnych to małe aplikacje, które zapewniają konfigurację po wdrożeniu i zadania automatyzacji na maszynach wirtualnych platformy Azure.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME -o JSON
```

Wyniki:

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

## Przeglądanie bezpiecznej witryny internetowej

Sprawdź, czy aplikacja jest uruchomiona, odwiedzając adres URL aplikacji:

```bash
curl --max-time 120 -k "https://$FQDN"
```

Wyniki:

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
