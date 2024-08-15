---
title: Vytvoření infrastruktury pro nasazení vysoce dostupné databáze PostgreSQL v AKS
description: Vytvořte infrastrukturu potřebnou k nasazení vysoce dostupné databáze PostgreSQL v AKS pomocí operátoru CloudNativePG.
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# Vytvoření infrastruktury pro nasazení vysoce dostupné databáze PostgreSQL v AKS

V tomto článku vytvoříte infrastrukturu potřebnou k nasazení vysoce dostupné databáze PostgreSQL v AKS pomocí operátoru [CloudNativePG (CNPG](https://cloudnative-pg.io/) ).

## Než začnete

* Projděte si přehled nasazení a ujistěte se, že splňujete všechny požadavky v [tématu Nasazení vysoce dostupné databáze PostgreSQL v AKS pomocí Azure CLI][postgresql-ha-deployment-overview].
* [Nastavte proměnné](#set-environment-variables) prostředí pro použití v tomto průvodci.
* [Nainstalujte požadovaná rozšíření](#install-required-extensions).

## Nastavení proměnných prostředí

V tomto průvodci nastavte následující proměnné prostředí:

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

## Instalace požadovaných rozšíření

`k8s-extension` Rozšíření `aks-preview`poskytují `amg` další funkce pro správu clusterů Kubernetes a dotazování prostředků Azure. Nainstalujte tato rozšíření pomocí následujících [`az extension add`][az-extension-add] příkazů:

```bash
az extension add --upgrade --name aks-preview --yes --allow-preview true
az extension add --upgrade --name k8s-extension --yes --allow-preview false
az extension add --upgrade --name amg --yes --allow-preview false
```

Jako předpoklad pro použití kubectl je nezbytné nejprve nainstalovat [Krew][install-krew], následovaný instalací [modulu plug-in][cnpg-plugin] CNPG. To umožní správu operátoru PostgreSQL pomocí následujících příkazů.

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

## Vytvoření skupiny zdrojů

Pomocí příkazu vytvořte skupinu prostředků, která bude obsahovat prostředky, které vytvoříte v této příručce [`az group create`][az-group-create] .

```bash
az group create \
    --name $RESOURCE_GROUP_NAME \
    --location $PRIMARY_CLUSTER_REGION \
    --tags $TAGS \
    --query 'properties.provisioningState' \
    --output tsv
```

## Vytvoření spravované identity přiřazené uživatelem

V této části vytvoříte spravovanou identitu přiřazenou uživatelem (UAMI), která umožní CNPG PostgreSQL používat identitu úlohy AKS pro přístup ke službě Azure Blob Storage. Tato konfigurace umožňuje clusteru PostgreSQL v AKS připojit se ke službě Azure Blob Storage bez tajného kódu.

1. Pomocí příkazu vytvořte spravovanou identitu přiřazenou uživatelem [`az identity create`][az-identity-create] .

    ```bash
    AKS_UAMI_WI_IDENTITY=$(az identity create \
        --name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --output json)
    ```

1. Pomocí následujících příkazů povolte identitu úloh AKS a vygenerujte účet služby pro pozdější použití v této příručce:

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

ID objektu je jedinečný identifikátor ID klienta (označovaného také jako ID aplikace), který jednoznačně identifikuje objekt zabezpečení typu *Aplikace* v tenantovi Entra ID. ID prostředku je jedinečný identifikátor pro správu a vyhledání prostředku v Azure. Tyto hodnoty jsou potřeba k povolení identity úloh AKS.

Operátor CNPG automaticky vygeneruje účet služby s názvem *postgres* , který použijete později v průvodci k vytvoření federovaných přihlašovacích údajů, které umožňují přístup K OAuth z PostgreSQL do Azure Storage.

## Vytvoření účtu úložiště v primární oblasti

1. Pomocí příkazu vytvořte účet úložiště objektů pro ukládání záloh PostgreSQL v primární oblasti [`az storage account create`][az-storage-account-create] .

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

1. Vytvořte kontejner úložiště, do kterého se budou ukládat protokoly wal (Write Ahead Logs) a pravidelné postgreSQL na vyžádání a plánované zálohování pomocí [`az storage container create`][az-storage-container-create] příkazu.

    ```bash
    az storage container create \
        --name $PG_STORAGE_BACKUP_CONTAINER_NAME \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --auth-mode login
    ```

    Příklad výstupu:

    ```output
    {
        "created": true
    }
    ```

    > [!NOTE]
    > Pokud se zobrazí chybová zpráva: `The request may be blocked by network rules of storage account. Please check network rule set using 'az storage account show -n accountname --query networkRuleSet'. If you want to change the default action to apply when no rule matches, please use 'az storage account update'`. Ověřte uživatelská oprávnění pro Azure Blob Storage a v případě **potřeby zvyšte svoji roli `Storage Blob Data Owner` pomocí níže uvedených příkazů a po opakování [`az storage container create`][az-storage-container-create] příkazu.**

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

## Přiřazení RBAC k účtům úložiště

Aby bylo možné povolit zálohování, musí cluster PostgreSQL číst a zapisovat do úložiště objektů. Cluster PostgreSQL spuštěný v AKS používá identitu úlohy pro přístup k účtu úložiště prostřednictvím konfiguračního parametru [`inheritFromAzureAD`][inherit-from-azuread]operátoru CNPG .

1. Pomocí příkazu získejte ID primárního prostředku pro účet [`az storage account show`][az-storage-account-show] úložiště.

    ```bash
    export STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID=$(az storage account show \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "id" \
        --output tsv)

    echo $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID
    ````

1. Přiřaďte předdefinované roli Azure Přispěvatel dat objektů blob úložiště k ID objektu s oborem ID prostředku účtu úložiště pro UAMI přidruženou ke spravované identitě pro každý cluster AKS pomocí [`az role assignment create`][az-role-assignment-create] příkazu.

    ```bash
    az role assignment create \
        --role "Storage Blob Data Contributor" \
        --assignee-object-id $AKS_UAMI_WORKLOAD_OBJECTID \
        --assignee-principal-type ServicePrincipal \
        --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID \
        --query "id" \
        --output tsv
    ```

## Nastavení infrastruktury monitorování

V této části nasadíte instanci Azure Managed Grafana, pracovního prostoru Azure Monitoru a pracovního prostoru služby Azure Monitor Log Analytics, abyste umožnili monitorování clusteru PostgreSQL. Také uložíte odkazy na vytvořenou monitorovací infrastrukturu, která se použije jako vstup během procesu vytváření clusteru AKS později v průvodci. Dokončení této části může nějakou dobu trvat.

> [!NOTE]
> Instance a clustery AKS spravované v Azure Grafana se účtují nezávisle na sobě. Další informace o cenách najdete v tématu [o cenách][azure-managed-grafana-pricing] služby Azure Managed Grafana.

1. Pomocí příkazu vytvořte spravovanou instanci [`az grafana create`][az-grafana-create] Grafana Azure.

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

1. Pomocí příkazu vytvořte pracovní prostor Azure Monitoru [`az monitor account create`][az-monitor-account-create] .

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

1. Pomocí příkazu vytvořte pracovní prostor [`az monitor log-analytics workspace create`][az-monitor-log-analytics-workspace-create] služby Azure Monitor Log Analytics.

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

## Vytvoření clusteru AKS pro hostování clusteru PostgreSQL

V této části vytvoříte cluster AKS s vícezonem s fondem systémových uzlů. Cluster AKS hostuje primární repliku clusteru PostgreSQL a dvě pohotovostní repliky, které jsou v souladu s jinou zónou dostupnosti, aby bylo možné zónovou redundanci.

Také přidáte fond uzlů uživatele do clusteru AKS pro hostování clusteru PostgreSQL. Použití samostatného fondu uzlů umožňuje řídit skladové položky virtuálních počítačů Azure používané pro PostgreSQL a umožňuje fondu systémů AKS optimalizovat výkon a náklady. Popisek použijete u fondu uzlů uživatele, na který můžete odkazovat při nasazování operátoru CNPG dále v této příručce. Dokončení této části může nějakou dobu trvat.

1. Pomocí příkazu vytvořte cluster [`az aks create`][az-aks-create] AKS.

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

2. Přidejte fond uzlů uživatele do clusteru AKS pomocí [`az aks nodepool add`][az-aks-node-pool-add] příkazu.

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
> Pokud se při přidávání fondu uzlů AKS zobrazí chybová zpráva `"(OperationNotAllowed) Operation is not allowed: Another operation (Updating) is in progress, please wait for it to finish before starting a new operation."` , počkejte několik minut, než se operace clusteru AKS dokončí, a pak spusťte `az aks nodepool add` příkaz.

## Připojení ke clusteru AKS a vytvoření oborů názvů

V této části získáte přihlašovací údaje clusteru AKS, které slouží jako klíče, které umožňují ověřování a interakci s clusterem. Po připojení vytvoříte dva obory názvů: jeden pro služby správce kontroleru CNPG a jeden pro cluster PostgreSQL a jeho související služby.

1. Pomocí příkazu získejte přihlašovací údaje clusteru [`az aks get-credentials`][az-aks-get-credentials] AKS.

    ```bash
    az aks get-credentials \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --output none
     ```

2. Pomocí příkazu vytvořte obor názvů pro služby správce kontroleru CNPG, cluster PostgreSQL a související služby [`kubectl create namespace`][kubectl-create-namespace] .

    ```bash
    kubectl create namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    kubectl create namespace $PG_SYSTEM_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## Aktualizace infrastruktury monitorování

Pracovní prostor Azure Monitoru pro spravované prometheus a Azure Managed Grafana se automaticky propojí s clusterem AKS pro metriky a vizualizaci během procesu vytváření clusteru. V této části povolíte shromažďování protokolů pomocí přehledů kontejneru AKS a ověříte, že managed Prometheus ingestuje metriky a přehledy kontejnerů ingestují protokoly.

1. Pomocí příkazu povolte monitorování Container Insights v clusteru [`az aks enable-addons`][az-aks-enable-addons] AKS.

    ```bash
    az aks enable-addons \
        --addon monitoring \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --workspace-resource-id $ALA_RESOURCE_ID \
        --output table
    ```

2. Pomocí příkazu a příkazu ověřte, že managed Prometheus zaznamenává metriky a přehledy kontejnerů ingestují protokoly z clusteru AKS. Zkontrolujte daemonSet pomocí [`kubectl get`][kubectl-get] příkazu a [`az aks show`][az-aks-show] příkazu.

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

    Výstup by měl vypadat podobně jako v následujícím příkladu s celkovým *šesti* uzly (tři pro fond uzlů systému a tři pro fond uzlů PostgreSQL) a přehledy kontejneru ukazující `"enabled": true`:

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

## Vytvoření veřejné statické IP adresy pro příchozí přenos dat clusteru PostgreSQL

Pokud chcete ověřit nasazení clusteru PostgreSQL a používat klientské nástroje PostgreSQL, jako *je psql* a *PgAdmin*, musíte zpřístupnit primární a jen pro čtení replik pro příchozí přenos dat. V této části vytvoříte prostředek veřejné IP adresy Azure, který později zadáte do nástroje pro vyrovnávání zatížení Azure, abyste zpřístupnili koncové body PostgreSQL pro dotazy.

1. Pomocí příkazu získejte název skupiny [`az aks show`][az-aks-show] prostředků uzlu clusteru AKS.

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME=$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query nodeResourceGroup \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME
    ```

2. Pomocí příkazu vytvořte veřejnou IP adresu [`az network public-ip create`][az-network-public-ip-create] .

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

3. Pomocí příkazu získejte nově vytvořenou [`az network public-ip show`][az-network-public-ip-show] veřejnou IP adresu.

    ```bash
    export AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS=$(az network public-ip show \
        --resource-group $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --name $AKS_PRIMARY_CLUSTER_PUBLICIP_NAME \
        --query ipAddress \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS
    ```

4. Pomocí příkazu získejte ID prostředku skupiny [`az group show`][az-group-show] prostředků uzlu.

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE=$(az group show --name \
        $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --query id \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE
    ```

5. Přiřaďte roli Přispěvatel sítě k ID objektu UAMI pomocí oboru skupiny prostředků uzlu pomocí [`az role assignment create`][az-role-assignment-create] příkazu.

    ```bash
    az role assignment create \
        --assignee-object-id ${AKS_UAMI_WORKLOAD_OBJECTID} \
        --assignee-principal-type ServicePrincipal \
        --role "Network Contributor" \
        --scope ${AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE}
    ```

## Instalace operátoru CNPG v clusteru AKS

V této části nainstalujete operátor CNPG v clusteru AKS pomocí manifestu Helm nebo YAML.

### [Helm](#tab/helm)

1. Přidejte úložiště HELM CNPG pomocí [`helm repo add`][helm-repo-add] příkazu.

    ```bash
    helm repo add cnpg https://cloudnative-pg.github.io/charts
    ```

2. Upgradujte úložiště Helm CNPG a nainstalujte ho [`helm upgrade`][helm-upgrade] do clusteru AKS pomocí příkazu s příznakem `--install` .

    ```bash
    helm upgrade --install cnpg \
        --namespace $PG_SYSTEM_NAMESPACE \
        --create-namespace \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME \
        cnpg/cloudnative-pg
    ```

3. Pomocí příkazu ověřte instalaci operátora [`kubectl get`][kubectl-get] v clusteru AKS.

    ```bash
    kubectl get deployment \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-cloudnative-pg
    ```

### [YAML](#tab/yaml)

1. Pomocí příkazu nainstalujte operátor CNPG do clusteru [`kubectl apply`][kubectl-apply] AKS.

    ```bash
    kubectl apply --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE \
        --server-side -f \
        https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.23/releases/cnpg-1.23.1.yaml
    ```

2. Pomocí příkazu ověřte instalaci operátora [`kubectl get`][kubectl-get] v clusteru AKS.

    ```bash
    kubectl get deployment \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-controller-manager \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

---

## Další kroky

> [!div class="nextstepaction"]
> [Nasazení vysoce dostupné databáze PostgreSQL v clusteru AKS][deploy-postgresql]

## Přispěvatelé

*Tento článek spravuje Microsoft. Původně byla napsána následujícími přispěvateli*:

* Ken Kilty | Hlavní čip TPM
* Russell de Pina | Hlavní čip TPM
* Adrian Joian | Vedoucí zákaznický inženýr
* Jenny Hayes | Vedoucí vývojář obsahu
* Carol Smith | Vedoucí vývojář obsahu
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
