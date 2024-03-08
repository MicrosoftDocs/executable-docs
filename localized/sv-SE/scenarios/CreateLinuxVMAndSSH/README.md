---
title: Skapa en virtuell Linux-dator och SSH på Azure
description: Den här självstudien visar hur du skapar en virtuell Linux-dator och SSH på Azure.
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Skapa en virtuell Linux-dator och SSH på Azure

[![Distribuera till Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateLinuxVMAndSSH)


## Definiera miljövariabler

Det första steget i den här självstudien är att definiera miljövariabler.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
```

# Logga in på Azure med HJÄLP av CLI

För att kunna köra kommandon mot Azure med hjälp av CLI måste du logga in. Detta görs, mycket enkelt, men `az login` kommandot:

# Skapa en resursgrupp

En resursgrupp är en container för relaterade resurser. Alla resurser måste placeras i en resursgrupp. Vi skapar en för den här självstudien. Följande kommando skapar en resursgrupp med de tidigare definierade parametrarna $MY_RESOURCE_GROUP_NAME och $REGION.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Resultat:

<!-- expected_similarity=0.3 -->
```json   
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMResourceGroup",
  "location": "eastus",
  "managedBy": null,
  "name": "myVMResourceGroup",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Skapa den virtuella datorn

För att skapa en virtuell dator i den här resursgruppen måste vi köra ett enkelt kommando. Här har vi angett `--generate-ssh-keys` flaggan, vilket gör att CLI söker efter en avialable ssh-nyckel i `~/.ssh`, om en hittas kommer den att användas, annars genereras och lagras i `~/.ssh`. Vi tillhandahåller `--public-ip-sku Standard` också flaggan för att säkerställa att datorn är tillgänglig via en offentlig IP-adress. Slutligen distribuerar vi den senaste `Ubuntu 22.04` avbildningen. 

Alla andra värden konfigureras med hjälp av miljövariabler.

```bash
az vm create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_VM_NAME \
    --image $MY_VM_IMAGE \
    --admin-username $MY_USERNAME \
    --assign-identity \
    --generate-ssh-keys \
    --public-ip-sku Standard
```

Resultat:

<!-- expected_similarity=0.3 -->
```json
{
  "fqdns": "",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMResourceGroup/providers/Microsoft.Compute/virtualMachines/myVM",
  "location": "eastus",
  "macAddress": "00-0D-3A-10-4F-70",
  "powerState": "VM running",
  "privateIpAddress": "10.0.0.4",
  "publicIpAddress": "52.147.208.85",
  "resourceGroup": "myVMResourceGroup",
  "zones": ""
}
```

### Aktivera Azure AD-inloggning för en virtuell Linux-dator i Azure

Följande exempel har distribuerat en virtuell Linux-dator och installerar sedan tillägget för att aktivera Azure AD-inloggning för en virtuell Linux-dator. VM-tillägg är små program som tillhandahåller konfigurations- och automatiseringsuppgifter efter distributionen på virtuella Azure-datorer.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

# Lagra IP-adressen för den virtuella datorn för att kunna SSH
kör följande kommando för att hämta IP-adressen för den virtuella datorn och lagra den som en miljövariabel

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

# SSH till virtuell dator

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Login to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

Nu kan du SSH till den virtuella datorn genom att köra utdata från följande kommando i valfri ssh-klient

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

# Nästa steg

* [Dokumentation om virtuella datorer](https://learn.microsoft.com/azure/virtual-machines/)
* [Använda Cloud-Init för att initiera en virtuell Linux-dator vid första starten](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-automate-vm-deployment)
* [Skapa anpassade avbildningar av en virtuell dator](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-custom-images)
* [Belastningsutjämning av virtuella datorer](https://learn.microsoft.com/azure/load-balancer/quickstart-load-balancer-standard-public-cli)
