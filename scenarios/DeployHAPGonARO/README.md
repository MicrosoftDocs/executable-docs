---
title: Create a Highly Available PostgreSQL Cluster on Azure Red Hat OpenShift
description: This tutorial shows how to create a Highly Available PostgreSQL cluster on Azure Red Hat OpenShift (ARO) using the CloudNativePG operator
author: russd2357
ms.author: rdepina
ms.topic: article
ms.date: 04/02/2024
ms.custom: innovation-engine, linux-related content
---

# Create a Highly Available PostgreSQL Cluster on Azure Red Hat OpenShift

## Login to Azure using the CLI

In order to run commands against Azure using the CLI you need to login. This is done, very simply, though the `az login` command:

## Check for Prerequisites

Next, check for prerequisites. This section checks for the following prerequisites: RedHat OpenShift and kubectl.

### RedHat OpenShift

```bash
az provider register -n Microsoft.RedHatOpenShift --wait
```

### Kubectl

```bash
az aks install-cli
```

### Openshift Client

Install the Openshift client locally.

```bash
mkdir ~/ocp
wget -q https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/openshift-client-linux.tar.gz -O ~/ocp/openshift-client-linux.tar.gz
tar -xf ~/ocp/openshift-client-linux.tar.gz
export PATH="$PATH:~/ocp"
```

## Create a resource group

A resource group is a container for related resources. All resources must be placed in a resource group. We will create one for this tutorial. The following command creates a resource group with the previously defined $RG_NAME, $LOCATION, and $RGTAGS parameters.

```bash
export RGTAGS="owner=ARO Demo"
export LOCATION="westus"
export LOCAL_NAME="arodemo"
export SUFFIX=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 6; echo)
export RG_NAME="rg-${LOCAL_NAME}-${SUFFIX}"
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

## Create VNet

In this section, you'll be creating a Virtual Network (VNet) in Azure. Start by defining several environment variables. These variables will hold the names of your VNet and subnets, as well as the CIDR block for your VNet. Next, create the VNet  with the specified name and CIDR block in your resource group using the az network vnet create command. This process may take a few minutes.

```bash
export VNET_NAME="vnet-${LOCAL_NAME}-${SUFFIX}"
export SUBNET1_NAME="sn-main-${SUFFIX}"
export SUBNET2_NAME="sn-worker-${SUFFIX}"
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

## Create Main Nodes Subnet

In this section, you'll be creating the main nodes subnet with the specified name and CIDR block within your previously created Virtual Network (VNet). Start by running the az network vnet subnet create command. This process may take a few minutes. After the subnet is successfully created, you'll be ready to deploy resources into this subnet.

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

## Create Worker Nodes Subnet

In this section, you'll be creating a subnet for your worker nodes with the specified name and CIDR block within your previously created Virtual Network (VNet). Start by running the az network vnet subnet create command. After the subnet is successfully created, you'll be ready to deploy your worker nodes into this subnet.

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

## Create a service principal for the ARO cluster

In this section, you'll be creating a service principal for your Azure Red Hat OpenShift (ARO) cluster. The SP_NAME variable will hold the name of your service principal. The SUBSCRIPTION_ID variable, which can be retrieved using the az account show command, will store your Azure subscription ID. This ID is necessary for assigning roles to your service principal. After that, create the service principal using the az ad sp create-for-rbac command. Finally, extract the service principal's ID and secret from the servicePrincipalInfo variable, output as a JSON object. These values will be used later to authenticate your ARO cluster with Azure.

```bash
export SP_NAME="sp-aro-${LOCAL_NAME}-${SUFFIX}"
export SUBSCRIPTION_ID=$(az account show --query id --output tsv)
servicePrincipalInfo=$(az ad sp create-for-rbac -n $SP_NAME --role Contributor --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RG_NAME --output json)
SP_ID=$(echo $servicePrincipalInfo | jq -r '.appId')
SP_SECRET=$(echo $servicePrincipalInfo | jq -r '.password')
```

## Deploy the ARO cluster

In this section, you'll be deploying an Azure Red Hat OpenShift (ARO) cluster. The ARO_CLUSTER_NAME variable will hold the name of your ARO cluster. The az aro create command will deploy the ARO cluster with the specified name, resource group, virtual network, subnets, and service principal. This process may take about 30 minutes to complete.

```bash
export ARO_CLUSTER_NAME="aro-${LOCAL_NAME}-${SUFFIX}"
echo "This will take about 30 minutes to complete..." 
az aro create -g $RG_NAME -n $ARO_CLUSTER_NAME --vnet $VNET_NAME --master-subnet $SUBNET1_NAME --worker-subnet $SUBNET2_NAME --tags $RGTAGS --client-id ${SP_ID} --client-secret ${SP_SECRET}
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

## Obtain cluster credentials and login

This code retrieves the API server URL and login credentials for an Azure Red Hat OpenShift (ARO) cluster using the Azure CLI.

The `az aro show` command is used to get the API server URL by providing the resource group name and ARO cluster name. The `--query` parameter is used to extract the `apiserverProfile.url` property, and the `-o tsv` option is used to output the result as a tab-separated value.

The `az aro list-credentials` command is used to get the login credentials for the ARO cluster. The `--name` parameter specifies the ARO cluster name, and the `--resource-group` parameter specifies the resource group name. The `--query` parameter is used to extract the `kubeadminPassword` property, and the `-o tsv` option is used to output the result as a tab-separated value.

Finally, the `oc login` command is used to log in to the ARO cluster using the retrieved API server URL, the `kubeadmin` username, and the login credentials.

```bash
apiServer=$(az aro show -g $RG_NAME -n $ARO_CLUSTER_NAME --query apiserverProfile.url -o tsv)
loginCred=$(az aro list-credentials --name $ARO_CLUSTER_NAME --resource-group $RG_NAME --query "kubeadminPassword" -o tsv)

oc login $apiServer -u kubeadmin -p $loginCred
```

## Deploy the CMS workload

The code block below sets environment variables for deploying a High Availability PostgreSQL (HAPG) on Azure Red Hat OpenShift (ARO). Here's a breakdown of the variables being set:

- `PGSQL_DB_NAME`: A randomly generated name for the PostgreSQL database.
- `PGSQL_ADMIN_USERNAME`: A randomly generated username for the PostgreSQL admin.
- `PGSQL_ADMIN_PW`: A randomly generated password for the PostgreSQL admin.
- `PGSQL_SN_NAME`: A randomly generated name for the PostgreSQL server name.
- `PGSQL_HOSTNAME`: The hostname for the PostgreSQL database, constructed using the `PGSQL_DB_NAME` variable.

```bash
export PGSQL_DB_NAME="pgsqldb$SUFFIX"
export PGSQL_ADMIN_USERNAME="dbadmin$SUFFIX"
export PGSQL_ADMIN_PW="$(openssl rand -base64 32)"
export PGSQL_HOSTNAME="$PGSQL_DB_NAME.PGSQL.database.azure.com"
```

1. Create ARO project

    ```bash
    oc new-project cms-demo
    ```

2. Deploy PostgreSQL

    ```bash
    kubectl create -n cms-demo secret generic cms-creds --from-literal=postgres-password=$PGSQL_ADMIN_PW
    ```

## Install your CMS to ARO cluster

For this tutorial, we're using an existing Helm chart for Drupal built by Bitnami. The Bitnami Helm chart uses a local MariaDB as the database, so we need to override these values to use the app with an external PostgreSQL DB.

1. Add the Wordpress Bitnami Helm repository.

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. Update local Helm chart repository cache.

    ```bash
    helm repo update
    ```

3. Install Wordpress workload via Helm.

    ```bash
    helm upgrade --install --cleanup-on-fail \
        --wait --timeout 10m0s \
        --namespace cms-demo \
        --create-namespace \
        --set externalDatabase.host="$PGSQL_HOSTNAME" \
        --set externalDatabase.user="$PGSQL_ADMIN_USERNAME" \
        --set externalDatabase.password="$PGSQL_ADMIN_PW" \
        --set externalDatabase.database="$PGSQL_DB_NAME" \
        --set externalDatabase.port=5432
        drupal bitnami/drupal
    ```

    Results:
    <!-- expected_similarity=0.3 -->
    ```text
    Release "drupal" does not exist. Installing it now.
    NAME: drupal
    LAST DEPLOYED: Fri Apr 12 19:23:50 2024
    NAMESPACE: demo
    STATUS: deployed
    REVISION: 1
    TEST SUITE: None
    NOTES:
    CHART NAME: drupal
    CHART VERSION: 18.0.2
    APP VERSION: 10.2.5** Please be patient while the chart is being deployed **
    
    1. Get the Drupal URL:
    
      NOTE: It may take a few minutes for the LoadBalancer IP to be available.
            Watch the status with: 'kubectl get svc --namespace demo -w drupal'
    
      export SERVICE_IP=$(kubectl get svc --namespace demo drupal --template "{{ range (index .status.loadBalancer.ingress 0) }}{{ . }}{{ end }}")
      echo "Drupal URL: http://$SERVICE_IP/"
    
    2. Get your Drupal login credentials by running:
    
      echo Username: user
      echo Password: $(kubectl get secret --namespace demo drupal -o jsonpath="{.data.drupal-password}" | base64 -d)
    ```

4. Expose the CMS workload

    ```bash
    oc create route edge --service=drupal
    ```

5. Access the workload

    ```bash
    curl -Iv https://drupal-cms-demo.$SUFFIX.westus.aroapp.io
    ```
