---
title: 'Tutorial: Despliegue WordPress en el cluster AKS usando Azure CLI'
description: Aprenda a compilar e implementar rápidamente WordPress en AKS con Servidor flexible de Azure Database for MySQL.
ms.service: mysql
ms.subservice: flexible-server
author: mksuni
ms.author: sumuth
ms.topic: tutorial
ms.date: 3/20/2024
ms.custom: 'vc, devx-track-azurecli, innovation-engine, linux-related-content'
---

# Tutorial: Implementación de una aplicación WordPress en AKS con Servidor flexible de Azure Database for MySQL

[!INCLUDE[applies-to-mysql-flexible-server](../includes/applies-to-mysql-flexible-server.md)]

[![Implementación en Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262843)

En este tutorial, implementará una aplicación de WordPress escalable protegida mediante HTTPS en un clúster de Azure Kubernetes Service (AKS) con el servidor flexible de Azure Database for MySQL mediante la CLI de Azure.
**[AKS](../../aks/intro-kubernetes.md)** es un servicio de Kubernetes administrado que permite implementar y administrar clústeres rápidamente. **[Servidor flexible de Azure Database for MyS](overview.md)** QL es un servicio de base de datos totalmente administrado diseñado para proporcionar un control más granular y una mayor flexibilidad sobre las funciones de administración de bases de datos y las opciones de configuración.

> [!NOTE]
> En este tutorial se da por supuesto un conocimiento básico de los conceptos de Kubernetes, WordPress y MySQL.

[!INCLUDE [flexible-server-free-trial-note](../includes/flexible-server-free-trial-note.md)]

## Requisitos previos 

Antes de empezar, asegúrese de que ha iniciado sesión en la CLI de Azure y de que ha seleccionado una suscripción para usarla con la CLI. Asegúrese de que tiene [Helm instalado](https://helm.sh/docs/intro/install/).

> [!NOTE]
> Si ejecuta los comandos de este tutorial localmente en lugar de Azure Cloud Shell, ejecute los comandos como administrador.

## Crear un grupo de recursos

Un grupo de recursos de Azure es un grupo lógico en el que se implementan y administran recursos de Azure. Todos los recursos se deben colocar en un grupo de recursos. El comando siguiente crea un grupo de recursos con los parámetros `$MY_RESOURCE_GROUP_NAME` y `$REGION` definidos anteriormente.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myWordPressAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION
```

Resultados:
<!-- expected_similarity=0.3 -->
```json
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX",
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

> [!NOTE]
> La ubicación del grupo de recursos es donde se almacenan los metadatos del grupo de recursos. También es donde se ejecutan los recursos en Azure si no especifica otra región durante la creación de recursos.

## Creación de una red virtual y una subred

Una red virtual es el bloque de compilación fundamental para las redes privadas en Azure. Azure Virtual Network permite que los recursos de Azure, como las máquinas virtuales, se comuniquen de manera segura entre sí y con Internet.

```bash
export NETWORK_PREFIX="$(($RANDOM % 253 + 1))"
export MY_VNET_PREFIX="10.$NETWORK_PREFIX.0.0/16"
export MY_SN_PREFIX="10.$NETWORK_PREFIX.0.0/22"
export MY_VNET_NAME="myVNet$RANDOM_ID"
export MY_SN_NAME="mySN$RANDOM_ID"
az network vnet create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --name $MY_VNET_NAME \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefixes $MY_SN_PREFIX
```

Resultados:
<!-- expected_similarity=0.3 -->
```json
{
  "newVNet": {
    "addressSpace": {
      "addressPrefixes": [
        "10.210.0.0/16"
      ]
    },
    "enableDdosProtection": false,
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/myWordPressAKSResourceGroupXXX/providers/Microsoft.Network/virtualNetworks/myVNetXXX",
    "location": "eastus",
    "name": "myVNet210",
    "provisioningState": "Succeeded",
    "resourceGroup": "myWordPressAKSResourceGroupXXX",
    "subnets": [
      {
        "addressPrefix": "10.210.0.0/22",
        "delegations": [],
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/myWordPressAKSResourceGroupXXX/providers/Microsoft.Network/virtualNetworks/myVNetXXX/subnets/mySNXXX",
        "name": "mySN210",
        "privateEndpointNetworkPolicies": "Disabled",
        "privateLinkServiceNetworkPolicies": "Enabled",
        "provisioningState": "Succeeded",
        "resourceGroup": "myWordPressAKSResourceGroupXXX",
        "type": "Microsoft.Network/virtualNetworks/subnets"
      }
    ],
    "type": "Microsoft.Network/virtualNetworks",
    "virtualNetworkPeerings": []
  }
}
```

## Creación de una instancia del servidor flexible de Azure Database for MySQL

Un servidor flexible de Azure Database for MySQL es un servicio administrado que se usa para ejecutar, administrar y escalar servidores MySQL de alta disponibilidad en la nube. Cree una instancia de servidor flexible Azure Database para MySQL con el comando [az mysql flexible-server create](/cli/azure/mysql/flexible-server). Un servidor puede contener varias bases de datos. El comando siguiente crea un servidor mediante valores predeterminados de servicio y valores variables a partir del contexto local de la CLI de Azure:

```bash
export MY_MYSQL_ADMIN_USERNAME="dbadmin$RANDOM_ID"
export MY_WP_ADMIN_PW="$(openssl rand -base64 32)"
echo "Your MySQL user $MY_MYSQL_ADMIN_USERNAME password is: $MY_WP_ADMIN_PW" 
```

```bash
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
export MY_MYSQL_DB_NAME="mydb$RANDOM_ID"
export MY_MYSQL_ADMIN_PW="$(openssl rand -base64 32)"
export MY_MYSQL_SN_NAME="myMySQLSN$RANDOM_ID"
az mysql flexible-server create \
    --admin-password $MY_MYSQL_ADMIN_PW \
    --admin-user $MY_MYSQL_ADMIN_USERNAME \
    --auto-scale-iops Disabled \
    --high-availability Disabled \
    --iops 500 \
    --location $REGION \
    --name $MY_MYSQL_DB_NAME \
    --database-name wordpress \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --sku-name Standard_B2s \
    --storage-auto-grow Disabled \
    --storage-size 20 \
    --subnet $MY_MYSQL_SN_NAME \
    --private-dns-zone $MY_DNS_LABEL.private.mysql.database.azure.com \
    --tier Burstable \
    --version 8.0.21 \
    --vnet $MY_VNET_NAME \
    --yes -o JSON
```

Resultados:
<!-- expected_similarity=0.3 -->
```json
{
  "databaseName": "wordpress",
  "host": "mydbxxx.mysql.database.azure.com",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX/providers/Microsoft.DBforMySQL/flexibleServers/mydbXXX",
  "location": "East US",
  "resourceGroup": "myWordPressAKSResourceGroupXXX",
  "skuname": "Standard_B2s",
  "subnetId": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX/providers/Microsoft.Network/virtualNetworks/myVNetXXX/subnets/myMySQLSNXXX",
  "username": "dbadminxxx",
  "version": "8.0.21"
}
```

El servidor creado tiene los siguientes atributos:

- Se crea una nueva base de datos vacía cuando el servidor se aprovisiona por primera vez.
- El nombre del servidor, el nombre de usuario administrador, la contraseña del administrador, el nombre del grupo de recursos y la ubicación ya se especifican en el entorno de contexto local de Cloud Shell y están en la misma ubicación que el grupo de recursos y otros componentes de Azure.
- Los valores predeterminados del servicio para las configuraciones de servidor restantes son el nivel de proceso (ampliable), el tamaño de proceso o la SKU (Standard_B2s), el período de retención de copia de seguridad (siete días) y la versión de MySQL (8.0.21).
- El método de conectividad predeterminado es Acceso privado (integración de red virtual) con una red virtual vinculada y una subred generada automáticamente.

> [!NOTE]
> El método de conectividad no se puede cambiar después de crear el servidor. Por ejemplo, si seleccionó `Private access (VNet Integration)` durante la creación, no puede cambiar a `Public access (allowed IP addresses)` después. Se recomienda encarecidamente crear un servidor con acceso privado para acceder de forma segura a su servidor mediante la integración con la red virtual. Obtenga más información sobre el acceso privado en el [artículo de conceptos](./concepts-networking-vnet.md).

Si quiere cambiar algún valor predeterminado, consulte en la [documentación de referencia](/cli/azure//mysql/flexible-server) de la CLI de Azure la lista completa de parámetros configurables de la CLI.

## Comprobación del Azure Database for MySQL: estado del servidor flexible

Se tarda unos minutos en crear el servidor flexible de Azure Database for MySQL y los recursos auxiliares.

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## Configuración de parámetros de servidor en Azure Database for MySQL: servidor flexible

Es posible administrar la configuración de Azure Database for MySQL: servidor flexible con los parámetros de servidor. Los parámetros de servidor se configuran con los valores predeterminados y recomendados al crear el servidor.

Para mostrar los detalles de un parámetro específico de un servidor, ejecute el comando [az mysql flexible-server parameter show](/cli/azure/mysql/flexible-server/parameter).

### Deshabilitación de Azure Database for MySQL: parámetro de conexión SSL de servidor flexible para la integración de Wordpress

También puede modificar el valor de determinados parámetros de servidor para actualizar los valores de configuración subyacentes para el motor de servidor MySQL. Para actualizar el parámetro, use el comando [az mysql flexible-server parameter set](/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set).

```bash
az mysql flexible-server parameter set \
    -g $MY_RESOURCE_GROUP_NAME \
    -s $MY_MYSQL_DB_NAME \
    -n require_secure_transport -v "OFF" -o JSON
```

Resultados:
<!-- expected_similarity=0.3 -->
```json
{
  "allowedValues": "ON,OFF",
  "currentValue": "OFF",
  "dataType": "Enumeration",
  "defaultValue": "ON",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX/providers/Microsoft.DBforMySQL/flexibleServers/mydbXXX/configurations/require_secure_transport",
  "isConfigPendingRestart": "False",
  "isDynamicConfig": "True",
  "isReadOnly": "False",
  "name": "require_secure_transport",
  "resourceGroup": "myWordPressAKSResourceGroupXXX",
  "source": "user-override",
  "systemData": null,
  "type": "Microsoft.DBforMySQL/flexibleServers/configurations",
  "value": "OFF"
}
```

## Creación de un clúster de AKS

Para crear un clúster de AKS con Container Insights, use el comando [az aks create](/cli/azure/aks#az-aks-create) con el parámetro de supervisión **--enable-addons**. En el ejemplo siguiente se crea un clúster habilitado para zonas de disponibilidad con escalado automático llamado **myAKSCluster**:

Esta acción tarda unos minutos.

```bash
export MY_SN_ID=$(az network vnet subnet list --resource-group $MY_RESOURCE_GROUP_NAME --vnet-name $MY_VNET_NAME --query "[0].id" --output tsv)
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"

az aks create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_AKS_CLUSTER_NAME \
    --auto-upgrade-channel stable \
    --enable-cluster-autoscaler \
    --enable-addons monitoring \
    --location $REGION \
    --node-count 1 \
    --min-count 1 \
    --max-count 3 \
    --network-plugin azure \
    --network-policy azure \
    --vnet-subnet-id $MY_SN_ID \
    --no-ssh-key \
    --node-vm-size Standard_DS2_v2 \
    --service-cidr 10.255.0.0/24 \
    --dns-service-ip 10.255.0.10 \
    --zones 1 2 3
```
> [!NOTE]
> Al crear un clúster de AKS, se crea automáticamente un segundo grupo de recursos para almacenar los recursos de AKS. Consulte [¿Por qué se crean dos grupos de recursos con AKS?](../../aks/faq.md#why-are-two-resource-groups-created-with-aks)

## Conectarse al clúster

Para administrar un clúster de Kubernetes, use [kubectl](https://kubernetes.io/docs/reference/kubectl/overview/), el cliente de línea de comandos de Kubernetes. Si usa Azure Cloud Shell, `kubectl` ya está instalado. En el ejemplo siguiente se instala `kubectl` localmente mediante el comando [az aks install-cli](/cli/azure/aks#az-aks-install-cli). 

 ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
```

A continuación, configure `kubectl` para conectarse al clúster de Kubernetes mediante el comando [az aks get-credentials](/cli/azure/aks#az-aks-get-credentials). Con este comando se descargan las credenciales y se configura la CLI de Kubernetes para usarlas. El comando usa `~/.kube/config`, la ubicación predeterminada del [archivo de configuración de Kubernetes](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/). Puede especificar otra ubicación para el archivo de configuración de Kubernetes con el argumento **--file**.

> [!WARNING]
> Este comando sobrescribirá las credenciales existentes con la misma entrada.

```bash
az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
```

Para comprobar la conexión al clúster, use el comando [kubectl get]( https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#get) para devolver una lista de los nodos del clúster.

```bash
kubectl get nodes
```

## Instalación del controlador de entrada NGINX

Puede configurar el controlador de entrada con una dirección IP pública estática. La IP pública estática se conserva si se elimina el controlador de entrada. La dirección IP no permanece si elimina el clúster de AKS.
Al actualizar el controlador de entrada, debe pasar un parámetro a la versión de Helm para asegurarse de que el servicio del controlador de entrada tenga en cuenta el equilibrador de carga que se le asignará. Para que los certificados HTTPS funcionen correctamente, use una etiqueta DNS para configurar un nombre de dominio completo (FQDN) para la dirección IP del controlador de entrada. El FQDN debe seguir este formato: $MY_DNS_LABEL. AZURE_REGION_NAME.cloudapp.azure.com.

```bash
export MY_PUBLIC_IP_NAME="myPublicIP$RANDOM_ID"
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

A continuación, agregue el repositorio de Helm ingress-nginx, actualice la caché del repositorio de gráficos de Helm local e instale el complemento ingress-nginx a través de Helm. Puede establecer la etiqueta DNS con el **--set controller.service.annotations". service\.beta\.kubernetes\.io/azure-dns-label-name"="<DNS_LABEL>"** parámetro cuando se implementa por primera vez el controlador de entrada o posterior. En este ejemplo, especificará su propia dirección IP pública que creó en el paso anterior con el parámetro **--set controller.service.loadBalancerIP="<STATIC_IP>"**.

```bash
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    helm repo update
    helm upgrade --install --cleanup-on-fail --atomic ingress-nginx ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --create-namespace \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"=$MY_DNS_LABEL \
        --set controller.service.loadBalancerIP=$MY_STATIC_IP \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
        --wait --timeout 10m0s
```

## Adición de la terminación HTTPS al dominio personalizado

En este punto del tutorial, tiene una aplicación web de AKS con NGINX como controlador de entrada y un dominio personalizado que puede usar para acceder a la aplicación. El siguiente paso consiste en agregar un certificado SSL al dominio para que los usuarios puedan acceder a la aplicación de forma segura a través de https.

### Implementación del administrador de certificados

Para agregar HTTPS, vamos a usar Cert Manager. Cert Manager es una herramienta de código abierto para obtener y administrar certificados SSL para implementaciones de Kubernetes. Cert Manager obtiene certificados de emisores públicos conocidos y emisores privados, garantiza que los certificados sean válidos y estén actualizados, e intenta renovar certificados en un momento configurado antes de que expiren.

1. Para instalar el administrador de certificados, primero debemos crear un espacio de nombres en el que ejecutarlo. En este tutorial se instala cert-manager en el espacio de nombres cert-manager. Puede ejecutar cert-manager en otro espacio de nombres, pero debe realizar modificaciones en los manifiestos de implementación.

    ```bash
    kubectl create namespace cert-manager
    ```

2. Ahora podemos instalar el administrador de certificados. Todos los recursos están incluidos en un solo archivo de manifiesto de YAML. Instale el archivo de manifiesto con el siguiente comando:

    ```bash
    kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
    ```

3. Para agregar la etiqueta `certmanager.k8s.io/disable-validation: "true"` al espacio de nombres cert-manager, ejecute lo siguiente: Esto permite que los recursos del sistema que cert-manager necesita para arrancar TLS se creen en su propio espacio de nombres.

    ```bash
    kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
    ```

## Obtención de certificados mediante gráficos de Helm

Helm es una herramienta de implementación de Kubernetes para automatizar la creación, el empaquetado, la configuración y la implementación de aplicaciones y servicios en clústeres de Kubernetes.

El administrador de certificados proporciona gráficos de Helm como método de instalación de primera clase en Kubernetes.

1. Agregue el repositorio Helm de Jetstack. Este repositorio es el único origen admitido de gráficos del administrador de certificados. Hay otros reflejos y copias en Internet, pero no son oficiales y podrían presentar un riesgo de seguridad.

    ```bash
    helm repo add jetstack https://charts.jetstack.io
    ```

2. Actualice la memoria caché del repositorio local de gráficos de Helm.

    ```bash
    helm repo update
    ```

3. Instale el complemento Cert-Manager mediante Helm.

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. Aplique el archivo YAML del emisor de certificado. ClusterIssuers son recursos de Kubernetes que representan entidades de certificación (CA) que pueden generar certificados firmados respetando las solicitudes de firma de certificados. Todos los certificados del administrador de certificados requieren un emisor al que se haga referencia que esté preparado para intentar aceptar la solicitud. Puede encontrar el emisor que somos en `cluster-issuer-prod.yml file`.

    ```bash
    export SSL_EMAIL_ADDRESS="$(az account show --query user.name --output tsv)"
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## Creación de una clase de almacenamiento personalizada

Las clases de almacenamiento predeterminadas se adaptan a los escenarios más comunes, pero no a todos. En algunos casos, puede que quiera tener una clase de almacenamiento propia personalizada con sus propios parámetros. Por ejemplo, use el siguiente manifiesto para configurar el elemento **mountOptions** del recurso compartido de archivos.
El valor predeterminado de **fileMode** y **dirMode** es **0755** para recursos compartidos de archivos montados en Kubernetes. Puede especificar las diferentes opciones de montaje en el objeto de clase de almacenamiento.

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## Implementación de WordPress en el clúster de AKS

En este tutorial, vamos a usar un gráfico de Helm existente para WordPress creado por Bitnami. El gráfico de Helm de Bitnami usa una instancia local de MariaDB como base de datos, por lo que es necesario reemplazar estos valores para usar la aplicación con Azure Database for MySQL. Puede reemplazar los valores y la configuración personalizada del archivo `helm-wp-aks-values.yaml`.

1. Agregue el repositorio de Helm para Wordpress de Bitnami.

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. Actualice la memoria caché del repositorio local de gráficos de Helm.

    ```bash
    helm repo update
    ```

3. Instale la carga de trabajo de Wordpress mediante Helm.

    ```bash
    export MY_MYSQL_HOSTNAME="$MY_MYSQL_DB_NAME.mysql.database.azure.com"
    export MY_WP_ADMIN_USER="wpcliadmin"
    export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
    helm upgrade --install --cleanup-on-fail \
        --wait --timeout 10m0s \
        --namespace wordpress \
        --create-namespace \
        --set wordpressUsername="$MY_WP_ADMIN_USER" \
        --set wordpressPassword="$MY_WP_ADMIN_PW" \
        --set wordpressEmail="$SSL_EMAIL_ADDRESS" \
        --set externalDatabase.host="$MY_MYSQL_HOSTNAME" \
        --set externalDatabase.user="$MY_MYSQL_ADMIN_USERNAME" \
        --set externalDatabase.password="$MY_MYSQL_ADMIN_PW" \
        --set ingress.hostname="$FQDN" \
        --values helm-wp-aks-values.yaml \
        wordpress bitnami/wordpress
    ```

Resultados:
<!-- expected_similarity=0.3 -->
```text
Release "wordpress" does not exist. Installing it now.
NAME: wordpress
LAST DEPLOYED: Tue Oct 24 16:19:35 2023
NAMESPACE: wordpress
STATUS: deployed
REVISION: 1
TEST SUITE: None
NOTES:
CHART NAME: wordpress
CHART VERSION: 18.0.8
APP VERSION: 6.3.2

** Please be patient while the chart is being deployed **

Your WordPress site can be accessed through the following DNS name from within your cluster:

    wordpress.wordpress.svc.cluster.local (port 80)

To access your WordPress site from outside the cluster follow the steps below:

1. Get the WordPress URL and associate WordPress hostname to your cluster external IP:

   export CLUSTER_IP=$(minikube ip) # On Minikube. Use: `kubectl cluster-info` on others K8s clusters
   echo "WordPress URL: https://mydnslabelxxx.eastus.cloudapp.azure.com/"
   echo "$CLUSTER_IP  mydnslabelxxx.eastus.cloudapp.azure.com" | sudo tee -a /etc/hosts
    export CLUSTER_IP=$(minikube ip) # On Minikube. Use: `kubectl cluster-info` on others K8s clusters
    echo "WordPress URL: https://mydnslabelxxx.eastus.cloudapp.azure.com/"
    echo "$CLUSTER_IP  mydnslabelxxx.eastus.cloudapp.azure.com" | sudo tee -a /etc/hosts

2. Open a browser and access WordPress using the obtained URL.

3. Login with the following credentials below to see your blog:

    echo Username: wpcliadmin
    echo Password: $(kubectl get secret --namespace wordpress wordpress -o jsonpath="{.data.wordpress-password}" | base64 -d)
```

## Examen de la implementación de AKS protegida con HTTPS

Ejecute el siguiente comando para obtener el punto de conexión HTTPS de la aplicación:

> [!NOTE]
> A menudo, el certificado SSL tarda entre 2 y 3 minutos en propagarse y unos 5 minutos para que todas las réplicas POD de WordPress estén listas y el sitio sea totalmente accesible a través de https.

```bash
runtime="5 minute"
endtime=$(date -ud "$runtime" +%s)
while [[ $(date -u +%s) -le $endtime ]]; do
    export DEPLOYMENT_REPLICAS=$(kubectl -n wordpress get deployment wordpress -o=jsonpath='{.status.availableReplicas}');
    echo Current number of replicas "$DEPLOYMENT_REPLICAS/3";
    if [ "$DEPLOYMENT_REPLICAS" = "3" ]; then
        break;
    else
        sleep 10;
    fi;
done
```

Compruebe que el contenido de WordPress se entrega correctamente con el siguiente comando:

```bash
if curl -I -s -f https://$FQDN > /dev/null ; then 
    curl -L -s -f https://$FQDN 2> /dev/null | head -n 9
else 
    exit 1
fi;
```

Resultados:
<!-- expected_similarity=0.3 -->
```HTML
{
<!DOCTYPE html>
<html lang="en-US">
<head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name='robots' content='max-image-preview:large' />
<title>WordPress on AKS</title>
<link rel="alternate" type="application/rss+xml" title="WordPress on AKS &raquo; Feed" href="https://mydnslabelxxx.eastus.cloudapp.azure.com/feed/" />
<link rel="alternate" type="application/rss+xml" title="WordPress on AKS &raquo; Comments Feed" href="https://mydnslabelxxx.eastus.cloudapp.azure.com/comments/feed/" />
}
```

Visite el sitio web mediante la siguiente dirección URL:

```bash
echo "You can now visit your web server at https://$FQDN"
```

## Limpieza de los recursos (opcional)

Para evitar los cargos de Azure, se recomienda limpiar los recursos que no sean necesarios. Cuando ya no necesite el clúster, use el comando [az group delete](/cli/azure/group#az-group-delete) para quitar el grupo de recursos, el servicio de contenedor y todos los recursos relacionados. 

> [!NOTE]
> Cuando elimina el clúster, la entidad de servicio de Microsoft Entra que utiliza el clúster de AKS no se quita. Para conocer los pasos que hay que realizar para quitar la entidad de servicio, consulte [Consideraciones principales y eliminación de AKS](../../aks/kubernetes-service-principal.md#other-considerations). Si usó una identidad administrada, esta está administrada por la plataforma y no requiere que la quite.

## Pasos siguientes

- Aprenda a [acceder al panel web de Kubernetes](../../aks/kubernetes-dashboard.md) del clúster de AKS.
- Aprenda a [escalar el clúster](../../aks/tutorial-kubernetes-scale.md).
- Aprenda a configurar la [instancia del servidor flexible de Azure Database for MySQL](./quickstart-create-server-cli.md)
- Aprenda a [configurar parámetros de servidor](./how-to-configure-server-parameters-cli.md) para el servidor de bases de datos
