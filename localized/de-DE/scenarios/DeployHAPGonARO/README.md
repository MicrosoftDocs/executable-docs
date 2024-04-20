---
title: Erstellen eines hochgradig verfügbaren PostgreSQL-Clusters in Azure Red Hat OpenShift
description: 'In diesem Tutorial wird gezeigt, wie Sie mithilfe des CloudNativePG-Operators einen Hochgradig verfügbaren PostgreSQL-Cluster auf Azure Red Hat OpenShift (ARO) erstellen'
author: russd2357
ms.author: rdepina
ms.topic: article
ms.date: 04/16/2024
ms.custom: 'innovation-engine, linux-related content'
---

# Erstellen eines hochgradig verfügbaren PostgreSQL-Clusters in Azure Red Hat OpenShift

## Anmelden bei Azure mit der CLI

Um Befehle für Azure mithilfe der CLI auszuführen, müssen Sie sich anmelden. Dies geschieht ganz einfach mit dem Befehl `az login`:

## Überprüfen auf Voraussetzungen

Als nächstes, prüfen Sie auf Voraussetzungen Dies kann durch Ausführen der folgenden Befehle erfolgen:

- RedHat OpenShift: `az provider register -n Microsoft.RedHatOpenShift --wait`
- kubectl: `az aks install-cli`
- Openshift Client: `mkdir ~/ocp ; wget -q https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/openshift-client-linux.tar.gz -O ~/ocp/openshift-client-linux.tar.gz ; tar -xf ~/ocp/openshift-client-linux.tar.gz ; export PATH="$PATH:~/ocp"`

## Erstellen einer Ressourcengruppe

Eine Ressourcengruppe ist ein Container für zugehörige Ressourcen. Alle Ressourcen müssen in einer Ressourcengruppe platziert werden. In diesem Tutorial erstellen wir eine Ressourcengruppe. Mit dem folgenden Befehl wird eine Ressourcengruppe mit den zuvor definierten Parametern $RG_NAME, $LOCATION und $RGTAGS erstellt.

```bash
export RGTAGS="owner=ARO Demo"
export LOCATION="westus"
export LOCAL_NAME="arodemo"
export SUFFIX=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 6; echo)
export RG_NAME="rg-arodemo-perm"
```

## Erstellen eines VNET

In diesem Abschnitt erstellen Sie ein virtuelles Netzwerk (Virtual Network, VNet) in Azure. Definieren Sie zunächst mehrere Umgebungsvariablen. Diese Variablen enthalten die Namen Ihrer VNet- und Subnetze sowie den CIDR-Block für Ihr VNet. Erstellen Sie als Nächstes das VNet mit dem angegebenen Namen und dem CIDR-Block in Ihrer Ressourcengruppe, indem Sie den Befehl "az network vnet create" verwenden. Dieser Prozess kann einige Minuten in Anspruch nehmen.

```bash
export VNET_NAME="vnet-${LOCAL_NAME}-${SUFFIX}"
export SUBNET1_NAME="sn-main-${SUFFIX}"
export SUBNET2_NAME="sn-worker-${SUFFIX}"
export VNET_CIDR="10.0.0.0/22"
az network vnet create -g $RG_NAME -n $VNET_NAME --address-prefixes $VNET_CIDR
```

Ergebnisse:

<!-- expected_similarity=0.3 -->
```json
{
  "newVNet": {
    "addressSpace": {
      "addressPrefixes": [
        "xx.x.x.x/xx"
      ]
    },
    "enableDdosProtection": false,
    "etag": "W/\"xxxxx-xxxxx-xxxxx-xxxxx\"",
    "id": "/subscriptions/xxxxxx-xxxx-xxxx-xxxxxx/resourceGroups/xx-xxxxx-xxxxx/providers/Microsoft.Network/virtualNetworks/vnet-xx-xxxxx-xxxxx",
    "location": "westus",
    "name": "xxxxx-xxxxx-xxxxx-xxxxx",
    "provisioningState": "Succeeded",
    "resourceGroup": "xx-xxxxx-xxxxx",
    "resourceGuid": "xxxxx-xxxxx-xxxxx-xxxxx",
    "subnets": [],
    "type": "Microsoft.Network/virtualNetworks",
    "virtualNetworkPeerings": []
  }
}
```

## Hauptknoten-Subnetz erstellen

In diesem Abschnitt erstellen Sie das Hauptknoten-Subnetz mit dem angegebenen Namen und dem CIDR-Block in Ihrem zuvor erstellten virtuellen Netzwerk (VNet). Führen Sie zunächst den Befehl "az network vnet subnetz create" aus. Dieser Prozess kann einige Minuten in Anspruch nehmen. Nachdem das Subnetz erfolgreich erstellt wurde, können Sie Ressourcen in diesem Subnetz bereitstellen.

```bash
az network vnet subnet create -g $RG_NAME --vnet-name $VNET_NAME -n $SUBNET1_NAME --address-prefixes 10.0.0.0/23
```

Ergebnisse:

<!-- expected_similarity=0.3 -->
```json
{
  "addressPrefix": "xx.x.x.x/xx",
  "delegations": [],
  "etag": "W/\"xxxxx-xxxxx-xxxxx-xxxxx\"",
  "id": "/subscriptions/xxxxxx-xxxx-xxxx-xxxxxx/resourceGroups/xx-xxxxx-xxxxx/providers/Microsoft.Network/virtualNetworks/vnet-xx-xxxxx-xxxxx/subnets/sn-main-xxxxx",
  "name": "sn-main-xxxxx",
  "privateEndpointNetworkPolicies": "Disabled",
  "privateLinkServiceNetworkPolicies": "Enabled",
  "provisioningState": "Succeeded",
  "resourceGroup": "xx-xxxxx-xxxxx",
  "type": "Microsoft.Network/virtualNetworks/subnets"
}
```

## Workerknoten-Subnetz erstellen

In diesem Abschnitt erstellen Sie ein Subnetz für Ihre Arbeitsknoten mit dem angegebenen Namen und DEM CIDR-Block in Ihrem zuvor erstellten virtuellen Netzwerk (VNet). Führen Sie zunächst den Befehl "az network vnet subnetz create" aus. Nachdem das Subnetz erfolgreich erstellt wurde, können Sie Ihre Arbeitsknoten in diesem Subnetz bereitstellen.

```bash
az network vnet subnet create -g $RG_NAME --vnet-name $VNET_NAME -n $SUBNET2_NAME --address-prefixes 10.0.2.0/23
```

Ergebnisse:

<!-- expected_similarity=0.3 -->
```json
{
  "addressPrefix": "xx.x.x.x/xx",
  "delegations": [],
  "etag": "W/\"xxxxx-xxxxx-xxxxx-xxxxx\"",
  "id": "/subscriptions/xxxxxx-xxxx-xxxx-xxxxxx/resourceGroups/xx-xxxxx-xxxxx/providers/Microsoft.Network/virtualNetworks/vnet-xx-xxxxx-xxxxx/subnets/sn-worker-xxxxx",
  "name": "sn-worker-xxxxx",
  "privateEndpointNetworkPolicies": "Disabled",
  "privateLinkServiceNetworkPolicies": "Enabled",
  "provisioningState": "Succeeded",
  "resourceGroup": "xx-xxxxx-xxxxx",
  "type": "Microsoft.Network/virtualNetworks/subnets"
}
```

## Erstellen von Speicherkonten

Dieser Codeausschnitt führt die folgenden Schritte aus:

1. Legt die `STORAGE_ACCOUNT_NAME` Umgebungsvariable auf eine Verkettung von `stor`, `LOCAL_NAME` (konvertiert in Kleinbuchstaben) und `SUFFIX` (in Kleinbuchstaben konvertiert) fest.
2. Legt die Umgebungsvariable `BARMAN_CONTAINER_NAME` auf `"barman"`.
3. Erstellt ein Speicherkonto mit dem in der angegebenen Ressourcengruppe angegebenen `STORAGE_ACCOUNT_NAME` .
4. Erstellt einen Speichercontainer mit dem im erstellten Speicherkonto angegebenen `BARMAN_CONTAINER_NAME` .

```bash
export STORAGE_ACCOUNT_NAME="stor${LOCAL_NAME,,}${SUFFIX,,}"
export BARMAN_CONTAINER_NAME="barman"

az storage account create --name "${STORAGE_ACCOUNT_NAME}" --resource-group "${RG_NAME}" --sku Standard_LRS
az storage container create --name "${BARMAN_CONTAINER_NAME}" --account-name "${STORAGE_ACCOUNT_NAME}"
```

## Bereitstellen des ARO-Clusters

In diesem Abschnitt stellen Sie einen Azure Red Hat OpenShift (ARO)-Cluster bereit. Die ARO_CLUSTER_NAME Variable enthält den Namen Ihres ARO-Clusters. Der Befehl "az aro create" stellt den ARO-Cluster mit dem angegebenen Namen, der Ressourcengruppe, dem virtuellen Netzwerk, den Subnetzen und dem RedHat OpenShift-Pullschlüssel bereit, den Sie zuvor in Ihrem Key Vault heruntergeladen und gespeichert haben. Dieser Vorgang kann bis zu 30 Minuten dauern.

```bash
export ARO_CLUSTER_NAME="aro-${LOCAL_NAME}-${SUFFIX}"
export ARO_PULL_SECRET=$(az keyvault secret show --name AroPullSecret --vault-name kv-rdp-dev --query value -o tsv)
export ARO_SP_ID=$(az keyvault secret show --name arodemo-sp-id --vault-name kv-rdp-dev --query value -o tsv)
export ARO_SP_PASSWORD=$(az keyvault secret show --name arodemo-sp-password --vault-name kv-rdp-dev --query value -o tsv)
echo "This will take about 30 minutes to complete..." 
az aro create -g $RG_NAME -n $ARO_CLUSTER_NAME --vnet $VNET_NAME --master-subnet $SUBNET1_NAME --worker-subnet $SUBNET2_NAME --tags $RGTAGS --pull-secret ${ARO_PULL_SECRET} --client-id ${ARO_SP_ID} --client-secret ${ARO_SP_PASSWORD}
```

Ergebnisse:
<!-- expected_similarity=0.3 -->
```json
{
  "apiserverProfile": {
    "ip": "xx.xxx.xx.xxx",
    "url": "https://api.xxxxx.xxxxxx.aroapp.io:xxxx/",
    "visibility": "Public"
  },
  "clusterProfile": {
    "domain": "xxxxxx",
    "fipsValidatedModules": "Disabled",
    "pullSecret": null,
    "resourceGroupId": "/subscriptions/xxxxxx-xxxxxx-xxxxxx-xxxxxx-xxxxxx/resourcegroups/xxxxxx-xxxxxx",
    "version": "4.12.25"
  },
  "consoleProfile": {
    "url": "https://console-openshift-console.apps.xxxxxx.xxxxxx.aroapp.io/"
  },
  "id": "/subscriptions/xxxxxx-xxxxxx-xxxxxx-xxxxxx-xxxxxx/resourceGroups/rg-arodemo-xxxxxx/providers/Microsoft.RedHatOpenShift/openShiftClusters/aro-arodemo-xxxxxx",
  "ingressProfiles": [
    {
      "ip": "xx.xxx.xx.xxx",
      "name": "default",
      "visibility": "Public"
    }
  ],
  "location": "westus",
  "masterProfile": {
    "diskEncryptionSetId": null,
    "encryptionAtHost": "Disabled",
    "subnetId": "/subscriptions/xxxxxx-xxxxxx-xxxxxx-xxxxxx-xxxxxx/resourceGroups/rg-arodemo-xxxxxx/providers/Microsoft.Network/virtualNetworks/vnet-arodemo-xxxxxx/subnets/sn-main-jffspl",
    "vmSize": "Standard_D8s_v3"
  },
  "name": "aro-arodemo-xxxxxx",
  "networkProfile": {
    "outboundType": "Loadbalancer",
    "podCidr": "xx.xxx.xx.xxx/xx",
    "preconfiguredNsg": "Disabled",
    "serviceCidr": "xx.xxx.xx.xxx/xx"
  },
  "provisioningState": "Succeeded",
  "resourceGroup": "rg-arodemo-xxxxxx",
  "servicePrincipalProfile": {
    "clientId": "xxxxxx-xxxxxx-xxxxxx-xxxxxx-xxxxxx",
    "clientSecret": null
  },
  "systemData": {
    "createdAt": "xxxxxx-xx-xxxxxx:xx:xx.xxxxxx+xx:xx",
    "createdBy": "xxxxxx@xxxxxx.xxx",
    "createdByType": "User",
    "lastModifiedAt": "xxxxxx-xx-xxxxxx:xx:xx.xxxxxx+xx:xx",
    "lastModifiedBy": "xxxxxx@xxxxxx.xxx",
    "lastModifiedByType": "User"
  },
  "tags": {
    "Demo": "",
    "owner": "ARO"
  },
  "type": "Microsoft.RedHatOpenShift/openShiftClusters",
  "workerProfiles": [
    {
      "count": 3,
      "diskEncryptionSetId": null,
      "diskSizeGb": 128,
      "encryptionAtHost": "Disabled",
      "name": "worker",
      "subnetId": "/subscriptions/xxxxxx-xxxxxx-xxxxxx-xxxxxx-xxxxxx/resourceGroups/rg-arodemo-xxxxxx/providers/Microsoft.Network/virtualNetworks/vnet-arodemo-xxxxxx/subnets/sn-worker-xxxxxx",
      "vmSize": "Standard_D4s_v3"
    }
  ],
  "workerProfilesStatus": [
    {
      "count": 3,
      "diskEncryptionSetId": null,
      "diskSizeGb": 128,
      "encryptionAtHost": "Disabled",
      "name": "aro-arodemo-xxxxxx-xxxxxx-worker-westus",
      "subnetId": "/subscriptions/xxxxxx-xxxxxx-xxxxxx-xxxxxx-xxxxxx/resourceGroups/rg-arodemo-xxxxxx/providers/Microsoft.Network/virtualNetworks/vnet-arodemo-xxxxxx/subnets/sn-worker-xxxxxx",
      "vmSize": "Standard_D4s_v3"
    }
  ]
}
```

## Abrufen von Clusteranmeldeinformationen und Anmeldung

Dieser Code ruft die API-Server-URL und Anmeldeinformationen für einen Azure Red Hat OpenShift (ARO)-Cluster mithilfe der Azure CLI ab.

Der `az aro show` Befehl wird verwendet, um die API-Server-URL abzurufen, indem der Ressourcengruppenname und der ARO-Clustername angegeben wird. Der `--query` Parameter wird verwendet, um die `apiserverProfile.url` Eigenschaft zu extrahieren, und die `-o tsv` Option wird verwendet, um das Ergebnis als tabstopptrennten Wert auszugeben.

Der `az aro list-credentials` Befehl wird verwendet, um die Anmeldeinformationen für den ARO-Cluster abzurufen. Der `--name` Parameter gibt den ARO-Clusternamen an, und der `--resource-group` Parameter gibt den Ressourcengruppennamen an. Der `--query` Parameter wird verwendet, um die `kubeadminPassword` Eigenschaft zu extrahieren, und die `-o tsv` Option wird verwendet, um das Ergebnis als tabstopptrennten Wert auszugeben.

Schließlich wird der `oc login` Befehl verwendet, um sich mit der abgerufenen API-Server-URL, dem `kubeadmin` Benutzernamen und den Anmeldeinformationen beim ARO-Cluster anzumelden.

```bash
export apiServer=$(az aro show -g $RG_NAME -n $ARO_CLUSTER_NAME --query apiserverProfile.url -o tsv)
export loginCred=$(az aro list-credentials --name $ARO_CLUSTER_NAME --resource-group $RG_NAME --query "kubeadminPassword" -o tsv)

oc login $apiServer -u kubeadmin -p $loginCred --insecure-skip-tls-verify
```

## Hinzufügen von Operatoren zu ARO

Legen Sie den Namespace fest, um die Operatoren im integrierten Namespace `openshift-operators`zu installieren.

```bash
export NAMESPACE="openshift-operators"
```

Cloud Native Postgresql-Operator

```bash
channelspec=$(oc get packagemanifests cloud-native-postgresql -o jsonpath="{range .status.channels[*]}Channel: {.name} currentCSV: {.currentCSV}{'\n'}{end}" | grep "stable-v1.22")
IFS=" " read -r -a array <<< "${channelspec}"
channel=${array[1]}
csv=${array[3]}

catalogSource=$(oc get packagemanifests cloud-native-postgresql -o jsonpath="{.status.catalogSource}")
catalogSourceNamespace=$(oc get packagemanifests cloud-native-postgresql -o jsonpath="{.status.catalogSourceNamespace}")

cat <<EOF | oc apply -f -
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: cloud-native-postgresql
  namespace: ${NAMESPACE}
spec:
    channel: $channel
    name: cloud-native-postgresql
    source: $catalogSource
    sourceNamespace: $catalogSourceNamespace
    installPlanApproval: Automatic
    startingCSV: $csv
EOF
```

RedHat Keycloak-Operator

```bash
channelspec_kc=$(oc get packagemanifests rhbk-operator -o jsonpath="{range .status.channels[*]}Channel: {.name} currentCSV: {.currentCSV}{'\n'}{end}" | grep "stable-v22")
IFS=" " read -r -a array <<< "${channelspec_kc}"
channel_kc=${array[1]}
csv_kc=${array[3]}

catalogSource_kc=$(oc get packagemanifests rhbk-operator -o jsonpath="{.status.catalogSource}")
catalogSourceNamespace_kc=$(oc get packagemanifests rhbk-operator -o jsonpath="{.status.catalogSourceNamespace}")

cat <<EOF | oc apply -f -
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: rhbk-operator
  namespace: ${NAMESPACE}
spec:
  channel: $channel_kc
  name: rhbk-operator
  source: $catalogSource_kc
  sourceNamespace: $catalogSourceNamespace_kc
  startingCSV: $csv_kc
EOF
```

Ergebnisse:
<!-- expected_similarity=0.3 -->
```text
subscription.operators.coreos.com/rhbk-operator created
```

## Erstellen sie die ARO Posgre SQL-Datenbank

Rufen Sie geheime Schlüssel aus Key Vault ab, und erstellen Sie das geheime ARO-Datenbank-Anmeldeschlüsselobjekt.

```bash
pgUserName=$(az keyvault secret show --name AroPGUser --vault-name kv-rdp-dev --query value -o tsv)
pgPassword=$(az keyvault secret show --name AroPGPassword --vault-name kv-rdp-dev --query value -o tsv)

oc create secret generic app-auth --from-literal=username=${pgUserName} --from-literal=password=${pgPassword} -n ${NAMESPACE}
```

Ergebnisse:
<!-- expected_similarity=0.3 -->
```text
secret/app-auth created
```

Erstellen des geheimen Schlüssels für die Sicherung in Azure Storage

```bash
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name ${STORAGE_ACCOUNT_NAME} --resource-group ${RG_NAME} --query "[0].value" --output tsv)
oc create secret generic azure-storage-secret --from-literal=storage-account-name=${STORAGE_ACCOUNT_NAME} --from-literal=storage-account-key=${STORAGE_ACCOUNT_KEY} --namespace ${NAMESPACE}
```

Ergebnisse:
<!-- expected_similarity=0.3 -->
```text
secret/azure-storage-secret created
```

Erstellen des Postgres-Clusters

```bash
cat <<EOF | oc apply -f -
---
apiVersion: postgresql.k8s.enterprisedb.io/v1
kind: Cluster
metadata:
  name: cluster-arodemo
  namespace: ${NAMESPACE}
spec:
  description: "HA Postgres Cluster Demo for ARO"
  # Choose your PostGres Database Version
  imageName: ghcr.io/cloudnative-pg/postgresql:15.2
  # Number of Replicas
  instances: 3
  startDelay: 300
  stopDelay: 300
  replicationSlots:
    highAvailability:
      enabled: true
    updateInterval: 300
  primaryUpdateStrategy: unsupervised
  postgresql:
    parameters:
      shared_buffers: 256MB
      pg_stat_statements.max: '10000'
      pg_stat_statements.track: all
      auto_explain.log_min_duration: '10s'
    pg_hba:
      # - hostssl app all all cert
      - host app app all password
  logLevel: debug
  # Choose the right storageclass for type of workload.
  storage:
    storageClass: managed-csi
    size: 1Gi
  walStorage:
    storageClass: managed-csi
    size: 1Gi
  monitoring:
    enablePodMonitor: true
  bootstrap:
    initdb: # Deploying a new cluster
      database: WorldDB
      owner: app
      secret:
        name: app-auth
  backup:
    barmanObjectStore:
      # For backup, we use a blob container in an Azure Storage Account to store data.
      # On this Blueprint, we get the account and container name from the environment variables.
      destinationPath: https://${STORAGE_ACCOUNT_NAME}.blob.core.windows.net/${BARMAN_CONTAINER_NAME}/
      azureCredentials:
        storageAccount:
          name: azure-storage-secret
          key: storage-account-name
        storageKey:
          name: azure-storage-secret
          key: storage-account-key
      wal:
        compression: gzip
        maxParallel: 8
    retentionPolicy: "30d"

  affinity:
    enablePodAntiAffinity: true
    topologyKey: failure-domain.beta.kubernetes.io/zone

  nodeMaintenanceWindow:
    inProgress: false
    reusePVC: false
EOF
```

Ergebnisse:
<!-- expected_similarity=0.3 -->
```text
cluster.postgresql.k8s.enterprisedb.io/cluster-arodemo created
```

## Erstellen der ARO Keycloak-Instanz

Stellen Sie eine Keycloak-Instanz auf einem OpenShift-Cluster bereit. Er verwendet den `oc apply` Befehl, um eine YAML-Konfigurationsdatei anzuwenden, die die Keycloak-Ressource definiert.
Die YAML-Konfiguration gibt verschiedene Einstellungen für die Keycloak-Instanz an, einschließlich datenbank, Hostname, HTTP-Einstellungen, Eingangs, Anzahl von Instanzen und Transaktionseinstellungen.
Um Keycloak bereitzustellen, führen Sie diesen Codeblock in einer Shellumgebung mit den erforderlichen Berechtigungen und dem Zugriff auf den OpenShift-Cluster aus.
Hinweis: Ersetzen Sie die Werte der Variablen `$apiServer`, `$kc_hosts`und die Datenbankanmeldeinformationen (`passwordSecret` und `usernameSecret`) durch die entsprechenden Werte für Ihre Umgebung.

```bash
export kc_hosts=$(echo $apiServer | sed -E 's/\/\/api\./\/\/apps./' | sed -En 's/.*\/\/([^:]+).*/\1/p' )

cat <<EOF | oc apply -f -
apiVersion: k8s.keycloak.org/v2alpha1
kind: Keycloak
metadata:
  labels:
    app: sso
  name: kc001
  namespace: ${NAMESPACE}
spec:
  db:
    database: WorldDB
    host: cluster-arodemo-rw
    passwordSecret:
      key: password
      name: app-auth
    port: 5432
    usernameSecret:
      key: username
      name: app-auth
    vendor: postgres
  hostname:
    hostname: kc001.${kc_hosts}
  http:
    httpEnabled: true
  ingress:
    enabled: true
  instances: 1
  transaction:
    xaEnabled: false
EOF
```

Ergebnisse:
<!-- expected_similarity=0.3 -->
```text
keycloak.k8s.keycloak.org/kc001 created
```

Zugreifen auf die Workload

```bash
URL=$(ooc get ingress kc001-ingress -o json | jq -r '.spec.rules[0].host')
curl -Iv https://$URL
```

Ergebnisse:
<!-- expected_similarity=0.3 -->
```text
*   Trying 104.42.132.245:443...
* Connected to kc001.apps.foppnyl9.westus.aroapp.io (104.42.132.245) port 443 (#0)
* ALPN, offering h2
* ALPN, offering http/1.1
*  CAfile: /etc/ssl/certs/ca-certificates.crt
*  CApath: /etc/ssl/certs
* TLSv1.0 (OUT), TLS header, Certificate Status (22):
* TLSv1.3 (OUT), TLS handshake, Client hello (1):
* TLSv1.2 (IN), TLS header, Certificate Status (22):
* TLSv1.3 (IN), TLS handshake, Server hello (2):
```
