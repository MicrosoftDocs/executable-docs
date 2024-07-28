---
title: Panoramica della distribuzione di un database PostgreSQL a disponibilità elevata nel servizio Azure Kubernetes con l'interfaccia della riga di comando di Azure
description: Informazioni su come distribuire un database PostgreSQL a disponibilità elevata nel servizio Azure Kubernetes usando l'operatore CloudNativePG con l'interfaccia della riga di comando di Azure.
ms.topic: overview
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---
# Distribuire un database PostgreSQL a disponibilità elevata nel servizio Azure Kubernetes con l'interfaccia della riga di comando di Azure

In questa guida si distribuisce un cluster PostgreSQL a disponibilità elevata che si estende su più zone di disponibilità di Azure nel servizio Azure Kubernetes con l'interfaccia della riga di comando di Azure.

Questo articolo illustra i prerequisiti per la configurazione di un cluster PostgreSQL nel [servizio Azure Kubernetes][what-is-aks] e offre una panoramica del processo di distribuzione completo e dell'architettura.

## Prerequisiti

* Questa guida presuppone una conoscenza di base dei [concetti di base di Kubernetes][core-kubernetes-concepts] e [PostgreSQL][postgresql].
* Sono necessari i **ruoli predefiniti di Azure** **Proprietario** o **Amministratore accesso utenti** e [Collaboratore][azure-roles] in una sottoscrizione nell'account Azure.

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

* Sono necessarie anche le risorse seguenti installate:

  * [Interfaccia della riga di comando di Azure](/cli/azure/install-azure-cli) 2.56 o versione successiva.
  * [Estensione di anteprima del servizio Azure Kubernetes][aks-preview].
  * [jq][jq], versione 1.5 o successiva.
  * [kubectl][install-kubectl] versione 1.21.0 o successiva.
  * [Helm][install-helm] versione 3.0.0 o successiva.
  * [apresl][install-openssl] versione 3.3.0 o successiva.
  * [Visual Studio Code][install-vscode] o equivalente.
  * [Krew][install-krew] versione 0.4.4 o successiva.
  * [kubectl CloudNativePG (CNPG) Plugin][cnpg-plugin].

## Processo di distribuzione

Questa guida illustra come eseguire queste operazioni:

* Usare l'interfaccia della riga di comando di Azure per creare un cluster del servizio Azure Kubernetes a più zone.
* Distribuire un cluster e un database PostgreSQL a disponibilità elevata usando l'[operatore CNPG][cnpg-plugin].
* Configurare il monitoraggio per PostgreSQL usando Prometheus e Grafana.
* Distribuire un set di dati di esempio in un database PostgreSQL.
* Eseguire gli aggiornamenti del cluster PostgreSQL e del servizio Azure Kubernetes.
* Simulare un'interruzione del cluster e il failover della replica PostgreSQL.
* Eseguire il backup e il ripristino di un database PostgreSQL.

## Architettura di distribuzione

Questo diagramma illustra la configurazione di un cluster PostgreSQL con una replica primaria e due repliche in lettura gestite dall'operatore [CloudNativePG (CNPG)](https://cloudnative-pg.io/). L'architettura offre un postgreSQL a disponibilità elevata in esecuzione in un cluster del servizio Azure Kubernetes in grado di resistere a un'interruzione della zona eseguendo il failover tra le repliche.

I backup vengono archiviati in [Archiviazione BLOB di Azure](/azure/storage/blobs/), offrendo un altro modo per ripristinare il database in caso di problemi con la replica di streaming dalla replica primaria.

:::image source="./media/postgresql-ha-overview/architecture-diagram.png" alt-text="Diagramma dell'architettura CNPG." lightbox="./media/postgresql-ha-overview/architecture-diagram.png":::

> [!NOTE]
> L'operatore CNPG supporta solo *un database per ogni cluster*. Pianificare di conseguenza le applicazioni che richiedono la separazione dei dati a livello di database.

## Passaggi successivi

> [!div class="nextstepaction"]
> [Creare l'infrastruttura per distribuire un database PostgreSQL a disponibilità elevata nel servizio Azure Kubernetes usando l'operatore CNPG][create-infrastructure]

## Collaboratori

*Questo articolo viene gestito da Microsoft. Originariamente è stato scritto dai collaboratori* seguenti:

* Ken Kilty | Responsabile TPM
* Russell de Pina | Responsabile TPM
* Adrian Joian | Senior Customer Engineer
* Jenny Hayes | Sviluppatore di contenuti senior
* Carol Smith | Sviluppatore di contenuti senior
* Erin Schaffer | Sviluppatore di contenuti 2
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
