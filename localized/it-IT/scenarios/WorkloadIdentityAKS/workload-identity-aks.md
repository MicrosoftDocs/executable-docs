---
title: Distribuire e configurare un cluster del servizio Azure Kubernetes con l'identità del carico di lavoro
description: In questo articolo sul servizio Azure Kubernetes si distribuisce un cluster del servizio Azure Kubernetes e lo si configura con un ID dei carichi di lavoro di Microsoft Entra.
author: tamram
ms.topic: article
ms.subservice: aks-security
ms.custom: devx-track-azurecli
ms.date: 05/28/2024
ms.author: tamram
---

# Distribuire e configurare l'identità dei carichi di lavoro in un cluster del servizio Azure Kubernetes

Il servizio Azure Kubernetes è un servizio Kubernetes gestito che permette di distribuire e gestire rapidamente i cluster Kubernetes. Questo articolo illustra come:

* Distribuire un cluster del servizio Azure Kubernetes usando l'interfaccia della riga di comando di Azure con l'autorità di certificazione OpenID Connect e un ID dei carichi di lavoro di Microsoft Entra.
* Creare un ID carico di lavoro Microsoft Entra e un account del servizio Kubernetes.
* Configurare l'identità gestita per la federazione dei token.
* Distribuire il carico di lavoro e verificare l'autenticazione con l'identità del carico di lavoro.
* Facoltativamente, concedere a un pod nel cluster l'accesso ai segreti in Azure Key Vault.

Questo articolo presuppone che si abbia una conoscenza di base dei concetti relativi a Kubernetes. Per altre informazioni, vedere [Concetti di base relativi a Kubernetes per il servizio Azure Kubernetes][kubernetes-concepts]. Se non si ha familiarità con l'ID dei carichi di lavoro di Microsoft Entra, vedere l'articolo [Panoramica][workload-identity-overview] seguente.

## Prerequisiti

* [!INCLUDE [quickstarts-free-trial-note](~/reusable-content/ce-skilling/azure/includes/quickstarts-free-trial-note.md)]
* Questo articolo richiede la versione 2.47.0 o successiva dell'interfaccia della riga di comando di Azure. Se si usa Azure Cloud Shell, la versione più recente è già installata.
* Assicurarsi che l'identità usata per creare il cluster disponga delle autorizzazioni minime appropriate. Per altre informazioni sull'accesso e l'identità per il servizio Azure Kubernetes, vedere [Opzioni di accesso e identità per il servizio Azure Kubernetes (AKS).][aks-identity-concepts]
* Se si hanno più sottoscrizioni di Azure, selezionare l'ID sottoscrizione appropriato in cui devono essere fatturate le risorse, usando il comando [set account az][az-account-set].

> [!NOTE]
> È possibile usare _Service Connector_ per configurare automaticamente alcuni passaggi. Vedere anche: [Esercitazione: Connettersi all'account di archiviazione di Azure nel servizio Azure Kubernetes con Service Connector usando l'identità del carico di lavoro][tutorial-python-aks-storage-workload-identity].

## Creare un gruppo di risorse

Un [gruppo di risorse][azure-resource-group] di Azure è un gruppo logico in cui le risorse di Azure vengono distribuite e gestite. Quando si crea un gruppo di risorse, viene richiesto di specificare una posizione. Questa posizione è la posizione di archiviazione dei metadati del gruppo di risorse e dove le risorse vengono eseguite in Azure se non si specifica un'altra regione durante la creazione della risorsa.

Creare un gruppo di risorse chiamando il comando [az group create][az-group-create]:

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export RESOURCE_GROUP="myResourceGroup$RANDOM_ID"
export LOCATION="centralindia"
az group create --name "${RESOURCE_GROUP}" --location "${LOCATION}"
```

L'output di esempio seguente mostra la corretta creazione di un gruppo di risorse:

Risultati:
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

## Creare un cluster del servizio Azure Kubernetes

Creare un cluster del servizio Azure Kubernetes usando il comando [az aks create][az-aks-create] con il parametro `--enable-oidc-issuer` per abilitare l'autorità di certificazione OIDC. L'esempio seguente crea un cluster con un singolo nodo:

```azurecli-interactive
export CLUSTER_NAME="myAKSCluster$RANDOM_ID"
az aks create \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity \
    --generate-ssh-keys
```

Il comando viene completato dopo pochi minuti e vengono restituite informazioni in formato JSON sul cluster.

> [!NOTE]
> Quando si crea un cluster del servizio Azure Kubernetes, viene creato automaticamente un secondo gruppo di risorse per archiviare le risorse del servizio Azure Kubernetes. Per altre informazioni, vedere [Perché vengono creati due gruppi di risorse con servizio Azure Kubernetes?][aks-two-resource-groups].

## Aggiornare un cluster del servizio Azure Kubernetes esistente

È possibile aggiornare un cluster del servizio Azure Kubernetes in modo da usare l'autorità di certificazione OIDC chiamando il comando [az aks update][az aks update] con i parametri `--enable-oidc-issuer` e `--enable-workload-identity`. Nell'esempio seguente viene aggiornato un cluster esistente:

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity
```

## Recuperare l'URL dell'autorità di certificazione OIDC

Per ottenere l'URL dell'autorità di certificazione OIDC e salvarlo in una variabile di ambiente, eseguire il comando seguente:

```azurecli-interactive
export AKS_OIDC_ISSUER="$(az aks show --name "${CLUSTER_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --query "oidcIssuerProfile.issuerUrl" \
    --output tsv)"
```

La variabile di ambiente deve contenere l'URL dell'autorità di certificazione, in modo simile all'esempio seguente:

```output
https://eastus.oic.prod-aks.azure.com/00000000-0000-0000-0000-000000000000/11111111-1111-1111-1111-111111111111/
```

Per impostazione predefinita, l'autorità di certificazione è impostata per usare l'URL di base `https://{region}.oic.prod-aks.azure.com/{tenant_id}/{uuid}`, dove il valore per `{region}` corrisponde alla posizione in cui è distribuito il cluster del servizio Azure Kubernetes. Il valore `{uuid}` rappresenta la chiave OIDC, che è un GUID generato in modo casuale per ogni cluster, il quale non è modificabile.

## Creare un'identità gestita

Chiamare il comando [az identity create][az-identity-create] per creare un'identità gestita.

```azurecli-interactive
export SUBSCRIPTION="$(az account show --query id --output tsv)"
export USER_ASSIGNED_IDENTITY_NAME="myIdentity$RANDOM_ID"
az identity create \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --location "${LOCATION}" \
    --subscription "${SUBSCRIPTION}"
```

L'esempio di output seguente mostra la corretta creazione di un'identità gestita:

Risultati:
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

Creare quindi una variabile per l'ID client dell'identità gestita.

```azurecli-interactive
export USER_ASSIGNED_CLIENT_ID="$(az identity show \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --query 'clientId' \
    --output tsv)"
```

## Creare un account del servizio Kubernetes

Creare un account del servizio Kubernetes e annotarlo con l'ID client dell'identità gestita creata nel passaggio precedente. Usare il comando [az aks get-credentials][az-aks-get-credentials] e sostituire i valori del nome del cluster e il nome del gruppo di risorse.

```azurecli-interactive
az aks get-credentials --name "${CLUSTER_NAME}" --resource-group "${RESOURCE_GROUP}"
```

Copiare e incollare il seguente input su più righe nell'interfaccia della riga di comando di Azure.

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

L'output seguente mostra la corretta creazione dell'identità del carico di lavoro:

```output
serviceaccount/workload-identity-sa created
```

## Creare le credenziali dell'identità federata

Chiamare il comando [az identity federated-credential create][az-identity-federated-credential-create] per creare le credenziali di identità federata tra l'identità gestita, l'autorità di certificazione dell'account del servizio e l'oggetto. Per altre informazioni sulle credenziali di identità federate in Microsoft Entra, vedere [Panoramica delle credenziali di identità federate in Microsoft Entra ID][federated-identity-credential].

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
> La propagazione delle credenziali dell'identità federata dopo l'aggiunta iniziale richiede alcuni secondi. Se una richiesta di token viene effettuata immediatamente dopo l'aggiunta della credenziale dell'identità federata, la richiesta potrebbe non riuscire finché non viene aggiornata la cache. Per evitare questo problema, è possibile aggiungere un lieve ritardo dopo l'aggiunta delle credenziali di identità federate.

## Distribuire l'applicazione

Quando si distribuiscono i pod dell'applicazione, il manifesto deve fare riferimento all'account del servizio creato nel passaggio **Creare l'account del servizio Kubernetes**. Il manifesto seguente illustra come fare riferimento all'account, in particolare alle proprietà _metadata\namespace_ e _spec\serviceAccountName_. Assicurarsi di specificare un'immagine per `<image>` e un nome del contenitore per `<containerName>`:

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
> Assicurarsi che i pod dell'applicazione che usano l'identità del carico di lavoro includano l'etichetta `azure.workload.identity/use: "true"` nella specifica del pod. In caso contrario, i pod avranno esito negativo dopo il riavvio.

## Concedere le autorizzazioni per l'accesso ad Azure Key Vault

Le istruzioni in questo passaggio illustrano come accedere a segreti, chiavi o certificati in Azure Key Vault dal pod. Gli esempi in questa sezione configurano l'accesso ai segreti nell'insieme di credenziali delle chiavi per l'identità del carico di lavoro, ma è possibile eseguire passaggi simili per configurare l'accesso a chiavi o certificati.

L'esempio seguente illustra come usare il modello di autorizzazione Controllo degli accessi in base al ruolo di Azure per concedere al pod l'accesso a Key Vault. Per altre informazioni sul modello di autorizzazione Controllo degli accessi in base al ruolo di Azure per Azure Key Vault, vedere [Concedere alle applicazioni l'autorizzazione per accedere ad Azure Key Vault usando il controllo degli accessi in base al ruolo di Azure](/azure/key-vault/general/rbac-guide).

1. Creare un'istanza di Key Vault con la protezione dall'eliminazione e l'autorizzazione di Controllo degli accessi in base al ruolo abilitata. È anche possibile usare un'istanza di Key Vault esistente se è configurata sia per la protezione dall'eliminazione che per l'autorizzazione di Controllo degli accessi in base al ruolo:

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

1. Assegnare a se stessi il ruolo [Responsabile dei segreti di Key Vault](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-officer) di Controllo degli accessi in base al ruolo in modo da poter creare un segreto nella nuova istanza di Key Vault:

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

1. Creare un segreto in Key Vault:

    ```azurecli-interactive
    export KEYVAULT_SECRET_NAME="my-secret$RANDOM_ID"
    az keyvault secret set \
        --vault-name "${KEYVAULT_NAME}" \
        --name "${KEYVAULT_SECRET_NAME}" \
        --value "Hello\!"
    ```

1. Assegnare il ruolo [Utente dei segreti di Key Vault](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-user) all'identità gestita assegnata dall'utente creata in precedenza. Questo passaggio concede all'identità gestita l'autorizzazione per leggere i segreti da Key Vault:

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

1. Creare una variabile di ambiente per l'URL di Key Vault:

    ```azurecli-interactive
    export KEYVAULT_URL="$(az keyvault show \
        --resource-group ${RESOURCE_GROUP} \
        --name ${KEYVAULT_NAME} \
        --query properties.vaultUri \
        --output tsv)"
    ```

1. Distribuire un pod che fa riferimento all'account del servizio e all'URL di Key Vault:

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

Per verificare se tutte le proprietà vengono inserite correttamente dal webhook, usare il comando [kubectl describe][kubectl-describe]:

```azurecli-interactive
kubectl describe pod sample-workload-identity-key-vault | grep "SECRET_NAME:"
```

In caso di esito positivo, l'output dovrebbe essere simile al seguente:

```output
      SECRET_NAME:                 ${KEYVAULT_SECRET_NAME}
```

Per verificare che il pod sia in grado di ottenere un token e accedere alla risorsa, usare il comando kubectl logs:

```azurecli-interactive
kubectl logs sample-workload-identity-key-vault
```

In caso di esito positivo, l'output dovrebbe essere simile al seguente:

```output
I0114 10:35:09.795900       1 main.go:63] "successfully got secret" secret="Hello\\!"
```

> [!IMPORTANT]
> La propagazione delle assegnazioni del ruolo Controllo degli accessi in base al ruolo di Azure può richiedere fino a dieci minuti. Se il pod non è in grado di accedere al segreto, può essere necessario attendere la propagazione dell'assegnazione di ruolo. Per altre informazioni, vedere [Risolvere i problemi relativi al controllo degli accessi in base al ruolo di Azure](/azure/role-based-access-control/troubleshooting#).

## Disabilitare l'identità dei carichi di lavoro

Per disabilitare l'ID dei carichi di lavoro di Microsoft Entra nel cluster servizio Azure Kubernetes in cui è stato abilitato e configurato, è possibile eseguire il comando seguente:

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --disable-workload-identity
```

## Passaggi successivi

In questo articolo è stato distribuito e configurato un cluster Kubernetes per l'uso di un'identità dei carichi di lavoro in preparazione per l'autenticazione dei carichi di lavoro dell'applicazione con tale credenziale. A questo punto è possibile distribuire l'applicazione e configurarla per usare l'identità dei carichi di lavoro con la versione più recente della libreria client [Identità di Azure][azure-identity-libraries]. Se non è possibile riscrivere l'applicazione per usare la versione più recente della libreria client, è possibile [configurare il pod dell'applicazione][workload-identity-migration] per eseguire l'autenticazione usando l'identità gestita con l'identità dei carichi di lavoro come soluzione di migrazione a breve termine.

L'integrazione del [connettore di servizi](/azure/service-connector/overview) semplifica la configurazione della connessione per i carichi di lavoro del servizio Azure Kubernetes e i servizi sottostanti di Azure. Gestisce in modo sicuro le configurazioni di autenticazione e di rete e segue le procedure consigliate per la connessione ai servizi di Azure. Per altre informazioni, vedere [Connettersi al Servizio OpenAI di Azure nel servizio Azure Kubernetes usando l'identità del carico di lavoro](/azure/service-connector/tutorial-python-aks-openai-workload-identity) e l'[introduzione al connettore di servizi](https://azure.github.io/AKS/2024/05/23/service-connector-intro).

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