---
title: Een infrastructuur maken voor het implementeren van een maximaal beschikbare PostgreSQL-database op AKS
description: Maak de infrastructuur die nodig is voor het implementeren van een maximaal beschikbare PostgreSQL-database op AKS met behulp van de CloudNativePG-operator.
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# Een infrastructuur maken voor het implementeren van een maximaal beschikbare PostgreSQL-database op AKS

In dit artikel maakt u de infrastructuur die nodig is voor het implementeren van een maximaal beschikbare PostgreSQL-database op AKS met behulp van de [CNPG-operator (CloudNativePG).](https://cloudnative-pg.io/)

## Voordat u begint

* Bekijk het implementatieoverzicht en zorg ervoor dat u voldoet aan alle vereisten in [Het implementeren van een maximaal beschikbare PostgreSQL-database op AKS met Azure CLI][postgresql-ha-deployment-overview].
* [Stel omgevingsvariabelen](#set-environment-variables) in voor gebruik in deze handleiding.
* [Installeer de vereiste extensies](#install-required-extensions).

## Omgevingsvariabelen instellen

Stel de volgende omgevingsvariabelen in voor gebruik in deze handleiding:

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

## Vereiste extensies installeren

De `aks-preview`en `k8s-extension` `amg` extensies bieden meer functionaliteit voor het beheren van Kubernetes-clusters en het uitvoeren van query's op Azure-resources. Installeer deze extensies met behulp van de volgende [`az extension add`][az-extension-add] opdrachten:

```bash
az extension add --upgrade --name aks-preview --yes --allow-preview true
az extension add --upgrade --name k8s-extension --yes --allow-preview false
az extension add --upgrade --name amg --yes --allow-preview false
```

Als vereiste voor het gebruik van kubectl is het essentieel om Krew[ eerst te installeren][install-krew], gevolgd door de installatie van de [CNPG-invoegtoepassing][cnpg-plugin]. Hiermee schakelt u het beheer van de PostgreSQL-operator in met behulp van de volgende opdrachten.

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

## Een brongroep maken

Maak een resourcegroep voor het opslaan van de resources die u in deze handleiding maakt met behulp van de [`az group create`][az-group-create] opdracht.

```bash
az group create \
    --name $RESOURCE_GROUP_NAME \
    --location $PRIMARY_CLUSTER_REGION \
    --tags $TAGS \
    --query 'properties.provisioningState' \
    --output tsv
```

## Een door de gebruiker toegewezen beheerde identiteit maken

In deze sectie maakt u een door de gebruiker toegewezen beheerde identiteit (UAMI) om de CNPG PostgreSQL toe te staan een AKS-workloadidentiteit te gebruiken voor toegang tot Azure Blob Storage. Met deze configuratie kan het PostgreSQL-cluster in AKS zonder geheim verbinding maken met Azure Blob Storage.

1. Maak een door de gebruiker toegewezen beheerde identiteit met behulp van de [`az identity create`][az-identity-create] opdracht.

    ```bash
    AKS_UAMI_WI_IDENTITY=$(az identity create \
        --name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --output json)
    ```

1. Schakel AKS-workloadidentiteit in en genereer een serviceaccount om later in deze handleiding te gebruiken met behulp van de volgende opdrachten:

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

De object-id is een unieke id voor de client-id (ook wel de toepassings-id genoemd) waarmee een beveiligingsprincipaal van het type *Toepassing* in de Entra ID-tenant uniek wordt geïdentificeerd. De resource-id is een unieke id voor het beheren en vinden van een resource in Azure. Deze waarden zijn vereist voor het inschakelen van AKS-workloadidentiteit.

De CNPG-operator genereert automatisch een serviceaccount met de naam *postgres* dat u later in de handleiding gebruikt om een federatieve referentie te maken die OAuth-toegang vanuit PostgreSQL naar Azure Storage mogelijk maakt.

## Een opslagaccount maken in de primaire regio

1. Maak een objectopslagaccount voor het opslaan van PostgreSQL-back-ups in de primaire regio met behulp van de [`az storage account create`][az-storage-account-create] opdracht.

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

1. Maak de opslagcontainer om de Write Ahead Logs (WAL) en reguliere PostgreSQL on-demand en geplande back-ups op te slaan met behulp van de [`az storage container create`][az-storage-container-create] opdracht.

    ```bash
    az storage container create \
        --name $PG_STORAGE_BACKUP_CONTAINER_NAME \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --auth-mode login
    ```

    Voorbeelduitvoer:

    ```output
    {
        "created": true
    }
    ```

    > [!NOTE]
    > Als u het foutbericht krijgt: `The request may be blocked by network rules of storage account. Please check network rule set using 'az storage account show -n accountname --query networkRuleSet'. If you want to change the default action to apply when no rule matches, please use 'az storage account update'`. Controleer de gebruikersmachtigingen voor Azure Blob Storage en **verhoog indien nodig** uw rol met `Storage Blob Data Owner` behulp van de onderstaande opdrachten en voer de opdracht opnieuw [`az storage container create`][az-storage-container-create] uit.

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

## RBAC toewijzen aan opslagaccounts

Als u back-ups wilt inschakelen, moet het PostgreSQL-cluster lezen en schrijven naar een objectarchief. Het PostgreSQL-cluster dat wordt uitgevoerd op AKS maakt gebruik van een workloadidentiteit voor toegang tot het opslagaccount via de configuratieparameter [`inheritFromAzureAD`][inherit-from-azuread]van de CNPG-operator.

1. Haal de primaire resource-id voor het opslagaccount op met behulp van de [`az storage account show`][az-storage-account-show] opdracht.

    ```bash
    export STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID=$(az storage account show \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "id" \
        --output tsv)

    echo $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID
    ````

1. Wijs de ingebouwde Azure-rol 'Inzender voor opslagblobgegevens' toe aan de object-id met het resource-id-bereik van het opslagaccount voor de UAMI die is gekoppeld aan de beheerde identiteit voor elk AKS-cluster met behulp van de [`az role assignment create`][az-role-assignment-create] opdracht.

    ```bash
    az role assignment create \
        --role "Storage Blob Data Contributor" \
        --assignee-object-id $AKS_UAMI_WORKLOAD_OBJECTID \
        --assignee-principal-type ServicePrincipal \
        --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID \
        --query "id" \
        --output tsv
    ```

## Bewakingsinfrastructuur instellen

In deze sectie implementeert u een exemplaar van Azure Managed Grafana, een Azure Monitor-werkruimte en een Azure Monitor Log Analytics-werkruimte om bewaking van het PostgreSQL-cluster mogelijk te maken. U slaat ook verwijzingen op naar de gemaakte bewakingsinfrastructuur die moet worden gebruikt als invoer tijdens het maken van het AKS-cluster verderop in de handleiding. Het kan enige tijd duren voordat deze sectie is voltooid.

> [!NOTE]
> Azure Managed Grafana-exemplaren en AKS-clusters worden onafhankelijk gefactureerd. Zie prijzen voor Azure Managed Grafana voor meer informatie over [prijzen][azure-managed-grafana-pricing].

1. Maak een Azure Managed Grafana-exemplaar met behulp van de [`az grafana create`][az-grafana-create] opdracht.

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

1. Maak een Azure Monitor-werkruimte met behulp van de [`az monitor account create`][az-monitor-account-create] opdracht.

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

1. Maak een Azure Monitor Log Analytics-werkruimte met behulp van de [`az monitor log-analytics workspace create`][az-monitor-log-analytics-workspace-create] opdracht.

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

## Het AKS-cluster maken om het PostgreSQL-cluster te hosten

In deze sectie maakt u een AKS-cluster met meerdere zones met een systeemknooppuntgroep. Het AKS-cluster fungeert als host voor de primaire replica van het PostgreSQL-cluster en twee stand-byreplica's, die elk zijn uitgelijnd op een andere beschikbaarheidszone om zonegebonden redundantie mogelijk te maken.

U voegt ook een gebruikersknooppuntgroep toe aan het AKS-cluster om het PostgreSQL-cluster te hosten. Met behulp van een afzonderlijke knooppuntgroep kunt u controle krijgen over de Azure VM-SKU's die worden gebruikt voor PostgreSQL en zorgt u ervoor dat de AKS-systeemgroep de prestaties en kosten optimaliseert. U past een label toe op de gebruikersknooppuntgroep waarnaar u kunt verwijzen voor knooppuntselectie bij het implementeren van de CNPG-operator verderop in deze handleiding. Het kan enige tijd duren voordat deze sectie is voltooid.

1. Maak een AKS-cluster met behulp van de [`az aks create`][az-aks-create] opdracht.

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

2. Voeg een gebruikersknooppuntgroep toe aan het AKS-cluster met behulp van de [`az aks nodepool add`][az-aks-node-pool-add] opdracht.

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
> Als u het foutbericht `"(OperationNotAllowed) Operation is not allowed: Another operation (Updating) is in progress, please wait for it to finish before starting a new operation."` ontvangt bij het toevoegen van de AKS-knooppuntgroep, wacht u enkele minuten totdat de AKS-clusterbewerkingen zijn voltooid en voert u de `az aks nodepool add` opdracht uit.

## Verbinding maken met het AKS-cluster en naamruimten maken

In deze sectie krijgt u de AKS-clusterreferenties, die fungeren als de sleutels waarmee u het cluster kunt verifiëren en ermee kunt werken. Zodra u verbinding hebt gemaakt, maakt u twee naamruimten: één voor de CNPG Controller Manager-services en één voor het PostgreSQL-cluster en de bijbehorende services.

1. Haal de AKS-clusterreferenties op met behulp van de [`az aks get-credentials`][az-aks-get-credentials] opdracht.

    ```bash
    az aks get-credentials \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --output none
     ```

2. Maak de naamruimte voor de SERVICES van CNPG Controller Manager, het PostgreSQL-cluster en de bijbehorende services met behulp van de [`kubectl create namespace`][kubectl-create-namespace] opdracht.

    ```bash
    kubectl create namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    kubectl create namespace $PG_SYSTEM_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## De bewakingsinfrastructuur bijwerken

De Azure Monitor-werkruimte voor Managed Prometheus en Azure Managed Grafana worden automatisch gekoppeld aan het AKS-cluster voor metrische gegevens en visualisatie tijdens het maken van het cluster. In deze sectie schakelt u logboekverzameling met AKS Container Insights in en controleert u of Managed Prometheus metrische gegevens scrapt en Container Insights logboeken opneemt.

1. Schakel Container Insights-bewaking in op het AKS-cluster met behulp van de [`az aks enable-addons`][az-aks-enable-addons] opdracht.

    ```bash
    az aks enable-addons \
        --addon monitoring \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --workspace-resource-id $ALA_RESOURCE_ID \
        --output table
    ```

2. Controleer of Managed Prometheus metrische gegevens scrapt en Container Insights logboeken uit het AKS-cluster opneemt door de DaemonSet te inspecteren met behulp van de [`kubectl get`][kubectl-get] opdracht en de [`az aks show`][az-aks-show] opdracht.

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

    Uw uitvoer moet lijken op de volgende voorbeelduitvoer, met *zes* knooppunten in totaal (drie voor de systeemknooppuntgroep en drie voor de PostgreSQL-knooppuntgroep) en de containerinzichten die worden weergegeven `"enabled": true`:

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

## Een openbaar statisch IP-adres voor inkomend PostgreSQL-cluster maken

Als u de implementatie van het PostgreSQL-cluster wilt valideren en Client PostgreSQL-hulpprogramma's, zoals *psql* en *PgAdmin*, wilt gebruiken, moet u de primaire en alleen-lezen replica's beschikbaar maken voor inkomend verkeer. In deze sectie maakt u een openbare IP-resource van Azure die u later aan een Azure Load Balancer levert om PostgreSQL-eindpunten beschikbaar te maken voor query's.

1. Haal de naam van de resourcegroep van het AKS-clusterknooppunt op met behulp van de [`az aks show`][az-aks-show] opdracht.

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME=$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query nodeResourceGroup \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME
    ```

2. Maak het openbare IP-adres met behulp van de [`az network public-ip create`][az-network-public-ip-create] opdracht.

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

3. Haal het zojuist gemaakte openbare IP-adres op met behulp van de [`az network public-ip show`][az-network-public-ip-show] opdracht.

    ```bash
    export AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS=$(az network public-ip show \
        --resource-group $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --name $AKS_PRIMARY_CLUSTER_PUBLICIP_NAME \
        --query ipAddress \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS
    ```

4. Haal de resource-id van de knooppuntresourcegroep op met behulp van de [`az group show`][az-group-show] opdracht.

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE=$(az group show --name \
        $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --query id \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE
    ```

5. Wijs de rol Netwerkbijdrager toe aan de UAMI-object-id met behulp van het bereik van de knooppuntresourcegroep met behulp van de [`az role assignment create`][az-role-assignment-create] opdracht.

    ```bash
    az role assignment create \
        --assignee-object-id ${AKS_UAMI_WORKLOAD_OBJECTID} \
        --assignee-principal-type ServicePrincipal \
        --role "Network Contributor" \
        --scope ${AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE}
    ```

## De CNPG-operator installeren in het AKS-cluster

In deze sectie installeert u de CNPG-operator in het AKS-cluster met behulp van Helm of een YAML-manifest.

### [Helm](#tab/helm)

1. Voeg de CNPG Helm-opslagplaats toe met behulp van de [`helm repo add`][helm-repo-add] opdracht.

    ```bash
    helm repo add cnpg https://cloudnative-pg.github.io/charts
    ```

2. Werk de CNPG Helm-opslagplaats bij en installeer deze op het AKS-cluster met behulp van de [`helm upgrade`][helm-upgrade] opdracht met de `--install` vlag.

    ```bash
    helm upgrade --install cnpg \
        --namespace $PG_SYSTEM_NAMESPACE \
        --create-namespace \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME \
        cnpg/cloudnative-pg
    ```

3. Controleer de operatorinstallatie op het AKS-cluster met behulp van de [`kubectl get`][kubectl-get] opdracht.

    ```bash
    kubectl get deployment \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-cloudnative-pg
    ```

### [YAML](#tab/yaml)

1. Installeer de CNPG-operator op het AKS-cluster met behulp van de [`kubectl apply`][kubectl-apply] opdracht.

    ```bash
    kubectl apply --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE \
        --server-side -f \
        https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.23/releases/cnpg-1.23.1.yaml
    ```

2. Controleer de operatorinstallatie op het AKS-cluster met behulp van de [`kubectl get`][kubectl-get] opdracht.

    ```bash
    kubectl get deployment \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-controller-manager \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

---

## Volgende stappen

> [!div class="nextstepaction"]
> [Een maximaal beschikbare PostgreSQL-database implementeren in het AKS-cluster][deploy-postgresql]

## Medewerkers

*Dit artikel wordt onderhouden door Microsoft. Het is oorspronkelijk geschreven door de volgende inzenders*:

* Ken Kilty | Principal TPM
* Russell de Tina | Principal TPM
* Adrian Joian | Senior klanttechnicus
* Jenny Hayes | Senior Content Developer
* Carol Smith | Senior Content Developer
* Erin Schaffer | Inhoudsontwikkelaar 2

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
