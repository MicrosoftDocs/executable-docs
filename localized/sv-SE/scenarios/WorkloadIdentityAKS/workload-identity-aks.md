---
title: Distribuera och konfigurera ett AKS-kluster med arbetsbelastningsidentitet
description: I den här artikeln om Azure Kubernetes Service (AKS) distribuerar du ett Azure Kubernetes Service-kluster och konfigurerar det med ett Microsoft Entra-arbetsbelastnings-ID.
author: tamram
ms.topic: article
ms.subservice: aks-security
ms.custom: devx-track-azurecli
ms.date: 05/28/2024
ms.author: tamram
---

# Distribuera och konfigurera arbetsbelastningsidentitet i ett AKS-kluster (Azure Kubernetes Service)

Azure Kubernetes Service (AKS) är en hanterad Kubernetes-tjänst som gör att du snabbt kan distribuera och hantera Kubernetes-kluster. Den här artikeln visar hur du gör följande:

* Distribuera ett AKS-kluster med Azure CLI med OpenID Connect-utfärdaren och ett Microsoft Entra-arbetsbelastnings-ID.
* Skapa ett Microsoft Entra-arbetsbelastnings-ID och Kubernetes-tjänstkonto.
* Konfigurera den hanterade identiteten för tokenfederation.
* Distribuera arbetsbelastningen och verifiera autentiseringen med arbetsbelastningsidentiteten.
* Du kan också ge en podd i klustret åtkomst till hemligheter i ett Azure-nyckelvalv.

Den här artikeln förutsätter att du har en grundläggande förståelse för Kubernetes-begrepp. Mer information finns i [Viktiga koncept för Azure Kubernetes Service (AKS)][kubernetes-concepts]. Om du inte är bekant med Microsoft Entra-arbetsbelastnings-ID kan du läsa följande [översiktsartikel][workload-identity-overview] .

## Förutsättningar

* [!INCLUDE [quickstarts-free-trial-note](~/reusable-content/ce-skilling/azure/includes/quickstarts-free-trial-note.md)]
* Den här artikeln kräver version 2.47.0 eller senare av Azure CLI. Om du använder Azure Cloud Shell är den senaste versionen redan installerad.
* Kontrollera att den identitet som du använder för att skapa klustret har lämpliga minimibehörigheter. Mer information om åtkomst och identitet för AKS finns i [Åtkomst- och identitetsalternativ för Azure Kubernetes Service (AKS)][aks-identity-concepts].
* Om du har flera Azure-prenumerationer väljer du lämpligt prenumerations-ID där resurserna ska faktureras med [kommandot az account set][az-account-set] .

> [!NOTE]
> Du kan använda _Service Connector_ för att konfigurera vissa steg automatiskt. Se även: [Självstudie: Ansluta till Azure Storage-konto i Azure Kubernetes Service (AKS) med Service Connector med hjälp av arbetsbelastningsidentitet][tutorial-python-aks-storage-workload-identity].

## Skapa en resursgrupp

En [Azure-resursgrupp][azure-resource-group] är en logisk grupp där Azure-resurser distribueras och hanteras. När du skapar en resursgrupp uppmanas du att ange en plats. Den här platsen är lagringsplatsen för dina resursgruppsmetadata och där dina resurser körs i Azure om du inte anger en annan region när du skapar resurser.

Skapa en resursgrupp genom att [anropa kommandot az group create][az-group-create] :

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export RESOURCE_GROUP="myResourceGroup$RANDOM_ID"
export LOCATION="centralindia"
az group create --name "${RESOURCE_GROUP}" --location "${LOCATION}"
```

Följande utdataexempel visar hur en resursgrupp har skapats:

Resultat:
<!-- expected_similarity=0.3 -->
```json
{
  "id": "/subscriptions/<guid>/resourceGroups/myResourceGroup",
  "location": "eastus",
  "managedBy": null,
  "name": "myResourceGroup",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Skapa ett AKS-kluster

Skapa ett AKS-kluster med [kommandot az aks create][az-aks-create] med parametern `--enable-oidc-issuer` för att aktivera OIDC-utfärdaren. I följande exempel skapas ett kluster med en enda nod:

```azurecli-interactive
export CLUSTER_NAME="myAKSCluster$RANDOM_ID"
az aks create \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity \
    --generate-ssh-keys
```

Efter några minuter slutförs kommandot och returnerar JSON-formaterad information om klustret.

> [!NOTE]
> När du skapar ett AKS-kluster skapas en andra resursgrupp automatiskt för att lagra AKS-resurserna. Mer information finns i [Varför skapas två resursgrupper med AKS?][aks-two-resource-groups].

## Uppdatera ett befintligt AKS-kluster

Du kan uppdatera ett AKS-kluster för att använda OIDC-utfärdaren och aktivera arbetsbelastningsidentitet genom att anropa [kommandot az aks update][az aks update] med parametrarna `--enable-workload-identity` `--enable-oidc-issuer` och . I följande exempel uppdateras ett befintligt kluster:

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity
```

## Hämta URL:en för OIDC-utfärdaren

Kör följande kommando för att hämta url:en för OIDC-utfärdaren och spara den i en miljövariabel:

```azurecli-interactive
export AKS_OIDC_ISSUER="$(az aks show --name "${CLUSTER_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --query "oidcIssuerProfile.issuerUrl" \
    --output tsv)"
```

Miljövariabeln bör innehålla utfärdarens URL, ungefär som i följande exempel:

```output
https://eastus.oic.prod-aks.azure.com/00000000-0000-0000-0000-000000000000/11111111-1111-1111-1111-111111111111/
```

Som standard är utfärdaren inställd på att använda bas-URL:en `https://{region}.oic.prod-aks.azure.com/{tenant_id}/{uuid}`, där värdet för `{region}` matchar platsen där AKS-klustret distribueras. Värdet `{uuid}` representerar OIDC-nyckeln, som är ett slumpmässigt genererat guid för varje kluster som inte kan ändras.

## Skapa en hanterad identitet

[Anropa kommandot az identity create][az-identity-create] för att skapa en hanterad identitet.

```azurecli-interactive
export SUBSCRIPTION="$(az account show --query id --output tsv)"
export USER_ASSIGNED_IDENTITY_NAME="myIdentity$RANDOM_ID"
az identity create \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --location "${LOCATION}" \
    --subscription "${SUBSCRIPTION}"
```

I följande utdataexempel visas hur en hanterad identitet har skapats:

Resultat:
<!-- expected_similarity=0.3 -->
```output
{
  "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourcegroups/myResourceGroupxxxxxx/providers/Microsoft.ManagedIdentity/userAssignedIdentities/myIdentityxxxxxx",
  "location": "centralindia",
  "name": "myIdentityxxxxxx",
  "principalId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "resourceGroup": "myResourceGroupxxxxxx",
  "systemData": null,
  "tags": {},
  "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "type": "Microsoft.ManagedIdentity/userAssignedIdentities"
}
```

Skapa sedan en variabel för den hanterade identitetens klient-ID.

```azurecli-interactive
export USER_ASSIGNED_CLIENT_ID="$(az identity show \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --query 'clientId' \
    --output tsv)"
```

## Skapa ett Kubernetes-tjänstkonto

Skapa ett Kubernetes-tjänstkonto och kommentera det med klient-ID:t för den hanterade identiteten som skapades i föregående steg. [Använd kommandot az aks get-credentials][az-aks-get-credentials] och ersätt värdena för klusternamnet och resursgruppens namn.

```azurecli-interactive
az aks get-credentials --name "${CLUSTER_NAME}" --resource-group "${RESOURCE_GROUP}"
```

Kopiera och klistra in följande indata med flera rader i Azure CLI.

```azurecli-interactive
export SERVICE_ACCOUNT_NAMESPACE="default"
export SERVICE_ACCOUNT_NAME="workload-identity-sa$RANDOM_ID"
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  annotations:
    azure.workload.identity/client-id: "${USER_ASSIGNED_CLIENT_ID}"
  name: "${SERVICE_ACCOUNT_NAME}"
  namespace: "${SERVICE_ACCOUNT_NAMESPACE}"
EOF
```

Följande utdata visar hur arbetsbelastningsidentiteten har skapats:

```output
serviceaccount/workload-identity-sa created
```

## Skapa federerade identitetsautentiseringsuppgifter

[Anropa kommandot az identity federated-credential create][az-identity-federated-credential-create] för att skapa den federerade identitetsautentiseringsuppgiften mellan den hanterade identiteten, utfärdaren av tjänstkontot och ämnet. Mer information om federerade identitetsuppgifter i Microsoft Entra [finns i Översikt över federerade identitetsautentiseringsuppgifter i Microsoft Entra-ID][federated-identity-credential].

```azurecli-interactive
export FEDERATED_IDENTITY_CREDENTIAL_NAME="myFedIdentity$RANDOM_ID"
az identity federated-credential create \
    --name ${FEDERATED_IDENTITY_CREDENTIAL_NAME} \
    --identity-name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --issuer "${AKS_OIDC_ISSUER}" \
    --subject system:serviceaccount:"${SERVICE_ACCOUNT_NAMESPACE}":"${SERVICE_ACCOUNT_NAME}" \
    --audience api://AzureADTokenExchange
```

> [!NOTE]
> Det tar några sekunder innan den federerade identitetsautentiseringsuppgiften sprids när den har lagts till. Om en tokenbegäran görs omedelbart efter att den federerade identitetsautentiseringsuppgiften har lagts till kan begäran misslyckas tills cachen har uppdaterats. För att undvika det här problemet kan du lägga till en liten fördröjning när du har lagt till den federerade identitetsautentiseringsuppgiften.

## Distribuera appen

När du distribuerar programpoddar bör manifestet referera till tjänstkontot som skapades i **steget Skapa Kubernetes-tjänstkonto** . Följande manifest visar hur du refererar till kontot, särskilt _egenskaperna metadata\namespace_ och _spec\serviceAccountName_ . Se till att ange en avbildning för `<image>` och ett containernamn för `<containerName>`:

```bash
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: sample-workload-identity
  namespace: ${SERVICE_ACCOUNT_NAMESPACE}  # Replace with your namespace
  labels:
    azure.workload.identity/use: "true"  # Required. Only pods with this label can use workload identity.
spec:
  serviceAccountName: ${SERVICE_ACCOUNT_NAME}  # Replace with your service account name
  containers:
    - name: rabbitmq  # Replace with your container name
      image: mcr.microsoft.com/mirror/docker/library/rabbitmq:3.10-management-alpine  # Replace with your Docker image
      ports:
        - containerPort: 5672
          name: rabbitmq-amqp
        - containerPort: 15672
          name: rabbitmq-http
      env:
        - name: RABBITMQ_DEFAULT_USER
          value: "username"
        - name: RABBITMQ_DEFAULT_PASS
          value: "password"
      resources:
        requests:
          cpu: 10m
          memory: 128Mi
        limits:
          cpu: 250m
          memory: 256Mi
EOF
```

> [!IMPORTANT]
> Kontrollera att de programpoddar som använder arbetsbelastningsidentiteten innehåller etiketten `azure.workload.identity/use: "true"` i poddspecifikationen. Annars misslyckas poddarna när de har startats om.

## Bevilja behörigheter för åtkomst till Azure Key Vault

Anvisningarna i det här steget visar hur du kommer åt hemligheter, nycklar eller certifikat i ett Azure-nyckelvalv från podden. Exemplen i det här avsnittet konfigurerar åtkomst till hemligheter i nyckelvalvet för arbetsbelastningsidentiteten, men du kan utföra liknande steg för att konfigurera åtkomst till nycklar eller certifikat.

I följande exempel visas hur du använder azure-behörighetsmodellen för rollbaserad åtkomstkontroll (Azure RBAC) för att ge podden åtkomst till nyckelvalvet. Mer information om Azure RBAC-behörighetsmodellen för Azure Key Vault finns i [Bevilja behörighet till program för åtkomst till ett Azure-nyckelvalv med Hjälp av Azure RBAC](/azure/key-vault/general/rbac-guide).

1. Skapa ett nyckelvalv med rensningsskydd och RBAC-auktorisering aktiverat. Du kan också använda ett befintligt nyckelvalv om det är konfigurerat för både rensningsskydd och RBAC-auktorisering:

    ```azurecli-interactive
    export KEYVAULT_NAME="keyvault-workload-id$RANDOM_ID"
    # Ensure the key vault name is between 3-24 characters
    if [ ${#KEYVAULT_NAME} -gt 24 ]; then
        KEYVAULT_NAME="${KEYVAULT_NAME:0:24}"
    fi
    az keyvault create \
        --name "${KEYVAULT_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --location "${LOCATION}" \
        --enable-purge-protection \
        --enable-rbac-authorization 
    ```

1. Tilldela dig rollen RBAC [Key Vault Secrets Officer](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-officer) så att du kan skapa en hemlighet i det nya nyckelvalvet:

    ```azurecli-interactive
    export KEYVAULT_RESOURCE_ID=$(az keyvault show --resource-group "${KEYVAULT_RESOURCE_GROUP}" \
        --name "${KEYVAULT_NAME}" \
        --query id \
        --output tsv)

    export CALLER_OBJECT_ID=$(az ad signed-in-user show --query objectId -o tsv)

    az role assignment create --assignee "${CALLER_OBJECT_ID}" \
    --role "Key Vault Secrets Officer" \
    --scope "${KEYVAULT_RESOURCE_ID}"
    ```

1. Skapa en hemlighet i nyckelvalvet:

    ```azurecli-interactive
    export KEYVAULT_SECRET_NAME="my-secret$RANDOM_ID"
    az keyvault secret set \
        --vault-name "${KEYVAULT_NAME}" \
        --name "${KEYVAULT_SECRET_NAME}" \
        --value "Hello\!"
    ```

1. [Tilldela rollen Key Vault Secrets User](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-user) till den användartilldelade hanterade identiteten som du skapade tidigare. Det här steget ger den hanterade identiteten behörighet att läsa hemligheter från nyckelvalvet:

    ```azurecli-interactive
    export IDENTITY_PRINCIPAL_ID=$(az identity show \
        --name "${USER_ASSIGNED_IDENTITY_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --query principalId \
        --output tsv)
    
    az role assignment create \
        --assignee-object-id "${IDENTITY_PRINCIPAL_ID}" \
        --role "Key Vault Secrets User" \
        --scope "${KEYVAULT_RESOURCE_ID}" \
        --assignee-principal-type ServicePrincipal
    ```

1. Skapa en miljövariabel för nyckelvalvs-URL:en:

    ```azurecli-interactive
    export KEYVAULT_URL="$(az keyvault show \
        --resource-group ${RESOURCE_GROUP} \
        --name ${KEYVAULT_NAME} \
        --query properties.vaultUri \
        --output tsv)"
    ```

1. Distribuera en podd som refererar till tjänstkontot och key vault-URL:en:

    ```bash
    cat <<EOF | kubectl apply -f -
    apiVersion: v1
    kind: Pod
    metadata:
    name: sample-workload-identity-key-vault
    namespace: ${SERVICE_ACCOUNT_NAMESPACE}
    labels:
        azure.workload.identity/use: "true"
    spec:
    serviceAccountName: ${SERVICE_ACCOUNT_NAME}
    containers:
        - image: ghcr.io/azure/azure-workload-identity/msal-go
        name: oidc
        env:
            - name: KEYVAULT_URL
            value: ${KEYVAULT_URL}
            - name: SECRET_NAME
            value: ${KEYVAULT_SECRET_NAME}
    nodeSelector:
        kubernetes.io/os: linux
    EOF
    ```

Om du vill kontrollera om alla egenskaper matas in korrekt av webhooken använder du [kommandot kubectl describe][kubectl-describe] :

```azurecli-interactive
kubectl describe pod sample-workload-identity-key-vault | grep "SECRET_NAME:"
```

Om det lyckas bör utdata se ut ungefär så här:

```output
      SECRET_NAME:                 ${KEYVAULT_SECRET_NAME}
```

Om du vill kontrollera att podden kan hämta en token och komma åt resursen använder du kommandot kubectl logs:

```azurecli-interactive
kubectl logs sample-workload-identity-key-vault
```

Om det lyckas bör utdata se ut ungefär så här:

```output
I0114 10:35:09.795900       1 main.go:63] "successfully got secret" secret="Hello\\!"
```

> [!IMPORTANT]
> Azure RBAC-rolltilldelningar kan ta upp till tio minuter att sprida. Om podden inte kan komma åt hemligheten kan du behöva vänta tills rolltilldelningen sprids. Mer information finns i [Felsöka Azure RBAC](/azure/role-based-access-control/troubleshooting#).

## Inaktivera arbetsbelastningsidentitet

Om du vill inaktivera Microsoft Entra-arbetsbelastnings-ID:t i AKS-klustret där det har aktiverats och konfigurerats kan du köra följande kommando:

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --disable-workload-identity
```

## Nästa steg

I den här artikeln distribuerade du ett Kubernetes-kluster och konfigurerade det att använda en arbetsbelastningsidentitet inför programarbetsbelastningar för att autentisera med den autentiseringsuppgiften. Nu är du redo att distribuera ditt program och konfigurera det så att det använder arbetsbelastningsidentiteten med den senaste versionen av [Azure Identity-klientbiblioteket][azure-identity-libraries] . Om du inte kan skriva om programmet för att använda den senaste klientbiblioteksversionen kan [du konfigurera programpodden att autentisera][workload-identity-migration] med hanterad identitet med arbetsbelastningsidentitet som en kortsiktig migreringslösning.

Integreringen [av Service Connector](/azure/service-connector/overview) förenklar anslutningskonfigurationen för AKS-arbetsbelastningar och Azure-säkerhetskopieringstjänster. Den hanterar autentisering och nätverkskonfigurationer på ett säkert sätt och följer metodtipsen för att ansluta till Azure-tjänster. Mer information [finns i Ansluta till Azure OpenAI-tjänsten i AKS med hjälp av arbetsbelastningsidentitet](/azure/service-connector/tutorial-python-aks-openai-workload-identity) och introduktionen[ till ](https://azure.github.io/AKS/2024/05/23/service-connector-intro)Service Connector.

<!-- EXTERNAL LINKS -->
[kubectl-describe]: https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#describe

<!-- INTERNAL LINKS -->
[kubernetes-concepts]: concepts-clusters-workloads.md
[workload-identity-overview]: workload-identity-overview.md
[azure-resource-group]: /azure/azure-resource-manager/management/overview
[az-group-create]: /cli/azure/group#az-group-create
[aks-identity-concepts]: concepts-identity.md
[federated-identity-credential]: /graph/api/resources/federatedidentitycredentials-overview
[tutorial-python-aks-storage-workload-identity]: /azure/service-connector/tutorial-python-aks-storage-workload-identity
[az-aks-create]: /cli/azure/aks#az-aks-create
[az aks update]: /cli/azure/aks#az-aks-update
[aks-two-resource-groups]: faq.yml
[az-account-set]: /cli/azure/account#az-account-set
[az-identity-create]: /cli/azure/identity#az-identity-create
[az-aks-get-credentials]: /cli/azure/aks#az-aks-get-credentials
[az-identity-federated-credential-create]: /cli/azure/identity/federated-credential#az-identity-federated-credential-create
[workload-identity-migration]: workload-identity-migrate-from-pod-identity.md
[azure-identity-libraries]: /azure/active-directory/develop/reference-v2-libraries