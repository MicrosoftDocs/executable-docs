---
title: 使用 Azure CLI 在 AKS 上部署高可用性 PostgreSQL 数据库的概述
description: 了解如何通过 Azure CLI 使用 CloudNativePG 运算符在 AKS 上部署高度可用的 PostgreSQL 数据库。
ms.topic: overview
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---
# 使用 Azure CLI 在 AKS 上部署高可用性 PostgreSQL 数据库

在本指南中，你将使用 Azure CLI 在 AKS 上部署跨多个 Azure 可用区的高可用性 PostgreSQL 群集。

本文逐步介绍了在 [Azure Kubernetes 服务 (AKS)][what-is-aks] 上设置 PostgreSQL 群集的先决条件，并概述了完整的部署过程和体系结构。

## 先决条件

* 本指南假设读者基本了解[核心 Kubernetes 概念][core-kubernetes-concepts]以及 [PostgreSQL][postgresql]。
* 你需要 Azure 帐户中的订阅上的“所有者”**** 或“用户访问管理员”**** 和****“参与者”[Azure 内置角色][azure-roles]。

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

* 还需要安装以下资源：

  * [Azure CLI](/cli/azure/install-azure-cli) 版本 2.56 或更高版本。
  * [Azure Kubernetes 服务 (AKS) 预览版扩展][aks-preview]。
  * [jq][jq] 1.5 或更高版本。
  * [kubectl][install-kubectl] 1.21.0 或更高版本。
  * [Helm][install-helm] 3.0.0 或更高版本。
  * [openssl][install-openssl] 3.3.0 或更高版本。
  * [Visual Studio Code][install-vscode] 或等效项。
  * [Krew][install-krew] 0.4.4 或更高版本。
  * [kubectl CloudNativePG (CNPG) 插件][cnpg-plugin]。

## 部署过程

本指南介绍如何：

* 使用 Azure CLI 创建多区域 AKS 群集。
* 使用 [CNPG operator][cnpg-plugin] 部署高可用性 PostgreSQL 群集和数据库。
* 设置使用 Prometheus 和 Grafana 监视 PostgreSQL。
* 将示例数据集部署到 PostgreSQL 数据库。
* 执行 PostgreSQL 和 AKS 群集升级。
* 模拟群集中断和 PostgreSQL 副本故障转移。
* 执行 PostgreSQL 数据库的备份和还原。

## 部署体系结构

此图演示了一个 PostgreSQL 群集设置，其中一个主要副本和两个只读副本由 [CloudNativePG (CNPG)](https://cloudnative-pg.io/) operator 管理。 该体系结构提供在 AKS 群集上运行的高可用性 PostgreSQL，此群集可通过跨副本进行故障转移来承受区域中断。

备份存储在 [Azure Blob 存储](/azure/storage/blobs/)上，这提供了另一种在主副本的流式复制出现问题时恢复数据库的方法。

:::image source="./media/postgresql-ha-overview/architecture-diagram.png" alt-text="CNPG 体系结构示意图。" lightbox="./media/postgresql-ha-overview/architecture-diagram.png":::

> [!NOTE]
> CNPG operator 仅支持*每个群集一个数据库*。 针对需要在数据库级别进行数据分离的应用程序进行相应规划。

## 后续步骤

> [!div class="nextstepaction"]
> [创建基础架构以使用 CNPG operator 在 AKS 上部署高可用性 PostgreSQL 数据库][create-infrastructure]

## 作者

*本文由Microsoft维护。它最初由以下参与者*编写：

* Ken Kilty | 首席 TPM
* Russell de Pina | 首席 TPM
* Adrian Joian | 高级客户工程师
* Jenny Hayes | 高级内容开发人员
* Carol Smith | 高级内容开发人员
* Erin Schaffer | 内容开发人员 2
* Adam Sharif | 客户工程师 2

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
