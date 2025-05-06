---
title: 'Configure and deploy a MongoDB cluster on Azure Kubernetes Service (AKS)'
description: In this article, you configure and deploy a MongoDB cluster on AKS.
ms.topic: how-to
ms.date: 01/07/2025
author: fossygirl
ms.author: carols
ms.custom: aks-related-content
zone_pivot_groups: azure-cli-or-terraform
---

# Configure and deploy a MongoDB cluster on Azure Kubernetes Service (AKS)

In this article, you configure and deploy a MongoDB cluster on Azure Kubernetes Service (AKS).

## Configure a workload identity

1. Create a namespace for the MongoDB cluster using the `kubectl create namespace` command.

    ```bash
    kubectl create namespace ${AKS_MONGODB_NAMESPACE} --dry-run=client --output yaml | kubectl apply -f -
    ```

    Example output:

    <!-- expected_similarity=0.8 -->
    ```output
    namespace/mongodb created
    ```

2. Create a service account and configure a workload identity using the `kubectl apply` command.

    ```bash
    export TENANT_ID=$(az account show --query tenantId -o tsv)
    cat <<EOF | kubectl apply -f -
    apiVersion: v1
    kind: ServiceAccount
    metadata:
      annotations:
        azure.workload.identity/client-id: "${MY_IDENTITY_NAME_CLIENT_ID}"
        azure.workload.identity/tenant-id: "${TENANT_ID}"
      name: "${SERVICE_ACCOUNT_NAME}"
      namespace: "${AKS_MONGODB_NAMESPACE}"
    EOF
    ```

    Example output:

    <!-- expected_similarity=0.8 -->
     ```output
    serviceaccount/mongodb created
    ```

## Install External Secrets Operator

In this section, you use Helm to install External Secrets Operator. External Secrets Operator is a Kubernetes operator that manages the life cycle of external secrets stored in external secret stores like Azure Key Vault.

1. Add the External Secrets Helm repository and update the repository using the `helm repo add` and `helm repo update` commands.

    ```bash
    helm repo add external-secrets https://charts.external-secrets.io
    helm repo update
    ```

    Example output:

    <!-- expected_similarity=0.1 -->
    ```output
    Hang tight while we grab the latest from your chart repositories...
    ...Successfully got an update from the "external-secrets" chart repository
    ```

2. Install External Secrets Operator using the `helm install` command.

    ```bash
    helm install external-secrets \
    external-secrets/external-secrets \
    --namespace ${AKS_MONGODB_NAMESPACE} \
    --create-namespace \
    --set installCRDs=true \
    --wait \
    --set nodeSelector."kubernetes\.azure\.com/agentpool"=mongodbpool
    ```

    Example output:
  
    <!-- expected_similarity=0.8 -->
    ```output
    NAME: external-secrets
    LAST DEPLOYED: Tue Jun 11 11:55:32 2024
    NAMESPACE: mongodb
    STATUS: deployed
    REVISION: 1
    TEST SUITE: None
    NOTES:
    external-secrets has been deployed successfully in namespace mongodb!
    
    In order to begin using ExternalSecrets, you will need to set up a SecretStore
    or ClusterSecretStore resource (for example, by creating a 'vault' SecretStore).
    
    More information on the different types of SecretStores and how to configure them
    can be found in our Github: https://github.com/external-secrets/external-secrets
    ```
3. Generate a random password using the below function:

    ```bash
    #MongoDB connection strings can contain special characters in the password, which need to be URL encoded. 
    #This is because the connection string is a URI, and special characters can interfere with the URI structure.
    #This function generates secrets of 32 characters using only alphanumeric characters.

    generateRandomPasswordString() {
        cat /dev/urandom | LC_ALL=C tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1
    }
    ```
## Create MongoDB secrets

:::zone pivot="azure-cli"

1. Create a MongoDB [backup user and password](https://www.mongodb.com/docs/manual/reference/built-in-roles/#backup-and-restoration-roles) secret to use for any backup and restore operations using the [`az keyvault secret set`](/cli/azure/keyvault/secret#az-keyvault-secret-set) command.

    ```azurecli-interactive
    az keyvault secret set --vault-name $MY_KEYVAULT_NAME --name MONGODB-BACKUP-USER --value MONGODB_BACKUP_USER --output none
    az keyvault secret set --vault-name $MY_KEYVAULT_NAME --name MONGODB-BACKUP-PASSWORD --value $(generateRandomPasswordString) --output none
    ```

2. Create a MongoDB [database admin user and password](https://www.mongodb.com/docs/manual/reference/built-in-roles/#all-database-roles) secret for database administration using the [`az keyvault secret set`](/cli/azure/keyvault/secret#az-keyvault-secret-set) command.

    ```azurecli-interactive
    az keyvault secret set --vault-name $MY_KEYVAULT_NAME --name MONGODB-DATABASE-ADMIN-USER --value MONGODB_DATABASE_ADMIN_USER --output none
    az keyvault secret set --vault-name $MY_KEYVAULT_NAME --name MONGODB-DATABASE-ADMIN-PASSWORD --value $(generateRandomPasswordString) --output none
    ```

3. Create a MongoDB [cluster administration user and admin](https://www.mongodb.com/docs/manual/reference/built-in-roles/#mongodb-authrole-clusterAdmin) secret for a cluster administration role that provides administration for more than one database using the [`az keyvault secret set`](/cli/azure/keyvault/secret#az-keyvault-secret-set) command.

    ```azurecli-interactive
    az keyvault secret set --vault-name $MY_KEYVAULT_NAME --name MONGODB-CLUSTER-ADMIN-USER --value MONGODB_CLUSTER_ADMIN_USER --output none
    az keyvault secret set --vault-name $MY_KEYVAULT_NAME --name MONGODB-CLUSTER-ADMIN-PASSWORD --value $(generateRandomPasswordString) --output none
    ```

4. Create a MongoDB [cluster monitoring user and admin](https://www.mongodb.com/docs/manual/reference/built-in-roles/#mongodb-authrole-clusterMonitor) secret for cluster monitoring using the [`az keyvault secret set`](/cli/azure/keyvault/secret#az-keyvault-secret-set) command.

    ```azurecli-interactive
    az keyvault secret set --vault-name $MY_KEYVAULT_NAME --name MONGODB-CLUSTER-MONITOR-USER --value MONGODB_CLUSTER_MONITOR_USER --output none
    az keyvault secret set --vault-name $MY_KEYVAULT_NAME --name MONGODB-CLUSTER-MONITOR-PASSWORD --value $(generateRandomPasswordString) --output none
    ```

5. Create a user and password secret for [user administration](https://www.mongodb.com/docs/manual/reference/built-in-roles/#mongodb-authrole-userAdminAnyDatabase) using the [`az keyvault secret set`](/cli/azure/keyvault/secret#az-keyvault-secret-set) command.

    ```azurecli-interactive
    az keyvault secret set --vault-name $MY_KEYVAULT_NAME --name MONGODB-USER-ADMIN-USER --value MONGODB_USER_ADMIN_USER --output none
    az keyvault secret set --vault-name $MY_KEYVAULT_NAME --name MONGODB-USER-ADMIN-PASSWORD --value $(generateRandomPasswordString) --output none
    ```

6. Create a secret for the API key used to access the Percona Monitoring and Management (PMM) server using the [`az keyvault secret set`](/cli/azure/keyvault/secret#az-keyvault-secret-set) command. You update the value of this secret later when you deploy the PMM server.

    ```azurecli-interactive
    az keyvault secret set --vault-name $MY_KEYVAULT_NAME --name PMM-SERVER-API-KEY --value $(openssl rand -base64 32) --output none
    ```

7. Add `AZURE-STORAGE-ACCOUNT-NAME` to use later for backups using the [`az keyvault secret set`](/cli/azure/keyvault/secret#az-keyvault-secret-set) command.

    ```azurecli-interactive
    az keyvault secret set --vault-name $MY_KEYVAULT_NAME --name AZURE-STORAGE-ACCOUNT-NAME --value $AKS_MONGODB_BACKUP_STORAGE_ACCOUNT_NAME --output none
    ```
:::zone-end

:::zone pivot="terraform"
1. Run the following command to update the `mongodb.tfvars` file created earlier with the following configuration:
    ```bash
    cat >> mongodb.tfvars <<EOL
    mongodb_kv_secrets = {
      MONGODB-BACKUP-USER              = "MONGODB_BACKUP_USER"
      MONGODB-BACKUP-PASSWORD          = "$(generateRandomPasswordString)"
      MONGODB-DATABASE-ADMIN-USER      = "MONGODB_DATABASE_ADMIN_USER"
      MONGODB-DATABASE-ADMIN-PASSWORD  = "$(generateRandomPasswordString)"
      MONGODB-CLUSTER-ADMIN-USER       = "MONGODB_CLUSTER_ADMIN_USER"
      MONGODB-CLUSTER-ADMIN-PASSWORD   = "$(generateRandomPasswordString)"
      MONGODB-CLUSTER-MONITOR-USER     = "MONGODB_CLUSTER_MONITOR_USER"
      MONGODB-CLUSTER-MONITOR-PASSWORD = "$(generateRandomPasswordString)"
      MONGODB-USER-ADMIN-USER          = "MONGODB_USER_ADMIN_USER"
      MONGODB-USER-ADMIN-PASSWORD      = "$(generateRandomPasswordString)"
      PMM-SERVER-API-KEY               = "$(generateRandomPasswordString)"
    }
    EOL
    ```
2. Apply the terraform configuration to the target resource.

   ```bash
   terraform fmt
   terraform apply -var-file="mongodb.tfvars" -target module.mongodb[0].azurerm_key_vault_secret.this
   ```
:::zone-end
## Create secrets resources

1. Create a `SecretStore` resource to access the MongoDB passwords stored in your key vault using the `kubectl apply` command.

    ```bash
    kubectl apply -f - <<EOF
    apiVersion: external-secrets.io/v1beta1
    kind: SecretStore
    metadata:
      name: azure-store
      namespace: ${AKS_MONGODB_NAMESPACE}
    spec:
      provider:
        # provider type: azure keyvault
        azurekv:
          authType: WorkloadIdentity
          vaultUrl: "${KEYVAULTURL}"
          serviceAccountRef:
            name: ${SERVICE_ACCOUNT_NAME}
    EOF
    ```

    Example output:

    <!-- expected_similarity=0.8 -->
    ```output
    secretstore.external-secrets.io/azure-store created
    ```

2. Create an `ExternalSecret` resource using the `kubectl apply` command. This resource creates a Kubernetes secret in the `mongodb` namespace with the MongoDB secrets stored in your key vault.

    ```bash
    kubectl apply -f - <<EOF
    apiVersion: external-secrets.io/v1beta1
    kind: ExternalSecret
    metadata:
      name: ${AKS_MONGODB_SECRETS_NAME}
      namespace: ${AKS_MONGODB_NAMESPACE}
    spec:
      refreshInterval: 1h
      secretStoreRef:
        kind: SecretStore
        name: azure-store

      target:
        name: "${AKS_MONGODB_SECRETS_NAME}"
        creationPolicy: Owner

      data:
        # name of the SECRET in the Azure key vault (no prefix is by default a SECRET)
        - secretKey: MONGODB_BACKUP_USER
          remoteRef:
            key: MONGODB-BACKUP-USER
        - secretKey: MONGODB_BACKUP_PASSWORD
          remoteRef:
            key: MONGODB-BACKUP-PASSWORD
        - secretKey: MONGODB_DATABASE_ADMIN_USER
          remoteRef:
            key: MONGODB-DATABASE-ADMIN-USER
        - secretKey: MONGODB_DATABASE_ADMIN_PASSWORD
          remoteRef:
            key: MONGODB-DATABASE-ADMIN-PASSWORD
        - secretKey: MONGODB_CLUSTER_ADMIN_USER
          remoteRef:
            key: MONGODB-CLUSTER-ADMIN-USER
        - secretKey: MONGODB_CLUSTER_ADMIN_PASSWORD
          remoteRef:
            key: MONGODB-CLUSTER-ADMIN-PASSWORD
        - secretKey: MONGODB_CLUSTER_MONITOR_USER
          remoteRef:
            key: MONGODB-CLUSTER-MONITOR-USER
        - secretKey: MONGODB_CLUSTER_MONITOR_PASSWORD
          remoteRef:
            key: MONGODB-CLUSTER-MONITOR-PASSWORD
        - secretKey: MONGODB_USER_ADMIN_USER
          remoteRef:
            key: MONGODB-USER-ADMIN-USER
        - secretKey: MONGODB_USER_ADMIN_PASSWORD
          remoteRef:
            key: MONGODB-USER-ADMIN-PASSWORD
        - secretKey: PMM_SERVER_API_KEY
          remoteRef:
            key: PMM-SERVER-API-KEY
    EOF
    ```

    Example output:

    <!-- expected_similarity=0.8 -->
    ```output
    externalsecret.external-secrets.io/cluster-aks-mongodb-secrets created
    ```

3. Create an `ExternalSecret` resource using the `kubectl apply` command. This resource creates a Kubernetes secret in the `mongodb` namespace for Azure Blob Storage secrets stored in your key vault.

    ```bash
    kubectl apply -f - <<EOF
    apiVersion: external-secrets.io/v1beta1
    kind: ExternalSecret
    metadata:
      name: ${AKS_AZURE_SECRETS_NAME}
      namespace: ${AKS_MONGODB_NAMESPACE}
    spec:
      refreshInterval: 1h
      secretStoreRef:
        kind: SecretStore
        name: azure-store

      target:
        name: "${AKS_AZURE_SECRETS_NAME}"
        creationPolicy: Owner

      data:
        # name of the SECRET in the Azure key vault (no prefix is by default a SECRET)
        - secretKey: AZURE_STORAGE_ACCOUNT_NAME
          remoteRef:
            key: AZURE-STORAGE-ACCOUNT-NAME
        - secretKey: AZURE_STORAGE_ACCOUNT_KEY
          remoteRef:
            key: AZURE-STORAGE-ACCOUNT-KEY
    EOF
    ```

    Example output:

    <!-- expected_similarity=0.8 -->
    ```output
    externalsecret.external-secrets.io/cluster-aks-azure-secrets created
    ```
:::zone pivot="azure-cli"

4. Create a federated credential using the [`az identity federated-credential create`](/cli/azure/identity/federated-credential#az-identity-federated-credential-create) command.

    ```azurecli-interactive
    az identity federated-credential create \
                --name external-secret-operator \
                --identity-name ${MY_IDENTITY_NAME} \
                --resource-group ${MY_RESOURCE_GROUP_NAME} \
                --issuer ${OIDC_URL} \
                --subject system:serviceaccount:${AKS_MONGODB_NAMESPACE}:${SERVICE_ACCOUNT_NAME} \
                --output none
    ```

5. Give permission to the user-assigned identity to access the secret using the [`az keyvault set-policy`](/cli/azure/keyvault#az-keyvault-set-policy) command.

    ```azurecli-interactive
    az keyvault set-policy --name $MY_KEYVAULT_NAME --object-id $MY_IDENTITY_NAME_PRINCIPAL_ID --secret-permissions get --output table
    ```

    Example output:

    <!-- expected_similarity=0.8 -->
    ```output
    Location       Name            ResourceGroup
    -------------  --------------  --------------------------------
    australiaeast  vault-cjcfc-kv  myResourceGroup-rg-australiaeast
    ```
:::zone-end

:::zone pivot="terraform"

4. Add the following terraform configuration in `mongodb/main.tf` to create a federated credential.

    ```hcl
    ## Section to create the federated identity credential for external secret operator
    resource "azurerm_federated_identity_credential" "this" {
      name                = "external-secret-operator"
      resource_group_name = var.resource_group_name
      audience            = ["api://AzureADTokenExchange"]
      issuer              = var.oidc_issuer_url
      parent_id           = azurerm_user_assigned_identity.this.id
      subject             = "system:serviceaccount:${var.mongodb_namespace}:${var.service_account_name}"
    }
    ```

5. Add the following terraform configuration in `mongodb/main.tf` to give permission to the user-assigned identity to access the secret.

    ```hcl
    ## Section to assign permission to the user-assigned identity to access the secret
    resource "azurerm_key_vault_access_policy" "this" {
      key_vault_id = var.key_vault_id
      tenant_id    = azurerm_user_assigned_identity.this.tenant_id
      object_id    = azurerm_user_assigned_identity.this.principal_id
    
      secret_permissions = [
        "Get"
      ]
    }
    ```
6. Apply the terraform configuraion.
   ```bash
       terraform fmt
   
       terraform apply -var-file="mongodb.tfvars" \
      -target=module.mongodb[0].azurerm_federated_identity_credential.this \
      -target=module.mongodb[0].azurerm_key_vault_access_policy.this
   ```
:::zone-end

## Install the Percona Operator and CRDs

The Percona Operator is typically distributed as a Kubernetes `Deployment` or `Operator`. You can deploy it by using a `kubectl apply -f` command with a manifest file. You can find the latest manifests in the [Percona GitHub repository](https://github.com/percona/percona-server-mongodb-operator) or the [official documentation](https://docs.percona.com/percona-operator-for-mongodb/aks.html).

* Deploy the Percona Operator and custom resource definitions (CRDs) using the `kubectl apply` command.

    ```bash
    kubectl apply --server-side -f https://raw.githubusercontent.com/percona/percona-server-mongodb-operator/v1.16.0/deploy/bundle.yaml -n "${AKS_MONGODB_NAMESPACE}"
    ```

    Example output:

    <!-- expected_similarity=0.8 -->
    ```output
    customresourcedefinition.apiextensions.k8s.io/perconaservermongodbbackups.psmdb.percona.com serverside-applied
    customresourcedefinition.apiextensions.k8s.io/perconaservermongodbrestores.psmdb.percona.com serverside-applied
    customresourcedefinition.apiextensions.k8s.io/perconaservermongodbs.psmdb.percona.com serverside-applied
    role.rbac.authorization.k8s.io/percona-server-mongodb-operator serverside-applied
    serviceaccount/percona-server-mongodb-operator serverside-applied
    rolebinding.rbac.authorization.k8s.io/service-account-percona-server-mongodb-operator serverside-applied
    deployment.apps/percona-server-mongodb-operator serverside-applied
    ```

## Deploy the MongoDB cluster

1. Deploy a MongoDB cluster with the Percona Operator using the `kubectl apply` command. To help ensure high availability, you deploy the MongoDB cluster with a replica set, with sharding enabled, in multiple availability zones, and with a backup solution that stores the backups in an Azure Blob Storage account.

    ```bash
    kubectl apply -f - <<EOF
    apiVersion: psmdb.percona.com/v1
    kind: PerconaServerMongoDB
    metadata:
      name: ${AKS_MONGODB_CLUSTER_NAME}
      namespace: ${AKS_MONGODB_NAMESPACE}
      finalizers:
        - delete-psmdb-pods-in-order
    spec:
      crVersion: 1.16.0
      image: ${MY_ACR_REGISTRY}.azurecr.io/percona-server-mongodb:7.0.8-5
      imagePullPolicy: Always
      updateStrategy: SmartUpdate
      upgradeOptions:
        versionServiceEndpoint: https://check.percona.com
        apply: disabled
        schedule: "0 2 * * *"
        setFCV: false
      secrets:
        users: "${AKS_MONGODB_SECRETS_NAME}"
        encryptionKey: "${AKS_MONGODB_SECRETS_ENCRYPTION_KEY}"
      pmm:
        enabled: true
        image: ${MY_ACR_REGISTRY}.azurecr.io/pmm-client:2.41.2
        serverHost: monitoring-service
      replsets:
        - name: rs0
          size: 3
          affinity:
            antiAffinityTopologyKey: "failure-domain.beta.kubernetes.io/zone"
          nodeSelector:
            kubernetes.azure.com/agentpool: "mongodbpool"
          podDisruptionBudget:
            maxUnavailable: 1
          expose:
            enabled: false
            exposeType: ClusterIP
          resources:
            limits:
              cpu: "300m"
              memory: "0.5G"
            requests:
              cpu: "300m"
              memory: "0.5G"
          volumeSpec:
            persistentVolumeClaim:
              storageClassName: managed-csi-premium
              accessModes: ["ReadWriteOnce"]
              resources:
                requests:
                  storage: 1Gi
          nonvoting:
            enabled: false
            size: 3
            affinity:
              antiAffinityTopologyKey: "failure-domain.beta.kubernetes.io/zone"
            nodeSelector:
              kubernetes.azure.com/agentpool: "mongodbpool"		 
            podDisruptionBudget:
              maxUnavailable: 1
            resources:
              limits:
                cpu: "300m"
                memory: "0.5G"
              requests:
                cpu: "300m"
                memory: "0.5G"
            volumeSpec:
              persistentVolumeClaim:
                storageClassName: managed-csi-premium
                accessModes: ["ReadWriteOnce"]
                resources:
                  requests:
                    storage: 1Gi
          arbiter:
            enabled: false
            size: 1
            affinity:
              antiAffinityTopologyKey: "failure-domain.beta.kubernetes.io/zone"
            nodeSelector:
              kubernetes.azure.com/agentpool: "mongodbpool"
            resources:
              limits:
                cpu: "300m"
                memory: "0.5G"
              requests:
                cpu: "300m"
                memory: "0.5G"
      sharding:
        enabled: true
        configsvrReplSet:
          size: 3
          affinity:
            antiAffinityTopologyKey: "failure-domain.beta.kubernetes.io/zone"
          nodeSelector:
            kubernetes.azure.com/agentpool: "mongodbpool"
          podDisruptionBudget:
            maxUnavailable: 1
          expose:
            enabled: false
          resources:
            limits:
              cpu: "300m"
              memory: "0.5G"
            requests:
              cpu: "300m"
              memory: "0.5G"
          volumeSpec:
            persistentVolumeClaim:
              storageClassName: managed-csi-premium
              accessModes: ["ReadWriteOnce"]
              resources:
                requests:
                  storage: 1Gi
        mongos:
          size: 3
          affinity:
            antiAffinityTopologyKey: "failure-domain.beta.kubernetes.io/zone"
          nodeSelector:
            kubernetes.azure.com/agentpool: "mongodbpool"
          podDisruptionBudget:
            maxUnavailable: 1
          resources:
            limits:
              cpu: "300m"
              memory: "0.5G"
            requests:
              cpu: "300m"
              memory: "0.5G"
          expose:
            exposeType: ClusterIP
      backup:
        enabled: true
        image: ${MY_ACR_REGISTRY}.azurecr.io/percona-backup-mongodb:2.4.1
        storages:
          azure-blob:
            type: azure
            azure:
              container: "${AKS_MONGODB_BACKUP_STORAGE_CONTAINER_NAME}"
              prefix: psmdb
              endpointUrl: "https://${AKS_MONGODB_BACKUP_STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
              credentialsSecret: "${AKS_AZURE_SECRETS_NAME}"
        pitr:
          enabled: false
          oplogOnly: false
          compressionType: gzip
          compressionLevel: 6
        tasks:
          - name: daily-azure-us-east
            enabled: true
            schedule: "0 0 * * *"
            keep: 3
            storageName: azure-blob    
            compressionType: gzip
            compressionLevel: 6
    EOF
    ```

    Example output:

    <!-- expected_similarity=0.8 -->
    ```output
    perconaservermongodb.psmdb.percona.com/cluster-aks-mongodb created
    ```

2. Finish the MongoDB cluster deployment process using the following script:

    ```bash
    while [ "$(kubectl get psmdb -n ${AKS_MONGODB_NAMESPACE} -o jsonpath='{.items[0].status.state}')" != "ready" ]; do echo "waiting for MongoDB cluster to be ready"; sleep 10; done
    ```

3. When the process finishes, your cluster shows the `Ready` status. You can view the status using the `kubectl get` command.

    ```bash
    kubectl get psmdb -n ${AKS_MONGODB_NAMESPACE}
    ```

    Example output:

    <!-- expected_similarity=0.8 -->
    ```output
    NAME                  ENDPOINT                                               STATUS   AGE
    cluster-aks-mongodb   cluster-aks-mongodb-mongos.mongodb.svc.cluster.local   ready    3m1s
    ```

4. View the availability zones of the nodes in your cluster using the `kubectl get` command.

    ```bash
    kubectl get node -o custom-columns=Name:.metadata.name,Zone:".metadata.labels.topology\.kubernetes\.io/zone"
    ```

    Example output:

    <!-- expected_similarity=0.8 -->
    ```output
    Name                                   Zone
    aks-mongodbpool-30094695-vmss000000    australiaeast-1
    aks-systempool-28994785-vmss000000     australiaeast-1
    aks-systempool-28994785-vmss000001     australiaeast-2
    aks-systempool-28994785-vmss000002     australiaeast-3
    ```

## Connect to the Percona Server

To connect to Percona Server for MongoDB, you need to construct the MongoDB connection URI string. It includes the credentials of the admin user, which are stored in the `Secrets` object.

1. List the `Secrets` objects using the `kubectl get` command.

    ```bash
    kubectl get secrets -n ${AKS_MONGODB_NAMESPACE}
    ```

    Example output:

    <!-- expected_similarity=0.8 -->
    ```output
    NAME                                                 TYPE                 DATA   AGE
    cluster-aks-azure-secrets                            Opaque               2      2m56s
    cluster-aks-mongodb-mongodb-keyfile                  Opaque               1      2m54s
    cluster-aks-mongodb-secrets                          Opaque               11     2m56s
    cluster-aks-mongodb-secrets-mongodb-encryption-key   Opaque               1      2m54s
    cluster-aks-mongodb-ssl                              kubernetes.io/tls    3      2m55s
    cluster-aks-mongodb-ssl-internal                     kubernetes.io/tls    3      2m54s
    external-secrets-webhook                             Opaque               4      3m49s
    internal-cluster-aks-mongodb-users                   Opaque               11     2m56s
    sh.helm.release.v1.external-secrets.v1               helm.sh/release.v1   1      3m49s
    ```

2. View the `Secrets` contents to retrieve the admin user credentials using the `kubectl get` command.

    ```bash
    kubectl describe secret ${AKS_MONGODB_SECRETS_NAME} -n ${AKS_MONGODB_NAMESPACE}
    ```

    Example output:

    <!-- expected_similarity=0.1 -->
    ```output
    Name:         cluster-aks-mongodb-secrets
    Namespace:    mongodb
    Labels:       reconcile.external-secrets.io/managed=true
    Annotations:  <none>

    Type:  Opaque

    Data
    ====
    MONGODB_CLUSTER_ADMIN_USER:        12 bytes
    MONGODB_CLUSTER_MONITOR_PASSWORD:  16 bytes
    MONGODB_CLUSTER_MONITOR_USER:      14 bytes
    MONGODB_DATABASE_ADMIN_USER:       13 bytes
    MONGODB_USER_ADMIN_USER:           9 bytes
    MONGODB_BACKUP_PASSWORD:           16 bytes
    MONGODB_BACKUP_USER:               6 bytes
    MONGODB_CLUSTER_ADMIN_PASSWORD:    18 bytes
    MONGODB_DATABASE_ADMIN_PASSWORD:   18 bytes
    MONGODB_USER_ADMIN_PASSWORD:       17 bytes
    ```

3. Decode the Base64-encoded login name and password and export the connection string to the environment variable using the following commands:

    ```bash
    export databaseAdmin=$(kubectl get secret ${AKS_MONGODB_SECRETS_NAME} -n ${AKS_MONGODB_NAMESPACE} -o jsonpath="{.data.MONGODB_DATABASE_ADMIN_USER}" | base64 --decode)
    export databaseAdminPassword=$(kubectl get secret ${AKS_MONGODB_SECRETS_NAME} -n ${AKS_MONGODB_NAMESPACE} -o jsonpath="{.data.MONGODB_DATABASE_ADMIN_PASSWORD}" | base64 --decode)
    export connectionString="mongodb://${databaseAdmin}:${databaseAdminPassword}@${AKS_MONGODB_CLUSTER_NAME}-mongos.mongodb.svc.cluster.local/admin?replicaSet=rs0&ssl=false&directConnection=true"

    ```

## Verify the MongoDB cluster

In this section, you verify your MongoDB cluster by running a container with a MongoDB client and connect its console output to your terminal.

1. Create a pod named `percona-client` under the `${AKS_MONGODB_NAMESPACE}` namespace in your cluster using the `kubectl run` command.

    ```bash
    kubectl -n "${AKS_MONGODB_NAMESPACE}" run -i --rm --tty percona-client --image=${MY_ACR_REGISTRY}.azurecr.io/percona-server-mongodb:7.0.8-5 --restart=Never -- env CONN_STR=$connectionString bash -il
    ```

2. In a different terminal window, verify the pod was successfully created using the `kubectl get` command.

    ```bash
    kubectl get pod percona-client -n ${AKS_MONGODB_NAMESPACE}
    ```

    Example output:

    <!-- expected_similarity=0.4 -->
    ```output
    NAME             READY   STATUS    RESTARTS   AGE
    percona-client   1/1     Running   0          39s
    ```

3. Connect to the MongoDB cluster using the admin user credentials from the previous section in the terminal window that you used to create the `percona-client` pod.

    ```bash  
    mongosh $CONN_STR
    ```

    Example output:

    <!-- expected_similarity=0.4 -->
    ```output
    Current Mongosh Log ID: L6mN7oP8qR9sT0uV1wX2yZ3a
    Connecting to:          mongodb://<credentials>@cluster-aks-mongodb-mongos.mongodb.svc.cluster.local/admin?replicaSet=rs0&ssl=false&directConnection=true&appName=mongosh+2.1.5
    Using MongoDB:          7.0.8-5
    Using Mongosh:          2.1.5

    For mongosh info see: https://docs.mongodb.com/mongodb-shell/
    ...
    ```

4. List the databases in your cluster using the `show dbs` command.

    ```bash
    show dbs
    ```

    Example output:

    <!-- expected_similarity=0.8 -->
    ```output
    rs0 [direct: mongos] admin> show dbs
    admin   960.00 KiB
    config    3.45 MiB
    rs0 [direct: mongos] admin>
    ```

## Create a MongoDB backup

You can back up your data to Azure using one of the following methods:

* **Manual**: Manually back up your data at any time.
* **Scheduled**: Configure backups and their schedules in the CRD YAML. The Percona Operator makes the backups automatically according to the specified schedule.

The Percona Operator can perform either of the following backup types:

* **Logical backup**: Query Percona Server for MongoDB for the database data, and then write the retrieved data to the remote backup storage.
* **Physical backup**: Copy physical files from the Percona Server for MongoDB `dbPath` data directory to the remote backup storage.

Logical backups use less storage but are slower than physical backups.

To store backups on Azure Blob Storage using Percona, you need to create a secret. You completed this step in an earlier command. For detailed instructions, follow the steps in the [Percona documentation about Azure Blob Storage](https://docs.percona.com/percona-operator-for-mongodb/backups-storage.html#microsoft-azure-blob-storage).

### Configure scheduled backups

You can define the backup schedule in the backup section of the CRD in *mongodb-cr.yaml* using the following guidance:

* Set the `backup.enabled` key to `true`.
* Ensure that the `backup.storages` subsection contains at least one configured storage resource.
* Ensure that the `backup.tasks` subsection enables backup scheduling.

For more information, see [Making scheduled backups](https://docs.percona.com/percona-operator-for-mongodb/backups-scheduled.html).

### Perform manual backups

You can make a manual, on-demand backup in the backup section of the CRD in *mongodb-cr.yaml* using the following guidance:

* Set the `backup.enabled` key to `true`.
* Ensure that the `backup.storages` subsection contains at least one configured storage resource.

For more information, see [Making on-demand backups](https://docs.percona.com/percona-operator-for-mongodb/backups-ondemand.html).

## Deploy a MongoDB backup

1. Deploy your MongoDB backup using the `kubectl apply` command.

    ```bash
    kubectl apply -f - <<EOF
    apiVersion: psmdb.percona.com/v1
    kind: PerconaServerMongoDBBackup
    metadata:
      finalizers:
      - delete-backup
      name: az-backup1
      namespace: ${AKS_MONGODB_NAMESPACE}
    spec:
      clusterName: ${AKS_MONGODB_CLUSTER_NAME}
      storageName: azure-blob
      type: logical
    EOF
    ```

    Example output:

    <!-- expected_similarity=0.8 -->
    ```output
   perconaservermongodbbackup.psmdb.percona.com/az-backup1 created
    ```

2. Finish the MongoDB backup deployment process using the following script:

    ```bash
    while [ "$(kubectl get psmdb-backup -n ${AKS_MONGODB_NAMESPACE} -o jsonpath='{.items[0].status.state}')" != "ready" ]; do echo "waiting for the backup to be ready"; sleep 10; done
    ```
  
    Example output:
  
    <!-- expected_similarity=0.8 -->
    ```output
    waiting for the backup to be ready
    ```

3. When the process finishes, the backup should return the `Ready` status. Verify the backup deployment was successful using the `kubectl get` command.

    ```bash
    kubectl get psmdb-backup -n ${AKS_MONGODB_NAMESPACE}
    ```

    Example output:
  
    <!-- expected_similarity=0.8 -->
    ```output
    NAME         CLUSTER               STORAGE      DESTINATION                                                                       TYPE      STATUS   COMPLETED   AGE
    az-backup1   cluster-aks-mongodb   azure-blob   https://mongodbsacjcfc.blob.core.windows.net/backups/psmdb/2024-07-01T12:27:57Z   logical   ready    3h3m        3h3m
    ```

4. If you have any problems with the backup, you can view logs from the `backup-agent` container of the appropriate pod using the `kubectl logs` command.

    ```bash
    kubectl logs pod/${AKS_MONGODB_CLUSTER_NAME}-rs0-0 -c backup-agent -n ${AKS_MONGODB_NAMESPACE}
    ```

## Next step

> [!div class="nextstepaction"]
> [Deploy a client application (Mongo Express)][validate-mongodb-cluster]

<!-- Links -->
[validate-mongodb-cluster]: ./validate-mongodb-cluster.md
