---
title: Azure CLI を使用して高可用性 PostgreSQL データベースを AKS にデプロイする方法の概要
description: Azure CLI で CloudNativePG オペレーターを使用して、AKS に高可用性 PostgreSQL データベースをデプロイする方法について説明します。
ms.topic: overview
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---
# Azure CLI を使用して高可用性 PostgreSQL データベースを AKS にデプロイする

このガイドでは、Azure CLI を使用して複数の Azure 可用性ゾーンにまたがる高可用性 PostgreSQL クラスターを AKS 上にデプロイします。

この記事では、PostgreSQL クラスターを [Azure Kubernetes Service (AKS)][what-is-aks] 上で設定するための前提条件を示すとともに、デプロイ プロセス全体とアーキテクチャの概要を説明します。

## 前提条件

* このクイックスタートは、[Kubernetes の中核的な概念][core-kubernetes-concepts]と [PostgreSQL][postgresql] の基礎を理解していることを前提としています。
* Azure アカウント内のサブスクリプションに対する**所有者**または**ユーザー アクセス管理者**と**共同作成者**の [Azure 組み込みロール][azure-roles]が必要です。

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

* 次のリソースもインストールされている必要があります。

  * [Azure CLI](/cli/azure/install-azure-cli) バージョン 2.56 以降。
  * [Azure Kubernetes Service (AKS) プレビュー拡張機能][aks-preview]。
  * [jq][jq] バージョン 1.5 以降。
  * [kubectl][install-kubectl] バージョン 1.21.0 以降。
  * [Helm][install-helm] バージョン 3.0.0 以降。
  * [openssl][install-openssl] バージョン 3.3.0 以降。
  * [Visual Studio Code][install-vscode] または同等の機能。
  * [Krew][install-krew] バージョン 0.4.4 以降。
  * [kubectl CloudNativePG (CNPG) プラグイン][cnpg-plugin]。

## デプロイ プロセス

このガイドでは、以下の方法について説明します。

* Azure CLI を使用してマルチゾーン AKS クラスターを作成する。
* [CNPG オペレーター][cnpg-plugin]を使用して高可用性 PostgreSQL クラスターとデータベースをデプロイする。
* Prometheus と Grafana を使用して PostgreSQL の監視を設定する。
* サンプル データセットを PostgreSQL データベースにデプロイする。
* PostgreSQL と AKS クラスターのアップグレードを実行する。
* クラスターの中断と PostgreSQL レプリカのフェールオーバーをシミュレートする。
* PostgreSQL データベースのバックアップと復元を実行する。

## デプロイ アーキテクチャ

この図は、ある PostgreSQL クラスターのセットアップを示しています。1 つのプライマリ レプリカと 2 つの読み取りレプリカがあり、これらは [CloudNativePG (CNPG)](https://cloudnative-pg.io/) オペレーターによって管理されます。 このアーキテクチャによって、AKS クラスター上で実行される高可用性 PostgreSQL が実現し、ゾーンの 1 つが停止してもレプリカ間でフェールオーバーすることによって稼働を継続できます。

バックアップは [Azure Blob Storage](/azure/storage/blobs/) に格納されるため、プライマリ レプリカからのストリーミング レプリケーションで問題が発生した場合にデータベースを復元する別の方法として利用できます。

:::image source="./media/postgresql-ha-overview/architecture-diagram.png" alt-text="CNPG アーキテクチャの図。" lightbox="./media/postgresql-ha-overview/architecture-diagram.png":::

> [!NOTE]
> CNPG オペレーターでサポートされるのは、1 クラスターにつき 1 つのデータベースのみです。** データベース レベルでデータの分離を必要とするアプリケーションについては、このことを考慮してください。

## 次のステップ

> [!div class="nextstepaction"]
> [CNPG オペレーターを使用して高可用性 PostgreSQL データベースを AKS にデプロイするためのインフラストラクチャを作成する][create-infrastructure]

## 共同作成者

*この記事は Microsoft によって管理されています。これはもともと次の共同作成者によって書かれました*:

* Ken Kilty | プリンシパル TPM
* Russell de Pina | プリンシパル TPM
* Adrian Joian | シニア カスタマー エンジニア
* Jenny Hayes | シニア コンテンツ開発者
* Carol Smith | シニア コンテンツ開発者
* Erin Schaffer |コンテンツ開発者 2
* Adam Sharif | カスタマー エンジニア 2

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
