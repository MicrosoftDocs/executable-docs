---
title: Wdrażanie i konfigurowanie klastra usługi AKS przy użyciu tożsamości obciążenia
description: W tym artykule dotyczącym usługi Azure Kubernetes Service (AKS) wdrożysz klaster usługi Azure Kubernetes Service i skonfigurujesz go przy użyciu Tożsamość obciążeń Microsoft Entra.
author: tamram
ms.topic: article
ms.subservice: aks-security
ms.custom: devx-track-azurecli
ms.date: 05/28/2024
ms.author: tamram
---

# Wdrażanie i konfigurowanie tożsamości obciążenia w klastrze usługi Azure Kubernetes Service (AKS)

Azure Kubernetes Service (AKS) to zarządzana usługa Kubernetes, która umożliwia szybkie wdrażanie klastrów Kubernetes i zarządzanie nimi. W tym artykule pokazano, w jaki sposób wykonać następujące czynności:

* Wdróż klaster usługi AKS przy użyciu interfejsu wiersza polecenia platformy Azure za pomocą wystawcy OpenID Connect i Tożsamość obciążeń Microsoft Entra.
* Utwórz konto usługi Tożsamość obciążeń Microsoft Entra i Kubernetes Service.
* Skonfiguruj tożsamość zarządzaną na potrzeby federacji tokenów.
* Wdróż obciążenie i zweryfikuj uwierzytelnianie przy użyciu tożsamości obciążenia.
* Opcjonalnie przyznaj zasobnikowi w klastrze dostęp do wpisów tajnych w magazynie kluczy platformy Azure.

W tym artykule założono, że masz podstawową wiedzę na temat pojęć związanych z platformą Kubernetes. Aby uzyskać więcej informacji, zobacz temat [Kubernetes core concepts for Azure Kubernetes Service (AKS)][kubernetes-concepts] (Kubernetes — podstawowe pojęcia dotyczące usługi Azure Kubernetes Service (AKS)). Jeśli nie znasz Tożsamość obciążeń Microsoft Entra, zapoznaj się z następującym [artykułem Omówienie][workload-identity-overview].

## Wymagania wstępne

* [!INCLUDE [quickstarts-free-trial-note](~/reusable-content/ce-skilling/azure/includes/quickstarts-free-trial-note.md)]
* Ten artykuł wymaga wersji 2.47.0 lub nowszej interfejsu wiersza polecenia platformy Azure. W przypadku korzystania z usługi Azure Cloud Shell najnowsza wersja jest już zainstalowana.
* Upewnij się, że tożsamość używana do utworzenia klastra ma odpowiednie minimalne uprawnienia. Aby uzyskać więcej informacji na temat dostępu i tożsamości dla usługi AKS, zobacz [Opcje dostępu i tożsamości dla usługi Azure Kubernetes Service (AKS).][aks-identity-concepts]
* Jeśli masz wiele subskrypcji platformy Azure, wybierz odpowiedni identyfikator subskrypcji, w którym mają być rozliczane zasoby przy użyciu [polecenia az account set][az-account-set] .

> [!NOTE]
> Możesz użyć _łącznika_ usługi, aby ułatwić automatyczne konfigurowanie niektórych kroków. Zobacz również: Samouczek: [nawiązywanie połączenia z kontem usługi Azure Storage w usłudze Azure Kubernetes Service (AKS) przy użyciu łącznika usługi przy użyciu tożsamości][tutorial-python-aks-storage-workload-identity] obciążenia.

## Tworzenie grupy zasobów

[Grupa][azure-resource-group] zasobów platformy Azure to grupa logiczna, w której zasoby platformy Azure są wdrażane i zarządzane. Podczas tworzenia grupy zasobów zostanie wyświetlony monit o określenie lokalizacji. Ta lokalizacja to lokalizacja magazynu metadanych grupy zasobów i lokalizacja, w której zasoby są uruchamiane na platformie Azure, jeśli nie określisz innego regionu podczas tworzenia zasobów.

Utwórz grupę zasobów, wywołując [polecenie az group create][az-group-create] :

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export RESOURCE_GROUP="myResourceGroup$RANDOM_ID"
export LOCATION="centralindia"
az group create --name "${RESOURCE_GROUP}" --location "${LOCATION}"
```

Poniższy przykład danych wyjściowych przedstawia pomyślne utworzenie grupy zasobów:

Wyniki:
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

## Tworzenie klastra AKS

Utwórz klaster usługi AKS przy użyciu [polecenia az aks create][az-aks-create] z parametrem `--enable-oidc-issuer` , aby włączyć wystawcę OIDC. Poniższy przykład tworzy klaster z jednym węzłem:

```azurecli-interactive
export CLUSTER_NAME="myAKSCluster$RANDOM_ID"
az aks create \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity \
    --generate-ssh-keys
```

Po kilku minutach polecenie zostanie wykonane i zwróci informacje o klastrze w formacie JSON.

> [!NOTE]
> Podczas tworzenia klastra usługi AKS druga grupa zasobów jest tworzona automatycznie w celu przechowywania zasobów usługi AKS. Aby uzyskać więcej informacji, zobacz [Dlaczego dwie grupy zasobów są tworzone za pomocą usługi AKS?][aks-two-resource-groups].

## Aktualizowanie istniejącego klastra usługi AKS

Klaster usługi AKS można zaktualizować, aby używał wystawcy OIDC i włączyć tożsamość obciążenia, wywołując [polecenie az aks update][az aks update] za pomocą parametrów `--enable-workload-identity` `--enable-oidc-issuer` i . Poniższy przykład aktualizuje istniejący klaster:

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity
```

## Pobieranie adresu URL wystawcy OIDC

Aby uzyskać adres URL wystawcy OIDC i zapisać go w zmiennej środowiskowej, uruchom następujące polecenie:

```azurecli-interactive
export AKS_OIDC_ISSUER="$(az aks show --name "${CLUSTER_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --query "oidcIssuerProfile.issuerUrl" \
    --output tsv)"
```

Zmienna środowiskowa powinna zawierać adres URL wystawcy podobny do następującego przykładu:

```output
https://eastus.oic.prod-aks.azure.com/00000000-0000-0000-0000-000000000000/11111111-1111-1111-1111-111111111111/
```

Domyślnie wystawca jest ustawiony tak, aby używał podstawowego adresu URL `https://{region}.oic.prod-aks.azure.com/{tenant_id}/{uuid}`, gdzie wartość parametru `{region}` jest zgodna z lokalizacją, do której wdrożony jest klaster usługi AKS. Wartość `{uuid}` reprezentuje klucz OIDC, który jest losowo generowany identyfikator GUID dla każdego klastra, który jest niezmienny.

## Tworzenie tożsamości zarządzanej

Wywołaj [polecenie az identity create][az-identity-create] , aby utworzyć tożsamość zarządzaną.

```azurecli-interactive
export SUBSCRIPTION="$(az account show --query id --output tsv)"
export USER_ASSIGNED_IDENTITY_NAME="myIdentity$RANDOM_ID"
az identity create \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --location "${LOCATION}" \
    --subscription "${SUBSCRIPTION}"
```

Poniższy przykład danych wyjściowych przedstawia pomyślne utworzenie tożsamości zarządzanej:

Wyniki:
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

Następnie utwórz zmienną dla identyfikatora klienta tożsamości zarządzanej.

```azurecli-interactive
export USER_ASSIGNED_CLIENT_ID="$(az identity show \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --query 'clientId' \
    --output tsv)"
```

## Tworzenie konta usługi Kubernetes

Utwórz konto usługi Kubernetes i dodaj do niego adnotację przy użyciu identyfikatora klienta tożsamości zarządzanej utworzonej w poprzednim kroku. [Użyj polecenia az aks get-credentials][az-aks-get-credentials] i zastąp wartości nazwy klastra i nazwy grupy zasobów.

```azurecli-interactive
az aks get-credentials --name "${CLUSTER_NAME}" --resource-group "${RESOURCE_GROUP}"
```

Skopiuj i wklej następujące dane wejściowe wielowierszowe w interfejsie wiersza polecenia platformy Azure.

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

Następujące dane wyjściowe pokazują pomyślne utworzenie tożsamości obciążenia:

```output
serviceaccount/workload-identity-sa created
```

## Tworzenie poświadczeń tożsamości federacyjnej

Wywołaj [polecenie az identity federated-credential create][az-identity-federated-credential-create] , aby utworzyć poświadczenia tożsamości federacyjnej między tożsamością zarządzaną, wystawcą konta usługi i tematem. Aby uzyskać więcej informacji na temat poświadczeń tożsamości federacyjnej w usłudze Microsoft Entra, zobacz [Overview of federated identity credentials in Microsoft Entra ID (Omówienie poświadczeń tożsamości federacyjnej w usłudze Microsoft Entra ID][federated-identity-credential]).

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
> Propagacja po dodaniu poświadczeń tożsamości federacyjnej trwa kilka sekund. Jeśli żądanie tokenu zostanie wykonane natychmiast po dodaniu poświadczeń tożsamości federacyjnej, żądanie może zakończyć się niepowodzeniem do czasu odświeżenia pamięci podręcznej. Aby uniknąć tego problemu, możesz dodać niewielkie opóźnienie po dodaniu poświadczeń tożsamości federacyjnej.

## Wdrażanie aplikacji

Podczas wdrażania zasobników aplikacji manifest powinien odwoływać się do konta usługi utworzonego **w kroku Tworzenie konta** usługi Kubernetes Service. Poniższy manifest pokazuje, jak odwoływać się do konta, w szczególności _właściwości metadata\namespace_ i _spec\serviceAccountName_ . Upewnij się, że określono obraz dla `<image>` parametru i nazwę kontenera dla `<containerName>`elementu :

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
> Upewnij się, że zasobniki aplikacji korzystające z tożsamości obciążenia zawierają etykietę `azure.workload.identity/use: "true"` w specyfikacji zasobnika. W przeciwnym razie zasobniki nie będą działać po ponownym uruchomieniu.

## Udzielanie uprawnień dostępu do usługi Azure Key Vault

Instrukcje w tym kroku pokazują, jak uzyskać dostęp do wpisów tajnych, kluczy lub certyfikatów w magazynie kluczy platformy Azure z zasobnika. Przykłady w tej sekcji umożliwiają skonfigurowanie dostępu do wpisów tajnych w magazynie kluczy dla tożsamości obciążenia, ale możesz wykonać podobne kroki, aby skonfigurować dostęp do kluczy lub certyfikatów.

W poniższym przykładzie pokazano, jak używać modelu uprawnień kontroli dostępu na podstawie ról (RBAC) platformy Azure w celu udzielenia zasobnikowi dostępu do magazynu kluczy. Aby uzyskać więcej informacji na temat modelu uprawnień RBAC platformy Azure dla usługi Azure Key Vault, zobacz [Udzielanie aplikacji uprawnień dostępu do magazynu kluczy platformy Azure przy użyciu kontroli dostępu opartej na rolach](/azure/key-vault/general/rbac-guide) platformy Azure.

1. Utwórz magazyn kluczy z włączoną ochroną przeczyszczania i autoryzacją RBAC. Możesz również użyć istniejącego magazynu kluczy, jeśli jest skonfigurowany do ochrony przed przeczyszczeniem i autoryzacji RBAC:

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

1. Przypisz sobie rolę RBAC [Key Vault Secrets Officer](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-officer) , aby można było utworzyć wpis tajny w nowym magazynie kluczy:

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

1. Utwórz wpis tajny w magazynie kluczy:

    ```azurecli-interactive
    export KEYVAULT_SECRET_NAME="my-secret$RANDOM_ID"
    az keyvault secret set \
        --vault-name "${KEYVAULT_NAME}" \
        --name "${KEYVAULT_SECRET_NAME}" \
        --value "Hello\!"
    ```

1. [Przypisz rolę Użytkownika](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-user) wpisów tajnych usługi Key Vault do utworzonej wcześniej tożsamości zarządzanej przypisanej przez użytkownika. Ten krok zapewnia uprawnienie tożsamości zarządzanej do odczytywania wpisów tajnych z magazynu kluczy:

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

1. Utwórz zmienną środowiskową dla adresu URL magazynu kluczy:

    ```azurecli-interactive
    export KEYVAULT_URL="$(az keyvault show \
        --resource-group ${RESOURCE_GROUP} \
        --name ${KEYVAULT_NAME} \
        --query properties.vaultUri \
        --output tsv)"
    ```

1. Wdróż zasobnik, który odwołuje się do konta usługi i adresu URL magazynu kluczy:

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

Aby sprawdzić, czy wszystkie właściwości są prawidłowo wstrzykiwane przez element webhook, użyj [polecenia kubectl describe][kubectl-describe] :

```azurecli-interactive
kubectl describe pod sample-workload-identity-key-vault | grep "SECRET_NAME:"
```

W przypadku powodzenia dane wyjściowe powinny być podobne do następujących:

```output
      SECRET_NAME:                 ${KEYVAULT_SECRET_NAME}
```

Aby sprawdzić, czy zasobnik może uzyskać token i uzyskać dostęp do zasobu, użyj polecenia kubectl logs:

```azurecli-interactive
kubectl logs sample-workload-identity-key-vault
```

W przypadku powodzenia dane wyjściowe powinny być podobne do następujących:

```output
I0114 10:35:09.795900       1 main.go:63] "successfully got secret" secret="Hello\\!"
```

> [!IMPORTANT]
> Propagacja przypisań ról RBAC platformy Azure może potrwać do dziesięciu minut. Jeśli zasobnik nie może uzyskać dostępu do wpisu tajnego, może być konieczne poczekanie na propagację przypisania roli. Aby uzyskać więcej informacji, zobacz Rozwiązywanie problemów z kontrolą dostępu opartą na[ rolach ](/azure/role-based-access-control/troubleshooting#)platformy Azure.

## Wyłączanie tożsamości obciążenia

Aby wyłączyć Tożsamość obciążeń Microsoft Entra w klastrze usługi AKS, w którym została włączona i skonfigurowana, możesz uruchomić następujące polecenie:

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --disable-workload-identity
```

## Następne kroki

W tym artykule wdrożono klaster Kubernetes i skonfigurowano go do używania tożsamości obciążenia w ramach przygotowań do uwierzytelniania obciążeń aplikacji przy użyciu tego poświadczenia. Teraz możesz przystąpić do wdrażania aplikacji i konfigurować ją tak, aby korzystała z tożsamości obciążenia z najnowszą wersją [biblioteki klienta usługi Azure Identity][azure-identity-libraries] . Jeśli nie możesz ponownie napisać aplikacji w celu korzystania z najnowszej wersji biblioteki klienta, możesz skonfigurować [zasobnik][workload-identity-migration] aplikacji do uwierzytelniania przy użyciu tożsamości zarządzanej z tożsamością obciążenia jako rozwiązaniem do migracji krótkoterminowej.

[Integracja łącznika](/azure/service-connector/overview) usług pomaga uprościć konfigurację połączenia dla obciążeń usługi AKS i usług zaplecza platformy Azure. Bezpiecznie obsługuje konfiguracje uwierzytelniania i sieci oraz postępuje zgodnie z najlepszymi rozwiązaniami dotyczącymi nawiązywania połączenia z usługami platformy Azure. Aby uzyskać więcej informacji, zobacz [Connect to Azure OpenAI Service in AKS using Workload Identity and the Service Connector introduction (Nawiązywanie połączenia z usługą Azure OpenAI w usłudze AKS przy użyciu tożsamości](/azure/service-connector/tutorial-python-aks-openai-workload-identity) obciążenia i wprowadzenie[ do łącznika ](https://azure.github.io/AKS/2024/05/23/service-connector-intro)usługi).

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