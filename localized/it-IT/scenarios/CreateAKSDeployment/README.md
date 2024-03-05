---
title: Distribuire un cluster di servizio Azure Kubernetes scalabile e sicuro usando l'interfaccia della riga di comando di Azure
description: Questa esercitazione illustra in modo dettagliato la creazione di un'applicazione Web Azure Kubernetes protetta tramite https.
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Guida introduttiva: Distribuire un cluster di servizio Azure Kubernetes scalabile e sicuro usando l'interfaccia della riga di comando di Azure

[![Distribuzione in Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateAKSDeployment)

Questa esercitazione illustra in modo dettagliato la creazione di un'applicazione Web Azure Kubernetes protetta tramite https. Questa esercitazione presuppone che l'utente sia già connesso all'interfaccia della riga di comando di Azure e abbia selezionato una sottoscrizione da usare con l'interfaccia della riga di comando. Si presuppone anche che Helm sia installato ([le istruzioni sono disponibili qui](https://helm.sh/docs/intro/install/)).

## Definire le variabili di ambiente

Il primo passaggio di questa esercitazione consiste nel definire le variabili di ambiente.

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

## Creare un gruppo di risorse

Un gruppo di risorse è un contenitore per le risorse correlate. Tutte le risorse devono essere inserite in un gruppo di risorse. Ne verrà creata una per questa esercitazione. Il comando seguente crea un gruppo di risorse con i parametri $MY_RESOURCE_GROUP_NAME definiti in precedenza e $REGION.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Risultati:

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

## Eseguire la registrazione ai provider di risorse di Azure del servizio Azure Kubernetes

Verificare che i provider Microsoft.OperationsManagement e Microsoft.OperationalInsights siano registrati nella sottoscrizione. Questi sono i provider di risorse di Azure necessari per supportare [informazioni dettagliate sui contenitori](https://docs.microsoft.com/azure/azure-monitor/containers/container-insights-overview). Per controllare lo stato della registrazione, eseguire i comandi seguenti

```bash
az provider register --namespace Microsoft.Insights
az provider register --namespace Microsoft.OperationsManagement
az provider register --namespace Microsoft.OperationalInsights
```

## Creare un cluster del servizio Azure Kubernetes

Creare un cluster del servizio Azure Kubernetes usando il comando az aks create con il parametro di monitoraggio --enable-addons per abilitare Informazioni dettagliate sui contenitori. L'esempio seguente crea un cluster abilitato per la scalabilità automatica e la zona di disponibilità.

L'operazione richiederà qualche minuto.

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

## Stabilire la connessione al cluster

Per gestire un cluster Kubernetes, usare il client da riga di comando kubernetes kubectl. kubectl è già installato se si usa Azure Cloud Shell.

1. Installare l'interfaccia della riga di comando del servizio Azure Kubernetes in locale usando il comando az aks install-cli

   ```bash
   if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
   ```

2. Per configurare kubectl per la connessione al cluster Kubernetes, usare il comando az aks get-credentials. Con il comando seguente:

   - Scarica le credenziali e configura l'interfaccia della riga di comando di Kubernetes per usarle.
   - Usa ~/.kube/config, il percorso predefinito per il file di configurazione di Kubernetes. Specificare un percorso diverso per il file di configurazione di Kubernetes usando l'argomento --file.

   > [!WARNING]
   > Verrà sovrascritto qualsiasi credenziale esistente con la stessa voce

   ```bash
   az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
   ```

3. Verificare la connessione al cluster usando il comando kubectl get. Questo comando restituisce un elenco dei nodi del cluster.

   ```bash
   kubectl get nodes
   ```

## Installare il controller di ingresso NGINX

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

## Distribuire l'applicazione

Un file manifesto Kubernetes definisce lo stato desiderato di un cluster, ad esempio le immagini del contenitore da eseguire.

In questa guida introduttiva si userà un manifesto per creare tutti gli oggetti necessari per eseguire l'applicazione Azure Vote. Questo manifesto include due distribuzioni kubernetes:

- Applicazioni Python di azure Vote di esempio.
- Istanza di Redis.

Vengono creati anche due servizi Kubernetes:

- Servizio interno per l'istanza di Redis.
- Un servizio esterno per accedere all'applicazione Azure Vote da Internet.

Viene infine creata una risorsa in ingresso per instradare il traffico all'applicazione Azure Vote.

Un file YML dell'app di voto di test è già preparato. Per distribuire questa app, eseguire il comando seguente

```bash
kubectl apply -f azure-vote-start.yml
```

## Testare l'applicazione

Verificare che l'applicazione sia in esecuzione visitando l'indirizzo IP pubblico o l'URL dell'applicazione. L'URL dell'applicazione è reperibile eseguendo il comando seguente:

> [!Note]
> La creazione dei POD richiede spesso 2-3 minuti e il sito può essere raggiungibile tramite HTTP

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

Risultati:

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

## Aggiungere la terminazione HTTPS al dominio personalizzato

A questo punto dell'esercitazione è disponibile un'app Web del servizio Azure Kubernetes con NGINX come controller di ingresso e un dominio personalizzato che è possibile usare per accedere all'applicazione. Il passaggio successivo consiste nell'aggiungere un certificato SSL al dominio in modo che gli utenti possano raggiungere l'applicazione in modo sicuro tramite HTTPS.

## Configurare Gestione certificati

Per aggiungere HTTPS si userà Cert Manager. Cert Manager è uno strumento open source usato per ottenere e gestire il certificato SSL per le distribuzioni Kubernetes. Cert Manager otterrà i certificati da un'ampia gamma di autorità emittenti, autorità emittenti pubbliche e autorità emittenti private e garantirà che i certificati siano validi e aggiornati e tenteranno di rinnovare i certificati in un momento configurato prima della scadenza.

1. Per installare cert-manager, è prima necessario creare uno spazio dei nomi in cui eseguirlo. Questa esercitazione installerà cert-manager nello spazio dei nomi cert-manager. È possibile eseguire cert-manager in uno spazio dei nomi diverso, anche se sarà necessario apportare modifiche ai manifesti della distribuzione.

   ```bash
   kubectl create namespace cert-manager
   ```

2. È ora possibile installare cert-manager. Tutte le risorse sono incluse in un singolo file manifesto YAML. Questa operazione può essere installata eseguendo quanto segue:

   ```bash
   kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
   ```

3. Aggiungere l'etichetta certmanager.k8s.io/disable-validation: "true" allo spazio dei nomi cert-manager eseguendo quanto segue. In questo modo le risorse di sistema che cert-manager richiede di avviare TLS per essere create nel proprio spazio dei nomi.

   ```bash
   kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
   ```

## Ottenere un certificato tramite grafici Helm

Helm è uno strumento di distribuzione Kubernetes per automatizzare la creazione, la creazione di pacchetti, la configurazione e la distribuzione di applicazioni e servizi nei cluster Kubernetes.

Cert-manager fornisce grafici Helm come metodo di installazione di prima classe in Kubernetes.

1. Aggiungere il repository Helm jetstack

   Questo repository è l'unica origine supportata dei grafici cert-manager. Ci sono altri mirror e copie su Internet, ma sono completamente non ufficiali e potrebbero presentare un rischio per la sicurezza.

   ```bash
   helm repo add jetstack https://charts.jetstack.io
   ```

2. Aggiornare la cache del repository helm chart locale

   ```bash
   helm repo update
   ```

3. Installare il componente aggiuntivo Cert-Manager tramite helm eseguendo quanto segue:

   ```bash
   helm install cert-manager jetstack/cert-manager --namespace cert-manager --version v1.7.0
   ```

4. Applica file YAML dell'autorità di certificazione

   I clusterIssuers sono risorse Kubernetes che rappresentano le autorità di certificazione (CA) in grado di generare certificati firmati rispettando le richieste di firma del certificato. Tutti i certificati cert-manager richiedono un'autorità di certificazione di riferimento in una condizione pronta per tentare di rispettare la richiesta.
   L'autorità emittente in uso è disponibile in `cluster-issuer-prod.yml file`

   ```bash
   cluster_issuer_variables=$(<cluster-issuer-prod.yml)
   echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
   ```

5. Upate Voting App Application per usare Cert-Manager per ottenere un certificato SSL.

   Il file YAML completo è disponibile in `azure-vote-nginx-ssl.yml`

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

## Esplorare la distribuzione del servizio Azure Kubernetes protetta tramite HTTPS

Eseguire il comando seguente per ottenere l'endpoint HTTPS per l'applicazione:

> [!Note]
> La propogate del certificato SSL richiede spesso 2-3 minuti e il sito può essere raggiungibile tramite HTTPS.

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

## Passaggi successivi

- [Documentazione del servizio Azure Kubernetes](https://learn.microsoft.com/azure/aks/)
- [Creare un Registro Azure Container](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-prepare-acr?tabs=azure-cli)
- [Ridimensionare l'applciation nel servizio Azure Kubernetes](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-scale?tabs=azure-cli)
- [Aggiornare l'applicazione nel servizio Azure Kubernetes](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-app-update?tabs=azure-cli)
