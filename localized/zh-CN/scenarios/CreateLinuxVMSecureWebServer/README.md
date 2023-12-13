---
title: 创建一个通过 HTTPS 进行安全保护的 NGINX Web 服务器
description: 本教程演示如何创建一个通过 HTTPS 进行安全保护的 NGINX Web 服务器。
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# 创建一个通过 HTTPS 进行安全保护的 NGINX Web 服务器

若要保护 Web 服务器，可以使用传输层安全 (TLS)（以前称为安全套接字层 (SSL)）证书来加密 Web 流量。 这些 TLS/SSL 证书可存储在 Azure Key Vault 中，并可安全部署到 Azure 中的 Linux 虚拟机 (VM)。 本教程介绍如何执行下列操作：

> [!div class="checklist"]

> * 设置和保护 Azure 网络
> * 创建 Azure Key Vault
> * 生成证书或将其上传到 Key Vault
> * 创建 VM 并安装 NGINX Web 服务器
> * 将证书注入 VM 并为 NGINX 配置 TLS 绑定

如果选择在本地安装并使用 CLI，本教程要求运行 Azure CLI 2.0.30 或更高版本。 运行 `az --version` 即可查找版本。 如果需要进行安装或升级，请参阅[安装 Azure CLI]( https://learn.microsoft.com//cli/azure/install-azure-cli )。

## 变量声明

执行本教程所需的所有环境变量的列表：

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

## 创建资源组。

使用 az group create 创建一个资源组，然后才能创建安全的 Linux 虚拟机。 以下示例创建一个资源组，该资源组与“MY_RESOURCE_GROUP_NAME”变量的内容相等，位置由变量内容“REGION”指定：****

```bash
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION -o JSON
```

结果：

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

## 设置虚拟机网络

使用 az network vnet create 创建名为“$MY_VNET_NAME”的虚拟网络，并在“$MY_RESOURCE_GROUP_NAME”资源组中创建名为“$MY_SN_NAME”的子网。******

```bash
az network vnet create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_VNET_NAME \
    --location $REGION \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefix $MY_SN_PREFIX -o JSON
```

结果：

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

使用 az network public-ip create 在“$MY_RESOURCE_GROUP_NAME”中创建名为“$MY_PUBLIC_IP_NAME”的标准区域冗余公共 IPv4 地址。****

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

结果：

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

通过网络安全组中的安全规则，可以筛选可流入和流出虚拟网络子网和网络接口的流量类型。 若要深入了解网络安全组，请参阅[网络安全组概述](https://learn.microsoft.com/azure/virtual-network/network-security-groups-overview)。

```bash
az network nsg create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_NSG_NAME \
    --location $REGION -o JSON
```

结果：

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

打开端口 22 (SSH)、80 (HTTP) 和 443 (HTTPS)，以允许 SSH 和 Web 流量通过

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

结果：

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

最后创建网络接口卡 (NIC)：

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

结果：

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

## 生成证书并将其存储在 Azure 密钥保管库中

Azure Key Vault 保护加密密钥和机密，例如证书或密码。 Key Vault 有助于简化证书管理过程，让我们持续掌控用于访问这些证书的密钥。 可以在 Key Vault 中创建自签名证书，或者上传已拥有的现有受信任证书。 在本教程中，我们将在密钥保管库中创建自签名证书，然后将这些证书注入正在运行的虚拟机。 此过程可确保在部署过程中，在 Web 服务器上安装最新的证书。

以下示例在所选区域“$REGION”中创建名为“$MY_KEY_VAULT”的 Azure 密钥保管库，其保留策略为 7 天。**** 这意味着如果机密、密钥、证书或密钥保管库被删除，在一个可配置的时间段（ 7 到 90 个日历日）内将一直保持可恢复状态。

```bash
az keyvault create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_KEY_VAULT \
    --location $REGION \
    --retention-days 7\
    --enabled-for-deployment true -o JSON
```

结果：

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

## 创建证书并存储在 Azure 密钥保管库中

现在，让我们使用 az keyvault certificate create 创建自签名证书，该证书使用默认证书策略：

```bash
az keyvault certificate create \
    --vault-name $MY_KEY_VAULT \
    --name $MY_CERT_NAME \
    --policy "$(az keyvault certificate get-default-policy)" -o JSON
```

结果：

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

最后，我们需要准备证书，以便在虚拟机创建过程中使用它。 为此，我们需要使用 az keyvault secret list-versions 来获取证书 ID，并使用 az vm secret format 转换证书格式。 以下示例将这些命令的输出分配给变量，以便在后续步骤中使用：

```bash
az identity create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_VM_ID_NAME -o JSON
```

结果：

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

结果：

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

## 创建 VM

现使用 az vm create 创建 VM。 使用 --custom-data 参数传入 cloud-init 配置文件，名为“cloud-init-nginx.txt”。**
Cloud-init 是一种广泛使用的方法，用于在首次启动 Linux VM 时对其进行自定义。 可使用 cloud-init 来安装程序包和写入文件，或者配置用户和安全性。 在初始启动期间运行 cloud-init 时，无需额外的步骤且无需代理来应用配置。
创建 VM 时，证书和密钥都将存储在受保护的 /var/lib/waagent/  目录中。 在此示例中，我们将安装和配置 NGINX Web 服务器。

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

以下示例创建了名为“myVMName$UNIQUE_POSTFIX”的虚拟机：**

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

结果：

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

## 为虚拟机 $vm_name 部署 AKV 扩展，以从 AKV $akv_name 中检索证书 $cert_name...”

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

结果：

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

## 在 Azure 中为 Linux 虚拟机启用 Azure AD 登录

以下示例部署一个 VM，然后安装该扩展以启用适用于 Linux VM 的 Azure AD 登录。 VM 扩展是小型应用程序，可在 Azure 虚拟机上提供部署后配置和自动化任务。

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME -o JSON
```

结果：

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

## 浏览安全网站

通过访问应用程序 URL 验证应用程序是否正在运行：

```bash
curl --max-time 120 -k "https://$FQDN"
```

结果：

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
