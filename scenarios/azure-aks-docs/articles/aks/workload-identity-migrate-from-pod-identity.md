---
title: Migrate your Azure Kubernetes Service (AKS) pod to use workload identity
description: In this Azure Kubernetes Service (AKS) article, you learn how to configure your Azure Kubernetes Service pod to authenticate with workload identity.
ms.topic: how-to
ms.subservice: aks-security
ms.custom: devx-track-azurecli, innovation-engine
ms.date: 07/31/2023
author: nickomang
ms.author: nickoman
---

# Migrate from pod managed-identity to workload identity

This article focuses on migrating from a pod-managed identity to Microsoft Entra Workload ID for your Azure Kubernetes Service (AKS) cluster. It also provides guidance depending on the version of the [Azure Identity][azure-identity-supported-versions] client library used by your container-based application.

If you aren't familiar with Microsoft Entra Workload ID, see the [Overview][workload-identity-overview] article.

## Before you begin

Ensure you have the Azure CLI version 2.47.0 or later installed. Run the `az --version` command to find the version

If you need to install or upgrade, see [Install Azure CLI][install-azure-cli].

## Migration scenarios

This section explains the migration options available depending on what version of the Azure Identity SDK is installed.

For either scenario, you need to have the federated trust set up before you update your application to use the workload identity. The following are the minimum steps required:

- Create a managed identity credential.
- Associate the managed identity with the Kubernetes service account already used for the pod-managed identity or create a new Kubernetes service account and then associate it with the managed identity.
- Establish a federated trust relationship between the managed identity and Microsoft Entra ID.

### Migrate from latest version

If your application is already using the latest version of the Azure Identity SDK, perform the following steps to complete the authentication configuration:

- Deploy workload identity in parallel with pod-managed identity. You can restart your application deployment to begin using the workload identity, where it injects the OIDC annotations into the application automatically.
- After verifying the application is able to authenticate successfully, you can remove the pod-managed identity annotations from your application and then remove the pod-managed identity add-on.

### Migrate from older version

If your application isn't using the latest version of the Azure Identity SDK, you have two options:

- Use a migration sidecar that we provide within your Linux applications, which proxies the IMDS transactions your application makes over to [OpenID Connect][openid-connect-overview] (OIDC). The migration sidecar isn't intended to be a long-term solution, but a way to get up and running quickly on workload identity. Perform the following steps:

  - Deploy the workload with migration sidecar to proxy the application IMDS transactions.
  - Verify the authentication transactions are completing successfully.
  - Schedule the work for the applications to update their SDKs to a supported version.
  - Once the SDKs are updated to the supported version, you can remove the proxy sidecar and redeploy the application.

  > [!NOTE]
  > The migration sidecar is **not supported for production use**. This feature is meant to give you time to migrate your application SDKs to a supported version, and not meant or intended to be a long-term solution.
  > The migration sidecar is only available for Linux containers, due to only providing pod-managed identities with Linux node pools.

- Rewrite your application to support the latest version of the [Azure Identity][azure-identity-supported-versions] client library. Afterwards, perform the following steps:

  - Restart your application deployment to begin authenticating using the workload identity.
  - Once you verify the authentication transactions are completing successfully, you can remove the pod-managed identity annotations from your application and then remove the pod-managed identity add-on.

## Create a managed identity

If you don't have a managed identity created and assigned to your pod, perform the following steps to create and grant the necessary permissions to storage, Key Vault, or whatever resources your application needs to authenticate with in Azure.

1. Set your subscription to be the current active subscription using the `az account set` command. Then, create a random suffix to ensure unique resource names.

   ```bash
   export RANDOM_SUFFIX=$(openssl rand -hex 3)
   ```

3. Create a resource group.

   ```bash
   export RESOURCE_GROUP_NAME="myResourceGroup$RANDOM_SUFFIX"
   export LOCATION="WestUS2"
   az group create --name "$RESOURCE_GROUP_NAME" --location "$LOCATION"
   ```

   Results:

   <!-- expected_similarity=0.3 -->

   ```json
   {
     "id": "/subscriptions/xxxxx/resourceGroups/myResourceGroupxxx",
     "location": "<location>",
     "managedBy": null,
     "name": "myResourceGroupxxx",
     "properties": {
       "provisioningState": "Succeeded"
     },
     "tags": null,
     "type": "Microsoft.Resources/resourceGroups"
   }
   ```

4. Create a managed identity.

   ```bash
   export IDENTITY_NAME="userAssignedIdentity$RANDOM_SUFFIX"
   az identity create --name "$IDENTITY_NAME" --resource-group "$RESOURCE_GROUP_NAME" --location "$LOCATION"
   ```

   Results:

   <!-- expected_similarity=0.3 -->

   ```json
   {
     "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
     "id": "/subscriptions/xxxxx/resourceGroups/myResourceGroupxxx/providers/Microsoft.ManagedIdentity/userAssignedIdentities/userAssignedIdentityxxx",
     "location": "<location>",
     "name": "userAssignedIdentityxxx",
     "principalId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
     "resourceGroup": "myResourceGroupxxx",
     "tags": {},
     "type": "Microsoft.ManagedIdentity/userAssignedIdentities"
   }
   ```

5. Save the client ID of the managed identity to an environment variable.

   ```bash
   export USER_ASSIGNED_CLIENT_ID="$(az identity show --resource-group "$RESOURCE_GROUP_NAME" --name "$IDENTITY_NAME" --query 'clientId' -o tsv)"
   ```

6. Grant the managed identity the permissions required to access the resources in Azure it requires. For information on how to do this, see [Assign a managed identity access to a resource][assign-rbac-managed-identity].

7. Get the OIDC Issuer URL and save it to an environment variable. Replace the default values for the cluster name and the resource group name.

   ```bash
   export AKS_CLUSTER_NAME=$MY_AKS_CLUSTER_NAME
   export AKS_RESOURCE_GROUP=$MY_AKS_RESOURCE_GROUP
   export AKS_OIDC_ISSUER="$(az aks show --name "$AKS_CLUSTER_NAME" --resource-group "$AKS_RESOURCE_GROUP" --query "oidcIssuerProfile.issuerUrl" -o tsv)"
   ```

   The variable should contain the Issuer URL similar to the following example:

   ```bash
   echo "$AKS_OIDC_ISSUER"
   ```

   Results:

   <!-- expected_similarity=0.3 -->

   ```output
   https://eastus.oic.prod-aks.azure.com/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/
   ```

   By default, the Issuer is set to use the base URL `https://{region}.oic.prod-aks.azure.com/{uuid}`, where the value for `{region}` matches the location the AKS cluster is deployed in. The value `{uuid}` represents the OIDC key.

## Create Kubernetes service account

If you don't have a dedicated Kubernetes service account created for this application, perform the following steps to create and then annotate it with the client ID of the managed identity created in the previous step.

1. Get the Kubernetes credentials for your cluster.

   ```bash
   az aks get-credentials --name "$AKS_CLUSTER_NAME" --resource-group "$AKS_RESOURCE_GROUP"
   ```

2. Create a namespace if you don't have one.

   ```bash
   export SERVICE_ACCOUNT_NAMESPACE="mynamespace$RANDOM_SUFFIX"
   kubectl create namespace "$SERVICE_ACCOUNT_NAMESPACE"
   ```

3. Create the service account and annotate it with the client ID of the managed identity.

   ```bash
   export SERVICE_ACCOUNT_NAME="myserviceaccount$RANDOM_SUFFIX"
   kubectl create serviceaccount "$SERVICE_ACCOUNT_NAME" -n "$SERVICE_ACCOUNT_NAMESPACE"
   kubectl annotate serviceaccount "$SERVICE_ACCOUNT_NAME" --namespace "$SERVICE_ACCOUNT_NAMESPACE" azure.workload.identity/client-id="$USER_ASSIGNED_CLIENT_ID"
   ```

   The following output resembles successful creation of the service account:

   ```output
   serviceaccount/<service-account-name> annotated
   ```

## Establish federated identity credential trust

Establish a federated identity credential between the managed identity, the service account issuer, and the subject.

1. Create the federated identity credential. Replace the values `federated-identity-name`, `service-account-namespace`, and `service-account-name`.

   ```bash
   export FEDERATED_CREDENTIAL_NAME="myFederatedCredentialName$RANDOM_SUFFIX"
   az identity federated-credential create --name "$FEDERATED_CREDENTIAL_NAME" --identity-name "$IDENTITY_NAME" --resource-group "$RESOURCE_GROUP_NAME" --issuer "$AKS_OIDC_ISSUER" --subject "system:serviceaccount:$SERVICE_ACCOUNT_NAMESPACE:$SERVICE_ACCOUNT_NAME" --audience "api://AzureADTokenExchange"
   ```

   > [!NOTE]
   > It takes a few seconds for the federated identity credential to be propagated after being initially added. If a token request is made immediately after adding the federated identity credential, it might lead to failure for a couple of minutes as the cache is populated in the directory with old data. To avoid this issue, you can add a slight delay after adding the federated identity credential.

## Deploy the workload with migration sidecar

If your application is using managed identity and still relies on IMDS to get an access token, you can use the workload identity migration sidecar to start migrating to workload identity. This sidecar is a migration solution and in the long-term, applications should modify their code to use the latest Azure Identity SDKs that support client assertion.

To update or deploy the workload, add the following pod annotations to use the migration sidecar in your pod specification:

- `azure.workload.identity/inject-proxy-sidecar` - value is `"true"` or `"false"`
- `azure.workload.identity/proxy-sidecar-port` - value is the desired port for the proxy sidecar. The default value is `"8000"`.

When a pod with the above annotations is created, the Azure Workload Identity mutating webhook automatically injects the init-container and proxy sidecar to the pod spec.

Here's an example of the mutated pod spec:

```bash
export POD_NAME="httpbin-pod"
```

```bash
cat <<EOF > pod.yaml
apiVersion: v1
kind: Pod
metadata:
  name: $POD_NAME
  namespace: $SERVICE_ACCOUNT_NAMESPACE
  labels:
    app: httpbin
  annotations:
    azure.workload.identity/inject-proxy-sidecar: "true"
    azure.workload.identity/proxy-sidecar-port: "8000"
spec:
  serviceAccountName: $SERVICE_ACCOUNT_NAME
  containers:
  - name: httpbin
    image: docker.io/kennethreitz/httpbin
    env:
    - name: IDENTITY_ENDPOINT
      value: "http://localhost:8000/metadata/identity/oauth2/token"
    - name: IDENTITY_HEADER
      value: "true"
    - name: IMDS_ENDPOINT
      value: "http://169.254.169.254"
EOF
```

After updating or deploying your application, verify the pod is in a running state using the [kubectl describe pod][kubectl-describe] command. Replace `$POD_NAME` with the name of your deployed pod.

Apply the pod specification:

```bash
kubectl apply -f pod.yaml
kubectl wait --for=condition=Ready pod/httpbin-pod -n "$SERVICE_ACCOUNT_NAMESPACE" --timeout=120s
```

```bash

kubectl describe pods $POD_NAME -n "$SERVICE_ACCOUNT_NAMESPACE"
```

To verify that the pod is passing IMDS transactions, use the [kubectl logs][kubelet-logs] command.

```bash
kubectl logs $POD_NAME -n "$SERVICE_ACCOUNT_NAMESPACE"
```

The following log output resembles successful communication through the proxy sidecar. Verify that the logs show a token is successfully acquired and the GET operation is successful.

```output
I0926 00:29:29.968723       1 proxy.go:97] proxy "msg"="starting the proxy server" "port"=8080 "userAgent"="azure-workload-identity/proxy/v0.13.0-12-gc8527f3 (linux/amd64) c8527f3/2022-09-26-00:19"
I0926 00:29:29.972496       1 proxy.go:173] proxy "msg"="received readyz request" "method"="GET" "uri"="/readyz"
I0926 00:29:30.936769       1 proxy.go:107] proxy "msg"="received token request" "method"="GET" "uri"="/metadata/identity/oauth2/token?resource=https://management.core.windows.net/api-version=2018-02-01&client_id=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
I0926 00:29:31.101998       1 proxy.go:129] proxy "msg"="successfully acquired token" "method"="GET" "uri"="/metadata/identity/oauth2/token?resource=https://management.core.windows.net/api-version=2018-02-01&client_id=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

## Remove pod-managed identity

After you've completed your testing and the application is successfully able to get a token using the proxy sidecar, you can remove the Microsoft Entra pod-managed identity mapping for the pod from your cluster, and then remove the identity.

1. Remove the identity from your pod. This should only be done after all pods in the namespace using the pod-managed identity mapping have migrated to use the sidecar.

    Use the `az aks pod-identity delete` command to delete the pod-managed identity. Ensure you replace `<pod-managed-identity-name>` with the name of the pod-managed identity you wish to delete.

## Next steps

This article showed you how to set up your pod to authenticate using a workload identity as a migration option. For more information about Microsoft Entra Workload ID, see the [Overview][workload-identity-overview] article.

<!-- INTERNAL LINKS -->
[pod-annotations]: workload-identity-overview.md#pod-annotations
[az-identity-create]: /cli/azure/identity#az-identity-create
[az-account-set]: /cli/azure/account#az-account-set
[az-aks-get-credentials]: /cli/azure/aks#az-aks-get-credentials
[workload-identity-overview]: workload-identity-overview.md
[az-identity-federated-credential-create]: /cli/azure/identity/federated-credential#az-identity-federated-credential-create
[az-aks-pod-identity-delete]: /cli/azure/aks/pod-identity#az-aks-pod-identity-delete
[azure-identity-supported-versions]: workload-identity-overview.md#dependencies
[azure-identity-libraries]: ../active-directory/develop/reference-v2-libraries.md
[openid-connect-overview]: /azure/active-directory/develop/v2-protocols-oidc
[install-azure-cli]: /cli/azure/install-azure-cli
[assign-rbac-managed-identity]: /azure/role-based-access-control/role-assignments-portal-managed-identity

<!-- EXTERNAL LINKS -->
[kubectl-describe]: https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#describe
[kubelet-logs]: https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#logs