---
title: 'Rövid útmutató: Linux rendszerű virtuális gép létrehozása az Azure CLI használatával'
description: 'Ebből a rövid útmutatóból elsajátíthatja, hogyan hozhat létre Linux rendszerű virtuális gépet az Azure CLI használatával.'
author: ju-shim
ms.service: virtual-machines
ms.collection: linux
ms.topic: quickstart
ms.date: 03/11/2024
ms.author: jushiman
ms.custom: 'mvc, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Rövid útmutató: Linux rendszerű virtuális gép létrehozása az Azure CLI-vel az Azure-ban

**A következőre vonatkozik:** :heavy_check_mark: Linux rendszerű virtuális gépek

[![Üzembe helyezés az Azure-ban](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262692)

Ez a rövid útmutató bemutatja, hogyan helyezhet üzembe az Azure CLI segítségével Linux rendszerű virtuális gépeket (VM-eket) az Azure-ban. Az Azure CLI használatával azure-erőforrások hozhatók létre és kezelhetők parancssoron vagy szkripteken keresztül.

Ha még nincs Azure-előfizetése, kezdés előtt hozzon létre egy [ingyenes fiókot](https://azure.microsoft.com/free/?WT.mc_id=A261C142F).

## Az Azure Cloud Shell elindítása

Az Azure Cloud Shell egy olyan ingyenes interaktív kezelőfelület, amelyet a jelen cikkben található lépések futtatására használhat. A fiókjával való használat érdekében a gyakran használt Azure-eszközök már előre telepítve és konfigurálva vannak rajta. 

A Cloud Shell megnyitásához válassza a **Kipróbálás** lehetőséget egy kódblokk jobb felső sarkában. A Cloud Shellt külön böngészőlapon is megnyithatja a következő lépéssel [https://shell.azure.com/bash](https://shell.azure.com/bash): Válassza **a Másolás** lehetőséget a kódblokkok másolásához, illessze be a Cloud Shellbe, majd az Enter** gombra kattintva **futtassa.

Ha a parancssori felület helyi telepítését és használatát választja, akkor ehhez a rövid útmutatóhoz az Azure CLI 2.0.30-es vagy újabb verziójára lesz szükség. A verzió azonosításához futtassa a következőt: `az --version`. Ha telepíteni vagy frissíteni szeretne: [Az Azure CLI telepítése]( /cli/azure/install-azure-cli).

## Bejelentkezés az Azure-ba a parancssori felület használatával

Ahhoz, hogy parancsokat futtasson az Azure-ban a parancssori felület használatával, először be kell jelentkeznie. Jelentkezzen be a `az login` parancs használatával.

## Erőforráscsoport létrehozása

Az erőforráscsoportok a kapcsolódó erőforrások tárolói. Minden erőforrást egy erőforráscsoportba kell helyezni. Az [az group create](/cli/azure/group) parancs létrehoz egy erőforráscsoportot a korábban definiált $MY_RESOURCE_GROUP_NAME és $REGION paraméterekkel.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Eredmények:

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

## A virtuális gép létrehozása

Ha virtuális gépet szeretne létrehozni ebben az erőforráscsoportban, használja a `vm create` parancsot. 

Az alábbi példa létrehoz egy virtuális gépet, és hozzáad egy felhasználói fiókot. A `--generate-ssh-keys` paraméter hatására a parancssori felület egy elérhető ssh-kulcsot keres a fájlban `~/.ssh`. Ha talál ilyet, a rendszer ezt a kulcsot használja. Ha nem, akkor a rendszer létrehoz és tárol egyet.`~/.ssh` A `--public-ip-sku Standard` paraméter biztosítja, hogy a gép nyilvános IP-címmel legyen elérhető. Végül üzembe helyezzük a legújabb `Ubuntu 22.04` rendszerképet.

Minden más érték környezeti változók használatával van konfigurálva.

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

A virtuális gép és a kapcsolódó erőforrások létrehozása csak néhány percet vesz igénybe. A következő kimeneti példa azt mutatja be, hogy a virtuális gép létrehozási művelete sikeres volt.

Eredmények:
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

## Azure AD-bejelentkezés engedélyezése Linux rendszerű virtuális gépekhez az Azure-ban

Az alábbi példakód egy Linux rendszerű virtuális gépet helyez üzembe, majd telepíti a bővítményt, hogy engedélyezze az Azure AD-bejelentkezést linuxos virtuális gépeken. A virtuálisgép-bővítmények olyan kis alkalmazások, amelyek üzembe helyezés utáni konfigurációs és automatizálási feladatokat biztosítanak az Azure-beli virtuális gépeken.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

## A virtuális gép IP-címének tárolása az SSH-hoz

Futtassa a következő parancsot a virtuális gép IP-címének környezeti változóként való tárolásához:

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

## SSH a virtuális gépre

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Log in to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

Most már SSH-t is be tud illeszteni a virtuális gépbe, ha a következő parancs kimenetét futtatja a választott ssh-ügyfélben:

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

## Következő lépések

* [Tudnivalók a virtuális gépekről](../index.yml)
* [Linux rendszerű virtuális gép inicializálása a Cloud-Init használatával az első rendszerindításkor](tutorial-automate-vm-deployment.md)
* [Egyéni virtuálisgép-rendszerképek létrehozása](tutorial-custom-images.md)
* [Virtuális gépek terheléselosztása](../../load-balancer/quickstart-load-balancer-standard-public-cli.md)