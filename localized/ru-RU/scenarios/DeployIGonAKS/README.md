---
title: Развертывание Inspektor Gadget в кластере Служба Azure Kubernetes
description: 'В этом руководстве показано, как развернуть Inspektor Gadget в кластере AKS'
author: josebl
ms.author: josebl
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Краткое руководство. Развертывание гаджета Inspektor в кластере Служба Azure Kubernetes

[![Развертывание в Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262844)

Добро пожаловать в это руководство, где мы пошаговые инструкции по развертыванию [Inspektor Gadget](https://www.inspektor-gadget.io/) в кластере Служба Azure Kubernetes (AKS) с подключаемым модулем kubectl: `gadget` В этом руководстве предполагается, что вы уже вошли в Azure CLI и выбрали подписку для использования с интерфейсом командной строки.

## Определение переменных среды

Первым шагом в этом руководстве является определение переменных среды:

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myResourceGroup$RANDOM_ID"
export REGION="eastus"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
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
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myResourceGroup210",
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

## Создание кластера AKS

Теперь создайте кластер AKS с помощью команды az aks create.

Это займет несколько минут.

```bash
az aks create \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --name $MY_AKS_CLUSTER_NAME \
  --location $REGION \
  --no-ssh-key
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

## Установка гаджета Inspektor

Установка Inspektor Gadget состоит из двух шагов:

1. Установка подключаемого модуля kubectl в системе пользователя.
2. Установка Inspektor Gadget в кластере.

    > [!NOTE]
    > Существуют дополнительные механизмы для развертывания и использования Inspektor Gadget, которые зависят от конкретных вариантов использования и требований. Использование подключаемого `kubectl gadget` модуля охватывает многие из них, но не все. Например, развертывание Inspektor Gadget с `kubectl gadget` подключаемым модулем зависит от доступности сервера API Kubernetes. Поэтому, если вы не можете зависеть от такого компонента, так как его доступность иногда может быть скомпрометирована, рекомендуется не использовать `kubectl gadget`механизм развертывания. Проверка [документацию](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/ig.md) по ig, чтобы узнать, что делать в этом случае, и другие варианты использования.

### Установка подключаемого модуля kubectl: `gadget`

Установите последнюю версию подключаемого модуля kubectl на странице выпусков, распакуйте и переместите исполняемый файл `$HOME/.local/bin`в`kubectl-gadget`:

> [!NOTE]
> Если вы хотите установить его с помощью [`krew`](https://sigs.k8s.io/krew) или скомпилировать его из источника, следуйте официальной документации: [установка гаджета](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-kubectl-gadget) kubectl.

```bash
IG_VERSION=$(curl -s https://api.github.com/repos/inspektor-gadget/inspektor-gadget/releases/latest | jq -r .tag_name)
IG_ARCH=amd64
mkdir -p $HOME/.local/bin
export PATH=$PATH:$HOME/.local/bin
curl -sL https://github.com/inspektor-gadget/inspektor-gadget/releases/download/${IG_VERSION}/kubectl-gadget-linux-${IG_ARCH}-${IG_VERSION}.tar.gz  | tar -C $HOME/.local/bin -xzf - kubectl-gadget
```

Теперь давайте проверим установку `version` , выполнив команду:

```bash
kubectl gadget version
```

Команда `version` отобразит версию клиента (подключаемый модуль kubectl гаджета) и покажет, что он еще не установлен на сервере (кластер):

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: not installed$"-->
```text
Client version: vX.Y.Z
Server version: not installed
```

### Установка Inspektor Gadget в кластере

Следующая команда развернет DaemonSet:

> [!NOTE]
> Для настройки развертывания доступны несколько вариантов: используйте определенный образ контейнера, развернитесь на определенных узлах и многие другие. Чтобы узнать все из них, проверка официальную документацию: [установку в кластере](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-in-the-cluster).

```bash
kubectl gadget deploy
```

Теперь давайте проверим установку `version` , выполнив команду еще раз:

```bash
kubectl gadget version
```

На этот раз клиент и сервер будут правильно установлены:

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: v\d+\.\d+\.\d+$"-->
```text
Client version: vX.Y.Z
Server version: vX.Y.Z
```

Теперь вы можете запустить гаджеты:

```bash
kubectl gadget help
```

<!--
## Clean Up

### Undeploy Inspektor Gadget

```bash
kubectl gadget undeploy
```

### Clean up Azure resources

When no longer needed, you can use `az group delete` to remove the resource group, cluster, and all related resources as follows. The `--no-wait` parameter returns control to the prompt without waiting for the operation to complete. The `--yes` parameter confirms that you wish to delete the resources without an additional prompt to do so.

```bash
az group delete --name $MY_RESOURCE_GROUP_NAME --no-wait --yes
```
-->

## Next Steps
- [Реальные сценарии, в которых inspektor Gadget может помочь вам](https://go.microsoft.com/fwlink/p/?linkid=2260402#use-cases)
- [Изучение доступных гаджетов](https://go.microsoft.com/fwlink/p/?linkid=2260070)
- [Запуск собственной программы eBPF](https://go.microsoft.com/fwlink/p/?linkid=2259865)
