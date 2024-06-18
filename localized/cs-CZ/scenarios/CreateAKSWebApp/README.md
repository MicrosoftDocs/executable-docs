---
title: Nasazení škálovatelného a zabezpečeného clusteru Azure Kubernetes Service pomocí Azure CLI
description: 'V tomto kurzu vás provedeme krok za krokem při vytváření webové aplikace Azure Kubernetes, která je zabezpečená přes https.'
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Rychlý start: Nasazení škálovatelného a zabezpečeného clusteru Azure Kubernetes Service pomocí Azure CLI

[![Nasazení do Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/?Microsoft_Azure_CloudNative_clientoptimizations=false&feature.canmodifyextensions=true#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateAKSDeployment)

Vítejte v tomto kurzu, kde vás provedeme krok za krokem při vytváření webové aplikace Azure Kubernetes, která je zabezpečená přes https. V tomto kurzu se předpokládá, že jste už přihlášení k Azure CLI a vybrali jste předplatné, které se má použít s rozhraním příkazového řádku. Předpokládá se také, že máte nainstalovaný Helm ([pokyny najdete tady](https://helm.sh/docs/intro/install/)).

## Definování proměnných prostředí

Prvním krokem v tomto kurzu je definování proměnných prostředí.

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

## Vytvoření skupiny zdrojů

Skupina prostředků je kontejner pro související prostředky. Všechny prostředky musí být umístěné ve skupině prostředků. Pro účely tohoto kurzu ho vytvoříme. Následující příkaz vytvoří skupinu prostředků s dříve definovanými parametry $MY_RESOURCE_GROUP_NAME a $REGION.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Výsledky:

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

## Registrace k poskytovatelům prostředků Azure AKS

Ověřte, že jsou ve vašem předplatném zaregistrovaní poskytovatelé Microsoft.OperationsManagement a Microsoft.OperationalInsights. Jedná se o poskytovatele prostředků Azure, kteří musí podporovat [přehledy](https://docs.microsoft.com/azure/azure-monitor/containers/container-insights-overview) kontejnerů. Pokud chcete zkontrolovat stav registrace, spusťte následující příkazy.

```bash
az provider register --namespace Microsoft.Insights
az provider register --namespace Microsoft.OperationsManagement
az provider register --namespace Microsoft.OperationalInsights
```

## Vytvoření clusteru AKS

Vytvořte cluster AKS pomocí příkazu az aks create s parametrem monitorování --enable-addons, který povolí Container Insights. Následující příklad vytvoří cluster s povoleným automatickým škálováním a zónou dostupnosti.

Bude to několik minut trvat.

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

## Připojení ke clusteru

Ke správě clusteru Kubernetes použijte klienta příkazového řádku Kubernetes kubectl. Kubectl je už nainstalovaný, pokud používáte Azure Cloud Shell.

1. Místní instalace az aks CLI pomocí příkazu az aks install-cli

   ```bash
   if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
   ```

2. Pomocí příkazu az aks get-credentials nakonfigurujte kubectl pro připojení ke clusteru Kubernetes. Následující příkaz:

   - Stáhne přihlašovací údaje a nakonfiguruje rozhraní příkazového řádku Kubernetes tak, aby je používalo.
   - Používá ~/.kube/config, výchozí umístění konfiguračního souboru Kubernetes. Pomocí argumentu --file zadejte jiné umístění konfiguračního souboru Kubernetes.

   > [!WARNING]
   > Tím se přepíše všechny existující přihlašovací údaje se stejnou položkou.

   ```bash
   az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
   ```

3. Pomocí příkazu kubectl get ověřte připojení ke clusteru. Tento příkaz vrátí seznam uzlů clusteru.

   ```bash
   kubectl get nodes
   ```

## Instalace kontroleru příchozího přenosu dat NGINX

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

## Nasazení aplikace

Soubor manifestu Kubernetes definuje požadovaný stav clusteru, například které image kontejneru se mají spustit.

V tomto rychlém startu použijete manifest k vytvoření všech objektů potřebných ke spuštění aplikace Azure Vote. Tento manifest zahrnuje dvě nasazení Kubernetes:

- Ukázkové aplikace Azure Vote Python.
- Instance Redis.

Vytvoří se také dvě služby Kubernetes:

- Interní služba instance Redis.
- Externí služba pro přístup k aplikaci Azure Vote z internetu.

Nakonec se vytvoří prostředek příchozího přenosu dat pro směrování provozu do aplikace Azure Vote.

Soubor YML testovací hlasovací aplikace je již připravený. Spuštěním následujícího příkazu nasaďte tuto aplikaci.

```bash
kubectl apply -f azure-vote-start.yml
```

## Otestování aplikace

Ověřte, že je aplikace spuštěná, a to tak, že navštívíte veřejnou IP adresu nebo adresu URL aplikace. Adresu URL aplikace najdete spuštěním následujícího příkazu:

> [!Note]
> Vytvoření identifikátorů POD a připojení k webu prostřednictvím protokolu HTTP často trvá 2 až 3 minuty.

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

Výsledky:

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

## Přidání ukončení protokolu HTTPS do vlastní domény

V tomto okamžiku v kurzu máte webovou aplikaci AKS s NGINX jako kontrolerem příchozího přenosu dat a vlastní doménou, kterou můžete použít pro přístup k aplikaci. Dalším krokem je přidání certifikátu SSL do domény, aby se uživatelé mohli k vaší aplikaci bezpečně dostat přes HTTPS.

## Nastavení správce certifikátů

Abychom mohli přidat HTTPS, použijeme Správce certifikátů. Cert Manager je opensourcový nástroj používaný k získání a správě certifikátu SSL pro nasazení Kubernetes. Správce certifikátů získá certifikáty od různých vystavitelů, oblíbených veřejných vystavitelů i privátních vystavitelů a zajistí, že certifikáty jsou platné a aktuální, a pokusí se obnovit certifikáty v nakonfigurované době před vypršením platnosti.

1. Abychom mohli nainstalovat nástroj cert-manager, musíme nejprve vytvořit obor názvů pro jeho spuštění. Tento kurz nainstaluje nástroj cert-manager do oboru názvů cert-manager. Nástroj cert-manager je možné spustit v jiném oboru názvů, i když budete muset provést změny manifestů nasazení.

   ```bash
   kubectl create namespace cert-manager
   ```

2. Teď můžeme nainstalovat nástroj cert-manager. Všechny prostředky jsou součástí jednoho souboru manifestu YAML. Můžete ho nainstalovat spuštěním následujícího příkazu:

   ```bash
   kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
   ```

3. Přidejte popisek certmanager.k8s.io/disable-validation: true do oboru názvů cert-manager spuštěním následujícího příkazu. To umožní systémovým prostředkům, které cert-manager vyžaduje, aby se protokol TLS bootstrap vytvořil ve vlastním oboru názvů.

   ```bash
   kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
   ```

## Získání certifikátu prostřednictvím chartů Helm

Helm je nástroj pro nasazení Kubernetes pro automatizaci vytváření, balení, konfigurace a nasazování aplikací a služeb do clusterů Kubernetes.

Cert-manager poskytuje charty Helm jako prvotřídní metodu instalace v Kubernetes.

1. Přidání úložiště Jetstack Helm

   Toto úložiště je jediným podporovaným zdrojem grafů cert-manageru. Existují další zrcadla a kopie po internetu, ale ty jsou zcela neoficiální a můžou představovat bezpečnostní riziko.

   ```bash
   helm repo add jetstack https://charts.jetstack.io
   ```

2. Aktualizace místní mezipaměti úložiště Helm Chart

   ```bash
   helm repo update
   ```

3. Nainstalujte doplněk Cert-Manager pomocí nástroje Helm spuštěním následujícího příkazu:

   ```bash
   helm install cert-manager jetstack/cert-manager --namespace cert-manager --version v1.7.0
   ```

4. Použití souboru YAML vystavitele certifikátu

   ClusterIssuers jsou prostředky Kubernetes, které představují certifikační autority (CA), které můžou generovat podepsané certifikáty tím, že dodržují žádosti o podepsání certifikátu. Všechny certifikáty cert-manager vyžadují odkazovaného vystavitele, který je v připravené podmínce, aby se pokusil požadavek respektovat.
   Vystavitel, který používáme, najdete v části `cluster-issuer-prod.yml file`

   ```bash
   cluster_issuer_variables=$(<cluster-issuer-prod.yml)
   echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
   ```

5. Upate Voting App Application to use Cert-Manager to obtain an SSL Certificate.

   Úplný soubor YAML najdete v `azure-vote-nginx-ssl.yml`

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

## Procházení nasazení AKS zabezpečeného přes PROTOKOL HTTPS

Spuštěním následujícího příkazu získejte koncový bod HTTPS pro vaši aplikaci:

> [!Note]
> Často trvá 2 až 3 minuty, než se certifikát SSL propogateuje a web bude dostupný přes HTTPS.

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

## Další kroky

- [Dokumentace ke službě Azure Kubernetes Service](https://learn.microsoft.com/azure/aks/)
- [Vytvoření služby Azure Container Registry](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-prepare-acr?tabs=azure-cli)
- [Škálování aplikace v AKS](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-scale?tabs=azure-cli)
- [Aktualizace aplikace v AKS](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-app-update?tabs=azure-cli)