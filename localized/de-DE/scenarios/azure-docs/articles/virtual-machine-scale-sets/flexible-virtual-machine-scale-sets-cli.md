---
title: Erstellen von VMs in einer flexiblen Skalierungsgruppe mit Azure CLI
description: 'Erfahren Sie, wie Sie im Orchestrierungsmodus „Flexibel“ eine VM-Skalierungsgruppe im Azure-CLI erstellen.'
author: fitzgeraldsteele
ms.author: fisteele
ms.topic: how-to
ms.service: virtual-machine-scale-sets
ms.date: 3/19/2024
ms.reviewer: jushiman
ms.custom: 'mimckitt, devx-track-azurecli, vmss-flex, innovation-engine, linux-related-content'
---

# Erstellen von VMs in einer Skalierungsgruppe mit der Azure CLI

[![Bereitstellung in Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262759)

In diesem Artikel wird beschrieben, wie Sie mithilfe der Azure CLI eine VM-Skalierungsgruppe erstellen.

Achten Sie darauf, dass Sie die aktuelle Version der [Azure CLI](/cli/azure/install-az-cli2) installiert haben und mit [az login](/cli/azure/reference-index) bei einem Azure-Konto angemeldet sind.


## Starten von Azure Cloud Shell

Azure Cloud Shell ist eine kostenlose interaktive Shell, mit der Sie die Schritte in diesem Artikel durchführen können. Sie verfügt über allgemeine vorinstallierte Tools und ist für die Verwendung mit Ihrem Konto konfiguriert.

Wählen Sie zum Öffnen von Cloud Shell oben rechts in einem Codeblock einfach die Option **Cloud Shell öffnen** aus. Sie können Cloud Shell auch auf einem separaten Browsertab starten, indem Sie zu [https://shell.azure.com/cli](https://shell.azure.com/cli) navigieren. Wählen Sie **Kopieren**, um die Blöcke mit dem Code zu kopieren. Fügen Sie ihn anschließend in Cloud Shell ein, und drücken Sie die EINGABETASTE, um ihn auszuführen.

## Definieren von Umgebungsvariablen

Definieren Sie Umgebungsvariablen wie folgt.

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

## Erstellen einer Ressourcengruppe

Eine Ressourcengruppe ist ein logischer Container, in dem Azure-Ressourcen bereitgestellt und verwaltet werden. Alle Ressourcen müssen in einer Ressourcengruppe platziert werden. Mit dem folgenden Befehl wird eine Ressourcengruppe mit den zuvor definierten Parametern $MY_RESOURCE_GROUP_NAME und $REGION erstellt.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION -o JSON
```

Ergebnisse:
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

## Erstellen von Netzwerkressourcen 

Jetzt erstellen Sie Netzwerkressourcen. In diesem Schritt erstellen Sie ein virtuelles Netzwerk, ein Subnetz für Anwendungsgateway und ein Subnetz für VMs. Sie benötigen außerdem eine öffentliche IP-Adresse, an die sie Ihr Application Gateway anfügen können, um Ihre Webanwendung über das Internet zu erreichen. 

#### Erstellen eines virtuellen Netzwerks und Subnetzes

```bash
az network vnet create  --name $MY_VNET_NAME  --resource-group $MY_RESOURCE_GROUP_NAME --location $REGION  --address-prefix $MY_VNET_PREFIX  --subnet-name $MY_VM_SN_NAME --subnet-prefix $MY_VM_SN_PREFIX -o JSON
```

Ergebnisse:
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

### Erstellen von Application Gateway-Ressourcen

Azure Application Gateway benötigt innerhalb Ihres virtuellen Netzwerks ein dediziertes Subnetz. Der folgende Befehl erstellt ein Subnetz namens „$MY_APPGW_SN_NAME“ mit einem angegebenen Adresspräfix „$MY_APPGW_SN_PREFIX“ in Ihrem virtuellen Netzwerk „$MY_VNET_NAME“.

```bash
az network vnet subnet create  --name $MY_APPGW_SN_NAME  --resource-group $MY_RESOURCE_GROUP_NAME --vnet-name  $MY_VNET_NAME --address-prefix  $MY_APPGW_SN_PREFIX -o JSON
```

Ergebnisse:
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
Mit dem folgenden Befehl wird eine standardmäßige, zonenredundante, statische, öffentliche IPv4-Adresse in Ihrer Ressourcengruppe erstellt.  

```bash
az network public-ip create  --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_APPGW_PUBLIC_IP_NAME --sku Standard   --location $REGION  --allocation-method static --version IPv4 --zone 1 2 3 -o JSON
```

Ergebnisse:
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

In diesem Schritt erstellen Sie ein Application Gateway, das Sie in Ihre VM-Skalierungsgruppe integrieren werden. In diesem Beispiel wird ein zonenredundantes Application Gateway mit einer Standard_v2-SKU erstellt und die HTTP-Kommunikation für das Application Gateway aktiviert. Die öffentliche IP-Adresse „$MY_APPGW_PUBLIC_IP_NAME“, die im vorherigen Schritt erstellt wurde, wird an das Application Gateway angefügt. 

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

## Erstellen einer VM-Skalierungsgruppe

> [!IMPORTANT]
>Ab November 2023 werden VM-Skalierungsgruppen, die mit PowerShell und der Azure CLI erstellt wurden, standardmäßig auf den flexiblen Orchestrierungsmodus festgelegt, wenn kein Orchestrierungsmodus angegeben wird. Weitere Informationen zu dieser Änderung und zu den Maßnahmen, die Sie ergreifen sollten, finden Sie unter [Breaking Change für PowerShell-/CLI-Kunden mit VMSS – Microsoft Community Hub](
https://techcommunity.microsoft.com/t5/azure-compute-blog/breaking-change-for-vmss-powershell-cli-customers/ba-p/3818295).

Erstellen Sie dann mit [az vmss create](/cli/azure/vmss) eine VM-Skalierungsgruppe. Im folgenden Beispiel wird ein zonenredundanter Skalierungssatz mit einer Instanzanzahl von *2* mit öffentlicher IP in Subnetz-$MY_VM_SN_NAME in Ihrer Ressourcengruppe $MY_RESOURCE_GROUP_NAME erstellt, das Anwendungsgateway integriert und SSH-Schlüssel generiert. Achten Sie darauf, die SSH-Schlüssel zu speichern, wenn Sie sich über SSH bei Ihren virtuellen Computern anmelden müssen.

```bash
az vmss create --name $MY_VMSS_NAME --resource-group $MY_RESOURCE_GROUP_NAME --image $MY_VM_IMAGE --admin-username $MY_USERNAME --generate-ssh-keys --public-ip-per-vm --orchestration-mode Uniform --instance-count 2 --zones 1 2 3 --vnet-name $MY_VNET_NAME --subnet $MY_VM_SN_NAME --vm-sku Standard_DS2_v2 --upgrade-policy-mode Automatic --app-gateway $MY_APPGW_NAME --backend-pool-name appGatewayBackendPool -o JSON
 ```

Ergebnisse:
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

### Installieren von ngnix mit Erweiterungen für Virtual Machine Scale Sets 

Der folgende Befehl verwendet die Erweiterung für Virtual Machine Scale Sets zum Ausführen eines [benutzerdefinierten Skripts](https://github.com/Azure-Samples/compute-automation-configurations/blob/master/automate_nginx.sh), das ngnix installiert und eine Seite veröffentlicht, die den Hostnamen der VM anzeigt, auf den Ihre HTTP-Anforderungen zugeht. 

```bash
az vmss extension set --publisher Microsoft.Azure.Extensions --version 2.0  --name CustomScript --resource-group $MY_RESOURCE_GROUP_NAME --vmss-name $MY_VMSS_NAME --settings '{ "fileUris": ["https://raw.githubusercontent.com/Azure-Samples/compute-automation-configurations/master/automate_nginx.sh"], "commandToExecute": "./automate_nginx.sh" }' -o JSON
```

Ergebnisse:
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

## Definieren eines Profils für die automatische Skalierung  

Zum Aktivieren der automatischen Skalierung für eine Skalierungsgruppe legen Sie zuerst ein Profil für die automatische Skalierung fest. Dieses Profil definiert die standardmäßige, minimale und maximale Kapazität der Skalierungsgruppe. Diese Grenzwerte sind hilfreich bei der Kostenkontrolle und sorgen nicht nur dafür, dass nicht fortlaufend VM-Instanzen erstellt werden, sondern gewährleisten auch ein ausgewogenes Verhältnis zwischen angemessener Leistung und einer minimalen Anzahl von Instanzen, die beim horizontalen Herunterskalieren erhalten bleiben.
Im folgenden Beispiel werden die Standardkapazität, die Mindestkapazität von zwei VM-Instanzen und eine maximale Kapazität von 10 festgelegt:

```bash
az monitor autoscale create --resource-group $MY_RESOURCE_GROUP_NAME --resource  $MY_VMSS_NAME --resource-type Microsoft.Compute/virtualMachineScaleSets --name autoscale --min-count 2 --max-count 10 --count 2
```

Ergebnisse:
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

## Erstellen einer Regel zum automatischen Aufskalieren

Der folgende Befehl erstellt eine Regel, welche die Anzahl von VM-Instanzen in einer Skalierungsgruppe erhöht, wenn die durchschnittliche CPU-Last fünf Minuten lang über 70 % liegt. Wenn die Regel ausgelöst wird, wird die Anzahl von VM-Instanzen um 3 erhöht.

```bash
az monitor autoscale rule create --resource-group $MY_RESOURCE_GROUP_NAME --autoscale-name autoscale --condition "Percentage CPU > 70 avg 5m" --scale out 3
```

Ergebnisse:
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

## Erstellen einer Regel zum automatischen Abskalieren

Erstellen Sie eine weitere Regel mit `az monitor autoscale rule create`, mit der die Anzahl von VM-Instanzen in einer Skalierungsgruppe verringert wird, wenn die durchschnittliche CPU-Last fünf Minuten lang unter 30% fällt. Im folgenden Beispiel wird die Regel zum horizontalen Herunterskalieren der Anzahl von VM-Instanzen um 1 definiert.

```bash
az monitor autoscale rule create --resource-group  $MY_RESOURCE_GROUP_NAME --autoscale-name autoscale --condition "Percentage CPU < 30 avg 5m" --scale in 1
```

Ergebnisse:
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

### Testen der Seite

Der folgende Befehl zeigt die öffentliche IP-Adresse Ihres Application Gateways. Fügen Sie die IP-Adresse zu Testzwecken in eine Browserseite ein.

```bash
az network public-ip show --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_APPGW_PUBLIC_IP_NAME --query [ipAddress]  --output tsv
```

## Bereinigen von Ressourcen (optional)

Zum Vermeiden von Azure-Gebühren sollten Sie nicht benötigte Ressourcen bereinigen. Wenn Sie ihren Skalierungssatz und andere Ressourcen nicht mehr benötigen, löschen Sie die Ressourcengruppe und alle zugehörigen Ressourcen mit [az group delete](/cli/azure/group). Der Parameter `--no-wait` gibt die Steuerung an die Eingabeaufforderung zurück, ohne zu warten, bis der Vorgang abgeschlossen ist. Der Parameter `--yes` bestätigt, dass Sie die Ressourcen ohne weitere Aufforderung löschen möchten. In diesem Tutorial werden Ressourcen für Sie bereinigt.

## Nächste Schritte
- [Erfahren Sie, wie Sie eine Skalierungsgruppe im Azure-Portal erstellen.](flexible-virtual-machine-scale-sets-portal.md)
- [Informationen zu Virtual Machine Scale Sets.](overview.md)
- [Automatisches Skalieren einer VM-Skalierungsgruppe mit Azure CLI](tutorial-autoscale-cli.md)
