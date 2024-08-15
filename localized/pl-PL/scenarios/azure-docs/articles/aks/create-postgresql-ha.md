---
title: Tworzenie infrastruktury do wdrażania bazy danych PostgreSQL o wysokiej dostępności w usłudze AKS
description: Utwórz infrastrukturę wymaganą do wdrożenia bazy danych PostgreSQL o wysokiej dostępności w usłudze AKS przy użyciu operatora CloudNativePG.
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# Tworzenie infrastruktury do wdrażania bazy danych PostgreSQL o wysokiej dostępności w usłudze AKS

W tym artykule utworzysz infrastrukturę wymaganą do wdrożenia bazy danych PostgreSQL o wysokiej dostępności w usłudze AKS przy użyciu [operatora CloudNativePG (CNPG](https://cloudnative-pg.io/) ).

## Zanim rozpoczniesz

* Zapoznaj się z omówieniem wdrożenia i upewnij się, że zostały spełnione wszystkie wymagania wstępne w temacie [Jak wdrożyć bazę danych PostgreSQL o wysokiej dostępności w usłudze AKS przy użyciu interfejsu wiersza polecenia][postgresql-ha-deployment-overview] platformy Azure.
* [Ustaw zmienne środowiskowe](#set-environment-variables) do użycia w tym przewodniku.
* [Zainstaluj wymagane rozszerzenia](#install-required-extensions).

## Ustawianie zmiennych środowiskowych

Ustaw następujące zmienne środowiskowe do użycia w tym przewodniku:

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

## Instalowanie wymaganych rozszerzeń

`k8s-extension` Rozszerzenia `aks-preview`i `amg` zapewniają więcej funkcji zarządzania klastrami Kubernetes i wykonywania zapytań dotyczących zasobów platformy Azure. Zainstaluj te rozszerzenia przy użyciu następujących [`az extension add`][az-extension-add] poleceń:

```bash
az extension add --upgrade --name aks-preview --yes --allow-preview true
az extension add --upgrade --name k8s-extension --yes --allow-preview false
az extension add --upgrade --name amg --yes --allow-preview false
```

W ramach wymagań wstępnych dotyczących korzystania z narzędzia kubectl należy najpierw zainstalować aplikację [Krew][install-krew], a następnie zainstalować wtyczkę [][cnpg-plugin]CNPG. Umożliwi to zarządzanie operatorem PostgreSQL przy użyciu kolejnych poleceń.

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

## Tworzenie grupy zasobów

Utwórz grupę zasobów do przechowywania zasobów utworzonych w tym przewodniku [`az group create`][az-group-create] przy użyciu polecenia .

```bash
az group create \
    --name $RESOURCE_GROUP_NAME \
    --location $PRIMARY_CLUSTER_REGION \
    --tags $TAGS \
    --query 'properties.provisioningState' \
    --output tsv
```

## Tworzenie tożsamości zarządzanej przypisanej przez użytkownika

W tej sekcji utworzysz tożsamość zarządzaną przypisaną przez użytkownika (UAMI), aby umożliwić usłudze CNPG PostgreSQL używanie tożsamości obciążenia usługi AKS w celu uzyskania dostępu do usługi Azure Blob Storage. Ta konfiguracja umożliwia klastrowi PostgreSQL w usłudze AKS łączenie się z usługą Azure Blob Storage bez wpisu tajnego.

1. Utwórz tożsamość zarządzaną przypisaną przez użytkownika przy użyciu [`az identity create`][az-identity-create] polecenia .

    ```bash
    AKS_UAMI_WI_IDENTITY=$(az identity create \
        --name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --output json)
    ```

1. Włącz tożsamość obciążenia usługi AKS i wygeneruj konto usługi do użycia w dalszej części tego przewodnika przy użyciu następujących poleceń:

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

Identyfikator obiektu jest unikatowym identyfikatorem klienta (znanym również jako identyfikator aplikacji), który jednoznacznie identyfikuje podmiot zabezpieczeń typu *Aplikacja* w dzierżawie entra ID. Identyfikator zasobu jest unikatowym identyfikatorem do zarządzania i lokalizowania zasobu na platformie Azure. Te wartości są wymagane do włączenia tożsamości obciążenia usługi AKS.

Operator CNPG automatycznie generuje konto usługi o nazwie *postgres* , które jest używane w dalszej części przewodnika w celu utworzenia poświadczeń federacyjnych, które umożliwiają dostęp OAuth z bazy danych PostgreSQL do usługi Azure Storage.

## Tworzenie konta magazynu w regionie podstawowym

1. Utwórz konto magazynu obiektów do przechowywania kopii zapasowych PostgreSQL w regionie podstawowym przy użyciu [`az storage account create`][az-storage-account-create] polecenia .

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

1. Utwórz kontener magazynu do przechowywania dzienników zapisu z wyprzedzeniem (WAL) i zwykłych kopii zapasowych PostgreSQL na żądanie i zaplanowanych kopii zapasowych przy użyciu [`az storage container create`][az-storage-container-create] polecenia .

    ```bash
    az storage container create \
        --name $PG_STORAGE_BACKUP_CONTAINER_NAME \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --auth-mode login
    ```

    Przykładowe wyjście:

    ```output
    {
        "created": true
    }
    ```

    > [!NOTE]
    > Jeśli wystąpi komunikat o błędzie: `The request may be blocked by network rules of storage account. Please check network rule set using 'az storage account show -n accountname --query networkRuleSet'. If you want to change the default action to apply when no rule matches, please use 'az storage account update'`. Sprawdź uprawnienia użytkownika dla usługi Azure Blob Storage i, w razie **potrzeby**, podnieś poziom roli do `Storage Blob Data Owner` używania poleceń podanych poniżej i po ponów próbę[ ][az-storage-container-create]`az storage container create`polecenia.

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

## Przypisywanie kontroli dostępu opartej na rolach do kont magazynu

Aby umożliwić tworzenie kopii zapasowych, klaster PostgreSQL musi odczytywać i zapisywać w magazynie obiektów. Klaster PostgreSQL uruchomiony w usłudze AKS używa tożsamości obciążenia w celu uzyskania dostępu do konta magazynu za pośrednictwem parametru [`inheritFromAzureAD`][inherit-from-azuread]konfiguracji operatora CPG.

1. Pobierz identyfikator zasobu podstawowego dla konta magazynu przy użyciu [`az storage account show`][az-storage-account-show] polecenia .

    ```bash
    export STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID=$(az storage account show \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "id" \
        --output tsv)

    echo $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID
    ````

1. Przypisz wbudowaną rolę platformy Azure "Współautor danych obiektu blob usługi Storage" do identyfikatora obiektu z zakresem identyfikatora zasobu konta magazynu skojarzonym z tożsamością zarządzaną dla każdego klastra usługi AKS przy użyciu [`az role assignment create`][az-role-assignment-create] polecenia .

    ```bash
    az role assignment create \
        --role "Storage Blob Data Contributor" \
        --assignee-object-id $AKS_UAMI_WORKLOAD_OBJECTID \
        --assignee-principal-type ServicePrincipal \
        --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID \
        --query "id" \
        --output tsv
    ```

## Konfigurowanie infrastruktury monitorowania

W tej sekcji wdrożysz wystąpienie usługi Azure Managed Grafana, obszar roboczy usługi Azure Monitor i obszar roboczy usługi Azure Monitor Log Analytics, aby umożliwić monitorowanie klastra PostgreSQL. Odwołania do utworzonej infrastruktury monitorowania są również przechowywane jako dane wejściowe podczas procesu tworzenia klastra usługi AKS w dalszej części przewodnika. Ukończenie tej sekcji może zająć trochę czasu.

> [!NOTE]
> Wystąpienia zarządzane przez platformę Azure Grafana i klastry usługi AKS są rozliczane niezależnie. Aby uzyskać więcej informacji o cenach, zobacz [Cennik][azure-managed-grafana-pricing] usługi Azure Managed Grafana.

1. Utwórz wystąpienie zarządzanego narzędzia Grafana platformy [`az grafana create`][az-grafana-create] Azure przy użyciu polecenia .

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

1. Utwórz obszar roboczy usługi Azure Monitor przy użyciu [`az monitor account create`][az-monitor-account-create] polecenia .

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

1. Utwórz obszar roboczy usługi Log Analytics usługi Azure Monitor przy użyciu [`az monitor log-analytics workspace create`][az-monitor-log-analytics-workspace-create] polecenia .

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

## Tworzenie klastra usługi AKS do hostowania klastra PostgreSQL

W tej sekcji utworzysz wielostrefowy klaster usługi AKS z pulą węzłów systemowych. Klaster AKS hostuje replikę podstawową klastra PostgreSQL i dwie repliki rezerwowe, z których każda jest wyrównana do innej strefy dostępności, aby umożliwić nadmiarowość strefową.

Do klastra usługi AKS można również dodać pulę węzłów użytkownika w celu hostowania klastra PostgreSQL. Użycie oddzielnej puli węzłów umożliwia kontrolę nad jednostkami SKU maszyn wirtualnych platformy Azure używanymi na potrzeby bazy danych PostgreSQL i umożliwia puli systemu AKS optymalizowanie wydajności i kosztów. Etykietę stosuje się do puli węzłów użytkownika, do której można odwoływać się do wyboru węzła podczas wdrażania operatora CNPG w dalszej części tego przewodnika. Ukończenie tej sekcji może zająć trochę czasu.

1. Utwórz klaster usługi AKS przy użyciu [`az aks create`][az-aks-create] polecenia .

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

2. Dodaj pulę węzłów użytkownika do klastra usługi AKS przy użyciu [`az aks nodepool add`][az-aks-node-pool-add] polecenia .

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
> Jeśli podczas dodawania puli węzłów usługi AKS zostanie wyświetlony komunikat `"(OperationNotAllowed) Operation is not allowed: Another operation (Updating) is in progress, please wait for it to finish before starting a new operation."` o błędzie, zaczekaj kilka minut na ukończenie operacji klastra usługi AKS, a następnie uruchom `az aks nodepool add` polecenie .

## Nawiązywanie połączenia z klastrem usługi AKS i tworzenie przestrzeni nazw

W tej sekcji uzyskasz poświadczenia klastra usługi AKS, które służą jako klucze, które umożliwiają uwierzytelnianie i interakcję z klastrem. Po nawiązaniu połączenia utworzysz dwie przestrzenie nazw: jedną dla usług menedżera kontrolera CNPG i jedną dla klastra PostgreSQL i powiązanych usług.

1. Pobierz poświadczenia klastra usługi AKS przy użyciu [`az aks get-credentials`][az-aks-get-credentials] polecenia .

    ```bash
    az aks get-credentials \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --output none
     ```

2. Utwórz przestrzeń nazw dla usług menedżera kontrolera CNPG, klastra PostgreSQL i powiązanych z nią usług przy użyciu [`kubectl create namespace`][kubectl-create-namespace] polecenia .

    ```bash
    kubectl create namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    kubectl create namespace $PG_SYSTEM_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## Aktualizowanie infrastruktury monitorowania

Obszar roboczy usługi Azure Monitor dla zarządzanych rozwiązań Prometheus i Azure Managed Grafana są automatycznie połączone z klastrem AKS na potrzeby metryk i wizualizacji podczas procesu tworzenia klastra. W tej sekcji włączysz zbieranie dzienników za pomocą szczegółowych informacji o kontenerze usługi AKS i sprawdzisz, czy zarządzany prometheus jest złomowaniem metryk, a szczegółowe informacje o kontenerze pozyskują dzienniki.

1. Włącz monitorowanie usługi Container Insights w klastrze usługi AKS przy użyciu [`az aks enable-addons`][az-aks-enable-addons] polecenia .

    ```bash
    az aks enable-addons \
        --addon monitoring \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --workspace-resource-id $ALA_RESOURCE_ID \
        --output table
    ```

2. Zweryfikuj, czy zarządzany prometheus to złomowanie metryk, a szczegółowe informacje o kontenerze pozyskują dzienniki z klastra usługi AKS, sprawdzając element DaemonSet przy użyciu [`kubectl get`][kubectl-get] polecenia i [`az aks show`][az-aks-show] polecenia .

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

    Dane wyjściowe powinny przypominać następujące przykładowe dane wyjściowe z sześcioma* węzłami *łącznie (trzy dla puli węzłów systemowych i trzy dla puli węzłów PostgreSQL) oraz szczegółowe informacje o kontenerze z wyświetlonymi `"enabled": true`informacjami:

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

## Tworzenie publicznego statycznego adresu IP dla ruchu przychodzącego klastra PostgreSQL

Aby zweryfikować wdrożenie klastra PostgreSQL i użyć narzędzi klienta PostgreSQL, takich jak *psql* i *PgAdmin*, należy uwidocznić repliki podstawowe i tylko do odczytu do ruchu przychodzącego. W tej sekcji utworzysz zasób publicznego adresu IP platformy Azure, który później zostanie udostępniony modułowi równoważenia obciążenia platformy Azure, aby uwidocznić punkty końcowe postgreSQL na potrzeby zapytań.

1. Pobierz nazwę grupy zasobów węzła klastra usługi AKS przy użyciu [`az aks show`][az-aks-show] polecenia .

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME=$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query nodeResourceGroup \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME
    ```

2. Utwórz publiczny adres IP przy użyciu [`az network public-ip create`][az-network-public-ip-create] polecenia .

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

3. Pobierz nowo utworzony publiczny adres IP przy użyciu [`az network public-ip show`][az-network-public-ip-show] polecenia .

    ```bash
    export AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS=$(az network public-ip show \
        --resource-group $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --name $AKS_PRIMARY_CLUSTER_PUBLICIP_NAME \
        --query ipAddress \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS
    ```

4. Pobierz identyfikator zasobu grupy zasobów węzła przy użyciu [`az group show`][az-group-show] polecenia .

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE=$(az group show --name \
        $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --query id \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE
    ```

5. Przypisz rolę "Współautor sieci" do identyfikatora obiektu UAMI przy użyciu zakresu grupy zasobów węzła [`az role assignment create`][az-role-assignment-create] przy użyciu polecenia .

    ```bash
    az role assignment create \
        --assignee-object-id ${AKS_UAMI_WORKLOAD_OBJECTID} \
        --assignee-principal-type ServicePrincipal \
        --role "Network Contributor" \
        --scope ${AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE}
    ```

## Instalowanie operatora CNPG w klastrze usługi AKS

W tej sekcji zainstalujesz operator CNPG w klastrze usługi AKS przy użyciu programu Helm lub manifestu YAML.

### [Helm](#tab/helm)

1. Dodaj repozytorium programu Helm CNPG przy użyciu [`helm repo add`][helm-repo-add] polecenia .

    ```bash
    helm repo add cnpg https://cloudnative-pg.github.io/charts
    ```

2. Uaktualnij repozytorium helm CNPG i zainstaluj je w klastrze usługi AKS przy użyciu [`helm upgrade`][helm-upgrade] polecenia z flagą .`--install`

    ```bash
    helm upgrade --install cnpg \
        --namespace $PG_SYSTEM_NAMESPACE \
        --create-namespace \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME \
        cnpg/cloudnative-pg
    ```

3. Sprawdź instalację operatora w klastrze usługi AKS przy użyciu [`kubectl get`][kubectl-get] polecenia .

    ```bash
    kubectl get deployment \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-cloudnative-pg
    ```

### [YAML](#tab/yaml)

1. Zainstaluj operator CNPG w klastrze usługi AKS przy użyciu [`kubectl apply`][kubectl-apply] polecenia .

    ```bash
    kubectl apply --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE \
        --server-side -f \
        https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.23/releases/cnpg-1.23.1.yaml
    ```

2. Sprawdź instalację operatora w klastrze usługi AKS przy użyciu [`kubectl get`][kubectl-get] polecenia .

    ```bash
    kubectl get deployment \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-controller-manager \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

---

## Następne kroki

> [!div class="nextstepaction"]
> [Wdrażanie bazy danych PostgreSQL o wysokiej dostępności w klastrze usługi AKS][deploy-postgresql]

## Współautorzy

*Ten artykuł jest obsługiwany przez firmę Microsoft. Pierwotnie został napisany przez następujących współautorów*:

* Ken Kilty | Moduł TPM podmiotu zabezpieczeń
* Russell de Pina | Moduł TPM podmiotu zabezpieczeń
* Adrian Joian | Starszy inżynier klienta
* Jenny Hayes | Starszy deweloper zawartości
* Carol Smith | Starszy deweloper zawartości
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
