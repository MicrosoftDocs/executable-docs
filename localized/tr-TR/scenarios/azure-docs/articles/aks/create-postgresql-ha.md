---
title: AKS'de yüksek oranda kullanılabilir bir PostgreSQL veritabanı dağıtmak için altyapı oluşturma
description: CloudNativePG işlecini kullanarak AKS üzerinde yüksek oranda kullanılabilir bir PostgreSQL veritabanı dağıtmak için gereken altyapıyı oluşturun.
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# AKS'de yüksek oranda kullanılabilir bir PostgreSQL veritabanı dağıtmak için altyapı oluşturma

Bu makalede CloudNativePG (CNPG)[ işlecini kullanarak AKS üzerinde yüksek oranda kullanılabilir bir PostgreSQL veritabanı dağıtmak için gereken altyapıyı ](https://cloudnative-pg.io/)oluşturacaksınız.

## Başlamadan önce

* Dağıtıma genel bakış bölümünü gözden geçirin ve Azure CLI[ ile AKS'de ][postgresql-ha-deployment-overview]yüksek oranda kullanılabilir bir PostgreSQL veritabanı dağıtma konusunda tüm önkoşulları karşıladığınızdan emin olun.
* [Bu kılavuz boyunca kullanılacak ortam değişkenlerini](#set-environment-variables) ayarlayın.
* [Gerekli uzantıları](#install-required-extensions) yükleyin.

## Ortam değişkenlerini belirleme

Bu kılavuz boyunca kullanmak üzere aşağıdaki ortam değişkenlerini ayarlayın:

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

## Gerekli uzantıları yükleme

`aks-preview`ve `k8s-extension` `amg` uzantıları, Kubernetes kümelerini yönetmek ve Azure kaynaklarını sorgulamak için daha fazla işlevsellik sağlar. Aşağıdaki [`az extension add`][az-extension-add] komutları kullanarak bu uzantıları yükleyin:

```bash
az extension add --upgrade --name aks-preview --yes --allow-preview true
az extension add --upgrade --name k8s-extension --yes --allow-preview false
az extension add --upgrade --name amg --yes --allow-preview false
```

Kubectl'yi kullanmak için önkoşul olarak, önce Krew'i ve [ardından CNPG eklentisinin[ yüklenmesini ][cnpg-plugin]yüklemek][install-krew] önemlidir. Bu, sonraki komutları kullanarak PostgreSQL işlecinin yönetimini etkinleştirir.

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

## Kaynak grubu oluşturma

komutunu kullanarak [`az group create`][az-group-create] bu kılavuzda oluşturduğunuz kaynakları tutmak için bir kaynak grubu oluşturun.

```bash
az group create \
    --name $RESOURCE_GROUP_NAME \
    --location $PRIMARY_CLUSTER_REGION \
    --tags $TAGS \
    --query 'properties.provisioningState' \
    --output tsv
```

## Kullanıcı tarafından atanan yönetilen kimlik oluşturma

Bu bölümde, CNPG PostgreSQL'in Azure Blob Depolama erişmek için AKS iş yükü kimliğini kullanmasına izin vermek için kullanıcı tarafından atanan bir yönetilen kimlik (UAMI) oluşturacaksınız. Bu yapılandırma, AKS üzerindeki PostgreSQL kümesinin gizli dizi olmadan Azure Blob Depolama bağlanmasına olanak tanır.

1. komutunu kullanarak [`az identity create`][az-identity-create] kullanıcı tarafından atanan bir yönetilen kimlik oluşturun.

    ```bash
    AKS_UAMI_WI_IDENTITY=$(az identity create \
        --name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --output json)
    ```

1. AKS iş yükü kimliğini etkinleştirin ve aşağıdaki komutları kullanarak bu kılavuzun devamında kullanmak üzere bir hizmet hesabı oluşturun:

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

Nesne kimliği, entra kimliği kiracısı içinde Application* türünde *bir güvenlik sorumlusunu benzersiz olarak tanımlayan istemci kimliği (uygulama kimliği olarak da bilinir) için benzersiz bir tanımlayıcıdır. Kaynak kimliği, Azure'da bir kaynağı yönetmek ve bulmak için benzersiz bir tanımlayıcıdır. Aks iş yükü kimliğini etkinleştirmek için bu değerler gereklidir.

CNPG işleci, postgreSQL'den* Azure Depolama'ya OAuth erişimini sağlayan bir federasyon kimlik bilgisi oluşturmak için kılavuzun ilerleyen bölümlerinde kullandığınız postgres adlı *bir hizmet hesabını otomatik olarak oluşturur.

## Birincil bölgede depolama hesabı oluşturma

1. Komutunu kullanarak [`az storage account create`][az-storage-account-create] PostgreSQL yedeklemelerini birincil bölgede depolamak için bir nesne depolama hesabı oluşturun.

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

1. komutunu kullanarak Önceden Yazma Günlüklerini (WAL) ve normal PostgreSQL isteğe bağlı ve zamanlanmış yedeklemeleri depolamak için depolama kapsayıcısını [`az storage container create`][az-storage-container-create] oluşturun.

    ```bash
    az storage container create \
        --name $PG_STORAGE_BACKUP_CONTAINER_NAME \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --auth-mode login
    ```

    Örnek çıkış:

    ```output
    {
        "created": true
    }
    ```

    > [!NOTE]
    > Hata iletisiyle karşılaşırsanız: `The request may be blocked by network rules of storage account. Please check network rule set using 'az storage account show -n accountname --query networkRuleSet'. If you want to change the default action to apply when no rule matches, please use 'az storage account update'`. Lütfen Azure Blob Depolama için kullanıcı izinlerini doğrulayın ve gerekirse **, aşağıda sağlanan komutları kullanarak ve komutu yeniden denedikten sonra rolünüzü `Storage Blob Data Owner` yükseltin[`az storage container create`][az-storage-container-create].**

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

## Depolama hesaplarına RBAC atama

Yedeklemeleri etkinleştirmek için PostgreSQL kümesinin bir nesne deposuna okuması ve yazması gerekir. AKS üzerinde çalışan PostgreSQL kümesi, CNPG işleci yapılandırma parametresi [`inheritFromAzureAD`][inherit-from-azuread]aracılığıyla depolama hesabına erişmek için bir iş yükü kimliği kullanır.

1. komutunu kullanarak [`az storage account show`][az-storage-account-show] depolama hesabının birincil kaynak kimliğini alın.

    ```bash
    export STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID=$(az storage account show \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "id" \
        --output tsv)

    echo $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID
    ````

1. komutunu kullanarak her AKS kümesinin yönetilen kimliğiyle ilişkilendirilmiş UAMI'nin depolama hesabı kaynak kimliği kapsamına sahip nesne kimliğine "Depolama Blobu Veri Katkıda Bulunanı" Azure yerleşik rolünü atayın [`az role assignment create`][az-role-assignment-create] .

    ```bash
    az role assignment create \
        --role "Storage Blob Data Contributor" \
        --assignee-object-id $AKS_UAMI_WORKLOAD_OBJECTID \
        --assignee-principal-type ServicePrincipal \
        --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID \
        --query "id" \
        --output tsv
    ```

## İzleme altyapısını ayarlama

Bu bölümde, PostgreSQL kümesinin izlenmesini sağlamak için Azure Yönetilen Grafana, Azure İzleyici çalışma alanı ve Azure İzleyici Log Analytics çalışma alanı örneği dağıtacaksınız. Ayrıca, kılavuzun devamında AKS kümesi oluşturma işlemi sırasında giriş olarak kullanmak üzere oluşturulan izleme altyapısına yönelik başvuruları depolarsınız. Bu bölümün tamamlanması biraz zaman alabilir.

> [!NOTE]
> Azure Yönetilen Grafana örnekleri ve AKS kümeleri bağımsız olarak faturalandırılır. Daha fazla fiyatlandırma bilgisi için bkz [. Azure Yönetilen Grafana fiyatlandırması][azure-managed-grafana-pricing].

1. komutunu kullanarak [`az grafana create`][az-grafana-create] bir Azure Yönetilen Grafana örneği oluşturun.

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

1. komutunu kullanarak [`az monitor account create`][az-monitor-account-create] bir Azure İzleyici çalışma alanı oluşturun.

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

1. komutunu kullanarak [`az monitor log-analytics workspace create`][az-monitor-log-analytics-workspace-create] bir Azure İzleyici Log Analytics çalışma alanı oluşturun.

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

## PostgreSQL kümesini barındırmak için AKS kümesini oluşturma

Bu bölümde, sistem düğümü havuzuyla çok bölgeli bir AKS kümesi oluşturacaksınız. AKS kümesi PostgreSQL kümesi birincil çoğaltmasını ve her birinin bölgesel yedekliliği etkinleştirmek için farklı bir kullanılabilirlik alanına hizalanmış iki bekleme çoğaltmasını barındırıyor.

PostgreSQL kümesini barındırmak için AKS kümesine bir kullanıcı düğümü havuzu da eklersiniz. Ayrı düğüm havuzu kullanmak PostgreSQL için kullanılan Azure VM SKU'ları üzerinde denetim sağlar ve AKS sistem havuzunun performansı ve maliyetleri iyileştirmesini sağlar. Bu kılavuzun devamında CNPG işlecini dağıtırken düğüm seçimi için başvurabileceğiniz kullanıcı düğümü havuzuna bir etiket uygulayacaksınız. Bu bölümün tamamlanması biraz zaman alabilir.

1. komutunu kullanarak [`az aks create`][az-aks-create] bir AKS kümesi oluşturun.

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

2. komutunu kullanarak [`az aks nodepool add`][az-aks-node-pool-add] AKS kümesine bir kullanıcı düğümü havuzu ekleyin.

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
> AKS düğüm havuzunu eklerken hata iletisini `"(OperationNotAllowed) Operation is not allowed: Another operation (Updating) is in progress, please wait for it to finish before starting a new operation."` alırsanız, AKS kümesi işlemlerinin tamamlanması için lütfen birkaç dakika bekleyin ve ardından komutunu çalıştırın `az aks nodepool add` .

## AKS kümesine bağlanma ve ad alanları oluşturma

Bu bölümde, kimlik doğrulaması yapmanıza ve kümeyle etkileşim kurmanıza olanak tanıyan anahtarlar olarak hizmet veren AKS kümesi kimlik bilgilerini alırsınız. Bağlandıktan sonra iki ad alanı oluşturursunuz: biri CNPG denetleyici yöneticisi hizmetleri ve biri PostgreSQL kümesi ve ilgili hizmetleri için.

1. komutunu kullanarak [`az aks get-credentials`][az-aks-get-credentials] AKS kümesi kimlik bilgilerini alın.

    ```bash
    az aks get-credentials \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --output none
     ```

2. komutunu kullanarak CNPG denetleyici yöneticisi hizmetleri, PostgreSQL kümesi ve ilgili hizmetleri için ad alanını [`kubectl create namespace`][kubectl-create-namespace] oluşturun.

    ```bash
    kubectl create namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    kubectl create namespace $PG_SYSTEM_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## İzleme altyapısını güncelleştirme

Yönetilen Prometheus ve Azure Yönetilen Grafana için Azure İzleyici çalışma alanı, küme oluşturma işlemi sırasında ölçümler ve görselleştirmeler için AKS kümesine otomatik olarak bağlanır. Bu bölümde AKS Container insights ile günlük toplamayı etkinleştirip Yönetilen Prometheus'un ölçümleri kazıdığını ve Kapsayıcı içgörülerinin günlükleri içeri aktardığını doğrulaacaksınız.

1. komutunu kullanarak [`az aks enable-addons`][az-aks-enable-addons] AKS kümesinde Kapsayıcı içgörüleri izlemeyi etkinleştirin.

    ```bash
    az aks enable-addons \
        --addon monitoring \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --workspace-resource-id $ALA_RESOURCE_ID \
        --output table
    ```

2. Yönetilen Prometheus'un ölçümleri kazıdığını ve Kapsayıcı içgörülerinin, komutu ve [`az aks show`][az-aks-show] komutunu kullanarak [`kubectl get`][kubectl-get] DaemonSet'i inceleyerek AKS kümesinden günlükleri alındığını doğrulayın.

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

    Çıkışınız aşağıdaki örnek çıkışa *benzemelidir; toplam altı* düğüm (sistem düğümü havuzu için üç ve PostgreSQL düğüm havuzu için üç düğüm) ve kapsayıcı içgörüleri şunu gösterir `"enabled": true`:

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

## PostgreSQL kümesi girişi için genel statik IP oluşturma

PostgreSQL kümesinin dağıtımını doğrulamak ve psql* ve *PgAdmin* gibi *istemci PostgreSQL araçlarını kullanmak için birincil ve salt okunur çoğaltmaları girişte kullanıma sunmanız gerekir. Bu bölümde, daha sonra sorgu için PostgreSQL uç noktalarını kullanıma sunma amacıyla bir Azure yük dengeleyiciye sağladığınız bir Azure genel IP kaynağı oluşturacaksınız.

1. komutunu kullanarak [`az aks show`][az-aks-show] AKS kümesi düğümü kaynak grubunun adını alın.

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME=$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query nodeResourceGroup \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME
    ```

2. komutunu kullanarak [`az network public-ip create`][az-network-public-ip-create] genel IP adresini oluşturun.

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

3. komutunu kullanarak [`az network public-ip show`][az-network-public-ip-show] yeni oluşturulan genel IP adresini alın.

    ```bash
    export AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS=$(az network public-ip show \
        --resource-group $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --name $AKS_PRIMARY_CLUSTER_PUBLICIP_NAME \
        --query ipAddress \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS
    ```

4. komutunu kullanarak [`az group show`][az-group-show] düğüm kaynak grubunun kaynak kimliğini alın.

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE=$(az group show --name \
        $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --query id \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE
    ```

5. komutunu kullanarak düğüm kaynak grubu kapsamını kullanarak UAMI nesne kimliğine "Ağ Katkıda Bulunanı" rolünü atayın [`az role assignment create`][az-role-assignment-create] .

    ```bash
    az role assignment create \
        --assignee-object-id ${AKS_UAMI_WORKLOAD_OBJECTID} \
        --assignee-principal-type ServicePrincipal \
        --role "Network Contributor" \
        --scope ${AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE}
    ```

## AKS kümesine CNPG işlecini yükleme

Bu bölümde, Helm veya YAML bildirimi kullanarak AKS kümesine CNPG işlecini yüklersiniz.

### [Helm](#tab/helm)

1. komutunu kullanarak CNPG Helm deposunu [`helm repo add`][helm-repo-add] ekleyin.

    ```bash
    helm repo add cnpg https://cloudnative-pg.github.io/charts
    ```

2. CNPG Helm deposunu yükseltin ve bayrağıyla komutunu kullanarak AKS kümesine [`helm upgrade`][helm-upgrade] `--install` yükleyin.

    ```bash
    helm upgrade --install cnpg \
        --namespace $PG_SYSTEM_NAMESPACE \
        --create-namespace \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME \
        cnpg/cloudnative-pg
    ```

3. komutunu kullanarak AKS kümesinde operatör yüklemesini [`kubectl get`][kubectl-get] doğrulayın.

    ```bash
    kubectl get deployment \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-cloudnative-pg
    ```

### [YAML](#tab/yaml)

1. komutunu kullanarak AKS kümesine CNPG işlecini [`kubectl apply`][kubectl-apply] yükleyin.

    ```bash
    kubectl apply --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE \
        --server-side -f \
        https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.23/releases/cnpg-1.23.1.yaml
    ```

2. komutunu kullanarak AKS kümesinde operatör yüklemesini [`kubectl get`][kubectl-get] doğrulayın.

    ```bash
    kubectl get deployment \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-controller-manager \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

---

## Sonraki adımlar

> [!div class="nextstepaction"]
> [AKS kümesinde yüksek oranda kullanılabilir bir PostgreSQL veritabanı dağıtma][deploy-postgresql]

## Katkıda Bulunanlar

*Bu makale Microsoft tarafından yönetilir. Başlangıçta aşağıdaki katkıda bulunanlar* tarafından yazılmıştır:

* Ken Kilty | Asıl TPM
* Russell de Pina | Asıl TPM
* Adrian Joian | Kıdemli Müşteri Mühendisi
* Jenny Hayes | Kıdemli İçerik Geliştirici
* Carol Smith | Kıdemli İçerik Geliştirici
* Erin Schaffer | İçerik Geliştirici 2

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
