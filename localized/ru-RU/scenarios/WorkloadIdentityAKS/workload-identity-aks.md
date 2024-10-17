---
title: Развертывание и настройка кластера AKS с удостоверением рабочей нагрузки
description: В этой статье Служба Azure Kubernetes (AKS) вы развернете кластер Служба Azure Kubernetes и настройте его с помощью Идентификация рабочей нагрузки Microsoft Entra.
author: tamram
ms.topic: article
ms.subservice: aks-security
ms.custom: devx-track-azurecli
ms.date: 05/28/2024
ms.author: tamram
---

# Развертывание и настройка удостоверения рабочей нагрузки в кластере Служба Azure Kubernetes (AKS)

Служба Azure Kubernetes (AKS) — это управляемая служба Kubernetes, которая позволяет быстро развертывать кластеры Kubernetes и управлять ими. Из этой статьи вы узнаете, как выполнять следующие задачи:

* Разверните кластер AKS с помощью Azure CLI с издателем OpenID Connect и Идентификация рабочей нагрузки Microsoft Entra.
* Создайте учетную запись службы Идентификация рабочей нагрузки Microsoft Entra и Kubernetes.
* Настройте управляемое удостоверение для федерации маркеров.
* Разверните рабочую нагрузку и проверьте проверку подлинности с помощью удостоверения рабочей нагрузки.
* При необходимости предоставьте pod в кластере доступ к секретам в хранилище ключей Azure.

В этой статье предполагается, что у вас есть базовое представление о концепциях Kubernetes. Дополнительные сведения см. в статье [Ключевые концепции Kubernetes для службы Azure Kubernetes (AKS)][kubernetes-concepts]. Если вы не знакомы с Идентификация рабочей нагрузки Microsoft Entra, ознакомьтесь со следующей [статьей обзора][workload-identity-overview].

## Необходимые компоненты

* [!INCLUDE [quickstarts-free-trial-note](~/reusable-content/ce-skilling/azure/includes/quickstarts-free-trial-note.md)]
* Для этой статьи требуется версия 2.47.0 или более поздняя версия Azure CLI. Если вы используете Azure Cloud Shell, последняя версия уже установлена.
* Убедитесь, что удостоверение, которое вы используете для создания кластера, имеет соответствующие минимальные разрешения. Дополнительные сведения о доступе и удостоверении для AKS см. в разделе ["Параметры доступа и удостоверения" для Служба Azure Kubernetes (AKS).][aks-identity-concepts]
* Если у вас несколько подписок Azure, выберите соответствующий идентификатор подписки, в котором необходимо выставлять счета за ресурсы с помощью [команды az account set][az-account-set] .

> [!NOTE]
> Соединитель_ служб можно использовать _для автоматической настройки некоторых шагов. См. также: руководство. [Подключение к учетной записи хранения Azure в Служба Azure Kubernetes (AKS) с помощью соединителя службы с помощью удостоверения рабочей нагрузки][tutorial-python-aks-storage-workload-identity].

## Создание или изменение группы ресурсов

[Группа ресурсов Azure][azure-resource-group] — это логическая группа, в которой развертываются и управляются ресурсы Azure. При создании группы ресурсов вам будет предложено указать расположение. Это расположение хранилища метаданных группы ресурсов и место, где ресурсы выполняются в Azure, если вы не указываете другой регион во время создания ресурса.

Создайте группу ресурсов, вызвав [команду az group create][az-group-create] :

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export RESOURCE_GROUP="myResourceGroup$RANDOM_ID"
export LOCATION="centralindia"
az group create --name "${RESOURCE_GROUP}" --location "${LOCATION}"
```

В следующем примере выходных данных показано успешное создание группы ресурсов:

Результаты.
<!-- expected_similarity=0.3 -->
```json
{
  "id": "/subscriptions/<guid>/resourceGroups/myResourceGroup",
  "location": "eastus",
  "managedBy": null,
  "name": "myResourceGroup",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Создание кластера AKS

Создайте кластер AKS с помощью [команды az aks create][az-aks-create] с параметром `--enable-oidc-issuer` , чтобы включить издателя OIDC. В следующем примере создается кластер с одним узлом:

```azurecli-interactive
export CLUSTER_NAME="myAKSCluster$RANDOM_ID"
az aks create \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity \
    --generate-ssh-keys
```

Через несколько минут выполнение команды завершается и отображаются сведения о кластере в формате JSON.

> [!NOTE]
> При создании кластера AKS автоматически создается вторая группа ресурсов для хранения ресурсов AKS. Дополнительные сведения см. в статье ["Почему создаются две группы ресурсов с помощью AKS?"][aks-two-resource-groups].

## Обновление существующего кластера AKS

Вы можете обновить кластер AKS, чтобы использовать издателя OIDC и включить удостоверение рабочей нагрузки, вызвав [команду az aks update][az aks update] с `--enable-oidc-issuer` параметрами `--enable-workload-identity` . В следующем примере обновляется существующий кластер:

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity
```

## Получение URL-адреса издателя OIDC

Чтобы получить URL-адрес издателя OIDC и сохранить его в переменной среды, выполните следующую команду:

```azurecli-interactive
export AKS_OIDC_ISSUER="$(az aks show --name "${CLUSTER_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --query "oidcIssuerProfile.issuerUrl" \
    --output tsv)"
```

Переменная среды должна содержать URL-адрес издателя, аналогичный следующему примеру:

```output
https://eastus.oic.prod-aks.azure.com/00000000-0000-0000-0000-000000000000/11111111-1111-1111-1111-111111111111/
```

По умолчанию издателю присваивается базовый URL-адрес `https://{region}.oic.prod-aks.azure.com/{tenant_id}/{uuid}`, где значение для `{region}` соответствия расположению, в котором развертывается кластер AKS. Значение `{uuid}` представляет ключ OIDC, который является случайным образом созданным guid для каждого кластера, который является неизменяемым.

## Создание управляемого удостоверения

[Вызовите команду az identity create][az-identity-create], чтобы создать управляемое удостоверение.

```azurecli-interactive
export SUBSCRIPTION="$(az account show --query id --output tsv)"
export USER_ASSIGNED_IDENTITY_NAME="myIdentity$RANDOM_ID"
az identity create \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --location "${LOCATION}" \
    --subscription "${SUBSCRIPTION}"
```

В следующем примере выходных данных показано успешное создание управляемого удостоверения:

Результаты.
<!-- expected_similarity=0.3 -->
```output
{
  "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourcegroups/myResourceGroupxxxxxx/providers/Microsoft.ManagedIdentity/userAssignedIdentities/myIdentityxxxxxx",
  "location": "centralindia",
  "name": "myIdentityxxxxxx",
  "principalId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "resourceGroup": "myResourceGroupxxxxxx",
  "systemData": null,
  "tags": {},
  "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "type": "Microsoft.ManagedIdentity/userAssignedIdentities"
}
```

Затем создайте переменную для идентификатора клиента управляемого удостоверения.

```azurecli-interactive
export USER_ASSIGNED_CLIENT_ID="$(az identity show \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --query 'clientId' \
    --output tsv)"
```

## Создание учетной записи службы Kubernetes

Создайте учетную запись службы Kubernetes и заметите ее с идентификатором клиента управляемого удостоверения, созданного на предыдущем шаге. [Используйте команду az aks get-credentials][az-aks-get-credentials] и замените значения для имени кластера и имени группы ресурсов.

```azurecli-interactive
az aks get-credentials --name "${CLUSTER_NAME}" --resource-group "${RESOURCE_GROUP}"
```

Скопируйте и вставьте следующие многострочный ввод в Azure CLI.

```azurecli-interactive
export SERVICE_ACCOUNT_NAMESPACE="default"
export SERVICE_ACCOUNT_NAME="workload-identity-sa$RANDOM_ID"
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  annotations:
    azure.workload.identity/client-id: "${USER_ASSIGNED_CLIENT_ID}"
  name: "${SERVICE_ACCOUNT_NAME}"
  namespace: "${SERVICE_ACCOUNT_NAMESPACE}"
EOF
```

В следующих выходных данных показано успешное создание удостоверения рабочей нагрузки:

```output
serviceaccount/workload-identity-sa created
```

## Создание учетных данных федеративного удостоверения

[Вызовите команду az identity federated-credential create][az-identity-federated-credential-create], чтобы создать федеративные учетные данные удостоверения между управляемым удостоверением, издателем учетной записи службы и субъектом. Дополнительные сведения об учетных данных федеративных удостоверений в Microsoft Entra см. в разделе ["Обзор федеративных учетных данных удостоверений" в идентификаторе Microsoft Entra.][federated-identity-credential]

```azurecli-interactive
export FEDERATED_IDENTITY_CREDENTIAL_NAME="myFedIdentity$RANDOM_ID"
az identity federated-credential create \
    --name ${FEDERATED_IDENTITY_CREDENTIAL_NAME} \
    --identity-name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --issuer "${AKS_OIDC_ISSUER}" \
    --subject system:serviceaccount:"${SERVICE_ACCOUNT_NAMESPACE}":"${SERVICE_ACCOUNT_NAME}" \
    --audience api://AzureADTokenExchange
```

> [!NOTE]
> После добавления учетных данных федеративного удостоверения потребуется несколько секунд. Если запрос маркера выполняется сразу после добавления учетных данных федеративного удостоверения, запрос может завершиться ошибкой до обновления кэша. Чтобы избежать этой проблемы, можно добавить небольшую задержку после добавления учетных данных федеративного удостоверения.

## Развертывание приложения

При развертывании модулей pod приложения манифест должен ссылаться на учетную запись службы, созданную на шаге **создания учетной записи** службы Kubernetes. В следующем манифесте показано, как ссылаться на учетную запись, в частности _метаданные\пространство_ имен и _свойства spec\serviceAccountName_ . Обязательно укажите изображение и `<image>` имя контейнера для `<containerName>`:

```bash
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: sample-workload-identity
  namespace: ${SERVICE_ACCOUNT_NAMESPACE}  # Replace with your namespace
  labels:
    azure.workload.identity/use: "true"  # Required. Only pods with this label can use workload identity.
spec:
  serviceAccountName: ${SERVICE_ACCOUNT_NAME}  # Replace with your service account name
  containers:
    - name: rabbitmq  # Replace with your container name
      image: mcr.microsoft.com/mirror/docker/library/rabbitmq:3.10-management-alpine  # Replace with your Docker image
      ports:
        - containerPort: 5672
          name: rabbitmq-amqp
        - containerPort: 15672
          name: rabbitmq-http
      env:
        - name: RABBITMQ_DEFAULT_USER
          value: "username"
        - name: RABBITMQ_DEFAULT_PASS
          value: "password"
      resources:
        requests:
          cpu: 10m
          memory: 128Mi
        limits:
          cpu: 250m
          memory: 256Mi
EOF
```

> [!IMPORTANT]
> Убедитесь, что модули pod приложения, использующие удостоверение рабочей нагрузки, включают метку `azure.workload.identity/use: "true"` в спецификацию pod. В противном случае модули pod завершаются сбоем после перезапуска.

## Предоставление разрешений для доступа к Azure Key Vault

Инструкции на этом шаге показано, как получить доступ к секретам, ключам или сертификатам в хранилище ключей Azure из модуля pod. Примеры в этом разделе позволяют настроить доступ к секретам в хранилище ключей для удостоверения рабочей нагрузки, но можно выполнить аналогичные действия, чтобы настроить доступ к ключам или сертификатам.

В следующем примере показано, как использовать модель управления доступом на основе ролей Azure (Azure RBAC) для предоставления pod-доступа к хранилищу ключей. Дополнительные сведения о модели разрешений Azure RBAC для Azure Key Vault см. в статье [Предоставление разрешений приложениям для доступа к хранилищу ключей Azure с помощью Azure RBAC](/azure/key-vault/general/rbac-guide).

1. Создайте хранилище ключей с включенной защитой очистки и авторизацией RBAC. Вы также можете использовать существующее хранилище ключей, если оно настроено для защиты от очистки и RBAC авторизации:

    ```azurecli-interactive
    export KEYVAULT_NAME="keyvault-workload-id$RANDOM_ID"
    # Ensure the key vault name is between 3-24 characters
    if [ ${#KEYVAULT_NAME} -gt 24 ]; then
        KEYVAULT_NAME="${KEYVAULT_NAME:0:24}"
    fi
    az keyvault create \
        --name "${KEYVAULT_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --location "${LOCATION}" \
        --enable-purge-protection \
        --enable-rbac-authorization 
    ```

1. Назначьте себе роль офицера[ секретов RBAC ](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-officer)Key Vault, чтобы создать секрет в новом хранилище ключей:

    ```azurecli-interactive
    export KEYVAULT_RESOURCE_ID=$(az keyvault show --resource-group "${KEYVAULT_RESOURCE_GROUP}" \
        --name "${KEYVAULT_NAME}" \
        --query id \
        --output tsv)

    export CALLER_OBJECT_ID=$(az ad signed-in-user show --query objectId -o tsv)

    az role assignment create --assignee "${CALLER_OBJECT_ID}" \
    --role "Key Vault Secrets Officer" \
    --scope "${KEYVAULT_RESOURCE_ID}"
    ```

1. Создайте секрет в хранилище ключей:

    ```azurecli-interactive
    export KEYVAULT_SECRET_NAME="my-secret$RANDOM_ID"
    az keyvault secret set \
        --vault-name "${KEYVAULT_NAME}" \
        --name "${KEYVAULT_SECRET_NAME}" \
        --value "Hello\!"
    ```

1. [Назначьте роль пользователя](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-user) секретов Key Vault управляемому удостоверению, созданному ранее. На этом шаге предоставляется разрешение на чтение секретов из хранилища ключей:

    ```azurecli-interactive
    export IDENTITY_PRINCIPAL_ID=$(az identity show \
        --name "${USER_ASSIGNED_IDENTITY_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --query principalId \
        --output tsv)
    
    az role assignment create \
        --assignee-object-id "${IDENTITY_PRINCIPAL_ID}" \
        --role "Key Vault Secrets User" \
        --scope "${KEYVAULT_RESOURCE_ID}" \
        --assignee-principal-type ServicePrincipal
    ```

1. Создайте переменную среды для URL-адреса хранилища ключей:

    ```azurecli-interactive
    export KEYVAULT_URL="$(az keyvault show \
        --resource-group ${RESOURCE_GROUP} \
        --name ${KEYVAULT_NAME} \
        --query properties.vaultUri \
        --output tsv)"
    ```

1. Разверните pod, ссылающийся на учетную запись службы и URL-адрес хранилища ключей:

    ```bash
    cat <<EOF | kubectl apply -f -
    apiVersion: v1
    kind: Pod
    metadata:
    name: sample-workload-identity-key-vault
    namespace: ${SERVICE_ACCOUNT_NAMESPACE}
    labels:
        azure.workload.identity/use: "true"
    spec:
    serviceAccountName: ${SERVICE_ACCOUNT_NAME}
    containers:
        - image: ghcr.io/azure/azure-workload-identity/msal-go
        name: oidc
        env:
            - name: KEYVAULT_URL
            value: ${KEYVAULT_URL}
            - name: SECRET_NAME
            value: ${KEYVAULT_SECRET_NAME}
    nodeSelector:
        kubernetes.io/os: linux
    EOF
    ```

Чтобы проверить правильность внедрения всех свойств веб-перехватчиком, используйте [команду kubectl описать][kubectl-describe] :

```azurecli-interactive
kubectl describe pod sample-workload-identity-key-vault | grep "SECRET_NAME:"
```

При успешном выполнении выходные данные должны быть похожи на следующие:

```output
      SECRET_NAME:                 ${KEYVAULT_SECRET_NAME}
```

Чтобы убедиться, что модуль pod может получить маркер и получить доступ к ресурсу, используйте команду kubectl logs:

```azurecli-interactive
kubectl logs sample-workload-identity-key-vault
```

При успешном выполнении выходные данные должны быть похожи на следующие:

```output
I0114 10:35:09.795900       1 main.go:63] "successfully got secret" secret="Hello\\!"
```

> [!IMPORTANT]
> Назначения ролей RBAC Azure могут занять до десяти минут. Если модуль pod не может получить доступ к секрету, может потребоваться дождаться распространения назначения роли. Дополнительные сведения см. в статье об [устранении неполадок службы Azure RBAC](/azure/role-based-access-control/troubleshooting#).

## Отключение удостоверения рабочей нагрузки

Чтобы отключить Идентификация рабочей нагрузки Microsoft Entra в кластере AKS, где он был включен и настроен, можно выполнить следующую команду:

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --disable-workload-identity
```

## Следующие шаги

В этой статье вы развернули кластер Kubernetes и настроили его для использования удостоверения рабочей нагрузки для подготовки рабочих нагрузок приложений для проверки подлинности с помощью этих учетных данных. Теперь вы готовы развернуть приложение и настроить его для использования удостоверения рабочей нагрузки с последней версией клиентской [библиотеки удостоверений][azure-identity-libraries] Azure. Если вы не можете перезаписать приложение для использования последней версии клиентской библиотеки, вы можете [настроить модуль pod][workload-identity-migration] приложения для проверки подлинности с помощью управляемого удостоверения с удостоверением рабочей нагрузки в качестве краткосрочного решения миграции.

Интеграция [соединителя](/azure/service-connector/overview) служб помогает упростить конфигурацию подключения для рабочих нагрузок AKS и служб резервного копирования Azure. Он безопасно обрабатывает проверку подлинности и конфигурации сети и следует рекомендациям по подключению к службам Azure. Дополнительные сведения см. в статье ["Подключение к службе Azure OpenAI" в AKS с помощью удостоверений](/azure/service-connector/tutorial-python-aks-openai-workload-identity) рабочей нагрузки и [введение](https://azure.github.io/AKS/2024/05/23/service-connector-intro) в соединитель служб.

<!-- EXTERNAL LINKS -->
[kubectl-describe]: https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#describe

<!-- INTERNAL LINKS -->
[kubernetes-concepts]: concepts-clusters-workloads.md
[workload-identity-overview]: workload-identity-overview.md
[azure-resource-group]: /azure/azure-resource-manager/management/overview
[az-group-create]: /cli/azure/group#az-group-create
[aks-identity-concepts]: concepts-identity.md
[federated-identity-credential]: /graph/api/resources/federatedidentitycredentials-overview
[tutorial-python-aks-storage-workload-identity]: /azure/service-connector/tutorial-python-aks-storage-workload-identity
[az-aks-create]: /cli/azure/aks#az-aks-create
[az aks update]: /cli/azure/aks#az-aks-update
[aks-two-resource-groups]: faq.yml
[az-account-set]: /cli/azure/account#az-account-set
[az-identity-create]: /cli/azure/identity#az-identity-create
[az-aks-get-credentials]: /cli/azure/aks#az-aks-get-credentials
[az-identity-federated-credential-create]: /cli/azure/identity/federated-credential#az-identity-federated-credential-create
[workload-identity-migration]: workload-identity-migrate-from-pod-identity.md
[azure-identity-libraries]: /azure/active-directory/develop/reference-v2-libraries