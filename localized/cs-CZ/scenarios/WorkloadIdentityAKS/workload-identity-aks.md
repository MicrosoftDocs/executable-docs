---
title: Nasazení a konfigurace clusteru AKS s identitou úloh
description: V tomto článku o službě Azure Kubernetes Service (AKS) nasadíte cluster Azure Kubernetes Service a nakonfigurujete ho pomocí ID úloh Microsoft Entra.
author: tamram
ms.topic: article
ms.subservice: aks-security
ms.custom: devx-track-azurecli
ms.date: 05/28/2024
ms.author: tamram
---

# Nasazení a konfigurace identity úloh v clusteru Azure Kubernetes Service (AKS)

Azure Kubernetes Service (AKS) je spravovaná služba Kubernetes, která umožňuje rychle nasazovat a spravovat clustery Kubernetes. V tomto článku se dozvíte, jak:

* Nasaďte cluster AKS pomocí Azure CLI s vystavitelem OpenID Connect a ID úloh Microsoft Entra.
* Vytvořte ID úloh Microsoft Entra a účet služby Kubernetes.
* Nakonfigurujte spravovanou identitu pro federaci tokenů.
* Nasaďte úlohu a ověřte ověřování pomocí identity úlohy.
* Volitelně můžete podu v clusteru udělit přístup k tajným kódům v trezoru klíčů Azure.

Tento článek předpokládá, že máte základní znalosti konceptů Kubernetes. Další informace najdete v tématu [Základní koncepty Kubernetes pro Službu Azure Kubernetes Service (AKS).][kubernetes-concepts] Pokud ID úloh Microsoft Entra neznáte, přečtěte si následující [článek s přehledem][workload-identity-overview].

## Požadavky

* [!INCLUDE [quickstarts-free-trial-note](~/reusable-content/ce-skilling/azure/includes/quickstarts-free-trial-note.md)]
* Tento článek vyžaduje verzi 2.47.0 nebo novější azure CLI. Pokud používáte Azure Cloud Shell, je už nainstalovaná nejnovější verze.
* Ujistěte se, že identita, kterou používáte k vytvoření clusteru, má odpovídající minimální oprávnění. Další informace o přístupu a identitě pro AKS najdete v tématu [Možnosti přístupu a identit pro Službu Azure Kubernetes Service (AKS).][aks-identity-concepts]
* Pokud máte více předplatných Azure, vyberte odpovídající ID předplatného, ve kterém se mají prostředky fakturovat pomocí [příkazu az account set][az-account-set] .

> [!NOTE]
> Pomocí _konektoru Service Connector_ můžete automaticky nakonfigurovat některé kroky. Viz také: Kurz: [Připojení k účtu úložiště Azure ve službě Azure Kubernetes Service (AKS) pomocí konektoru služby s využitím identity][tutorial-python-aks-storage-workload-identity] úloh.

## Vytvoření skupiny zdrojů

Skupina [][azure-resource-group] prostředků Azure je logická skupina, ve které se nasazují a spravují prostředky Azure. Při vytváření skupiny prostředků se zobrazí výzva k zadání umístění. Toto umístění je umístění úložiště metadat vaší skupiny prostředků a místo, kde vaše prostředky běží v Azure, pokud během vytváření prostředků nezadáte jinou oblast.

Vytvořte skupinu prostředků voláním [příkazu az group create][az-group-create] :

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export RESOURCE_GROUP="myResourceGroup$RANDOM_ID"
export LOCATION="centralindia"
az group create --name "${RESOURCE_GROUP}" --location "${LOCATION}"
```

Následující příklad výstupu ukazuje úspěšné vytvoření skupiny prostředků:

Výsledky:
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

## Vytvoření clusteru AKS

Vytvořte cluster AKS pomocí [příkazu az aks create][az-aks-create] s parametrem `--enable-oidc-issuer` pro povolení vystavitele OIDC. Následující příklad vytvoří cluster s jedním uzlem:

```azurecli-interactive
export CLUSTER_NAME="myAKSCluster$RANDOM_ID"
az aks create \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity \
    --generate-ssh-keys
```

Po několika minutách se příkaz dokončí a vrátí informace o clusteru ve formátu JSON.

> [!NOTE]
> Při vytváření clusteru AKS se automaticky vytvoří druhá skupina prostředků pro uložení prostředků AKS. Další informace najdete v tématu [Proč jsou dvě skupiny prostředků vytvořené pomocí AKS?][aks-two-resource-groups].

## Aktualizace existujícího clusteru AKS

Cluster AKS můžete aktualizovat tak, aby používal vystavitele OIDC a povolil identitu úlohy voláním [příkazu az aks update][az aks update] s parametry `--enable-oidc-issuer` a parametry `--enable-workload-identity` . Následující příklad aktualizuje existující cluster:

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity
```

## Načtení adresy URL vystavitele OIDC

Pokud chcete získat adresu URL vystavitele OIDC a uložit ji do proměnné prostředí, spusťte následující příkaz:

```azurecli-interactive
export AKS_OIDC_ISSUER="$(az aks show --name "${CLUSTER_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --query "oidcIssuerProfile.issuerUrl" \
    --output tsv)"
```

Proměnná prostředí by měla obsahovat adresu URL vystavitele, podobně jako v následujícím příkladu:

```output
https://eastus.oic.prod-aks.azure.com/00000000-0000-0000-0000-000000000000/11111111-1111-1111-1111-111111111111/
```

Ve výchozím nastavení je vystavitel nastavený tak, aby používal základní adresu URL `https://{region}.oic.prod-aks.azure.com/{tenant_id}/{uuid}`, kde hodnota odpovídá `{region}` umístění, do kterého je cluster AKS nasazený. Hodnota `{uuid}` představuje klíč OIDC, což je náhodně vygenerovaný identifikátor GUID pro každý cluster, který je neměnný.

## Vytvoření spravované identity

Voláním [příkazu az identity create][az-identity-create] vytvořte spravovanou identitu.

```azurecli-interactive
export SUBSCRIPTION="$(az account show --query id --output tsv)"
export USER_ASSIGNED_IDENTITY_NAME="myIdentity$RANDOM_ID"
az identity create \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --location "${LOCATION}" \
    --subscription "${SUBSCRIPTION}"
```

Následující příklad výstupu ukazuje úspěšné vytvoření spravované identity:

Výsledky:
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

Dále vytvořte proměnnou pro ID klienta spravované identity.

```azurecli-interactive
export USER_ASSIGNED_CLIENT_ID="$(az identity show \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --query 'clientId' \
    --output tsv)"
```

## Vytvoření účtu služby Kubernetes

Vytvořte účet služby Kubernetes a označte ho ID klienta spravované identity vytvořené v předchozím kroku. [Použijte příkaz az aks get-credentials][az-aks-get-credentials] a nahraďte hodnoty názvu clusteru a názvu skupiny prostředků.

```azurecli-interactive
az aks get-credentials --name "${CLUSTER_NAME}" --resource-group "${RESOURCE_GROUP}"
```

Zkopírujte a vložte následující víceřádkový vstup do Azure CLI.

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

Následující výstup ukazuje úspěšné vytvoření identity úlohy:

```output
serviceaccount/workload-identity-sa created
```

## Vytvoření přihlašovacích údajů federované identity

Voláním [příkazu az identity federated-credential create][az-identity-federated-credential-create] vytvořte přihlašovací údaje federované identity mezi spravovanou identitou, vystavitelem účtu služby a předmětem. Další informace o přihlašovacích údajích federované identity v Microsoft Entra najdete v tématu [Přehled přihlašovacích údajů federované identity v Microsoft Entra ID][federated-identity-credential].

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
> Rozšíření přihlašovacích údajů federované identity po přidání trvá několik sekund. Pokud se žádost o token provede okamžitě po přidání přihlašovacích údajů federované identity, může požadavek selhat, dokud se mezipaměť neaktualizuje. Abyste se tomuto problému vyhnuli, můžete po přidání přihlašovacích údajů federované identity přidat mírné zpoždění.

## Nasazení aplikace

Když nasadíte pody aplikace, měl by manifest odkazovat na účet služby vytvořený v **kroku Vytvoření účtu** služby Kubernetes. Následující manifest ukazuje, jak odkazovat na účet, konkrétně _metadata\obor názvů_ a _spec\serviceAccountName_ vlastnosti. Nezapomeňte zadat image pro `<image>` a název kontejneru pro `<containerName>`:

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
> Ujistěte se, že pody aplikace používající identitu úlohy obsahují popisek `azure.workload.identity/use: "true"` ve specifikaci podu. Jinak se pody po restartování nezdaří.

## Udělení oprávnění pro přístup ke službě Azure Key Vault

Pokyny v tomto kroku ukazují, jak získat přístup k tajným kódům, klíčům nebo certifikátům v trezoru klíčů Azure z podu. Příklady v této části konfiguruje přístup k tajným kódům v trezoru klíčů pro identitu úlohy, ale můžete provést podobné kroky ke konfiguraci přístupu ke klíčům nebo certifikátům.

Následující příklad ukazuje, jak pomocí modelu oprávnění řízení přístupu na základě role (Azure RBAC) Azure udělit podu přístup k trezoru klíčů. Další informace o modelu oprávnění Azure RBAC pro Azure Key Vault najdete v tématu [Udělení oprávnění aplikacím pro přístup k trezoru klíčů Azure pomocí Azure RBAC](/azure/key-vault/general/rbac-guide).

1. Vytvořte trezor klíčů s povolenou ochranou před vymazáním a autorizací RBAC. Existující trezor klíčů můžete použít také v případě, že je nakonfigurovaný pro ochranu před vymazáním i autorizaci RBAC:

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

1. Přiřaďte si roli RBAC [Key Vault Secret Officer](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-officer) , abyste mohli vytvořit tajný kód v novém trezoru klíčů:

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

1. Vytvořte tajný klíč v trezoru klíčů:

    ```azurecli-interactive
    export KEYVAULT_SECRET_NAME="my-secret$RANDOM_ID"
    az keyvault secret set \
        --vault-name "${KEYVAULT_NAME}" \
        --name "${KEYVAULT_SECRET_NAME}" \
        --value "Hello\!"
    ```

1. [Přiřaďte roli uživatele tajných](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-user) kódů služby Key Vault spravované identitě přiřazené uživatelem, kterou jste vytvořili dříve. Tento krok poskytuje spravované identitě oprávnění ke čtení tajných kódů z trezoru klíčů:

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

1. Vytvořte proměnnou prostředí pro adresu URL trezoru klíčů:

    ```azurecli-interactive
    export KEYVAULT_URL="$(az keyvault show \
        --resource-group ${RESOURCE_GROUP} \
        --name ${KEYVAULT_NAME} \
        --query properties.vaultUri \
        --output tsv)"
    ```

1. Nasaďte pod, který odkazuje na účet služby a adresu URL trezoru klíčů:

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

Pokud chcete zkontrolovat, jestli webhook správně vloží všechny vlastnosti, použijte [příkaz kubectl describe][kubectl-describe] :

```azurecli-interactive
kubectl describe pod sample-workload-identity-key-vault | grep "SECRET_NAME:"
```

V případě úspěchu by měl být výstup podobný následujícímu:

```output
      SECRET_NAME:                 ${KEYVAULT_SECRET_NAME}
```

Pokud chcete ověřit, že pod dokáže získat token a získat přístup k prostředku, použijte příkaz kubectl logs:

```azurecli-interactive
kubectl logs sample-workload-identity-key-vault
```

V případě úspěchu by měl být výstup podobný následujícímu:

```output
I0114 10:35:09.795900       1 main.go:63] "successfully got secret" secret="Hello\\!"
```

> [!IMPORTANT]
> Rozšíření přiřazení rolí Azure RBAC může trvat až deset minut. Pokud pod nemůže získat přístup k tajnému kódu, možná budete muset počkat na rozšíření přiřazení role. Další informace najdete v tématu [Řešení potíží s Azure RBAC](/azure/role-based-access-control/troubleshooting#).

## Zakázání identity úloh

Pokud chcete zakázat ID úloh Microsoft Entra v clusteru AKS, kde je povolený a nakonfigurovaný, můžete spustit následující příkaz:

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --disable-workload-identity
```

## Další kroky

V tomto článku jste nasadili cluster Kubernetes a nakonfigurovali ho tak, aby používal identitu úloh při přípravě úloh na úlohy aplikací k ověření pomocí těchto přihlašovacích údajů. Teď jste připraveni nasadit aplikaci a nakonfigurovat ji tak, aby používala identitu úloh s nejnovější verzí [klientské knihovny Azure Identity][azure-identity-libraries] . Pokud nemůžete aplikaci přepsat tak, aby používala nejnovější verzi klientské knihovny, můžete [nastavit pod][workload-identity-migration] aplikace tak, aby se ověřil pomocí spravované identity s identitou úloh jako krátkodobé řešení migrace.

Integrace [konektoru](/azure/service-connector/overview) služby pomáhá zjednodušit konfiguraci připojení pro úlohy AKS a backingové služby Azure. Bezpečně zpracovává konfiguraci ověřování a sítě a dodržuje osvědčené postupy pro připojení ke službám Azure. Další informace najdete v tématu [Připojení ke službě Azure OpenAI v AKS pomocí identity](/azure/service-connector/tutorial-python-aks-openai-workload-identity) úloh a úvodu[ ke konektoru ](https://azure.github.io/AKS/2024/05/23/service-connector-intro)služby.

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