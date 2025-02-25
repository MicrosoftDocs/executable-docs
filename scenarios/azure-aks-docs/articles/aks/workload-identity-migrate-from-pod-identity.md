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

## Create resource group
Set your subscription to be the current active subscription using the `az account set` command. Then, create a random suffix to ensure unique resource names.

```bash
export RANDOM_SUFFIX=$(openssl rand -hex 3)
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

## Create a managed identity.

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

## Get Client ID

Save the client ID of the managed identity to an environment variable.

```bash
export USER_ASSIGNED_CLIENT_ID="$(az identity show --resource-group "$RESOURCE_GROUP_NAME" --name "$IDENTITY_NAME" --query 'clientId' -o tsv)"
```

## Save OIDC Issuer URL
Get the OIDC Issuer URL and save it to an environment variable.By default, the Issuer is set to use the base URL `https://{region}.oic.prod-aks.azure.com/{uuid}`, where the value for `{region}` matches the location the AKS cluster is deployed in. The value `{uuid}` represents the OIDC key.

```bash
export AKS_CLUSTER_NAME=$MY_AKS_CLUSTER_NAME
export AKS_RESOURCE_GROUP=$MY_AKS_RESOURCE_GROUP
export AKS_OIDC_ISSUER="$(az aks show --name "$AKS_CLUSTER_NAME" --resource-group "$AKS_RESOURCE_GROUP" --query "oidcIssuerProfile.issuerUrl" -o tsv)"
```

## Load credentials

Get the Kubernetes credentials for your cluster.

```bash
az aks get-credentials --name "$AKS_CLUSTER_NAME" --resource-group "$AKS_RESOURCE_GROUP"
```

## Create Namespace

Create a namespace.

```bash
export SERVICE_ACCOUNT_NAMESPACE="mynamespace$RANDOM_SUFFIX"
kubectl create namespace "$SERVICE_ACCOUNT_NAMESPACE"
```

## Create Service Account
Create the service account and annotate it with the client ID of the managed identity.

```bash
export SERVICE_ACCOUNT_NAME="myserviceaccount$RANDOM_SUFFIX"
kubectl create serviceaccount "$SERVICE_ACCOUNT_NAME" -n "$SERVICE_ACCOUNT_NAMESPACE"
kubectl annotate serviceaccount "$SERVICE_ACCOUNT_NAME" --namespace "$SERVICE_ACCOUNT_NAMESPACE" azure.workload.identity/client-id="$USER_ASSIGNED_CLIENT_ID"
```

## Establish federated identity credential trust

Establish a federated identity credential between the managed identity, the service account issuer, and the subject.

```bash
export FEDERATED_CREDENTIAL_NAME="myFederatedCredentialName$RANDOM_SUFFIX"
az identity federated-credential create --name "$FEDERATED_CREDENTIAL_NAME" --identity-name "$IDENTITY_NAME" --resource-group "$RESOURCE_GROUP_NAME" --issuer "$AKS_OIDC_ISSUER" --subject "system:serviceaccount:$SERVICE_ACCOUNT_NAMESPACE:$SERVICE_ACCOUNT_NAME" --audience "api://AzureADTokenExchange"
```

## Deploy the workload with migration sidecar

```bash
export POD_NAME="httpbin-pod"

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
kubectl apply -f pod.yaml
kubectl wait --for=condition=Ready pod/httpbin-pod -n "$SERVICE_ACCOUNT_NAMESPACE" --timeout=120s
kubectl describe pods $POD_NAME -n "$SERVICE_ACCOUNT_NAMESPACE"
kubectl logs $POD_NAME -n "$SERVICE_ACCOUNT_NAMESPACE"
```

## Remove pod-managed identity

After you've completed your testing and the application is successfully able to get a token using the proxy sidecar, you can remove the Microsoft Entra pod-managed identity mapping for the pod from your cluster, and then remove the identity.

```bash
az aks pod-identity delete $IDENTITY_NAME
```

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