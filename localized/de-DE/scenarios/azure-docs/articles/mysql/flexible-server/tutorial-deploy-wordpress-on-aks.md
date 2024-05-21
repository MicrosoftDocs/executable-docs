---
title: "Tutorial: Bereitstellen von WordPress in einem AKS-Cluster unter Verwendung der Azure\_CLI"
description: "Hier erfahren Sie, wie Sie WordPress in AKS mit Azure Database for MySQL\_– Flexible Server schnell erstellen und bereitstellen."
ms.service: mysql
ms.subservice: flexible-server
author: mksuni
ms.author: sumuth
ms.topic: tutorial
ms.date: 3/20/2024
ms.custom: 'vc, devx-track-azurecli, innovation-engine, linux-related-content'
---

# Tutorial: Bereitstellen einer WordPress-App in AKS mit Azure Database for MySQL – Flexible Server

[!INCLUDE[applies-to-mysql-flexible-server](../includes/applies-to-mysql-flexible-server.md)]

[![Bereitstellung in Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262843)

In dieser Schnellstartanleitung wird eine skalierbare über HTTPS geschützte WordPress-Anwendung in einem AKS-Cluster (Azure Kubernetes Service) mit Azure Database for MySQL – Flexibler Server unter Verwendung der Azure CLI bereitgestellt.
**[AKS](../../aks/intro-kubernetes.md)** ist ein verwalteter Kubernetes-Dienst, mit dem Sie Cluster schnell bereitstellen und verwalten können. **[Azure Database for MySQL – Flexible Server](overview.md)** ist ein vollständig verwalteter Datenbankdienst, der eine differenziertere Steuerung und mehr Flexibilität bei den Verwaltungsfunktionen und Konfigurationseinstellungen der Datenbank bietet.

> [!NOTE]
> In diesem Tutorial werden grundlegende Kenntnisse von Kubernetes-Konzepten, WordPress und MySQL vorausgesetzt.

[!INCLUDE [flexible-server-free-trial-note](../includes/flexible-server-free-trial-note.md)]

## Voraussetzungen 

Bevor Sie beginnen, stellen Sie sicher, dass Sie bei der Azure CLI angemeldet sind und ein Abonnement ausgewählt haben, das mit der CLI verwendet werden soll. Stellen Sie sicher, dass [Helm installiert ist](https://helm.sh/docs/intro/install/).

> [!NOTE]
> Wenn Sie die Befehle in diesem Tutorial lokal anstatt in Azure Cloud Shell ausführen, stellen Sie sicher, dass Sie sie als Administrator ausführen.

## Umgebungsvariablen definieren

Der erste Schritt in diesem Tutorial besteht darin, Umgebungsvariablen zu definieren.

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

## Erstellen einer Ressourcengruppe

Eine Azure-Ressourcengruppe ist eine logische Gruppe, in der Azure-Ressourcen bereitgestellt und verwaltet werden. Alle Ressourcen müssen in einer Ressourcengruppe platziert werden. Mit dem folgenden Befehl wird eine Ressourcengruppe mit den zuvor definierten `$MY_RESOURCE_GROUP_NAME`- und `$REGION`-Parametern erstellt.

```bash
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION
```

Ergebnisse:
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
> Der Standort für die Ressourcengruppe ist der Ort, an dem die Metadaten der Ressourcengruppen gespeichert werden. Darüber hinaus werden dort Ihre Ressourcen in Azure ausgeführt, sofern Sie im Rahmen der Ressourcenerstellung keine andere Region angeben.

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

## Erstellen einer Azure Database for MySQL Flexible Server-Instanz

Azure Database for MySQL Flexible Server ist ein verwalteter Dienst, mit dem Sie hochverfügbare MySQL-Serverinstanzen in der Cloud ausführen, verwalten und skalieren können. Erstellen Sie mithilfe des Befehls [az mysql flexible-server create](/cli/azure/mysql/flexible-server) eine Instanz von Azure Database for MySQL – Flexible Server. Ein Server kann mehrere Datenbanken enthalten. Mit dem folgenden Befehl wird ein Server mit Dienststandardwerten und Variablenwerten aus dem lokalen Kontext Ihrer Azure CLI erstellt:

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

Ergebnisse:
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

Der erstellte Server weist die folgenden Attribute auf:

- Bei der erstmaligen Bereitstellung des Servers wird eine neue leere Datenbank erstellt.
- Der Servername, der Administratorbenutzername, das Administratorkennwort, der Name der Ressourcengruppe und der Standort sind bereits in der lokalen Kontextumgebung der Cloudshell angegeben und werden an demselben Speicherort wie die Ressourcengruppe und die anderen Azure-Komponenten erstellt.
- Die Dienststandardwerte für die verbleibenden Serverkonfigurationen lauten wie folgt: Computeebene (Burstfähig), Computegröße/SKU (Standard_B2s), Aufbewahrungszeitraum für Sicherungen (sieben Tage) und MySQL-Version (8.0.21).
- Die Standardkonnektivitätsmethode ist der private Zugriff (VNet-Integration) mit einem verknüpften virtuellen Netzwerk und einem automatisch generierten Subnetz.

> [!NOTE]
> Die Konnektivitätsmethode kann nicht geändert werden, nachdem der Server erstellt wurde. Wenn Sie z. B. `Private access (VNet Integration)` während der Erstellung ausgewählt haben, können Sie nach dem Erstellen nicht zu `Public access (allowed IP addresses)` wechseln. Es wird dringend empfohlen, einen Server mit privatem Zugriff zu erstellen, um mithilfe der VNET-Integration sicher auf den Server zugreifen zu können. Weitere Informationen zum privaten Zugriff finden Sie im Artikel zu [Konzepten](./concepts-networking-vnet.md).

Wenn Sie irgendwelche Standardwerte ändern möchten, finden Sie in der [Referenzdokumentation](/cli/azure//mysql/flexible-server) zur Azure CLI die komplette Liste der konfigurierbaren CLI-Parameter.

## Überprüfen des Status von „Azure Database for MySQL – Flexibler Server“

Es dauert einige Minuten, die Instanz von Azure Database for MySQL – Flexibler Server und unterstützende Ressourcen zu erstellen.

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## Konfigurieren von Serverparametern in Azure Database for MySQL – Flexibler Server

Sie können die Konfiguration von Azure Database for MySQL – Flexible Server über Serverparameter verwalten. Die Serverparameter werden beim Erstellen des Servers mit einem Standardwert und einem empfohlenen Wert konfiguriert.

Um Details zu einem bestimmten Parameter für einen Server anzuzeigen, führen Sie den Befehl [az mysql flexible-server parameter show](/cli/azure/mysql/flexible-server/parameter) aus.

### Deaktivieren des SSL-Verbindungsparameter für „Azure Database for MySQL – Flexible Server“ für die WordPress-Integration

Sie können auch den Wert eines bestimmten Serverparameters ändern und dadurch den zugrunde liegenden Konfigurationswert für die MySQL-Server-Engine aktualisieren. Um den Serverparameter zu aktualisieren, verwenden Sie den Befehl [az mysql flexible-server parameter set](/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set).

```bash
az mysql flexible-server parameter set \
    -g $MY_RESOURCE_GROUP_NAME \
    -s $MY_MYSQL_DB_NAME \
    -n require_secure_transport -v "OFF" -o JSON
```

Ergebnisse:
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

## Erstellen eines ACS-Clusters

Um einen AKS-Cluster mit Container Insights zu erstellen, verwenden Sie den Befehl[az aks create](/cli/azure/aks#az-aks-create) mit dem Überwachungsparameter **--enable-addons**. Im folgenden Beispiel wird ein Cluster mit automatischer Skalierung und aktivierter Verfügbarkeitszone namens **myAKSCluster** erstellt:

Dieser Vorgang dauert einige Minuten.

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
> Beim Erstellen eines AKS-Clusters wird automatisch eine zweite Ressourcengruppe erstellt, um die AKS-Ressourcen zu speichern. Weitere Informationen finden Sie unter [Warum werden zwei Ressourcengruppen mit AKS erstellt?](../../aks/faq.md#why-are-two-resource-groups-created-with-aks).

## Herstellen einer Verbindung mit dem Cluster

Verwenden Sie zum Verwalten eines Kubernetes-Clusters den Kubernetes-Befehlszeilenclient [kubectl](https://kubernetes.io/docs/reference/kubectl/overview/). Bei Verwendung von Azure Cloud Shell ist `kubectl` bereits installiert. Im folgenden Beispiel wird `kubectl` lokal mithilfe des Befehls [az aks install-cli](/cli/azure/aks#az-aks-install-cli) installiert. 

 ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
```

Konfigurieren Sie als Nächstes `kubectl`, um eine Verbindung mit Ihrem Kubernetes-Cluster mithilfe des Befehls [az aks get-credentials](/cli/azure/aks#az-aks-get-credentials) herzustellen. Mit diesem Befehl werden die Anmeldeinformationen heruntergeladen und die Kubernetes-CLI für ihre Verwendung konfiguriert. Der Befehl verwendet `~/.kube/config`, den Standardspeicherort für die [Kubernetes-Konfigurationsdatei](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/). Sie können mit dem Argument **--file** einen anderen Speicherort für Ihre Kubernetes-Konfigurationsdatei angeben.

> [!WARNING]
> Mit diesem Befehl werden alle vorhandenen Anmeldeinformationen mit demselben Eintrag überschrieben.

```bash
az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
```

Überprüfen Sie die Verbindung mit Ihrem Cluster mithilfe des Befehls [kubectl get]( https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#get), um eine Liste der Clusterknoten zurückzugeben.

```bash
kubectl get nodes
```

## Installieren des NGINX-Eingangsdatencontrollers

Sie können Ihren Eingangsdatencontroller mit einer statischen öffentlichen IP-Adresse konfigurieren. Die statische öffentliche IP-Adresse wird beibehalten, wenn der Eingangsdatencontroller gelöscht wird. Die IP-Adresse bleibt nicht erhalten, wenn Sie Ihren AKS-Cluster löschen.
Wenn Sie Ihren Eingangsdatencontroller aktualisieren, müssen Sie einen Parameter an den Helm-Release übergeben. So können Sie sicherstellen, dass der Dienst des Eingangsdatencontrollers auf den Lastenausgleich aufmerksam gemacht wird, der ihm zugeordnet wird. Damit die HTTPS-Zertifikate ordnungsgemäß funktionieren, wird eine DNS-Bezeichnung verwendet, um einen vollqualifizierten Domänennamen (FQDN) für die IP-Adresse des Eingangsdatencontrollers zu konfigurieren. Ihr FQDN sollte diesem Formular folgen: $MY_DNS_LABEL. AZURE_REGION_NAME.cloudapp.azure.com.

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

Als Nächstes fügen Sie das Helm-Repository „ingress-nginx“ hinzu, aktualisieren den lokalen Repositorycache für Helm-Diagramme und installieren das Addon „ingress-nginx“ über Helm. Sie können die DNS-Bezeichnung mit dem Parameter **--set controller.service.annotations festlegen." service\.beta\.kubernetes\.io/azure-dns-label-name"="<DNS_LABEL>"** entweder bei der erstmaligen Bereitstellung des Eingangsdatencontrollers oder zu einem späteren Zeitpunkt festlegen. In diesem Beispiel geben Sie Ihre eigene öffentliche IP-Adresse an, die Sie im vorherigen Schritt mit dem Parameter **--set controller.service.loadBalancerIP="<STATIC_IP>" ** erstellt haben.

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

## Hinzufügen von HTTPS-Beendigung zu einer benutzerdefinierten Domäne

An diesem Punkt im Tutorial verfügen Sie über eine AKS-Web-App mit NGINX als Eingangsdatencontroller und eine benutzerdefinierte Domäne, die Sie für den Zugriff auf Ihre Anwendung verwenden können. Der nächste Schritt besteht darin, der Domäne ein SSL-Zertifikat hinzuzufügen, damit Benutzer*innen Ihre Anwendung sicher über HTTPS erreichen können.

### Einrichten von Cert Manager

Wir verwenden Cert Manager zum Hinzufügen von HTTPS. Cert Manager ist ein Open Source-Tool zum Abrufen und Verwalten von SSL-Zertifikaten für Kubernetes-Bereitstellungen. Cert Manager erhält Zertifikate von beliebten öffentlichen und privaten Zertifikatausstellern, stellt sicher, dass die Zertifikate gültig und auf dem neuesten Stand sind, und versucht, Zertifikate zu einem konfigurierten Zeitpunkt vor Ablauf zu verlängern.

1. Zum Installieren von Cert Manager müssen Sie zuerst einen Namespace für die Ausführung erstellen. In diesem Tutorial wird Cert Manager im Cert Manager-Namespace installiert. Es ist möglich, Cert Manager in einem anderen Namespace auszuführen. Dann müssen Sie jedoch Änderungen an den Bereitstellungsmanifesten vornehmen.

    ```bash
    kubectl create namespace cert-manager
    ```

2. Sie können nun Cert Manager installieren. Alle Ressourcen sind in einer einzigen YAML-Manifestdatei enthalten. Installieren Sie die Manifestdatei mit dem folgenden Befehl:

    ```bash
    kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
    ```

3. Fügen Sie dem Cert Manager-Namespace die Bezeichnung `certmanager.k8s.io/disable-validation: "true"` hinzu, indem Sie den folgenden Befehl ausführen. Dadurch können die Systemressourcen, die von Cert Manager für das Bootstrapping von TLS benötigt werden, in einem eigenen Namespace erstellt werden.

    ```bash
    kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
    ```

## Abrufen von Zertifikaten über Helm-Diagramme

Helm ist ein Kubernetes-Bereitstellungstool zur Automatisierung von Erstellen, Packen, Konfigurieren und Bereitstellen von Anwendungen und Diensten für Kubernetes-Cluster.

Cert Manager stellt Helm-Diagramme als erstklassige Methode zur Installation in Kubernetes bereit.

1. Fügen Sie das Jetstack Helm-Repository hinzu. Dieses Repository ist die einzige unterstützte Quelle von Cert Manager-Diagrammen. Es gibt einige andere Spiegelungen und Kopien im Internet, aber diese sind völlig inoffiziell und könnten ein Sicherheitsrisiko darstellen.

    ```bash
    helm repo add jetstack https://charts.jetstack.io
    ```

2. Aktualisieren Sie den lokalen Repositorycache für Helm-Diagramme.

    ```bash
    helm repo update
    ```

3. Installieren Sie das Cert Manager-Addon über Helm.

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. Wenden Sie die YAML-Datei des Zertifikatausstellers an. ClusterIssuers sind Kubernetes-Ressourcen, die Zertifizierungsstellen darstellen, die signierte Zertifikate generieren können, indem Zertifikatsignaturanforderungen berücksichtigt werden. Alle Cert Manager-Zertifikate erfordern einen referenzierten Zertifikataussteller, der in der Lage ist, die Anforderung zu berücksichtigen. Sie finden den Aussteller in `cluster-issuer-prod.yml file`.

    ```bash
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## Erstellen einer benutzerdefinierten Speicherklasse

Die Standardspeicherklassen eignen sich für die gängigsten Szenarien, aber nicht für alle. In einigen Fällen möchten Sie möglicherweise Ihre eigene Speicherklasse mit eigenen Parametern anpassen. Verwenden Sie beispielsweise das folgende Manifest, um **mountOptions** der Dateifreigabe zu konfigurieren.
Der Standardwert für **fileMode** und **dirMode** lautet **0755** für in Kubernetes eingebundene Dateifreigaben. Sie können die verschiedenen Einbindungsoptionen im Speicherklassenobjekt angeben.

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## Bereitstellen von WordPress im AKS-Cluster

Für dieses Tutorial verwenden wir ein vorhandenes Helm-Diagramm für WordPress, das von Bitnami erstellt wurde. Das Bitnami Helm-Diagramm verwendet eine lokale MariaDB-Datenbank, und wir müssen diese Werte außer Kraft setzen, um die App mit Azure Database for MySQL zu verwenden. Sie können die Werte und die benutzerdefinierten Einstellungen der `helm-wp-aks-values.yaml`-Datei außer Kraft setzen.

1. Hinzufügen des Wordpress Bitnami Helm-Repositorys.

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. Aktualisieren Sie den lokalen Repositorycache für Helm-Diagramme.

    ```bash
    helm repo update
    ```

3. Installieren Sie die Wordpress-Workload über Helm.

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

Ergebnisse:
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

## Durchsuchen Ihrer über HTTPS gesicherten AKS-Bereitstellung

Führen Sie den folgenden Befehl aus, um den HTTPS-Endpunkt für Ihre Anwendung abzurufen:

> [!NOTE]
> Es dauert oft 2-3 Minuten, bis das SSL-Zertifikat übertragen ist, und etwa 5 Minuten, bis alle WordPress POD-Replikate bereit sind und die Website vollständig über HTTPS erreichbar ist.

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

Überprüfen Sie mit dem folgenden Befehl, ob WordPress-Inhalte ordnungsgemäß übermittelt werden:

```bash
if curl -I -s -f https://$FQDN > /dev/null ; then 
    curl -L -s -f https://$FQDN 2> /dev/null | head -n 9
else 
    exit 1
fi;
```

Ergebnisse:
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

Besuchen Sie die Website über die folgende URL:

```bash
echo "You can now visit your web server at https://$FQDN"
```

## Bereinigen von Ressourcen (optional)

Zum Vermeiden von Azure-Gebühren sollten Sie nicht benötigte Ressourcen bereinigen. Wenn der Cluster nicht mehr benötigt wird, entfernen Sie mit dem Befehl [az group delete](/cli/azure/group#az-group-delete) die Ressourcengruppe, den Containerdienst und alle zugehörigen Ressourcen. 

> [!NOTE]
> Wenn Sie den Cluster löschen, wird der vom AKS-Cluster verwendete Microsoft Entra-Dienstprinzipal nicht entfernt. Schritte zum Entfernen des Dienstprinzipals finden Sie unter den [Überlegungen zum AKS-Dienstprinzipal und dessen Löschung](../../aks/kubernetes-service-principal.md#other-considerations). Wenn Sie eine verwaltete Identität verwendet haben, wird die Identität von der Plattform verwaltet und muss nicht entfernt werden.

## Nächste Schritte

- Informieren Sie sich, wie Sie [auf das Kubernetes-Webdashboard für Ihren AKS-Cluster zugreifen](../../aks/kubernetes-dashboard.md).
- Machen Sie sich mit der Vorgehensweise zum [Skalieren Ihres Clusters](../../aks/tutorial-kubernetes-scale.md) vertraut.
- Informieren Sie sich über die Verwaltung Ihrer [Instanz von Azure Database for MySQL – Flexible Server](./quickstart-create-server-cli.md).
- Informieren Sie sich über das [Konfigurieren von Serverparametern](./how-to-configure-server-parameters-cli.md) für Ihren Datenbankserver.
