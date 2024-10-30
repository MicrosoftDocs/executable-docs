---
title: AKS-fürt üzembe helyezése és konfigurálása számítási feladat identitásával
description: 'Ebben az Azure Kubernetes Service(AKS)-cikkben üzembe helyezhet egy Azure Kubernetes Service-fürtöt, és konfigurálhatja egy Microsoft Entra Számítási feladat ID.'
author: tamram
ms.topic: article
ms.subservice: aks-security
ms.custom: devx-track-azurecli
ms.date: 05/28/2024
ms.author: tamram
---

# Számítási feladatok identitásának üzembe helyezése és konfigurálása Egy Azure Kubernetes Service-fürtön

Az Azure Kubernetes Service (AKS) egy felügyelt Kubernetes-szolgáltatás, amely lehetővé teszi a Kubernetes-fürtök gyors üzembe helyezését és kezelését. Ez a cikk bemutatja, hogyan:

* AKS-fürt üzembe helyezése az Azure CLI használatával az OpenID Connect-kiállítóval és egy Microsoft Entra Számítási feladat ID.
* Hozzon létre egy Microsoft Entra Számítási feladat ID és Egy Kubernetes-szolgáltatásfiókot.
* Konfigurálja a felügyelt identitást a jogkivonat-összevonáshoz.
* Telepítse a számítási feladatot, és ellenőrizze a hitelesítést a számítási feladat identitásával.
* Ha szeretné, a fürt egyik podjának hozzáférést adhat egy Azure-kulcstartó titkos kulcsaihoz.

Ez a cikk feltételezi, hogy alapszintű ismereteket szerzett a Kubernetes-fogalmakról. További információkért tekintse meg [az Azure Kubernetes Service (AKS)][kubernetes-concepts] Kubernetes alapfogalmait. Ha nem ismeri a Microsoft Entra Számítási feladat ID, tekintse meg az alábbi [Áttekintés][workload-identity-overview] cikket.

## Előfeltételek

* [!INCLUDE [quickstarts-free-trial-note](~/reusable-content/ce-skilling/azure/includes/quickstarts-free-trial-note.md)]
* Ez a cikk az Azure CLI 2.47.0-s vagy újabb verzióját igényli. Az Azure Cloud Shell használata esetén a legújabb verzió már telepítve van.
* Győződjön meg arról, hogy a fürt létrehozásához használt identitás rendelkezik a megfelelő minimális engedélyekkel. Az AKS-hez való hozzáféréssel és identitással kapcsolatos további információkért lásd [az Azure Kubernetes Service (AKS)][aks-identity-concepts] hozzáférési és identitásbeállításait.
* Ha több Azure-előfizetéssel rendelkezik, válassza ki a megfelelő előfizetés-azonosítót, amelyben az erőforrásokat az [az account set][az-account-set] paranccsal kell számlázni.

> [!NOTE]
> A Service Connector_ segítségével _automatikusan konfigurálhat néhány lépést. Lásd még: Oktatóanyag: [Csatlakozás azure-tárfiókhoz az Azure Kubernetes Service-ben (AKS) a Service Connector használatával számítási feladat identitásával][tutorial-python-aks-storage-workload-identity].

## Erőforráscsoport létrehozása

Az [Azure-erőforráscsoportok][azure-resource-group] olyan logikai csoportok, amelyekben az Azure-erőforrások üzembe helyezése és kezelése történik. Erőforráscsoport létrehozásakor a rendszer kérni fogja, hogy adjon meg egy helyet. Ez a hely az erőforráscsoport metaadatainak tárolási helye, és ahol az erőforrások az Azure-ban futnak, ha nem ad meg egy másik régiót az erőforrás létrehozása során.

Hozzon létre egy erőforráscsoportot az [az group create][az-group-create] parancs meghívásával:

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export RESOURCE_GROUP="myResourceGroup$RANDOM_ID"
export LOCATION="centralindia"
az group create --name "${RESOURCE_GROUP}" --location "${LOCATION}"
```

Az alábbi kimeneti példa egy erőforráscsoport sikeres létrehozását mutatja be:

Eredmények:
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

## AKS-fürt létrehozása

Hozzon létre egy AKS-fürtöt az az aks [create][az-aks-create] paranccsal a paraméterrel az `--enable-oidc-issuer` OIDC-kiállító engedélyezéséhez. Az alábbi példa egyetlen csomóponttal rendelkező fürtöt hoz létre:

```azurecli-interactive
export CLUSTER_NAME="myAKSCluster$RANDOM_ID"
az aks create \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity \
    --generate-ssh-keys
```

Néhány perc elteltével a parancs befejeződik, és JSON formátumú információkat ad vissza a fürtről.

> [!NOTE]
> AKS-fürt létrehozásakor a rendszer automatikusan létrehoz egy második erőforráscsoportot az AKS-erőforrások tárolásához. További információ: [Miért jön létre két erőforráscsoport az AKS-sel?][aks-two-resource-groups]

## Meglévő AKS-fürt frissítése

Az AKS-fürtöket frissítheti az OIDC-kiállító használatára, és engedélyezheti a számítási feladatok identitását az az aks [update][az aks update] parancs és a `--enable-workload-identity` `--enable-oidc-issuer` paraméterek meghívásával. Az alábbi példa egy meglévő fürtöt frissít:

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity
```

## Az OIDC-kiállító URL-címének lekérése

Az OIDC-kiállító URL-címének lekéréséhez és egy környezeti változóba való mentéséhez futtassa a következő parancsot:

```azurecli-interactive
export AKS_OIDC_ISSUER="$(az aks show --name "${CLUSTER_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --query "oidcIssuerProfile.issuerUrl" \
    --output tsv)"
```

A környezeti változónak tartalmaznia kell a kiállító URL-címét az alábbi példához hasonlóan:

```output
https://eastus.oic.prod-aks.azure.com/00000000-0000-0000-0000-000000000000/11111111-1111-1111-1111-111111111111/
```

Alapértelmezés szerint a kiállító az alap URL-címet `https://{region}.oic.prod-aks.azure.com/{tenant_id}/{uuid}`használja, ahol az érték `{region}` megegyezik az AKS-fürt üzembe helyezésének helyével. Az érték `{uuid}` az OIDC-kulcsot jelöli, amely véletlenszerűen generált guid minden egyes nem módosítható fürthöz.

## Felügyelt identitás létrehozása

A felügyelt identitás létrehozásához hívja meg az [az identity create][az-identity-create] parancsot.

```azurecli-interactive
export SUBSCRIPTION="$(az account show --query id --output tsv)"
export USER_ASSIGNED_IDENTITY_NAME="myIdentity$RANDOM_ID"
az identity create \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --location "${LOCATION}" \
    --subscription "${SUBSCRIPTION}"
```

Az alábbi kimeneti példa egy felügyelt identitás sikeres létrehozását mutatja be:

Eredmények:
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

Ezután hozzon létre egy változót a felügyelt identitás ügyfélazonosítójának.

```azurecli-interactive
export USER_ASSIGNED_CLIENT_ID="$(az identity show \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --query 'clientId' \
    --output tsv)"
```

## Kubernetes-szolgáltatásfiók létrehozása

Hozzon létre egy Kubernetes-szolgáltatásfiókot, és jegyzetelje meg az előző lépésben létrehozott felügyelt identitás ügyfélazonosítójával. Használja az az aks [get-credentials parancsot][az-aks-get-credentials] , és cserélje le a fürt nevének és az erőforráscsoport nevének értékeit.

```azurecli-interactive
az aks get-credentials --name "${CLUSTER_NAME}" --resource-group "${RESOURCE_GROUP}"
```

Másolja és illessze be a következő többsoros bemenetet az Azure CLI-ben.

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

Az alábbi kimenet a számítási feladat identitásának sikeres létrehozását mutatja be:

```output
serviceaccount/workload-identity-sa created
```

## Az összevont identitás hitelesítő adatainak létrehozása

Hívja meg az [az identity federated-credential create][az-identity-federated-credential-create] parancsot az összevont identitás hitelesítő adatainak létrehozásához a felügyelt identitás, a szolgáltatásfiók kiállítója és a tulajdonos között. A Microsoft Entra összevont identitás-hitelesítő adatairól további információt a Microsoft Entra-azonosítóban[ található összevont identitás hitelesítő adatainak áttekintése című témakörben talál][federated-identity-credential].

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
> Az összevont identitás hitelesítő adatainak propagálása a hozzáadás után néhány másodpercet vesz igénybe. Ha a jogkivonat-kérés közvetlenül az összevont identitás hitelesítő adatainak hozzáadása után történik, a kérés meghiúsulhat a gyorsítótár frissítéséig. A probléma elkerülése érdekében az összevont identitás hitelesítő adatainak hozzáadása után némi késést adhat hozzá.

## Az alkalmazás üzembe helyezése

Az alkalmazás podok telepítésekor a jegyzéknek hivatkoznia kell a **Kubernetes-szolgáltatásfiók létrehozása lépésben létrehozott szolgáltatásfiókra** . Az alábbi jegyzék bemutatja, hogyan hivatkozhat a fiókra, különösen a metaadatok\névtér_ és _a _spec\serviceAccountName_ tulajdonságokra. Mindenképpen adjon meg egy lemezképet `<image>` és egy tárolónevet a következőhöz `<containerName>`:

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
> Győződjön meg arról, hogy a számítási feladat identitását használó alkalmazás podjai tartalmazzák a pod specifikációjában szereplő címkét `azure.workload.identity/use: "true"` . Ellenkező esetben a podok újraindításuk után sikertelenek lesznek.

## Engedélyek megadása az Azure Key Vault eléréséhez

Az ebben a lépésben ismertetett utasítások bemutatják, hogyan férhet hozzá titkos kulcsokhoz, kulcsokhoz vagy tanúsítványokhoz egy Azure-kulcstartóban a podról. Az ebben a szakaszban szereplő példák a számítási feladat identitásának kulcstartójában lévő titkos kulcsokhoz való hozzáférést konfigurálják, de hasonló lépéseket hajthat végre a kulcsokhoz vagy tanúsítványokhoz való hozzáférés konfigurálásához.

Az alábbi példa bemutatja, hogyan használhatja az Azure szerepköralapú hozzáférés-vezérlési (Azure RBAC) engedélymodellt a pod hozzáférésének a kulcstartóhoz való biztosításához. Az Azure Key VaultHoz készült Azure RBAC-engedélymodellről további információt az Azure RBAC-t[ használó Azure-kulcstartók elérésére vonatkozó alkalmazások engedélyének megadása című témakörben talál](/azure/key-vault/general/rbac-guide).

1. Hozzon létre egy kulcstartót, amelyen engedélyezve van a törlés elleni védelem és az RBAC-engedélyezés. Meglévő kulcstartót akkor is használhat, ha a törlés elleni védelemhez és az RBAC-engedélyezéshez is konfigurálva van:

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

1. Rendelje hozzá saját magának az RBAC [Key Vault titkos kulcstartó-tisztviselői](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-officer) szerepkört, hogy létrehozhasson egy titkos kulcsot az új kulcstartóban:

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

1. Hozzon létre egy titkos kulcsot a kulcstartóban:

    ```azurecli-interactive
    export KEYVAULT_SECRET_NAME="my-secret$RANDOM_ID"
    az keyvault secret set \
        --vault-name "${KEYVAULT_NAME}" \
        --name "${KEYVAULT_SECRET_NAME}" \
        --value "Hello\!"
    ```

1. Rendelje hozzá a [Key Vault titkos kulcsfelhasználói](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-user) szerepkörét a korábban létrehozott, felhasználó által hozzárendelt felügyelt identitáshoz. Ez a lépés engedélyezi a felügyelt identitásnak, hogy titkos kulcsokat olvasson be a kulcstartóból:

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

1. Hozzon létre egy környezeti változót a Key Vault URL-címéhez:

    ```azurecli-interactive
    export KEYVAULT_URL="$(az keyvault show \
        --resource-group ${RESOURCE_GROUP} \
        --name ${KEYVAULT_NAME} \
        --query properties.vaultUri \
        --output tsv)"
    ```

1. Helyezzen üzembe egy podot, amely a szolgáltatásfiókra és a key vault URL-címére hivatkozik:

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

Annak ellenőrzéséhez, hogy a webhook megfelelően injektálja-e az összes tulajdonságot, használja a [kubectl leíró][kubectl-describe] parancsot:

```azurecli-interactive
kubectl describe pod sample-workload-identity-key-vault | grep "SECRET_NAME:"
```

Ha sikeres, a kimenetnek a következőhöz hasonlónak kell lennie:

```output
      SECRET_NAME:                 ${KEYVAULT_SECRET_NAME}
```

Annak ellenőrzéséhez, hogy a pod képes-e jogkivonatot lekérni és hozzáférni az erőforráshoz, használja a kubectl logs parancsot:

```azurecli-interactive
kubectl logs sample-workload-identity-key-vault
```

Ha sikeres, a kimenetnek a következőhöz hasonlónak kell lennie:

```output
I0114 10:35:09.795900       1 main.go:63] "successfully got secret" secret="Hello\\!"
```

> [!IMPORTANT]
> Az Azure RBAC-szerepkör-hozzárendelések propagálása akár tíz percet is igénybe vehet. Ha a pod nem tudja elérni a titkos kulcsot, előfordulhat, hogy várnia kell a szerepkör-hozzárendelés propagálására. További információ: [Az Azure RBAC](/azure/role-based-access-control/troubleshooting#) hibaelhárítása.

## Számítási feladatok identitásának letiltása

Ha le szeretné tiltani a Microsoft Entra Számítási feladat ID azon az AKS-fürtön, ahol engedélyezve és konfigurálva van, futtassa a következő parancsot:

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --disable-workload-identity
```

## Következő lépések

Ebben a cikkben üzembe helyezett egy Kubernetes-fürtöt, és konfigurálta egy számítási feladat identitásának használatára az alkalmazás számítási feladatainak előkészítéséhez a hitelesítő adatokkal való hitelesítéshez. Most már készen áll az alkalmazás üzembe helyezésére és konfigurálására, hogy a számítási feladat identitását [az Azure Identity][azure-identity-libraries] ügyfélkódtár legújabb verziójával használja. Ha nem tudja átírni az alkalmazást a legújabb ügyfélkódtár-verzió használatára, [beállíthatja az alkalmazás podját][workload-identity-migration] a felügyelt identitás és a számítási feladat identitásának rövid távú migrálási megoldásként történő hitelesítésére.

A [Service Connector](/azure/service-connector/overview) integrációja leegyszerűsíti az AKS-számítási feladatok és az Azure-háttérszolgáltatások kapcsolatkonfigurációját. Biztonságosan kezeli a hitelesítést és a hálózati konfigurációkat, és követi az Azure-szolgáltatásokhoz való csatlakozás ajánlott eljárásait. További információ: [Csatlakozás az Azure OpenAI szolgáltatáshoz az AKS-ben a Számítási feladatok identitása](/azure/service-connector/tutorial-python-aks-openai-workload-identity) és a [Szolgáltatás-összekötő bemutatása című témakörben](https://azure.github.io/AKS/2024/05/23/service-connector-intro).

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