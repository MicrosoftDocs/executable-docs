---
title: 使用 Azure CLI 在 AKS 上部署高可用性 PostgreSQL 資料庫的概觀
description: 瞭解如何使用 CloudNativePG 運算符在 AKS 上部署高可用性 PostgreSQL 資料庫！！
ms.topic: overview
ms.date: 07/24/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---
# 使用 Azure CLI 在 AKS 上部署高可用性 PostgreSQL 資料庫

在本指南中，您會部署高可用性 PostgreSQL 叢集，此叢集橫跨 AKS 上的多個 Azure 可用性區域與 Azure CLI！

本文逐步解說在 [Azure Kubernetes Service (AKS)][what-is-aks] 上設定 PostgreSQL 叢集的必要條件，並提供完整部署程式和架構的概觀。

## 必要條件

* 本指南假設對於 [核心 Kubernetes 概念][core-kubernetes-concepts] 和 [PostgreSQL][postgresql] 有基本瞭解。
* 您需要 **擁有者** 或 **使用者存取系統管理員**，以及 Azure 帳戶中訂用帳戶的 **參與者** [Azure 內建角色][azure-roles]。

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

* 您也需要安裝下列資源：

  * [Azure CLI](/cli/azure/install-azure-cli) 2.56 版或更新版本。
  * [Azure Kubernetes Service (AKS) 預覽延伸模組][aks-preview]。
  * [jq][jq]1.5 版或更新版本。
  * [kubectl][install-kubectl] 1.21.0 版或更新版本。
  * [Helm][install-helm] 3.0.0 版或更新版本
  * [openssl][install-openssl] 3.3.0 版或更新版本。
  * [Visual Studio Code][install-vscode] 或對等工具。
  * [Krew][install-krew] 0.4.4 版或更新版本。
  * [kubectl CloudNativePG (CNPG) 外掛程式][cnpg-plugin]。

## 部署程序

在本指南中，您將了解如何：

* 使用 Azure CLI 建立多區域 AKS 叢集。
* 使用 [CNPG 運算子][cnpg-plugin] 部署高可用性 PostgreSQL 叢集和資料庫。
* 使用 Prometheus 和 Grafana 設定 PostgreSQL 的監視。
* 將範例資料集部署至 PostgreSQL 資料庫。
* 執行 PostgreSQL 和 AKS 叢集升級。
* 模擬叢集中斷和 PostgreSQL 複本容錯移轉。
* 執行 PostgreSQL 資料庫的備份和還原。

## 部署架構

此圖說明 PostgreSQL 叢集設定，其中一個主要複本和兩個讀取複本是由 [CloudNativePG (CNPG)](https://cloudnative-pg.io/) 運算子所管理。 此架構提供在 AKS 叢集上執行的高可用性 PostgreSQL，可透過跨複本故障轉移來承受區域中斷。

備份會儲存在 [Azure Blob 儲存體](/azure/storage/blobs/) 上，提供當主要複本發生串流複寫問題時，另一種還原資料庫的方式。

:::image source="./media/postgresql-ha-overview/architecture-diagram.png" alt-text="CNPG 架構的圖表。" lightbox="./media/postgresql-ha-overview/architecture-diagram.png":::

> [!NOTE]
> CNPG 運算子僅支援每個叢集 *一個資料庫*。 針對需要資料庫層級資料區隔的應用程式進行相應規劃。

## 下一步

> [!div class="nextstepaction"]
> [使用 CNPG 運算子在 AKS 上建立高可用性 PostgreSQL 資料庫部署基礎結構][create-infrastructure]

## 參與者

*本文由 Microsoft 維護。它最初是由下列參與者*所撰寫：

* Ken Kilty | 首席 TPM
* Russell de Pina | 首席 TPM
* Adrian Joian |資深客戶工程師
* Jenny Hayes | 資深內容開發人員
* Carol Smith | 資深內容開發人員
* Erin Schaffer |內容開發人員 2
* Adam Sharif |客戶工程師 2

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
