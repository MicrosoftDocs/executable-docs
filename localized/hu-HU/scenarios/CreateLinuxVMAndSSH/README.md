---
title: Linux rendszerű virtuális gép és SSH létrehozása az Azure-ban
description: 'Ez az oktatóanyag bemutatja, hogyan hozhat létre Linux rendszerű virtuális gépet és SSH-t az Azure-ban.'
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Linux rendszerű virtuális gép és SSH létrehozása az Azure-ban

[![Üzembe helyezés az Azure-ban](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateLinuxVMAndSSH)


## Környezeti változók definiálása

Az oktatóanyag első lépése a környezeti változók definiálása.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
```

# Bejelentkezés az Azure-ba a parancssori felület használatával

Ahhoz, hogy parancsokat futtasson az Azure-on a parancssori felülettel, be kell jelentkeznie. Ez nagyon egyszerűen történik, bár a `az login` parancs:

# Erőforráscsoport létrehozása

Az erőforráscsoportok a kapcsolódó erőforrások tárolói. Minden erőforrást egy erőforráscsoportba kell helyezni. Létrehozunk egyet ehhez az oktatóanyaghoz. A következő parancs létrehoz egy erőforráscsoportot a korábban definiált $MY_RESOURCE_GROUP_NAME és $REGION paraméterekkel.

```bash
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

Ahhoz, hogy létrehozhasson egy virtuális gépet ebben az erőforráscsoportban`~/.ssh`, egy egyszerű parancsot kell futtatnunk. Itt adták meg a `--generate-ssh-keys` jelzőt, ami miatt a parancssori felület egy avialable ssh-kulcsot keres, ha az egyiket használni fogja, ellenkező esetben a rendszer létrehoz és tárol `~/.ssh`egyet. A jelölőt is biztosítjuk `--public-ip-sku Standard` , hogy a gép nyilvános IP-címen keresztül legyen elérhető. Végül üzembe helyezzük a legújabb `Ubuntu 22.04` rendszerképet. 

Minden más érték környezeti változók használatával van konfigurálva.

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

### Azure AD-bejelentkezés engedélyezése Linux rendszerű virtuális gépekhez az Azure-ban

Az alábbi példa egy Linux rendszerű virtuális gépet helyez üzembe, majd telepíti a bővítményt, hogy engedélyezze az Azure AD-bejelentkezést egy Linux rendszerű virtuális géphez. A virtuálisgép-bővítmények olyan kis alkalmazások, amelyek üzembe helyezés utáni konfigurációs és automatizálási feladatokat biztosítanak az Azure-beli virtuális gépeken.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

# A virtuális gép IP-címének tárolása az SSH-hoz
futtassa a következő parancsot a virtuális gép IP-címének lekéréséhez és környezeti változóként való tárolásához

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

# SSH virtuális gépre

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Login to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

Most már SSH-t is be tud illeszteni a virtuális gépbe az alábbi parancs kimenetének futtatásával a választott SSH-ügyfélben

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

# Következő lépések

* [Virtuális gép dokumentációja](https://learn.microsoft.com/azure/virtual-machines/)
* [Linux rendszerű virtuális gép inicializálása a Cloud-Init használatával az első rendszerindításkor](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-automate-vm-deployment)
* [Egyéni virtuálisgép-rendszerképek létrehozása](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-custom-images)
* [Virtuális gépek terheléselosztása](https://learn.microsoft.com/azure/load-balancer/quickstart-load-balancer-standard-public-cli)
