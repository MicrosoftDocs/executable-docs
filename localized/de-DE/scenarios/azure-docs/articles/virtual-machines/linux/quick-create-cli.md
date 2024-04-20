---
title: 'Schnellstart: Verwenden der Azure CLI zum Erstellen einer Linux-VM'
description: 'In dieser Schnellstartanleitung erfahren Sie, wie Sie mit Azure CLI einen virtuellen Linux-Computer erstellen.'
author: ju-shim
ms.service: virtual-machines
ms.collection: linux
ms.topic: quickstart
ms.date: 03/11/2024
ms.author: jushiman
ms.custom: 'mvc, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Schnellstart: Erstellen einer Linux-VM mit der Azure CLI auf Azure

**Gilt für**: :heavy_check_mark: Linux-VMs

[![Bereitstellung in Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262692)

In dieser Schnellstartanleitung wird gezeigt, wie Sie mit der Azure CLI einen virtuellen Linux-Computer in Azure bereitstellen. Die Azure-Befehlszeilenschnittstelle dient zum Erstellen und Verwalten von Azure-Ressourcen über die Befehlszeile oder mit Skripts.

Wenn Sie kein Azure-Abonnement besitzen, können Sie ein [kostenloses Konto](https://azure.microsoft.com/free/?WT.mc_id=A261C142F) erstellen, bevor Sie beginnen.

## Starten von Azure Cloud Shell

Azure Cloud Shell ist eine kostenlose interaktive Shell, mit der Sie die Schritte in diesem Artikel durchführen können. Sie verfügt über allgemeine vorinstallierte Tools und ist für die Verwendung mit Ihrem Konto konfiguriert. 

Wählen Sie zum Öffnen von Cloud Shell oben rechts in einem Codeblock einfach die Option **Ausprobieren**. Sie können Cloud Shell auch auf einer separaten Browserregisterkarte öffnen, indem Sie zu [https://shell.azure.com/bash](https://shell.azure.com/bash) navigieren. Wählen Sie **Kopieren** aus, um die Codeblöcke zu kopieren. Fügen Sie die Blöcke anschließend in Cloud Shell ein, und wählen Sie **Eingabe**, um sie auszuführen.

Wenn Sie es vorziehen, die Befehlszeilenschnittstelle lokal zu installieren und zu verwenden, müssen Sie für diese Schnellstartanleitung mindestens Azure CLI-Version 2.0.30 verwenden. Führen Sie `az --version` aus, um die Version zu ermitteln. Informationen zum Durchführen einer Installation oder eines Upgrades finden Sie bei Bedarf unter [Installieren der Azure CLI]( /cli/azure/install-azure-cli).

## Definieren von Umgebungsvariablen

Der erste Schritt besteht darin, die Umgebungsvariablen zu definieren. Umgebungsvariablen werden in Linux häufig verwendet, um Konfigurationsdaten zu zentralisieren und so die Konsistenz und Wartbarkeit des Systems zu verbessern. Erstellen Sie die folgenden Umgebungsvariablen, um die Namen der Ressourcen anzugeben, die Sie später in diesem Tutorial erstellen:

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
```

## Melden Sie sich mit der CLI bei Azure an

Um Befehle in Azure mithilfe der CLI auszuführen, müssen Sie sich zuerst anmelden. Melden Sie sich mit dem Befehl `az login` an.

## Erstellen einer Ressourcengruppe

Eine Ressourcengruppe ist ein Container für zugehörige Ressourcen. Alle Ressourcen müssen in einer Ressourcengruppe platziert werden. Mit dem Befehl [az group create](/cli/azure/group) wird eine Ressourcengruppe mit den zuvor definierten Parametern $MY_RESOURCE_GROUP_NAME und $REGION erstellt.

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

Verwenden Sie den Befehl `vm create`, um eine VM in dieser Ressourcengruppe zu erstellen. 

Im folgenden Beispiel wird eine VM erstellt und ein Benutzerkonto hinzugefügt. Der Parameter `--generate-ssh-keys` bewirkt, dass die CLI in `~/.ssh` nach einem verfügbaren SSH-Schlüssel sucht. Wenn ein Schlüssel gefunden wird, wird dieser Schlüssel verwendet. Andernfalls wird einer generiert und in `~/.ssh` gespeichert. Der Parameter `--public-ip-sku Standard` stellt sicher, dass die VM über eine öffentliche IP-Adresse zugänglich ist. Schließlich stellen wir das neueste `Ubuntu 22.04`-Image bereit.

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

Das Erstellen des virtuellen Computers und der unterstützenden Ressourcen dauert einige Minuten. In der folgenden Beispielausgabe wird angezeigt, dass der Vorgang der VM-Erstellung erfolgreich war.

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

## Aktivieren der Azure AD-Anmeldung für eine Linux-VM in Azure

Im folgenden Codebeispiel wird eine Linux-VM bereitgestellt und dann die Erweiterung installiert, um die Azure AD-Anmeldung für eine Linux-VM zu aktivieren. VM-Erweiterungen sind kleine Anwendungen, die Konfigurations- und Automatisierungsaufgaben auf virtuellen Azure-Computern nach der Bereitstellung ermöglichen.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

## Speichern der IP-Adresse der VM für SSH

Führen Sie den folgenden Befehl aus, um die IP-Adresse der VM als Umgebungsvariable zu speichern:

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

## Stellen Sie eine SSH-Verbindung mit der VM her.

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Log in to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

Sie können nun SSH auf der VM ausführen, indem Sie die Ausgabe des folgenden Befehls in Ihrem SSH-Client ausführen:

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

## Nächste Schritte

* [Weitere Informationen zu VMs](../index.yml)
* [Verwenden von Cloud-Init zum Initialisieren einer Linux-VM beim ersten Start](tutorial-automate-vm-deployment.md)
* [Erstellen von benutzerdefinierten VM-Images](tutorial-custom-images.md)
* [Lastenausgleich für virtuelle Computer](../../load-balancer/quickstart-load-balancer-standard-public-cli.md)