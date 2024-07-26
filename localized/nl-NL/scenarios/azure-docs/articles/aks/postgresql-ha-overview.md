---
title: Overzicht van het implementeren van een maximaal beschikbare PostgreSQL-database op AKS met Azure CLI
description: Meer informatie over het implementeren van een maximaal beschikbare PostgreSQL-database op AKS met behulp van de CloudNativePG-operator!!
ms.topic: overview
ms.date: 07/24/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---
# Een maximaal beschikbare PostgreSQL-database implementeren in AKS met Azure CLI

In deze handleiding implementeert u een maximaal beschikbaar PostgreSQL-cluster dat meerdere Azure-beschikbaarheidszones omvat op AKS met Azure CLI!

In dit artikel worden de vereisten beschreven voor het instellen van een PostgreSQL-cluster in [Azure Kubernetes Service (AKS)][what-is-aks] en vindt u een overzicht van het volledige implementatieproces en de volledige architectuur.

## Vereisten

* In deze handleiding wordt ervan uitgegaan dat u basiskennis hebt van de basisconcepten[ van ][core-kubernetes-concepts]Kubernetes en [PostgreSQL][postgresql].
* U hebt de **eigenaar** of **beheerder van gebruikerstoegang** en de **ingebouwde rollen[ in Inzender** ][azure-roles]van Azure nodig voor een abonnement in uw Azure-account.

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

* U hebt ook de volgende resources geïnstalleerd:

  * [Azure CLI](/cli/azure/install-azure-cli) versie 2.56 of hoger.
  * [Preview-extensie][aks-preview] voor Azure Kubernetes Service (AKS).
  * [jq][jq], versie 1.5 of hoger.
  * [kubectl][install-kubectl] versie 1.21.0 of hoger.
  * [Helm-versie][install-helm] 3.0.0 of hoger.
  * [openssl][install-openssl] versie 3.3.0 of hoger.
  * [Visual Studio Code][install-vscode] of gelijkwaardig.
  * [Krew][install-krew] versie 0.4.4 of hoger.
  * [Invoegtoepassing][cnpg-plugin] kubectl CloudNativePG (CNPG).

## Implementatieproces

In deze handleiding leert u het volgende:

* Gebruik Azure CLI om een AKS-cluster met meerdere zones te maken.
* Implementeer een postgreSQL-cluster en -database met hoge beschikbaarheid met behulp van de [CNPG-operator][cnpg-plugin].
* Bewaking voor PostgreSQL instellen met Prometheus en Grafana.
* Een voorbeeldgegevensset implementeren in een PostgreSQL-database.
* PostgreSQL- en AKS-clusterupgrades uitvoeren.
* Simuleer een onderbreking van een cluster en een PostgreSQL-replicafailover.
* Back-up en herstel uitvoeren van een PostgreSQL-database.

## Implementatiearchitectuur

Dit diagram illustreert het instellen van een PostgreSQL-cluster met één primaire replica en twee leesreplica's die worden beheerd door de [OPERATOR CloudNativePG (CNPG).](https://cloudnative-pg.io/) De architectuur biedt een maximaal beschikbare PostgreSQL die wordt uitgevoerd op een AKS-cluster dat bestand is tegen een zonestoring door failover van replica's uit te voeren.

Back-ups worden opgeslagen in [Azure Blob Storage](/azure/storage/blobs/) en bieden een andere manier om de database te herstellen in het geval van een probleem met streamingreplicatie van de primaire replica.

:::image source="./media/postgresql-ha-overview/architecture-diagram.png" alt-text="Diagram van CNPG-architectuur." lightbox="./media/postgresql-ha-overview/architecture-diagram.png":::

> [!NOTE]
> De CNPG-operator ondersteunt slechts *één database per cluster*. Plan dienovereenkomstig voor toepassingen waarvoor gegevensscheiding op databaseniveau is vereist.

## Volgende stappen

> [!div class="nextstepaction"]
> [De infrastructuur maken voor het implementeren van een maximaal beschikbare PostgreSQL-database op AKS met behulp van de CNPG-operator][create-infrastructure]

## Medewerkers

*Dit artikel wordt onderhouden door Microsoft. Het is oorspronkelijk geschreven door de volgende inzenders*:

* Ken Kilty | Principal TPM
* Russell de Tina | Principal TPM
* Adrian Joian | Senior klanttechnicus
* Jenny Hayes | Senior Content Developer
* Carol Smith | Senior Content Developer
* Erin Schaffer | Inhoudsontwikkelaar 2
* Adam Sharif | Klanttechnicus 2

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
