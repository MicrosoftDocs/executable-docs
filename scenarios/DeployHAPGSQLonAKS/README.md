---
title: Create a Highly Available PostgreSQL Cluster on Azure Kubernetes Service
description: This tutorial shows how to create a Highly Available PostgreSQL cluster on Azure Kubernetes Service (AKS) using the CloudNativePG operator
author: russd2357
ms.author: rdepina
ms.topic: article
ms.date: 03/19/2024
ms.custom: innovation-engine, linux-related content
---

# Create a Highly Available PostgreSQL Cluster on Azure Kubernetes Service

## Define Environment Variables

The First step in this tutorial is to define environment variables.

```bash
export ERROR=$(tput setaf 1)
export OUTPUT=$(tput setaf 2)
export NC=$(tput sgr0) 
export LOCAL_NAME="cnpg"
export RGTAGS="owner=cnpg"
export LOCATION="eastus"
export CLUSTER_VERSION="1.27"
export AKS_NODE_COUNT=2
export SUFFIX=$(tr -dc a-z0-9 </dev/urandom | head -c 6; echo)
export RG_NAME="rg-${LOCAL_NAME}-${SUFFIX}"
export AKS_MANAGED_IDENTITY_NAME="mi-aks-${LOCAL_NAME}-${SUFFIX}"
export AKS_CLUSTER_NAME="aks-${LOCAL_NAME}-${SUFFIX}"
export STORAGE_ACCOUNT_NAME="stor${LOCAL_NAME}${SUFFIX}"
export KEYVAULT_NAME="kv-${LOCAL_NAME}-${SUFFIX}"
export BARMAN_CONTAINER_NAME="barman"
```

## Login to Azure using the CLI

In order to run commands against Azure using the CLI you need to login. This is done, very simply, though the `az login` command:

## Check for Prerequisites

Next, check for prerequisites. This section checks for the following prerequisites: aks-preview extension, helm, and kubectl. It also checks if the NodeAutoProvisioningPreview feature is already enabled. If not, it registers the feature flag, waits for the feature registration to complete, and refreshes the registration of the Microsoft.ContainerService resource provider until the feature is registered.

### AKS-Preview Extension

```bash
echo ${OUTPUT} "Checking if aks-preview extension is installed..." ${NC}
if ! az extension show --name aks-preview &> /dev/null; then
  az extension add --name aks-preview 
fi
```

### NodeAutoProvisioningPreview Feature

```bash
if ! az feature show --namespace "Microsoft.ContainerService" --name "NodeAutoProvisioningPreview" --subscription "$SUBSCRIPTION_ID" --query "properties.state" --output tsv | grep -wq "Registered"; then
    az feature register --namespace "Microsoft.ContainerService" --name "NodeAutoProvisioningPreview"
    status=""
    timeout=60
    start_time=$(date +%s)
    while true; do
        current_time=$(date +%s)
        elapsed_time=$((current_time - start_time))
        if [ $elapsed_time -ge $timeout ]; then
            echo "Unable to register NodeAutoProvisioningPreview feature. Exiting..."
        fi
        status=$(az feature show --namespace "Microsoft.ContainerService" --name "NodeAutoProvisioningPreview" --subscription "$SUBSCRIPTION_ID" --query "properties.state" --output tsv | tr '[=upper=]' '[=lower=]')
        if [ "$(echo "$status" | tr '[=upper=]' '[=lower=]')" = "registered" ]; then
            break
        else
            sleep 5
        fi
    done
    az feature register --namespace "Microsoft.ContainerService" --name "NodeAutoProvisioningPreview"
fi
```

### Helm

```bash
if ! command -v helm &> /dev/null; then
    curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3
    chmod 700 get_helm.sh
    ./get_helm.sh
fi
```

### Kubectl

```bash
if ! command -v kubectl &> /dev/null; then
    az aks install-cli
fi
```

## Create a Resource Group

A resource group is a container for related resources. All resources must be placed in a resource group. We will create one for this tutorial. The following command creates a resource group with the previously defined $RG_NAME and $LOCATION parameters.

```bash
export RG_NAME="rg-${LOCAL_NAME}-${SUFFIX}"
if ! az group show -n $RG_NAME &> /dev/null; then
    az group create -n $RG_NAME -l $LOCATION --tags $RGTAGS
fi
```

Results:

<!-- expected_similarity=0.3 -->
```json   
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMResourceGroup",
  "location": "eastus",
  "managedBy": null,
  "name": "myVMResourceGroup",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Create an Azure Storage Account and Container for Postgres Backups

In this part of the process, you'll be creating an Azure Storage Account and a container for Postgres backups. 

Start by creating a storage account. Here, the az storage account create command is used. You'll need to provide the name of the storage account, the resource group it belongs to, the location (region) where it should be created, and the type of storage account you want to create. In this case, a Standard_LRS (Locally redundant storage) account is created.

If the storage account is created successfully, you'll see a message indicating "Storage account created." If the storage account already exists, you'll see a message stating "Storage account already exists."

This storage account will be used for backing up your Postgres database in this deployment.

```bash
if ! az storage account show --name "${STORAGE_ACCOUNT_NAME}" --resource-group "${RG_NAME}" &> /dev/null; then
    az storage account create --name "${STORAGE_ACCOUNT_NAME}" --resource-group "${RG_NAME}" --location "${LOCATION}" --sku Standard_LRS
fi
```

Results:

<!-- expected_similarity=0.3 -->
```json   
{
  "accessTier": "Hot",
  "accountMigrationInProgress": null,
  "allowBlobPublicAccess": false,
  "allowCrossTenantReplication": false,
  "allowSharedKeyAccess": null,
  "allowedCopyScope": null,
  "azureFilesIdentityBasedAuthentication": null,
  "blobRestoreStatus": null,
  "creationTime": "xxxx-xx-xxxx:xx:xx.xxxxx+xx:xx",
  "customDomain": null,
  "defaultToOAuthAuthentication": null,
  "dnsEndpointType": null,
  "enableHttpsTrafficOnly": true,
  "enableNfsV3": null,
  "encryption": {
    "encryptionIdentity": null,
    "keySource": "Microsoft.Storage",
    "keyVaultProperties": null,
    "requireInfrastructureEncryption": null,
    "services": {
      "blob": {
        "enabled": true,
        "keyType": "Account",
        "lastEnabledTime": "xxxx-xx-xxxx:xx:xx.xxxxx+xx:xx"
      },
      "file": {
        "enabled": true,
        "keyType": "Account",
        "lastEnabledTime": "xxxx-xx-xxxx:xx:xx.xxxxx+xx:xx"
      },
      "queue": null,
      "table": null
    }
  },
  "extendedLocation": null,
  "failoverInProgress": null,
  "geoReplicationStats": null,
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/xx-xxxx-xxxx/providers/Microsoft.Storage/storageAccounts/xxxxxxxxxx",
  "identity": null,
  "immutableStorageWithVersioning": null,
  "isHnsEnabled": null,
  "isLocalUserEnabled": null,
  "isSftpEnabled": null,
  "isSkuConversionBlocked": null,
  "keyCreationTime": {
    "key1": "xxxx-xx-xxxx:xx:xx.xxxxx+xx:xx",
    "key2": "xxxx-xx-xxxx:xx:xx.xxxxx+xx:xx"
  },
  "keyPolicy": null,
  "kind": "StorageV2",
  "largeFileSharesState": null,
  "lastGeoFailoverTime": null,
  "location": "eastus",
  "minimumTlsVersion": "TLS1_0",
  "name": "xxxxxxxxxx",
  "networkRuleSet": {
    "bypass": "AzureServices",
    "defaultAction": "Allow",
    "ipRules": [],
    "ipv6Rules": [],
    "resourceAccessRules": null,
    "virtualNetworkRules": []
  },
  "primaryEndpoints": {
    "blob": "https://storcnpgdfpu2m.blob.core.windows.net/",
    "dfs": "https://storcnpgdfpu2m.dfs.core.windows.net/",
    "file": "https://storcnpgdfpu2m.file.core.windows.net/",
    "internetEndpoints": null,
    "microsoftEndpoints": null,
    "queue": "https://storcnpgdfpu2m.queue.core.windows.net/",
    "table": "https://storcnpgdfpu2m.table.core.windows.net/",
    "web": "https://storcnpgdfpu2m.z22.web.core.windows.net/"
  },
  "primaryLocation": "eastus",
  "privateEndpointConnections": [],
  "provisioningState": "Succeeded",
  "publicNetworkAccess": null,
  "resourceGroup": "xxxxxxxxxx",
  "routingPreference": null,
  "sasPolicy": null,
  "secondaryEndpoints": null,
  "secondaryLocation": null,
  "sku": {
    "name": "Standard_LRS",
    "tier": "Standard"
  },
  "statusOfPrimary": "available",
  "statusOfSecondary": null,
  "storageAccountSkuConversionStatus": null,
  "tags": {},
  "type": "Microsoft.Storage/storageAccounts"
}
```

Next, you'll be creating a container in your Azure Storage Account specifically for Postgres backups. This is done using the az storage container create command. You'll need to provide the name of the container and the name of the storage account it belongs to.

```bash
if ! az storage container show --name "${BARMAN_CONTAINER_NAME}" --account-name "${STORAGE_ACCOUNT_NAME}" &> /dev/null; then
    az storage container create --name "${BARMAN_CONTAINER_NAME}" --account-name "${STORAGE_ACCOUNT_NAME}"
fi
```

Results:

<!-- expected_similarity=0.3 -->
```json   
{
  "created": true
}
```

## Create AKS Cluster

The next step is to create an Azure Kubernetes Service (AKS) cluster. This is done using the az aks create command. In the first phase, you'll need to check if the user assigned managed identity for the AKS cluster exists. If not, you'll create the managed identity. Next, you'll create the AKS cluster. This is done using the az aks create command. You'll need to provide the name of the AKS cluster, the resource group it belongs to, the number of nodes in the cluster, and the name of the user assigned managed identity for the AKS cluster.

```bash
managedIdentity=$(az identity create --name "${AKS_MANAGED_IDENTITY_NAME}" --resource-group "${RG_NAME}")
managedIdentityObjectId=$(echo "${managedIdentity}" | jq -r '.principalId')
managedIdentityResourceId=$(echo "${managedIdentity}" | jq -r '.id')
if ! az aks show --name "${AKS_CLUSTER_NAME}" --resource-group "${RG_NAME}" &> /dev/null; then
    az aks create --tags "$RGTAGS" --name "${AKS_CLUSTER_NAME}" --resource-group "${RG_NAME}" --enable-keda --enable-managed-identity --assign-identity $managedIdentityResourceId --node-provisioning-mode Auto --network-plugin azure --network-plugin-mode overlay --network-dataplane cilium --nodepool-taints CriticalAddonsOnly=true:NoSchedule --node-count "$AKS_NODE_COUNT" --enable-oidc-issuer --generate-ssh-keys
fi
```

Results:

<!-- expected_similarity=0.3 -->
```json  
{
  "aadProfile": null,
  "addonProfiles": {
    "KubeDashboard": {
      "config": null,
      "enabled": false
    },
    "azurepolicy": {
      "config": null,
      "enabled": false
    }
  },
  "agentPoolProfiles": [
    {
      "availabilityZones": null,
      "count": 3,
      "enableAutoScaling": null,
      "enableNodePublicIp": false,
      "maxCount": null,
      "maxPods": 110,
      "minCount": null,
      "mode": "System",
      "name": "nodepool1",
      "nodeImageVersion": "AKSUbuntu-1804gen2containerd-2021.09.22",
      "nodeLabels": {},
      "nodeTaints": null,
      "orchestratorVersion": "1.20.7",
      "osDiskSizeGb": 128,
      "osDiskType": "Managed",
      "osType": "Linux",
      "provisioningState": "Succeeded",
      "scaleSetEvictionPolicy": null,
      "scaleSetPriority": null,
      "spotMaxPrice": null,
      "tags": null,
      "type": "VirtualMachineScaleSets",
      "vmSize": "Standard_D2s_v3"
    }
  ],
  "apiServerAccessProfile": null,
  "autoScalerProfile": null,
  "autoUpgradeProfile": null,
  "azurePortalFQDN": "xxxxxxxxxx-xxxxxxx.xxx.xxxxxx.xxxxx.xx",
  "diskEncryptionSetId": null,
  "dnsPrefix": "xxxxxxxxxx",
  "enablePodSecurityPolicy": null,
  "enableRbac": true,
  "fqdn": "xxxxxxxxxx-xxxxxxx.xxx.xxxxxx.xxxxx.xx",
  "id": "/subscriptions/xxxxxxxxxx-xx-xxxx-xxx-xxx/resourcegroups/myResourceGroup/providers/Microsoft.ContainerService/managedClusters/xxxxxxxxxx",
  "identity": null,
  "kubernetesVersion": "1.20.7",
  "linuxProfile": null,
  "location": "eastus",
  "maxAgentPools": 100,
  "name": "xxxxxxxxxx",
  "networkProfile": {
    "dnsServiceIp": "xx.x.x.xx",
    "dockerBridgeCidr": "xxx.xx.x.x/xx",
    "loadBalancerProfile": null,
    "networkMode": null,
    "networkPlugin": "kubenet",
    "networkPolicy": null,
    "outboundType": "loadBalancer",
    "podCidr": "xx.xxx.x.x/xx",
    "serviceCidr": "xx.xxx.x.x/xx"
  },
  "nodeResourceGroup": "MC_xxxxxxxxxx_xxxxxxxxxx_eastus",
  "powerState": {
    "code": "Running"
  },
  "privateFqdn": null,
  "provisioningState": "Succeeded",
  "resourceGroup": "xxxxxxxxxx",
  "servicePrincipalProfile": null,
  "sku": {
    "name": "Basic",
    "tier": "Free"
  },
  "tags": {
    "Environment": "Production"
  },
  "type": "Microsoft.ContainerService/ManagedClusters",
  "windowsProfile": null
}
```

By this point the cluster should be up and running. This step ensures that by getting access credentials for the cluster.

```bash
az aks get-credentials --name ${AKS_CLUSTER_NAME} --resource-group ${RG_NAME}
```

## Install the Postgres Cluster

The next step is to install the Postgres Cluster. This is done using the CloudNativePG operator. The CloudNativePG operator is a Kubernetes operator that manages PostgreSQL clusters. It is designed to be cloud-native and to provide a high level of automation for managing PostgreSQL clusters. The CloudNativePG operator is installed using the kubectl apply command.

### Install the CloudNativePG Operator

First, install the CloudNativePG operator on the AKS cluster.

```bash
kubectl apply -f https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/main/releases/cnpg-1.22.0.yaml
```

### Enable Expanding Volumes for AKS

Next, update the configuration of the CloudNativePG operator to enable expanding volumes for AKS.

```bash
kubectl apply -f az-expanding-vols.yaml
```

```bash
kubectl rollout restart deployment -n cnpg-system cnpg-controller-manager
```

### Create the Storage Class for the Postgres Deployment

Next, create the storage class for the Postgres deployment.

```bash
kubectl apply -f std-storageclass.yaml
```

### Create the Namespace and Secrets for the Postgres Deployment

Next, create the namespace and secrets for the Postgres deployment.

```bash
kubectl create -f auth-prod.yaml
```

Finally, create the Postgres cluster.

```bash
STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name ${STORAGE_ACCOUNT_NAME} --resource-group ${RG_NAME} --query "[0].value" --output tsv)
cat  <<EOF | kubectl apply -f -
---
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: prod
  namespace: demo
spec:
  description: "Cluster Demo for DoEKS"
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
  # serviceAccountTemplate:
  #   metadata:
  #     annotations:
  #       eks.amazonaws.com/role-arn: arn:aws:iam::<<account_id>>:role/cnpg-on-eks-prod-irsa
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
    storageClass: storageclass-io2
    size: 1Gi
  walStorage:
    storageClass: storageclass-io2
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
    # We retrieved the storage account key previously so we don't need to save secrets anywhere.
      destinationPath: https://${STORAGE_ACCOUNT_NAME}.blob.core.windows.net/${BARMAN_CONTAINER_NAME}/
      azureCredentials:
        storageAccount:
          name: recovery-object-store-secret
          key: ${STORAGE_ACCOUNT_NAME}
        storageKey:
          name: recovery-object-store-secret
          key: ${STORAGE_ACCOUNT_KEY}
      wal:
        compression: gzip
        maxParallel: 8
    retentionPolicy: "30d"
  affinity:
    enablePodAntiAffinity: true
    topologyKey: kubernetes.io/hostname
    pointAntiAffinityType: preferred
 
  nodeMaintenanceWindow:
    inProgress: false
    reusePVC: false
EOF
```
