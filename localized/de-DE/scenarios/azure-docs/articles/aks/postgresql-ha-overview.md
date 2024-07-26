---
title: Übersicht über die Bereitstellung einer hochverfügbaren PostgreSQL-Datenbank in AKS mithilfe der Azure CLI
description: 'Erfahren Sie, wie Sie eine hoch verfügbare PostgreSQL-Datenbank auf AKS mithilfe des CloudNativePG-Operators bereitstellen!!'
ms.topic: overview
ms.date: 07/24/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---
# Bereitstellen einer hochverfügbaren PostgreSQL-Datenbank in AKS mithilfe der Azure CLI

In diesem Leitfaden stellen Sie einen hochgradig verfügbaren PostgreSQL-Cluster bereit, der mehrere Azure-Verfügbarkeitszonen auf AKS mit Azure CLI umfasst!

In diesem Artikel werden die Voraussetzungen für das Einrichten eines PostgreSQL-Clusters in [Azure Kubernetes Service (AKS)][what-is-aks] erläutert. Zudem bietet er einen Überblick über den vollständigen Bereitstellungsprozess und die Architektur.

## Voraussetzungen

* In diesem Leitfaden wird ein grundlegendes Verständnis der [Kubernetes-Kernkonzepte][core-kubernetes-concepts] und [PostgreSQL][postgresql] vorausgesetzt.
* Sie benötigen die [integrierten Azure-Rollen][azure-roles] **Besitzer** oder **Benutzerzugriffsadministrator** und **Mitwirkender** für ein Abonnement in Ihrem Azure-Konto.

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

* Außerdem müssen die folgenden Ressourcen installiert sein:

  * [Azure-Befehlszeilenschnittstelle](/cli/azure/install-azure-cli) Version 2.56 oder höher
  * [AKS-Erweiterung (Azure Kubernetes Service) in der Vorschau][aks-preview]
  * [jq][jq], Version 1.5 oder höher
  * [kubectl][install-kubectl], Version 1.21.0 oder höher
  * [Helm][install-helm], Version 3.0.0 oder höher
  * [openssl][install-openssl], Version 3.3.0 oder höher
  * [Visual Studio Code][install-vscode] oder ein ähnliches Tool
  * [Krew][install-krew], Version 0.4.4 oder höher
  * [kubectl CloudNativePG-Plug-In (CNPG)][cnpg-plugin]

## Bereitstellungsprozess

In diesem Artikel lernen Sie Folgendes:

* Verwenden der Azure CLI zum Erstellen eines AKS-Clusters mit mehreren Zonen
* Bereitstellen eines hochverfügbaren PostgreSQL-Clusters und einer Datenbank mithilfe des [CNPG-Operators][cnpg-plugin]
* Einrichten der Überwachung für PostgreSQL mithilfe von Prometheus und Grafana
* Bereitstellen eines Beispieldatasets für eine PostgreSQL-Datenbank
* Durchführen von PostgreSQL- und AKS-Clusterupgrades
* Simulieren einer Clusterunterbrechung und eines PostgreSQL-Replikatfailovers
* Durchführen der Sicherung und Wiederherstellung einer PostgreSQL-Datenbank

## Bereitstellungsarchitektur

Dieses Diagramm veranschaulicht ein PostgreSQL-Clustersetup mit einem primären Replikat und zwei Lesereplikaten, die vom [CloudNativePG-Operator (CNPG)](https://cloudnative-pg.io/) verwaltet werden. Die Architektur bietet eine hochverfügbare PostgreSQL-Instanz, die auf einem AKS-Cluster ausgeführt wird, der einem Zonenausfall standhalten kann, indem ein replikatübergreifender Failover ausgeführt wird.

Sicherungen werden in [Azure Blob Storage](/azure/storage/blobs/) gespeichert und bieten eine weitere Möglichkeit, die Datenbank im Falle eines Problems mit der Streamingreplikation über das primäre Replikat wiederherzustellen.

:::image source="./media/postgresql-ha-overview/architecture-diagram.png" alt-text="Diagramm der CNPG-Architektur." lightbox="./media/postgresql-ha-overview/architecture-diagram.png":::

> [!NOTE]
> Der CNPG-Operator unterstützt nur *eine Datenbank pro Cluster*. Planen Sie entsprechend für Anwendungen, die eine Datentrennung auf Datenbankebene erfordern.

## Nächste Schritte

> [!div class="nextstepaction"]
> [Erstellen der Infrastruktur für die Bereitstellung einer hochverfügbaren PostgreSQL-Datenbank in AKS mithilfe des CNPG-Operators][create-infrastructure]

## Beitragende

*Dieser Artikel wird von Microsoft verwaltet. Sie wurde ursprünglich von den folgenden Mitwirkenden* verfasst:

* Ken Kilty | Principal TPM
* Russell de Pina | Principal TPM
* Adrian Joian | Senior Customer Engineer
* Jenny Hayes | Senior Content Developer
* Carol Smith | Senior Content Developer
* Erin Schaffer | Content Developer 2
* Adam Sharif | Customer Engineer 2

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
