---
title: Tworzenie zestawu skalowania maszyn wirtualnych za pomocą usługi Application Gateway z obrazem systemu Linux
description: 'W tym samouczku pokazano, jak utworzyć zestaw skalowania maszyn wirtualnych przy użyciu usługi Application Gateway z obrazem systemu Linux'
author: belginceran
ms.author: belginceran
ms.topic: article
ms.date: 01/05/2024
ms.custom: innovation-engine
---

# Tworzenie zestawu skalowania maszyn wirtualnych za pomocą usługi Application Gateway z obrazem systemu Linux

## Definiowanie zmiennych środowiskowych

Pierwszym krokiem w tym samouczku jest zdefiniowanie zmiennych środowiskowych.

```bash

export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMSSResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VMSS_NAME="myVMSS$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Ubuntu2204"
export MY_VNET_NAME="myVNet$RANDOM_ID"
export NETWORK_PREFIX="$(($RANDOM % 254 + 1))"
export MY_VNET_PREFIX="10.$NETWORK_PREFIX.0.0/16"
export MY_VM_SN_NAME="myVMSN$RANDOM_ID"
export MY_VM_SN_PREFIX="10.$NETWORK_PREFIX.0.0/24"
export MY_APPGW_SN_NAME="myAPPGWSN$RANDOM_ID"
export MY_APPGW_SN_PREFIX="10.$NETWORK_PREFIX.1.0/24"
export MY_APPGW_NAME="myAPPGW$RANDOM_ID"
export MY_APPGW_PUBLIC_IP_NAME="myAPPGWPublicIP$RANDOM_ID"

```
# Logowanie do platformy Azure przy użyciu interfejsu wiersza polecenia

Aby uruchamiać polecenia na platformie Azure przy użyciu interfejsu wiersza polecenia, musisz się zalogować. Odbywa się to bardzo po prostu, choć `az login` polecenie:

# Tworzenie grupy zasobów

Grupa zasobów to kontener powiązanych zasobów. Wszystkie zasoby należy umieścić w grupie zasobów. Utworzymy go na potrzeby tego samouczka. Następujące polecenie tworzy grupę zasobów z wcześniej zdefiniowanymi parametrami $MY_RESOURCE_GROUP_NAME i $REGION.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION -o JSON
```

Wyniki:

<!-- expected_similarity=0.3 -->
```json   
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxxx",
  "location": "eastus",
  "managedBy": null,
  "name": "myVMSSResourceGroupxxxxxx",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

# Tworzenie zasobów sieciowych 

Przed kontynuowaniem kroków usługi VMSS należy utworzyć zasoby sieciowe. W tym kroku utworzysz sieć wirtualną, 2 podsieci 1 dla usługi Application Gateway i 1 dla maszyn wirtualnych. Musisz również mieć publiczny adres IP, aby dołączyć usługę Application Gateway, aby móc uzyskać dostęp do aplikacji internetowej z Internetu. 


#### Tworzenie sieci wirtualnej i podsieci maszyn wirtualnych

```bash
az network vnet create  --name $MY_VNET_NAME  --resource-group $MY_RESOURCE_GROUP_NAME --location $REGION  --address-prefix $MY_VNET_PREFIX  --subnet-name $MY_VM_SN_NAME --subnet-prefix $MY_VM_SN_PREFIX -o JSON
```

Wyniki:

<!-- expected_similarity=0.3 -->
```json   
{
  "newVNet": {
    "addressSpace": {
      "addressPrefixes": [
        "10.X.0.0/16"
      ]
    },
    "enableDdosProtection": false,
    "etag": "W/\"xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\"",
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxxx/providers/Microsoft.Network/virtualNetworks/myVNetxxxxxx",
    "location": "eastus",
    "name": "myVNetxxxxxx",
    "provisioningState": "Succeeded",
    "resourceGroup": "myVMSSResourceGroupxxxxxx",
    "resourceGuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "subnets": [
      {
        "addressPrefix": "10.X.0.0/24",
        "delegations": [],
        "etag": "W/\"xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\"",
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxxx/providers/Microsoft.Network/virtualNetworks/myVNetxxxxxx/subnets/myVMSNxxxxxx", 
        "name": "myVMSNxxxxxx",
        "privateEndpointNetworkPolicies": "Disabled",
        "privateLinkServiceNetworkPolicies": "Enabled",
        "provisioningState": "Succeeded",
        "resourceGroup": "myVMSSResourceGroupxxxxxx",
        "type": "Microsoft.Network/virtualNetworks/subnets"
      }
    ],
    "type": "Microsoft.Network/virtualNetworks",
    "virtualNetworkPeerings": []
  }
}
```

### Tworzenie zasobów usługi Application Gateway

aplikacja systemu Azure Gateway wymaga dedykowanej podsieci w sieci wirtualnej. Poniższe polecenie tworzy podsieć o nazwie $MY_APPGW_SN_NAME z określonym prefiksem adresu o nazwie $MY_APPGW_SN_PREFIX w sieci wirtualnej $MY_VNET_NAME 


```bash
az network vnet subnet create  --name $MY_APPGW_SN_NAME  --resource-group $MY_RESOURCE_GROUP_NAME --vnet-name  $MY_VNET_NAME --address-prefix  $MY_APPGW_SN_PREFIX -o JSON
```

Wyniki:

<!-- expected_similarity=0.3 -->
```json  
{
  "addressPrefix": "10.66.1.0/24",
  "delegations": [],
  "etag": "W/\"xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\"",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxxx/providers/Microsoft.Network/virtualNetworks/myVNetxxxxxx/subnets/myAPPGWSNxxxxxx",    
  "name": "myAPPGWSNxxxxxx",
  "privateEndpointNetworkPolicies": "Disabled",
  "privateLinkServiceNetworkPolicies": "Enabled",
  "provisioningState": "Succeeded",
  "resourceGroup": "myVMSSResourceGroupxxxxxx",
  "type": "Microsoft.Network/virtualNetworks/subnets"
}
```
Poniższe polecenie tworzy standardowy, strefowo nadmiarowy, statyczny, publiczny protokół IPv4 w grupie zasobów.  

```bash
az network public-ip create  --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_APPGW_PUBLIC_IP_NAME --sku Standard   --location $REGION  --allocation-method static --version IPv4 --zone 1 2 3 -o JSON
 ```

Wyniki:

<!-- expected_similarity=0.3 -->
```json  
{
  "publicIp": {
    "ddosSettings": {
      "protectionMode": "VirtualNetworkInherited"
    },
    "etag": "W/\"xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\"",
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxxx/providers/Microsoft.Network/publicIPAddresses//myAPPGWPublicIPxxxxxx",
    "idleTimeoutInMinutes": 4,
    "ipAddress": "X.X.X.X",
    "ipTags": [],
    "location": "eastus",
    "name": "/myAPPGWPublicIPxxxxxx",
    "provisioningState": "Succeeded",
    "publicIPAddressVersion": "IPv4",
    "publicIPAllocationMethod": "Static",
    "resourceGroup": "myVMSSResourceGroupxxxxxx",
    "resourceGuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
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

W tym kroku utworzysz usługę Application Gateway, która zostanie zintegrowana z zestawem skalowania maszyn wirtualnych. W tym przykładzie utworzymy strefowo nadmiarową usługę Application Gateway z Standard_v2 sku i włączymy komunikację HTTP dla usługi Application Gateway. Publiczny adres IP $MY_APPGW_PUBLIC_IP_NAME utworzony w poprzednim kroku dołączonym do usługi Application Gateway. 

```bash
az network application-gateway create   --name $MY_APPGW_NAME --location $REGION --resource-group $MY_RESOURCE_GROUP_NAME --vnet-name $MY_VNET_NAME --subnet $MY_APPGW_SN_NAME --capacity 2  --zones 1 2 3 --sku Standard_v2   --http-settings-cookie-based-affinity Disabled   --frontend-port 80 --http-settings-port 80   --http-settings-protocol Http --public-ip-address $MY_APPGW_PUBLIC_IP_NAME --priority 1001 -o JSON
 ```

<!-- expected_similarity=0.3 -->
```json 
{
  "applicationGateway": {
    "backendAddressPools": [
      {
        "etag": "W/\"xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\"",
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxxx/providers/Microsoft.Network/applicationGateways/myAPPGWxxxxxx/backendAddressPools/appGatewayBackendPool",
        "name": "appGatewayBackendPool",
        "properties": {
          "backendAddresses": [],
          "provisioningState": "Succeeded",
          "requestRoutingRules": [
            {
              "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxxx/providers/Microsoft.Network/applicationGateways/myAPPGWxxxxxx/requestRoutingRules/rule1",
              "resourceGroup": "myVMSSResourceGroupxxxxxx"
            }
          ]
        },
        "resourceGroup": "myVMSSResourceGroupxxxxxx",
        "type": "Microsoft.Network/applicationGateways/backendAddressPools"
      }
    ],
    "backendHttpSettingsCollection": [
      {
        "etag": "W/\"xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\"",
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxxx/providers/Microsoft.Network/applicationGateways/myAPPGWxxxxxx/backendHttpSettingsCollection/appGatewayBackendHttpSettings",
        "name": "appGatewayBackendHttpSettings",
        "properties": {
          "connectionDraining": {
            "drainTimeoutInSec": 1,
            "enabled": false
          },
          "cookieBasedAffinity": "Disabled",
          "pickHostNameFromBackendAddress": false,
          "port": 80,
          "protocol": "Http",
          "provisioningState": "Succeeded",
          "requestRoutingRules": [
            {
              "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxxx/providers/Microsoft.Network/applicationGateways/myAPPGWxxxxxx/requestRoutingRules/rule1",
              "resourceGroup": "myVMSSResourceGroupxxxxxx"
            }
          ],
          "requestTimeout": 30
        },
        "resourceGroup": "myVMSSResourceGroupxxxxxx",
        "type": "Microsoft.Network/applicationGateways/backendHttpSettingsCollection"
      }
    ],
    "backendSettingsCollection": [],
    "frontendIPConfigurations": [
      {
        "etag": "W/\"xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\"",
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxxx/providers/Microsoft.Network/applicationGateways/myAPPGWxxxxxx/frontendIPConfigurations/appGatewayFrontendIP",
        "name": "appGatewayFrontendIP",
        "properties": {
          "httpListeners": [
            {
              "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxxx/providers/Microsoft.Network/applicationGateways/myAPPGWxxxxxx/httpListeners/appGatewayHttpListener",
              "resourceGroup": "myVMSSResourceGroupxxxxxx"
            }
          ],
          "privateIPAllocationMethod": "Dynamic",
          "provisioningState": "Succeeded",
          "publicIPAddress": {
            "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxxx/providers/Microsoft.Network/publicIPAddresses/myAPPGWPublicIPxxxxxx",       
            "resourceGroup": "myVMSSResourceGroupxxxxxx"
          }
        },
        "resourceGroup": "myVMSSResourceGroupxxxxxx",
        "type": "Microsoft.Network/applicationGateways/frontendIPConfigurations"
      }
    ],
    "frontendPorts": [
      {
        "etag": "W/\"xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\"",
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxxx/providers/Microsoft.Network/applicationGateways/myAPPGWxxxxxx/frontendPorts/appGatewayFrontendPort",
        "name": "appGatewayFrontendPort",
        "properties": {
          "httpListeners": [
            {
              "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxxx/providers/Microsoft.Network/applicationGateways/myAPPGWxxxxxx/httpListeners/appGatewayHttpListener",
              "resourceGroup": "myVMSSResourceGroupxxxxxx"
            }
          ],
          "port": 80,
          "provisioningState": "Succeeded"
        },
        "resourceGroup": "myVMSSResourceGroupxxxxxx",
        "type": "Microsoft.Network/applicationGateways/frontendPorts"
      }
    ],
    "gatewayIPConfigurations": [
      {
        "etag": "W/\"xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\"",
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxxx/providers/Microsoft.Network/applicationGateways/myAPPGWxxxxxx/gatewayIPConfigurations/appGatewayFrontendIP",
        "name": "appGatewayFrontendIP",
        "properties": {
          "provisioningState": "Succeeded",
          "subnet": {
            "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxxx/providers/Microsoft.Network/virtualNetworks/myVNetxxxxxx/subnets/myAPPGWSNxxxxxx",
            "resourceGroup": "myVMSSResourceGroupxxxxxx"
          }
        },
        "resourceGroup": "myVMSSResourceGroupxxxxxx",
        "type": "Microsoft.Network/applicationGateways/gatewayIPConfigurations"
      }
    ],
    "httpListeners": [
      {
        "etag": "W/\"xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\"",
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxxx/providers/Microsoft.Network/applicationGateways/myAPPGWxxxxxx/httpListeners/appGatewayHttpListener",
        "name": "appGatewayHttpListener",
        "properties": {
          "frontendIPConfiguration": {
            "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxxx/providers/Microsoft.Network/applicationGateways/myAPPGWxxxxxx/frontendIPConfigurations/appGatewayFrontendIP",
            "resourceGroup": "myVMSSResourceGroupxxxxxx"
          },
          "frontendPort": {
            "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxxx/providers/Microsoft.Network/applicationGateways/myAPPGWxxxxxx/frontendPorts/appGatewayFrontendPort",
            "resourceGroup": "myVMSSResourceGroupxxxxxx"
          },
          "hostNames": [],
          "protocol": "Http",
          "provisioningState": "Succeeded",
          "requestRoutingRules": [
            {
              "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxxx/providers/Microsoft.Network/applicationGateways/myAPPGWxxxxxx/requestRoutingRules/rule1",
              "resourceGroup": "myVMSSResourceGroupxxxxxx"
            }
          ],
          "requireServerNameIndication": false
        },
        "resourceGroup": "myVMSSResourceGroupxxxxxx",
        "type": "Microsoft.Network/applicationGateways/httpListeners"
      }
    ],
    "listeners": [],
    "loadDistributionPolicies": [],
    "operationalState": "Running",
    "privateEndpointConnections": [],
    "privateLinkConfigurations": [],
    "probes": [],
    "provisioningState": "Succeeded",
    "redirectConfigurations": [],
    "requestRoutingRules": [
      {
        "etag": "W/\"xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\"",
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxxx/providers/Microsoft.Network/applicationGateways/myAPPGWxxxxxx/requestRoutingRules/rule1",
        "name": "rule1",
        "properties": {
          "backendAddressPool": {
            "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxxx/providers/Microsoft.Network/applicationGateways/myAPPGWxxxxxx/backendAddressPools/appGatewayBackendPool",
            "resourceGroup": "myVMSSResourceGroupxxxxxx"
          },
          "backendHttpSettings": {
            "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxxx/providers/Microsoft.Network/applicationGateways/myAPPGWxxxxxx/backendHttpSettingsCollection/appGatewayBackendHttpSettings",
            "resourceGroup": "myVMSSResourceGroupxxxxxx"
          },
          "httpListener": {
            "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxxx/providers/Microsoft.Network/applicationGateways/myAPPGWxxxxxx/httpListeners/appGatewayHttpListener",
            "resourceGroup": "myVMSSResourceGroupxxxxxx"
          },
          "priority": 1001,
          "provisioningState": "Succeeded",
          "ruleType": "Basic"
        },
        "resourceGroup": "myVMSSResourceGroupxxxxxx",
        "type": "Microsoft.Network/applicationGateways/requestRoutingRules"
      }
    ],
    "resourceGuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "rewriteRuleSets": [],
    "routingRules": [],
    "sku": {
      "capacity": 2,
      "family": "Generation_1",
      "name": "Standard_v2",
      "tier": "Standard_v2"
    },
    "sslCertificates": [],
    "sslProfiles": [],
    "trustedClientCertificates": [],
    "trustedRootCertificates": [],
    "urlPathMaps": []
  }
}
 ```


# Tworzenie zestawu skalowania maszyn wirtualnych 

Poniższe polecenie tworzy strefowo nadmiarowy zestaw skalowania maszyn wirtualnych (VMSS) w grupie zasobów $MY_RESOURCE_GROUP_NAME. Integrujemy usługę Application Gateway, która została utworzona w poprzednim kroku. To polecenie tworzy 2 maszyny wirtualne jednostki SKU Standard_DS2_v2 z publicznym adresem IP w podsieci $MY_VM_SN_NAME. Klucz SSH zostanie utworzony w poniższym kroku, aby zapisać klucz, jeśli musisz zalogować się do maszyn wirtualnych za pośrednictwem protokołu SSH.

```bash
az vmss create --name $MY_VMSS_NAME --resource-group $MY_RESOURCE_GROUP_NAME --image $MY_VM_IMAGE --admin-username $MY_USERNAME --generate-ssh-keys --public-ip-per-vm --orchestration-mode Uniform --instance-count 2 --zones 1 2 3 --vnet-name $MY_VNET_NAME --subnet $MY_VM_SN_NAME --vm-sku Standard_DS2_v2 --upgrade-policy-mode Automatic --app-gateway $MY_APPGW_NAME --backend-pool-name appGatewayBackendPool -o JSON
 ```

Wyniki:

<!-- expected_similarity=0.3 -->
```json  
{
  "vmss": {
    "doNotRunExtensionsOnOverprovisionedVMs": false,
    "orchestrationMode": "Uniform",
    "overprovision": true,
    "platformFaultDomainCount": 1,
    "provisioningState": "Succeeded",
    "singlePlacementGroup": false,
    "timeCreated": "20xx-xx-xxTxx:xx:xx.xxxxxx+00:00",
    "uniqueId": "xxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxx",
    "upgradePolicy": {
      "mode": "Automatic",
      "rollingUpgradePolicy": {
        "maxBatchInstancePercent": 20,
        "maxSurge": false,
        "maxUnhealthyInstancePercent": 20,
        "maxUnhealthyUpgradedInstancePercent": 20,
        "pauseTimeBetweenBatches": "PT0S",
        "rollbackFailedInstancesOnPolicyBreach": false
      }
    },
    "virtualMachineProfile": {
      "networkProfile": {
        "networkInterfaceConfigurations": [
          {
            "name": "myvmsa53cNic",
            "properties": {
              "disableTcpStateTracking": false,
              "dnsSettings": {
                "dnsServers": []
              },
              "enableAcceleratedNetworking": false,
              "enableIPForwarding": false,
              "ipConfigurations": [
                {
                  "name": "myvmsa53cIPConfig",
                  "properties": {
                    "applicationGatewayBackendAddressPools": [
                      {
                        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxx/providers/Microsoft.Network/applicationGateways/myAPPGW7xxxxx/backendAddressPools/appGatewayBackendPool",   
                        "resourceGroup": "myVMSSResourceGroupxxxxxx"
                      }
                    ],
                    "privateIPAddressVersion": "IPv4",
                    "publicIPAddressConfiguration": {
                      "name": "instancepublicip",
                      "properties": {
                        "idleTimeoutInMinutes": 10,
                        "ipTags": [],
                        "publicIPAddressVersion": "IPv4"
                      }
                    },
                    "subnet": {
                      "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxx/providers/Microsoft.Network/virtualNetworks/myVNetxxxxx/subnets/myVMSN7xxxxx",
                      "resourceGroup": "myVMSSResourceGroupxxxxxxx"
                    }
                  }
                }
              ],
              "primary": true
            }
          }
        ]
      },
      "osProfile": {
        "adminUsername": "azureuser",
        "allowExtensionOperations": true,
        "computerNamePrefix": "myvmsa53c",
        "linuxConfiguration": {
          "disablePasswordAuthentication": true,
          "enableVMAgentPlatformUpdates": false,
          "provisionVMAgent": true,
          "ssh": {
            "publicKeys": [
              {
                "keyData": "ssh-rsa xxxxxxxx",
                "path": "/home/azureuser/.ssh/authorized_keys"
              }
            ]
          }
        },
        "requireGuestProvisionSignal": true,
        "secrets": []
      },
      "storageProfile": {
        "diskControllerType": "SCSI",
        "imageReference": {
          "offer": "0001-com-ubuntu-server-jammy",
          "publisher": "Canonical",
          "sku": "22_04-lts-gen2",
          "version": "latest"
        },
        "osDisk": {
          "caching": "ReadWrite",
          "createOption": "FromImage",
          "diskSizeGB": 30,
          "managedDisk": {
            "storageAccountType": "Premium_LRS"
          },
          "osType": "Linux"
        }
      },
      "timeCreated": "20xx-xx-xxTxx:xx:xx.xxxxxx+00:00"
    },
    "zoneBalance": false
  }
}
```

### Instalowanie rozwiązania ngnix przy użyciu rozszerzeń zestawu skalowania maszyn wirtualnych 

Poniższe polecenie używa rozszerzenia VMSS do uruchamiania skryptu niestandardowego. Na potrzeby testowania zainstalujemy usługę ngnix i opublikujemy stronę zawierającą nazwę hosta maszyny wirtualnej, która napotka żądania HTTP. Ten skrypt niestandardowy jest używany dla tego repozytorium: https://raw.githubusercontent.com/Azure-Samples/compute-automation-configurations/master/automate_nginx.sh 


```bash
az vmss extension set --publisher Microsoft.Azure.Extensions --version 2.0  --name CustomScript --resource-group $MY_RESOURCE_GROUP_NAME --vmss-name $MY_VMSS_NAME --settings '{ "fileUris": ["https://raw.githubusercontent.com/Azure-Samples/compute-automation-configurations/master/automate_nginx.sh"], "commandToExecute": "./automate_nginx.sh" }' -o JSON
```

Wyniki:

<!-- expected_similarity=0.3 -->
```json  
{
  "additionalCapabilities": null,
  "automaticRepairsPolicy": null,
  "constrainedMaximumCapacity": null,
  "doNotRunExtensionsOnOverprovisionedVMs": false,
  "extendedLocation": null,
  "hostGroup": null,
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxx/providers/Microsoft.Compute/virtualMachineScaleSets/myVMSSxxxxx",
  "identity": null,
  "location": "eastus",
  "name": "myVMSSxxxx",
  "orchestrationMode": "Uniform",
  "overprovision": true,
  "plan": null,
  "platformFaultDomainCount": 1,
  "priorityMixPolicy": null,
  "provisioningState": "Succeeded",
  "proximityPlacementGroup": null,
  "resourceGroup": "myVMSSResourceGroupxxxxx",
  "scaleInPolicy": null,
  "singlePlacementGroup": false,
  "sku": {
    "capacity": 2,
    "name": "Standard_DS2_v2",
    "tier": "Standard"
  },
  "spotRestorePolicy": null,
  "tags": {},
  "timeCreated": "20xx-xx-xxTxx:xx:xx.xxxxxx+00:00",
  "type": "Microsoft.Compute/virtualMachineScaleSets",
  "uniqueId": "xxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxx",
  "upgradePolicy": {
    "automaticOsUpgradePolicy": null,
    "mode": "Automatic",
    "rollingUpgradePolicy": {
      "enableCrossZoneUpgrade": null,
      "maxBatchInstancePercent": 20,
      "maxSurge": false,
      "maxUnhealthyInstancePercent": 20,
      "maxUnhealthyUpgradedInstancePercent": 20,
      "pauseTimeBetweenBatches": "PT0S",
      "prioritizeUnhealthyInstances": null,
      "rollbackFailedInstancesOnPolicyBreach": false
    }
  },
  "virtualMachineProfile": {
    "applicationProfile": null,
    "billingProfile": null,
    "capacityReservation": null,
    "diagnosticsProfile": null,
    "evictionPolicy": null,
    "extensionProfile": {
      "extensions": [
        {
          "autoUpgradeMinorVersion": true,
          "enableAutomaticUpgrade": null,
          "forceUpdateTag": null,
          "id": null,
          "name": "CustomScript",
          "protectedSettings": null,
          "protectedSettingsFromKeyVault": null,
          "provisionAfterExtensions": null,
          "provisioningState": null,
          "publisher": "Microsoft.Azure.Extensions",
          "settings": {
            "commandToExecute": "./automate_nginx.sh",
            "fileUris": [
              "https://raw.githubusercontent.com/Azure-Samples/compute-automation-configurations/master/automate_nginx.sh"
            ]
          },
          "suppressFailures": null,
          "type": null,
          "typeHandlerVersion": "2.0",
          "typePropertiesType": "CustomScript"
        }
      ],
      "extensionsTimeBudget": null
    },
    "hardwareProfile": null,
    "licenseType": null,
    "networkProfile": {
      "healthProbe": null,
      "networkApiVersion": null,
      "networkInterfaceConfigurations": [
        {
          "deleteOption": null,
          "disableTcpStateTracking": false,
          "dnsSettings": {
            "dnsServers": []
          },
          "enableAcceleratedNetworking": false,
          "enableFpga": null,
          "enableIpForwarding": false,
          "ipConfigurations": [
            {
              "applicationGatewayBackendAddressPools": [
                {
                  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxx/providers/Microsoft.Network/applicationGateways/myAPPGWxxxx/backendAddressPools/appGatewayBackendPool",
                  "resourceGroup": "myVMSSResourceGroupxxxxxx"
                }
              ],
              "applicationSecurityGroups": null,
              "loadBalancerBackendAddressPools": null,
              "loadBalancerInboundNatPools": null,
              "name": "myvmsdxxxIPConfig",
              "primary": null,
              "privateIpAddressVersion": "IPv4",
              "publicIpAddressConfiguration": null,
              "subnet": {
                "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxx/providers/Microsoft.Network/virtualNetworks/myVNetxxxxx/subnets/myVMSNxxxxx",
                "resourceGroup": "myVMSSResourceGroupaxxxxx"
              }
            }
          ],
          "name": "myvmsxxxxxx",
          "networkSecurityGroup": null,
          "primary": true
        }
      ]
    },
    "osProfile": {
      "adminPassword": null,
      "adminUsername": "azureuser",
      "allowExtensionOperations": true,
      "computerNamePrefix": "myvmsdxxx",
      "customData": null,
      "linuxConfiguration": {
        "disablePasswordAuthentication": true,
        "enableVmAgentPlatformUpdates": false,
        "patchSettings": null,
        "provisionVmAgent": true,
        "ssh": {
          "publicKeys": [
            {
              "keyData": "ssh-rsa xxxxxxxx",
              "path": "/home/azureuser/.ssh/authorized_keys"
            }
          ]
        }
      },
      "requireGuestProvisionSignal": true,
      "secrets": [],
      "windowsConfiguration": null
    },
    "priority": null,
    "scheduledEventsProfile": null,
    "securityPostureReference": null,
    "securityProfile": null,
    "serviceArtifactReference": null,
    "storageProfile": {
      "dataDisks": null,
      "diskControllerType": "SCSI",
      "imageReference": {
        "communityGalleryImageId": null,
        "exactVersion": null,
        "id": null,
        "offer": "0001-com-ubuntu-server-jammy",
        "publisher": "Canonical",
        "sharedGalleryImageId": null,
        "sku": "22_04-lts-gen2",
        "version": "latest"
      },
      "osDisk": {
        "caching": "ReadWrite",
        "createOption": "FromImage",
        "deleteOption": null,
        "diffDiskSettings": null,
        "diskSizeGb": 30,
        "image": null,
        "managedDisk": {
          "diskEncryptionSet": null,
          "securityProfile": null,
          "storageAccountType": "Premium_LRS"
        },
        "name": null,
        "osType": "Linux",
        "vhdContainers": null,
        "writeAcceleratorEnabled": null
      }
    },
    "userData": null
  },
  "zoneBalance": false,
  "zones": [
    "1",
    "2",
    "3"
  ]
}
```


# Definiowanie profilu skalowania automatycznego  

Aby włączyć skalowanie automatyczne na zestawie skalowania, najpierw zdefiniuj profil skalowania automatycznego. Ten profil obejmuje definiowanie domyślnej, minimalnej i maksymalnej pojemności zestawu skalowania. Dzięki tym limitom możesz kontrolować koszty, ponieważ wystąpienia maszyn wirtualnych nie są tworzone w sposób ciągły, zaś akceptowalna wydajność jest zrównoważona z minimalną liczbą wystąpień, które pozostają w zdarzeniu skalowania w pionie.
W poniższym przykładzie ustawiono domyślną, minimalną pojemność — 2 — oraz maksymalną pojemność — 10 wystąpień maszyn wirtualnych:

```bash
az monitor autoscale create --resource-group $MY_RESOURCE_GROUP_NAME --resource  $MY_VMSS_NAME --resource-type Microsoft.Compute/virtualMachineScaleSets --name autoscale --min-count 2 --max-count 10 --count 2
```


Wyniki:

<!-- expected_similarity=0.3 -->
```json  
{
  "enabled": true,
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxx/providers/microsoft.insights/autoscalesettings/autoscale",
  "location": "eastus",
  "name": "autoscale",
  "namePropertiesName": "autoscale",
  "notifications": [
    {
      "email": {
        "customEmails": [],
        "sendToSubscriptionAdministrator": false,
        "sendToSubscriptionCoAdministrators": false
      },
      "webhooks": []
    }
  ],
  "predictiveAutoscalePolicy": {
    "scaleLookAheadTime": null,
    "scaleMode": "Disabled"
  },
  "profiles": [
    {
      "capacity": {
        "default": "2",
        "maximum": "10",
        "minimum": "2"
      },
      "fixedDate": null,
      "name": "default",
      "recurrence": null,
      "rules": []
    }
  ],
  "resourceGroup": "myVMSSResourceGroupxxxxx",
  "systemData": null,
  "tags": {},
  "targetResourceLocation": null,
  "targetResourceUri": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxxx/providers/Microsoft.Compute/virtualMachineScaleSets/myVMSSxxxxxx",
  "type": "Microsoft.Insights/autoscaleSettings"
}
```

# Tworzenie reguły skalowania automatycznego w poziomie

Następujące polecenie tworzy regułę, która zwiększa liczbę wystąpień maszyn wirtualnych w zestawie skalowania, gdy średnie obciążenie procesora CPU jest większe niż 70% w okresie 5 minut. Wyzwolenie reguły powoduje zwiększenie liczby wystąpień maszyn wirtualnych o trzy.

```bash
az monitor autoscale rule create --resource-group $MY_RESOURCE_GROUP_NAME --autoscale-name autoscale --condition "Percentage CPU > 70 avg 5m" --scale out 3
```

Wyniki:

<!-- expected_similarity=0.3 -->
```json 
{
  "metricTrigger": {
    "dimensions": [],
    "dividePerInstance": null,
    "metricName": "Percentage CPU",
    "metricNamespace": null,
    "metricResourceLocation": null,
    "metricResourceUri": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxxx/providers/Microsoft.Compute/virtualMachineScaleSets/myVMSSxxxxxx",
    "operator": "GreaterThan",
    "statistic": "Average",
    "threshold": "70",
    "timeAggregation": "Average",
    "timeGrain": "PT1M",
    "timeWindow": "PT5M"
  },
  "scaleAction": {
    "cooldown": "PT5M",
    "direction": "Increase",
    "type": "ChangeCount",
    "value": "3"
  }
} 
```

# Tworzenie reguły skalowania automatycznego w pionie

Za pomocą polecenia az monitor autoscale rule create utwórz inną regułę, która zmniejsza liczbę wystąpień maszyn wirtualnych w zestawie skalowania, jeśli w okresie 5 minut średnie obciążenie procesora CPU spadnie poniżej 30%. W poniższym przykładzie zdefiniowano regułę umożliwiającą skalowanie w pionie liczby wystąpień maszyn wirtualnych o jeden.

```bash
az monitor autoscale rule create --resource-group  $MY_RESOURCE_GROUP_NAME --autoscale-name autoscale --condition "Percentage CPU < 30 avg 5m" --scale in 1
```

Wyniki:

<!-- expected_similarity=0.3 -->
```json 
{
  "metricTrigger": {
    "dimensions": [],
    "dividePerInstance": null,
    "metricName": "Percentage CPU",
    "metricNamespace": null,
    "metricResourceLocation": null,
    "metricResourceUri": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMSSResourceGroupxxxxxx/providers/Microsoft.Compute/virtualMachineScaleSets/myVMSSxxxxxx",
    "operator": "LessThan",
    "statistic": "Average",
    "threshold": "30",
    "timeAggregation": "Average",
    "timeGrain": "PT1M",
    "timeWindow": "PT5M"
  },
  "scaleAction": {
    "cooldown": "PT5M",
    "direction": "Decrease",
    "type": "ChangeCount",
    "value": "1"
  }
}
```


### Testowanie strony

Poniższe polecenie pokazuje publiczny adres IP usługi Application Gateway. Adresy IP można wkleić do strony przeglądarki na potrzeby testowania.

```bash
az network public-ip show --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_APPGW_PUBLIC_IP_NAME --query [ipAddress]  --output tsv
```



# Informacje

* [Dokumentacja usługi VMSS](https://learn.microsoft.com/en-us/azure/virtual-machine-scale-sets/overview)
* [Skalowanie automatyczne w usłudze VMSS](https://learn.microsoft.com/en-us/azure/virtual-machine-scale-sets/tutorial-autoscale-cli?tabs=Ubuntu)

