---
title: Een AKS-cluster implementeren en configureren met workloadidentiteit
description: In dit artikel over Azure Kubernetes Service (AKS) implementeert u een Azure Kubernetes Service-cluster en configureert u dit met een Microsoft Entra Workload-ID.
author: tamram
ms.topic: article
ms.subservice: aks-security
ms.custom: devx-track-azurecli
ms.date: 05/28/2024
ms.author: tamram
---

# Workloadidentiteit implementeren en configureren op een AKS-cluster (Azure Kubernetes Service)

Azure Kubernetes Service (AKS) is een beheerde Kubernetes-service waarmee u Kubernetes-clusters snel kunt implementeren en beheren. Dit artikel laat het volgende zien:

* Implementeer een AKS-cluster met behulp van de Azure CLI met de OpenID Connect-verlener en een Microsoft Entra Workload-ID.
* Maak een Microsoft Entra Workload-ID- en Kubernetes-serviceaccount.
* Configureer de beheerde identiteit voor tokenfederatie.
* Implementeer de workload en controleer de verificatie met de workload-id.
* U kunt desgewenst een pod in het cluster toegang verlenen tot geheimen in een Azure-sleutelkluis.

In dit artikel wordt ervan uitgegaan dat u basiskennis hebt van Kubernetes-concepten. Zie [Kubernetes-kernconcepten voor Azure Kubernetes Service (AKS)][kubernetes-concepts] voor meer informatie. Als u niet bekend bent met Microsoft Entra Workload-ID, raadpleegt u het volgende [artikel overzicht][workload-identity-overview].

## Vereisten

* [!INCLUDE [quickstarts-free-trial-note](~/reusable-content/ce-skilling/azure/includes/quickstarts-free-trial-note.md)]
* Voor dit artikel is versie 2.47.0 of hoger van de Azure CLI vereist. Als u Azure Cloud Shell gebruikt, is de nieuwste versie al geïnstalleerd.
* Zorg ervoor dat de identiteit die u gebruikt om uw cluster te maken over de juiste minimale machtigingen beschikt. Zie Toegangs- en identiteitsopties voor Azure Kubernetes Service (AKS)[ voor meer informatie over toegang en identiteit voor AKS][aks-identity-concepts].
* Als u meerdere Azure-abonnementen hebt, selecteert u de juiste abonnements-id waarin de resources moeten worden gefactureerd met behulp van de [opdracht az account set][az-account-set] .

> [!NOTE]
> U kunt serviceconnector_ gebruiken _om bepaalde stappen automatisch te configureren. Zie ook: Zelfstudie: [Verbinding maken met een Azure-opslagaccount in Azure Kubernetes Service (AKS) met Service Connector met behulp van workloadidentiteit][tutorial-python-aks-storage-workload-identity].

## Een brongroep maken

Een [Azure-resourcegroep][azure-resource-group] is een logische groep waarin Azure-resources worden geïmplementeerd en beheerd. Wanneer u een resourcegroep maakt, wordt u gevraagd een locatie op te geven. Deze locatie is de opslaglocatie van de metagegevens van uw resourcegroep en waar uw resources worden uitgevoerd in Azure als u geen andere regio opgeeft tijdens het maken van de resource.

Maak een resourcegroep door de [opdracht az group create][az-group-create] aan te roepen:

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export RESOURCE_GROUP="myResourceGroup$RANDOM_ID"
export LOCATION="centralindia"
az group create --name "${RESOURCE_GROUP}" --location "${LOCATION}"
```

In het volgende uitvoervoorbeeld ziet u hoe een resourcegroep is gemaakt:

Resultaten:
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

## Een AKS-cluster maken

Maak een AKS-cluster met behulp van de [opdracht az aks create][az-aks-create] met de `--enable-oidc-issuer` parameter om de OIDC-verlener in te schakelen. In het volgende voorbeeld wordt een cluster met één knooppunt gemaakt:

```azurecli-interactive
export CLUSTER_NAME="myAKSCluster$RANDOM_ID"
az aks create \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity \
    --generate-ssh-keys
```

Na enkele minuten is de opdracht voltooid en retourneert deze informatie over het cluster in JSON-indeling.

> [!NOTE]
> Wanneer u een AKS-cluster maakt, wordt automatisch een tweede resourcegroep gemaakt om de AKS-resources op te slaan. Zie [Waarom zijn er twee resourcegroepen gemaakt met AKS?][aks-two-resource-groups] voor meer informatie.

## Een bestaand AKS-cluster bijwerken

U kunt een AKS-cluster bijwerken om de OIDC-verlener te gebruiken en workloadidentiteit in te schakelen door de [opdracht az aks update][az aks update] aan te roepen met de `--enable-oidc-issuer` en de `--enable-workload-identity` parameters. In het volgende voorbeeld wordt een bestaand cluster bijgewerkt:

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity
```

## De URL van de OIDC-verlener ophalen

Voer de volgende opdracht uit om de URL van de OIDC-verlener op te halen en op te slaan in een omgevingsvariabele:

```azurecli-interactive
export AKS_OIDC_ISSUER="$(az aks show --name "${CLUSTER_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --query "oidcIssuerProfile.issuerUrl" \
    --output tsv)"
```

De omgevingsvariabele moet de URL van de verlener bevatten, vergelijkbaar met het volgende voorbeeld:

```output
https://eastus.oic.prod-aks.azure.com/00000000-0000-0000-0000-000000000000/11111111-1111-1111-1111-111111111111/
```

De verlener is standaard ingesteld op het gebruik van de basis-URL `https://{region}.oic.prod-aks.azure.com/{tenant_id}/{uuid}`, waarbij de waarde voor `{region}` de locatie waarop het AKS-cluster wordt geïmplementeerd, overeenkomt met de locatie. De waarde `{uuid}` vertegenwoordigt de OIDC-sleutel. Dit is een willekeurig gegenereerde GUID voor elk cluster dat onveranderbaar is.

## Een beheerde identiteit maken

Roep de [opdracht az identity create][az-identity-create] aan om een beheerde identiteit te maken.

```azurecli-interactive
export SUBSCRIPTION="$(az account show --query id --output tsv)"
export USER_ASSIGNED_IDENTITY_NAME="myIdentity$RANDOM_ID"
az identity create \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --location "${LOCATION}" \
    --subscription "${SUBSCRIPTION}"
```

In het volgende uitvoervoorbeeld ziet u hoe een beheerde identiteit is gemaakt:

Resultaten:
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

Maak vervolgens een variabele voor de client-id van de beheerde identiteit.

```azurecli-interactive
export USER_ASSIGNED_CLIENT_ID="$(az identity show \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --query 'clientId' \
    --output tsv)"
```

## Een Kubernetes-serviceaccount maken

Maak een Kubernetes-serviceaccount en annotaeer dit met de client-id van de beheerde identiteit die u in de vorige stap hebt gemaakt. Gebruik de [opdracht az aks get-credentials][az-aks-get-credentials] en vervang de waarden voor de clusternaam en de naam van de resourcegroep.

```azurecli-interactive
az aks get-credentials --name "${CLUSTER_NAME}" --resource-group "${RESOURCE_GROUP}"
```

Kopieer en plak de volgende invoer met meerdere regels in de Azure CLI.

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

In de volgende uitvoer ziet u dat de workloadidentiteit is gemaakt:

```output
serviceaccount/workload-identity-sa created
```

## De federatieve identiteitsreferentie maken

Roep de [opdracht az identity federated-credential create][az-identity-federated-credential-create] aan om de federatieve identiteitsreferentie te maken tussen de beheerde identiteit, de verlener van het serviceaccount en het onderwerp. Zie Overzicht van federatieve identiteitsreferenties in Microsoft Entra [voor meer informatie over federatieve identiteitsreferenties in Microsoft Entra-id][federated-identity-credential].

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
> Het duurt enkele seconden voordat de federatieve identiteitsreferentie is doorgegeven nadat deze is toegevoegd. Als er direct na het toevoegen van de federatieve identiteitsreferentie een tokenaanvraag wordt gedaan, mislukt de aanvraag mogelijk totdat de cache wordt vernieuwd. U kunt dit probleem voorkomen door een kleine vertraging toe te voegen nadat u de federatieve identiteitsreferentie hebt toegevoegd.

## Uw toepassing implementeren

Wanneer u uw toepassingspods implementeert, moet het manifest verwijzen naar het serviceaccount dat is gemaakt in de **stap Kubernetes-serviceaccount** maken. In het volgende manifest ziet u hoe u naar het account verwijst, met name de _eigenschappen metadata\namespace_ en _spec\serviceAccountName_ . Zorg ervoor dat u een installatiekopieën voor en een containernaam opgeeft `<image>` voor `<containerName>`:

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
> Zorg ervoor dat de toepassingspods die gebruikmaken van de workloadidentiteit het label `azure.workload.identity/use: "true"` in de podspecificatie bevatten. Anders mislukken de pods nadat ze opnieuw zijn opgestart.

## Machtigingen verlenen voor toegang tot Azure Key Vault

In de instructies in deze stap ziet u hoe u vanuit de pod toegang krijgt tot geheimen, sleutels of certificaten in een Azure-sleutelkluis. In de voorbeelden in deze sectie wordt de toegang tot geheimen in de sleutelkluis voor de workloadidentiteit geconfigureerd, maar u kunt vergelijkbare stappen uitvoeren om toegang tot sleutels of certificaten te configureren.

In het volgende voorbeeld ziet u hoe u het machtigingsmodel voor op rollen gebaseerd toegangsbeheer (Azure RBAC) van Azure gebruikt om de pod toegang te verlenen tot de sleutelkluis. Zie Machtiging verlenen aan toepassingen voor toegang tot een Azure-sleutelkluis met behulp van Azure RBAC voor meer informatie over het Azure RBAC-machtigingsmodel[ voor Azure Key Vault](/azure/key-vault/general/rbac-guide).

1. Maak een sleutelkluis met beveiliging tegen opschonen en RBAC-autorisatie ingeschakeld. U kunt ook een bestaande sleutelkluis gebruiken als deze is geconfigureerd voor zowel beveiliging tegen opschonen als RBAC-autorisatie:

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

1. Wijs uzelf de rol RBAC [Key Vault Secrets Officer](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-officer) toe, zodat u een geheim kunt maken in de nieuwe sleutelkluis:

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

1. Maak een geheim in de sleutelkluis:

    ```azurecli-interactive
    export KEYVAULT_SECRET_NAME="my-secret$RANDOM_ID"
    az keyvault secret set \
        --vault-name "${KEYVAULT_NAME}" \
        --name "${KEYVAULT_SECRET_NAME}" \
        --value "Hello\!"
    ```

1. Wijs de [rol Key Vault Secrets User](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-user) toe aan de door de gebruiker toegewezen beheerde identiteit die u eerder hebt gemaakt. Deze stap geeft de beheerde identiteit toestemming om geheimen uit de sleutelkluis te lezen:

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

1. Maak een omgevingsvariabele voor de URL van de sleutelkluis:

    ```azurecli-interactive
    export KEYVAULT_URL="$(az keyvault show \
        --resource-group ${RESOURCE_GROUP} \
        --name ${KEYVAULT_NAME} \
        --query properties.vaultUri \
        --output tsv)"
    ```

1. Implementeer een pod die verwijst naar de URL van het serviceaccount en de sleutelkluis:

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

Als u wilt controleren of alle eigenschappen correct worden geïnjecteerd door de webhook, gebruikt u de [opdracht kubectl describe][kubectl-describe] :

```azurecli-interactive
kubectl describe pod sample-workload-identity-key-vault | grep "SECRET_NAME:"
```

Als dit lukt, moet de uitvoer er ongeveer als volgt uitzien:

```output
      SECRET_NAME:                 ${KEYVAULT_SECRET_NAME}
```

Gebruik de opdracht kubectl-logboeken om te controleren of de pod een token kan ophalen en toegang heeft tot de resource:

```azurecli-interactive
kubectl logs sample-workload-identity-key-vault
```

Als dit lukt, moet de uitvoer er ongeveer als volgt uitzien:

```output
I0114 10:35:09.795900       1 main.go:63] "successfully got secret" secret="Hello\\!"
```

> [!IMPORTANT]
> Het kan tot tien minuten duren voordat Azure RBAC-roltoewijzingen zijn doorgegeven. Als de pod geen toegang heeft tot het geheim, moet u mogelijk wachten totdat de roltoewijzing is doorgegeven. Zie [Problemen met Azure RBAC](/azure/role-based-access-control/troubleshooting#) oplossen voor meer informatie.

## Workloadidentiteit uitschakelen

Als u de Microsoft Entra Workload-ID wilt uitschakelen op het AKS-cluster waarvoor het is ingeschakeld en geconfigureerd, kunt u de volgende opdracht uitvoeren:

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --disable-workload-identity
```

## Volgende stappen

In dit artikel hebt u een Kubernetes-cluster geïmplementeerd en geconfigureerd voor het gebruik van een workloadidentiteit ter voorbereiding op toepassingsworkloads voor verificatie met die referentie. U bent nu klaar om uw toepassing te implementeren en deze te configureren voor het gebruik van de workloadidentiteit met de nieuwste versie van de [Azure Identity-clientbibliotheek][azure-identity-libraries] . Als u uw toepassing niet kunt herschrijven om de nieuwste versie van de clientbibliotheek te gebruiken, kunt [u uw toepassingspod][workload-identity-migration] instellen voor verificatie met beheerde identiteit met workloadidentiteit als een kortetermijnmigratieoplossing.

De [serviceconnectorintegratie](/azure/service-connector/overview) vereenvoudigt de verbindingsconfiguratie voor AKS-workloads en Azure-backingservices. Het verwerkt verificatie- en netwerkconfiguraties veilig en volgt aanbevolen procedures voor het maken van verbinding met Azure-services. Zie Verbinding maken met De Azure OpenAI-service in AKS met behulp van workloadidentiteit[ en de inleiding[ tot de ](https://azure.github.io/AKS/2024/05/23/service-connector-intro)serviceconnector voor meer informatie](/azure/service-connector/tutorial-python-aks-openai-workload-identity).

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