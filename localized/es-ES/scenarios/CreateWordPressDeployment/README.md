---
title: Implementación de una instancia escalable y segura de WordPress en AKS
description: En este tutorial se muestra cómo implementar una instancia escalable y segura de WordPress en AKS a través de la CLI.
author: adrian.joian
ms.author: adrian.joian
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Inicio rápido: Implementación de una instancia escalable y segura de WordPress en AKS

Te damos la bienvenida a este tutorial en el que le guiaremos paso a paso en la creación de una aplicación web de Azure Kubernetes protegida mediante https. En este tutorial se supone que ya ha iniciado sesión en la CLI de Azure y ha seleccionado una suscripción para usarla con la CLI. También supone que tiene Helm instalado ([Las instrucciones se pueden encontrar aquí](https://helm.sh/docs/intro/install/)).

## Definición de las variables de entorno

El primer paso de este tutorial es definir variables de entorno.

```bash
export SSL_EMAIL_ADDRESS="$(az account show --query user.name --output tsv)"
export NETWORK_PREFIX="$(($RANDOM % 253 + 1))"
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myWordPressAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_PUBLIC_IP_NAME="myPublicIP$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
export MY_VNET_NAME="myVNet$RANDOM_ID"
export MY_VNET_PREFIX="10.$NETWORK_PREFIX.0.0/16"
export MY_SN_NAME="mySN$RANDOM_ID"
export MY_SN_PREFIX="10.$NETWORK_PREFIX.0.0/22"
export MY_MYSQL_DB_NAME="mydb$RANDOM_ID"
export MY_MYSQL_ADMIN_USERNAME="dbadmin$RANDOM_ID"
export MY_MYSQL_ADMIN_PW="$(openssl rand -base64 32)"
export MY_MYSQL_SN_NAME="myMySQLSN$RANDOM_ID"
export MY_MYSQL_HOSTNAME="$MY_MYSQL_DB_NAME.mysql.database.azure.com"
export MY_WP_ADMIN_PW="$(openssl rand -base64 32)"
export MY_WP_ADMIN_USER="wpcliadmin"
export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
```

## Crear un grupo de recursos

Un grupo de recursos es un contenedor para los recursos relacionados. Todos los recursos se deben colocar en un grupo de recursos. Vamos a crear uno para este tutorial. El comando siguiente crea un grupo de recursos con los parámetros $MY_RESOURCE_GROUP_NAME y $REGION definidos anteriormente.

```bash
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

## Creación de una red virtual y una subred

Una red virtual es el bloque de compilación fundamental para las redes privadas en Azure. Azure Virtual Network permite que los recursos de Azure, como las máquinas virtuales, se comuniquen de manera segura entre sí y con Internet.

```bash
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

## Creación de un Servidor flexible de Azure Database for MySQL

Servidor flexible de Azure Database for MySQL es un servicio administrado que se usa para ejecutar, administrar y escalar servidores MySQL de alta disponibilidad en la nube. Cree un servidor flexible con el comando [az mysql flexible-server create](https://learn.microsoft.com/cli/azure/mysql/flexible-server#az-mysql-flexible-server-create). Un servidor puede contener varias bases de datos. El siguiente comando crea un servidor mediante valores predeterminados de servicio y variables desde el entorno local de la CLI de Azure:

```bash
echo "Your MySQL user $MY_MYSQL_ADMIN_USERNAME password is: $MY_WP_ADMIN_PW" 
```

```bash
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

- El nombre del servidor, el nombre de usuario de administrador, la contraseña del administrador, el nombre del grupo de recursos y la ubicación ya se especifican en el entorno de contexto local de Cloud Shell y se crearán en la misma ubicación que el grupo de recursos y los demás componentes de Azure.
- Valores predeterminados del servicio para las configuraciones de servidor restantes: nivel de proceso (ampliable), tamaño de proceso/SKU (Standard_B2s), período de retención de copia de seguridad (7 días) y versión de MySQL (8.0.21)
- El método de conectividad predeterminado es acceso privado (integración con red virtual) con una red virtual vinculada y una subred generada automáticamente.

> [!NOTE]
> El método de conectividad no se puede cambiar después de crear el servidor. Por ejemplo, si seleccionó `Private access (VNet Integration)` durante la creación, no puede cambiar a `Public access (allowed IP addresses)` después de la creación. Se recomienda encarecidamente crear un servidor con acceso privado para acceder de forma segura a su servidor mediante la integración con la red virtual. Obtenga más información sobre el acceso privado en el [artículo de conceptos](https://learn.microsoft.com/azure/mysql/flexible-server/concepts-networking-vnet).

Si quiere cambiar algún valor predeterminado, consulte en la [documentación de referencia](https://learn.microsoft.com/cli/azure//mysql/flexible-server)de la CLI de Azure la lista completa de parámetros configurables de la CLI.

## Comprobación del Azure Database for MySQL: estado del servidor flexible

Se tarda unos minutos en crear el servidor flexible de Azure Database for MySQL y los recursos auxiliares.

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## Configuración de parámetros de servidor en Azure Database for MySQL: servidor flexible

Es posible administrar la configuración de Azure Database for MySQL: servidor flexible con los parámetros de servidor. Los parámetros de servidor se configuran con los valores predeterminados y recomendados al crear el servidor.

Mostrar detalles del parámetro de servidor: para mostrar los detalles sobre un parámetro determinado para un servidor, ejecute el comando [az mysql flexible-server parameter show](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter).

### Deshabilitación de Azure Database for MySQL: parámetro de conexión SSL de servidor flexible para la integración de Wordpress

También puede modificar el valor de determinados parámetros del servidor, lo que actualiza los valores de configuración subyacentes del motor del servidor MySQL. Para actualizar el parámetro, use el comando [az mysql flexible-server parameter set](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set).

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

## Crear clúster de AKS

Cree un clúster de AKS con el comando az aks create con el parámetro --enable-addons monitoring para habilitar Container Insights. En el ejemplo siguiente se crea un clúster habilitado para zonas de disponibilidad y escalado automático llamado myAKSCluster:

Esta operación tarda unos minutos.

```bash
export MY_SN_ID=$(az network vnet subnet list --resource-group $MY_RESOURCE_GROUP_NAME --vnet-name $MY_VNET_NAME --query "[0].id" --output tsv)

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

## Instalación del controlador de entrada NGINX

Puede configurar el controlador de entrada con una dirección IP pública estática. La IP pública estática se conserva si se elimina el controlador de entrada. La dirección IP no permanece si elimina el clúster de AKS.
Al actualizar el controlador de entrada, debe pasar un parámetro a la versión de Helm para asegurarse de que el servicio del controlador de entrada tenga en cuenta el equilibrador de carga que se le asignará. Para que los certificados HTTPS funcionen correctamente se usa una etiqueta DNS para configurar un FQDN para la dirección IP del controlador de entrada.
El FQDN debe seguir este formato: $MY_DNS_LABEL. AZURE_REGION_NAME.cloudapp.azure.com.

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

Agregue el parámetro --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"="<DNS_LABEL>". La etiqueta DNS se puede establecer cuando el controlador de entrada se implementa por primera vez, o bien más adelante. Agregue el parámetro --set controller.service.loadBalancerIP="<STATIC_IP>". Especifique su propia dirección IP pública creada en el paso anterior.

1. Adición del repositorio de Helm ingress-nginx

    ```bash
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    ```

2. Actualización de la caché del repositorio de gráficos local de Helm

    ```bash
    helm repo update
    ```

3. Instale el complemento ingress-nginx a través de Helm mediante la ejecución de lo siguiente:

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic ingress-nginx ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --create-namespace \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"=$MY_DNS_LABEL \
        --set controller.service.loadBalancerIP=$MY_STATIC_IP \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
        --wait --timeout 10m0s
    ```

## Adición de la terminación HTTPS al dominio personalizado

En este punto del tutorial tiene una aplicación web de AKS con NGINX como controlador de entrada y un dominio personalizado que puede usar para acceder a la aplicación. El siguiente paso consiste en agregar un certificado SSL al dominio para que los usuarios puedan acceder a la aplicación de forma segura a través de https.

## Implementación del administrador de certificados

Para agregar HTTPS vamos a usar el administrador de certificados. El administrador de certificados es una herramienta de código abierto que se usa para obtener y administrar certificados SSL para implementaciones de Kubernetes. El administrador de certificados obtiene los certificados de diversos emisores, tanto emisores públicos populares como emisores privados, y garantiza que los certificados sean válidos y estén actualizados, e intenta renovar los certificados en un momento configurado antes de la fecha de caducidad.

1. Para instalar el administrador de certificados, primero debemos crear un espacio de nombres en el que ejecutarlo. En este tutorial se instalará el administrador de certificados en el espacio de nombres cert-manager. Es posible ejecutar el administrador de certificados en un espacio de nombres diferente, aunque tendrá que realizar modificaciones en los manifiestos de implementación.

    ```bash
    kubectl create namespace cert-manager
    ```

2. Ahora podemos instalar el administrador de certificados. Todos los recursos están incluidos en un solo archivo de manifiesto de YAML. Para instalarlo, ejecute:

    ```bash
    kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
    ```

3. Para agregar la etiqueta certmanager.k8s.io/disable-validation: "true" al espacio de nombres cert-manager, ejecute lo siguiente. Esto permitirá que los recursos del sistema que necesita el administrador de certificados para arrancar TLS se creen en su propio espacio de nombres.

    ```bash
    kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
    ```

## Obtención de certificados mediante gráficos de Helm

Helm es una herramienta de implementación de Kubernetes para automatizar la creación, empaquetado, configuración e implementación de aplicaciones y servicios en clústeres de Kubernetes.

El administrador de certificados proporciona gráficos de Helm como método de instalación de primera clase en Kubernetes.

1. Adición del repositorio de Helm de Jetstack

    Este repositorio es el único origen admitido de gráficos del administrador de certificados. Hay otros reflejos y copias en Internet, pero esos no son oficiales en absoluto y podrían suponer un riesgo de seguridad.

    ```bash
    helm repo add jetstack https://charts.jetstack.io
    ```

2. Actualización de la caché del repositorio de gráficos local de Helm

    ```bash
    helm repo update
    ```

3. Para instalar el complemento del administrador de certificados a través de Helm, haga lo siguiente:

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. Aplicación del archivo YAML del emisor de certificados

    Los ClusterIssuers son recursos de Kubernetes que representan entidades de certificación (CA) capaces de generar certificados firmados aceptando solicitudes de firma de certificados. Todos los certificados del administrador de certificados requieren un emisor al que se haga referencia que esté preparado para intentar aceptar la solicitud.
    El emisor que vamos a usar se puede encontrar en el archivo `cluster-issuer-prod.yml file`.

    ```bash
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## Creación de una clase de almacenamiento personalizada

Las clases de almacenamiento predeterminadas se adaptan a los escenarios más comunes, pero no a todos. En algunos casos, puede que quiera tener una clase de almacenamiento propia personalizada con sus propios parámetros. Por ejemplo, use el siguiente manifiesto para configurar el parámetro mountOptions del recurso compartido de archivos.
El valor predeterminado de fileMode y dirMode es 0755 para los recursos compartidos de archivos montados en Kubernetes. Puede especificar las diferentes opciones de montaje en el objeto de clase de almacenamiento.

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## Implementación de WordPress en el clúster de AKS

Para este documento, usamos un gráfico de Helm para WordPress existente creado por Bitnami. Por ejemplo, el gráfico de Helm de Bitnami usa MariaDB local como base de datos y es necesario invalidar estos valores para usar la aplicación con Azure Database for MySQL. Todos los valores de invalidación. Se pueden invalidar los valores y la configuración personalizada se puede encontrar en el archivo `helm-wp-aks-values.yaml`.

1. Adición del repositorio de Helm de Bitnami de Wordpress

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. Actualización de la caché del repositorio de gráficos local de Helm

    ```bash
    helm repo update
    ```

3. Instale la carga de trabajo de Wordpress a través de Helm mediante la ejecución de lo siguiente:

    ```bash
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

## Examinar la implementación de AKS protegida a través de HTTPS

Ejecute el siguiente comando para obtener el punto de conexión HTTPS de la aplicación:

> [!NOTE]
> A menudo, el certificado SSL tarda entre 2 y 3 minutos en propagarse y unos 5 minutos para que todas las réplicas de pod de WordPress estén listas y el sitio sea totalmente accesible a través de https.

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

Comprobar que el contenido de WordPress se está entregando correctamente.

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

El sitio web se puede visitar siguiendo la dirección URL siguiente:

```bash
echo "You can now visit your web server at https://$FQDN"
```
