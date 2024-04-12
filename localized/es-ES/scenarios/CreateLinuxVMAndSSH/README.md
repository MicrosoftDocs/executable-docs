---
title: 'Inicio rápido: Uso de la CLI de Azure para crear una máquina virtual Linux'
description: 'En esta guía de inicio rápido, aprenderá a utilizar la CLI de Azure para crear una máquina virtual Linux'
author: ju-shim
ms.service: virtual-machines
ms.collection: linux
ms.topic: quickstart
ms.date: 03/11/2024
ms.author: jushiman
ms.custom: 'mvc, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Guía de inicio rápido: Creación de una máquina virtual Linux con la CLI de Azure

**Se aplica a:** :heavy_check_mark: Máquinas virtuales Linux

[![Implementación en Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262692)

En esta guía de inicio rápido se muestra como usar la CLI de Azure para implementar una máquina virtual (VM) Linux en Azure. La CLI de Azure se usa para crear y administrar recursos de Azure mediante la línea de comandos o scripts.

Si no tiene una suscripción a Azure, cree una cuenta [gratuita](https://azure.microsoft.com/free/?WT.mc_id=A261C142F) antes de empezar.

## Inicio de Azure Cloud Shell

Azure Cloud Shell es un shell interactivo gratuito que puede usar para ejecutar los pasos de este artículo. Tiene las herramientas comunes de Azure preinstaladas y configuradas para usarlas en la cuenta. 

Para abrir Cloud Shell, seleccione **Pruébelo** en la esquina superior derecha de un bloque de código. También puede abrir Cloud Shell en una pestaña independiente acudiendo a [https://shell.azure.com/bash](https://shell.azure.com/bash). Seleccione **Copiar** para copiar los bloques de código, péguelos en Cloud Shell y, después, seleccione **Entrar** para ejecutarlos.

Si prefiere instalar y usar la CLI en un entorno local, para esta guía de inicio rápido se requiere la versión 2.0.30 de la CLI de Azure o una versión posterior. Ejecute `az --version` para encontrar la versión. Si necesita instalarla o actualizarla, vea [Instalación de la CLI de Azure]( /cli/azure/install-azure-cli).

## Definición de las variables de entorno

El primer paso es definir las variables de entorno. Las variables de entorno se usan normalmente en Linux para centralizar los datos de configuración para mejorar la coherencia y el mantenimiento del sistema. Cree las siguientes variables de entorno para especificar los nombres de los recursos que creará más adelante en este tutorial:

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
```

## Inicie sesión en Azure mediante la CLI

Para ejecutar comandos en Azure utilizando la CLI, primero debe iniciar sesión. Inicie sesión con el comando `az login`.

## Crear un grupo de recursos

Un grupo de recursos es un contenedor para los recursos relacionados. Todos los recursos se deben colocar en un grupo de recursos. El comando [az group create](/cli/azure/group) crea un grupo de recursos con los parámetros $MY_RESOURCE_GROUP_NAME y $REGION definidos anteriormente.

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

Para crear una máquina virtual en este grupo de recursos, es necesario usar el comando `vm create`. 

En el ejemplo siguiente se crea una máquina virtual y se agrega una cuenta de usuario. El parámetro `--generate-ssh-keys` hace que la CLI busque una clave SSH disponible en `~/.ssh`. Si encuentra una, se usa esa clave. Si no es así, se genera y se almacena en `~/.ssh`. El parámetro `--public-ip-sku Standard` garantiza que la máquina sea accesible a través de una dirección IP pública. Por último, implementamos la imagen más reciente `Ubuntu 22.04`.

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

La creación de la máquina virtual y los recursos auxiliares tarda unos minutos en realizarse. En la salida de ejemplo siguiente se muestra que la operación de creación de la máquina virtual se realizó correctamente.

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

## Habilitación del inicio de sesión de Azure AD para una máquina virtual Linux en Azure

El siguiente ejemplo de código despliega una VM Linux y luego instala la extensión para habilitar un inicio de sesión Azure AD para una VM Linux. Las extensiones de máquina virtual son aplicaciones pequeñas que realizan tareas de automatización y configuración posterior a la implementación en máquinas virtuales de Azure.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

## Almacenar la dirección IP de la máquina virtual con el fin de SSH

Ejecute el siguiente comando para almacenar la dirección IP de la máquina virtual como variable de entorno:

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

## Conéctese mediante SSH a la máquina virtual.

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Log in to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

Ahora puede acceder mediante SSH a la VM ejecutando la salida del siguiente comando en el cliente ssh de su elección:

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

## Pasos siguientes

* [Más información sobre las máquinas virtuales](../index.yml)
* [Uso de cloud-init para inicializar una máquina virtual Linux en el primer arranque](tutorial-automate-vm-deployment.md)
* [Creación de imágenes personalizadas de máquinas virtuales](tutorial-custom-images.md)
* [Equilibrio de carga de máquinas virtuales](../../load-balancer/quickstart-load-balancer-standard-public-cli.md)