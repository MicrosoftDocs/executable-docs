---
title: Magas rendelkezésre állású PostgreSQL-adatbázis AKS-en való üzembe helyezéséhez szükséges infrastruktúra létrehozása
description: Hozza létre a magas rendelkezésre állású PostgreSQL-adatbázis üzembe helyezéséhez szükséges infrastruktúrát az AKS-en a CloudNativePG operátorral.
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# Magas rendelkezésre állású PostgreSQL-adatbázis AKS-en való üzembe helyezéséhez szükséges infrastruktúra létrehozása

Ebben a cikkben egy magas rendelkezésre állású PostgreSQL-adatbázis üzembe helyezéséhez szükséges infrastruktúrát hozza létre az AKS-en a [CloudNativePG (CNPG)](https://cloudnative-pg.io/) operátorral.

## Mielőtt elkezdené

* Tekintse át az üzembe helyezés áttekintését, és győződjön meg arról, hogy megfelel egy magas rendelkezésre állású PostgreSQL-adatbázis üzembe helyezésének az Azure CLI-vel[ az AKS-ben való üzembe helyezéséhez szükséges összes előfeltételnek][postgresql-ha-deployment-overview].
* [Környezeti változók](#set-environment-variables) beállítása a jelen útmutatóban való használatra.
* [Telepítse a szükséges bővítményeket](#install-required-extensions).

## Környezeti változók beállítása

Az útmutatóban a következő környezeti változókat használhatja:

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

## A szükséges bővítmények telepítése

A `aks-preview`, `k8s-extension` és `amg` a bővítmények további funkciókat biztosítanak a Kubernetes-fürtök kezeléséhez és az Azure-erőforrások lekérdezéséhez. Telepítse ezeket a bővítményeket a következő [`az extension add`][az-extension-add] parancsokkal:

```bash
az extension add --upgrade --name aks-preview --yes --allow-preview true
az extension add --upgrade --name k8s-extension --yes --allow-preview false
az extension add --upgrade --name amg --yes --allow-preview false
```

A kubectl használatának előfeltételeként elengedhetetlen a Krew[ első telepítése][install-krew], majd a [CNPG beépülő modul][cnpg-plugin] telepítése. Ez lehetővé teszi a PostgreSQL-operátor kezelését a következő parancsokkal.

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

## Erőforráscsoport létrehozása

Hozzon létre egy erőforráscsoportot az ebben az útmutatóban létrehozott erőforrások tárolásához a [`az group create`][az-group-create] parancs használatával.

```bash
az group create \
    --name $RESOURCE_GROUP_NAME \
    --location $PRIMARY_CLUSTER_REGION \
    --tags $TAGS \
    --query 'properties.provisioningState' \
    --output tsv
```

## Felhasználó által hozzárendelt felügyelt identitás létrehozása

Ebben a szakaszban egy felhasználó által hozzárendelt felügyelt identitást (UAMI) hoz létre, amely lehetővé teszi a CNPG PostgreSQL számára, hogy AKS számítási feladatok identitását használja az Azure Blob Storage eléréséhez. Ez a konfiguráció lehetővé teszi, hogy az AKS PostgreSQL-fürtje titkos kód nélkül csatlakozzon az Azure Blob Storage-hoz.

1. Hozzon létre egy felhasználó által hozzárendelt felügyelt identitást a [`az identity create`][az-identity-create] paranccsal.

    ```bash
    AKS_UAMI_WI_IDENTITY=$(az identity create \
        --name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --output json)
    ```

1. Engedélyezze az AKS számítási feladat identitását, és hozzon létre egy szolgáltatásfiókot az útmutató későbbi részében a következő parancsok használatával:

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

Az objektumazonosító az ügyfélazonosító (más néven az alkalmazásazonosító) egyedi azonosítója, amely egyedileg azonosít egy alkalmazás* típusú *biztonsági tagot az Entra ID-bérlőn belül. Az erőforrás-azonosító egy egyedi azonosító, amely egy erőforrást kezel és keres az Azure-ban. Ezek az értékek szükségesek az engedélyezett AKS-számítási feladatok identitásához.

A CNPG-operátor automatikusan létrehoz egy postgres* nevű *szolgáltatásfiókot, amelyet az útmutató későbbi részében használ egy összevont hitelesítő adat létrehozásához, amely lehetővé teszi az OAuth-hozzáférést a PostgreSQL-ből az Azure Storage-ba.

## Tárfiók létrehozása az elsődleges régióban

1. Hozzon létre egy objektumtárfiókot a PostgreSQL-biztonsági mentések elsődleges régióban való tárolásához a [`az storage account create`][az-storage-account-create] parancs használatával.

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

1. Hozza létre a tárolót az Előre írási naplók (WAL) és a rendszeres PostgreSQL igény szerinti és ütemezett biztonsági mentések tárolásához a [`az storage container create`][az-storage-container-create] parancs használatával.

    ```bash
    az storage container create \
        --name $PG_STORAGE_BACKUP_CONTAINER_NAME \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --auth-mode login
    ```

    Példa a kimenetre:

    ```output
    {
        "created": true
    }
    ```

    > [!NOTE]
    > Ha a következő hibaüzenet jelenik meg: `The request may be blocked by network rules of storage account. Please check network rule set using 'az storage account show -n accountname --query networkRuleSet'. If you want to change the default action to apply when no rule matches, please use 'az storage account update'`. Ellenőrizze az Azure Blob Storage felhasználói engedélyeit, és szükség esetén emelje fel a szerepkört `Storage Blob Data Owner` az alábbi parancsok használatára, majd a parancs újrapróbálkozása`az storage container create`[][az-storage-container-create] után.****

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

## RBAC hozzárendelése tárfiókokhoz

A biztonsági mentések engedélyezéséhez a PostgreSQL-fürtnek olvasnia és írnia kell egy objektumtárolóba. Az AKS-en futó PostgreSQL-fürt számítási feladatok identitásával fér hozzá a tárfiókhoz a CNPG operátor konfigurációs paraméterén [`inheritFromAzureAD`][inherit-from-azuread]keresztül.

1. Kérje le a tárfiók elsődleges erőforrás-azonosítóját a [`az storage account show`][az-storage-account-show] parancs használatával.

    ```bash
    export STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID=$(az storage account show \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "id" \
        --output tsv)

    echo $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID
    ````

1. Rendelje hozzá a "Storage Blob Data Contributor" Azure beépített szerepkört az objektumazonosítóhoz az egyes AKS-fürtök felügyelt identitásához társított UAMI tárfiók erőforrás-azonosító hatókörével a [`az role assignment create`][az-role-assignment-create] parancs használatával.

    ```bash
    az role assignment create \
        --role "Storage Blob Data Contributor" \
        --assignee-object-id $AKS_UAMI_WORKLOAD_OBJECTID \
        --assignee-principal-type ServicePrincipal \
        --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID \
        --query "id" \
        --output tsv
    ```

## Monitorozási infrastruktúra beállítása

Ebben a szakaszban üzembe helyezi az Azure Managed Grafana egy példányát, egy Azure Monitor-munkaterületet és egy Azure Monitor Log Analytics-munkaterületet a PostgreSQL-fürt monitorozásának engedélyezéséhez. Az útmutató későbbi részében az AKS-fürtlétrehozási folyamat során bemenetként használandó létrehozott monitorozási infrastruktúrára mutató hivatkozásokat is tárolhat. Ez a szakasz eltarthat egy ideig.

> [!NOTE]
> Az Azure Managed Grafana-példányok és az AKS-fürtök számlázása független. További díjszabási információkért tekintse meg az [Azure Managed Grafana díjszabását][azure-managed-grafana-pricing].

1. Hozzon létre egy Azure Managed Grafana-példányt a [`az grafana create`][az-grafana-create] paranccsal.

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

1. Hozzon létre egy Azure Monitor-munkaterületet a [`az monitor account create`][az-monitor-account-create] paranccsal.

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

1. Hozzon létre egy Azure Monitor Log Analytics-munkaterületet a [`az monitor log-analytics workspace create`][az-monitor-log-analytics-workspace-create] paranccsal.

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

## Az AKS-fürt létrehozása a PostgreSQL-fürt üzemeltetéséhez

Ebben a szakaszban egy többzónás AKS-fürtöt hoz létre egy rendszercsomópontkészlettel. Az AKS-fürt a PostgreSQL-fürt elsődleges replikáját és két készenléti replikát üzemeltet, amelyek mindegyike egy másik rendelkezésre állási zónához van igazítva, hogy lehetővé tegye a zónaszintű redundanciát.

A PostgreSQL-fürt üzemeltetéséhez felhasználói csomópontkészletet is hozzáadhat az AKS-fürthöz. Egy külön csomópontkészlet használata lehetővé teszi a PostgreSQL-hez használt Azure-beli virtuálisgép-termékváltozatok ellenőrzését, és lehetővé teszi az AKS-rendszerkészlet számára a teljesítmény és a költségek optimalizálását. A felhasználói csomópontkészletre olyan címkét alkalmazhat, amely a CNPG-operátor üzembe helyezésekor hivatkozhat a csomópontok kiválasztására az útmutató későbbi részében. Ez a szakasz eltarthat egy ideig.

1. Hozzon létre egy AKS-fürtöt a [`az aks create`][az-aks-create] paranccsal.

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

2. Adjon hozzá egy felhasználói csomópontkészletet az AKS-fürthöz a [`az aks nodepool add`][az-aks-node-pool-add] paranccsal.

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
> Ha az `"(OperationNotAllowed) Operation is not allowed: Another operation (Updating) is in progress, please wait for it to finish before starting a new operation."` AKS-csomópontkészlet hozzáadásakor hibaüzenet jelenik meg, várjon néhány percet, amíg az AKS-fürtműveletek befejeződnek, majd futtassa a `az aks nodepool add` parancsot.

## Csatlakozás az AKS-fürthöz és névterek létrehozása

Ebben a szakaszban lekérheti az AKS-fürt hitelesítő adatait, amelyek a fürt hitelesítését és használatát lehetővé tevő kulcsokként szolgálnak. A csatlakozás után két névteret hoz létre: egyet a CNPG vezérlőkezelői szolgáltatásaihoz, egyet pedig a PostgreSQL-fürthöz és annak kapcsolódó szolgáltatásaihoz.

1. Kérje le az AKS-fürt hitelesítő adatait a [`az aks get-credentials`][az-aks-get-credentials] paranccsal.

    ```bash
    az aks get-credentials \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --output none
     ```

2. A parancs használatával [`kubectl create namespace`][kubectl-create-namespace] hozza létre a CNPG-vezérlőkezelői szolgáltatások, a PostgreSQL-fürt és a kapcsolódó szolgáltatások névterét.

    ```bash
    kubectl create namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    kubectl create namespace $PG_SYSTEM_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## A figyelési infrastruktúra frissítése

A felügyelt Prometheushoz és az Azure Managed Grafana-hoz készült Azure Monitor-munkaterület automatikusan kapcsolódik az AKS-fürthöz metrikák és vizualizációk céljából a fürtlétrehozási folyamat során. Ebben a szakaszban engedélyezi a naplógyűjtést az AKS Container Insights használatával, és ellenőrzi, hogy a Felügyelt Prometheus kaparja-e a metrikákat, és a Container Insights betölti-e a naplókat.

1. Engedélyezze a Container Insights monitorozását az AKS-fürtön a [`az aks enable-addons`][az-aks-enable-addons] paranccsal.

    ```bash
    az aks enable-addons \
        --addon monitoring \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --workspace-resource-id $ALA_RESOURCE_ID \
        --output table
    ```

2. Ellenőrizze, hogy a Felügyelt Prometheus kaparja-e a metrikákat, és a Container Insights naplókat fogad az AKS-fürtből a DaemonSet parancs és a [`az aks show``kubectl get`][kubectl-get] [][az-aks-show] parancs használatával történő vizsgálatával.

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

    A kimenetnek a következő példakimenethez kell hasonlítania, összesen hat* csomóponttal *(a rendszercsomópontkészlethez három, a PostgreSQL-csomópontkészlethez háromhoz) és a Container Insightshoz:`"enabled": true`

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

## Nyilvános statikus IP-cím létrehozása a PostgreSQL-fürt bejövő forgalmához

A PostgreSQL-fürt üzembe helyezésének ellenőrzéséhez és az ügyfél PostgreSQL-eszközkészlet (például *psql* és *PgAdmin*) használatához el kell helyeznie az elsődleges és írásvédett replikákat a bejövő forgalom számára. Ebben a szakaszban létrehoz egy Nyilvános Azure IP-erőforrást, amelyet később egy Azure-terheléselosztónak ad meg a PostgreSQL-végpontok lekérdezéshez való közzétételéhez.

1. Kérje le az AKS-fürtcsomópont erőforráscsoportjának nevét a [`az aks show`][az-aks-show] paranccsal.

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME=$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query nodeResourceGroup \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME
    ```

2. Hozza létre a nyilvános IP-címet a [`az network public-ip create`][az-network-public-ip-create] paranccsal.

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

3. Kérje le az újonnan létrehozott nyilvános IP-címet a [`az network public-ip show`][az-network-public-ip-show] paranccsal.

    ```bash
    export AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS=$(az network public-ip show \
        --resource-group $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --name $AKS_PRIMARY_CLUSTER_PUBLICIP_NAME \
        --query ipAddress \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS
    ```

4. Kérje le a csomópont erőforráscsoportjának erőforrás-azonosítóját a [`az group show`][az-group-show] paranccsal.

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE=$(az group show --name \
        $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --query id \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE
    ```

5. Rendelje hozzá a "Hálózati közreműködő" szerepkört az UAMI-objektumazonosítóhoz a csomópont erőforráscsoport hatókörének használatával a [`az role assignment create`][az-role-assignment-create] parancs használatával.

    ```bash
    az role assignment create \
        --assignee-object-id ${AKS_UAMI_WORKLOAD_OBJECTID} \
        --assignee-principal-type ServicePrincipal \
        --role "Network Contributor" \
        --scope ${AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE}
    ```

## A CNPG-operátor telepítése az AKS-fürtben

Ebben a szakaszban a CNPG-operátort az AKS-fürtbe telepíti a Helm vagy egy YAML-jegyzék használatával.

### [Helm](#tab/helm)

1. Adja hozzá a CNPG Helm-adattárat a [`helm repo add`][helm-repo-add] paranccsal.

    ```bash
    helm repo add cnpg https://cloudnative-pg.github.io/charts
    ```

2. Frissítse a CNPG Helm-adattárat, és telepítse az AKS-fürtre a [`helm upgrade`][helm-upgrade] jelölővel ellátott `--install` paranccsal.

    ```bash
    helm upgrade --install cnpg \
        --namespace $PG_SYSTEM_NAMESPACE \
        --create-namespace \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME \
        cnpg/cloudnative-pg
    ```

3. Ellenőrizze az operátor telepítését az AKS-fürtön a [`kubectl get`][kubectl-get] paranccsal.

    ```bash
    kubectl get deployment \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-cloudnative-pg
    ```

### [YAML](#tab/yaml)

1. Telepítse a CNPG-operátort az AKS-fürtre a [`kubectl apply`][kubectl-apply] parancs használatával.

    ```bash
    kubectl apply --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE \
        --server-side -f \
        https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.23/releases/cnpg-1.23.1.yaml
    ```

2. Ellenőrizze az operátor telepítését az AKS-fürtön a [`kubectl get`][kubectl-get] paranccsal.

    ```bash
    kubectl get deployment \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-controller-manager \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

---

## Következő lépések

> [!div class="nextstepaction"]
> [Magas rendelkezésre állású PostgreSQL-adatbázis üzembe helyezése az AKS-fürtön][deploy-postgresql]

## Közreműködők

*Ezt a cikket a Microsoft tartja karban. Eredetileg a következő közreműködők* írták:

* Ken Kilty | Egyszerű TPM
* Russell de | Egyszerű TPM
* Adrian Joian | Vezető ügyfélmérnök
* Jenny Hayes | Vezető tartalomfejlesztő
* Carol Smith | Vezető tartalomfejlesztő
* Erin Schaffer | Tartalomfejlesztő 2

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
