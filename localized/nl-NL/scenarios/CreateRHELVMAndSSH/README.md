---
title: 'Quickstart: De Azure CLI gebruiken om een virtuele Red Hat Enterprise Linux-machine te maken'
description: In deze quickstart leert u hoe u de Azure CLI gebruikt om een virtuele Red Hat Enterprise Linux-machine te maken
author: namanparikh
ms.service: virtual-machines
ms.collection: linux
ms.topic: quickstart
ms.date: 05/03/2024
ms.author: namanparikh
ms.custom: 'mvc, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Quickstart: Een virtuele Red Hat Enterprise Linux-machine maken met de Azure CLI in Azure

**Van toepassing op:** :heavy_check_mark: Virtuele Linux-machines

[![Implementeren naar Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262692)

In deze quickstart ziet u hoe u de Azure CLI gebruikt om een virtuele Linux-machine (VM) van Red Hat Enterprise te implementeren in Azure. De Azure CLI wordt gebruikt om Azure-resources te maken en te beheren via de opdrachtregel of scripts.

Als u geen Azure-abonnement hebt, maakt u een [gratis account](https://azure.microsoft.com/free/?WT.mc_id=A261C142F) voordat u begint.

## Azure Cloud Shell starten

Azure Cloud Shell is een gratis interactieve shell waarmee u de stappen in dit artikel kunt uitvoeren. In deze shell zijn algemene Azure-hulpprogramma's vooraf geïnstalleerd en geconfigureerd voor gebruik met uw account. 

Als u Cloud Shell wilt openen, selecteert u **Proberen** in de rechterbovenhoek van een codeblok. Als u naar [https://shell.azure.com/bash](https://shell.azure.com/bash) gaat, kunt u Cloud Shell ook openen in een afzonderlijk browsertabblad. Selecteer **Kopiëren** om de codeblokken te kopiëren, plak deze in Cloud Shell en selecteer vervolgens **Enter** om de code uit te voeren.

Als u ervoor kiest om de CLI lokaal te installeren en te gebruiken, hebt u voor deze snelstart versie 2.0.30 of hoger van Azure CLI nodig. Voer `az --version` uit om de versie te bekijken. Als u Azure CLI 2.0 wilt installeren of upgraden, raadpleegt u [Azure CLI 2.0 installeren]( /cli/azure/install-azure-cli).

## Omgevingsvariabelen definiëren

De eerste stap is het definiëren van de omgevingsvariabelen. Omgevingsvariabelen worden vaak gebruikt in Linux om configuratiegegevens te centraliseren om de consistentie en onderhoudbaarheid van het systeem te verbeteren. Maak de volgende omgevingsvariabelen om de namen op te geven van resources die u later in deze zelfstudie maakt:

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="RedHat:RHEL:8-LVM:latest"
```

## Aanmelden bij Azure met behulp van de CLI

Als u opdrachten wilt uitvoeren in Azure met behulp van de CLI, moet u zich eerst aanmelden. Meld u aan met de `az login` opdracht.

## Een brongroep maken

Een resourcegroep is een container voor gerelateerde resources. Alle resources moeten in een resourcegroep worden geplaatst. Met [de opdracht az group create](/cli/azure/group) maakt u een resourcegroep met de eerder gedefinieerde $MY_RESOURCE_GROUP_NAME en $REGION parameters.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Resultaten:

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

## De virtuele machine maken

Gebruik de `vm create` opdracht om een VIRTUELE machine in deze resourcegroep te maken. 

In het volgende voorbeeld wordt een virtuele machine gemaakt en wordt een gebruikersaccount toegevoegd. De `--generate-ssh-keys` parameter zorgt ervoor dat de CLI zoekt naar een beschikbare ssh-sleutel in `~/.ssh`. Als er een wordt gevonden, wordt die sleutel gebruikt. Zo niet, dan wordt er een gegenereerd en opgeslagen in `~/.ssh`. De `--public-ip-sku Standard` parameter zorgt ervoor dat de machine toegankelijk is via een openbaar IP-adres. Ten slotte implementeren we de nieuwste `Ubuntu 22.04` installatiekopieën.

Alle andere waarden worden geconfigureerd met behulp van omgevingsvariabelen.

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

Het maken van de VM en de ondersteunende resources duurt enkele minuten. In het volgende voorbeeld van uitvoer ziet u dat het maken van de virtuele machine is geslaagd.

Resultaten:
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

## Azure AD-aanmelding inschakelen voor een virtuele Linux-machine in Azure

In het volgende codevoorbeeld wordt een Virtuele Linux-machine geïmplementeerd en vervolgens de extensie geïnstalleerd om een Azure AD-aanmelding in te schakelen voor een Virtuele Linux-machine. Extensies van virtuele Azure-machines (VM's) zijn kleine toepassingen die configuratie na de implementatie en automatiseringstaken voor Azure-VM's bieden.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

## IP-adres van de VIRTUELE machine opslaan in SSH

Voer de volgende opdracht uit om het IP-adres van de VIRTUELE machine op te slaan als een omgevingsvariabele:

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

## SSH in de VIRTUELE machine

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Log in to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

U kunt nu SSH naar de virtuele machine uitvoeren door de uitvoer van de volgende opdracht uit te voeren in uw ssh-client naar keuze:

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

## Volgende stappen

* [Meer informatie over virtuele machines](../index.yml)
* [Cloud-Init gebruiken om een Linux-VM te initialiseren bij de eerste keer opstarten](tutorial-automate-vm-deployment.md)
* [Aangepaste VM-installatiekopieën maken](tutorial-custom-images.md)
* [Taken verdelen over VM's](../../load-balancer/quickstart-load-balancer-standard-public-cli.md)
