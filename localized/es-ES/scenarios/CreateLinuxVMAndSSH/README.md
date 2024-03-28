---
title: Creación de una máquina virtual Linux y SSH en Azure
description: En este tutorial se muestra cómo crear una máquina virtual Linux y SSH en Azure.
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Creación de una máquina virtual Linux y SSH en Azure

[![Implementación en Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262692)


## Definición de las variables de entorno

El primer paso de este tutorial es definir las variables de entorno.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
```

# Iniciar sesión en Azure mediante la CLI

Para ejecutar comandos en Azure mediante la CLI, debe iniciar sesión. Esto se hace, muy simplemente, a través del comando `az login`:

# Crear un grupo de recursos

Un grupo de recursos es un contenedor para los recursos relacionados. Todos los recursos se deben colocar en un grupo de recursos. Vamos a crear uno para este tutorial. El comando siguiente crea un grupo de recursos con los parámetros $MY_RESOURCE_GROUP_NAME y $REGION definidos anteriormente.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Resultados:

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

## Creación de la máquina virtual

Para crear una máquina virtual en este grupo de recursos, es necesario ejecutar un comando sencillo. Aquí se ha proporcionado la marca `--generate-ssh-keys` y esto hará que la CLI busque una clave SSH disponible en `~/.ssh`; si se encuentra una, esta se usará; de lo contrario, se generará una clave y se almacenará en `~/.ssh`. También proporcionamos la marca `--public-ip-sku Standard` para asegurarse de que la máquina sea accesible a través de una dirección IP pública. Por último, estamos implementando la imagen `Ubuntu 22.04` más reciente. 

Todos los demás valores se configuran mediante variables de entorno.

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

Resultados:

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

### Habilitación del inicio de sesión de Azure AD para una máquina virtual Linux en Azure

En el ejemplo siguiente, se implementa una máquina virtual Linux y, a continuación, se instala la extensión para habilitar el inicio de sesión de Azure AD para una máquina virtual Linux. Las extensiones de máquina virtual son aplicaciones pequeñas que realizan tareas de automatización y configuración posterior a la implementación en máquinas virtuales de Azure.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

# Almacenar la dirección IP de la máquina virtual con el fin de SSH
ejecutar el siguiente comando para obtener la dirección IP de la máquina virtual y almacenarla como una variable de entorno

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

# SSH en una máquina virtual

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Login to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

Ahora puede conectarse mediante SSH a la máquina virtual ejecutando la salida del comando siguiente en el cliente ssh que prefiera

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

# Pasos siguientes

* [Documentación de máquina virtual](https://learn.microsoft.com/azure/virtual-machines/)
* [Uso de cloud-init para inicializar una máquina virtual Linux en el primer arranque](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-automate-vm-deployment)
* [Creación de imágenes personalizadas de máquinas virtuales](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-custom-images)
* [Equilibrio de carga de máquinas virtuales](https://learn.microsoft.com/azure/load-balancer/quickstart-load-balancer-standard-public-cli)
