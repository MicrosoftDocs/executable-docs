---
title: Een Virtuele Linux-machine en SSH maken in Azure
description: Deze zelfstudie laat zien hoe u een Virtuele Linux-machine en SSH maakt in Azure.
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Een Virtuele Linux-machine en SSH maken in Azure

[![Implementeren naar Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateLinuxVMAndSSH)


## Omgevingsvariabelen definiëren

De eerste stap in deze zelfstudie is het definiëren van omgevingsvariabelen.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
```

# Aanmelden bij Azure met behulp van de CLI

Als u opdrachten wilt uitvoeren voor Azure met behulp van de CLI, moet u zich aanmelden. Dit wordt gedaan, heel eenvoudig, hoewel de `az login` opdracht:

# Een brongroep maken

Een resourcegroep is een container voor gerelateerde resources. Alle resources moeten in een resourcegroep worden geplaatst. We maken er een voor deze zelfstudie. Met de volgende opdracht maakt u een resourcegroep met de eerder gedefinieerde parameters $MY_RESOURCE_GROUP_NAME en $REGION parameters.

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

Als u een VIRTUELE machine in deze resourcegroep wilt maken, moet u een eenvoudige opdracht uitvoeren. Hier hebben we de `--generate-ssh-keys` vlag opgegeven. Dit zorgt ervoor dat de CLI zoekt naar een avialable ssh-sleutel in `~/.ssh`, als er een wordt gevonden die wordt gebruikt, anders wordt er een gegenereerd en opgeslagen in `~/.ssh`. We bieden ook de `--public-ip-sku Standard` vlag om ervoor te zorgen dat de machine toegankelijk is via een openbaar IP-adres. Ten slotte implementeren we de nieuwste `Ubuntu 22.04` installatiekopieën. 

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

### Azure AD-aanmelding inschakelen voor een virtuele Linux-machine in Azure

In het volgende voorbeeld wordt een Virtuele Linux-machine geïmplementeerd en vervolgens de extensie geïnstalleerd om Azure AD-aanmelding in te schakelen voor een Virtuele Linux-machine. Extensies van virtuele Azure-machines (VM's) zijn kleine toepassingen die configuratie na de implementatie en automatiseringstaken voor Azure-VM's bieden.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

# IP-adres van vm opslaan in SSH
voer de volgende opdracht uit om het IP-adres van de VIRTUELE machine op te halen en op te slaan als een omgevingsvariabele

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

# SSH in VM

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Login to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

U kunt nu SSH naar de VIRTUELE machine uitvoeren door de uitvoer van de volgende opdracht uit te voeren in uw ssh-client naar keuze

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

# Volgende stappen

* [VM-documentatie](https://learn.microsoft.com/azure/virtual-machines/)
* [Cloud-Init gebruiken om een Linux-VM te initialiseren bij de eerste keer opstarten](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-automate-vm-deployment)
* [Aangepaste VM-installatiekopieën maken](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-custom-images)
* [Taken verdelen over VM's](https://learn.microsoft.com/azure/load-balancer/quickstart-load-balancer-standard-public-cli)
