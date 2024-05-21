---
title: 'Avvio rapido: Usare l''interfaccia della riga di comando di Azure per creare una macchina virtuale Linux'
description: In questa guida introduttiva si apprenderà come usare l'interfaccia della riga di comando di Azure per creare una macchina virtuale Linux
author: ju-shim
ms.service: virtual-machines
ms.collection: linux
ms.topic: quickstart
ms.date: 03/11/2024
ms.author: jushiman
ms.custom: 'mvc, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Avvio rapido: Creare una macchina virtuale Linux con l'interfaccia della riga di comando di Azure in Azure

**Si applica a:** :heavy_check_mark: macchine virtuali Linux

[![Distribuzione in Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262692)

Questa guida introduttiva illustra come usare l'interfaccia della riga di comando di Azure per distribuire in Azure una macchina virtuale Linux. Viene usata l'interfaccia della riga di comando di Azure per creare e gestire le risorse di Azure dalla riga di comando o tramite script.

Se non si ha una sottoscrizione di Azure, creare un [account gratuito](https://azure.microsoft.com/free/?WT.mc_id=A261C142F) prima di iniziare.

## Avviare Azure Cloud Shell

Azure Cloud Shell è una shell interattiva gratuita che può essere usata per eseguire la procedura di questo articolo. Include strumenti comuni di Azure preinstallati e configurati per l'uso con l'account. 

Per aprire Cloud Shell, basta selezionare **Prova** nell'angolo superiore destro di un blocco di codice. È anche possibile aprire Cloud Shell in una scheda separata del browser visitando [https://shell.azure.com/bash](https://shell.azure.com/bash). Selezionare **Copia** per copiare i blocchi di codice, incollarli in Cloud Shell e premere **INVIO** per eseguirli.

Se si preferisce installare e usare l'interfaccia della riga di comando in locale, per questa guida introduttiva è necessaria l'interfaccia della riga di comando di Azure versione 2.0.30 o successiva. Eseguire `az --version` per trovare la versione. Se è necessario eseguire l'installazione o l'aggiornamento, vedere [Installare l'interfaccia della riga di comando di Azure]( /cli/azure/install-azure-cli).

## Definire le variabili di ambiente

Il primo passaggio consiste nel definire le variabili di ambiente. Le variabili di ambiente vengono comunemente usate in Linux per centralizzare i dati di configurazione per migliorare la coerenza e la gestibilità del sistema. Creare le variabili di ambiente seguenti per specificare i nomi delle risorse create più avanti in questa esercitazione:

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
```

## Accedere ad Azure usando l'interfaccia della riga di comando

Per eseguire i comandi in Azure usando l'interfaccia della riga di comando, è prima necessario eseguire l'accesso. Accedere usando il `az login` comando .

## Creare un gruppo di risorse

Un gruppo di risorse è un contenitore per le risorse correlate. Tutte le risorse devono essere inserite in un gruppo di risorse. Il [comando az group create](/cli/azure/group) crea un gruppo di risorse con i parametri definiti in precedenza $MY_RESOURCE_GROUP_NAME e $REGION.

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

Per creare una macchina virtuale in questo gruppo di risorse, usare il `vm create` comando . 

Nell'esempio seguente viene creata una macchina virtuale e aggiunto un account utente. Il `--generate-ssh-keys` parametro fa in modo che l'interfaccia della riga di comando cerchi una chiave SSH disponibile in `~/.ssh`. Se ne viene trovata una, viene usata la chiave. In caso contrario, ne viene generato e archiviato in `~/.ssh`. Il `--public-ip-sku Standard` parametro garantisce che il computer sia accessibile tramite un indirizzo IP pubblico. Infine, viene distribuita l'immagine più recente `Ubuntu 22.04` .

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

La creazione della macchina virtuale e delle risorse di supporto richiede alcuni minuti. L'output di esempio seguente mostra che l'operazione di creazione della macchina virtuale ha avuto esito positivo.

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

## Abilitare l'accesso di Azure AD per una macchina virtuale Linux in Azure

L'esempio di codice seguente distribuisce una macchina virtuale Linux e quindi installa l'estensione per abilitare un account di accesso di Azure AD per una macchina virtuale Linux. Le estensioni della macchina virtuale sono piccole applicazioni che eseguono attività di configurazione e automazione post-distribuzione nelle macchine virtuali di Azure.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

## Archiviare l'indirizzo IP della macchina virtuale per ssh

Eseguire il comando seguente per archiviare l'indirizzo IP della macchina virtuale come variabile di ambiente:

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

## SSH nella macchina virtuale

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Log in to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

È ora possibile eseguire SSH nella macchina virtuale eseguendo l'output del comando seguente nel client SSH scelto:

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

## Passaggi successivi

* [Informazioni sulle macchine virtuali](../index.yml)
* [Usare Cloud-Init per inizializzare una macchina virtuale Linux al primo avvio](tutorial-automate-vm-deployment.md)
* [Creare un'immagine di VM personalizzata](tutorial-custom-images.md)
* [Bilanciare il carico delle macchine virtuali](../../load-balancer/quickstart-load-balancer-standard-public-cli.md)
