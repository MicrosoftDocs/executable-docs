---
title: Skapa infrastruktur för att distribuera en PostgreSQL-databas med hög tillgänglighet på AKS
description: Skapa den infrastruktur som behövs för att distribuera en PostgreSQL-databas med hög tillgänglighet på AKS med hjälp av CloudNativePG-operatorn.
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# Skapa infrastruktur för att distribuera en PostgreSQL-databas med hög tillgänglighet på AKS

I den här artikeln skapar du den infrastruktur som behövs för att distribuera en PostgreSQL-databas med hög tillgänglighet på AKS med hjälp av operatören [CloudNativePG (CNPG).](https://cloudnative-pg.io/)

## Innan du börjar

* Granska distributionsöversikten och se till att du uppfyller alla krav i [Så här distribuerar du en PostgreSQL-databas med hög tillgänglighet i AKS med Azure CLI][postgresql-ha-deployment-overview].
* [Ange miljövariabler](#set-environment-variables) som ska användas i den här guiden.
* [Installera de tillägg](#install-required-extensions) som krävs.

## Ange miljövariabler

Ange följande miljövariabler för användning i den här guiden:

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

## Installera nödvändiga tillägg

Tilläggen `aks-preview`och `amg` `k8s-extension` ger fler funktioner för att hantera Kubernetes-kluster och köra frågor mot Azure-resurser. Installera dessa tillägg med hjälp av följande [`az extension add`][az-extension-add] kommandon:

```bash
az extension add --upgrade --name aks-preview --yes --allow-preview true
az extension add --upgrade --name k8s-extension --yes --allow-preview false
az extension add --upgrade --name amg --yes --allow-preview false
```

Som en förutsättning för att använda kubectl är det viktigt att först installera [Krew][install-krew], följt av installationen av [CNPG-plugin-programmet][cnpg-plugin]. Detta aktiverar hanteringen av PostgreSQL-operatorn med hjälp av efterföljande kommandon.

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

## Skapa en resursgrupp

Skapa en resursgrupp för att lagra de resurser som du skapar i den här guiden med hjälp av [`az group create`][az-group-create] kommandot .

```bash
az group create \
    --name $RESOURCE_GROUP_NAME \
    --location $PRIMARY_CLUSTER_REGION \
    --tags $TAGS \
    --query 'properties.provisioningState' \
    --output tsv
```

## Skapa en användartilldelad hanterad identitet

I det här avsnittet skapar du en användartilldelad hanterad identitet (UAMI) så att CNPG PostgreSQL kan använda en AKS-arbetsbelastningsidentitet för åtkomst till Azure Blob Storage. Med den här konfigurationen kan PostgreSQL-klustret på AKS ansluta till Azure Blob Storage utan hemlighet.

1. Skapa en användartilldelad hanterad identitet med kommandot [`az identity create`][az-identity-create] .

    ```bash
    AKS_UAMI_WI_IDENTITY=$(az identity create \
        --name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --output json)
    ```

1. Aktivera AKS-arbetsbelastningsidentitet och generera ett tjänstkonto som ska användas senare i den här guiden med hjälp av följande kommandon:

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

Objekt-ID:t är en unik identifierare för klient-ID :t (även kallat program-ID) som unikt identifierar ett säkerhetsobjekt av typen *Program* i Entra-ID-klientorganisationen. Resurs-ID:t är en unik identifierare för att hantera och hitta en resurs i Azure. Dessa värden krävs för aktiverad AKS-arbetsbelastningsidentitet.

CNPG-operatorn genererar automatiskt ett tjänstkonto med namnet *postgres* som du använder senare i guiden för att skapa en federerad autentiseringsuppgift som möjliggör OAuth-åtkomst från PostgreSQL till Azure Storage.

## Skapa ett lagringskonto i den primära regionen

1. Skapa ett objektlagringskonto för att lagra PostgreSQL-säkerhetskopior i den primära regionen med kommandot [`az storage account create`][az-storage-account-create] .

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

1. Skapa lagringscontainern för att lagra WAL (Write Ahead Logs) och vanliga PostgreSQL på begäran och schemalagda säkerhetskopieringar med kommandot [`az storage container create`][az-storage-container-create] .

    ```bash
    az storage container create \
        --name $PG_STORAGE_BACKUP_CONTAINER_NAME \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --auth-mode login
    ```

    Exempel på utdata>

    ```output
    {
        "created": true
    }
    ```

    > [!NOTE]
    > Om du får felmeddelandet: `The request may be blocked by network rules of storage account. Please check network rule set using 'az storage account show -n accountname --query networkRuleSet'. If you want to change the default action to apply when no rule matches, please use 'az storage account update'`. Kontrollera användarbehörigheterna för Azure Blob Storage och, om **det behövs**, höja din roll till att `Storage Blob Data Owner` använda kommandona nedan och efter att du har provat kommandot igen [`az storage container create`][az-storage-container-create] .

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

## Tilldela RBAC till lagringskonton

För att aktivera säkerhetskopior måste PostgreSQL-klustret läsa och skriva till ett objektarkiv. PostgreSQL-klustret som körs på AKS använder en arbetsbelastningsidentitet för att komma åt lagringskontot via konfigurationsparametern [`inheritFromAzureAD`][inherit-from-azuread]FÖR CNPG-operatör .

1. Hämta det primära resurs-ID:t för lagringskontot med kommandot [`az storage account show`][az-storage-account-show] .

    ```bash
    export STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID=$(az storage account show \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "id" \
        --output tsv)

    echo $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID
    ````

1. Tilldela den inbyggda rollen "Storage Blob Data Contributor" till objekt-ID:t med resurs-ID:t för lagringskontot för UAMI som är associerad med den hanterade identiteten för varje AKS-kluster med kommandot [`az role assignment create`][az-role-assignment-create] .

    ```bash
    az role assignment create \
        --role "Storage Blob Data Contributor" \
        --assignee-object-id $AKS_UAMI_WORKLOAD_OBJECTID \
        --assignee-principal-type ServicePrincipal \
        --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID \
        --query "id" \
        --output tsv
    ```

## Konfigurera övervakningsinfrastruktur

I det här avsnittet distribuerar du en instans av Azure Managed Grafana, en Azure Monitor-arbetsyta och en Azure Monitor Log Analytics-arbetsyta för att aktivera övervakning av PostgreSQL-klustret. Du lagrar även referenser till den skapade övervakningsinfrastrukturen som ska användas som indata under processen för att skapa AKS-kluster senare i guiden. Det här avsnittet kan ta lite tid att slutföra.

> [!NOTE]
> Azure Managed Grafana-instanser och AKS-kluster faktureras separat. Mer prisinformation finns i [Priser][azure-managed-grafana-pricing] för Azure Managed Grafana.

1. Skapa en Azure Managed Grafana-instans med kommandot [`az grafana create`][az-grafana-create] .

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

1. Skapa en Azure Monitor-arbetsyta med kommandot [`az monitor account create`][az-monitor-account-create] .

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

1. Skapa en Azure Monitor Log Analytics-arbetsyta med kommandot [`az monitor log-analytics workspace create`][az-monitor-log-analytics-workspace-create] .

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

## Skapa AKS-klustret som värd för PostgreSQL-klustret

I det här avsnittet skapar du ett AKS-kluster med flera zoner med en systemnodpool. AKS-klustret är värd för PostgreSQL-klustrets primära replik och två väntelägesrepliker, var och en justerad till en annan tillgänglighetszon för att aktivera zonredundans.

Du lägger också till en användarnodpool i AKS-klustret som värd för PostgreSQL-klustret. Med hjälp av en separat nodpool kan du styra över de virtuella Azure VM-SKU:er som används för PostgreSQL och gör det möjligt för AKS-systempoolen att optimera prestanda och kostnader. Du använder en etikett för användarnodpoolen som du kan referera till för nodval när du distribuerar CNPG-operatorn senare i den här guiden. Det här avsnittet kan ta lite tid att slutföra.

1. Skapa ett AKS-kluster med kommandot [`az aks create`][az-aks-create] .

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

2. Lägg till en användarnodpool i AKS-klustret med kommandot [`az aks nodepool add`][az-aks-node-pool-add] .

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
> Om du får felmeddelandet `"(OperationNotAllowed) Operation is not allowed: Another operation (Updating) is in progress, please wait for it to finish before starting a new operation."` när du lägger till AKS-nodpoolen väntar du några minuter på att AKS-klusteråtgärderna ska slutföras och kör `az aks nodepool add` sedan kommandot.

## Anslut till AKS-klustret och skapa namnområden

I det här avsnittet får du autentiseringsuppgifterna för AKS-klustret, som fungerar som de nycklar som gör att du kan autentisera och interagera med klustret. När du är ansluten skapar du två namnområden: en för CNPG-styrenhetshanterarens tjänster och en för PostgreSQL-klustret och dess relaterade tjänster.

1. Hämta autentiseringsuppgifterna för AKS-klustret med hjälp av [`az aks get-credentials`][az-aks-get-credentials] kommandot .

    ```bash
    az aks get-credentials \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --output none
     ```

2. Skapa namnområdet för CNPG-styrenhetshanterarens tjänster, PostgreSQL-klustret och dess relaterade tjänster med hjälp [`kubectl create namespace`][kubectl-create-namespace] av kommandot .

    ```bash
    kubectl create namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    kubectl create namespace $PG_SYSTEM_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## Uppdatera övervakningsinfrastrukturen

Azure Monitor-arbetsytan för Managed Prometheus och Azure Managed Grafana länkas automatiskt till AKS-klustret för mått och visualisering under processen för att skapa kluster. I det här avsnittet aktiverar du logginsamling med AKS Container-insikter och verifierar att Managed Prometheus skrapar mått och containerinsikter matar in loggar.

1. Aktivera Övervakning av containerinsikter i AKS-klustret med hjälp av [`az aks enable-addons`][az-aks-enable-addons] kommandot .

    ```bash
    az aks enable-addons \
        --addon monitoring \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --workspace-resource-id $ALA_RESOURCE_ID \
        --output table
    ```

2. Kontrollera att Managed Prometheus skrapar mått och containerinsikter matar in loggar från AKS-klustret genom att inspektera DaemonSet med kommandot [`kubectl get`][kubectl-get] och [`az aks show`][az-aks-show] kommandot .

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

    Dina utdata bör likna följande exempelutdata, med *totalt sex* noder (tre för systemnodpoolen och tre för PostgreSQL-nodpoolen) och containerinsikterna som visar `"enabled": true`:

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

## Skapa en offentlig statisk IP-adress för PostgreSQL-klusteringress

För att verifiera distributionen av PostgreSQL-klustret och använda postgreSQL-klientverktyg, till exempel *psql* och *PgAdmin*, måste du exponera de primära och skrivskyddade replikerna för ingress. I det här avsnittet skapar du en offentlig IP-resurs i Azure som du senare tillhandahåller till en Azure-lastbalanserare för att exponera PostgreSQL-slutpunkter för frågor.

1. Hämta namnet på resursgruppen för AKS-klusternoden [`az aks show`][az-aks-show] med hjälp av kommandot .

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME=$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query nodeResourceGroup \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME
    ```

2. Skapa den offentliga IP-adressen med kommandot [`az network public-ip create`][az-network-public-ip-create] .

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

3. Hämta den nyligen skapade offentliga IP-adressen med kommandot [`az network public-ip show`][az-network-public-ip-show] .

    ```bash
    export AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS=$(az network public-ip show \
        --resource-group $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --name $AKS_PRIMARY_CLUSTER_PUBLICIP_NAME \
        --query ipAddress \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS
    ```

4. Hämta resurs-ID:t för nodresursgruppen med kommandot [`az group show`][az-group-show] .

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE=$(az group show --name \
        $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --query id \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE
    ```

5. Tilldela rollen "Nätverksdeltagare" till UAMI-objekt-ID:t med hjälp av nodresursgruppens omfång med kommandot [`az role assignment create`][az-role-assignment-create] .

    ```bash
    az role assignment create \
        --assignee-object-id ${AKS_UAMI_WORKLOAD_OBJECTID} \
        --assignee-principal-type ServicePrincipal \
        --role "Network Contributor" \
        --scope ${AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE}
    ```

## Installera CNPG-operatorn i AKS-klustret

I det här avsnittet installerar du CNPG-operatorn i AKS-klustret med hjälp av Helm eller ett YAML-manifest.

### [Helm](#tab/helm)

1. Lägg till CNPG Helm-lagringsplatsen med kommandot [`helm repo add`][helm-repo-add] .

    ```bash
    helm repo add cnpg https://cloudnative-pg.github.io/charts
    ```

2. Uppgradera CNPG Helm-lagringsplatsen och installera den på AKS-klustret med kommandot [`helm upgrade`][helm-upgrade] med `--install` flaggan .

    ```bash
    helm upgrade --install cnpg \
        --namespace $PG_SYSTEM_NAMESPACE \
        --create-namespace \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME \
        cnpg/cloudnative-pg
    ```

3. Kontrollera operatörsinstallationen i AKS-klustret med hjälp av [`kubectl get`][kubectl-get] kommandot .

    ```bash
    kubectl get deployment \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-cloudnative-pg
    ```

### [YAML](#tab/yaml)

1. Installera CNPG-operatorn i AKS-klustret med kommandot [`kubectl apply`][kubectl-apply] .

    ```bash
    kubectl apply --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE \
        --server-side -f \
        https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.23/releases/cnpg-1.23.1.yaml
    ```

2. Kontrollera operatörsinstallationen i AKS-klustret med hjälp av [`kubectl get`][kubectl-get] kommandot .

    ```bash
    kubectl get deployment \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-controller-manager \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

---

## Nästa steg

> [!div class="nextstepaction"]
> [Distribuera en PostgreSQL-databas med hög tillgänglighet i AKS-klustret][deploy-postgresql]

## Deltagare

*Den här artikeln underhålls av Microsoft. Den skrevs ursprungligen av följande deltagare*:

* Ken Kilty | Huvudnamn för TPM
* Russell de Pina | Huvudnamn för TPM
* Adrian Joian | Senior kundtekniker
* Jenny Hayes | Senior innehållsutvecklare
* Carol Smith | Senior innehållsutvecklare
* Erin Schaffer | Innehållsutvecklare 2

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
