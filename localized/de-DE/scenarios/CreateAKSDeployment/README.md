---
title: Bereitstellen eines skalierbaren und sicheren Azure Kubernetes Service-Clusters über die Azure CLI
description: 'In diesem Tutorial wird Schritt für Schritt erläutert, wie Sie eine Azure Kubernetes-Webanwendung erstellen, die über HTTPS geschützt ist.'
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Schnellstart: Bereitstellung eines skalierbaren & sicheren Azure Kubernetes Service-Clusters mit der Azure CLI

[![Bereitstellung in Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262758)

Willkommen bei diesem Tutorial, in dem wir Sie Schritt für Schritt durch das Erstellen einer Azure Kubernetes-Webanwendung führen, die über HTTPS geschützt ist. In diesem Tutorial wird davon ausgegangen, dass Sie bereits bei der Azure CLI angemeldet sind und ein Abonnement ausgewählt haben, das mit der CLI verwendet werden soll. Es wird auch davon ausgegangen, dass Sie Helm installiert haben (entsprechende Anweisungen finden Sie [hier](https://helm.sh/docs/intro/install/)).

## Umgebungsvariablen definieren

Der erste Schritt in diesem Tutorial besteht darin, Umgebungsvariablen zu definieren.

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

## Erstellen einer Ressourcengruppe

Eine Ressourcengruppe ist ein Container für zugehörige Ressourcen. Alle Ressourcen müssen in einer Ressourcengruppe platziert werden. In diesem Tutorial erstellen wir eine Ressourcengruppe. Mit dem folgenden Befehl wird eine Ressourcengruppe mit den zuvor definierten Parametern $MY_RESOURCE_GROUP_NAME und $REGION erstellt.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Ergebnisse:

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

## Erstellen eines virtuellen Netzwerks und des Subnetzes

Ein virtuelles Netzwerk ist der grundlegende Baustein für private Netzwerke in Azure. Über Azure Virtual Network können Azure-Ressourcen wie etwa VMs sicher miteinander und mit dem Internet kommunizieren.

```bash
az network vnet create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --name $MY_VNET_NAME \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefixes $MY_SN_PREFIX
```

Ergebnisse:

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

## Registrieren bei AKS-Azure-Ressourcenanbietern

Überprüfen Sie, ob die Anbieter Microsoft.OperationsManagement und Microsoft.OperationalInsights in Ihrem Abonnement registriert sind. Dies sind Azure-Ressourcenanbieter, die für die Unterstützung von [Containererkenntnissen](https://docs.microsoft.com/azure/azure-monitor/containers/container-insights-overview) erforderlich sind. Führen Sie die folgenden Befehle aus, um den Registrierungsstatus zu überprüfen:

```bash
az provider register --namespace Microsoft.Insights
az provider register --namespace Microsoft.OperationsManagement
az provider register --namespace Microsoft.OperationalInsights
```

## Create AKS Cluster

Erstellen Sie mit dem Befehl az aks create mit dem Parameter --enable-addons monitoring einen AKS-Cluster, um Container Insights zu aktivieren. Im folgenden Beispiel wird ein Cluster mit automatischer Skalierung und aktivierter Verfügbarkeitszone erstellt.

Dieser Vorgang nimmt einige Minuten in Anspruch.

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

## Herstellen einer Verbindung mit dem Cluster

Verwenden Sie zum Verwalten eines Kubernetes-Clusters den Kubernetes-Befehlszeilenclient kubectl. Bei Verwendung von Azure Cloud Shell ist kubectl bereits installiert.

1. Verwenden Sie für die lokale Installation von „az aks CLI“ den Befehl „az aks install-cli“.

   ```bash
   if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
   ```

2. Konfigurieren Sie kubectl mit dem Befehl „az aks get-credentials“, um eine Verbindung mit Ihrem Kubernetes-Cluster herzustellen. Der unten angegebene Befehl bewirkt Folgendes:

   - Herunterladen von Anmeldeinformationen und Konfigurieren der Kubernetes-Befehlszeilenschnittstelle für ihre Verwendung
   - Verwenden von „~/.kube/config“ (Standardspeicherort für die Kubernetes-Konfigurationsdatei). Geben Sie mit dem --file-Argument einen anderen Speicherort für Ihre Kubernetes-Konfigurationsdatei an.

   > [!WARNING]
   > Dadurch werden alle vorhandenen Anmeldeinformationen mit demselben Eintrag überschrieben.

   ```bash
   az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
   ```

3. Überprüfen Sie die Verbindung mit dem Cluster mithilfe des Befehls kubectl get. Dieser Befehl gibt eine Liste der Clusterknoten zurück.

   ```bash
   kubectl get nodes
   ```

## Installieren des NGINX-Eingangsdatencontrollers

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

## Bereitstellen der Anwendung

Eine Kubernetes-Manifestdatei definiert den gewünschten Zustand (Desired State) eines Clusters – also beispielsweise, welche Containerimages ausgeführt werden sollen.

In dieser Schnellstartanleitung verwenden Sie ein Manifest, um alle Objekte zu erstellen, die zum Ausführen der Azure Vote-Anwendung benötigt werden. Dieses Manifest umfasst zwei Kubernetes-Bereitstellungen:

- Die Azure Vote-Python-Beispielanwendungen
- Eine Redis-Instanz

Darüber hinaus werden zwei Kubernetes-Dienste erstellt:

- Ein interner Dienst für die Redis-Instanz
- Ein externer Dienst für den Zugriff auf die Azure Vote-Anwendung über das Internet

Schließlich wird eine Eingangsressource erstellt, um den Datenverkehr an die Azure Vote-Anwendung weiterzuleiten.

Eine YML-Datei für die Testabstimmungs-App wurde bereits vorbereitet. Führen Sie zum Bereitstellen dieser App den folgenden Befehl aus:

```bash
kubectl apply -f azure-vote-start.yml
```

## Testen der Anwendung

Überprüfen Sie, ob die Anwendung ausgeführt wird, indem Sie entweder die öffentliche IP-Adresse oder die Anwendungs-URL aufrufen. Die Anwendungs-URL kann durch Ausführen des folgenden Befehls ermittelt werden:

> [!Note]
> Es dauert oft 2 bis 3 Minuten, bis die PODs erstellt werden und die Website über HTTP erreichbar ist.

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

Ergebnisse:

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

## Hinzufügen von HTTPS-Beendigung zu einer benutzerdefinierten Domäne

An diesem Punkt im Tutorial verfügen Sie über eine AKS-Web-App mit NGINX als Eingangsdatencontroller und einer benutzerdefinierten Domäne, die Sie für den Zugriff auf Ihre Anwendung verwenden können. Der nächste Schritt besteht darin, der Domäne ein SSL-Zertifikat hinzuzufügen, damit Benutzer*innen Ihre Anwendung sicher über HTTPS erreichen können.

## Einrichten von Cert Manager

Wir verwenden Cert Manager zum Hinzufügen von HTTPS. Cert Manager ist ein Open Source-Tool zum Abrufen und Verwalten von SSL-Zertifikaten für Kubernetes-Bereitstellungen. Cert Manager erhält Zertifikate von verschiedenen Zertifikatausstellern (sowohl von beliebten öffentlichen Zertifikatausstellern als auch von privaten Zertifikataussteller), stellt sicher, dass die Zertifikate gültig und auf dem neuesten Stand sind, und versucht, Zertifikate zu einem konfigurierten Zeitpunkt vor Ablauf zu verlängern.

1. Zum Installieren von Cert Manager müssen Sie zuerst einen Namespace für die Ausführung erstellen. In diesem Tutorial wird Cert Manager im Cert Manager-Namespace installiert. Es ist möglich, Cert Manager in einem anderen Namespace auszuführen. Dann müssen Sie jedoch Änderungen an den Bereitstellungsmanifesten vornehmen.

   ```bash
   kubectl create namespace cert-manager
   ```

2. Sie können nun Cert Manager installieren. Alle Ressourcen sind in einer einzigen YAML-Manifestdatei enthalten. Diese kann mithilfe der folgenden Befehle installiert werden:

   ```bash
   kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
   ```

3. Fügen Sie die Bezeichnung „certmanager.k8s.io/disable-validation: "true"“ zum Cert-Manager-Namespace hinzu, indem Sie Folgendes ausführen. Dadurch können die Systemressourcen, die von Cert Manager für das Bootstrapping von TLs benötigt werden, in einem eigenen Namespace erstellt werden.

   ```bash
   kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
   ```

## Abrufen von Zertifikaten über Helm-Diagramme

Helm ist ein Kubernetes-Bereitstellungstool zum Automatisieren von Erstellen, Packen, Konfigurieren und Bereitstellen von Anwendungen und Diensten für Kubernetes-Cluster.

Cert Manager stellt Helm-Diagramme als erstklassige Methode zur Installation in Kubernetes bereit.

1. Hinzufügen des Jetstack-Helm-Repositorys

   Dieses Repository ist die einzige unterstützte Quelle von Cert Manager-Diagrammen. Es gibt einige andere Spiegelungen und Kopien im Internet, aber diese sind völlig inoffiziell und könnten ein Sicherheitsrisiko darstellen.

   ```bash
   helm repo add jetstack https://charts.jetstack.io
   ```

2. Aktualisieren des lokalen Repositorycache für das Helm-Diagramm

   ```bash
   helm repo update
   ```

3. Installieren Sie das Cert Manager-Add-On über Helm, indem Sie Folgendes ausführen:

   ```bash
   helm install cert-manager jetstack/cert-manager --namespace cert-manager --version v1.7.0
   ```

4. Anwenden der YAML-Datei des Zertifikatausstellers

   ClusterIssuers sind Kubernetes-Ressourcen, die Zertifizierungsstellen darstellen, die signierte Zertifikate generieren können, indem Zertifikatsignaturanforderungen berücksichtigt werden. Alle Cert Manager-Zertifikate erfordern einen referenzierten Zertifikataussteller, der in der Lage ist, die Anforderung zu berücksichtigen.
   Den von uns verwendeten Zertifikataussteller finden Sie in der Datei `cluster-issuer-prod.yml file`.

   ```bash
   cluster_issuer_variables=$(<cluster-issuer-prod.yml)
   echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
   ```

5. Aktualisieren Sie die Abstimmungs-App so, dass sie Cert Manager um Abrufen eines SSL-Zertifikats verwendet.

   Die vollständige YAML-Datei finden Sie in `azure-vote-nginx-ssl.yml`.

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

## Durchsuchen Ihrer über HTTPS gesicherten AKS-Bereitstellung

Führen Sie den folgenden Befehl aus, um den HTTPS-Endpunkt für Ihre Anwendung abzurufen:

> [!Note]
> Es dauert oft 2 bis 3 Minuten, bis das SSL-Zertifikat weitergegeben wurde und die Website über HTTP erreichbar ist.

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

## Nächste Schritte

- [Dokumentation zu Azure Kubernetes Service](https://learn.microsoft.com/azure/aks/)
- [Erstellen einer Azure Container Registry-Instanz](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-prepare-acr?tabs=azure-cli)
- [Skalieren Ihrer Anwendung in AKS](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-scale?tabs=azure-cli)
- [Aktualisieren Ihrer Anwendung in AKS](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-app-update?tabs=azure-cli)
