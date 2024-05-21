---
title: Руководство по развертыванию WordPress в кластере AKS с помощью Azure CLI
description: 'Сведения о том, как быстро создать и развернуть WordPress в AKS с гибким сервером Базы данных Azure для MySQL.'
ms.service: mysql
ms.subservice: flexible-server
author: mksuni
ms.author: sumuth
ms.topic: tutorial
ms.date: 3/20/2024
ms.custom: 'vc, devx-track-azurecli, innovation-engine, linux-related-content'
---

# Руководство по развертыванию приложения WordPress в AKS с помощью База данных Azure для MySQL — гибкий сервер

[!INCLUDE[applies-to-mysql-flexible-server](../includes/applies-to-mysql-flexible-server.md)]

[![Развертывание в Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262843)

В этом руководстве вы развернете масштабируемое приложение WordPress, защищенное через HTTPS, в кластере Служба Azure Kubernetes (AKS) с База данных Azure для MySQL гибким сервером с помощью Azure CLI.
**[AKS](../../aks/intro-kubernetes.md)**  — это управляемая служба Kubernetes, которая позволяет быстро развертывать кластеры и управлять ими. **[гибкий сервер](overview.md)** База данных Azure для MySQL — это полностью управляемая служба базы данных, предназначенная для более детального управления и гибкости функций управления базами данных и параметров конфигурации.

> [!NOTE]
> В этом руководстве предполагается базовое понимание концепций Kubernetes, WordPress и MySQL.

[!INCLUDE [flexible-server-free-trial-note](../includes/flexible-server-free-trial-note.md)]

## Необходимые компоненты 

Прежде чем приступить к работе, убедитесь, что вы вошли в Azure CLI и выбрали подписку для использования с интерфейсом командной строки. Убедитесь, что [установлен](https://helm.sh/docs/intro/install/) Helm.

> [!NOTE]
> Если вы выполняете команды в этом руководстве локально вместо Azure Cloud Shell, выполните команды от имени администратора.

## Определение переменных среды

Первым шагом в этом руководстве является определение переменных среды.

```bash
export SSL_EMAIL_ADDRESS="$(az account show --query user.name --output tsv)"
export NETWORK_PREFIX="$(($RANDOM % 253 + 1))"
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myWordPressAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_PUBLIC_IP_NAME="myPublicIP$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
export MY_VNET_NAME="myVNet$RANDOM_ID"
export MY_VNET_PREFIX="10.$NETWORK_PREFIX.0.0/16"
export MY_SN_NAME="mySN$RANDOM_ID"
export MY_SN_PREFIX="10.$NETWORK_PREFIX.0.0/22"
export MY_MYSQL_DB_NAME="mydb$RANDOM_ID"
export MY_MYSQL_ADMIN_USERNAME="dbadmin$RANDOM_ID"
export MY_MYSQL_ADMIN_PW="$(openssl rand -base64 32)"
export MY_MYSQL_SN_NAME="myMySQLSN$RANDOM_ID"
export MY_MYSQL_HOSTNAME="$MY_MYSQL_DB_NAME.mysql.database.azure.com"
export MY_WP_ADMIN_PW="$(openssl rand -base64 32)"
export MY_WP_ADMIN_USER="wpcliadmin"
export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
```

## Создание или изменение группы ресурсов

Группа ресурсов Azure — это логическая группа, в которой развертываются и управляются ресурсы Azure. Все ресурсы должны быть помещены в группу ресурсов. Следующая команда создает группу ресурсов с ранее определенными `$MY_RESOURCE_GROUP_NAME` и `$REGION` параметрами.

```bash
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION
```

Результаты.
<!-- expected_similarity=0.3 -->
```json
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX",
  "location": "eastus",
  "managedBy": null,
  "name": "testResourceGroup",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

> [!NOTE]
> Расположением для группы ресурсов называется место хранения метаданных для этой группы ресурсов. Это также место, где ресурсы выполняются в Azure, если вы не указываете другой регион во время создания ресурса.

## Создание виртуальной сети и подсети

Виртуальная сеть — это базовый стандартный блок для частных сетей в Azure. Azure виртуальная сеть позволяет ресурсам Azure, таким как виртуальные машины, безопасно взаимодействовать друг с другом и Интернетом.

```bash
az network vnet create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --name $MY_VNET_NAME \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefixes $MY_SN_PREFIX
```

Результаты.
<!-- expected_similarity=0.3 -->
```json
{
  "newVNet": {
    "addressSpace": {
      "addressPrefixes": [
        "10.210.0.0/16"
      ]
    },
    "enableDdosProtection": false,
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/myWordPressAKSResourceGroupXXX/providers/Microsoft.Network/virtualNetworks/myVNetXXX",
    "location": "eastus",
    "name": "myVNet210",
    "provisioningState": "Succeeded",
    "resourceGroup": "myWordPressAKSResourceGroupXXX",
    "subnets": [
      {
        "addressPrefix": "10.210.0.0/22",
        "delegations": [],
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/myWordPressAKSResourceGroupXXX/providers/Microsoft.Network/virtualNetworks/myVNetXXX/subnets/mySNXXX",
        "name": "mySN210",
        "privateEndpointNetworkPolicies": "Disabled",
        "privateLinkServiceNetworkPolicies": "Enabled",
        "provisioningState": "Succeeded",
        "resourceGroup": "myWordPressAKSResourceGroupXXX",
        "type": "Microsoft.Network/virtualNetworks/subnets"
      }
    ],
    "type": "Microsoft.Network/virtualNetworks",
    "virtualNetworkPeerings": []
  }
}
```

## Создание гибкого экземпляра сервера База данных Azure для MySQL

База данных Azure для MySQL гибкий сервер — это управляемая служба, которую можно использовать для запуска, управления и масштабирования высокодоступных серверов MySQL в облаке. Создайте База данных Azure для MySQL гибкий экземпляр сервера с [помощью команды az mysql flexible-server create](/cli/azure/mysql/flexible-server). Сервер может управлять несколькими базами данных. Следующая команда создает сервер с помощью значений по умолчанию службы и переменных из локального контекста Azure CLI:

```bash
echo "Your MySQL user $MY_MYSQL_ADMIN_USERNAME password is: $MY_WP_ADMIN_PW" 
```

```bash
az mysql flexible-server create \
    --admin-password $MY_MYSQL_ADMIN_PW \
    --admin-user $MY_MYSQL_ADMIN_USERNAME \
    --auto-scale-iops Disabled \
    --high-availability Disabled \
    --iops 500 \
    --location $REGION \
    --name $MY_MYSQL_DB_NAME \
    --database-name wordpress \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --sku-name Standard_B2s \
    --storage-auto-grow Disabled \
    --storage-size 20 \
    --subnet $MY_MYSQL_SN_NAME \
    --private-dns-zone $MY_DNS_LABEL.private.mysql.database.azure.com \
    --tier Burstable \
    --version 8.0.21 \
    --vnet $MY_VNET_NAME \
    --yes -o JSON
```

Результаты.
<!-- expected_similarity=0.3 -->
```json
{
  "databaseName": "wordpress",
  "host": "mydbxxx.mysql.database.azure.com",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX/providers/Microsoft.DBforMySQL/flexibleServers/mydbXXX",
  "location": "East US",
  "resourceGroup": "myWordPressAKSResourceGroupXXX",
  "skuname": "Standard_B2s",
  "subnetId": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX/providers/Microsoft.Network/virtualNetworks/myVNetXXX/subnets/myMySQLSNXXX",
  "username": "dbadminxxx",
  "version": "8.0.21"
}
```

Созданный сервер имеет следующие атрибуты:

- При первой подготовке сервера создается новая пустая база данных.
- Имя сервера, имя администратора, пароль администратора, имя группы ресурсов и расположение уже указаны в локальной контекстной среде облачной оболочки и находятся в том же расположении, что и группа ресурсов и другие компоненты Azure.
- По умолчанию служба для оставшихся конфигураций сервера — это уровень вычислений (с возможностью ускорения), размер вычислительных ресурсов и номер SKU (Standard_B2s), период хранения резервных копий (семь дней) и версия MySQL (8.0.21).
- Метод подключения по умолчанию — это частный доступ (интеграция виртуальной сети) с связанной виртуальной сетью и автоматически созданной подсетью.

> [!NOTE]
> После создания сервера нельзя изменить метод подключения. Например, если вы выбрали `Private access (VNet Integration)` во время создания, вы не можете изменить его `Public access (allowed IP addresses)` после создания. Мы настоятельно рекомендуем создать сервер с закрытым доступом, чтобы безопасно обращаться к нему через интеграцию с виртуальной сетью. Дополнительные сведения о закрытом доступе см. в статье с [основными понятиями](./concepts-networking-vnet.md).

Если вы хотите изменить значения по умолчанию, ознакомьтесь со справочной документацией[ по Azure CLI для полного списка настраиваемых параметров CLI](/cli/azure//mysql/flexible-server).

## Проверка состояния База данных Azure для MySQL — гибкий сервер

Создание База данных Azure для MySQL — гибкий сервер и вспомогательные ресурсы занимает несколько минут.

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## Настройка параметров сервера в База данных Azure для MySQL — гибкий сервер

Вы можете управлять База данных Azure для MySQL — гибкой конфигурацией сервера с помощью параметров сервера. При создании сервера для параметров сервера устанавливаются используемые по умолчанию и рекомендуемые значения.

Чтобы посмотреть сведения об определенном параметре сервера, выполните команду [az mysql flexible-server parameter show](/cli/azure/mysql/flexible-server/parameter).

### Отключение База данных Azure для MySQL — параметр ssl-подключения гибкого сервера для интеграции WordPress

Можно также изменить значение определенных параметров сервера, чтобы обновить базовые значения конфигурации для ядра сервера MySQL. Чтобы обновить параметр сервера, используйте команду [az mysql flexible-server parameter set](/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set).

```bash
az mysql flexible-server parameter set \
    -g $MY_RESOURCE_GROUP_NAME \
    -s $MY_MYSQL_DB_NAME \
    -n require_secure_transport -v "OFF" -o JSON
```

Результаты.
<!-- expected_similarity=0.3 -->
```json
{
  "allowedValues": "ON,OFF",
  "currentValue": "OFF",
  "dataType": "Enumeration",
  "defaultValue": "ON",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX/providers/Microsoft.DBforMySQL/flexibleServers/mydbXXX/configurations/require_secure_transport",
  "isConfigPendingRestart": "False",
  "isDynamicConfig": "True",
  "isReadOnly": "False",
  "name": "require_secure_transport",
  "resourceGroup": "myWordPressAKSResourceGroupXXX",
  "source": "user-override",
  "systemData": null,
  "type": "Microsoft.DBforMySQL/flexibleServers/configurations",
  "value": "OFF"
}
```

## Создание кластера AKS

Чтобы создать кластер AKS с помощью контейнера Аналитика, используйте [команду az aks create](/cli/azure/aks#az-aks-create) с параметром **мониторинга --enable-addons**. В следующем примере создается кластер с поддержкой автомасштабирования с поддержкой зоны доступности с именем **myAKSCluster**:

Это действие занимает несколько минут.

```bash
export MY_SN_ID=$(az network vnet subnet list --resource-group $MY_RESOURCE_GROUP_NAME --vnet-name $MY_VNET_NAME --query "[0].id" --output tsv)

az aks create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_AKS_CLUSTER_NAME \
    --auto-upgrade-channel stable \
    --enable-cluster-autoscaler \
    --enable-addons monitoring \
    --location $REGION \
    --node-count 1 \
    --min-count 1 \
    --max-count 3 \
    --network-plugin azure \
    --network-policy azure \
    --vnet-subnet-id $MY_SN_ID \
    --no-ssh-key \
    --node-vm-size Standard_DS2_v2 \
    --service-cidr 10.255.0.0/24 \
    --dns-service-ip 10.255.0.10 \
    --zones 1 2 3
```
> [!NOTE]
> При создании кластера AKS для хранения ресурсов AKS автоматически создается вторая группа ресурсов. См. раздел [Почему с AKS создаются две группы ресурсов?](../../aks/faq.md#why-are-two-resource-groups-created-with-aks)

## Подключение к кластеру

Управлять кластером Kubernetes можно при помощи [kubectl](https://kubernetes.io/docs/reference/kubectl/overview/), клиента командной строки Kubernetes. Если вы используете Azure Cloud Shell, `kubectl` уже установлен. Следующий пример устанавливает `kubectl` локально с помощью [команды az aks install-cli](/cli/azure/aks#az-aks-install-cli) . 

 ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
```

Затем настройте `kubectl` подключение к кластеру Kubernetes с помощью [команды az aks get-credentials](/cli/azure/aks#az-aks-get-credentials) . Эта команда скачивает учетные данные и настраивает интерфейс командной строки Kubernetes для их использования. Команда использует `~/.kube/config`расположение по умолчанию для [файла](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/) конфигурации Kubernetes. Можно указать другое расположение для файла конфигурации Kubernetes с помощью аргумента **--file** .

> [!WARNING]
> Эта команда перезаписывает все существующие учетные данные с той же записью.

```bash
az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
```

Чтобы проверить подключение к кластеру, используйте команду [kubectl get]( https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#get) для получения списка узлов кластера.

```bash
kubectl get nodes
```

## Установка контроллера входящего трафика NGINX

Контроллер входящего трафика можно настроить со статическим общедоступным IP-адресом. Статический общедоступный IP-адрес остается при удалении контроллера входящего трафика. IP-адрес не остается, если удалить кластер AKS.
При обновлении контроллера входящего трафика необходимо передать параметр в выпуск Helm, чтобы служба контроллера входящего трафика была осведомлена о подсистеме балансировки нагрузки, которая будет выделена для него. Чтобы сертификаты HTTPS работали правильно, используйте метку DNS для настройки полного доменного имени (FQDN) для IP-адреса контроллера входящего трафика. Полное доменное имя должно соответствовать этой форме: $MY_DNS_LABEL. AZURE_REGION_NAME.cloudapp.azure.com.

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

Затем добавьте репозиторий ingress-nginx Helm, обновите локальный кэш репозитория диаграммы Helm и установите надстройку ingress-nginx через Helm. Вы можете задать метку DNS с **помощью --set controller.service.annotations". параметр service\.beta\.kubernetes\.io/azure-dns-label-name"="<DNS_LABEL>"** параметр при первом развертывании контроллера входящего трафика или более поздней версии. В этом примере вы укажите собственный общедоступный IP-адрес, созданный на предыдущем шаге, с параметром ****--set controller.service.loadBalancerIP="<STATIC_IP>".

```bash
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    helm repo update
    helm upgrade --install --cleanup-on-fail --atomic ingress-nginx ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --create-namespace \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"=$MY_DNS_LABEL \
        --set controller.service.loadBalancerIP=$MY_STATIC_IP \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
        --wait --timeout 10m0s
```

## Добавление завершения HTTPS в личный домен

На этом этапе руководства у вас есть веб-приложение AKS с NGINX в качестве контроллера входящего трафика и личного домена, который можно использовать для доступа к приложению. Следующий шаг — добавить SSL-сертификат в домен, чтобы пользователи могли безопасно связаться с приложением через https.

### Настройка диспетчера сертификатов

Чтобы добавить ПРОТОКОЛ HTTPS, мы будем использовать диспетчер сертификатов. Cert Manager — это средство открытый код для получения SSL-сертификатов и управления ими для развертываний Kubernetes. Cert Manager получает сертификаты от популярных общедоступных издателей и частных издателей, гарантирует, что сертификаты действительны и актуальны, и пытается продлить сертификаты в заданное время до истечения срока их действия.

1. Чтобы установить cert-manager, сначала необходимо создать пространство имен для его запуска. В этом руководстве cert-manager устанавливается в пространство имен cert-manager. Вы можете запустить диспетчер сертификатов в другом пространстве имен, но необходимо внести изменения в манифесты развертывания.

    ```bash
    kubectl create namespace cert-manager
    ```

2. Теперь можно установить cert-manager. Все ресурсы включены в один файл манифеста YAML. Установите файл манифеста с помощью следующей команды:

    ```bash
    kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
    ```

3. `certmanager.k8s.io/disable-validation: "true"` Добавьте метку в пространство имен cert-manager, выполнив следующую команду. Это позволяет системным ресурсам, которым диспетчер сертификатов требуется создать TLS начальной загрузки в собственном пространстве имен.

    ```bash
    kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
    ```

## Получение сертификата с помощью диаграмм Helm

Helm — это средство развертывания Kubernetes для автоматизации создания, упаковки, настройки и развертывания приложений и служб в кластерах Kubernetes.

Cert-manager предоставляет диаграммы Helm в качестве первого класса метода установки в Kubernetes.

1. Добавьте репозиторий Helm Jetstack. Этот репозиторий является единственным поддерживаемым источником диаграмм cert-manager. Существуют другие зеркало и копии через Интернет, но они являются неофициальными и могут представлять угрозу безопасности.

    ```bash
    helm repo add jetstack https://charts.jetstack.io
    ```

2. Обновите локальную диаграмму Helm кэш репозитория.

    ```bash
    helm repo update
    ```

3. Установите надстройку Cert-Manager через Helm.

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. Примените файл YAML издателя сертификатов. ClusterIssuers — это ресурсы Kubernetes, представляющие центры сертификации (ЦС), которые могут создавать подписанные сертификаты, выполняя запросы на подписывание сертификатов. Для всех сертификатов диспетчера сертификатов требуется указанный издатель, который находится в состоянии готовности, чтобы попытаться выполнить запрос. Вы можете найти издателя, в который `cluster-issuer-prod.yml file`мы находимся.

    ```bash
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## Создание пользовательского класса хранения

Классы хранения по умолчанию соответствуют наиболее распространенным сценариям, но не всем. В некоторых случаях может потребоваться настроить собственный класс хранения с собственными параметрами. Например, используйте следующий манифест для настройки **mountOptions** общей папки.
Значение по умолчанию для **fileMode и **dirMode**** — **0755** для подключенных общих папок Kubernetes. Для объекта класса хранения можно указать различные параметры подключения.

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## Развертывание WordPress в кластере AKS

В этом руководстве мы используем существующую диаграмму Helm для WordPress, созданную Bitnami. Диаграмма Bitnami Helm использует локальный MariaDB в качестве базы данных, поэтому необходимо переопределить эти значения для использования приложения с База данных Azure для MySQL. Вы можете переопределить значения и настраиваемые параметры `helm-wp-aks-values.yaml` файла.

1. Добавьте репозиторий Wordpress Bitnami Helm.

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. Обновите локальную диаграмму Helm кэш репозитория.

    ```bash
    helm repo update
    ```

3. Установите рабочую нагрузку Wordpress через Helm.

    ```bash
    helm upgrade --install --cleanup-on-fail \
        --wait --timeout 10m0s \
        --namespace wordpress \
        --create-namespace \
        --set wordpressUsername="$MY_WP_ADMIN_USER" \
        --set wordpressPassword="$MY_WP_ADMIN_PW" \
        --set wordpressEmail="$SSL_EMAIL_ADDRESS" \
        --set externalDatabase.host="$MY_MYSQL_HOSTNAME" \
        --set externalDatabase.user="$MY_MYSQL_ADMIN_USERNAME" \
        --set externalDatabase.password="$MY_MYSQL_ADMIN_PW" \
        --set ingress.hostname="$FQDN" \
        --values helm-wp-aks-values.yaml \
        wordpress bitnami/wordpress
    ```

Результаты.
<!-- expected_similarity=0.3 -->
```text
Release "wordpress" does not exist. Installing it now.
NAME: wordpress
LAST DEPLOYED: Tue Oct 24 16:19:35 2023
NAMESPACE: wordpress
STATUS: deployed
REVISION: 1
TEST SUITE: None
NOTES:
CHART NAME: wordpress
CHART VERSION: 18.0.8
APP VERSION: 6.3.2

** Please be patient while the chart is being deployed **

Your WordPress site can be accessed through the following DNS name from within your cluster:

    wordpress.wordpress.svc.cluster.local (port 80)

To access your WordPress site from outside the cluster follow the steps below:

1. Get the WordPress URL and associate WordPress hostname to your cluster external IP:

   export CLUSTER_IP=$(minikube ip) # On Minikube. Use: `kubectl cluster-info` on others K8s clusters
   echo "WordPress URL: https://mydnslabelxxx.eastus.cloudapp.azure.com/"
   echo "$CLUSTER_IP  mydnslabelxxx.eastus.cloudapp.azure.com" | sudo tee -a /etc/hosts
    export CLUSTER_IP=$(minikube ip) # On Minikube. Use: `kubectl cluster-info` on others K8s clusters
    echo "WordPress URL: https://mydnslabelxxx.eastus.cloudapp.azure.com/"
    echo "$CLUSTER_IP  mydnslabelxxx.eastus.cloudapp.azure.com" | sudo tee -a /etc/hosts

2. Open a browser and access WordPress using the obtained URL.

3. Login with the following credentials below to see your blog:

    echo Username: wpcliadmin
    echo Password: $(kubectl get secret --namespace wordpress wordpress -o jsonpath="{.data.wordpress-password}" | base64 -d)
```

## Просмотр развертывания AKS, защищенного через HTTPS

Выполните следующую команду, чтобы получить конечную точку HTTPS для приложения:

> [!NOTE]
> Часто требуется 2–3 минуты для распространения SSL-сертификата и около 5 минут, чтобы все реплика POD WordPress были готовы и сайт полностью доступен через https.

```bash
runtime="5 minute"
endtime=$(date -ud "$runtime" +%s)
while [[ $(date -u +%s) -le $endtime ]]; do
    export DEPLOYMENT_REPLICAS=$(kubectl -n wordpress get deployment wordpress -o=jsonpath='{.status.availableReplicas}');
    echo Current number of replicas "$DEPLOYMENT_REPLICAS/3";
    if [ "$DEPLOYMENT_REPLICAS" = "3" ]; then
        break;
    else
        sleep 10;
    fi;
done
```

Убедитесь, что содержимое WordPress доставлено правильно с помощью следующей команды:

```bash
if curl -I -s -f https://$FQDN > /dev/null ; then 
    curl -L -s -f https://$FQDN 2> /dev/null | head -n 9
else 
    exit 1
fi;
```

Результаты.
<!-- expected_similarity=0.3 -->
```HTML
{
<!DOCTYPE html>
<html lang="en-US">
<head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name='robots' content='max-image-preview:large' />
<title>WordPress on AKS</title>
<link rel="alternate" type="application/rss+xml" title="WordPress on AKS &raquo; Feed" href="https://mydnslabelxxx.eastus.cloudapp.azure.com/feed/" />
<link rel="alternate" type="application/rss+xml" title="WordPress on AKS &raquo; Comments Feed" href="https://mydnslabelxxx.eastus.cloudapp.azure.com/comments/feed/" />
}
```

Посетите веб-сайт по следующему URL-адресу:

```bash
echo "You can now visit your web server at https://$FQDN"
```

## Очистка ресурсов (необязательно)

Чтобы избежать расходов за использование Azure, необходимо удалить ненужные ресурсы. Если кластер больше не нужен, используйте [команду az group delete](/cli/azure/group#az-group-delete) , чтобы удалить группу ресурсов, службу контейнеров и все связанные ресурсы. 

> [!NOTE]
> При удалении кластера субъект-служба Microsoft Entra, используемая кластером AKS, не удаляется. Инструкции по удалению субъекта-службы см. в разделе с [дополнительными замечаниями](../../aks/kubernetes-service-principal.md#other-considerations). Управляемые удостоверения администрируются платформой, и их не нужно удалять.

## Следующие шаги

- Узнайте, как [открыть веб-панель мониторинга Kubernetes](../../aks/kubernetes-dashboard.md) для кластера AKS.
- Узнайте, как [масштабировать кластер](../../aks/tutorial-kubernetes-scale.md).
- Узнайте, как управлять [гибким экземпляром сервера База данных Azure для MySQL](./quickstart-create-server-cli.md)
- Узнайте, как [настроить параметры](./how-to-configure-server-parameters-cli.md) сервера для сервера базы данных
