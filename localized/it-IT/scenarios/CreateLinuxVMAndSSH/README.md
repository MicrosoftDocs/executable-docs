---
title: Creare una macchina virtuale Linux e SSH in Azure
description: Questa esercitazione illustra come creare una macchina virtuale Linux e SSH in Azure.
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Creare una macchina virtuale Linux e SSH in Azure

[![Distribuzione in Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/?Microsoft_Azure_CloudNative_clientoptimizations=false&feature.canmodifyextensions=true#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateLinuxVMAndSSH)


## Definire le variabili di ambiente

Il primo passaggio di questa esercitazione consiste nel definire le variabili di ambiente.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
```

# Accedere ad Azure usando l'interfaccia della riga di comando

Per eseguire i comandi in Azure usando l'interfaccia della riga di comando di cui è necessario accedere. Questa operazione viene eseguita, molto semplicemente, anche se il `az login` comando :

# Creare un gruppo di risorse

Un gruppo di risorse è un contenitore per le risorse correlate. Tutte le risorse devono essere inserite in un gruppo di risorse. Ne verrà creata una per questa esercitazione. Il comando seguente crea un gruppo di risorse con i parametri $MY_RESOURCE_GROUP_NAME definiti in precedenza e $REGION.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Risultati:

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

## Creare la macchina virtuale

Per creare una macchina virtuale in questo gruppo di risorse, è necessario eseguire un comando semplice, in questo caso è stato fornito il `--generate-ssh-keys` flag, in questo modo l'interfaccia della riga di comando cercherà una chiave SSH avialable in `~/.ssh`, se ne verrà trovata una, altrimenti ne verrà generata e archiviata in `~/.ssh`. Viene inoltre fornito il `--public-ip-sku Standard` flag per assicurarsi che il computer sia accessibile tramite un indirizzo IP pubblico. Infine, viene distribuita l'immagine più recente `Ubuntu 22.04` . 

Tutti gli altri valori vengono configurati usando le variabili di ambiente.

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

Risultati:

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

### Abilitare l'accesso di Azure AD per una macchina virtuale Linux in Azure

L'esempio seguente distribuisce una macchina virtuale Linux e quindi installa l'estensione per abilitare l'accesso di Azure AD per una macchina virtuale Linux. Le estensioni della macchina virtuale sono piccole applicazioni che eseguono attività di configurazione e automazione post-distribuzione nelle macchine virtuali di Azure.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

# Archiviare l'indirizzo IP della macchina virtuale per ssh
eseguire il comando seguente per ottenere l'indirizzo IP della macchina virtuale e archiviarlo come variabile di ambiente

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

# SSH in una macchina virtuale

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Login to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

È ora possibile eseguire SSH nella macchina virtuale eseguendo l'output del comando seguente nel client SSH scelto

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

# Passaggi successivi

* [Documentazione della macchina virtuale](https://learn.microsoft.com/azure/virtual-machines/)
* [Usare Cloud-Init per inizializzare una macchina virtuale Linux al primo avvio](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-automate-vm-deployment)
* [Creare un'immagine di VM personalizzata](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-custom-images)
* [Bilanciare il carico delle macchine virtuali](https://learn.microsoft.com/azure/load-balancer/quickstart-load-balancer-standard-public-cli)
