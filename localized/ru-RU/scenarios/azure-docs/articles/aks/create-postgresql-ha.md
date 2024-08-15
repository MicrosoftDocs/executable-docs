---
title: Создание инфраструктуры для развертывания высокодоступной базы данных PostgreSQL в AKS
description: 'Создайте инфраструктуру, необходимую для развертывания высокодоступной базы данных PostgreSQL в AKS с помощью оператора CloudNativePG.'
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# Создание инфраструктуры для развертывания высокодоступной базы данных PostgreSQL в AKS

В этой статье описано, как создать инфраструктуру, необходимую для развертывания высокодоступной базы данных PostgreSQL в AKS с помощью [оператора CloudNativePG (CNPG).](https://cloudnative-pg.io/)

## Подготовка к работе

* Ознакомьтесь с обзором развертывания и убедитесь, что выполнены все предварительные требования, приведенные в [статье "Как развернуть высокодоступную базу данных PostgreSQL в AKS" с помощью Azure CLI][postgresql-ha-deployment-overview].
* [Задайте переменные](#set-environment-variables) среды для использования в этом руководстве.
* [Установите необходимые](#install-required-extensions) расширения.

## Настройка переменных среды

Задайте следующие переменные среды для использования в этом руководстве:

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

## Установка необходимых расширений

`k8s-extension` `amg` Расширения `aks-preview`предоставляют дополнительные функциональные возможности для управления кластерами Kubernetes и запросами ресурсов Azure. Установите эти расширения с помощью следующих [`az extension add`][az-extension-add] команд:

```bash
az extension add --upgrade --name aks-preview --yes --allow-preview true
az extension add --upgrade --name k8s-extension --yes --allow-preview false
az extension add --upgrade --name amg --yes --allow-preview false
```

Для использования kubectl необходимо сначала установить Krew[, а затем установить ][install-krew]подключаемый [модуль][cnpg-plugin] CNPG. Это позволит управлять оператором PostgreSQL с помощью последующих команд.

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

## Создание или изменение группы ресурсов

Создайте группу ресурсов для хранения ресурсов, создаваемых в этом руководстве [`az group create`][az-group-create] , с помощью команды.

```bash
az group create \
    --name $RESOURCE_GROUP_NAME \
    --location $PRIMARY_CLUSTER_REGION \
    --tags $TAGS \
    --query 'properties.provisioningState' \
    --output tsv
```

## Создание управляемого удостоверения, назначаемого пользователем

В этом разделе описано, как создать управляемое удостоверение, назначаемое пользователем (UAMI), чтобы разрешить CNPG PostgreSQL использовать удостоверение рабочей нагрузки AKS для доступа к Хранилище BLOB-объектов Azure. Эта конфигурация позволяет кластеру PostgreSQL в AKS подключаться к Хранилище BLOB-объектов Azure без секрета.

1. Создайте управляемое удостоверение, назначаемое пользователем [`az identity create`][az-identity-create] , с помощью команды.

    ```bash
    AKS_UAMI_WI_IDENTITY=$(az identity create \
        --name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --output json)
    ```

1. Включите удостоверение рабочей нагрузки AKS и создайте учетную запись службы для использования далее в этом руководстве с помощью следующих команд:

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

Идентификатор объекта — это уникальный идентификатор клиента (также известный как идентификатор приложения), который однозначно идентифицирует субъект безопасности типа *Application* в клиенте Идентификатора записи. Идентификатор ресурса — это уникальный идентификатор для управления и поиска ресурса в Azure. Эти значения необходимы для включения удостоверения рабочей нагрузки AKS.

Оператор CNPG автоматически создает учетную запись службы с именем *postgres*, которую вы используете позже в руководстве для создания федеративных учетных данных, которые позволяют OAuth получить доступ из PostgreSQL к служба хранилища Azure.

## Создание учетной записи хранения в основном регионе

1. Создайте учетную запись хранения объектов для хранения резервных копий PostgreSQL в основном регионе [`az storage account create`][az-storage-account-create] с помощью команды.

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

1. Создайте контейнер хранилища для хранения журналов записи (WAL) и регулярных резервных копий PostgreSQL по запросу и запланированных резервных копий с помощью [`az storage container create`][az-storage-container-create] команды.

    ```bash
    az storage container create \
        --name $PG_STORAGE_BACKUP_CONTAINER_NAME \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --auth-mode login
    ```

    Пример результата:

    ```output
    {
        "created": true
    }
    ```

    > [!NOTE]
    > При возникновении сообщения об ошибке: `The request may be blocked by network rules of storage account. Please check network rule set using 'az storage account show -n accountname --query networkRuleSet'. If you want to change the default action to apply when no rule matches, please use 'az storage account update'` Проверьте разрешения пользователей для Хранилище BLOB-объектов Azure и **при необходимости** повысить уровень роли, чтобы `Storage Blob Data Owner` использовать команды, указанные ниже, и после повтора [`az storage container create`][az-storage-container-create] команды.

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

## Назначение RBAC учетным записям хранения

Чтобы включить резервное копирование, кластер PostgreSQL должен считывать и записывать данные в хранилище объектов. Кластер PostgreSQL, работающий в AKS, использует удостоверение рабочей нагрузки для доступа к учетной записи хранения с помощью параметра [`inheritFromAzureAD`][inherit-from-azuread]конфигурации оператора CNPG.

1. Получите идентификатор основного ресурса для учетной записи хранения с помощью [`az storage account show`][az-storage-account-show] команды.

    ```bash
    export STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID=$(az storage account show \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "id" \
        --output tsv)

    echo $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID
    ````

1. Назначьте встроенную роль Azure "Участник данных BLOB-объектов хранилища" идентификатору объекта с областью идентификатора ресурса учетной записи хранения для UAMI, связанной с управляемым удостоверением для каждого кластера AKS с помощью [`az role assignment create`][az-role-assignment-create] команды.

    ```bash
    az role assignment create \
        --role "Storage Blob Data Contributor" \
        --assignee-object-id $AKS_UAMI_WORKLOAD_OBJECTID \
        --assignee-principal-type ServicePrincipal \
        --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID \
        --query "id" \
        --output tsv
    ```

## Настройка инфраструктуры мониторинга

В этом разделе описано, как развернуть экземпляр Управляемой Grafana Azure, рабочую область Azure Monitor и рабочую область Azure Monitor Log Analytics, чтобы включить мониторинг кластера PostgreSQL. Вы также сохраняете ссылки на созданную инфраструктуру мониторинга для использования в качестве входных данных во время процесса создания кластера AKS далее в руководстве. Для завершения этого раздела может потребоваться некоторое время.

> [!NOTE]
> Управляемые экземпляры Grafana Azure и кластеры AKS оплачиваются независимо. Дополнительные сведения о ценах см. в разделе ["][azure-managed-grafana-pricing]Управляемые Grafana Azure".

1. Создайте экземпляр Azure Managed Grafana с помощью [`az grafana create`][az-grafana-create] команды.

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

1. Создайте рабочую область Azure Monitor с помощью [`az monitor account create`][az-monitor-account-create] команды.

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

1. Создайте рабочую область Azure Monitor Log Analytics с помощью [`az monitor log-analytics workspace create`][az-monitor-log-analytics-workspace-create] команды.

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

## Создание кластера AKS для размещения кластера PostgreSQL

В этом разделе описано, как создать кластер AKS с пулом системных узлов. Кластер AKS размещает основную реплику кластера PostgreSQL и две резервные реплики, каждая из которых соответствует другой зоне доступности, чтобы обеспечить зональную избыточность.

Вы также добавляете пул узлов пользователей в кластер AKS для размещения кластера PostgreSQL. Использование отдельного пула узлов позволяет управлять номерами SKU виртуальных машин Azure, используемыми для PostgreSQL, и позволяет системным пулу AKS оптимизировать производительность и затраты. Вы применяете метку к пулу узлов пользователя, который можно ссылаться на выбор узла при развертывании оператора CNPG далее в этом руководстве. Для завершения этого раздела может потребоваться некоторое время.

1. Создайте кластер AKS с помощью [`az aks create`][az-aks-create] команды.

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

2. Добавьте пул узлов пользователя в кластер AKS с помощью [`az aks nodepool add`][az-aks-node-pool-add] команды.

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
> Если при добавлении пула узлов AKS появится сообщение `"(OperationNotAllowed) Operation is not allowed: Another operation (Updating) is in progress, please wait for it to finish before starting a new operation."` об ошибке, подождите несколько минут до завершения операций кластера AKS, а затем выполните `az aks nodepool add` команду.

## Подключение к кластеру AKS и создание пространств имен

В этом разделе вы получите учетные данные кластера AKS, которые служат ключами, которые позволяют выполнять проверку подлинности и взаимодействовать с кластером. После подключения создайте два пространства имен: один для служб диспетчера контроллеров CNPG и один для кластера PostgreSQL и связанных служб.

1. Получите учетные данные кластера AKS с помощью [`az aks get-credentials`][az-aks-get-credentials] команды.

    ```bash
    az aks get-credentials \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --output none
     ```

2. Создайте пространство имен для служб диспетчера контроллеров CNPG, кластера PostgreSQL и связанных служб с помощью [`kubectl create namespace`][kubectl-create-namespace] команды.

    ```bash
    kubectl create namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    kubectl create namespace $PG_SYSTEM_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## Обновление инфраструктуры мониторинга

Рабочая область Azure Monitor для Managed Prometheus и Azure Managed Grafana автоматически связаны с кластером AKS для метрик и визуализации во время процесса создания кластера. В этом разделе описано, как включить сбор журналов с помощью аналитики контейнеров AKS и проверить, является ли Управляемый Prometheus ломать метрики, а аналитика контейнеров — прием журналов.

1. Включите мониторинг аналитики контейнеров в кластере [`az aks enable-addons`][az-aks-enable-addons] AKS с помощью команды.

    ```bash
    az aks enable-addons \
        --addon monitoring \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --workspace-resource-id $ALA_RESOURCE_ID \
        --output table
    ```

2. Убедитесь, что Управляемый Prometheus метрики и аналитика контейнеров отправляет журналы из кластера AKS, проверяя DaemonSet с помощью [`kubectl get`][kubectl-get] команды и [`az aks show`][az-aks-show] команды.

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

    Выходные данные должны выглядеть примерно так, как показано в следующем примере выходных данных: ** шесть узлов (три для пула узлов системы и три для пула узлов PostgreSQL) и аналитические `"enabled": true`сведения о контейнерах:

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

## Создание общедоступного статического IP-адреса для входящего трафика кластера PostgreSQL

Чтобы проверить развертывание кластера PostgreSQL и использовать клиентские средства PostgreSQL, такие как *psql* и *PgAdmin*, необходимо предоставить первичные и доступные только для чтения реплики для входящего трафика. В этом разделе описано, как создать ресурс общедоступного IP-адреса Azure, который позже будет предоставлен подсистеме балансировки нагрузки Azure для предоставления конечных точек PostgreSQL для запроса.

1. Получите имя группы ресурсов узла кластера AKS с помощью [`az aks show`][az-aks-show] команды.

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME=$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query nodeResourceGroup \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME
    ```

2. Создайте общедоступный IP-адрес с помощью [`az network public-ip create`][az-network-public-ip-create] команды.

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

3. Получите только что созданный общедоступный IP-адрес с помощью [`az network public-ip show`][az-network-public-ip-show] команды.

    ```bash
    export AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS=$(az network public-ip show \
        --resource-group $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --name $AKS_PRIMARY_CLUSTER_PUBLICIP_NAME \
        --query ipAddress \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS
    ```

4. Получите идентификатор ресурса группы ресурсов узла с помощью [`az group show`][az-group-show] команды.

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE=$(az group show --name \
        $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --query id \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE
    ```

5. Назначьте роль "Участник сети" идентификатору объекта UAMI с помощью области группы ресурсов узла с помощью [`az role assignment create`][az-role-assignment-create] команды.

    ```bash
    az role assignment create \
        --assignee-object-id ${AKS_UAMI_WORKLOAD_OBJECTID} \
        --assignee-principal-type ServicePrincipal \
        --role "Network Contributor" \
        --scope ${AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE}
    ```

## Установка оператора CNPG в кластере AKS

В этом разделе описано, как установить оператор CNPG в кластере AKS с помощью Helm или манифеста YAML.

### [Helm](#tab/helm)

1. Добавьте репозиторий CNPG Helm с помощью [`helm repo add`][helm-repo-add] команды.

    ```bash
    helm repo add cnpg https://cloudnative-pg.github.io/charts
    ```

2. Обновите репозиторий CNPG Helm и установите его в кластере AKS с помощью [`helm upgrade`][helm-upgrade] команды с флагом.`--install`

    ```bash
    helm upgrade --install cnpg \
        --namespace $PG_SYSTEM_NAMESPACE \
        --create-namespace \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME \
        cnpg/cloudnative-pg
    ```

3. Проверьте установку оператора в кластере AKS с помощью [`kubectl get`][kubectl-get] команды.

    ```bash
    kubectl get deployment \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-cloudnative-pg
    ```

### [YAML](#tab/yaml)

1. Установите оператор CNPG в кластере AKS с помощью [`kubectl apply`][kubectl-apply] команды.

    ```bash
    kubectl apply --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE \
        --server-side -f \
        https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.23/releases/cnpg-1.23.1.yaml
    ```

2. Проверьте установку оператора в кластере AKS с помощью [`kubectl get`][kubectl-get] команды.

    ```bash
    kubectl get deployment \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-controller-manager \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

---

## Следующие шаги

> [!div class="nextstepaction"]
> [Развертывание высокодоступной базы данных PostgreSQL в кластере AKS][deploy-postgresql]

## Соавторы

*Эта статья поддерживается корпорацией Майкрософт. Первоначально он был написан следующими участниками*:

* Кен Килти | Основной TPM
* Рассел де Пина | Основной TPM
* Адриан Джоан | Старший инженер клиента
* Дженни Хейс | Старший разработчик содержимого
* Кэрол Смит | Старший разработчик содержимого
* Эрин Шаффер | Разработчик содержимого 2

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
