---
title: Criar um cluster PostgreSQL altamente disponível no Red Hat OpenShift do Azure
description: Este tutorial mostra como criar um cluster PostgreSQL altamente disponível no Red Hat OpenShift (ARO) do Azure usando o operador CloudNativePG
author: russd2357
ms.author: rdepina
ms.topic: article
ms.date: 04/16/2024
ms.custom: 'innovation-engine, linux-related content'
---

# Criar um cluster PostgreSQL altamente disponível no Red Hat OpenShift do Azure

## Faça logon no Azure usando a CLI

Para executar comandos no Azure usando a CLI, você precisa fazer logon. Isto é feito, muito simplesmente, através do `az login` comando:

## Verificar pré-requisitos

Em seguida, verifique os pré-requisitos. Isso pode ser feito executando os seguintes comandos:

- RedHat OpenShift: `az provider register -n Microsoft.RedHatOpenShift --wait`
- Kubectl: `az aks install-cli`
- Cliente Openshift: `mkdir ~/ocp ; wget -q https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/openshift-client-linux.tar.gz -O ~/ocp/openshift-client-linux.tar.gz ; tar -xf ~/ocp/openshift-client-linux.tar.gz ; export PATH="$PATH:~/ocp"`

## Criar um grupo de recursos

Um grupo de recursos é um contêiner para recursos relacionados. Todos os recursos devem ser colocados em um grupo de recursos. Vamos criar um para este tutorial. O comando a seguir cria um grupo de recursos com os parâmetros $RG_NAME, $LOCATION e $RGTAGS definidos anteriormente.

```bash
export RGTAGS="owner=ARO Demo"
export LOCATION="westus"
export LOCAL_NAME="arodemo"
export SUFFIX=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 6; echo)
export RG_NAME="rg-arodemo-perm"
```

## Criar VNet

Nesta seção, você criará uma Rede Virtual (VNet) no Azure. Comece definindo várias variáveis de ambiente. Essas variáveis manterão os nomes de sua VNet e sub-redes, bem como o bloco CIDR para sua VNet. Em seguida, crie a VNet com o nome especificado e o bloco CIDR em seu grupo de recursos usando o comando az network vnet create. Este processo poderá demorar alguns minutos.

```bash
export VNET_NAME="vnet-${LOCAL_NAME}-${SUFFIX}"
export SUBNET1_NAME="sn-main-${SUFFIX}"
export SUBNET2_NAME="sn-worker-${SUFFIX}"
export VNET_CIDR="10.0.0.0/22"
az network vnet create -g $RG_NAME -n $VNET_NAME --address-prefixes $VNET_CIDR
```

Resultados:

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

## Criar sub-rede de nós principais

Nesta seção, você criará a sub-rede de nós principais com o nome especificado e o bloco CIDR dentro de sua Rede Virtual (VNet) criada anteriormente. Comece executando o comando az network vnet subnet create. Este processo poderá demorar alguns minutos. Depois que a sub-rede for criada com êxito, você estará pronto para implantar recursos nessa sub-rede.

```bash
az network vnet subnet create -g $RG_NAME --vnet-name $VNET_NAME -n $SUBNET1_NAME --address-prefixes 10.0.0.0/23
```

Resultados:

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

## Criar sub-rede de nós de trabalho

Nesta seção, você criará uma sub-rede para seus nós de trabalho com o nome especificado e o bloco CIDR dentro da Rede Virtual (VNet) criada anteriormente. Comece executando o comando az network vnet subnet create. Depois que a sub-rede for criada com êxito, você estará pronto para implantar seus nós de trabalho nessa sub-rede.

```bash
az network vnet subnet create -g $RG_NAME --vnet-name $VNET_NAME -n $SUBNET2_NAME --address-prefixes 10.0.2.0/23
```

Resultados:

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

## Criar contas de armazenamento

Este trecho de código executa as seguintes etapas:

1. Define a `STORAGE_ACCOUNT_NAME` variável de ambiente como uma concatenação de `stor`, `LOCAL_NAME` (convertido em minúsculas) e `SUFFIX` (convertido em minúsculas).
2. Define a `BARMAN_CONTAINER_NAME` variável de ambiente como `"barman"`.
3. Cria uma conta de armazenamento com o especificado `STORAGE_ACCOUNT_NAME` no grupo de recursos especificado.
4. Cria um contêiner de armazenamento com o especificado `BARMAN_CONTAINER_NAME` na conta de armazenamento criada.

```bash
export STORAGE_ACCOUNT_NAME="stor${LOCAL_NAME,,}${SUFFIX,,}"
export BARMAN_CONTAINER_NAME="barman"

az storage account create --name "${STORAGE_ACCOUNT_NAME}" --resource-group "${RG_NAME}" --sku Standard_LRS
az storage container create --name "${BARMAN_CONTAINER_NAME}" --account-name "${STORAGE_ACCOUNT_NAME}"
```

## Implantar o cluster ARO

Nesta seção, você implantará um cluster do Azure Red Hat OpenShift (ARO). A variável ARO_CLUSTER_NAME manterá o nome do cluster ARO. O comando az aro create implantará o cluster ARO com o nome especificado, o grupo de recursos, a rede virtual, as sub-redes e o segredo de pull do RedHat OpenShift que você baixou e salvou anteriormente no Cofre da Chave. Este processo pode levar cerca de 30 minutos para ser concluído.

```bash
export ARO_CLUSTER_NAME="aro-${LOCAL_NAME}-${SUFFIX}"
export ARO_PULL_SECRET=$(az keyvault secret show --name AroPullSecret --vault-name kv-rdp-dev --query value -o tsv)
export ARO_SP_ID=$(az keyvault secret show --name arodemo-sp-id --vault-name kv-rdp-dev --query value -o tsv)
export ARO_SP_PASSWORD=$(az keyvault secret show --name arodemo-sp-password --vault-name kv-rdp-dev --query value -o tsv)
echo "This will take about 30 minutes to complete..." 
az aro create -g $RG_NAME -n $ARO_CLUSTER_NAME --vnet $VNET_NAME --master-subnet $SUBNET1_NAME --worker-subnet $SUBNET2_NAME --tags $RGTAGS --pull-secret ${ARO_PULL_SECRET} --client-id ${ARO_SP_ID} --client-secret ${ARO_SP_PASSWORD}
```

Resultados:
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

## Obter credenciais de cluster e login

Esse código recupera a URL do servidor de API e as credenciais de logon para um cluster do Azure Red Hat OpenShift (ARO) usando a CLI do Azure.

O `az aro show` comando é usado para obter a URL do servidor de API fornecendo o nome do grupo de recursos e o nome do cluster ARO. O `--query` parâmetro é usado para extrair a `apiserverProfile.url` propriedade e a `-o tsv` opção é usada para gerar o resultado como um valor separado por tabulações.

O `az aro list-credentials` comando é usado para obter as credenciais de login para o cluster ARO. O `--name` parâmetro especifica o nome do cluster ARO e o `--resource-group` parâmetro especifica o nome do grupo de recursos. O `--query` parâmetro é usado para extrair a `kubeadminPassword` propriedade e a `-o tsv` opção é usada para gerar o resultado como um valor separado por tabulações.

Finalmente, o `oc login` comando é usado para efetuar login no cluster ARO usando a URL do servidor de API recuperada, o nome de `kubeadmin` usuário e as credenciais de login.

```bash
export apiServer=$(az aro show -g $RG_NAME -n $ARO_CLUSTER_NAME --query apiserverProfile.url -o tsv)
export loginCred=$(az aro list-credentials --name $ARO_CLUSTER_NAME --resource-group $RG_NAME --query "kubeadminPassword" -o tsv)

oc login $apiServer -u kubeadmin -p $loginCred --insecure-skip-tls-verify
```

## Adicionar operadores ao ARO

Defina o namespace para instalar os operadores no namespace `openshift-operators`interno.

```bash
export NAMESPACE="openshift-operators"
```

Operador Cloud Native Postgresql

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

Operador RedHat Keycloak

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

Resultados:
<!-- expected_similarity=0.3 -->
```text
subscription.operators.coreos.com/rhbk-operator created
```

## Criar o banco de dados ARO PosgreSQL

Buscar segredos do Cofre da Chave e criar o objeto secreto de login do banco de dados ARO.

```bash
pgUserName=$(az keyvault secret show --name AroPGUser --vault-name kv-rdp-dev --query value -o tsv)
pgPassword=$(az keyvault secret show --name AroPGPassword --vault-name kv-rdp-dev --query value -o tsv)

oc create secret generic app-auth --from-literal=username=${pgUserName} --from-literal=password=${pgPassword} -n ${NAMESPACE}
```

Resultados:
<!-- expected_similarity=0.3 -->
```text
secret/app-auth created
```

Criar o segredo para fazer backup no Armazenamento do Azure

```bash
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name ${STORAGE_ACCOUNT_NAME} --resource-group ${RG_NAME} --query "[0].value" --output tsv)
oc create secret generic azure-storage-secret --from-literal=storage-account-name=${STORAGE_ACCOUNT_NAME} --from-literal=storage-account-key=${STORAGE_ACCOUNT_KEY} --namespace ${NAMESPACE}
```

Resultados:
<!-- expected_similarity=0.3 -->
```text
secret/azure-storage-secret created
```

Criar o cluster Postgres

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

Resultados:
<!-- expected_similarity=0.3 -->
```text
cluster.postgresql.k8s.enterprisedb.io/cluster-arodemo created
```

## Criar a instância do ARO Keycloak

Implante uma instância do Keycloak em um cluster OpenShift. Ele usa o `oc apply` comando para aplicar um arquivo de configuração YAML que define o recurso Keycloak.
A configuração YAML especifica várias configurações para a instância Keycloak, incluindo o banco de dados, nome do host, configurações HTTP, entrada, número de instâncias e configurações de transação.
Para implantar o Keycloak, execute este bloco de código em um ambiente de shell com as permissões necessárias e acesso ao cluster OpenShift.
Nota: Certifique-se de substituir os valores das variáveis `$apiServer`, `$kc_hosts`e as credenciais do banco de dados (`passwordSecret` e `usernameSecret`) pelos valores apropriados para seu ambiente.

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

Resultados:
<!-- expected_similarity=0.3 -->
```text
keycloak.k8s.keycloak.org/kc001 created
```

Acesse a carga de trabalho

```bash
URL=$(ooc get ingress kc001-ingress -o json | jq -r '.spec.rules[0].host')
curl -Iv https://$URL
```

Resultados:
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
