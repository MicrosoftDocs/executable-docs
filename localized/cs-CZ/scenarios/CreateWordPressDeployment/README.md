---
title: 'Kurz: Nasazení WordPressu v clusteru AKS pomocí Azure CLI'
description: 'Zjistěte, jak rychle sestavit a nasadit WordPress v AKS pomocí flexibilního serveru Azure Database for MySQL.'
ms.service: mysql
ms.subservice: flexible-server
author: mksuni
ms.author: sumuth
ms.topic: tutorial
ms.date: 3/20/2024
ms.custom: 'vc, devx-track-azurecli, innovation-engine, linux-related-content'
---

# Kurz: Nasazení aplikace WordPress v AKS s flexibilním serverem Azure Database for MySQL

[!INCLUDE[applies-to-mysql-flexible-server](../includes/applies-to-mysql-flexible-server.md)]

[![Nasazení do Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262843)

V tomto kurzu nasadíte škálovatelnou aplikaci WordPress zabezpečenou přes HTTPS v clusteru Azure Kubernetes Service (AKS) s flexibilním serverem Azure Database for MySQL pomocí Azure CLI.
**[AKS](../../aks/intro-kubernetes.md)** je spravovaná služba Kubernetes, která umožňuje rychle nasazovat a spravovat clustery. **[Flexibilní server](overview.md)** Azure Database for MySQL je plně spravovaná databázová služba navržená tak, aby poskytovala podrobnější kontrolu a flexibilitu nad funkcemi správy databází a nastavením konfigurace.

> [!NOTE]
> V tomto kurzu se předpokládá základní znalost konceptů Kubernetes, WordPressu a MySQL.

[!INCLUDE [flexible-server-free-trial-note](../includes/flexible-server-free-trial-note.md)]

## Požadavky 

Než začnete, ujistěte se, že jste přihlášeni k Azure CLI a vybrali předplatné, které se má použít s rozhraním příkazového řádku. Ujistěte se, že máte [nainstalovaný](https://helm.sh/docs/intro/install/) Helm.

> [!NOTE]
> Pokud příkazy v tomto kurzu spouštíte místně místo Azure Cloud Shellu, spusťte příkazy jako správce.

## Definování proměnných prostředí

Prvním krokem v tomto kurzu je definování proměnných prostředí.

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

## Vytvoření skupiny zdrojů

Skupina prostředků Azure je logická skupina, ve které se nasazují a spravují prostředky Azure. Všechny prostředky musí být umístěné ve skupině prostředků. Následující příkaz vytvoří skupinu prostředků s dříve definovanými `$MY_RESOURCE_GROUP_NAME` parametry a `$REGION` parametry.

```bash
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION
```

Výsledky:
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
> Umístění skupiny prostředků je místo, kde jsou uložena metadata skupiny prostředků. Pokud během vytváření prostředků nezadáte jinou oblast, je to také místo, kde se vaše prostředky spouštějí v Azure.

## Vytvoření virtuální sítě a podsítě

Virtuální síť je základním stavebním blokem privátních sítí v Azure. Azure Virtual Network umožňuje prostředkům Azure, jako jsou virtuální počítače, bezpečně komunikovat mezi sebou a internetem.

```bash
az network vnet create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --name $MY_VNET_NAME \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefixes $MY_SN_PREFIX
```

Výsledky:
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

## Vytvoření instance flexibilního serveru Azure Database for MySQL

Flexibilní server Azure Database for MySQL je spravovaná služba, kterou můžete použít ke spouštění, správě a škálování vysoce dostupných serverů MySQL v cloudu. Vytvořte instanci flexibilního serveru Azure Database for MySQL pomocí [příkazu az mysql flexible-server create](/cli/azure/mysql/flexible-server) . Server může obsahovat více databází. Následující příkaz vytvoří server s použitím výchozích hodnot služby a proměnných z místního kontextu Azure CLI:

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

Výsledky:
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

Vytvořený server má následující atributy:

- Při prvním zřízení serveru se vytvoří nová prázdná databáze.
- Název serveru, uživatelské jméno správce, heslo správce, název skupiny prostředků a umístění jsou již zadané v místním kontextovém prostředí cloud shellu a jsou ve stejném umístění jako vaše skupina prostředků a další komponenty Azure.
- Výchozí nastavení služby pro zbývající konfigurace serveru jsou výpočetní úroveň (burstable), velikost výpočetních prostředků a skladová položka (Standard_B2s), doba uchovávání záloh (sedm dnů) a MySQL verze (8.0.21).
- Výchozí metoda připojení je privátní přístup (integrace virtuální sítě) s propojenou virtuální sítí a automaticky vygenerovanou podsítí.

> [!NOTE]
> Po vytvoření serveru nelze změnit metodu připojení. Pokud jste například vybrali `Private access (VNet Integration)` během vytváření, nemůžete po vytvoření přejít na `Public access (allowed IP addresses)` . Důrazně doporučujeme vytvořit server s privátním přístupem pro bezpečný přístup k vašemu serveru pomocí integrace virtuální sítě. Další informace o privátním přístupu najdete v [článku](./concepts-networking-vnet.md) o konceptech.

Pokud chcete změnit výchozí hodnoty, projděte si referenční dokumentaci[ k Azure CLI](/cli/azure//mysql/flexible-server), kde najdete úplný seznam konfigurovatelných parametrů rozhraní příkazového řádku.

## Kontrola stavu flexibilního serveru Azure Database for MySQL

Vytvoření flexibilního serveru Azure Database for MySQL a podpůrných prostředků trvá několik minut.

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## Konfigurace parametrů serveru na flexibilním serveru Azure Database for MySQL

Konfiguraci flexibilního serveru Azure Database for MySQL můžete spravovat pomocí parametrů serveru. Parametry serveru se při vytváření serveru konfigurují s výchozí a doporučenou hodnotou.

Pokud chcete zobrazit podrobnosti o konkrétním parametru pro server, spusťte [příkaz az mysql flexible-server parameter show](/cli/azure/mysql/flexible-server/parameter) .

### Zakázání parametru připojení SSL flexibilního serveru azure Database for MySQL pro integraci WordPressu

Můžete také upravit hodnotu určitých parametrů serveru tak, aby se aktualizovaly základní konfigurační hodnoty pro serverový stroj MySQL. Pokud chcete aktualizovat parametr serveru, použijte [příkaz az mysql flexible-server parameter set](/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set) .

```bash
az mysql flexible-server parameter set \
    -g $MY_RESOURCE_GROUP_NAME \
    -s $MY_MYSQL_DB_NAME \
    -n require_secure_transport -v "OFF" -o JSON
```

Výsledky:
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

## Vytvoření clusteru AKS

Pokud chcete vytvořit cluster AKS s kontejnerem Přehledy, použijte [příkaz az aks create](/cli/azure/aks#az-aks-create) s parametrem **monitorování --enable-addons**. Následující příklad vytvoří cluster s podporou automatického škálování a zóny dostupnosti s názvem **myAKSCluster**:

Tato akce trvá několik minut.

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
> [!NOTE]
> Při vytváření clusteru AKS se automaticky vytvoří druhá skupina prostředků pro ukládání prostředků AKS. Přečtěte si, [proč se v AKS vytvářejí dvě skupiny prostředků?](../../aks/faq.md#why-are-two-resource-groups-created-with-aks)

## Připojení ke clusteru

Ke správě clusteru Kubernetes použijte klienta příkazového řádku Kubernetes [kubectl](https://kubernetes.io/docs/reference/kubectl/overview/). Pokud používáte Azure Cloud Shell, `kubectl` je už nainstalovaný. Následující příklad se nainstaluje `kubectl` místně pomocí [příkazu az aks install-cli](/cli/azure/aks#az-aks-install-cli) . 

 ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
```

Dále nakonfigurujte `kubectl` připojení ke clusteru Kubernetes pomocí [příkazu az aks get-credentials](/cli/azure/aks#az-aks-get-credentials) . Tento příkaz stáhne přihlašovací údaje a nakonfiguruje rozhraní příkazového řádku Kubernetes tak, aby je používalo. Příkaz používá `~/.kube/config`výchozí umístění konfiguračního [souboru](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/) Kubernetes. Pomocí argumentu **--file** můžete pro konfigurační soubor Kubernetes zadat jiné umístění.

> [!WARNING]
> Tento příkaz přepíše všechny existující přihlašovací údaje se stejnou položkou.

```bash
az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
```

Pokud chcete ověřit připojení ke clusteru, použijte příkaz [kubectl get]( https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#get), který vrátí seznam uzlů clusteru.

```bash
kubectl get nodes
```

## Instalace kontroleru příchozího přenosu dat NGINX

Kontroler příchozího přenosu dat můžete nakonfigurovat se statickou veřejnou IP adresou. Statická veřejná IP adresa zůstane, pokud odstraníte kontroler příchozího přenosu dat. IP adresa nezůstane, pokud odstraníte cluster AKS.
Při upgradu kontroleru příchozího přenosu dat musíte předat do verze Helm parametr, aby služba kontroleru příchozího přenosu dat věděla o nástroji pro vyrovnávání zatížení, který bude přidělen. Aby certifikáty HTTPS fungovaly správně, použijte popisek DNS ke konfiguraci plně kvalifikovaného názvu domény (FQDN) pro IP adresu kontroleru příchozího přenosu dat. Plně kvalifikovaný název domény by měl vypadat takto: $MY_DNS_LABEL. AZURE_REGION_NAME.cloudapp.azure.com.

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

Dále přidáte úložiště Helm ingress-nginx, aktualizujete místní mezipaměť úložiště Helm Chart a prostřednictvím Helmu nainstalujete doplněk ingress-nginx. Popisek DNS můžete nastavit pomocí **--set controller.service.annotations. service\.beta\.kubernetes\.io/azure-dns-label-name"="<DNS_LABEL>"** parametr buď při prvním nasazení kontroleru příchozího přenosu dat, nebo novějším. V tomto příkladu zadáte vlastní veřejnou IP adresu, kterou jste vytvořili v předchozím kroku pomocí parametru ****--set controller.service.loadBalancerIP="<STATIC_IP>".

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

## Přidání ukončení protokolu HTTPS do vlastní domény

V tomto okamžiku v kurzu máte webovou aplikaci AKS s NGINX jako kontrolerem příchozího přenosu dat a vlastní doménu, kterou můžete použít pro přístup k aplikaci. Dalším krokem je přidání certifikátu SSL do domény, aby se uživatelé mohli k vaší aplikaci bezpečně dostat přes https.

### Nastavení správce certifikátů

Pokud chcete přidat HTTPS, použijeme Správce certifikátů. Cert Manager je opensourcový nástroj pro získávání a správu certifikátů SSL pro nasazení Kubernetes. Cert Manager získává certifikáty od oblíbených veřejných vystavitelů a privátních vystavitelů, zajišťuje, že certifikáty jsou platné a aktuální, a pokusí se obnovit certifikáty v nakonfigurovaný čas před vypršením jejich platnosti.

1. Abychom mohli nainstalovat nástroj cert-manager, musíme nejprve vytvořit obor názvů pro jeho spuštění. Tento kurz nainstaluje nástroj cert-manager do oboru názvů cert-manager. Nástroj cert-manager můžete spustit v jiném oboru názvů, ale musíte provést změny manifestů nasazení.

    ```bash
    kubectl create namespace cert-manager
    ```

2. Teď můžeme nainstalovat nástroj cert-manager. Všechny prostředky jsou součástí jednoho souboru manifestu YAML. Nainstalujte soubor manifestu pomocí následujícího příkazu:

    ```bash
    kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
    ```

3. `certmanager.k8s.io/disable-validation: "true"` Přidejte popisek do oboru názvů cert-manager spuštěním následujícího příkazu. To umožňuje systémovým prostředkům, které cert-manager vyžaduje, aby se protokol TLS bootstrap vytvořil ve vlastním oboru názvů.

    ```bash
    kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
    ```

## Získání certifikátu prostřednictvím chartů Helm

Helm je nástroj pro nasazení Kubernetes pro automatizaci vytváření, balení, konfigurace a nasazení aplikací a služeb do clusterů Kubernetes.

Cert-manager poskytuje charty Helm jako prvotřídní metodu instalace v Kubernetes.

1. Přidejte úložiště Jetstack Helm. Toto úložiště je jediným podporovaným zdrojem grafů cert-manageru. Existují další zrcadla a kopie po internetu, ale ty jsou neoficiální a můžou představovat bezpečnostní riziko.

    ```bash
    helm repo add jetstack https://charts.jetstack.io
    ```

2. Aktualizujte místní mezipaměť úložiště Helm Chart.

    ```bash
    helm repo update
    ```

3. Nainstalujte doplněk Cert-Manager přes Helm.

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. Použijte soubor YAML vystavitele certifikátu. ClusterIssuers jsou prostředky Kubernetes, které představují certifikační autority(CA), které můžou generovat podepsané certifikáty tím, že dodržují žádosti o podepsání certifikátu. Všechny certifikáty cert-manager vyžadují odkazovaného vystavitele, který je v připravené podmínce, aby se pokusil požadavek respektovat. Můžete najít vystavitele, který jsme v sadě `cluster-issuer-prod.yaml file`.

    ```bash
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## Vytvoření vlastní třídy úložiště

Výchozí třídy úložiště odpovídají nejběžnějším scénářům, ale ne všem. V některých případech můžete chtít mít vlastní třídu úložiště přizpůsobenou vlastními parametry. Například pomocí následujícího manifestu **nakonfigurujte připojeníOptions** sdílené složky.
Výchozí hodnota pro **fileMode** a **dirMode** je **0755** pro připojené sdílené složky Kubernetes. U objektu třídy úložiště můžete zadat různé možnosti připojení.

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## Nasazení WordPressu do clusteru AKS

Pro účely tohoto kurzu používáme existující chart Helm pro WordPress vytvořený nástrojem Bitnami. Chart Bitnami Helm používá jako databázi místní MariaDB, takže musíme tyto hodnoty přepsat, aby se aplikace používala se službou Azure Database for MySQL. Můžete přepsat hodnoty a vlastní nastavení `helm-wp-aks-values.yaml` souboru.

1. Přidejte úložiště Wordpress Bitnami Helm.

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. Aktualizujte místní mezipaměť úložiště chartů Helm.

    ```bash
    helm repo update
    ```

3. Nainstalujte úlohu Wordpressu přes Helm.

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

Výsledky:
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

## Procházení nasazení AKS zabezpečeného přes HTTPS

Spuštěním následujícího příkazu získejte koncový bod HTTPS pro vaši aplikaci:

> [!NOTE]
> Často trvá 2 až 3 minuty, než se certifikát SSL rozšíří a přibližně 5 minut bude mít všechny repliky podu WordPress připravené a web bude plně dostupný přes https.

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

Pomocí následujícího příkazu zkontrolujte, jestli je obsah WordPressu správně doručen:

```bash
if curl -I -s -f https://$FQDN > /dev/null ; then 
    curl -L -s -f https://$FQDN 2> /dev/null | head -n 9
else 
    exit 1
fi;
```

Výsledky:
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

Navštivte web prostřednictvím následující adresy URL:

```bash
echo "You can now visit your web server at https://$FQDN"
```

## Vyčištění prostředků (volitelné)

Abyste se vyhnuli poplatkům za Azure, měli byste vyčistit nepotřebné prostředky. Pokud už cluster nepotřebujete, pomocí [příkazu az group delete](/cli/azure/group#az-group-delete) odeberte skupinu prostředků, službu kontejneru a všechny související prostředky. 

> [!NOTE]
> Při odstranění clusteru se neodebere instanční objekt Microsoft Entra používaný clusterem AKS. Postup odebrání instančního objektu najdete v tématu věnovaném [aspektům instančního objektu AKS a jeho odstranění](../../aks/kubernetes-service-principal.md#other-considerations). Pokud jste použili spravovanou identitu, identita se spravuje platformou a nevyžaduje odebrání.

## Další kroky

- Zjistěte, jak získat přístup k [webovému řídicímu panelu](../../aks/kubernetes-dashboard.md) Kubernetes pro cluster AKS.
- Informace o [škálování clusteru](../../aks/tutorial-kubernetes-scale.md)
- Informace o správě [instance flexibilního serveru Azure Database for MySQL](./quickstart-create-server-cli.md)
- Informace o [konfiguraci parametrů](./how-to-configure-server-parameters-cli.md) serveru pro databázový server