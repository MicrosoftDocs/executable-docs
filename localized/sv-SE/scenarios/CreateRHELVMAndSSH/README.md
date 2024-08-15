---
title: 'Snabbstart: Använda Azure CLI för att skapa en virtuell Red Hat Enterprise Linux-dator'
description: I den här snabbstarten får du lära dig hur du använder Azure CLI för att skapa en virtuell Red Hat Enterprise Linux-dator
author: namanparikh
ms.service: virtual-machines
ms.collection: linux
ms.topic: quickstart
ms.date: 05/03/2024
ms.author: namanparikh
ms.custom: 'mvc, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Snabbstart: Skapa en virtuell Red Hat Enterprise Linux-dator med Azure CLI på Azure

**Gäller för:** :heavy_check_mark: Virtuella Linux-datorer

[![Distribuera till Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262692)

Den här snabbstarten visar hur du använder Azure CLI för att distribuera en virtuell Red Hat Enterprise Linux-dator (VM) i Azure. Azure CLI används för att skapa och hantera Azure-resurser via antingen kommandoraden eller skripten.

Om du inte har någon Azure-prenumeration skapar du ett [kostnadsfritt konto](https://azure.microsoft.com/free/?WT.mc_id=A261C142F) innan du börjar.

## Starta Azure Cloud Shell

Azure Cloud Shell är ett interaktivt gränssnitt som du kan använda för att utföra stegen i den här artikeln. Den har vanliga Azure-verktyg förinstallerat och har konfigurerats för användning med ditt konto. 

Om du vill öppna Cloud Shell väljer du bara **Prova** från det övre högra hörnet i ett kodblock. Du kan också öppna Cloud Shell på en separat webbläsarflik genom att gå till [https://shell.azure.com/bash](https://shell.azure.com/bash). Välj **Kopiera** för att kopiera kodblocken, klistra in det i Cloud Shell och välj **Retur** för att köra det.

Om du föredrar att installera och använda detta CLI lokalt måste du köra Azure CLI version 2.0.30 eller senare. Kör `az --version` för att hitta versionen. Om du behöver installera eller uppgradera kan du läsa [Installera Azure CLI]( /cli/azure/install-azure-cli).

## Definiera miljövariabler

Det första steget är att definiera miljövariablerna. Miljövariabler används ofta i Linux för att centralisera konfigurationsdata för att förbättra systemets konsekvens och underhåll. Skapa följande miljövariabler för att ange namnen på de resurser som du skapar senare i den här självstudien:

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="RedHat:RHEL:8-LVM:latest"
```

## Logga in på Azure med hjälp av CLI

För att kunna köra kommandon i Azure med hjälp av CLI måste du logga in först. Logga in med kommandot `az login` .

## Skapa en resursgrupp

En resursgrupp är en container för relaterade resurser. Alla resurser måste placeras i en resursgrupp. Kommandot [az group create](/cli/azure/group) skapar en resursgrupp med de tidigare definierade parametrarna $MY_RESOURCE_GROUP_NAME och $REGION.

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

Om du vill skapa en virtuell dator i den här resursgruppen använder du `vm create` kommandot . 

I följande exempel skapas en virtuell dator och ett användarkonto läggs till. Parametern `--generate-ssh-keys` gör att CLI söker efter en tillgänglig ssh-nyckel i `~/.ssh`. Om en hittas används den nyckeln. Annars genereras och lagras en i `~/.ssh`. Parametern `--public-ip-sku Standard` säkerställer att datorn är tillgänglig via en offentlig IP-adress. Slutligen distribuerar vi den senaste `Ubuntu 22.04` avbildningen.

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

Det tar några minuter att skapa den virtuella datorn och stödresurser. Utdataresultatet i följande exempel anger att den virtuella datorn har skapats.

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

## Aktivera Azure AD-inloggning för en virtuell Linux-dator i Azure

Följande kodexempel distribuerar en virtuell Linux-dator och installerar sedan tillägget för att aktivera en Azure AD-inloggning för en virtuell Linux-dator. VM-tillägg är små program som tillhandahåller konfigurations- och automatiseringsuppgifter efter distributionen på virtuella Azure-datorer.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

## Lagra IP-adressen för den virtuella datorn för att SSH

Kör följande kommando för att lagra IP-adressen för den virtuella datorn som en miljövariabel:

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

## SSH till den virtuella datorn

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Log in to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

Nu kan du SSH till den virtuella datorn genom att köra utdata från följande kommando i valfri ssh-klient:

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

## Nästa steg

* [Lär dig mer om virtuella datorer](../index.yml)
* [Använda Cloud-Init för att initiera en virtuell Linux-dator vid första starten](tutorial-automate-vm-deployment.md)
* [Skapa anpassade avbildningar av en virtuell dator](tutorial-custom-images.md)
* [Belastningsutjämning av virtuella datorer](../../load-balancer/quickstart-load-balancer-standard-public-cli.md)
