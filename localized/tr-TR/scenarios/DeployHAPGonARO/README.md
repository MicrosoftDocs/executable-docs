---
title: Azure Red Hat OpenShift'te Yüksek Oranda Kullanılabilir PostgreSQL Kümesi Oluşturma
description: Bu öğreticide CloudNativePG işlecini kullanarak Azure Red Hat OpenShift (ARO) üzerinde Yüksek Oranda Kullanılabilir PostgreSQL kümesi oluşturma işlemi gösterilmektedir
author: russd2357
ms.author: rdepina
ms.topic: article
ms.date: 04/30/2024
ms.custom: 'innovation-engine, linux-related content'
---

# Azure Red Hat OpenShift'te Yüksek Oranda Kullanılabilir PostgreSQL Kümesi Oluşturma

## CLI kullanarak Azure'da oturum açma

CLI kullanarak Azure'da komut çalıştırmak için oturum açmanız gerekir. Bu çok basit bir şekilde yapılır, ancak `az login` komut:

## Önkoşulları Denetleme

Ardından önkoşulları denetleyin. Bu, aşağıdaki komutları çalıştırarak yapılabilir:

- RedHat OpenShift: `az provider register -n Microsoft.RedHatOpenShift --wait`
- kubectl: `az aks install-cli`
- Openshift İstemcisi: `mkdir ~/ocp ; wget -q https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/openshift-client-linux.tar.gz -O ~/ocp/openshift-client-linux.tar.gz ; tar -xf ~/ocp/openshift-client-linux.tar.gz ; export PATH="$PATH:~/ocp"`

## Kaynak grubu oluşturma

Kaynak grubu, ilgili kaynaklar için bir kapsayıcıdır. Tüm kaynaklar bir kaynak grubuna yerleştirilmelidir. Bu öğretici için bir tane oluşturacağız. Aşağıdaki komut önceden tanımlanmış $RG_NAME, $LOCATION ve $RGTAGS parametreleriyle bir kaynak grubu oluşturur.

```bash
export RGTAGS="owner=ARO Demo"
export LOCATION="westus"
export LOCAL_NAME="arodemo"
export RG_NAME="rg-arodemo-perm"
```

## Sanal ağ oluşturma

Bu bölümde Azure'da bir Sanal Ağ (VNet) oluşturacaksınız. Birkaç ortam değişkeni tanımlayarak başlayın. Bu değişkenler, sanal ağınızın ve alt ağlarınızın adlarının yanı sıra sanal ağınızın CIDR bloğunu barındıracaktır. Ardından az network vnet create komutunu kullanarak kaynak grubunuzda belirtilen ad ve CIDR bloğuyla sanal ağı oluşturun. Bu süreç birkaç dakika sürebilir.

```bash
export VNET_NAME="vnet-${LOCAL_NAME}"
export SUBNET1_NAME="sn-main"
export SUBNET2_NAME="sn-worker"
export VNET_CIDR="10.0.0.0/22"
az network vnet create -g $RG_NAME -n $VNET_NAME --address-prefixes $VNET_CIDR
```

Sonuçlar:

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

## Ana DüğümLer Alt Ağı Oluşturma

Bu bölümde, daha önce oluşturduğunuz Sanal Ağ (VNet) içinde belirtilen ada ve CIDR bloğuna sahip ana düğüm alt ağı oluşturacaksınız. az network vnet subnet create komutunu çalıştırarak başlayın. Bu süreç birkaç dakika sürebilir. Alt ağ başarıyla oluşturulduktan sonra kaynakları bu alt ağa dağıtmaya hazır olursunuz.

```bash
az network vnet subnet create -g $RG_NAME --vnet-name $VNET_NAME -n $SUBNET1_NAME --address-prefixes 10.0.0.0/23
```

Sonuçlar:

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

## Çalışan Düğümleri Alt Ağı Oluşturma

Bu bölümde, önceden oluşturduğunuz Sanal Ağ (VNet) içinde çalışan düğümleriniz için belirtilen ada ve CIDR bloğuna sahip bir alt ağ oluşturacaksınız. az network vnet subnet create komutunu çalıştırarak başlayın. Alt ağ başarıyla oluşturulduktan sonra çalışan düğümlerinizi bu alt ağa dağıtmaya hazır olursunuz.

```bash
az network vnet subnet create -g $RG_NAME --vnet-name $VNET_NAME -n $SUBNET2_NAME --address-prefixes 10.0.2.0/23
```

Sonuçlar:

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

## Depolama hesapları oluşturma

Bu kod parçacığı aşağıdaki adımları gerçekleştirir:

1. Ortam değişkenini `STORAGE_ACCOUNT_NAME` , `LOCAL_NAME` (küçük harfe dönüştürülür) bir birleştirmesine `stor`ayarlar.
2. Ortam değişkenini `BARMAN_CONTAINER_NAME` olarak `"barman"`ayarlar.
3. Belirtilen kaynak grubunda belirtilen `STORAGE_ACCOUNT_NAME` ile bir depolama hesabı oluşturur.
4. Oluşturulan depolama hesabında belirtilen `BARMAN_CONTAINER_NAME` ile bir depolama kapsayıcısı oluşturur.

```bash
export STORAGE_ACCOUNT_NAME="stor${LOCAL_NAME,,}"
export BARMAN_CONTAINER_NAME="barman"

az storage account create --name "${STORAGE_ACCOUNT_NAME}" --resource-group "${RG_NAME}" --sku Standard_LRS
az storage container create --name "${BARMAN_CONTAINER_NAME}" --account-name "${STORAGE_ACCOUNT_NAME}"
```

## ARO kümesini dağıtma

Bu bölümde bir Azure Red Hat OpenShift (ARO) kümesi dağıtacaksınız. ARO_CLUSTER_NAME değişkeni, ARO kümenizin adını tutar. az aro create komutu, ARO kümesini daha önce indirdiğiniz ve Key Vault'unuza kaydettiğiniz belirtilen ad, kaynak grubu, sanal ağ, alt ağlar ve RedHat OpenShift çekme gizli dizisiyle dağıtır. Bu işlemin tamamlanması yaklaşık 30 dakika sürebilir.

```bash
export ARO_CLUSTER_NAME="aro-${LOCAL_NAME}"
export ARO_PULL_SECRET=$(az keyvault secret show --name AroPullSecret --vault-name kv-rdp-dev --query value -o tsv)
export ARO_SP_ID=$(az keyvault secret show --name arodemo-sp-id --vault-name kv-rdp-dev --query value -o tsv)
export ARO_SP_PASSWORD=$(az keyvault secret show --name arodemo-sp-password --vault-name kv-rdp-dev --query value -o tsv)
echo "This will take about 30 minutes to complete..." 
az aro create -g $RG_NAME -n $ARO_CLUSTER_NAME --vnet $VNET_NAME --master-subnet $SUBNET1_NAME --worker-subnet $SUBNET2_NAME --tags $RGTAGS --pull-secret ${ARO_PULL_SECRET} --client-id ${ARO_SP_ID} --client-secret ${ARO_SP_PASSWORD}
```

Sonuçlar:
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

## Küme kimlik bilgilerini alma ve oturum açma

Bu kod, Azure CLI kullanarak bir Azure Red Hat OpenShift (ARO) kümesi için API sunucusu URL'sini ve oturum açma kimlik bilgilerini alır.

`az aro show` Komutu, kaynak grubu adı ve ARO küme adı girerek API sunucusu URL'sini almak için kullanılır. `--query` parametresi özelliği ayıklamak `apiserverProfile.url` için kullanılır ve `-o tsv` sonucu sekmeyle ayrılmış bir değer olarak çıkarmak için seçeneği kullanılır.

`az aro list-credentials` komutu, ARO kümesi için oturum açma kimlik bilgilerini almak için kullanılır. `--name` parametresi ARO küme adını, parametresi ise `--resource-group` kaynak grubu adını belirtir. `--query` parametresi özelliği ayıklamak `kubeadminPassword` için kullanılır ve `-o tsv` sonucu sekmeyle ayrılmış bir değer olarak çıkarmak için seçeneği kullanılır.

Son olarak, `oc login` alınan API sunucusu URL'si, `kubeadmin` kullanıcı adı ve oturum açma kimlik bilgileri kullanılarak ARO kümesinde oturum açmak için komutu kullanılır.

```bash
export apiServer=$(az aro show -g $RG_NAME -n $ARO_CLUSTER_NAME --query apiserverProfile.url -o tsv)
export loginCred=$(az aro list-credentials --name $ARO_CLUSTER_NAME --resource-group $RG_NAME --query "kubeadminPassword" -o tsv)

oc login $apiServer -u kubeadmin -p $loginCred --insecure-skip-tls-verify
```

## ARO'ya işleç ekleme

İşleçleri yerleşik ad alanına yüklemek için ad alanını `openshift-operators`ayarlayın.

```bash
export NAMESPACE="openshift-operators"
```

Bulutta Yerel Postgresql işleci

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

RedHat Keycloak işleci

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

Sonuçlar:
<!-- expected_similarity=0.3 -->
```text
subscription.operators.coreos.com/rhbk-operator created
```

## ARO Posgre'yi oluşturun SQL Veritabanı

Key Vault'tan gizli dizileri getirin ve ARO veritabanı oturum açma gizli dizisi nesnesini oluşturun.

```bash
pgUserName=$(az keyvault secret show --name AroPGUser --vault-name kv-rdp-dev --query value -o tsv)
pgPassword=$(az keyvault secret show --name AroPGPassword --vault-name kv-rdp-dev --query value -o tsv)

oc create secret generic app-auth --from-literal=username=${pgUserName} --from-literal=password=${pgPassword} -n ${NAMESPACE}
```

Sonuçlar:
<!-- expected_similarity=0.3 -->
```text
secret/app-auth created
```

Azure Depolama yedeklemek için gizli dizi oluşturma

```bash
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name ${STORAGE_ACCOUNT_NAME} --resource-group ${RG_NAME} --query "[0].value" --output tsv)
oc create secret generic azure-storage-secret --from-literal=storage-account-name=${STORAGE_ACCOUNT_NAME} --from-literal=storage-account-key=${STORAGE_ACCOUNT_KEY} --namespace ${NAMESPACE}
```

Sonuçlar:
<!-- expected_similarity=0.3 -->
```text
secret/azure-storage-secret created
```

Postgres Kümesini oluşturma

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

Sonuçlar:
<!-- expected_similarity=0.3 -->
```text
cluster.postgresql.k8s.enterprisedb.io/cluster-arodemo created
```

## ARO Keycloak örneğini oluşturma

OpenShift kümesinde keycloak örneği dağıtma. Keycloak kaynağını tanımlayan bir YAML yapılandırma dosyası uygulamak için komutunu kullanır `oc apply` .
YAML yapılandırması, Keycloak örneği için veritabanı, konak adı, HTTP ayarları, giriş, örnek sayısı ve işlem ayarları gibi çeşitli ayarları belirtir.
Keycloak'ı dağıtmak için bu kod bloğunu gerekli izinlere ve OpenShift kümesine erişime sahip bir kabuk ortamında çalıştırın.
Not: , ve değişkenlerinin `$apiServer`değerlerini, `$kc_hosts`veritabanı kimlik bilgilerini (`passwordSecret` ve `usernameSecret`) ortamınız için uygun değerlerle değiştirdiğinden emin olun.

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

Sonuçlar:
<!-- expected_similarity=0.3 -->
```text
keycloak.k8s.keycloak.org/kc001 created
```

İş yüküne erişme

```bash
URL=$(ooc get ingress kc001-ingress -o json | jq -r '.spec.rules[0].host')
curl -Iv https://$URL
```

Sonuçlar:
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
