---
title: Bereitstellen und Konfigurieren eines AKS-Clusters mit einer Workloadidentität
description: In diesem Artikel zum Azure Kubernetes Service (AKS) stellen Sie einen Azure Kubernetes Service-Cluster bereit und konfigurieren ihn mit einer Microsoft Entra-Workload-ID.
author: tamram
ms.topic: article
ms.subservice: aks-security
ms.custom: devx-track-azurecli
ms.date: 05/28/2024
ms.author: tamram
---

# Bereitstellen und Konfigurieren einer Workloadidentität in einem Azure Kubernetes Service-Cluster (AKS)

Azure Kubernetes Service (AKS) ist ein verwalteter Kubernetes-Dienst, mit dem Sie schnell Kubernetes-Cluster bereitstellen und verwalten können. In diesem Artikel lernen Sie Folgendes:

* Bereitstellen eines AKS-Clusters mithilfe der Azure CLI mit dem OpenID Connect-Zertifikataussteller und einer Microsoft Entra-Workload-ID
* Erstellen Sie eine Microsoft Entra-Workload-ID und ein Kubernetes-Dienstkonto.
* Konfigurieren der verwalteten Identität für den Tokenverbund
* Bereitstellen der Workload und Überprüfen der Authentifizierung mit der Workloadidentität
* Gewähren Sie optional einem Pod im Cluster Zugriff auf Geheimnisse in einem Azure-Schlüsseltresor.

Für diesen Artikel werden Grundkenntnisse von Kubernetes-Konzepten vorausgesetzt. Weitere Informationen finden Sie unter [Grundlegende Kubernetes-Konzepte für Azure Kubernetes Service (AKS)][kubernetes-concepts]. Wenn Sie noch nicht mit der Microsoft Entra-Workload-ID vertraut sind, lesen Sie den folgenden [Übersichtsartikel][workload-identity-overview].

## Voraussetzungen

* [!INCLUDE [quickstarts-free-trial-note](~/reusable-content/ce-skilling/azure/includes/quickstarts-free-trial-note.md)]
* Für diesen Artikel ist mindestens Version 2.47.0 der Azure CLI erforderlich. Bei Verwendung von Azure Cloud Shell ist die aktuelle Version bereits installiert.
* Stellen Sie sicher, dass die Identität, die Sie zum Erstellen Ihres Clusters verwenden, über die erforderlichen Mindestberechtigungen verfügt. Weitere Informationen zu Zugriff und Identität für AKS finden Sie unter [Zugriffs- und Identitätsoptionen für Azure Kubernetes Service (AKS)][aks-identity-concepts].
* Wenn Sie über mehrere Azure-Abonnements verfügen, wählen Sie mithilfe des Befehls [az account set][az-account-set] die ID des Abonnements aus, in dem die Ressourcen fakturiert werden sollen.

> [!NOTE]
> Sie können den _Dienstconnector_ verwenden, um einige Schritte automatisch zu konfigurieren. Siehe auch: [Tutorial: Herstellen einer Verbindung mit einem Azure-Speicherkonto in Azure Kubernetes Service (AKS) mithilfe des Dienstconnectors und unter Verwendung einer Workloadidentität][tutorial-python-aks-storage-workload-identity].

## Erstellen einer Ressourcengruppe

Eine [Azure-Ressourcengruppe][azure-resource-group] ist eine logische Gruppe, in der Azure-Ressourcen bereitgestellt und verwaltet werden. Wenn Sie eine Ressourcengruppe erstellen, werden Sie zur Angabe eines Speicherorts aufgefordert. An diesem Speicherort werden die Metadaten Ihrer Ressourcengruppe gespeichert. Darüber hinaus werden dort die Ressourcen in Azure ausgeführt, wenn Sie während der Ressourcenerstellung keine andere Region angeben.

Erstellen Sie durch Aufrufen des Befehls [az group create][az-group-create] eine Ressourcengruppe:

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export RESOURCE_GROUP="myResourceGroup$RANDOM_ID"
export LOCATION="centralindia"
az group create --name "${RESOURCE_GROUP}" --location "${LOCATION}"
```

Das folgende Ausgabebeispiel zeigt die erfolgreiche Erstellung einer Ressourcengruppe:

Ergebnisse:
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

## Erstellen eines AKS-Clusters

Erstellen Sie einen AKS-Cluster mit dem Befehl [az aks create][az-aks-create] mit dem Parameter `--enable-oidc-issuer`, um den OIDC-Zertifikataussteller zu aktivieren. Im folgenden Beispiel wird ein Cluster mit einem einzelnen Knoten erstellt:

```azurecli-interactive
export CLUSTER_NAME="myAKSCluster$RANDOM_ID"
az aks create \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity \
    --generate-ssh-keys
```

Nach wenigen Minuten ist die Ausführung des Befehls abgeschlossen, und es werden Informationen zum Cluster im JSON-Format zurückgegeben.

> [!NOTE]
> Beim Erstellen eines AKS-Clusters wird automatisch eine zweite Ressourcengruppe erstellt, um die AKS-Ressourcen zu speichern. Weitere Informationen finden Sie unter [Warum werden zwei Ressourcengruppen mit AKS erstellt?][aks-two-resource-groups]

## Aktualisieren eines vorhandenen AKS-Clusters

Sie können einen AKS-Cluster aktualisieren, um den OIDC-Zertifikataussteller zu verwenden und die Workloadidentität zu aktivieren, indem Sie den Befehl [az aks update][az aks update] mit de Parametern `--enable-oidc-issuer` und `--enable-workload-identity` aufrufen. Im folgenden Beispiel wird ein vorhandener Cluster aktualisiert:

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity
```

## Abrufen der OIDC-Zertifikataussteller-URL

Um die URL des OIDC-Zertifikatausstellers abzurufen und in einer Umgebungsvariable zu speichern, führen Sie den folgenden Befehl aus:

```azurecli-interactive
export AKS_OIDC_ISSUER="$(az aks show --name "${CLUSTER_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --query "oidcIssuerProfile.issuerUrl" \
    --output tsv)"
```

Die Umgebungsvariable sollte die URL des Zertifikatausstellers enthalten, ähnlich wie im folgenden Beispiel:

```output
https://eastus.oic.prod-aks.azure.com/00000000-0000-0000-0000-000000000000/11111111-1111-1111-1111-111111111111/
```

Standardmäßig ist der Zertifikataussteller auf die Verwendung der Basis-URL `https://{region}.oic.prod-aks.azure.com/{tenant_id}/{uuid}`festgelegt, wobei der Wert für `{region}` mit dem Speicherort übereinstimmt, an dem der AKS-Cluster bereitgestellt wird. Der Wert `{uuid}` stellt den OIDC-Schlüssel dar, bei dem es sich um eine zufällig generierte GUID für jeden Cluster handelt, der unveränderlich ist.

## Erstellen einer verwalteten Identität

Rufen Sie den Befehl [az identity create][az-identity-create] auf, um eine verwaltete Identität zu erstellen.

```azurecli-interactive
export SUBSCRIPTION="$(az account show --query id --output tsv)"
export USER_ASSIGNED_IDENTITY_NAME="myIdentity$RANDOM_ID"
az identity create \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --location "${LOCATION}" \
    --subscription "${SUBSCRIPTION}"
```

Das folgende Ausgabebeispiel zeigt eine erfolgreiche Erstellung einer verwalteten Identität:

Ergebnisse:
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

Als Nächstes erstellen wir eine Variable für die Client-ID der verwalteten Identität.

```azurecli-interactive
export USER_ASSIGNED_CLIENT_ID="$(az identity show \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --query 'clientId' \
    --output tsv)"
```

## Erstellen eines Kubernetes-Dienstkontos

Erstellen Sie ein Kubernetes-Dienstkonto, und kommentieren Sie es mit der Client-ID der verwalteten Identität, die Sie im vorherigen Schritt erstellt haben. Verwenden Sie den Befehl [az aks get-credentials][az-aks-get-credentials], und ersetzen Sie die Werte für den Clusternamen und den Ressourcengruppennamen.

```azurecli-interactive
az aks get-credentials --name "${CLUSTER_NAME}" --resource-group "${RESOURCE_GROUP}"
```

Kopieren Sie die folgende mehrzeilige Eingabe, und fügen Sie sie in die Azure CLI ein.

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

Die folgende Ausgabe zeigt die erfolgreiche Erstellung der Workloadidentität:

```output
serviceaccount/workload-identity-sa created
```

## Erstellen von Anmeldeinformationen für eine Verbundidentität

Erstellen Sie mit dem Befehl [az identity federated-credential create][az-identity-federated-credential-create] die Anmeldeinformationen für die Verbundidentität zwischen der verwalteten Identität, dem Dienstkontoaussteller und dem Antragsteller. Weitere Informationen zu Anmeldeinformationen für eine Verbundidentität in Microsoft Entra finden Sie unter [Übersicht über die Anmeldeinformationen für Verbundidentitäten in Microsoft Entra ID][federated-identity-credential].

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
> Es dauert einige Sekunden, bis die Anmeldeinformationen für die Verbundidentität nach dem Hinzufügen weitergegeben werden. Wenn eine Tokenanforderung unmittelbar nach dem Hinzufügen der Anmeldeinformationen für die Verbundidentität erfolgt, schlägt die Anforderung möglicherweise fehl, bis der Cache aktualisiert wird. Um dieses Problem zu vermeiden, können Sie eine kleine Verzögerung nach dem Hinzufügen der Verbundidentitäts-Anmeldeinformationen hinzufügen.

## Bereitstellen der Anwendung

Wenn Sie Ihre Anwendungspods bereitstellen, sollte das Manifest auf das Dienstkonto verweisen, das im Schritt **Erstellen eines Kubernetes-Dienstkontos** erstellt wurde. Das folgende Manifest zeigt, wie auf das Konto verwiesen wird, insbesondere auf die Eigenschaften _metadata\namespace_ und _spec\serviceAccountName_. Achten Sie darauf, ein Image für `<image>` und einen Containernamen für `<containerName>` anzugeben:

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
> Stellen Sie sicher, dass die Anwendungspods, die die Workloadidentität verwenden, die Bezeichnung `azure.workload.identity/use: "true"` in der Podspezifikation enthalten. Andernfalls schlagen die Pods nach dem Neustart fehl.

## Erteilen von Berechtigungen für den Zugriff auf Azure Key Vault

Die Anweisungen in diesem Schritt zeigen, wie Sie über den Pod auf Geheimnisse, Schlüssel oder Zertifikate in einem Azure-Schlüsseltresor zugreifen. In den Beispielen in diesem Abschnitt wird der Zugriff auf geheime Schlüssel im Schlüsseltresor für die Workloadidentität konfiguriert. Sie können jedoch ähnliche Schritte ausführen, um den Zugriff auf Schlüssel oder Zertifikate zu konfigurieren.

Das folgende Beispiel zeigt, wie Sie das Azure-Berechtigungsmodell für die rollenbasierte Zugriffssteuerung (Azure RBAC) verwenden, um dem Pod Zugriff auf den Schlüsseltresor zu gewähren. Weitere Informationen zum Azure RBAC-Berechtigungsmodell für Azure Key Vault finden Sie unter [Gewähren der Berechtigung zum Zugreifen auf einen Azure-Schlüsseltresor für Anwendungen mit Azure RBAC](/azure/key-vault/general/rbac-guide).

1. Erstellen Sie einen neuen Schlüsseltresor mit aktiviertem Löschschutz und aktivierter RBAC-Autorisierung. Sie können auch einen vorhandenen Schlüsseltresor verwenden, wenn er sowohl für den Löschschutz als auch für die RBAC-Autorisierung konfiguriert ist:

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

1. Weisen Sie sich selbst die RBAC-Rolle [Key Vault-Geheimnisbeauftragter](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-officer) zu, damit Sie ein Geheimnis im neuen Schlüsseltresor erstellen können:

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

1. Erstellen eines Geheimnisses im Schlüsseltresor:

    ```azurecli-interactive
    export KEYVAULT_SECRET_NAME="my-secret$RANDOM_ID"
    az keyvault secret set \
        --vault-name "${KEYVAULT_NAME}" \
        --name "${KEYVAULT_SECRET_NAME}" \
        --value "Hello\!"
    ```

1. Weisen Sie die Rolle [Key Vault-Geheimnisbenutzer](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-user) der zuvor erstellten benutzerseitig zugewiesenen verwalteten Identität zu. Dieser Schritt gewährt der verwalteten Identität die Berechtigung zum Lesen von Geheimnissen aus dem Schlüsseltresor:

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

1. Erstellen einer Umgebungsvariable für die Schlüsseltresor-URL:

    ```azurecli-interactive
    export KEYVAULT_URL="$(az keyvault show \
        --resource-group ${RESOURCE_GROUP} \
        --name ${KEYVAULT_NAME} \
        --query properties.vaultUri \
        --output tsv)"
    ```

1. Stellen Sie einen Pod bereit, der auf das Dienstkonto und die Key Vault-URL verweist:

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

Um zu überprüfen, ob vom Webhook alle Eigenschaften ordnungsgemäß eingefügt werden, verwenden Sie den Befehl [kubectl describe][kubectl-describe]:

```azurecli-interactive
kubectl describe pod sample-workload-identity-key-vault | grep "SECRET_NAME:"
```

Bei Erfolg sollte die Ausgabe dem folgenden Beispiel ähneln:

```output
      SECRET_NAME:                 ${KEYVAULT_SECRET_NAME}
```

Um zu überprüfen, ob der Pod ein Token abrufen und auf die Ressource zugreifen kann, verwenden Sie den Befehl „kubectl logs“:

```azurecli-interactive
kubectl logs sample-workload-identity-key-vault
```

Bei Erfolg sollte die Ausgabe dem folgenden Beispiel ähneln:

```output
I0114 10:35:09.795900       1 main.go:63] "successfully got secret" secret="Hello\\!"
```

> [!IMPORTANT]
> Die Weitergabe von Azure RBAC-Rollenzuweisungen kann bis zu zehn Minuten dauern. Wenn der Pod nicht auf das Geheimnis zugreifen kann, müssen Sie möglicherweise warten, bis die Rollenzuweisung weitergegeben ist. Weitere Informationen finden Sie unter [Behandeln von Problemen bei Azure RBAC](/azure/role-based-access-control/troubleshooting#).

## Deaktivieren der Workloadidentität

Um die Microsoft Entra-Workload-ID in dem AKS-Cluster zu deaktivieren, in dem sie aktiviert und konfiguriert wurde, können Sie den folgenden Befehl ausführen:

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --disable-workload-identity
```

## Nächste Schritte

In diesem Artikel haben Sie einen Kubernetes-Cluster bereitgestellt und so konfiguriert, dass eine Workloadidentität zum Vorbereiten auf Anwendungsworkloads verwendet wird, um sich mit diesen Anmeldeinformationen zu authentifizieren. Jetzt können Sie Ihre Anwendung bereitstellen und konfigurieren, um die Workloadidentität mit der neuesten Version der [Azure Identity][azure-identity-libraries]-Clientbibliothek zu verwenden. Wenn Sie Ihre Anwendung nicht neu schreiben können, um die neueste Clientbibliotheksversion zu verwenden, können Sie [Ihren Anwendungspod so einrichten][workload-identity-migration], dass die Authentifizierung mithilfe der verwalteten Identität mit einer Workloadidentität als kurzfristige Migrationslösung durchgeführt wird.

Die [Dienstconnector](/azure/service-connector/overview)-Integration vereinfacht die Verbindungskonfiguration für AKS-Workloads und Azure-Sicherungsdienste. Sie verarbeitet Authentifizierungs- und Netzwerkkonfigurationen auf sichere Weise und folgt bewährten Methoden für die Verbindung mit Azure-Diensten. Weitere Informationen finden Sie unter [Herstellen einer Verbindung mit Azure OpenAI Service in AKS mit der Workloadidentität](/azure/service-connector/tutorial-python-aks-openai-workload-identity) und [Einführung in den Dienstconnector](https://azure.github.io/AKS/2024/05/23/service-connector-intro).

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