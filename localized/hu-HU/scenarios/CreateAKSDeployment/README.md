---
title: Skálázható és biztonságos Azure Kubernetes Service-fürt üzembe helyezése az Azure CLI használatával
description: Ebben az oktatóanyagban lépésről lépésre haladva létrehozunk egy Https használatával védett Azure Kubernetes-webalkalmazást.
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Rövid útmutató: Skálázható és biztonságos Azure Kubernetes Service-fürt üzembe helyezése az Azure CLI használatával

[![Üzembe helyezés az Azure-ban](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/?Microsoft_Azure_CloudNative_clientoptimizations=false&feature.canmodifyextensions=true#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateAKSDeployment)

Üdvözöljük ebben az oktatóanyagban, amelyben lépésről lépésre haladva létrehozunk egy Https-en keresztül biztonságos Azure Kubernetes-webalkalmazást. Ez az oktatóanyag feltételezi, hogy már bejelentkezett az Azure CLI-be, és kiválasztotta a parancssori felülettel használni kívánt előfizetést. Azt is feltételezi, hogy a Helm telepítve van ([az utasítások itt](https://helm.sh/docs/intro/install/) találhatók).

## Környezeti változók definiálása

Az oktatóanyag első lépése a környezeti változók definiálása.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export NETWORK_PREFIX="$(($RANDOM % 254 + 1))"
export SSL_EMAIL_ADDRESS="$(az account show --query user.name --output tsv)"
export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID"
export REGION="eastus"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_PUBLIC_IP_NAME="myPublicIP$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
export MY_VNET_NAME="myVNet$RANDOM_ID"
export MY_VNET_PREFIX="10.$NETWORK_PREFIX.0.0/16"
export MY_SN_NAME="mySN$RANDOM_ID"
export MY_SN_PREFIX="10.$NETWORK_PREFIX.0.0/22"
export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
```

## Erőforráscsoport létrehozása

Az erőforráscsoportok a kapcsolódó erőforrások tárolói. Minden erőforrást egy erőforráscsoportba kell helyezni. Létrehozunk egyet ehhez az oktatóanyaghoz. A következő parancs létrehoz egy erőforráscsoportot a korábban definiált $MY_RESOURCE_GROUP_NAME és $REGION paraméterekkel.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Eredmények:

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

## Virtuális hálózat és alhálózat létrehozása

A virtuális hálózat az Azure-beli magánhálózatok alapvető építőeleme. Az Azure Virtual Network lehetővé teszi, hogy az Azure-erőforrások, például a virtuális gépek biztonságosan kommunikáljanak egymással és az internettel.

```bash
az network vnet create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --name $MY_VNET_NAME \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefixes $MY_SN_PREFIX
```

Eredmények:

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

## Regisztráció az AKS Azure-erőforrás-szolgáltatókhoz

Ellenőrizze, hogy a Microsoft.OperationsManagement és a Microsoft.Operational Elemzések szolgáltatók regisztrálva vannak-e az előfizetésében. Ezek az Azure-erőforrás-szolgáltatók szükségesek a Container Insights[ támogatásához](https://docs.microsoft.com/azure/azure-monitor/containers/container-insights-overview). A regisztrációs állapot ellenőrzéséhez futtassa az alábbi parancsokat

```bash
az provider register --namespace Microsoft.Insights
az provider register --namespace Microsoft.OperationsManagement
az provider register --namespace Microsoft.OperationalInsights
```

## AKS-fürt létrehozása

Hozzon létre egy AKS-fürtöt az az aks create paranccsal az --enable-addons monitorozási paraméterrel a Container Insights engedélyezéséhez. Az alábbi példa egy automatikus skálázási, rendelkezésre állási zóna-kompatibilis fürtöt hoz létre.

Ez eltarthat néhány percig.

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

## Csatlakozás a fürthöz

Kubernetes-fürt kezeléséhez használja a Kubernetes parancssori ügyfelet, a kubectl-et. Az Azure Cloud Shell használata esetén a kubectl már telepítve van.

1. Az az aks CLI helyi telepítése az az aks install-cli paranccsal

   ```bash
   if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
   ```

2. A Kubectl konfigurálása a Kubernetes-fürthöz való csatlakozáshoz az az aks get-credentials paranccsal. A következő parancs:

   - Letölti a hitelesítő adatokat, és konfigurálja a Kubernetes parancssori felületét a használatukhoz.
   - A Kubernetes-konfigurációs fájl alapértelmezett helye a ~/.kube/config. Adjon meg egy másik helyet a Kubernetes-konfigurációs fájlhoz a --file argumentum használatával.

   > [!WARNING]
   > Ez felülírja a meglévő hitelesítő adatokat ugyanazzal a bejegyzéssel

   ```bash
   az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
   ```

3. Ellenőrizze a fürthöz való kapcsolatot a kubectl get paranccsal. Ez a parancs a fürtcsomópontok listáját adja vissza.

   ```bash
   kubectl get nodes
   ```

## NGINX bejövőforgalom-vezérlő telepítése

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

## Az alkalmazás üzembe helyezése

A Kubernetes-jegyzékfájl meghatározza a fürt kívánt állapotát, például hogy mely tárolólemezképeket kell futtatni.

Ebben a rövid útmutatóban egy jegyzék használatával hozza létre az Azure Vote alkalmazás futtatásához szükséges összes objektumot. Ez a jegyzék két Kubernetes-üzembe helyezést tartalmaz:

- A minta Azure Vote Python-alkalmazások.
- Egy Redis-példány.

Két Kubernetes-szolgáltatás is létrejön:

- A Redis-példány belső szolgáltatása.
- Egy külső szolgáltatás, amely az Azure Vote-alkalmazást az internetről éri el.

Végül létrejön egy bejövő erőforrás, amely átirányítja a forgalmat az Azure Vote alkalmazásba.

A teszt szavazóalkalmazás YML-fájlja már elkészült. Az alkalmazás üzembe helyezéséhez futtassa a következő parancsot

```bash
kubectl apply -f azure-vote-start.yml
```

## Az alkalmazás tesztelése

Ellenőrizze, hogy az alkalmazás fut-e a nyilvános IP-cím vagy az alkalmazás URL-címének felkeresésével. Az alkalmazás URL-címe a következő parancs futtatásával található:

> [!Note]
> Gyakran 2-3 percet vesz igénybe a poD-k létrehozása és a webhely HTTP-n keresztüli elérése

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

Eredmények:

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

## HTTPS-megszakítás hozzáadása egyéni tartományhoz

Az oktatóanyag ezen szakaszában egy NGINX-et használó AKS-webalkalmazással rendelkezik bejövőforgalom-vezérlőként, és egy egyéni tartományt, amellyel hozzáférhet az alkalmazáshoz. A következő lépés egy SSL-tanúsítvány hozzáadása a tartományhoz, hogy a felhasználók biztonságosan elérjék az alkalmazást HTTPS-en keresztül.

## A Cert Manager beállítása

A HTTPS hozzáadásához a Cert Managert fogjuk használni. A Cert Manager egy nyílt forráskód eszköz, aMellyel SSL-tanúsítványt szerezhet be és kezelhet a Kubernetes-környezetekhez. A Cert Manager számos kiállítótól szerez be tanúsítványokat, mind a népszerű nyilvános kiállítóktól, mind a magánkibocsátóktól, és gondoskodik arról, hogy a tanúsítványok érvényesek és naprakészek legyenek, és a lejárat előtt egy konfigurált időpontban megkísérli megújítani a tanúsítványokat.

1. A tanúsítványkezelő telepítéséhez először létre kell hoznunk egy névteret a futtatáshoz. Ez az oktatóanyag telepíti a cert-managert a cert-manager névtérbe. A tanúsítványkezelőt másik névtérben is futtathatja, bár módosítania kell az üzembehelyezési jegyzékeket.

   ```bash
   kubectl create namespace cert-manager
   ```

2. Most már telepítheti a cert-managert. Minden erőforrás egyetlen YAML-jegyzékfájlban található. Ez az alábbiak futtatásával telepíthető:

   ```bash
   kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
   ```

3. Adja hozzá a certmanager.k8s.io/disable-validation: "true" címkét a cert-manager névtérhez az alábbiak futtatásával. Ez lehetővé teszi, hogy a cert-manager által igényelt rendszererőforrások a TLS-t a saját névterében hozzák létre.

   ```bash
   kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
   ```

## Tanúsítvány beszerzése Helm-diagramokkal

A Helm egy Kubernetes-üzembehelyezési eszköz az alkalmazások és szolgáltatások Kubernetes-fürtökben való létrehozásának, csomagolásának, konfigurálásának és üzembe helyezésének automatizálásához.

A Cert-manager a Helm-diagramokat első osztályú telepítési módszerként biztosítja a Kubernetesen.

1. A Jetstack Helm-adattár hozzáadása

   Ez az adattár a cert-manager diagramok egyetlen támogatott forrása. Vannak más tükrözések és másolatok az interneten keresztül, de ezek teljesen nem hivatalosak, és biztonsági kockázatot jelenthetnek.

   ```bash
   helm repo add jetstack https://charts.jetstack.io
   ```

2. Helyi Helm Chart-adattár gyorsítótárának frissítése

   ```bash
   helm repo update
   ```

3. Telepítse a Cert-Manager bővítményt a helmel a következő futtatásával:

   ```bash
   helm install cert-manager jetstack/cert-manager --namespace cert-manager --version v1.7.0
   ```

4. Tanúsítványkibocsátó YAML-fájl alkalmazása

   A ClusterIssuers olyan Kubernetes-erőforrások, amelyek olyan hitelesítésszolgáltatókat (CA-kat) képviselnek, amelyek tanúsítvány-aláírási kérések teljesítésével képesek aláírt tanúsítványokat létrehozni. Minden tanúsítványkezelő tanúsítványhoz szükség van egy hivatkozott kiállítóra, amely készen áll a kérés teljesítésére.
   A használt kiállító a következő helyen található: `cluster-issuer-prod.yml file`

   ```bash
   cluster_issuer_variables=$(<cluster-issuer-prod.yml)
   echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
   ```

5. A szavazati alkalmazás alkalmazásának upate to use Cert-Manager to obtain an SSL Certificate.

   A teljes YAML-fájl a következő helyen található: `azure-vote-nginx-ssl.yml`

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

## Böngésszen a HTTPS-en keresztül biztonságos AKS-telepítés között

Futtassa a következő parancsot az alkalmazás HTTPS-végpontjának lekéréséhez:

> [!Note]
> Az SSL-tanúsítvány gyakran 2-3 percet vesz igénybe, és a webhely HTTPS-en keresztül érhető el.

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

## Következő lépések

- [Az Azure Kubernetes Service dokumentációja](https://learn.microsoft.com/azure/aks/)
- [Azure Container Registry létrehozása](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-prepare-acr?tabs=azure-cli)
- [Applciation skálázása az AKS-ben](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-scale?tabs=azure-cli)
- [Az alkalmazás frissítése az AKS-ben](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-app-update?tabs=azure-cli)
