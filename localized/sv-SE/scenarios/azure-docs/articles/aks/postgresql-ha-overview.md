---
title: Översikt över distribution av en PostgreSQL-databas med hög tillgänglighet på AKS med Azure CLI
description: Lär dig hur du distribuerar en PostgreSQL-databas med hög tillgänglighet på AKS med hjälp av CloudNativePG-operatorn!
ms.topic: overview
ms.date: 07/24/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---
# Distribuera en PostgreSQL-databas med hög tillgänglighet på AKS med Azure CLI

I den här guiden distribuerar du ett PostgreSQL-kluster med hög tillgänglighet som omfattar flera Azure-tillgänglighetszoner i AKS med Azure CLI!

Den här artikeln går igenom kraven för att konfigurera ett PostgreSQL-kluster i [Azure Kubernetes Service (AKS)][what-is-aks] och ger en översikt över den fullständiga distributionsprocessen och arkitekturen.

## Förutsättningar

* Den här guiden förutsätter en grundläggande förståelse av [grundläggande Kubernetes-begrepp][core-kubernetes-concepts] och [PostgreSQL][postgresql].
* Du behöver de **inbyggda rollerna[ Ägare** eller **Användaråtkomstadministratör** och **Deltagar-Azure** ][azure-roles]i en prenumeration i ditt Azure-konto.

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

* Du behöver också följande resurser installerade:

  * [Azure CLI](/cli/azure/install-azure-cli) version 2.56 eller senare.
  * [Förhandsversionstillägg för][aks-preview] Azure Kubernetes Service (AKS).
  * [jq][jq], version 1.5 eller senare.
  * [kubectl][install-kubectl] version 1.21.0 eller senare.
  * [Helm][install-helm] version 3.0.0 eller senare.
  * [öppnar version][install-openssl] 3.3.0 eller senare.
  * [Visual Studio Code][install-vscode] eller motsvarande.
  * [Krew][install-krew] version 0.4.4 eller senare.
  * [kubectl CloudNativePG(CNPG)-plugin-program][cnpg-plugin].

## Distributionsprocess

I den här guiden får du lära du dig att:

* Använd Azure CLI för att skapa ett AKS-kluster med flera zoner.
* Distribuera ett PostgreSQL-kluster och en databas med hög tillgänglighet med hjälp av [CNPG-operatorn][cnpg-plugin].
* Konfigurera övervakning för PostgreSQL med Prometheus och Grafana.
* Distribuera en exempeldatauppsättning till en PostgreSQL-databas.
* Utför uppgraderingar av PostgreSQL- och AKS-kluster.
* Simulera ett klusteravbrott och PostgreSQL-replikredundans.
* Utför säkerhetskopiering och återställning av en PostgreSQL-databas.

## Distributionsarkitektur

Det här diagrammet illustrerar en PostgreSQL-klusterkonfiguration med en primär replik och två läsrepliker som hanteras av Operatorn [CloudNativePG (CNPG).](https://cloudnative-pg.io/) Arkitekturen ger en PostgreSQL med hög tillgänglighet som körs på ett AKS-kluster som kan motstå ett zonavbrott genom att växla över över repliker.

Säkerhetskopior lagras i [Azure Blob Storage](/azure/storage/blobs/), vilket ger ett annat sätt att återställa databasen i händelse av ett problem med strömmande replikering från den primära repliken.

:::image source="./media/postgresql-ha-overview/architecture-diagram.png" alt-text="Diagram över CNPG-arkitektur." lightbox="./media/postgresql-ha-overview/architecture-diagram.png":::

> [!NOTE]
> CNPG-operatorn stöder endast *en databas per kluster*. Planera därefter för program som kräver dataavgränsning på databasnivå.

## Nästa steg

> [!div class="nextstepaction"]
> [Skapa infrastrukturen för att distribuera en PostgreSQL-databas med hög tillgänglighet på AKS med hjälp av CNPG-operatorn][create-infrastructure]

## Deltagare

*Den här artikeln underhålls av Microsoft. Den skrevs ursprungligen av följande deltagare*:

* Ken Kilty | Huvudnamn för TPM
* Russell de Pina | Huvudnamn för TPM
* Adrian Joian | Senior kundtekniker
* Jenny Hayes | Senior innehållsutvecklare
* Carol Smith | Senior innehållsutvecklare
* Erin Schaffer | Innehållsutvecklare 2
* Adam Sharif | Kundtekniker 2

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
