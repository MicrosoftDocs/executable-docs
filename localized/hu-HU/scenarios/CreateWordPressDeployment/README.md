---
title: Méretezhető és biztonságos WordPress-példány üzembe helyezése az AKS-ben
description: 'Ez az oktatóanyag bemutatja, hogyan helyezhet üzembe skálázható és biztonságos WordPress-példányt az AKS-en parancssori felületen'
author: adrian.joian
ms.author: adrian.joian
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Rövid útmutató: Méretezhető és biztonságos WordPress-példány üzembe helyezése az AKS-ben

Üdvözöljük ebben az oktatóanyagban, amelyben lépésről lépésre haladva létrehozunk egy Https-en keresztül biztonságos Azure Kubernetes-webalkalmazást. Ez az oktatóanyag feltételezi, hogy már bejelentkezett az Azure CLI-be, és kiválasztotta a parancssori felülettel használni kívánt előfizetést. Azt is feltételezi, hogy a Helm telepítve van ([az utasítások itt](https://helm.sh/docs/intro/install/) találhatók).

## Környezeti változók definiálása

Az oktatóanyag első lépése a környezeti változók definiálása.

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

## Erőforráscsoport létrehozása

Az erőforráscsoportok a kapcsolódó erőforrások tárolói. Minden erőforrást egy erőforráscsoportba kell helyezni. Létrehozunk egyet ehhez az oktatóanyaghoz. A következő parancs létrehoz egy erőforráscsoportot a korábban definiált $MY_RESOURCE_GROUP_NAME és $REGION paraméterekkel.

```bash
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION
```

Eredmények:

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

## Rugalmas Azure Database for MySQL-kiszolgáló létrehozása

A rugalmas Azure Database for MySQL-kiszolgáló egy felügyelt szolgáltatás, amellyel magas rendelkezésre állású MySQL-kiszolgálókat futtathat, kezelhet és skálázhat a felhőben. Hozzon létre egy rugalmas kiszolgálót az az [mysql flexible-server create](https://learn.microsoft.com/cli/azure/mysql/flexible-server#az-mysql-flexible-server-create) paranccsal. Egy kiszolgáló több adatbázist tartalmazhat. Az alábbi parancs létrehoz egy kiszolgálót az Azure CLI helyi környezetéből származó szolgáltatás alapértelmezései és változó értékei alapján:

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

Eredmények:

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

A létrehozott kiszolgáló az alábbi attribútumokkal rendelkezik:

- A kiszolgálónév, a rendszergazdai felhasználónév, a rendszergazdai jelszó, az erőforráscsoport neve és a hely már meg van adva a felhőhéj helyi környezetében, és ugyanabban a helyen lesz létrehozva, ahol Ön az erőforráscsoport és a többi Azure-összetevő.
- A fennmaradó kiszolgálókonfigurációk szolgáltatás alapértelmezései: számítási szint (Burstable), számítási méret/termékváltozat (Standard_B2s), biztonsági mentés megőrzési időtartama (7 nap) és MySQL-verzió (8.0.21)
- Az alapértelmezett kapcsolati módszer a privát hozzáférés (VNet-integráció) egy csatolt virtuális hálózattal és egy automatikusan létrehozott alhálózattal.

> [!NOTE]
> A kapcsolati módszer nem módosítható a kiszolgáló létrehozása után. Ha például a létrehozás során van kiválasztva `Private access (VNet Integration)` , akkor a létrehozás után nem válthat rá `Public access (allowed IP addresses)` . Javasoljuk, hogy hozzon létre egy privát hozzáféréssel rendelkező kiszolgálót, hogy biztonságosan elérhesse a kiszolgálót a VNet-integráció használatával. További információ a privát hozzáférésről az [alapfogalmakról szóló cikkben](https://learn.microsoft.com/azure/mysql/flexible-server/concepts-networking-vnet).

Ha módosítani szeretné az alapértelmezett beállításokat, tekintse meg az Azure CLI [referenciadokumentációját](https://learn.microsoft.com/cli/azure//mysql/flexible-server) a konfigurálható CLI-paraméterek teljes listájához.

## Ellenőrizze az Azure Database for MySQL rugalmas kiszolgálói állapotát

A rugalmas Azure Database for MySQL-kiszolgáló és a támogató erőforrások létrehozása néhány percet vesz igénybe.

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## Kiszolgálóparaméterek konfigurálása az Azure Database for MySQL-ben – rugalmas kiszolgáló

Az Azure Database for MySQL rugalmas kiszolgálókonfigurációját kiszolgálóparaméterekkel kezelheti. A kiszolgálóparaméterek a kiszolgáló létrehozásakor az alapértelmezett és ajánlott értékkel vannak konfigurálva.

A kiszolgálóparaméter részleteinek megjelenítése A kiszolgáló adott paraméterének részleteinek megjelenítéséhez futtassa az az [mysql flexible-server parameter show](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter) parancsot.

### Az Azure Database for MySQL letiltása – Rugalmas kiszolgálói SSL-kapcsolati paraméter a WordPress-integrációhoz

Módosíthatja bizonyos kiszolgálóparaméterek értékét is, amelyek frissítik a MySQL-kiszolgálómotor mögöttes konfigurációs értékeit. A kiszolgálóparaméter frissítéséhez használja az az [mysql flexible-server paraméterkészlet](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set) parancsot.

```bash
az mysql flexible-server parameter set \
    -g $MY_RESOURCE_GROUP_NAME \
    -s $MY_MYSQL_DB_NAME \
    -n require_secure_transport -v "OFF" -o JSON
```

Eredmények:

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

## AKS-fürt létrehozása

Hozzon létre egy AKS-fürtöt az az aks create paranccsal az --enable-addons monitorozási paraméterrel a Container Insights engedélyezéséhez. Az alábbi példa egy myAKSCluster nevű automatikus skálázási, rendelkezésre állási zóna-kompatibilis fürtöt hoz létre:

Ez néhány percet vesz igénybe

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

A bejövőforgalom-vezérlőt statikus nyilvános IP-címmel konfigurálhatja. A statikus nyilvános IP-cím megmarad, ha törli a bejövőforgalom-vezérlőt. Az IP-cím nem marad meg, ha törli az AKS-fürtöt.
A bejövőforgalom-vezérlő frissítésekor egy paramétert kell átadnia a Helm-kiadásnak, hogy a bejövőforgalom-vezérlő szolgáltatás értesüljön a terheléselosztóról, amely hozzá lesz rendelve. Ahhoz, hogy a HTTPS-tanúsítványok megfelelően működjenek, egy DNS-címkével konfiguráljon egy teljes tartománynevet a bejövőforgalom-vezérlő IP-címéhez.
A teljes tartománynévnek a következő űrlapot kell követnie: $MY_DNS_LABEL. AZURE_REGION_NAME.cloudapp.azure.com.

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

Adja hozzá a --set controller.service.annotations parancsot." service\.beta\.kubernetes\.io/azure-dns-label-name"="<DNS_LABEL>" paraméter. A DNS-címke beállítható a bejövőforgalom-vezérlő első üzembe helyezésekor, vagy később is konfigurálható. Adja hozzá a --set controller.service.loadBalancerIP="<STATIC_IP>" paramétert. Adja meg az előző lépésben létrehozott saját nyilvános IP-címét.

1. Az ingress-nginx Helm-adattár hozzáadása

    ```bash
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    ```

2. Helyi Helm Chart-adattár gyorsítótárának frissítése

    ```bash
    helm repo update
    ```

3. Telepítse az ingress-nginx bővítményt a Helmen keresztül az alábbiak futtatásával:

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic ingress-nginx ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --create-namespace \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"=$MY_DNS_LABEL \
        --set controller.service.loadBalancerIP=$MY_STATIC_IP \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
        --wait --timeout 10m0s
    ```

## HTTPS-megszakítás hozzáadása egyéni tartományhoz

Az oktatóanyag ezen szakaszában egy NGINX-et használó AKS-webalkalmazással rendelkezik bejövőforgalom-vezérlőként, és egy egyéni tartományt, amellyel hozzáférhet az alkalmazáshoz. A következő lépés egy SSL-tanúsítvány hozzáadása a tartományhoz, hogy a felhasználók biztonságosan elérjék az alkalmazást https-en keresztül.

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

3. Telepítse a Cert-Manager bővítményt a Helmen keresztül az alábbiak futtatásával:

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. Tanúsítványkibocsátó YAML-fájl alkalmazása

    A ClusterIssuers olyan Kubernetes-erőforrások, amelyek olyan hitelesítésszolgáltatókat (CA-kat) képviselnek, amelyek tanúsítvány-aláírási kérések teljesítésével képesek aláírt tanúsítványokat létrehozni. Minden tanúsítványkezelő tanúsítványhoz szükség van egy hivatkozott kiállítóra, amely készen áll a kérés teljesítésére.
    A használt kiállító a következő helyen található: `cluster-issuer-prod.yml file`

    ```bash
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## Egyéni tárosztály létrehozása

Az alapértelmezett tárolási osztályok megfelelnek a leggyakoribb forgatókönyveknek, de nem mindegyiknek. Bizonyos esetekben előfordulhat, hogy saját tárolóosztályt szeretne testreszabni a saját paramétereivel. Például a következő jegyzék használatával konfigurálhatja a fájlmegosztás mountOptions parancsait.
A fileMode és a dirMode alapértelmezett értéke a Kuberneteshez csatlakoztatott fájlmegosztások esetében 0755. A tárolási osztály objektumán különböző csatlakoztatási beállításokat adhat meg.

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## A WordPress üzembe helyezése az AKS-fürtben

Ebben a dokumentumban egy meglévő, Bitnami által készített Helm-diagramot használunk a WordPresshez. A Bitnami Helm-diagram például a helyi MariaDB-t használja adatbázisként, és felül kell bírálnunk ezeket az értékeket az alkalmazás Azure Database for MySQL-hez való használatához. Az összes felülbírálási érték: Felülbírálhatja az értékeket, és az egyéni beállítások megtalálhatók a fájlban `helm-wp-aks-values.yaml`

1. Adja hozzá a Wordpress Bitnami Helm-adattárat

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. Helyi Helm Chart-adattár gyorsítótárának frissítése

    ```bash
    helm repo update
    ```

3. Telepítse a Wordpress számítási feladatait a Helm-en keresztül a következő futtatásával:

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

Eredmények:

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

## Böngésszen a HTTPS-en keresztül biztonságos AKS-telepítés között

Futtassa a következő parancsot az alkalmazás HTTPS-végpontjának lekéréséhez:

> [!NOTE]
> Gyakran 2-3 percet vesz igénybe az SSL-tanúsítvány propogatása, és körülbelül 5 percig, amíg az összes WordPress POD-replika készen áll, és a webhely teljes mértékben elérhető https-en keresztül.

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

Annak ellenőrzése, hogy a WordPress-tartalom megfelelően van-e kézbesítve.

```bash
if curl -I -s -f https://$FQDN > /dev/null ; then 
    curl -L -s -f https://$FQDN 2> /dev/null | head -n 9
else 
    exit 1
fi;
```

Eredmények:

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

A webhely az alábbi URL-címen érhető el:

```bash
echo "You can now visit your web server at https://$FQDN"
```
