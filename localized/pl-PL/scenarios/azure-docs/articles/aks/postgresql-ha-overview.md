---
title: Omówienie wdrażania bazy danych PostgreSQL o wysokiej dostępności w usłudze AKS przy użyciu interfejsu wiersza polecenia platformy Azure
description: 'Dowiedz się, jak wdrożyć bazę danych PostgreSQL o wysokiej dostępności w usłudze AKS przy użyciu operatora CloudNativePG.'
ms.topic: overview
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---
# Wdrażanie bazy danych PostgreSQL o wysokiej dostępności w usłudze AKS przy użyciu interfejsu wiersza polecenia platformy Azure

W tym przewodniku wdrożysz klaster PostgreSQL o wysokiej dostępności obejmujący wiele stref dostępności platformy Azure w usłudze AKS za pomocą interfejsu wiersza polecenia platformy Azure.

W tym artykule przedstawiono wymagania wstępne dotyczące konfigurowania klastra PostgreSQL w [usłudze Azure Kubernetes Service (AKS)][what-is-aks] oraz omówienie pełnego procesu wdrażania i architektury.

## Wymagania wstępne

* W tym przewodniku założono, że podstawowa wiedza na temat podstawowych pojęć związanych z [platformą][core-kubernetes-concepts] Kubernetes i [bazy danych PostgreSQL][postgresql].
* **Potrzebujesz wbudowanych ról[ właściciela** lub **administratora** dostępu użytkowników i **współautora** ][azure-roles]platformy Azure w subskrypcji na koncie platformy Azure.

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

* Potrzebne są również następujące zasoby:

  * [Interfejs wiersza polecenia](/cli/azure/install-azure-cli) platformy Azure w wersji 2.56 lub nowszej.
  * [Rozszerzenie][aks-preview] usługi Azure Kubernetes Service (AKS) w wersji zapoznawczej.
  * [jq][jq], wersja 1.5 lub nowsza.
  * [kubectl][install-kubectl] w wersji 1.21.0 lub nowszej.
  * [Program Helm][install-helm] w wersji 3.0.0 lub nowszej.
  * [openssl][install-openssl] w wersji 3.3.0 lub nowszej.
  * [Program Visual Studio Code][install-vscode] lub odpowiednik.
  * [Krew][install-krew] w wersji 0.4.4 lub nowszej.
  * [wtyczka kubectl CloudNativePG (CNPG).][cnpg-plugin]

## Proces wdrażania

Niniejszy przewodnik zawiera informacje na temat wykonywania następujących czynności:

* Użyj interfejsu wiersza polecenia platformy Azure, aby utworzyć klaster usługi AKS z wieloma strefami.
* Wdróż klaster i bazę danych PostgreSQL o wysokiej dostępności przy użyciu [operatora][cnpg-plugin] CNPG.
* Konfigurowanie monitorowania bazy danych PostgreSQL przy użyciu rozwiązań Prometheus i Grafana.
* Wdrażanie przykładowego zestawu danych w bazie danych PostgreSQL.
* Wykonaj uaktualnienia klastrów PostgreSQL i AKS.
* Symulowanie przerw w działaniu klastra i trybu failover repliki PostgreSQL.
* Wykonaj kopię zapasową i przywracanie bazy danych PostgreSQL.

## Architektura wdrażania

Ten diagram przedstawia konfigurację klastra PostgreSQL z jedną repliką podstawową i dwie repliki do odczytu zarządzane przez [operator CloudNativePG (CNPG).](https://cloudnative-pg.io/) Architektura zapewnia wysoce dostępną usługę PostgreSQL działającą w klastrze usługi AKS, która może wytrzymać awarię strefy przez przełączenie w tryb failover między replikami.

Kopie zapasowe są przechowywane w [usłudze Azure Blob Storage](/azure/storage/blobs/), zapewniając inny sposób przywracania bazy danych w przypadku problemu z replikacją strumieniową z repliki podstawowej.

:::image source="./media/postgresql-ha-overview/architecture-diagram.png" alt-text="Diagram architektury CNPG." lightbox="./media/postgresql-ha-overview/architecture-diagram.png":::

> [!NOTE]
> Operator CNPG obsługuje tylko *jedną bazę danych na klaster*. Zaplanuj odpowiednio dla aplikacji, które wymagają separacji danych na poziomie bazy danych.

## Następne kroki

> [!div class="nextstepaction"]
> [Tworzenie infrastruktury w celu wdrożenia bazy danych PostgreSQL o wysokiej dostępności w usłudze AKS przy użyciu operatora CNPG][create-infrastructure]

## Współautorzy

*Ten artykuł jest obsługiwany przez firmę Microsoft. Pierwotnie został napisany przez następujących współautorów*:

* Ken Kilty | Moduł TPM podmiotu zabezpieczeń
* Russell de Pina | Moduł TPM podmiotu zabezpieczeń
* Adrian Joian | Starszy inżynier klienta
* Jenny Hayes | Starszy deweloper zawartości
* Carol Smith | Starszy deweloper zawartości
* Erin Schaffer | Content Developer 2
* Adam Sharif | Inżynier klienta 2

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
