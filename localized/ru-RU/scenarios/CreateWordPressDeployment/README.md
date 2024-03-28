---
title: Развертывание масштабируемого экземпляра WordPress в AKS
description: 'В этом руководстве показано, как развернуть экземпляр Scalable и Secure WordPress в AKS с помощью CLI'
author: adrian.joian
ms.author: adrian.joian
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Краткое руководство. Развертывание масштабируемого и безопасного экземпляра WordPress в AKS

[![Развертывание в Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262843)

Добро пожаловать в это руководство, где мы пошаговые инструкции по созданию веб-приложения Azure Kubernetes, защищенного через https. В этом руководстве предполагается, что вы уже вошли в Azure CLI и выбрали подписку для использования с интерфейсом командной строки. Кроме того, предполагается, что установлен Helm ([инструкции можно найти здесь](https://helm.sh/docs/intro/install/)).

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

Группа ресурсов — это контейнер для связанных ресурсов. Все ресурсы должны быть помещены в группу ресурсов. Мы создадим его для этого руководства. Следующая команда создает группу ресурсов с ранее определенными параметрами $MY_RESOURCE_GROUP_NAME и $REGION.

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

## Создание Гибкого сервера Базы данных Azure для MySQL

База данных Azure для MySQL . Гибкий сервер — это управляемая служба, которую можно использовать для запуска, управления и масштабирования серверов MySQL с высоким уровнем доступности в облаке. Создайте гибкий сервер с помощью команды [az mysql flexible-server create](https://learn.microsoft.com/cli/azure/mysql/flexible-server#az-mysql-flexible-server-create). Сервер может управлять несколькими базами данных. Следующая команда создает сервер с помощью значений по умолчанию службы и переменных из локальной среды Azure CLI:

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

Сервер создается со следующими атрибутами:

- Имя сервера, имя администратора, пароль администратора, имя группы ресурсов, расположение уже указано в локальной контекстной среде cloud shell и будет создано в том же расположении, что и группа ресурсов и другие компоненты Azure.
- По умолчанию службы для оставшихся конфигураций сервера: уровень вычислений (с возможностью ускорения), размер вычислительных ресурсов и номер SKU (Standard_B2s), период хранения резервных копий (7 дней) и MySQL (8.0.21)
- Метод подключения по умолчанию — это частный доступ (интеграция виртуальной сети) с связанной виртуальной сетью и автоматически созданной подсетью.

> [!NOTE]
> После создания сервера нельзя изменить метод подключения. Например, если вы выбрали `Private access (VNet Integration)` во время создания, вы не можете изменить его `Public access (allowed IP addresses)` после создания. Мы настоятельно рекомендуем создать сервер с закрытым доступом, чтобы безопасно обращаться к нему через интеграцию с виртуальной сетью. Дополнительные сведения о закрытом доступе см. в статье с [основными понятиями](https://learn.microsoft.com/azure/mysql/flexible-server/concepts-networking-vnet).

Если вы хотите изменить значения по умолчанию, воспользуйтесь [справочной документацией](https://learn.microsoft.com/cli/azure//mysql/flexible-server) по Azure CLI, где описаны все настраиваемые параметры интерфейса командной строки.

## Проверка состояния База данных Azure для MySQL — гибкий сервер

Создание База данных Azure для MySQL — гибкий сервер и вспомогательные ресурсы занимает несколько минут.

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## Настройка параметров сервера в База данных Azure для MySQL — гибкий сервер

Вы можете управлять База данных Azure для MySQL — гибкой конфигурацией сервера с помощью параметров сервера. При создании сервера для параметров сервера устанавливаются используемые по умолчанию и рекомендуемые значения.

Отображение сведений о параметрах сервера для отображения сведений о конкретном параметре для сервера выполните [команду az mysql flexible-server](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter) .

### Отключение База данных Azure для MySQL — параметр ssl-подключения гибкого сервера для интеграции WordPress

Можно также изменить значение определенных параметров сервера, которые обновляют базовые значения конфигурации для ядра сервера MySQL. Чтобы обновить параметр сервера, используйте команду [az mysql flexible-server parameter set](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set).

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

Создайте кластер AKS с помощью команды az aks create, задав для нее параметр --enable-addons monitoring, чтобы включить аналитику для контейнеров. В следующем примере создается кластер с поддержкой автомасштабирования с поддержкой зоны доступности с именем myAKSCluster:

Это займет несколько минут.

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

## Подключение к кластеру

Кластером Kubernetes можно управлять при помощи kubectl клиента командной строки Kubernetes. Kubectl уже установлен, если вы используете Azure Cloud Shell.

1. Установите az aks CLI локально с помощью команды az aks install-cli

    ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
    ```

2. Настройте kubectl для подключения к кластеру Kubernetes с помощью команды az aks get-credentials. Приведенная ниже команда:

    - скачивает учетные данные и настраивает интерфейс командной строки Kubernetes для их использования;
    - Использует ~/.kube/config, расположение по умолчанию для файла конфигурации Kubernetes. Чтобы указать другое расположение файла конфигурации Kubernetes, используйте аргумент --file.

    > [!WARNING]
    > При этом будут перезаписаны все существующие учетные данные с той же записью.

    ```bash
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
    ```

3. Проверьте подключение к кластеру, выполнив команду kubectl get. Эта команда возвращает список узлов кластера.

    ```bash
    kubectl get nodes
    ```

## Установка контроллера входящего трафика NGINX

Контроллер входящего трафика можно настроить со статическим общедоступным IP-адресом. Статический общедоступный IP-адрес остается при удалении контроллера входящего трафика. IP-адрес не остается, если удалить кластер AKS.
При обновлении контроллера входящего трафика необходимо передать параметр в выпуск Helm, чтобы служба контроллера входящего трафика была осведомлена о подсистеме балансировки нагрузки, которая будет выделена для него. Чтобы сертификаты HTTPS работали правильно, используйте метку DNS для настройки полного доменного имени для IP-адреса контроллера входящего трафика.
Полное доменное имя должно соответствовать этой форме: $MY_DNS_LABEL. AZURE_REGION_NAME.cloudapp.azure.com.

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

Добавьте --set controller.service.annotations". параметр service\.beta\.kubernetes\.io/azure-dns-label-name"="<DNS_LABEL>". Метку DNS можно задать либо при первом развертывании контроллера объекта ingress, либо настроить позже. Добавьте параметр --set controller.service.loadBalancerIP="<STATIC_IP>". Укажите собственный общедоступный IP-адрес, созданный на предыдущем шаге.

1. Добавление репозитория ingress-nginx Helm

    ```bash
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    ```

2. Обновление локальной диаграммы Helm кэш репозитория

    ```bash
    helm repo update
    ```

3. Установите надстройку ingress-nginx через Helm, выполнив следующую команду:

    ```bash
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

## Настройка диспетчера сертификатов

Чтобы добавить HTTPS, мы будем использовать диспетчер сертификатов. Cert Manager — это средство открытый код, используемое для получения SSL-сертификата и управления ими для развертываний Kubernetes. Диспетчер сертификатов получит сертификаты от различных издателей, как популярных общедоступных издателей, так и частных издателей, и гарантирует, что сертификаты действительны и актуальны, и попытаются обновить сертификаты в настроенное время до истечения срока действия.

1. Чтобы установить cert-manager, сначала необходимо создать пространство имен для его запуска. В этом руководстве показано, как установить cert-manager в пространство имен cert-manager. Можно запустить диспетчер сертификатов в другом пространстве имен, хотя вам потребуется внести изменения в манифесты развертывания.

    ```bash
    kubectl create namespace cert-manager
    ```

2. Теперь можно установить cert-manager. Все ресурсы включены в один файл манифеста YAML. Это можно установить, выполнив следующие действия:

    ```bash
    kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
    ```

3. Добавьте certmanager.k8s.io/disable-validation метку true в пространство имен cert-manager, выполнив следующую команду. Это позволит системным ресурсам, которым диспетчер сертификатов требуется создать TLS начальной загрузки в собственном пространстве имен.

    ```bash
    kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
    ```

## Получение сертификата с помощью диаграмм Helm

Helm — это средство развертывания Kubernetes для автоматизации создания, упаковки, настройки и развертывания приложений и служб в кластерах Kubernetes.

Cert-manager предоставляет диаграммы Helm в качестве первого класса метода установки в Kubernetes.

1. Добавление репозитория Jetstack Helm

    Этот репозиторий является единственным поддерживаемым источником диаграмм cert-manager. Есть некоторые другие зеркало и копии через Интернет, но они полностью неофициальны и могут представлять угрозу безопасности.

    ```bash
    helm repo add jetstack https://charts.jetstack.io
    ```

2. Обновление локальной диаграммы Helm кэш репозитория

    ```bash
    helm repo update
    ```

3. Установите надстройку Cert-Manager через Helm, выполнив следующую команду:

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. Применение YAML-файла издателя сертификатов

    ClusterIssuers — это ресурсы Kubernetes, представляющие центры сертификации (ЦС), которые могут создавать подписанные сертификаты, выполняя запросы на подписывание сертификатов. Для всех сертификатов диспетчера сертификатов требуется указанный издатель, который находится в состоянии готовности, чтобы попытаться выполнить запрос.
    Издатель, который мы используем, можно найти в . `cluster-issuer-prod.yml file`

    ```bash
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## Создание пользовательского класса хранения

Классы хранения по умолчанию соответствуют наиболее распространенным сценариям, но не всем. В некоторых случаях может потребоваться настроить собственный класс хранения с собственными параметрами. Например, используйте следующий манифест для настройки mountOptions общей папки.
Значение по умолчанию для fileMode и dirMode — 0755 для подключенных общих папок Kubernetes. Для объекта класса хранения можно указать различные параметры подключения.

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## Развертывание WordPress в кластере AKS

В этом документе мы используем существующую диаграмму Helm для WordPress, созданную Bitnami. Например, диаграмма Bitnami Helm использует local MariaDB в качестве базы данных, и нам нужно переопределить эти значения, чтобы использовать приложение с База данных Azure для MySQL. Все переопределения значений, которые можно переопределить, и настраиваемые параметры можно найти в файле. `helm-wp-aks-values.yaml`

1. Добавление репозитория Wordpress Bitnami Helm

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. Обновление локальной диаграммы Helm кэш репозитория

    ```bash
    helm repo update
    ```

3. Установите рабочую нагрузку Wordpress через Helm, выполнив следующую команду:

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

## Обзор развертывания AKS, защищенного через HTTPS

Выполните следующую команду, чтобы получить конечную точку HTTPS для приложения:

> [!NOTE]
> Часто требуется 2–3 минуты, чтобы ssl-сертификат пропогатировать и около 5 минут, чтобы все реплика POD WordPress были готовы и сайт будет полностью доступен через https.

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

Проверка правильности доставки содержимого WordPress.

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

Веб-сайт можно посетить по следующему URL-адресу:

```bash
echo "You can now visit your web server at https://$FQDN"
```
