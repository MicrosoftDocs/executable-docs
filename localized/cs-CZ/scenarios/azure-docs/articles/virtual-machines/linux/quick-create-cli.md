---
title: 'Rychlý start: Vytvoření virtuálního počítače s Linuxem pomocí Azure CLI'
description: 'V tomto rychlém startu zjistíte, jak pomocí Azure CLI vytvořit virtuální počítač s Linuxem'
author: ju-shim
ms.service: virtual-machines
ms.collection: linux
ms.topic: quickstart
ms.date: 03/11/2024
ms.author: jushiman
ms.custom: 'mvc, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Rychlý start: Vytvoření virtuálního počítače s Linuxem pomocí Azure CLI v Azure

**Platí pro:** :heavy_check_mark: virtuální počítače s Linuxem

[![Nasazení do Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262692)

V tomto rychlém startu se dozvíte, jak pomocí Azure CLI nasadit do Azure virtuální počítač s Linuxem. Azure CLI slouží k vytváření a správě prostředků Azure prostřednictvím příkazového řádku nebo skriptů.

Pokud ještě nemáte předplatné Azure, vytvořte si napřed [bezplatný účet](https://azure.microsoft.com/free/?WT.mc_id=A261C142F).

## Spuštění služby Azure Cloud Shell

Azure Cloud Shell je bezplatné interaktivní prostředí, které můžete použít k provedení kroků v tomto článku. Má předinstalované obecné nástroje Azure, které jsou nakonfigurované pro použití s vaším účtem. 

Pokud chcete otevřít Cloud Shell, vyberte položku **Vyzkoušet** v pravém horním rohu bloku kódu. Cloud Shell můžete otevřít také na samostatné kartě prohlížeče tak, že přejdete na [https://shell.azure.com/bash](https://shell.azure.com/bash). Výběrem **možnosti Kopírovat** zkopírujte bloky kódu, vložte ho do Cloud Shellu a stisknutím **klávesy Enter** ho spusťte.

Pokud dáváte přednost místní instalaci a používání rozhraní příkazového řádku, musíte mít Azure CLI verze 2.0.30 nebo novější. Verzi zjistíte spuštěním příkazu `az --version`. Pokud potřebujete instalaci nebo upgrade, přečtěte si téma [Instalace Azure CLI]( /cli/azure/install-azure-cli).

## Přihlášení k Azure pomocí rozhraní příkazového řádku

Abyste mohli spouštět příkazy v Azure pomocí rozhraní příkazového řádku, musíte se nejdřív přihlásit. Přihlaste se pomocí `az login` příkazu.

## Vytvoření skupiny zdrojů

Skupina prostředků je kontejner pro související prostředky. Všechny prostředky musí být umístěné ve skupině prostředků. Příkaz [az group create](/cli/azure/group) vytvoří skupinu prostředků s dříve definovanými parametry $MY_RESOURCE_GROUP_NAME a $REGION.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
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

## Vytvořte virtuální počítač.

Pokud chcete vytvořit virtuální počítač v této skupině prostředků, použijte `vm create` příkaz. 

Následující příklad vytvoří virtuální počítač a přidá uživatelský účet. Tento `--generate-ssh-keys` parametr způsobí, že rozhraní příkazového řádku vyhledá dostupný klíč ssh v `~/.ssh`souboru . Pokud se najde, použije se tento klíč. Pokud ne, jeden se vygeneruje a uloží v `~/.ssh`. Tento `--public-ip-sku Standard` parametr zajišťuje, že je počítač přístupný prostřednictvím veřejné IP adresy. Nakonec nasadíme nejnovější `Ubuntu 22.04` image.

Všechny ostatní hodnoty se konfigurují pomocí proměnných prostředí.

```bash
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
az vm create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_VM_NAME \
    --image $MY_VM_IMAGE \
    --admin-username $MY_USERNAME \
    --assign-identity \
    --generate-ssh-keys \
    --public-ip-sku Standard
```

Vytvoření virtuálního počítače a podpůrných prostředků trvá několik minut. Následující příklad ukazuje, že operace vytvoření virtuálního počítače byla úspěšná.

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

## Povolení přihlášení Azure AD pro virtuální počítač s Linuxem v Azure

Následující příklad kódu nasadí virtuální počítač s Linuxem a pak nainstaluje rozšíření, které povolí přihlášení Azure AD pro virtuální počítač s Linuxem. Rozšíření virtuálních počítačů jsou malé aplikace, které poskytují úlohy konfigurace a automatizace po nasazení na virtuálních počítačích Azure.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

## Uložení IP adresy virtuálního počítače pro SSH

Spuštěním následujícího příkazu uložte IP adresu virtuálního počítače jako proměnnou prostředí:

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

## Připojení SSH k virtuálnímu počítači

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Log in to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

Do virtuálního počítače teď můžete SSH připojit spuštěním výstupu následujícího příkazu ve zvoleném klientovi ssh:

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

## Další kroky

* [Další informace o virtuálních počítačích](../index.yml)
* [Použití Cloud-Init k inicializaci virtuálního počítače s Linuxem při prvním spuštění](tutorial-automate-vm-deployment.md)
* [Vytváření vlastních imagí virtuálních počítačů](tutorial-custom-images.md)
* [Vyrovnávání zatížení virtuálních počítačů](../../load-balancer/quickstart-load-balancer-standard-public-cli.md)