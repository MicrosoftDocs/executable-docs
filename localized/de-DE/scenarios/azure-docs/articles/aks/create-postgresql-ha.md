---
title: Erstellen von Infrastruktur für die Bereitstellung einer hochverfügbaren PostgreSQL-Datenbank in AKS
description: Erstellen der notwendigen Infrastruktur für die Bereitstellung einer hochverfügbaren PostgreSQL-Datenbank in AKS mithilfe des CloudNativePG-Operators.
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# Erstellen von Infrastruktur für die Bereitstellung einer hochverfügbaren PostgreSQL-Datenbank in AKS

In diesem Artikel werden Sie die notwendige Infrastruktur für die Bereitstellung einer hochverfügbaren PostgreSQL-Datenbank in AKS mithilfe des [CloudNativePG-Operators](https://cloudnative-pg.io/) (CNPG) erstellen.

## Voraussetzungen

* Überprüfen Sie die Bereitstellungsübersicht, und stellen Sie sicher, dass Sie alle Voraussetzungen unter [Bereitstellen einer hochverfügbaren PostgreSQL-Datenbank in AKS mithilfe der Azure CLI][postgresql-ha-deployment-overview] erfüllen.
* [Legen Sie Umgebungsvariablen fest](#set-environment-variables), die in dieser Anleitung verwendet werden.
* [Installieren Sie die erforderlichen Erweiterungen](#install-required-extensions).

## Festlegen von Umgebungsvariablen

Legen Sie die folgenden Umgebungsvariablen für die Verwendung in dieser Anleitung fest:

```bash
export SUFFIX=$(cat /dev/urandom | LC_ALL=C tr -dc 'a-z0-9' | fold -w 8 | head -n 1)
export LOCAL_NAME="cnpg"
export TAGS="owner=user"
export RESOURCE_GROUP_NAME="rg-${LOCAL_NAME}-${SUFFIX}"
export PRIMARY_CLUSTER_REGION="westus3"
export AKS_PRIMARY_CLUSTER_NAME="aks-primary-${LOCAL_NAME}-${SUFFIX}"
export AKS_PRIMARY_MANAGED_RG_NAME="rg-${LOCAL_NAME}-primary-aksmanaged-${SUFFIX}"
export AKS_PRIMARY_CLUSTER_FED_CREDENTIAL_NAME="pg-primary-fedcred1-${LOCAL_NAME}-${SUFFIX}"
export AKS_PRIMARY_CLUSTER_PG_DNSPREFIX=$(echo $(echo "a$(openssl rand -hex 5 | cut -c1-11)"))
export AKS_UAMI_CLUSTER_IDENTITY_NAME="mi-aks-${LOCAL_NAME}-${SUFFIX}"
export AKS_CLUSTER_VERSION="1.29"
export PG_NAMESPACE="cnpg-database"
export PG_SYSTEM_NAMESPACE="cnpg-system"
export PG_PRIMARY_CLUSTER_NAME="pg-primary-${LOCAL_NAME}-${SUFFIX}"
export PG_PRIMARY_STORAGE_ACCOUNT_NAME="hacnpgpsa${SUFFIX}"
export PG_STORAGE_BACKUP_CONTAINER_NAME="backups"
export ENABLE_AZURE_PVC_UPDATES="true"
export MY_PUBLIC_CLIENT_IP=$(dig +short myip.opendns.com @resolver3.opendns.com)
```

## Installieren der erforderlichen Erweiterungen

Die Erweiterungen `aks-preview`, `k8s-extension` und `amg` bieten mehr Funktionen zum Verwalten von Kubernetes-Clustern und Abfragen von Azure-Ressourcen. Installieren Sie diese Erweiterungen, indem Sie die folgenden [`az extension add`][az-extension-add]-Befehle ausführen:

```bash
az extension add --upgrade --name aks-preview --yes --allow-preview true
az extension add --upgrade --name k8s-extension --yes --allow-preview false
az extension add --upgrade --name amg --yes --allow-preview false
```

Als Voraussetzung für die Nutzung von kubectl ist es wichtig, [Krew][install-krew] zuerst zu installieren, gefolgt von der Installation des [CNPG-Plug-Ins][cnpg-plugin]. Das ermöglicht die Verwaltung des PostgreSQL-Operators mit den nachfolgenden Befehlen.

```bash
(
  set -x; cd "$(mktemp -d)" &&
  OS="$(uname | tr '[:upper:]' '[:lower:]')" &&
  ARCH="$(uname -m | sed -e 's/x86_64/amd64/' -e 's/\(arm\)\(64\)\?.*/\1\2/' -e 's/aarch64$/arm64/')" &&
  KREW="krew-${OS}_${ARCH}" &&
  curl -fsSLO "https://github.com/kubernetes-sigs/krew/releases/latest/download/${KREW}.tar.gz" &&
  tar zxvf "${KREW}.tar.gz" &&
  ./"${KREW}" install krew
)

export PATH="${KREW_ROOT:-$HOME/.krew}/bin:$PATH"

kubectl krew install cnpg
```

## Erstellen einer Ressourcengruppe

Erstellen Sie mithilfe des [`az group create`][az-group-create]-Befehls eine Ressourcengruppe, die Sie in dieser Anleitung erstellen.

```bash
az group create \
    --name $RESOURCE_GROUP_NAME \
    --location $PRIMARY_CLUSTER_REGION \
    --tags $TAGS \
    --query 'properties.provisioningState' \
    --output tsv
```

## Erstellen einer benutzerseitig zugewiesenen verwalteten Identität

In diesem Abschnitt erstellen Sie eine benutzerseitig zugewiesene verwaltete Identität (UAMI), damit CNPG PostgreSQL eine AKS-Workload-Identität für den Zugriff auf Azure Blob Storage verwenden kann. Diese Konfiguration ermöglicht es dem PostgreSQL-Cluster auf AKS, sich ohne ein Geheimnis mit Azure Blob Storage zu verbinden.

1. Erstellen Sie eine benutzerseitig zugewiesene verwaltete Identität mit dem Befehl [`az identity create`][az-identity-create].

    ```bash
    AKS_UAMI_WI_IDENTITY=$(az identity create \
        --name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --output json)
    ```

1. Aktivieren Sie die AKS-Workload-Identität und erstellen Sie mit den folgenden Befehlen ein Dienstkonto, das Sie später in dieser Anleitung verwenden werden:

    ```bash
    export AKS_UAMI_WORKLOAD_OBJECTID=$( \
        echo "${AKS_UAMI_WI_IDENTITY}" | jq -r '.principalId')
    export AKS_UAMI_WORKLOAD_RESOURCEID=$( \
        echo "${AKS_UAMI_WI_IDENTITY}" | jq -r '.id')
    export AKS_UAMI_WORKLOAD_CLIENTID=$( \
        echo "${AKS_UAMI_WI_IDENTITY}" | jq -r '.clientId')

    echo "ObjectId: $AKS_UAMI_WORKLOAD_OBJECTID"
    echo "ResourceId: $AKS_UAMI_WORKLOAD_RESOURCEID"
    echo "ClientId: $AKS_UAMI_WORKLOAD_CLIENTID"
    ```

Die Objekt-ID ist ein eindeutiger Bezeichner für die Client-ID (auch bekannt als Anwendungs-ID), die ein Sicherheitsprinzipal vom Typ *Anwendung* innerhalb des Entra ID-Mandanten eindeutig identifiziert. Die Ressourcen-ID ist eine eindeutige Kennung zur Verwaltung und Lokalisierung einer Ressource in Azure. Diese Werte sind für die Aktivierung der AKS Workload-Identität erforderlich.

Der CNPG-Operator erzeugt automatisch ein Dienstkonto namens *postgres*, das Sie später in der Anleitung verwenden, um eine Anmeldeinformation zu erstellen, die den OAuth-Zugriff von PostgreSQL auf Azure Storage ermöglicht.

## Erstellen eines Speicherkontos in der primären Region

1. Erstellen Sie ein Objektspeicherkonto, um PostgreSQL-Sicherungen in der primären Region zu speichern, indem Sie den Befehl [`az storage account create`][az-storage-account-create] verwenden.

    ```bash
    az storage account create \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --sku Standard_ZRS \
        --kind StorageV2 \
        --query 'provisioningState' \
        --output tsv
    ```

1. Erstellen Sie den Speichercontainer, um die Write-Ahead-Protokolle (Write Ahead Logs, WAL) und die regelmäßigen PostgreSQL-Backups nach Bedarf und nach Zeitplan zu speichern, indem Sie den Befehl [`az storage container create`][az-storage-container-create] verwenden.

    ```bash
    az storage container create \
        --name $PG_STORAGE_BACKUP_CONTAINER_NAME \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --auth-mode login
    ```

    Beispielausgabe:

    ```output
    {
        "created": true
    }
    ```

    > [!NOTE]
    > Wenn die folgende Fehlermeldung auftritt: `The request may be blocked by network rules of storage account. Please check network rule set using 'az storage account show -n accountname --query networkRuleSet'. If you want to change the default action to apply when no rule matches, please use 'az storage account update'`. Bitte überprüfen Sie die Benutzerberechtigungen für Azure Blob Storage und erhöhen Sie **gegebenenfalls** Ihre Rolle auf `Storage Blob Data Owner`, indem Sie die unten angegebenen Befehle verwenden und anschließend den Befehl [`az storage container create`][az-storage-container-create] erneut ausführen.

    ```bash
    az role assignment list --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID --output table

    export USER_ID=$(az ad signed-in-user show --query id --output tsv)

    export STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID=$(az storage account show \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "id" \
        --output tsv)

    az role assignment create \
        --assignee-object-id $USER_ID \
        --assignee-principal-type User \
        --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID \
        --role "Storage Blob Data Owner" \
        --output tsv
    ```

## Zuweisen von RBAC zu Speicherkonten

Um Sicherungen zu ermöglichen, muss der PostgreSQL-Cluster in einen Objektspeicher lesen und schreiben. Der PostgreSQL-Cluster, der auf AKS läuft, verwendet eine Workload-Identität für den Zugriff auf das Speicherkonto über den Konfigurationsparameter [`inheritFromAzureAD`][inherit-from-azuread] des CNPG- Operators.

1. Rufen Sie die primäre Ressourcen-ID für das Speicherkonto mit dem Befehl [`az storage account show`][az-storage-account-show] ab.

    ```bash
    export STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID=$(az storage account show \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "id" \
        --output tsv)

    echo $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID
    ````

1. Weisen Sie die integrierte Azure-Rolle „Mitwirkender an Storage-Blobdaten“ der Objekt-ID mit dem Ressourcenkontobereich für die UAMI, die mit der verwalteten Identität für jeden AKS-Cluster verbunden ist, mit dem Befehl [`az role assignment create`][az-role-assignment-create] zu.

    ```bash
    az role assignment create \
        --role "Storage Blob Data Contributor" \
        --assignee-object-id $AKS_UAMI_WORKLOAD_OBJECTID \
        --assignee-principal-type ServicePrincipal \
        --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID \
        --query "id" \
        --output tsv
    ```

## Einrichten der Überwachungsinfrastruktur

In diesem Abschnitt stellen Sie eine Instanz von Azure Managed Grafana, einen Azure Monitor-Arbeitsbereich und einen Azure Monitor Log Analytics-Arbeitsbereich bereit, um die Überwachung des PostgreSQL-Clusters zu ermöglichen. Sie speichern auch Verweise auf die erstellte Überwachungsinfrastruktur, die Sie später in der Anleitung als Eingabe für die Erstellung des AKS-Clusters verwenden können. Die Bearbeitung dieses Abschnitts kann einige Zeit in Anspruch nehmen.

> [!NOTE]
> Azure Managed Grafana-Instanzen und AKS-Cluster werden unabhängig voneinander abgerechnet. Weitere Preisinformationen finden Sie unter [Preise von Azure Managed Grafana][azure-managed-grafana-pricing].

1. Erstellen Sie eine Azure Managed Grafana-Instanz mit dem Befehl [`az grafana create`][az-grafana-create].

    ```bash
    export GRAFANA_PRIMARY="grafana-${LOCAL_NAME}-${SUFFIX}"

    export GRAFANA_RESOURCE_ID=$(az grafana create \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $GRAFANA_PRIMARY \
        --location $PRIMARY_CLUSTER_REGION \
        --zone-redundancy Enabled \
        --tags $TAGS \
        --query "id" \
        --output tsv)

    echo $GRAFANA_RESOURCE_ID
    ```

1. Erstellen Sie einen Azure Monitor-Arbeitsbereich mit dem Befehl [`az monitor account create`][az-monitor-account-create].

    ```bash
    export AMW_PRIMARY="amw-${LOCAL_NAME}-${SUFFIX}"

    export AMW_RESOURCE_ID=$(az monitor account create \
        --name $AMW_PRIMARY \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --tags $TAGS \
        --query "id" \
        --output tsv)

    echo $AMW_RESOURCE_ID
    ```

1. Erstellen Sie einen Azure Monitor Log Analytics-Arbeitsbereich mit dem Befehl [`az monitor log-analytics workspace create`][az-monitor-log-analytics-workspace-create].

    ```bash
    export ALA_PRIMARY="ala-${LOCAL_NAME}-${SUFFIX}"

    export ALA_RESOURCE_ID=$(az monitor log-analytics workspace create \
        --resource-group $RESOURCE_GROUP_NAME \
        --workspace-name $ALA_PRIMARY \
        --location $PRIMARY_CLUSTER_REGION \
        --query "id" \
        --output tsv)

    echo $ALA_RESOURCE_ID
    ```

## Erstellen des AKS-Clusters zum Hosten des PostgreSQL-Clusters

In diesem Abschnitt erstellen Sie einen AKS-Cluster für mehrere Zonen mit einem Systemknotenpool. Der AKS-Cluster hostet das primäre PostgreSQL- Clusterreplikat und zwei Standbyreplikate, die jeweils auf eine andere Verfügbarkeitszone ausgerichtet sind, um zonale Redundanz zu ermöglichen.

Sie fügen auch einen Benutzerknotenpunkt zum AKS-Cluster hinzu, um den PostgreSQL-Cluster zu hosten. Die Verwendung eines separaten Knotenpools ermöglicht die Steuerelemente für die Azure VM SKUs, die für PostgreSQL verwendet werden, und ermöglicht es dem AKS-Systempool, Leistung und Kosten zu optimieren. Sie weisen dem Benutzerknotenpool eine Bezeichnung zu, auf die Sie sich bei der Knotenauswahl beziehen können, wenn Sie den CNPG-Operator später in dieser Anleitung einsetzen. Die Bearbeitung dieses Abschnitts kann einige Zeit in Anspruch nehmen.

1. Erstellen Sie mit dem Befehl [`az aks create`][az-aks-create] einen AKS-Cluster.

    ```bash
    export SYSTEM_NODE_POOL_VMSKU="standard_d2s_v3"
    export USER_NODE_POOL_NAME="postgres"
    export USER_NODE_POOL_VMSKU="standard_d4s_v3"
    
    az aks create \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --tags $TAGS \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --generate-ssh-keys \
        --node-resource-group $AKS_PRIMARY_MANAGED_RG_NAME \
        --enable-managed-identity \
        --assign-identity $AKS_UAMI_WORKLOAD_RESOURCEID \
        --network-plugin azure \
        --network-plugin-mode overlay \
        --network-dataplane cilium \
        --nodepool-name systempool \
        --enable-oidc-issuer \
        --enable-workload-identity \
        --enable-cluster-autoscaler \
        --min-count 2 \
        --max-count 3 \
        --node-vm-size $SYSTEM_NODE_POOL_VMSKU \
        --enable-azure-monitor-metrics \
        --azure-monitor-workspace-resource-id $AMW_RESOURCE_ID \
        --grafana-resource-id $GRAFANA_RESOURCE_ID \
        --api-server-authorized-ip-ranges $MY_PUBLIC_CLIENT_IP \
        --tier standard \
        --kubernetes-version $AKS_CLUSTER_VERSION \
        --zones 1 2 3 \
        --output table
    ```

2. Fügen Sie dem AKS-Cluster einen Benutzerknotenpool mit dem Befehl [`az aks nodepool add`][az-aks-node-pool-add] hinzu.

    ```bash
    az aks nodepool add \
        --resource-group $RESOURCE_GROUP_NAME \
        --cluster-name $AKS_PRIMARY_CLUSTER_NAME \
        --name $USER_NODE_POOL_NAME \
        --enable-cluster-autoscaler \
        --min-count 3 \
        --max-count 6 \
        --node-vm-size $USER_NODE_POOL_VMSKU \
        --zones 1 2 3 \
        --labels workload=postgres \
        --output table
    ```

> [!NOTE]
> Wenn Sie beim Hinzufügen des AKS-Knotenpools die Fehlermeldung `"(OperationNotAllowed) Operation is not allowed: Another operation (Updating) is in progress, please wait for it to finish before starting a new operation."` erhalten, warten Sie bitte einige Minuten, bis die AKS-Clusteroperationen abgeschlossen sind, und führen Sie dann den Befehl `az aks nodepool add` aus.

## Verbindung zum AKS-Cluster herstellen und Namespaces erstellen

In diesem Abschnitt erhalten Sie die Anmeldeinformationen für den AKS-Cluster, die als Schlüssel für die Authentifizierung und Interaktion mit dem Cluster dienen. Nach der Verbindung erstellen Sie zwei Namespaces: einen für die Dienste des CNPG-Steuerelements und einen für den PostgreSQL-Cluster und die damit verbundenen Dienste.

1. Rufen Sie die Anmeldeinformationen des AKS-Clusters mit dem Befehl [`az aks get-credentials`][az-aks-get-credentials] ab.

    ```bash
    az aks get-credentials \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --output none
     ```

2. Erstellen Sie den Namespace für die CNPG-Steuerelemente, den PostgreSQL-Cluster und die zugehörigen Dienste mit dem Befehl [`kubectl create namespace`][kubectl-create-namespace].

    ```bash
    kubectl create namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    kubectl create namespace $PG_SYSTEM_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## Aktualisieren der Überwachungsinfrastruktur

Der Azure Monitor-Arbeitsbereich für Managed Prometheus und Azure Managed Grafana werden automatisch mit dem AKS-Cluster für Metriken und Visualisierung während des Clustererstellungsprozesses verknüpft. In diesem Abschnitt aktivieren Sie die Protokollerfassung mit AKS Container Insights und überprüfen, ob Managed Prometheus die Metriken auswertet und Container Insights die Protokolle erfasst.

1. Aktivieren Sie die Überwachung von Container Insights im AKS-Cluster mithilfe des Befehls [`az aks enable-addons`][az-aks-enable-addons].

    ```bash
    az aks enable-addons \
        --addon monitoring \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --workspace-resource-id $ALA_RESOURCE_ID \
        --output table
    ```

2. Überprüfen Sie, ob Managed Prometheus Metriken abruft und Container Insights Protokolle vom AKS-Cluster erfasst, indem Sie das DaemonSet mit dem Befehl [`kubectl get`][kubectl-get] und dem Befehl [`az aks show`][az-aks-show] untersuchen.

    ```bash
    kubectl get ds ama-metrics-node \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace=kube-system

    kubectl get ds ama-logs \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace=kube-system

    az aks show \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --query addonProfiles
    ```

    Ihre Ausgabe sollte der folgenden Beispielausgabe ähneln, mit insgesamt *sechs* Knoten (drei für den Systemknotenpool und drei für den PostgreSQL-Knotenpool) und der Anzeige von `"enabled": true` in den Container Insights:

    ```output
    NAME               DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR
    ama-metrics-node   6         6         6       6            6           <none>       

    NAME               DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR
    ama-logs           6         6         6       6            6           <none>       

    {
      "omsagent": {
        "config": {
          "logAnalyticsWorkspaceResourceID": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-cnpg-9vbin3p8/providers/Microsoft.OperationalInsights/workspaces/ala-cnpg-9vbin3p8",
          "useAADAuth": "true"
        },
        "enabled": true,
        "identity": null
      }
    }
    ```

## Erstellen einer öffentlichen statischen IP für den eingehenden PostgreSQL-Cluster

Um die Bereitstellung des PostgreSQL-Clusters zu validieren und PostgreSQL-Clienttools wie *psql* und *PgAdmin* zu verwenden, müssen Sie die primären und schreibgeschützten Replikate für den Eingang freigeben. In diesem Abschnitt erstellen Sie eine öffentliche Azure-IP-Ressource, die Sie später einem Azure Load Balancer zur Verfügung stellen, um PostgreSQL-Endpunkte für Abfragen bereitzustellen.

1. Rufen Sie den Namen der AKS-Clusterknotenressourcengruppe mithilfe des Befehls [`az aks show`][az-aks-show] ab.

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME=$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query nodeResourceGroup \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME
    ```

2. Erstellen Sie die öffentliche IP-Adresse mit dem Befehl [`az network public-ip create`][az-network-public-ip-create].

    ```bash
    export AKS_PRIMARY_CLUSTER_PUBLICIP_NAME="$AKS_PRIMARY_CLUSTER_NAME-pip"

    az network public-ip create \
        --resource-group $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --name $AKS_PRIMARY_CLUSTER_PUBLICIP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --sku Standard \
        --zone 1 2 3 \
        --allocation-method static \
        --output table
    ```

3. Rufen Sie die neu erstellte öffentliche IP-Adresse mithilfe des Befehls [`az network public-ip show`][az-network-public-ip-show] ab.

    ```bash
    export AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS=$(az network public-ip show \
        --resource-group $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --name $AKS_PRIMARY_CLUSTER_PUBLICIP_NAME \
        --query ipAddress \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS
    ```

4. Rufen Sie die Ressourcen-ID der Knotenressourcengruppe mithilfe des Befehls [`az group show`][az-group-show] ab.

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE=$(az group show --name \
        $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --query id \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE
    ```

5. Weisen Sie der UAMI-Objekt-ID die Rolle „Netzwerkmitwirkender“ mithilfe des Befehls [`az role assignment create`][az-role-assignment-create] zu.

    ```bash
    az role assignment create \
        --assignee-object-id ${AKS_UAMI_WORKLOAD_OBJECTID} \
        --assignee-principal-type ServicePrincipal \
        --role "Network Contributor" \
        --scope ${AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE}
    ```

## Installieren des CNPG-Operators im AKS-Cluster

In diesem Abschnitt installieren Sie den CNPG-Operator im AKS-Cluster mit Helm oder einem YAML-Manifest.

### [Helm](#tab/helm)

1. Fügen Sie das CNPG Helm-Repository mithilfe des Befehls [`helm repo add`][helm-repo-add] hinzu.

    ```bash
    helm repo add cnpg https://cloudnative-pg.github.io/charts
    ```

2. Aktualisieren Sie das CNPG Helm-Repository, und installieren Sie es mithilfe des Befehls [`helm upgrade`][helm-upgrade] mit der Kennzeichnung `--install` auf dem AKS-Cluster.

    ```bash
    helm upgrade --install cnpg \
        --namespace $PG_SYSTEM_NAMESPACE \
        --create-namespace \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME \
        cnpg/cloudnative-pg
    ```

3. Überprüfen Sie die Operatorinstallation im AKS-Cluster mithilfe des Befehls [`kubectl get`][kubectl-get].

    ```bash
    kubectl get deployment \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-cloudnative-pg
    ```

### [YAML](#tab/yaml)

1. Installieren Sie den CNPG-Operator im AKS-Cluster mit dem Befehl [`kubectl apply`][kubectl-apply].

    ```bash
    kubectl apply --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE \
        --server-side -f \
        https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.23/releases/cnpg-1.23.1.yaml
    ```

2. Überprüfen Sie die Operatorinstallation im AKS-Cluster mithilfe des Befehls [`kubectl get`][kubectl-get].

    ```bash
    kubectl get deployment \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-controller-manager \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

---

## Nächste Schritte

> [!div class="nextstepaction"]
> [Bereitstellen einer hoch verfügbaren PostgreSQL-Datenbank auf dem AKS-Cluster][deploy-postgresql]

## Beitragende

*Dieser Artikel wird von Microsoft verwaltet. Sie wurde ursprünglich von den folgenden Mitwirkenden* verfasst:

* Ken Kilty | Principal TPM
* Russell de Pina | Principal TPM
* Adrian Joian | Senior Customer Engineer
* Jenny Hayes | Senior Content Developer
* Carol Smith | Senior Content Developer
* Erin Schaffer | Content Developer 2

<!-- LINKS -->
[az-identity-create]: /cli/azure/identity#az-identity-create
[az-grafana-create]: /cli/azure/grafana#az-grafana-create
[postgresql-ha-deployment-overview]: ./postgresql-ha-overview.md
[az-extension-add]: /cli/azure/extension#az_extension_add
[az-group-create]: /cli/azure/group#az_group_create
[az-storage-account-create]: /cli/azure/storage/account#az_storage_account_create
[az-storage-container-create]: /cli/azure/storage/container#az_storage_container_create
[inherit-from-azuread]: https://cloudnative-pg.io/documentation/1.23/appendixes/object_stores/#azure-blob-storage
[az-storage-account-show]: /cli/azure/storage/account#az_storage_account_show
[az-role-assignment-create]: /cli/azure/role/assignment#az_role_assignment_create
[az-monitor-account-create]: /cli/azure/monitor/account#az_monitor_account_create
[az-monitor-log-analytics-workspace-create]: /cli/azure/monitor/log-analytics/workspace#az_monitor_log_analytics_workspace_create
[azure-managed-grafana-pricing]: https://azure.microsoft.com/pricing/details/managed-grafana/
[az-aks-create]: /cli/azure/aks#az_aks_create
[az-aks-node-pool-add]: /cli/azure/aks/nodepool#az_aks_nodepool_add
[az-aks-get-credentials]: /cli/azure/aks#az_aks_get_credentials
[kubectl-create-namespace]: https://kubernetes.io/docs/reference/kubectl/generated/kubectl_create/kubectl_create_namespace/
[az-aks-enable-addons]: /cli/azure/aks#az_aks_enable_addons
[kubectl-get]: https://kubernetes.io/docs/reference/kubectl/generated/kubectl_get/
[az-aks-show]: /cli/azure/aks#az_aks_show
[az-network-public-ip-create]: /cli/azure/network/public-ip#az_network_public_ip_create
[az-network-public-ip-show]: /cli/azure/network/public-ip#az_network_public_ip_show
[az-group-show]: /cli/azure/group#az_group_show
[helm-repo-add]: https://helm.sh/docs/helm/helm_repo_add/
[helm-upgrade]: https://helm.sh/docs/helm/helm_upgrade/
[kubectl-apply]: https://kubernetes.io/docs/reference/kubectl/generated/kubectl_apply/
[deploy-postgresql]: ./deploy-postgresql-ha.md
[install-krew]: https://krew.sigs.k8s.io/
[cnpg-plugin]: https://cloudnative-pg.io/documentation/current/kubectl-plugin/#using-krew
