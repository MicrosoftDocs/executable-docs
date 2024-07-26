---
title: Обзор развертывания высокодоступной базы данных PostgreSQL в AKS с помощью Azure CLI
description: 'Узнайте, как развернуть высокодоступную базу данных PostgreSQL в AKS с помощью оператора CloudNativePG!!'
ms.topic: overview
ms.date: 07/24/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---
# Развертывание высокодоступной базы данных PostgreSQL в AKS с помощью Azure CLI

В этом руководстве вы развернете высокодоступный кластер PostgreSQL, охватывающий несколько зон доступности Azure в AKS с помощью Azure CLI!

В этой статье описаны предварительные требования для настройки кластера PostgreSQL на [Служба Azure Kubernetes (AKS)][what-is-aks] и обзор полного процесса развертывания и архитектуры.

## Необходимые компоненты

* В этом руководстве предполагается базовое понимание основных концепций [][core-kubernetes-concepts] Kubernetes и [PostgreSQL][postgresql].
* Вам потребуется **администратор** доступа владельца** или **пользователя и **встроенные роли[ Azure в** ][azure-roles]подписке в учетной записи Azure.

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

* Вам также потребуется установить следующие ресурсы:

  * [Azure CLI](/cli/azure/install-azure-cli) версии 2.56 или более поздней.
  * [расширение предварительной версии][aks-preview] Служба Azure Kubernetes (AKS).
  * [jq][jq], версия 1.5 или более поздняя.
  * [kubectl][install-kubectl] версии 1.21.0 или более поздней.
  * [Helm][install-helm] версии 3.0.0 или более поздней.
  * [opensl][install-openssl] версии 3.3.0 или более поздней.
  * [Visual Studio Code][install-vscode] или эквивалент.
  * [Крев][install-krew] версии 0.4.4 или более поздней.
  * [Подключаемый модуль][cnpg-plugin] kubectl CloudNativePG (CNPG).

## Процесс развертывания

Из этого руководства вы узнаете, как выполнить следующие задачи:

* Используйте Azure CLI для создания кластера AKS с несколькими зонами.
* Разверните высокодоступный кластер PostgreSQL и базу данных с помощью [оператора][cnpg-plugin] CNPG.
* Настройте мониторинг для PostgreSQL с помощью Prometheus и Grafana.
* Разверните пример набора данных в базе данных PostgreSQL.
* Выполните обновление кластера PostgreSQL и AKS.
* Имитация прерывания кластера и отработка отказа реплики PostgreSQL.
* Выполните резервное копирование и восстановление базы данных PostgreSQL.

## Архитектура развертывания

На этой схеме показана настройка кластера PostgreSQL с одной первичной репликой и двумя репликами чтения, управляемыми оператором [CloudNativePG (CNPG](https://cloudnative-pg.io/) ). Архитектура предоставляет высокодоступную postgreSQL, запущенную в кластере AKS, которая может выдержать сбой зоны путем отработки отказа между репликами.

Резервные копии хранятся в [Хранилище BLOB-объектов Azure](/azure/storage/blobs/), предоставляя другой способ восстановления базы данных в случае проблемы с репликацией потоковой передачи из первичной реплики.

:::image source="./media/postgresql-ha-overview/architecture-diagram.png" alt-text="Схема архитектуры CNPG." lightbox="./media/postgresql-ha-overview/architecture-diagram.png":::

> [!NOTE]
> Оператор CNPG поддерживает только *одну базу данных на* кластер. Планируйте соответствующим образом приложения, требующие разделения данных на уровне базы данных.

## Следующие шаги

> [!div class="nextstepaction"]
> [Создание инфраструктуры для развертывания высокодоступной базы данных PostgreSQL в AKS с помощью оператора CNPG][create-infrastructure]

## Соавторы

*Эта статья поддерживается корпорацией Майкрософт. Первоначально он был написан следующими участниками*:

* Кен Килти | Основной TPM
* Рассел де Пина | Основной TPM
* Адриан Джоан | Старший инженер клиента
* Дженни Хейс | Старший разработчик содержимого
* Кэрол Смит | Старший разработчик содержимого
* Эрин Шаффер | Разработчик содержимого 2
* Адам Шариф | Инженер клиента 2

<!-- LINKS -->
[what-is-aks]: ./what-is-aks.md
[postgresql]: https://www.postgresql.org/
[core-kubernetes-concepts]: ./concepts-clusters-workloads.md
[azure-roles]: ../role-based-access-control/built-in-roles.md
[aks-preview]: ./draft.md#install-the-aks-preview-azure-cli-extension
[jq]: https://jqlang.github.io/jq/
[install-kubectl]: https://kubernetes.io/docs/tasks/tools/install-kubectl/
[install-helm]: https://helm.sh/docs/intro/install/
[install-openssl]: https://www.openssl.org/
[install-vscode]: https://code.visualstudio.com/Download
[install-krew]: https://krew.sigs.k8s.io/
[cnpg-plugin]: https://cloudnative-pg.io/documentation/current/kubectl-plugin/#using-krew
[create-infrastructure]: ./create-postgresql-ha.md
