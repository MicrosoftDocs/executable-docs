---
title: 'Esercitazione: Distribuire WordPress nel cluster del servizio Azure Kubernetes usando l''interfaccia della riga di comando di Azure'
description: Informazioni su come creare e distribuire rapidamente app WordPress nel servizio Azure Kubernetes con il server flessibile di Database di Azure per MySQL.
ms.service: mysql
ms.subservice: flexible-server
author: mksuni
ms.author: sumuth
ms.topic: tutorial
ms.date: 3/20/2024
ms.custom: 'vc, devx-track-azurecli, innovation-engine, linux-related-content'
---

# Esercitazione: Distribuire un'app WordPress nel servizio Azure Kubernetes con Database di Azure per MySQL - Server flessibile

[!INCLUDE[applies-to-mysql-flexible-server](../includes/applies-to-mysql-flexible-server.md)]

[![Distribuzione in Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262843)

In questa esercitazione si distribuisce un'applicazione WordPress scalabile protetta tramite HTTPS in un cluster servizio Azure Kubernetes (AKS) con Database di Azure per MySQL server flessibile usando l'interfaccia della riga di comando di Azure.
Il **[servizio Azure Kubernetes](../../aks/intro-kubernetes.md)** è un servizio Kubernetes gestito che consente di distribuire e gestire rapidamente i cluster. **[server flessibile](overview.md)** Database di Azure per MySQL è un servizio di database completamente gestito progettato per offrire un controllo e una flessibilità più granulari rispetto alle funzioni di gestione del database e alle impostazioni di configurazione.

> [!NOTE]
> Questa esercitazione presuppone una conoscenza di base dei concetti di Kubernetes, WordPress e MySQL.

[!INCLUDE [flexible-server-free-trial-note](../includes/flexible-server-free-trial-note.md)]

## Prerequisiti 

Prima di iniziare, assicurarsi di aver eseguito l'accesso all'interfaccia della riga di comando di Azure e di aver selezionato una sottoscrizione da usare con l'interfaccia della riga di comando. Assicurarsi di aver [installato](https://helm.sh/docs/intro/install/) Helm.

> [!NOTE]
> Se si eseguono i comandi in questa esercitazione in locale anziché Azure Cloud Shell, eseguire i comandi come amministratore.

## Definire le variabili di ambiente

Il primo passaggio di questa esercitazione consiste nel definire le variabili di ambiente.

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

## Creare un gruppo di risorse

Un gruppo di risorse di Azure è un gruppo logico in cui le risorse di Azure vengono distribuite e gestite. Tutte le risorse devono essere inserite in un gruppo di risorse. Il comando seguente crea un gruppo di risorse con i parametri e `$REGION` definiti `$MY_RESOURCE_GROUP_NAME` in precedenza.

```bash
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION
```

Risultati:
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
> La località del gruppo di risorse è quella in cui vengono archiviati i relativi metadati. È anche la posizione in cui le risorse vengono eseguite in Azure se non si specifica un'altra area durante la creazione delle risorse.

## Creare una rete virtuale e una subnet

Una rete virtuale è il blocco predefinito fondamentale per le reti private in Azure. Il servizio Rete virtuale di Microsoft Azure consente alle risorse di Azure, come le VM, di comunicare in modo sicuro tra loro e con Internet.

```bash
az network vnet create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --name $MY_VNET_NAME \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefixes $MY_SN_PREFIX
```

Risultati:
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

## Creare un'istanza del server flessibile Database di Azure per MySQL

Database di Azure per MySQL server flessibile è un servizio gestito che è possibile usare per eseguire, gestire e ridimensionare server MySQL a disponibilità elevata nel cloud. Creare un'istanza del server flessibile Database di Azure per MySQL con il [comando az mysql flexible-server create](/cli/azure/mysql/flexible-server). Un server può contenere più database. Il comando seguente crea un server usando le impostazioni predefinite del servizio e i valori delle variabili dal contesto locale dell'interfaccia della riga di comando di Azure:

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

Risultati:
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

Il server creato ha gli attributi seguenti:

- Al primo provisioning del server viene creato un nuovo database vuoto.
- Il nome del server, il nome utente amministratore, la password amministratore, il nome del gruppo di risorse e la posizione sono già specificati nell'ambiente di contesto locale di Cloud Shell e si trovano nella stessa posizione del gruppo di risorse e di altri componenti di Azure.
- Le impostazioni predefinite del servizio per le configurazioni del server rimanenti sono il livello di calcolo (burstable), le dimensioni di calcolo/SKU (Standard_B2s), il periodo di conservazione dei backup (sette giorni) e la versione di MySQL (8.0.21).
- Il metodo di connettività predefinito è Accesso privato (integrazione della rete virtuale) con una rete virtuale collegata e una subnet generata automaticamente.

> [!NOTE]
> Il metodo di connettività non può essere modificato dopo la creazione del server. Ad esempio, se è stata selezionata `Private access (VNet Integration)` durante la creazione, non è possibile passare a `Public access (allowed IP addresses)` dopo la creazione. È consigliabile creare un server con accesso privato per accedere in modo sicuro al server tramite l'integrazione rete virtuale. Altre informazioni sull'accesso privato sono disponibili nell'[articolo sui concetti](./concepts-networking-vnet.md).

Per modificare le impostazioni predefinite, vedere la documentazione[ di riferimento dell'interfaccia della riga di comando di Azure ](/cli/azure//mysql/flexible-server)per l'elenco completo dei parametri configurabili dell'interfaccia della riga di comando.

## Controllare lo stato del server flessibile Database di Azure per MySQL

La creazione della Database di Azure per MySQL - Server flessibile e risorse di supporto richiede alcuni minuti.

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## Configurare i parametri del server in Database di Azure per MySQL - Server flessibile

È possibile gestire Database di Azure per MySQL - Configurazione del server flessibile usando i parametri del server. I parametri del server vengono configurati con il valore predefinito e consigliato quando si crea il server.

Per visualizzare informazioni dettagliate su un determinato parametro per un server, eseguire il [comando az mysql flexible-server parameter show](/cli/azure/mysql/flexible-server/parameter) .

### Disabilitare Database di Azure per MySQL - Parametro di connessione SSL server flessibile per l'integrazione di WordPress

È anche possibile modificare il valore di determinati parametri del server per aggiornare i valori di configurazione sottostanti per il motore del server MySQL. Per aggiornare il parametro del server, usare il [comando az mysql flexible-server parameter set](/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set) .

```bash
az mysql flexible-server parameter set \
    -g $MY_RESOURCE_GROUP_NAME \
    -s $MY_MYSQL_DB_NAME \
    -n require_secure_transport -v "OFF" -o JSON
```

Risultati:
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

## Creare un cluster del servizio Azure Container

Per creare un cluster del servizio Azure Kubernetes con Container Insights, usare il [comando az aks create](/cli/azure/aks#az-aks-create) con il **parametro di monitoraggio --enable-addons** . L'esempio seguente crea un cluster abilitato per la zona di disponibilità denominato **myAKSCluster**:

Questa azione richiede alcuni minuti.

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
> Quando si crea un cluster del servizio Azure Kubernetes, viene creato automaticamente un secondo gruppo di risorse per archiviare le risorse del servizio Azure Kubernetes. Vedere [Perché vengono creati due gruppi di risorse con il servizio Azure Kubernetes?](../../aks/faq.md#why-are-two-resource-groups-created-with-aks)

## Stabilire la connessione al cluster

Per gestire un cluster Kubernetes, usare [kubectl](https://kubernetes.io/docs/reference/kubectl/overview/), il client da riga di comando di Kubernetes. Se si usa Azure Cloud Shell, `kubectl` è già installato. L'esempio seguente viene `kubectl` installato localmente usando il [comando az aks install-cli](/cli/azure/aks#az-aks-install-cli) . 

 ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
```

Configurare `kubectl` quindi per connettersi al cluster Kubernetes usando il [comando az aks get-credentials](/cli/azure/aks#az-aks-get-credentials) . Questo comando scarica le credenziali e configura l'interfaccia della riga di comando di Kubernetes per usarli. Il comando usa `~/.kube/config`, il percorso predefinito per il [file](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/) di configurazione kubernetes. È possibile specificare un percorso diverso per il file di configurazione di Kubernetes usando l'argomento **--file** .

> [!WARNING]
> Questo comando sovrascriverà le credenziali esistenti con la stessa voce.

```bash
az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
```

Per verificare la connessione al cluster, usare il comando [kubectl get]( https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#get) per restituire un elenco di nodi del cluster.

```bash
kubectl get nodes
```

## Installare il controller di ingresso NGINX

È possibile configurare il controller di ingresso con un indirizzo IP pubblico statico. L'indirizzo IP pubblico statico rimane se si elimina il controller di ingresso. L'indirizzo IP non rimane se si elimina il cluster del servizio Azure Kubernetes.
Quando si aggiorna il controller di ingresso, è necessario passare un parametro alla versione Helm per assicurarsi che il servizio controller in ingresso sia a conoscenza del servizio di bilanciamento del carico che verrà allocato. Per il corretto funzionamento dei certificati HTTPS, usare un'etichetta DNS per configurare un nome di dominio completo (FQDN) per l'indirizzo IP del controller in ingresso. Il nome di dominio completo deve seguire questo formato: $MY_DNS_LABEL. AZURE_REGION_NAME.cloudapp.azure.com.

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

Aggiungere quindi il repository Helm ingress-nginx, aggiornare la cache del repository helm chart locale e installare il componente aggiuntivo ingress-nginx tramite Helm. È possibile impostare l'etichetta DNS con - **-set controller.service.annotations". service\.beta\.kubernetes\.io/azure-dns-label-name"="<DNS_LABEL>"** parametro quando si distribuisce il controller di ingresso o versioni successive. In questo esempio si specifica il proprio indirizzo IP pubblico creato nel passaggio precedente con il **parametro** --set controller.service.loadBalancerIP="<STATIC_IP>".

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

## Aggiungere la terminazione HTTPS al dominio personalizzato

A questo punto dell'esercitazione è disponibile un'app Web del servizio Azure Kubernetes con NGINX come controller di ingresso e un dominio personalizzato che è possibile usare per accedere all'applicazione. Il passaggio successivo consiste nell'aggiungere un certificato SSL al dominio in modo che gli utenti possano raggiungere l'applicazione in modo sicuro tramite https.

### Configurare Gestione certificati

Per aggiungere HTTPS, useremo Cert Manager. Cert Manager è uno strumento open source per ottenere e gestire i certificati SSL per le distribuzioni Kubernetes. Cert Manager ottiene i certificati da autorità emittenti pubbliche e emittenti private più diffuse, garantisce che i certificati siano validi e aggiornati e tenti di rinnovare i certificati in un momento configurato prima della scadenza.

1. Per installare cert-manager, è prima necessario creare uno spazio dei nomi in cui eseguirlo. Questa esercitazione installa cert-manager nello spazio dei nomi cert-manager. È possibile eseguire cert-manager in uno spazio dei nomi diverso, ma è necessario apportare modifiche ai manifesti della distribuzione.

    ```bash
    kubectl create namespace cert-manager
    ```

2. È ora possibile installare cert-manager. Tutte le risorse sono incluse in un singolo file manifesto YAML. Installare il file manifesto con il comando seguente:

    ```bash
    kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
    ```

3. Aggiungere l'etichetta `certmanager.k8s.io/disable-validation: "true"` allo spazio dei nomi cert-manager eseguendo quanto segue. In questo modo le risorse di sistema che cert-manager richiede di avviare TLS per essere create nel proprio spazio dei nomi.

    ```bash
    kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
    ```

## Ottenere un certificato tramite grafici Helm

Helm è uno strumento di distribuzione Kubernetes per automatizzare la creazione, la creazione di pacchetti, la configurazione e la distribuzione di applicazioni e servizi nei cluster Kubernetes.

Cert-manager fornisce grafici Helm come metodo di installazione di prima classe in Kubernetes.

1. Aggiungere il repository Helm di Jetstack. Questo repository è l'unica origine supportata dei grafici cert-manager. Ci sono altri mirror e copie su Internet, ma non sono ufficiali e potrebbero presentare un rischio per la sicurezza.

    ```bash
    helm repo add jetstack https://charts.jetstack.io
    ```

2. Aggiornare la cache del repository helm chart locale.

    ```bash
    helm repo update
    ```

3. Installare il componente aggiuntivo Cert-Manager tramite Helm.

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. Applicare il file YAML dell'autorità di certificazione. I clusterIssuers sono risorse Kubernetes che rappresentano le autorità di certificazione (CA) che possono generare certificati firmati rispettando le richieste di firma dei certificati. Tutti i certificati cert-manager richiedono un'autorità di certificazione di riferimento in una condizione pronta per tentare di rispettare la richiesta. È possibile trovare l'autorità emittente in `cluster-issuer-prod.yaml file`.

    ```bash
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## Creare una classe di archiviazione personalizzata

Le classi di archiviazione predefinite soddisfano gli scenari più comuni, ma non tutti. Per alcuni casi, potrebbe essere necessario personalizzare la propria classe di archiviazione con i propri parametri. Ad esempio, usare il manifesto seguente per configurare mountOptions **** della condivisione file.
Il valore predefinito per **fileMode** e **dirMode** è **0755** per le condivisioni file montate in Kubernetes. È possibile specificare le diverse opzioni di montaggio nell'oggetto classe di archiviazione.

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## Distribuire WordPress nel cluster del servizio Azure Kubernetes

Per questa esercitazione viene usato un grafico Helm esistente per WordPress compilato da Bitnami. Il grafico Helm di Bitnami usa un database MariaDB locale, quindi è necessario eseguire l'override di questi valori per usare l'app con Database di Azure per MySQL. È possibile eseguire l'override dei valori e delle impostazioni personalizzate del `helm-wp-aks-values.yaml` file.

1. Aggiungere il repository Helm di Wordpress Bitnami.

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. Aggiornare la cache del repository dei grafici Helm locale.

    ```bash
    helm repo update
    ```

3. Installare il carico di lavoro Wordpress tramite Helm.

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

Risultati:
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

## Esplorare la distribuzione del servizio Azure Kubernetes protetta tramite HTTPS

Eseguire il comando seguente per ottenere l'endpoint HTTPS per l'applicazione:

> [!NOTE]
> La propagazione del certificato SSL richiede spesso 2-3 minuti e circa 5 minuti affinché tutte le repliche POD WordPress siano pronte e il sito sia completamente raggiungibile tramite https.

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

Verificare che il contenuto wordPress venga recapitato correttamente usando il comando seguente:

```bash
if curl -I -s -f https://$FQDN > /dev/null ; then 
    curl -L -s -f https://$FQDN 2> /dev/null | head -n 9
else 
    exit 1
fi;
```

Risultati:
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

Visitare il sito Web tramite l'URL seguente:

```bash
echo "You can now visit your web server at https://$FQDN"
```

## Pulire le risorse (facoltativo)

Per evitare addebiti per Azure, è necessario eliminare le risorse non necessarie. Quando il cluster non è più necessario, usare il [comando az group delete](/cli/azure/group#az-group-delete) per rimuovere il gruppo di risorse, il servizio contenitore e tutte le risorse correlate. 

> [!NOTE]
> Quando si elimina il cluster, l'entità servizio Microsoft Entra usata dal cluster del servizio Azure Kubernetes non viene rimossa. Per istruzioni su come rimuovere l'entità servizio, vedere le [considerazioni sull'entità servizio servizio Azure Kubernetes e la sua eliminazione](../../aks/kubernetes-service-principal.md#other-considerations). Se è stata usata un'identità gestita, l'identità viene gestita dalla piattaforma e non richiede la rimozione.

## Passaggi successivi

- Informazioni su come [accedere al dashboard Web di Kubernetes](../../aks/kubernetes-dashboard.md) per il cluster del servizio Azure Kubernetes
- Informazioni su come [dimensionare il cluster](../../aks/tutorial-kubernetes-scale.md)
- Informazioni su come gestire l'istanza [del server flessibile Database di Azure per MySQL](./quickstart-create-server-cli.md)
- Informazioni su come [configurare i](./how-to-configure-server-parameters-cli.md) parametri del server per il server di database