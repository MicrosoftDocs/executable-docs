---
title: Créer un cluster PostgreSQL hautement disponible sur Azure Red Hat OpenShift
description: Ce tutoriel montre comment créer un cluster PostgreSQL hautement disponible sur Azure Red Hat OpenShift (ARO) à l’aide de l’opérateur CloudNativePG
author: russd2357
ms.author: rdepina
ms.topic: article
ms.date: 04/16/2024
ms.custom: 'innovation-engine, linux-related content'
---

# Créer un cluster PostgreSQL hautement disponible sur Azure Red Hat OpenShift

## Connectez-vous à Azure à l’aide de l’interface CLI

Pour exécuter des commandes sur Azure à l’aide de l’interface CLI, vous devez vous connecter. Pour cela, utilisez tout simplement la commande `az login` :

## Rechercher les conditions préalables

Vérifiez ensuite les conditions préalables. Pour ce faire, exécutez les commandes suivantes :

- RedHat OpenShift : `az provider register -n Microsoft.RedHatOpenShift --wait`
- kubectl : `az aks install-cli`
- Openshift Client : `mkdir ~/ocp ; wget -q https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/openshift-client-linux.tar.gz -O ~/ocp/openshift-client-linux.tar.gz ; tar -xf ~/ocp/openshift-client-linux.tar.gz ; export PATH="$PATH:~/ocp"`

## Créer un groupe de ressources

Un groupe de ressources est un conteneur de ressources associées. Toutes les ressources doivent être placées dans un groupe de ressources. Nous en créons un pour ce tutoriel. La commande suivante crée un groupe de ressources avec les paramètres $RG_NAME, $LOCATION et $RGTAGS précédemment définis.

```bash
export RGTAGS="owner=ARO Demo"
export LOCATION="westus"
export LOCAL_NAME="arodemo"
export SUFFIX=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 6; echo)
export RG_NAME="rg-${LOCAL_NAME}-${SUFFIX}"
az group create -n $RG_NAME -l $LOCATION --tags $RGTAGS
```

Résultats :

<!-- expected_similarity=0.3 -->
```json
{
"id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/xx-xxxxx-xxxxx",
"location": "westus",
"managedBy": null,
"name": "xx-xxxxx-xxxxx",
"properties": {
    "provisioningState": "Succeeded"
},
"tags": {
    "owner": "xxx xxxx"
},
"type": "Microsoft.Resources/resourceGroups"
}
```

## Créer un réseau virtuel

Dans cette section, vous allez créer un réseau virtuel (VNet) dans Azure. Commencez par définir plusieurs variables d’environnement. Ces variables contiennent les noms de vos réseaux virtuels et sous-réseaux, ainsi que le bloc CIDR pour votre réseau virtuel. Ensuite, créez le réseau virtuel avec le nom et le bloc CIDR spécifiés dans votre groupe de ressources à l’aide de la commande az network vnet create. Cette opération peut prendre quelques minutes.

```bash
export VNET_NAME="vnet-${LOCAL_NAME}-${SUFFIX}"
export SUBNET1_NAME="sn-main-${SUFFIX}"
export SUBNET2_NAME="sn-worker-${SUFFIX}"
export VNET_CIDR="10.0.0.0/22"
az network vnet create -g $RG_NAME -n $VNET_NAME --address-prefixes $VNET_CIDR
```

Résultats :

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

## Créer un sous-réseau de nœuds principaux

Dans cette section, vous allez créer le sous-réseau principal des nœuds avec le nom et le bloc CIDR spécifiés dans votre réseau virtuel précédemment créé. Commencez par exécuter la commande az network vnet subnet create. Cette opération peut prendre quelques minutes. Une fois le sous-réseau créé, vous serez prêt à déployer des ressources dans ce sous-réseau.

```bash
az network vnet subnet create -g $RG_NAME --vnet-name $VNET_NAME -n $SUBNET1_NAME --address-prefixes 10.0.0.0/23
```

Résultats :

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

## Créer un sous-réseau de nœuds Worker

Dans cette section, vous allez créer un sous-réseau pour vos nœuds Worker avec le nom et le bloc CIDR spécifiés dans votre réseau virtuel précédemment créé. Commencez par exécuter la commande az network vnet subnet create. Une fois le sous-réseau créé, vous serez prêt à déployer vos nœuds Worker dans ce sous-réseau.

```bash
az network vnet subnet create -g $RG_NAME --vnet-name $VNET_NAME -n $SUBNET2_NAME --address-prefixes 10.0.2.0/23
```

Résultats :

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

## Créer des comptes de stockage

Cet extrait de code effectue les étapes suivantes :

1. Définit la `STORAGE_ACCOUNT_NAME` variable d’environnement en concaténation de `stor`, `LOCAL_NAME` (convertie en minuscules) et `SUFFIX` (convertie en minuscules).
2. Définit la variable d’environnement `BARMAN_CONTAINER_NAME` sur `"barman"`.
3. Crée un compte de stockage avec le groupe de ressources spécifié `STORAGE_ACCOUNT_NAME` .
4. Crée un conteneur de stockage avec le compte de stockage créé `BARMAN_CONTAINER_NAME` .

```bash
export STORAGE_ACCOUNT_NAME="stor${LOCAL_NAME,,}${SUFFIX,,}"
export BARMAN_CONTAINER_NAME="barman"

az storage account create --name "${STORAGE_ACCOUNT_NAME}" --resource-group "${RG_NAME}" --sku Standard_LRS
az storage container create --name "${BARMAN_CONTAINER_NAME}" --account-name "${STORAGE_ACCOUNT_NAME}"
```

## Déployer le cluster ARO

Dans cette section, vous allez déployer un cluster Azure Red Hat OpenShift (ARO). La variable ARO_CLUSTER_NAME contiendra le nom de votre cluster ARO. La commande az aro create déploie le cluster ARO avec le nom, le groupe de ressources, le réseau virtuel, les sous-réseaux et le secret d’extraction RedHat OpenShift que vous avez précédemment téléchargé et enregistré dans votre coffre de clés. Ce processus prend environ 30 minutes.

```bash
export ARO_CLUSTER_NAME="aro-${LOCAL_NAME}-${SUFFIX}"
export ARO_PULL_SECRET=$(az keyvault secret show --name AROPullSecret --vault-name AROKeyVault --query value -o tsv)
echo "This will take about 30 minutes to complete..." 
az aro create -g $RG_NAME -n $ARO_CLUSTER_NAME --vnet $VNET_NAME --master-subnet $SUBNET1_NAME --worker-subnet $SUBNET2_NAME --tags $RGTAGS --pull-secret ${ARO_PULL_SECRET}
```

Résultats :
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

## Obtenir les informations d’identification et la connexion du cluster

Ce code récupère l’URL du serveur d’API et les informations d’identification de connexion pour un cluster Azure Red Hat OpenShift (ARO) à l’aide d’Azure CLI.

La `az aro show` commande est utilisée pour obtenir l’URL du serveur d’API en fournissant le nom du groupe de ressources et le nom du cluster ARO. Le `--query` paramètre est utilisé pour extraire la `apiserverProfile.url` propriété et l’option `-o tsv` est utilisée pour générer le résultat sous forme de valeur séparée par tabulation.

La `az aro list-credentials` commande est utilisée pour obtenir les informations d’identification de connexion du cluster ARO. Le `--name` paramètre spécifie le nom du cluster ARO et le `--resource-group` paramètre spécifie le nom du groupe de ressources. Le `--query` paramètre est utilisé pour extraire la `kubeadminPassword` propriété et l’option `-o tsv` est utilisée pour générer le résultat sous forme de valeur séparée par tabulation.

Enfin, la `oc login` commande est utilisée pour se connecter au cluster ARO à l’aide de l’URL du serveur d’API récupérée, du `kubeadmin` nom d’utilisateur et des informations d’identification de connexion.

```bash
export apiServer=$(az aro show -g $RG_NAME -n $ARO_CLUSTER_NAME --query apiserverProfile.url -o tsv)
export loginCred=$(az aro list-credentials --name $ARO_CLUSTER_NAME --resource-group $RG_NAME --query "kubeadminPassword" -o tsv)

oc login $apiServer -u kubeadmin -p $loginCred --insecure-skip-tls-verify
```

## Ajouter des opérateurs à ARO

Définissez l’espace de noms pour installer les opérateurs dans l’espace de noms `openshift-operators`intégré.

```bash
export NAMESPACE="openshift-operators"
```

Opérateur Postgresql natif cloud

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

Opérateur RedHat Keycloak

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

Résultats :
<!-- expected_similarity=0.3 -->
```text
subscription.operators.coreos.com/rhbk-operator created
```

## Créer la base de données ARO PosgreSQL

Récupérez des secrets à partir de Key Vault et créez l’objet secret de connexion de base de données ARO.

```bash
pgUserName=$(az keyvault secret show --name AroPGUser --vault-name AROKeyVault --query value -o tsv)
pgPassword=$(az keyvault secret show --name AroPGPassword --vault-name AROKeyVault --query value -o tsv)

oc create secret generic app-auth --from-literal=username=${pgUserName} --from-literal=password=${pgPassword} -n ${NAMESPACE}
```

Résultats :
<!-- expected_similarity=0.3 -->
```text
secret/app-auth created
```

Créez le secret pour la sauvegarde sur Stockage Azure

```bash
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name ${STORAGE_ACCOUNT_NAME} --resource-group ${RG_NAME} --query "[0].value" --output tsv)
oc create secret generic azure-storage-secret --from-literal=storage-account-name=${STORAGE_ACCOUNT_NAME} --from-literal=storage-account-key=${STORAGE_ACCOUNT_KEY} --namespace ${NAMESPACE}
```

Résultats :
<!-- expected_similarity=0.3 -->
```text
secret/azure-storage-secret created
```

Créer le cluster Postgres

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

Résultats :
<!-- expected_similarity=0.3 -->
```text
cluster.postgresql.k8s.enterprisedb.io/cluster-arodemo created
```

## Créer l’instance ARO Keycloak

Déployez une instance Keycloak sur un cluster OpenShift. Il utilise la `oc apply` commande pour appliquer un fichier de configuration YAML qui définit la ressource Keycloak.
La configuration YAML spécifie différents paramètres pour l’instance Keycloak, notamment la base de données, le nom d’hôte, les paramètres HTTP, l’entrée, le nombre d’instances et les paramètres de transaction.
Pour déployer Keycloak, exécutez ce bloc de code dans un environnement shell avec les autorisations nécessaires et l’accès au cluster OpenShift.
Remarque : veillez à remplacer les valeurs des variables `$apiServer`, `$kc_hosts`ainsi que les informations d’identification de la base de données (`passwordSecret` et `usernameSecret`) par les valeurs appropriées pour votre environnement.

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

Résultats :
<!-- expected_similarity=0.3 -->
```text
keycloak.k8s.keycloak.org/kc001 created
```

Accéder à la charge de travail

```bash
URL=$(ooc get ingress kc001-ingress -o json | jq -r '.spec.rules[0].host')
curl -Iv https://$URL
```

Résultats :
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
