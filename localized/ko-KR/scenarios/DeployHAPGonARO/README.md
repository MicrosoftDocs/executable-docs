---
title: Azure Red Hat OpenShift에서 고가용성 PostgreSQL 클러스터 만들기
description: 이 자습서에서는 CloudNativePG 연산자를 사용하여 ARO(Azure Red Hat OpenShift)에서 고가용성 PostgreSQL 클러스터를 만드는 방법을 보여 줍니다.
author: russd2357
ms.author: rdepina
ms.topic: article
ms.date: 04/30/2024
ms.custom: 'innovation-engine, linux-related content'
---

# Azure Red Hat OpenShift에서 고가용성 PostgreSQL 클러스터 만들기

## CLI를 사용하여 Azure에 로그인

CLI를 사용하여 Azure에 대해 명령을 실행하려면 로그인해야 합니다. 이 작업은 명령을 통해 매우 간단하게 수행됩니다.`az login`

## 필수 구성 요소 확인

다음으로, 필수 구성 요소에 대한 검사. 이 작업은 다음 명령을 실행하여 수행할 수 있습니다.

- RedHat OpenShift: `az provider register -n Microsoft.RedHatOpenShift --wait`
- kubectl: `az aks install-cli`
- Openshift 클라이언트: `mkdir ~/ocp ; wget -q https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/openshift-client-linux.tar.gz -O ~/ocp/openshift-client-linux.tar.gz ; tar -xf ~/ocp/openshift-client-linux.tar.gz ; export PATH="$PATH:~/ocp"`

## 리소스 그룹 만들기

리소스 그룹은 관련 리소스에 대한 컨테이너입니다. 모든 리소스는 리소스 그룹에 배치되어야 합니다. 이 자습서에 대해 만들겠습니다. 다음 명령은 이전에 정의된 $RG_NAME, $LOCATION 및 $RGTAGS 매개 변수를 사용하여 리소스 그룹을 만듭니다.

```bash
export RGTAGS="owner=ARO Demo"
export LOCATION="westus"
export LOCAL_NAME="arodemo"
export RG_NAME="rg-arodemo-perm"
az group create -n $RG_NAME -l $LOCATION --tags $RGTAGS
```

Results:
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

## VNet 만들기

이 섹션에서는 Azure에서 VNet(Virtual Network)을 만듭니다. 먼저 여러 환경 변수를 정의합니다. 이러한 변수에는 VNet 및 서브넷의 이름과 VNet의 CIDR 블록이 포함됩니다. 다음으로, az network vnet create 명령을 사용하여 리소스 그룹에 지정된 이름과 CIDR 블록을 사용하여 VNet을 만듭니다. 이 프로세스에는 몇 분 정도가 소요됩니다.

```bash
export VNET_NAME="vnet-${LOCAL_NAME}"
export SUBNET1_NAME="sn-main"
export SUBNET2_NAME="sn-worker"
export VNET_CIDR="10.0.0.0/22"
az network vnet create -g $RG_NAME -n $VNET_NAME --address-prefixes $VNET_CIDR
```

Results:

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

## 주 노드 서브넷 만들기

이 섹션에서는 이전에 만든 VNet(Virtual Network) 내에서 지정된 이름과 CIDR 블록을 사용하여 기본 노드 서브넷을 만듭니다. 먼저 az network vnet subnet create 명령을 실행합니다. 이 프로세스에는 몇 분 정도가 소요됩니다. 서브넷이 성공적으로 만들어지면 이 서브넷에 리소스를 배포할 준비가 됩니다.

```bash
az network vnet subnet create -g $RG_NAME --vnet-name $VNET_NAME -n $SUBNET1_NAME --address-prefixes 10.0.0.0/23
```

Results:

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

## 작업자 노드 서브넷 만들기

이 섹션에서는 이전에 만든 VNet(Virtual Network) 내에서 지정된 이름과 CIDR 블록을 사용하여 작업자 노드에 대한 서브넷을 만듭니다. 먼저 az network vnet subnet create 명령을 실행합니다. 서브넷이 성공적으로 만들어지면 작업자 노드를 이 서브넷에 배포할 준비가 됩니다.

```bash
az network vnet subnet create -g $RG_NAME --vnet-name $VNET_NAME -n $SUBNET2_NAME --address-prefixes 10.0.2.0/23
```

Results:

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

## Storage 계정 만들기

이 코드 조각은 다음 단계를 수행합니다.

1. 환경 변수를 `STORAGE_ACCOUNT_NAME` 의 `stor``LOCAL_NAME` 연결(소문자로 변환)으로 설정합니다.
2. 환경 변수를 `BARMAN_CONTAINER_NAME` .로 `"barman"`설정합니다.
3. 지정된 리소스 그룹에 지정된 `STORAGE_ACCOUNT_NAME` 스토리지 계정을 만듭니다.
4. 만든 스토리지 계정에 지정된 `BARMAN_CONTAINER_NAME` 스토리지 컨테이너를 만듭니다.

```bash
export STORAGE_ACCOUNT_NAME="stor${LOCAL_NAME,,}"
export BARMAN_CONTAINER_NAME="barman"

az storage account create --name "${STORAGE_ACCOUNT_NAME}" --resource-group "${RG_NAME}" --sku Standard_LRS
az storage container create --name "${BARMAN_CONTAINER_NAME}" --account-name "${STORAGE_ACCOUNT_NAME}"
```

## ARO 클러스터 배포

이 섹션에서는 ARO(Azure Red Hat OpenShift) 클러스터를 배포합니다. ARO_CLUSTER_NAME 변수는 ARO 클러스터의 이름을 보유합니다. az aro create 명령은 이전에 Key Vault에서 다운로드하고 저장한 지정된 이름, 리소스 그룹, 가상 네트워크, 서브넷 및 RedHat OpenShift 끌어오기 비밀을 사용하여 ARO 클러스터를 배포합니다. 이 프로세스를 완료하는 데 약 30분이 걸릴 수 있습니다.

```bash
export ARO_CLUSTER_NAME="aro-${LOCAL_NAME}"
export ARO_PULL_SECRET=$(az keyvault secret show --name AroPullSecret --vault-name kv-rdp-dev --query value -o tsv)
export ARO_SP_ID=$(az keyvault secret show --name arodemo-sp-id --vault-name kv-rdp-dev --query value -o tsv)
export ARO_SP_PASSWORD=$(az keyvault secret show --name arodemo-sp-password --vault-name kv-rdp-dev --query value -o tsv)
echo "This will take about 30 minutes to complete..." 
az aro create -g $RG_NAME -n $ARO_CLUSTER_NAME --vnet $VNET_NAME --master-subnet $SUBNET1_NAME --worker-subnet $SUBNET2_NAME --tags $RGTAGS --pull-secret ${ARO_PULL_SECRET} --client-id ${ARO_SP_ID} --client-secret ${ARO_SP_PASSWORD}
```

Results:
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

## 클러스터 자격 증명 및 로그인 가져오기

이 코드는 Azure CLI를 사용하여 ARO(Azure Red Hat OpenShift) 클러스터에 대한 API 서버 URL 및 로그인 자격 증명을 검색합니다.

이 `az aro show` 명령은 리소스 그룹 이름 및 ARO 클러스터 이름을 제공하여 API 서버 URL을 가져오는 데 사용됩니다. 매개 변수는 `--query` 속성을 추출 `apiserverProfile.url` 하는 데 사용되며 `-o tsv` , 이 옵션은 결과를 탭으로 구분된 값으로 출력하는 데 사용됩니다.

이 `az aro list-credentials` 명령은 ARO 클러스터에 대한 로그인 자격 증명을 가져오는 데 사용됩니다. 매개 변수는 `--name` ARO 클러스터 이름을 지정하고 매개 변수는 `--resource-group` 리소스 그룹 이름을 지정합니다. 매개 변수는 `--query` 속성을 추출 `kubeadminPassword` 하는 데 사용되며 `-o tsv` , 이 옵션은 결과를 탭으로 구분된 값으로 출력하는 데 사용됩니다.

마지막으로 이 명령은 검색된 API 서버 URL, `oc login` 사용자 이름 및 로그인 자격 증명을 사용하여 ARO 클러스터에 `kubeadmin` 로그인하는 데 사용됩니다.

```bash
export apiServer=$(az aro show -g $RG_NAME -n $ARO_CLUSTER_NAME --query apiserverProfile.url -o tsv)
export loginCred=$(az aro list-credentials --name $ARO_CLUSTER_NAME --resource-group $RG_NAME --query "kubeadminPassword" -o tsv)

oc login $apiServer -u kubeadmin -p $loginCred --insecure-skip-tls-verify
```

## ARO에 연산자 추가

기본 제공 네임스페이스에 연산자를 설치하도록 네임스페이스를 `openshift-operators`설정합니다.

```bash
export NAMESPACE="openshift-operators"
```

클라우드 네이티브 Postgresql 연산자

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

RedHat Keycloak 연산자

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

Results:
<!-- expected_similarity=0.3 -->
```text
subscription.operators.coreos.com/rhbk-operator created
```

## ARO PosgreSQL 데이터베이스 만들기

Key Vault에서 비밀을 가져오고 ARO 데이터베이스 로그인 비밀 개체를 만듭니다.

```bash
pgUserName=$(az keyvault secret show --name AroPGUser --vault-name kv-rdp-dev --query value -o tsv)
pgPassword=$(az keyvault secret show --name AroPGPassword --vault-name kv-rdp-dev --query value -o tsv)

oc create secret generic app-auth --from-literal=username=${pgUserName} --from-literal=password=${pgPassword} -n ${NAMESPACE}
```

Results:
<!-- expected_similarity=0.3 -->
```text
secret/app-auth created
```

Azure Storage에 백업하기 위한 비밀 만들기

```bash
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name ${STORAGE_ACCOUNT_NAME} --resource-group ${RG_NAME} --query "[0].value" --output tsv)
oc create secret generic azure-storage-secret --from-literal=storage-account-name=${STORAGE_ACCOUNT_NAME} --from-literal=storage-account-key=${STORAGE_ACCOUNT_KEY} --namespace ${NAMESPACE}
```

Results:
<!-- expected_similarity=0.3 -->
```text
secret/azure-storage-secret created
```

Postgres 클러스터 만들기

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

Results:
<!-- expected_similarity=0.3 -->
```text
cluster.postgresql.k8s.enterprisedb.io/cluster-arodemo created
```

## ARO Keycloak 인스턴스 만들기

OpenShift 클러스터에 Keycloak 인스턴스를 배포합니다. 명령을 `oc apply` 사용하여 Keycloak 리소스를 정의하는 YAML 구성 파일을 적용합니다.
YAML 구성은 데이터베이스, 호스트 이름, HTTP 설정, 수신, 인스턴스 수 및 트랜잭션 설정을 포함하여 Keycloak 인스턴스에 대한 다양한 설정을 지정합니다.
Keycloak을 배포하려면 필요한 권한과 OpenShift 클러스터에 대한 액세스를 사용하여 셸 환경에서 이 코드 블록을 실행합니다.
참고: 변수 `$apiServer``$kc_hosts`및 데이터베이스 자격 증명(`passwordSecret`및`usernameSecret`)의 값을 사용자 환경에 적합한 값으로 바꿔야 합니다.

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

Results:
<!-- expected_similarity=0.3 -->
```text
keycloak.k8s.keycloak.org/kc001 created
```

워크로드 액세스

```bash
URL=$(ooc get ingress kc001-ingress -o json | jq -r '.spec.rules[0].host')
curl -Iv https://$URL
```

Results:
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
