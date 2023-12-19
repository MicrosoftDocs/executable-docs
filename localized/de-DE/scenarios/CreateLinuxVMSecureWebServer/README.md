---
title: Erstellen eines über HTTPS gesicherten NGINX-Webservers
description: 'In diesem Tutorial wird gezeigt, wie Sie einen über HTTPS gesicherten NGINX-Webserver erstellen.'
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Erstellen eines über HTTPS gesicherten NGINX-Webservers

Als Schutz für Webserver kann ein TLS-Zertifikat (Transport Layer Security) verwendet werden, um Webdatenverkehr zu verschlüsseln. „Transport Layer Security“ wurde früher als „Secure Sockets Layer“ (SSL) bezeichnet. Diese TLS/SSL-Zertifikate können in Azure Key Vault gespeichert werden. Sie ermöglichen sichere Bereitstellungen von Zertifikaten auf virtuellen Linux-Computern in Azure. In diesem Tutorial lernen Sie Folgendes:

> [!div class="checklist"]

> * Einrichten und Schützen von Azure-Netzwerken
> * Erstellen einer Azure Key Vault-Instanz
> * Generieren oder Hochladen eines Zertifikats in Key Vault
> * Erstellen eines virtuellen Computers und Installieren des NGINX-Webservers
> * Einfügen des Zertifikats auf dem virtuellen Computer und Konfigurieren von NGINX mit einer TLS-Bindung

Wenn Sie die CLI lokal installieren und verwenden möchten, müssen Sie für dieses Tutorial mindestens die Azure CLI-Version 2.0.30 ausführen. Führen Sie `az --version` aus, um die Version zu ermitteln. Informationen zum Durchführen einer Installation oder eines Upgrades finden Sie bei Bedarf unter [Installieren der Azure CLI]( https://learn.microsoft.com//cli/azure/install-azure-cli ).

## Variablendeklaration

Liste aller Umgebungsvariablen, die Sie zum Ausführen dieses Tutorials benötigen:

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

## Erstellen einer Ressourcengruppe

Vor der Erstellung einer sicheren Linux-VM müssen Sie zunächst mit „az group create“ eine Ressourcengruppe erstellen. Im folgenden Beispiel wird eine Ressourcengruppe erstellt, die dem Inhalt der Variablen *MY_RESOURCE_GROUP_NAME* an dem durch den Variableninhalt angegebenen Standort *REGION* entspricht:

```bash
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION -o JSON
```

Ergebnisse:

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

## Einrichten eines VM-Netzwerks

Erstellen Sie mit „az network vnet create“ ein virtuelles Netzwerk namens *$MY_VNET_NAME* mit dem Subnetznamen *$MY_SN_NAME* in der Ressourcengruppe *$MY_RESOURCE_GROUP_NAME*.

```bash
az network vnet create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_VNET_NAME \
    --location $REGION \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefix $MY_SN_PREFIX -o JSON
```

Ergebnisse:

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

Verwenden Sie „az network public-ip create“, um in *$MY_RESOURCE_GROUP_NAME* eine zonenredundante öffentliche IPv4-Standardadresse namens *$MY_PUBLIC_IP_NAME* zu erstellen.

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

Ergebnisse:

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

Mit Sicherheitsregeln in Netzwerksicherheitsgruppen können Sie den Typ des ein- und ausgehenden Netzwerkdatenverkehrs von Subnetzen virtueller Netzwerke und Netzwerkschnittstellen filtern. Weitere Informationen zu Netzwerksicherheitsgruppen finden Sie unter [Netzwerksicherheitsgruppen – Übersicht](https://learn.microsoft.com/azure/virtual-network/network-security-groups-overview).

```bash
az network nsg create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_NSG_NAME \
    --location $REGION -o JSON
```

Ergebnisse:

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

Offene Ports 22 (SSH), 80 (HTTP) und 443 (HTTPS), um SSH und Webdatenverkehr zuzulassen

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

Ergebnisse:

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

Erstellen Sie schließlich den Netzwerkadapter:

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

Ergebnisse:

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

## Generieren eines Zertifikats und Speichern des Zertifikats in Azure Key Vault

Azure Key Vault schützt Kryptografieschlüssel und Geheimnisse, wie z.B. Zertifikate oder Kennwörter. Key Vault optimiert die Zertifikatverwaltung und ermöglicht Ihnen, die Kontrolle über Schlüssel zu behalten, die auf diese Zertifikate zugreifen. Sie können ein selbstsigniertes Zertifikat in Key Vault erstellen oder ein vorhandenes vertrauenswürdiges Zertifikat verwenden, das Sie bereits besitzen. In diesem Tutorial erstellen Sie selbstsignierte Zertifikate in Key Vault und fügen diese Zertifikate anschließend in eine ausgeführte VM ein. Dadurch wird sichergestellt, dass auf einem Webserver während der Bereitstellung die aktuellen Zertifikate installiert sind.

Im folgenden Beispiel wird eine Azure Key Vault-Instanz mit dem Namen *$MY_KEY_VAULT* in der ausgewählten Region *$REGION* mit einer Aufbewahrungsrichtlinie von 7 Tagen erstellt. Das bedeutet Folgendes: Sobald Geheimnisse, Schlüssel, Zertifikate oder Schlüsseltresore gelöscht wurden, können sie wiederhergestellt werden. Dies ist je nach Ihrer Konfiguration für einen Zeitraum von 7 bis 90 Kalendertagen möglich.

```bash
az keyvault create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_KEY_VAULT \
    --location $REGION \
    --retention-days 7\
    --enabled-for-deployment true -o JSON
```

Ergebnisse:

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

## Erstellen eines Zertifikats und Speichern des Zertifikats in Azure Key Vault

Generieren Sie nun ein selbstsigniertes Zertifikat mit „az keyvault certificate create“, das die Standardzertifikatrichtlinie verwendet:

```bash
az keyvault certificate create \
    --vault-name $MY_KEY_VAULT \
    --name $MY_CERT_NAME \
    --policy "$(az keyvault certificate get-default-policy)" -o JSON
```

Ergebnisse:

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

Schließlich müssen Sie das Zertifikat vorbereiten, damit es während des Erstellungsprozesses der VM verwendet werden kann. Dazu müssen wir die ID des Zertifikats mit „az keyvault secret list-versions“ abrufen und das Zertifikat mit „az vm secret format“ konvertieren. Im folgenden Beispiel wird die Ausgabe dieser Befehle Variablen zugewiesen, um die Verwendung in den nächsten Schritten zu vereinfachen:

```bash
az identity create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_VM_ID_NAME -o JSON
```

Ergebnisse:

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

Ergebnisse:

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

## Erstellen des virtuellen Computers

Jetzt können Sie mit az vm create einen virtuellen Computer erstellen. Verwenden Sie den Parameter „--custom-data“, um die cloud-init-Konfigurationsdatei mit dem Namen *cloud-init-nginx.txt* zu übergeben.
Cloud-init ist ein weit verbreiteter Ansatz zum Anpassen einer Linux-VM beim ersten Start. Sie können mit cloud-init Pakete installieren und Dateien schreiben oder Benutzer und Sicherheit konfigurieren. Da cloud-init während des ersten Startvorgangs ausgeführt wird, müssen Sie keine zusätzlichen Schritte oder erforderlichen Agents auf Ihre Konfiguration anwenden.
Wenn Sie einen virtuellen Computer erstellen, werden Zertifikate und Schlüssel im geschützten Verzeichnis /var/lib/waagent/ gespeichert. In diesem Beispiel wird der NGINX-Webserver installiert und konfiguriert.

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

Im folgenden Beispiel wird eine VM namens *myVMName$UNIQUE_POSTFIX* erstellt:

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

Ergebnisse:

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

## Bereitstellen der AKV-Erweiterung für die VM „$vm_name“ zum Abrufen des Zertifikats „$cert_name“ aus der AKV-Instanz „$akv_name...“

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

Ergebnisse:

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

## Aktivieren der Azure AD-Anmeldung für eine Linux-VM in Azure

Im folgenden Beispiel wird eine VM bereitgestellt und dann die Erweiterung installiert, um die Azure AD-Anmeldung für eine Linux-VM zu aktivieren. VM-Erweiterungen sind kleine Anwendungen, die Konfigurations- und Automatisierungsaufgaben auf virtuellen Azure-Computern nach der Bereitstellung ermöglichen.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME -o JSON
```

Ergebnisse:

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

## Browsen auf Ihrer sicheren Website

Überprüfen Sie, ob die Anwendung ausgeführt wird, indem Sie die Anwendungs-URL aufrufen:

```bash
curl --max-time 120 -k "https://$FQDN"
```

Ergebnisse:

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
