---
title: 'Inicio rápido: Implementación de un clúster de Azure Kubernetes Service escalable y seguro mediante la CLI de Azure'
description: 'En este tutorial, le guiaremos paso a paso en la creación de una aplicación web de Azure Kubernetes protegida mediante https.'
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Inicio rápido: Implementación de un clúster de Azure Kubernetes Service escalable y seguro mediante la CLI de Azure

[![Implementación en Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262758)

Te damos la bienvenida a este tutorial en el que le guiaremos paso a paso en la creación de una aplicación web de Azure Kubernetes protegida mediante https. En este tutorial se supone que ya ha iniciado sesión en la CLI de Azure y ha seleccionado una suscripción para usarla con la CLI. También supone que tiene Helm instalado ([Las instrucciones se pueden encontrar aquí](https://helm.sh/docs/intro/install/)).

## Definición de las variables de entorno

El primer paso de este tutorial es definir variables de entorno.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export NETWORK_PREFIX="$(($RANDOM % 254 + 1))"
export SSL_EMAIL_ADDRESS="$(az account show --query user.name --output tsv)"
export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_PUBLIC_IP_NAME="myPublicIP$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
export MY_VNET_NAME="myVNet$RANDOM_ID"
export MY_VNET_PREFIX="10.$NETWORK_PREFIX.0.0/16"
export MY_SN_NAME="mySN$RANDOM_ID"
export MY_SN_PREFIX="10.$NETWORK_PREFIX.0.0/22"
export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
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
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myAKSResourceGroupxxxxxx",
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

```JSON
{
  "newVNet": {
    "addressSpace": {
      "addressPrefixes": [
        "10.xxx.0.0/16"
      ]
    },
    "enableDdosProtection": false,
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/myAKSResourceGroupxxxxxx/providers/Microsoft.Network/virtualNetworks/myVNetxxx",
    "location": "eastus",
    "name": "myVNetxxx",
    "provisioningState": "Succeeded",
    "resourceGroup": "myAKSResourceGroupxxxxxx",
    "subnets": [
      {
        "addressPrefix": "10.xxx.0.0/22",
        "delegations": [],
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/myAKSResourceGroupxxxxxx/providers/Microsoft.Network/virtualNetworks/myVNetxxx/subnets/mySNxxx",
        "name": "mySNxxx",
        "privateEndpointNetworkPolicies": "Disabled",
        "privateLinkServiceNetworkPolicies": "Enabled",
        "provisioningState": "Succeeded",
        "resourceGroup": "myAKSResourceGroupxxxxxx",
        "type": "Microsoft.Network/virtualNetworks/subnets"
      }
    ],
    "type": "Microsoft.Network/virtualNetworks",
    "virtualNetworkPeerings": []
  }
}
```

## Registro en AKS de los proveedores de recursos de Azure

Compruebe que los proveedores Microsoft.OperationsManagement y Microsoft.OperationalInsights están registrados en la suscripción. Estos son proveedores de recursos de Azure necesarios para admitir [Container Insights](https://docs.microsoft.com/azure/azure-monitor/containers/container-insights-overview). Ejecute los siguientes comandos para comprobar el estado del registro.

```bash
az provider register --namespace Microsoft.Insights
az provider register --namespace Microsoft.OperationsManagement
az provider register --namespace Microsoft.OperationalInsights
```

## Crear clúster de AKS

Cree un clúster de AKS con el comando az aks create con el parámetro --enable-addons monitoring para habilitar Container Insights. En el ejemplo siguiente se crea un clúster habilitado para zonas de disponibilidad y escalado automático.

Esta operación puede tardar unos minutos.

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

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"=$MY_DNS_LABEL \
  --set controller.service.loadBalancerIP=$MY_STATIC_IP \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
  --wait
```

## Implementación de la aplicación

Un archivo de manifiesto de Kubernetes define el estado deseado del clúster, por ejemplo, qué imágenes de contenedor se van a ejecutar.

En este inicio rápido se usa un manifiesto para crear todos los objetos necesarios para ejecutar la aplicación Azure Vote. Este manifiesto incluye dos implementaciones de Kubernetes:

- Las aplicaciones de Python de ejemplo de Azure Vote.
- Una instancia de Redis.

También se crean dos servicios de Kubernetes:

- Un servicio interno para la instancia de Redis.
- Un servicio externo para acceder a la aplicación Azure Vote desde Internet.

Por último, se crea un recurso de entrada para enrutar el tráfico a la aplicación Azure Vote.

Ya está preparado un archivo YML de la aplicación de votación de prueba. Para implementar esta aplicación, ejecute el siguiente comando

```bash
kubectl apply -f azure-vote-start.yml
```

## Probar la aplicación

Para comprobar que la aplicación se está ejecutando visite la dirección IP pública o la dirección URL de la aplicación. Para encontrar la dirección URL de la aplicación, ejecute el comando siguiente:

> [!Note]
> A menudo se tarda entre 2 y 3 minutos en crear los POD y en acceder al sitio a través de HTTP.

```bash
runtime="5 minute";
endtime=$(date -ud "$runtime" +%s);
while [[ $(date -u +%s) -le $endtime ]]; do
   STATUS=$(kubectl get pods -l app=azure-vote-front -o 'jsonpath={..status.conditions[?(@.type=="Ready")].status}'); echo $STATUS;
   if [ "$STATUS" == 'True' ]; then
      break;
   else
      sleep 10;
   fi;
done
```

```bash
curl "http://$FQDN"
```

Resultados:

<!-- expected_similarity=0.3 -->

```HTML
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <link rel="stylesheet" type="text/css" href="/static/default.css">
    <title>Azure Voting App</title>

    <script language="JavaScript">
        function send(form){
        }
    </script>

</head>
<body>
    <div id="container">
        <form id="form" name="form" action="/"" method="post"><center>
        <div id="logo">Azure Voting App</div>
        <div id="space"></div>
        <div id="form">
        <button name="vote" value="Cats" onclick="send()" class="button button1">Cats</button>
        <button name="vote" value="Dogs" onclick="send()" class="button button2">Dogs</button>
        <button name="vote" value="reset" onclick="send()" class="button button3">Reset</button>
        <div id="space"></div>
        <div id="space"></div>
        <div id="results"> Cats - 0 | Dogs - 0 </div>
        </form>
        </div>
    </div>
</body>
</html>
```

## Adición de la terminación HTTPS al dominio personalizado

En este punto del tutorial tiene una aplicación web de AKS con NGINX como controlador de entrada y un dominio personalizado que puede usar para acceder a la aplicación. El siguiente paso consiste en agregar un certificado SSL al dominio para que los usuarios puedan acceder a la aplicación de forma segura a través de HTTPS.

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
   helm install cert-manager jetstack/cert-manager --namespace cert-manager --version v1.7.0
   ```

4. Aplicación del archivo YAML del emisor de certificados

   Los ClusterIssuers son recursos de Kubernetes que representan entidades de certificación (CA) capaces de generar certificados firmados aceptando solicitudes de firma de certificados. Todos los certificados del administrador de certificados requieren un emisor al que se haga referencia que esté preparado para intentar aceptar la solicitud.
   El emisor que vamos a usar se puede encontrar en el archivo `cluster-issuer-prod.yml file`.

   ```bash
   cluster_issuer_variables=$(<cluster-issuer-prod.yml)
   echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
   ```

5. Actualice la aplicación de votaciones para que use el administrador de certificados para obtener un certificado SSL.

   El archivo YAML completo se puede encontrar en `azure-vote-nginx-ssl.yml`.

   ```bash
   azure_vote_nginx_ssl_variables=$(<azure-vote-nginx-ssl.yml)
   echo "${azure_vote_nginx_ssl_variables//\$FQDN/$FQDN}" | kubectl apply -f -
   ```

<!--## Validate application is working

Wait for the SSL certificate to issue. The following command will query the 
status of the SSL certificate for 3 minutes. In rare occasions it may take up to 
15 minutes for Lets Encrypt to issue a successful challenge and 
the ready state to be 'True'

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(kubectl get certificate --output jsonpath={..status.conditions[0].status}); echo $STATUS; if [ "$STATUS" = 'True' ]; then break; else sleep 10; fi; done
```

Validate SSL certificate is True by running the follow command:

```bash
kubectl get certificate --output jsonpath={..status.conditions[0].status}
```

Results:

<!-- expected_similarity=0.3 -->
<!--
```ASCII
True
```
-->

## Examinar la implementación de AKS protegida a través de HTTPS

Ejecute el siguiente comando para obtener el punto de conexión HTTPS de la aplicación:

> [!Note]
> A menudo se tarda entre 2 y 3 minutos en propagarse el certificado SSL y en poder acceder al sitio a través de HTTP.

```bash
runtime="5 minute";
endtime=$(date -ud "$runtime" +%s);
while [[ $(date -u +%s) -le $endtime ]]; do
   STATUS=$(kubectl get svc --namespace=ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}');
   echo $STATUS;
   if [ "$STATUS" == "$MY_STATIC_IP" ]; then
      break;
   else
      sleep 10;
   fi;
done
```

```bash
echo "You can now visit your web server at https://$FQDN"
```

## Pasos siguientes

- [Documentación de Azure Kubernetes Service](https://learn.microsoft.com/azure/aks/)
- [Creación de una instancia de Azure Container Registry](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-prepare-acr?tabs=azure-cli)
- [Escalar la aplicación en AKS](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-scale?tabs=azure-cli)
- [Actualizar la aplicación en AKS](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-app-update?tabs=azure-cli)
