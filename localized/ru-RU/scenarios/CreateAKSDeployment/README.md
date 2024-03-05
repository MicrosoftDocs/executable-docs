---
title: Развертывание масштабируемого кластера и безопасного Служба Azure Kubernetes с помощью Azure CLI
description: 'В этом руководстве мы пошаговые инструкции по созданию веб-приложения Azure Kubernetes, защищенного через https.'
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Краткое руководство. Развертывание масштабируемого и безопасного кластера Служба Azure Kubernetes с помощью Azure CLI

[![Развертывание в Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateAKSDeployment)

Добро пожаловать в это руководство, где мы пошаговые инструкции по созданию веб-приложения Azure Kubernetes, защищенного через https. В этом руководстве предполагается, что вы уже вошли в Azure CLI и выбрали подписку для использования с интерфейсом командной строки. Кроме того, предполагается, что установлен Helm ([инструкции можно найти здесь](https://helm.sh/docs/intro/install/)).

## Определение переменных среды

Первым шагом в этом руководстве является определение переменных среды.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export NETWORK_PREFIX="$(($RANDOM % 254 + 1))"
export SSL_EMAIL_ADDRESS="$(az account show --query user.name --output tsv)"
export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID"
export REGION="eastus"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_PUBLIC_IP_NAME="myPublicIP$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
export MY_VNET_NAME="myVNet$RANDOM_ID"
export MY_VNET_PREFIX="10.$NETWORK_PREFIX.0.0/16"
export MY_SN_NAME="mySN$RANDOM_ID"
export MY_SN_PREFIX="10.$NETWORK_PREFIX.0.0/22"
export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
```

## Создание или изменение группы ресурсов

Группа ресурсов — это контейнер для связанных ресурсов. Все ресурсы должны быть помещены в группу ресурсов. Мы создадим его для этого руководства. Следующая команда создает группу ресурсов с ранее определенными параметрами $MY_RESOURCE_GROUP_NAME и $REGION.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Результаты.

<!-- expected_similarity=0.3 -->

```JSON
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myAKSResourceGroupxxxxxx",
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

```JSON
{
  "newVNet": {
    "addressSpace": {
      "addressPrefixes": [
        "10.xxx.0.0/16"
      ]
    },
    "enableDdosProtection": false,
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/myAKSResourceGroupxxxxxx/providers/Microsoft.Network/virtualNetworks/myVNetxxx",
    "location": "eastus",
    "name": "myVNetxxx",
    "provisioningState": "Succeeded",
    "resourceGroup": "myAKSResourceGroupxxxxxx",
    "subnets": [
      {
        "addressPrefix": "10.xxx.0.0/22",
        "delegations": [],
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/myAKSResourceGroupxxxxxx/providers/Microsoft.Network/virtualNetworks/myVNetxxx/subnets/mySNxxx",
        "name": "mySNxxx",
        "privateEndpointNetworkPolicies": "Disabled",
        "privateLinkServiceNetworkPolicies": "Enabled",
        "provisioningState": "Succeeded",
        "resourceGroup": "myAKSResourceGroupxxxxxx",
        "type": "Microsoft.Network/virtualNetworks/subnets"
      }
    ],
    "type": "Microsoft.Network/virtualNetworks",
    "virtualNetworkPeerings": []
  }
}
```

## Регистрация в поставщиках ресурсов Azure AKS

Убедитесь, что в подписке зарегистрированы поставщики Microsoft.OperationsManagement и Microsoft.OperationalInsights. Эти поставщики ресурсов Azure требуются для поддержки [Аналитики контейнеров](https://docs.microsoft.com/azure/azure-monitor/containers/container-insights-overview). Чтобы проверка состояние регистрации, выполните следующие команды.

```bash
az provider register --namespace Microsoft.Insights
az provider register --namespace Microsoft.OperationsManagement
az provider register --namespace Microsoft.OperationalInsights
```

## Создание кластера AKS

Создайте кластер AKS с помощью команды az aks create, задав для нее параметр --enable-addons monitoring, чтобы включить аналитику для контейнеров. В следующем примере создается кластер с поддержкой автомасштабирования, зоны доступности.

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

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"=$MY_DNS_LABEL \
  --set controller.service.loadBalancerIP=$MY_STATIC_IP \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
  --wait
```

## Развертывание приложения

Файл манифеста Kubernetes используется для определения требуемого состояния кластера, например выполняемых в нем образов контейнеров.

В этом кратком руководстве вы примените манифест для создания всех объектов, необходимых для запуска приложения Azure для голосования. Этот манифест содержит два развертывания Kubernetes:

- пример приложения Azure для голосования на языке Python;
- экземпляр Redis.

Кроме того, создаются две Службы Kubernetes:

- внутренняя служба для экземпляра Redis;
- внешняя служба для доступа к приложению Azure для голосования из Интернета.

Наконец, создается ресурс входящего трафика для маршрутизации трафика в приложение Azure Vote.

Тестовый файл YML приложения для голосования уже подготовлен. Чтобы развернуть это приложение, выполните следующую команду.

```bash
kubectl apply -f azure-vote-start.yml
```

## Тестирование приложения

Убедитесь, что приложение запущено путем посещения общедоступного IP-адреса или URL-адреса приложения. URL-адрес приложения можно найти, выполнив следующую команду:

> [!Note]
> Часто требуется 2–3 минуты для создания POD и доступ к сайту через HTTP

```bash
runtime="5 minute";
endtime=$(date -ud "$runtime" +%s);
while [[ $(date -u +%s) -le $endtime ]]; do
   STATUS=$(kubectl get pods -l app=azure-vote-front -o 'jsonpath={..status.conditions[?(@.type=="Ready")].status}'); echo $STATUS;
   if [ "$STATUS" == 'True' ]; then
      break;
   else
      sleep 10;
   fi;
done
```

```bash
curl "http://$FQDN"
```

Результаты.

<!-- expected_similarity=0.3 -->

```HTML
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <link rel="stylesheet" type="text/css" href="/static/default.css">
    <title>Azure Voting App</title>

    <script language="JavaScript">
        function send(form){
        }
    </script>

</head>
<body>
    <div id="container">
        <form id="form" name="form" action="/"" method="post"><center>
        <div id="logo">Azure Voting App</div>
        <div id="space"></div>
        <div id="form">
        <button name="vote" value="Cats" onclick="send()" class="button button1">Cats</button>
        <button name="vote" value="Dogs" onclick="send()" class="button button2">Dogs</button>
        <button name="vote" value="reset" onclick="send()" class="button button3">Reset</button>
        <div id="space"></div>
        <div id="space"></div>
        <div id="results"> Cats - 0 | Dogs - 0 </div>
        </form>
        </div>
    </div>
</body>
</html>
```

## Добавление завершения HTTPS в личный домен

На этом этапе руководства у вас есть веб-приложение AKS с NGINX в качестве контроллера входящего трафика и личного домена, который можно использовать для доступа к приложению. Следующий шаг — добавить SSL-сертификат в домен, чтобы пользователи могли безопасно связаться с приложением через HTTPS.

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

3. Установите надстройку Cert-Manager через helm, выполнив следующую команду:

   ```bash
   helm install cert-manager jetstack/cert-manager --namespace cert-manager --version v1.7.0
   ```

4. Применение YAML-файла издателя сертификатов

   ClusterIssuers — это ресурсы Kubernetes, представляющие центры сертификации (ЦС), которые могут создавать подписанные сертификаты, выполняя запросы на подписывание сертификатов. Для всех сертификатов диспетчера сертификатов требуется указанный издатель, который находится в состоянии готовности, чтобы попытаться выполнить запрос.
   Издатель, который мы используем, можно найти в . `cluster-issuer-prod.yml file`

   ```bash
   cluster_issuer_variables=$(<cluster-issuer-prod.yml)
   echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
   ```

5. Upate Voting App Application to use Cert-Manager to get a SSL Certificate.

   Полный файл YAML можно найти в `azure-vote-nginx-ssl.yml`

   ```bash
   azure_vote_nginx_ssl_variables=$(<azure-vote-nginx-ssl.yml)
   echo "${azure_vote_nginx_ssl_variables//\$FQDN/$FQDN}" | kubectl apply -f -
   ```

<!--## Validate application is working

Wait for the SSL certificate to issue. The following command will query the 
status of the SSL certificate for 3 minutes. In rare occasions it may take up to 
15 minutes for Lets Encrypt to issue a successful challenge and 
the ready state to be 'True'

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(kubectl get certificate --output jsonpath={..status.conditions[0].status}); echo $STATUS; if [ "$STATUS" = 'True' ]; then break; else sleep 10; fi; done
```

Validate SSL certificate is True by running the follow command:

```bash
kubectl get certificate --output jsonpath={..status.conditions[0].status}
```

Results:

<!-- expected_similarity=0.3 -->
<!--
```ASCII
True
```
-->

## Обзор развертывания AKS, защищенного через HTTPS

Выполните следующую команду, чтобы получить конечную точку HTTPS для приложения:

> [!Note]
> Часто требуется 2–3 минуты, чтобы ssl-сертификат пропогател и сайт был доступен через HTTPS.

```bash
runtime="5 minute";
endtime=$(date -ud "$runtime" +%s);
while [[ $(date -u +%s) -le $endtime ]]; do
   STATUS=$(kubectl get svc --namespace=ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}');
   echo $STATUS;
   if [ "$STATUS" == "$MY_STATIC_IP" ]; then
      break;
   else
      sleep 10;
   fi;
done
```

```bash
echo "You can now visit your web server at https://$FQDN"
```

## Next Steps

- [Документация по Службе Azure Kubernetes](https://learn.microsoft.com/azure/aks/)
- [Создание Реестр контейнеров Azure](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-prepare-acr?tabs=azure-cli)
- [Масштабирование applciation в AKS](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-scale?tabs=azure-cli)
- [Обновление приложения в AKS](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-app-update?tabs=azure-cli)
