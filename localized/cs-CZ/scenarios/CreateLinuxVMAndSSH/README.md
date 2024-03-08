---
title: Vytvoření virtuálního počítače s Linuxem a SSH v Azure
description: 'V tomto kurzu se dozvíte, jak vytvořit virtuální počítač s Linuxem a SSH v Azure.'
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Vytvoření virtuálního počítače s Linuxem a SSH v Azure

[![Nasazení do Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateLinuxVMAndSSH)


## Definování proměnných prostředí

Prvním krokem v tomto kurzu je definování proměnných prostředí.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
```

# Přihlášení k Azure pomocí rozhraní příkazového řádku

Pokud chcete spouštět příkazy v Azure pomocí rozhraní příkazového řádku, musíte se přihlásit. To se provádí velmi jednoduše, i když příkaz `az login` :

# Vytvoření skupiny zdrojů

Skupina prostředků je kontejner pro související prostředky. Všechny prostředky musí být umístěné ve skupině prostředků. Pro účely tohoto kurzu ho vytvoříme. Následující příkaz vytvoří skupinu prostředků s dříve definovanými parametry $MY_RESOURCE_GROUP_NAME a $REGION.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Výsledky:

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

## Vytvoření virtuálního počítače

Abychom mohli vytvořit virtuální počítač v této skupině prostředků, musíme spustit jednoduchý příkaz, zde jsme zadali `--generate-ssh-keys` příznak, což způsobí, že rozhraní příkazového řádku vyhledá aviabilní klíč ssh v `~/.ssh`, pokud se najde, použije se, jinak se vygeneruje a uloží v `~/.ssh`. Poskytujeme `--public-ip-sku Standard` také příznak, který zajistí, že je počítač přístupný prostřednictvím veřejné IP adresy. Nakonec nasazujeme nejnovější `Ubuntu 22.04` image. 

Všechny ostatní hodnoty se konfigurují pomocí proměnných prostředí.

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

Výsledky:

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

### Povolení přihlášení k Azure AD pro virtuální počítač s Linuxem v Azure

Následující příklad nasadí virtuální počítač s Linuxem a pak nainstaluje rozšíření, které povolí přihlášení k Azure AD pro virtuální počítač s Linuxem. Rozšíření virtuálních počítačů jsou malé aplikace, které poskytují úlohy konfigurace a automatizace po nasazení na virtuálních počítačích Azure.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

# Uložení IP adresy virtuálního počítače pro SSH
Spuštěním následujícího příkazu získejte IP adresu virtuálního počítače a uložte ji jako proměnnou prostředí.

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

# Připojení SSH k virtuálnímu počítači

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Login to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

Do virtuálního počítače teď můžete SSH připojit spuštěním výstupu následujícího příkazu ve zvoleném klientovi ssh.

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

# Další kroky

* [Dokumentace k virtuálnímu počítači](https://learn.microsoft.com/azure/virtual-machines/)
* [Použití Cloud-Init k inicializaci virtuálního počítače s Linuxem při prvním spuštění](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-automate-vm-deployment)
* [Vytváření vlastních imagí virtuálních počítačů](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-custom-images)
* [Vyrovnávání zatížení virtuálních počítačů](https://learn.microsoft.com/azure/load-balancer/quickstart-load-balancer-standard-public-cli)
