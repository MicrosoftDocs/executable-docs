---
title: Erstellen einer virtuellen Linux-VM und SSH in Azure
description: 'In diesem Tutorial erfahren Sie, wie Sie eine Linux-VM und SSH in Azure erstellen.'
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Erstellen einer virtuellen Linux-VM und SSH in Azure

[![Bereitstellung in Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateLinuxVMAndSSH)


## Umgebungsvariablen definieren

Der erste Schritt in diesem Tutorial besteht darin, Umgebungsvariablen zu definieren.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
```

# Anmelden bei Azure mit der CLI

Um Befehle für Azure mithilfe der CLI auszuführen, müssen Sie sich anmelden. Dies geschieht ganz einfach mit dem Befehl `az login`:

# Erstellen einer Ressourcengruppe

Eine Ressourcengruppe ist ein Container für zugehörige Ressourcen. Alle Ressourcen müssen in einer Ressourcengruppe platziert werden. In diesem Tutorial erstellen wir eine Ressourcengruppe. Mit dem folgenden Befehl wird eine Ressourcengruppe mit den zuvor definierten Parametern $MY_RESOURCE_GROUP_NAME und $REGION erstellt.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Ergebnisse:

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

## Erstellen des virtuellen Computers

Um einen virtuellen Computer in dieser Ressourcengruppe zu erstellen, muss ein einfacher Befehl ausgeführt werden. Hier wurde das `--generate-ssh-keys`-Flag bereitgestellt. Dies führt dazu, dass die CLI nach einem verfügbaren SSH-Schlüssel in `~/.ssh` sucht. Wenn einer gefunden wird, wird er verwendet, andernfalls wird einer generiert und in `~/.ssh` gespeichert. Außerdem wird das `--public-ip-sku Standard`-Flag bereitgestellt, um sicherzustellen, dass der Computer über eine öffentliche IP-Adresse zugänglich ist. Schließlich wird das neueste `Ubuntu 22.04`-Image bereitgestellt. 

Alle anderen Werte werden mithilfe von Umgebungsvariablen konfiguriert.

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

Ergebnisse:

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

### Aktivieren der Azure AD-Anmeldung für eine Linux-VM in Azure

Im folgenden Beispiel wird eine Linux-VM bereitgestellt und dann die Erweiterung installiert, um die Azure AD-Anmeldung für eine Linux-VM zu aktivieren. VM-Erweiterungen sind kleine Anwendungen, die Konfigurations- und Automatisierungsaufgaben auf virtuellen Azure-Computern nach der Bereitstellung ermöglichen.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

# Speichern der IP-Adresse der VM, damit SSH
den folgenden Befehl ausführt, um die IP-Adresse des virtuellen Computers abzurufen und als Umgebungsvariable zu speichern

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

# SSH für VM

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Login to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

Sie können nun SSH auf der VM ausführen, indem Sie die Ausgabe des folgenden Befehls in Ihrem SSH-Client ausführen.

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

# Nächste Schritte

* [VM-Dokumentation](https://learn.microsoft.com/azure/virtual-machines/)
* [Verwenden von Cloud-Init zum Initialisieren einer Linux-VM beim ersten Start](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-automate-vm-deployment)
* [Erstellen von benutzerdefinierten VM-Images](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-custom-images)
* [Lastenausgleich für virtuelle Computer](https://learn.microsoft.com/azure/load-balancer/quickstart-load-balancer-standard-public-cli)
