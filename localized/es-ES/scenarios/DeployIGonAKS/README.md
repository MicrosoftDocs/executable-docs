---
title: "Implementación de Inspektor\_Gadget en un clúster de Azure\_Kubernetes Service"
description: "En este tutorial se muestra cómo implementar Inspektor\_Gadget en un clúster de AKS."
author: josebl
ms.author: josebl
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Inicio rápido: Implementación de Inspektor Gadget en un clúster de Azure Kubernetes Service

[![Implementación en Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262844)

Le damos la bienvenida a este tutorial en el que le guiaremos paso a paso en la implementación de [Inspektor Gadget](https://www.inspektor-gadget.io/) en un clúster de Azure Kubernetes Service (AKS) con el complemento de kubectl: `gadget`. En este tutorial se supone que ya ha iniciado sesión en la CLI de Azure y ha seleccionado una suscripción para usarla con la CLI.

## Definición de las variables de entorno

El primer paso de este tutorial es definir las variables de entorno:

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myResourceGroup$RANDOM_ID"
export REGION="eastus"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
```

## Crear un grupo de recursos

Un grupo de recursos es un contenedor para los recursos relacionados. Todos los recursos se deben colocar en un grupo de recursos. Vamos a crear uno para este tutorial. El comando siguiente crea un grupo de recursos con los parámetros $MY_RESOURCE_GROUP_NAME y $REGION definidos anteriormente.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Resultados:

<!-- expected_similarity=0.3 -->
```JSON
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myResourceGroup210",
  "location": "eastus",
  "managedBy": null,
  "name": "testResourceGroup",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Crear clúster de AKS

Cree un clúster de AKS con el comando az aks create.

Esta operación puede tardar unos minutos.

```bash
az aks create \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --name $MY_AKS_CLUSTER_NAME \
  --location $REGION \
  --no-ssh-key
```

## Conectarse al clúster

Para administrar un clúster de Kubernetes, use la línea de comandos de Kubernetes, kubectl. Si usa Azure Cloud Shell, kubectl ya está instalado.

1. Instale la CLI de az aks localmente mediante el comando az aks install-cli.

    ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
    ```

2. Configure kubectl para que se conecte al clúster de Kubernetes mediante el comando az aks get-credentials. El siguiente comando:
    - Descarga las credenciales y configura la CLI de Kubernetes para usarlas.
    - Usa ~/.kube/config, la ubicación predeterminada del archivo de configuración de Kubernetes. Puede especificar otra ubicación para el archivo de configuración de Kubernetes con el argumento --file.

    > [!WARNING]
    > Esto sobrescribirá las credenciales existentes con la misma entrada.

    ```bash
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
    ```

3. Compruebe la conexión al clúster con el comando kubectl get. Este comando devuelve una lista de los nodos del clúster.

    ```bash
    kubectl get nodes
    ```

## Instalación de Inspektor Gadget

La instalación de Inspektor Gadget consta de dos pasos:

1. Instalación del complemento de kubectl en el sistema del usuario.
2. Instalación de Inspektor Gadget en el clúster.

    > [!NOTE]
    > Hay mecanismos adicionales para implementar y usar Inspektor Gadget, cada uno adaptado a casos de uso y requisitos específicos. El uso del complemento `kubectl gadget` cubre muchos de ellos, pero no todos. Por ejemplo, la implementación de Inspektor Gadget con el complemento `kubectl gadget` depende de la disponibilidad del servidor de la API de Kubernetes. Por lo tanto, si no puede depender de este componente porque su disponibilidad podría verse comprometida a veces, se recomienda no usar el mecanismo de implementación `kubectl gadget`. Consulte la [documentación de IG](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/ig.md) para saber qué hacer en ese caso de uso y en otros.

### Instalación del complemento de kubectl: `gadget`

Instale la versión más reciente del complemento de kubectl desde la página de versiones, descomprima y mueva el archivo ejecutable `kubectl-gadget` a `$HOME/.local/bin`:

> [!NOTE]
> Si desea instalarlo mediante [`krew`](https://sigs.k8s.io/krew) o compilarlo desde el origen, siga la documentación oficial: [instalación de gadget kubectl](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-kubectl-gadget).

```bash
IG_VERSION=$(curl -s https://api.github.com/repos/inspektor-gadget/inspektor-gadget/releases/latest | jq -r .tag_name)
IG_ARCH=amd64
mkdir -p $HOME/.local/bin
export PATH=$PATH:$HOME/.local/bin
curl -sL https://github.com/inspektor-gadget/inspektor-gadget/releases/download/${IG_VERSION}/kubectl-gadget-linux-${IG_ARCH}-${IG_VERSION}.tar.gz  | tar -C $HOME/.local/bin -xzf - kubectl-gadget
```

Ahora, ejecutemos el comando `version` para comprobar la instalación:

```bash
kubectl gadget version
```

El comando `version` mostrará la versión del cliente (complemento kubectl gadget). Además, mostrará que aún no se ha instalado en el servidor (el clúster):

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: not installed$"-->
```text
Client version: vX.Y.Z
Server version: not installed
```

### Instalación de Inspektor Gadget en el clúster

El siguiente comando mostrará el recurso DaemonSet:

> [!NOTE]
> Hay varias opciones disponibles para personalizar la implementación: usar una imagen de contenedor específica, implementar en nodos específicos y muchas otras. Para conocerlas todas, consulte la documentación oficial: [instalación en el clúster](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-in-the-cluster).

```bash
kubectl gadget deploy
```

Ahora, ejecutemos el comando `version` para comprobar la instalación una vez más:

```bash
kubectl gadget version
```

Ahora, el cliente y el servidor sí se instalarán correctamente:

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: v\d+\.\d+\.\d+$"-->
```text
Client version: vX.Y.Z
Server version: vX.Y.Z
```

Ya puede empezar a ejecutar los gadgets:

```bash
kubectl gadget help
```

<!--
## Clean Up

### Undeploy Inspektor Gadget

```bash
kubectl gadget undeploy
```

### Clean up Azure resources

When no longer needed, you can use `az group delete` to remove the resource group, cluster, and all related resources as follows. The `--no-wait` parameter returns control to the prompt without waiting for the operation to complete. The `--yes` parameter confirms that you wish to delete the resources without an additional prompt to do so.

```bash
az group delete --name $MY_RESOURCE_GROUP_NAME --no-wait --yes
```
-->

## Pasos siguientes
- [Escenarios reales en los que Inspektor Gadget puede ayudarle](https://go.microsoft.com/fwlink/p/?linkid=2260402#use-cases)
- [Explorar los gadgets disponibles](https://go.microsoft.com/fwlink/p/?linkid=2260070)
- [Ejecutar su propio programa eBPF](https://go.microsoft.com/fwlink/p/?linkid=2259865)
