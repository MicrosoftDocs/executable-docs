---
title: 'Oktatóanyag: A WordPress üzembe helyezése AKS-fürtön az Azure CLI használatával'
description: 'Megtudhatja, hogyan hozhatja létre és helyezheti üzembe gyorsan a WordPresst az AKS-en a rugalmas Azure Database for MySQL-kiszolgálóval.'
ms.service: mysql
ms.subservice: flexible-server
author: mksuni
ms.author: sumuth
ms.topic: tutorial
ms.date: 3/20/2024
ms.custom: 'vc, devx-track-azurecli, innovation-engine, linux-related-content'
---

# Oktatóanyag: WordPress-alkalmazás üzembe helyezése az AKS-ben az Azure Database for MySQL-kiszolgálóval – rugalmas kiszolgáló

[!INCLUDE[applies-to-mysql-flexible-server](../includes/applies-to-mysql-flexible-server.md)]

[![Üzembe helyezés az Azure-ban](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262843)

Ebben az oktatóanyagban egy skálázható, HTTPS-en keresztül védett WordPress-alkalmazást helyez üzembe egy Rugalmas Azure Database for MySQL-kiszolgálóval rendelkező Azure Kubernetes Service-fürtön az Azure CLI használatával.
**[Az AKS](../../aks/intro-kubernetes.md)** egy felügyelt Kubernetes-szolgáltatás, amely lehetővé teszi a fürtök gyors üzembe helyezését és kezelését. **[A rugalmas Azure Database for MySQL-kiszolgáló](overview.md)** egy teljes mértékben felügyelt adatbázis-szolgáltatás, amely részletesebb vezérlést és rugalmasságot biztosít az adatbázis-kezelési funkciók és a konfigurációs beállítások felett.

> [!NOTE]
> Ez az oktatóanyag feltételezi a Kubernetes-fogalmak, a WordPress és a MySQL alapszintű megértését.

[!INCLUDE [flexible-server-free-trial-note](../includes/flexible-server-free-trial-note.md)]

## Előfeltételek 

Az első lépések előtt győződjön meg arról, hogy bejelentkezett az Azure CLI-be, és kiválasztotta a parancssori felülettel használni kívánt előfizetést. Győződjön meg arról, hogy telepítve[ van a ](https://helm.sh/docs/intro/install/)Helm.

> [!NOTE]
> Ha az oktatóanyagban szereplő parancsokat az Azure Cloud Shell helyett helyileg futtatja, futtassa a parancsokat rendszergazdaként.

## Erőforráscsoport létrehozása

Az Azure-erőforráscsoport olyan logikai csoport, amelyben az Azure-erőforrások üzembe helyezése és kezelése zajlik. Minden erőforrást egy erőforráscsoportba kell helyezni. Az alábbi parancs létrehoz egy erőforráscsoportot a korábban definiált `$MY_RESOURCE_GROUP_NAME` és `$REGION` paraméterekkel.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myWordPressAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
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

> [!NOTE]
> Az erőforráscsoport helye az erőforráscsoport metaadatainak tárolása. Az erőforrások akkor is az Azure-ban futnak, ha nem ad meg egy másik régiót az erőforrás létrehozása során.

## Virtuális hálózat és alhálózat létrehozása

A virtuális hálózat az Azure-beli magánhálózatok alapvető építőeleme. Az Azure Virtual Network lehetővé teszi, hogy az Azure-erőforrások, például a virtuális gépek biztonságosan kommunikáljanak egymással és az internettel.

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

## Rugalmas Azure Database for MySQL-kiszolgálópéldány létrehozása

A rugalmas Azure Database for MySQL-kiszolgáló egy felügyelt szolgáltatás, amellyel magas rendelkezésre állású MySQL-kiszolgálókat futtathat, kezelhet és méretezhet a felhőben. Hozzon létre egy rugalmas Azure Database for MySQL-kiszolgálópéldányt az az [mysql flexible-server create](/cli/azure/mysql/flexible-server) paranccsal. Egy kiszolgáló több adatbázist tartalmazhat. A következő parancs létrehoz egy kiszolgálót az Azure CLI helyi környezetéből származó szolgáltatás alapértelmezései és változó értékei alapján:

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

- A kiszolgáló első kiépítésekor létrejön egy új üres adatbázis.
- A kiszolgálónév, a rendszergazdai felhasználónév, a rendszergazdai jelszó, az erőforráscsoport neve és a hely már meg van adva a felhőhéj helyi környezetében, és ugyanazon a helyen vannak, mint az erőforráscsoport és más Azure-összetevők.
- A fennmaradó kiszolgálókonfigurációk alapértelmezett szolgáltatása a számítási szint (Burstable), a számítási méret/termékváltozat (Standard_B2s), a biztonsági mentés megőrzési időtartama (hét nap) és a MySQL-verzió (8.0.21).
- Az alapértelmezett kapcsolati módszer a privát hozzáférés (virtuális hálózat integrációja) egy csatolt virtuális hálózattal és egy automatikusan létrehozott alhálózattal.

> [!NOTE]
> A kapcsolati módszer nem módosítható a kiszolgáló létrehozása után. Ha például a létrehozás során van kiválasztva `Private access (VNet Integration)` , akkor a létrehozás után nem válthat át `Public access (allowed IP addresses)` . Javasoljuk, hogy hozzon létre egy privát hozzáféréssel rendelkező kiszolgálót, hogy biztonságosan elérhesse a kiszolgálót a VNet-integráció használatával. További információ a privát hozzáférésről az [alapfogalmakról szóló cikkben](./concepts-networking-vnet.md).

Ha módosítani szeretné az alapértelmezett beállításokat, tekintse meg az Azure CLI [referenciadokumentációját](/cli/azure//mysql/flexible-server) a konfigurálható CLI-paraméterek teljes listájához.

## Ellenőrizze az Azure Database for MySQL rugalmas kiszolgálói állapotát

A rugalmas Azure Database for MySQL-kiszolgáló és a támogató erőforrások létrehozása néhány percet vesz igénybe.

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## Kiszolgálóparaméterek konfigurálása az Azure Database for MySQL-ben – rugalmas kiszolgáló

Az Azure Database for MySQL rugalmas kiszolgálókonfigurációját kiszolgálóparaméterekkel kezelheti. A kiszolgálóparaméterek a kiszolgáló létrehozásakor az alapértelmezett és ajánlott értékkel vannak konfigurálva.

Egy kiszolgáló adott paraméterének részleteinek megjelenítéséhez futtassa az az [mysql rugalmas-kiszolgáló paraméterbemutató](/cli/azure/mysql/flexible-server/parameter) parancsot.

### Az Azure Database for MySQL letiltása – Rugalmas kiszolgálói SSL-kapcsolati paraméter a WordPress-integrációhoz

Bizonyos kiszolgálóparaméterek értékét is módosíthatja a MySQL-kiszolgálómotor mögöttes konfigurációs értékeinek frissítéséhez. A kiszolgálóparaméter frissítéséhez használja az az [mysql flexible-server paraméterkészlet](/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set) parancsot.

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

Ha AKS-fürtöt szeretne létrehozni a Container Insights használatával, használja az az aks [create](/cli/azure/aks#az-aks-create) parancsot az **--enable-addons monitorozási** paraméterrel. Az alábbi példa egy myAKSCluster** nevű **automatikus skálázási, rendelkezésre állási zóna-kompatibilis fürtöt hoz létre:

Ez a művelet néhány percet vesz igénybe.

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
> AKS-fürt létrehozásakor a rendszer automatikusan létrehoz egy második erőforráscsoportot az AKS-erőforrások tárolásához. Lásd: [Miért jön létre két erőforráscsoport az AKS-sel?](../../aks/faq.md#why-are-two-resource-groups-created-with-aks)

## Csatlakozás a fürthöz

Kubernetes-fürtök kezeléséhez használja a [kubectl](https://kubernetes.io/docs/reference/kubectl/overview/) eszközt, a Kubernetes parancssori ügyfelét. Ha az Azure Cloud Shellt használja, `kubectl` már telepítve van. Az alábbi példa helyileg telepíti `kubectl` az az aks [install-cli](/cli/azure/aks#az-aks-install-cli) parancsot. 

 ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
```

Ezután konfigurálja `kubectl` a Kubernetes-fürthöz való csatlakozást az az aks [get-credentials](/cli/azure/aks#az-aks-get-credentials) paranccsal. Ez a parancs letölti a hitelesítő adatokat, és konfigurálja a Kubernetes parancssori felületét a használatukhoz. A parancs a Kubernetes-konfigurációs fájl[ alapértelmezett helyét ](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/)használja`~/.kube/config`. A --file** argumentum használatával **megadhatja a Kubernetes-konfigurációs fájl egy másik helyét.

> [!WARNING]
> Ez a parancs felülírja a meglévő hitelesítő adatokat ugyanazzal a bejegyzéssel.

```bash
az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
```

A fürthöz való csatlakozás ellenőrzéséhez használja a [kubectl get]( https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#get) parancsot a fürtcsomópontok listájának lekéréséhez.

```bash
kubectl get nodes
```

## NGINX bejövőforgalom-vezérlő telepítése

A bejövőforgalom-vezérlőt statikus nyilvános IP-címmel konfigurálhatja. A statikus nyilvános IP-cím megmarad, ha törli a bejövőforgalom-vezérlőt. Az IP-cím nem marad meg, ha törli az AKS-fürtöt.
A bejövőforgalom-vezérlő frissítésekor egy paramétert kell átadnia a Helm-kiadásnak, hogy a bejövőforgalom-vezérlő szolgáltatás értesüljön a terheléselosztóról, amely hozzá lesz rendelve. Ahhoz, hogy a HTTPS-tanúsítványok megfelelően működjenek, egy DNS-címkével konfiguráljon egy teljes tartománynevet (FQDN) a bejövőforgalom-vezérlő IP-címéhez. A teljes tartománynévnek a következő űrlapot kell követnie: $MY_DNS_LABEL. AZURE_REGION_NAME.cloudapp.azure.com.

```bash
export MY_PUBLIC_IP_NAME="myPublicIP$RANDOM_ID"
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

Ezután hozzáadja az ingress-nginx Helm-adattárat, frissíti a helyi Helm-diagram adattár-gyorsítótárát, és telepíti az ingress-nginx bővítményt a Helmen keresztül. A DNS-címkét a **--set controller.service.annotations beállítással állíthatja be." service\.beta\.kubernetes\.io/azure-dns-label-name"="<DNS_LABEL>"** paraméter a bejövőforgalom-vezérlő vagy újabb telepítésekor. Ebben a példában az előző lépésben létrehozott saját nyilvános IP-címét adja meg a **--set controller.service.loadBalancerIP="<STATIC_IP>" paraméterrel**.

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

## HTTPS-megszakítás hozzáadása egyéni tartományhoz

Az oktatóanyag ezen szakaszában egy NGINX-et használó AKS-webalkalmazással rendelkezik bejövőforgalom-vezérlőként, valamint egy egyéni tartományt, amellyel hozzáférhet az alkalmazáshoz. A következő lépés egy SSL-tanúsítvány hozzáadása a tartományhoz, hogy a felhasználók biztonságosan elérjék az alkalmazást https-en keresztül.

### A Cert Manager beállítása

HTTPS hozzáadásához a Cert Managert fogjuk használni. A Cert Manager egy nyílt forráskód eszköz a Kubernetes-üzemelő példányok SSL-tanúsítványainak beszerzéséhez és kezeléséhez. A Cert Manager a népszerű nyilvános kiállítóktól és magánkibocsátóktól szerzi be a tanúsítványokat, gondoskodik arról, hogy a tanúsítványok érvényesek és naprakészek legyenek, és a tanúsítványokat a lejáratuk előtt konfigurált időpontban próbálja meg megújítani.

1. A tanúsítványkezelő telepítéséhez először létre kell hoznunk egy névteret a futtatáshoz. Ez az oktatóanyag telepíti a cert-managert a cert-manager névtérbe. A tanúsítványkezelőt másik névtérben is futtathatja, de módosítania kell az üzembehelyezési jegyzékeket.

    ```bash
    kubectl create namespace cert-manager
    ```

2. Most már telepítheti a cert-managert. Minden erőforrás egyetlen YAML-jegyzékfájlban található. Telepítse a jegyzékfájlt a következő paranccsal:

    ```bash
    kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
    ```

3. Adja hozzá a `certmanager.k8s.io/disable-validation: "true"` címkét a cert-manager névtérhez az alábbiak futtatásával. Ez lehetővé teszi, hogy a cert-manager által igényelt rendszererőforrások a TLS-t a saját névterében hozzák létre.

    ```bash
    kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
    ```

## Tanúsítvány beszerzése Helm-diagramokkal

A Helm egy Kubernetes-üzembehelyezési eszköz, amely automatizálja az alkalmazások és szolgáltatások Létrehozását, csomagolását, konfigurálását és üzembe helyezését a Kubernetes-fürtökben.

A Cert-manager a Helm-diagramokat első osztályú telepítési módszerként biztosítja a Kubernetesen.

1. Vegye fel a Jetstack Helm adattárat. Ez az adattár a cert-manager diagramok egyetlen támogatott forrása. Vannak más tükrözések és másolatok az interneten keresztül, de ezek nem hivatalosak, és biztonsági kockázatot jelenthetnek.

    ```bash
    helm repo add jetstack https://charts.jetstack.io
    ```

2. Frissítse a helyi Helm Chart-adattár gyorsítótárát.

    ```bash
    helm repo update
    ```

3. Telepítse a Cert-Manager bővítményt a Helm használatával.

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. A tanúsítványkibocsátó YAML-fájljának alkalmazása. A ClusterIssuers olyan Kubernetes-erőforrások, amelyek olyan hitelesítésszolgáltatókat (CA-kat) képviselnek, amelyek tanúsítvány-aláírási kérések teljesítésével létrehozhatnak aláírt tanúsítványokat. Minden tanúsítványkezelő tanúsítványhoz szükség van egy hivatkozott kiállítóra, amely készen áll a kérés teljesítésére. Megtalálhatja a kiállítót, akiben `cluster-issuer-prod.yml file`a .

    ```bash
    export SSL_EMAIL_ADDRESS="$(az account show --query user.name --output tsv)"
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## Egyéni tárosztály létrehozása

Az alapértelmezett tárolási osztályok megfelelnek a leggyakoribb forgatókönyveknek, de nem mindegyiknek. Bizonyos esetekben előfordulhat, hogy saját tárolóosztályt szeretne testreszabni a saját paramétereivel. Például a következő jegyzék használatával konfigurálhatja a **fájlmegosztás mountOptions** parancsait.
A fileMode és a dirMode** **alapértelmezett értéke **a Kuberneteshez csatlakoztatott fájlmegosztások esetében 0755**.**** A tárolási osztály objektumán különböző csatlakoztatási beállításokat adhat meg.

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## A WordPress üzembe helyezése az AKS-fürtben

Ebben az oktatóanyagban egy meglévő Helm-diagramot használunk a Bitnami által készített WordPresshez. A Bitnami Helm-diagram egy helyi MariaDB-t használ adatbázisként, ezért felül kell bírálnunk ezeket az értékeket, hogy az alkalmazást az Azure Database for MySQL-hez használhassuk. Felülbírálhatja a fájl értékeit és egyéni beállításait `helm-wp-aks-values.yaml` .

1. Adja hozzá a Wordpress Bitnami Helm-adattárat.

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. Frissítse a helyi Helm-diagramtártár gyorsítótárát.

    ```bash
    helm repo update
    ```

3. Telepítse a Wordpress számítási feladatait a Helmen keresztül.

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

## Tallózás a HTTPS-en keresztül biztonságos AKS-üzembe helyezés között

Futtassa a következő parancsot az alkalmazás HTTPS-végpontjának lekéréséhez:

> [!NOTE]
> Az SSL-tanúsítvány propagálása gyakran 2-3 percet vesz igénybe, és körülbelül 5 percet vesz igénybe, hogy az összes WordPress POD-replika készen álljon, és a webhely teljes mértékben elérhető legyen https-en keresztül.

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

Ellenőrizze, hogy a WordPress-tartalom megfelelően van-e kézbesítve a következő paranccsal:

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

Látogasson el a webhelyre a következő URL-címen keresztül:

```bash
echo "You can now visit your web server at https://$FQDN"
```

## Erőforrások törlése (nem kötelező)

Az Azure-díjak elkerülése érdekében távolítsa el a szükségtelen erőforrásokat. Ha már nincs szüksége a fürtre, az az [group delete](/cli/azure/group#az-group-delete) paranccsal távolítsa el az erőforráscsoportot, a tárolószolgáltatást és az összes kapcsolódó erőforrást. 

> [!NOTE]
> A fürt törlésekor az AKS-fürt által használt Microsoft Entra szolgáltatásnév nem lesz eltávolítva. A szolgáltatásnév eltávolításának lépéseiért lásd [az AKS-szolgáltatásnevekre vonatkozó szempontokat és a szolgáltatásnevek törlését](../../aks/kubernetes-service-principal.md#other-considerations) ismertető cikket. Ha felügyelt identitást használt, az identitást a platform kezeli, és nem igényel eltávolítást.

## Következő lépések

- Megtudhatja, [hogyan érheti el az AKS-fürt Kubernetes webes irányítópultját](../../aks/kubernetes-dashboard.md)
- Megtudhatja, [hogyan méretezheti a fürtöt](../../aks/tutorial-kubernetes-scale.md)
- Ismerje meg, hogyan kezelheti rugalmas [Azure Database for MySQL-kiszolgálópéldányát](./quickstart-create-server-cli.md)
- Megtudhatja, hogyan konfigurálhatja az [adatbázis-kiszolgáló kiszolgálóparamétereit](./how-to-configure-server-parameters-cli.md)
