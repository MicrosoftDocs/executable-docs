---
title: Přehled nasazení vysoce dostupné databáze PostgreSQL v AKS pomocí Azure CLI
description: 'Zjistěte, jak nasadit vysoce dostupnou databázi PostgreSQL v AKS pomocí operátoru CloudNativePG!!'
ms.topic: overview
ms.date: 07/24/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---
# Nasazení vysoce dostupné databáze PostgreSQL v AKS pomocí Azure CLI

V této příručce nasadíte vysoce dostupný cluster PostgreSQL, který zahrnuje více zón dostupnosti Azure v AKS pomocí Azure CLI!

Tento článek vás provede požadavky na nastavení clusteru PostgreSQL ve [službě Azure Kubernetes Service (AKS)][what-is-aks] a poskytuje přehled celého procesu nasazení a architektury.

## Požadavky

* Tato příručka předpokládá základní znalosti [základních konceptů][core-kubernetes-concepts] Kubernetes a [PostgreSQL][postgresql].
* Potřebujete roli **vlastníka** nebo **správce** uživatelských přístupů a **předdefinované role[ Azure přispěvatele ][azure-roles]** v předplatném ve vašem účtu Azure.

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

* Potřebujete také nainstalované následující prostředky:

  * [Azure CLI](/cli/azure/install-azure-cli) verze 2.56 nebo novější
  * [Rozšíření][aks-preview] Azure Kubernetes Service (AKS) ve verzi Preview
  * [jq][jq], verze 1.5 nebo novější.
  * [kubectl][install-kubectl] verze 1.21.0 nebo novější.
  * [Helm][install-helm] verze 3.0.0 nebo novější
  * [openssl][install-openssl] verze 3.3.0 nebo novější.
  * [Visual Studio Code][install-vscode] nebo ekvivalentní.
  * [Krew][install-krew] verze 0.4.4 nebo novější.
  * [modul plug-in][cnpg-plugin] kubectl CloudNativePG (CNPG).

## Proces nasazení

V této příručce se naučíte:

* Pomocí Azure CLI vytvořte cluster AKS s více zónami.
* Nasaďte vysoce dostupný cluster a databázi PostgreSQL pomocí operátoru [][cnpg-plugin]CNPG.
* Nastavení monitorování pro PostgreSQL pomocí Prometheus a Grafany
* Nasaďte ukázkovou datovou sadu do databáze PostgreSQL.
* Proveďte upgrady clusteru PostgreSQL a AKS.
* Simulace přerušení clusteru a převzetí služeb při selhání repliky PostgreSQL
* Proveďte zálohování a obnovení databáze PostgreSQL.

## Architektura nasazení

Tento diagram znázorňuje nastavení clusteru PostgreSQL s jednou primární replikou a dvěma replikami pro čtení spravovanými operátorem [CloudNativePG (CNPG](https://cloudnative-pg.io/) ). Architektura poskytuje vysoce dostupný PostgreSQL běžící v clusteru AKS, který dokáže odolat výpadku zóny převzetím služeb při selhání napříč replikami.

Zálohy se ukládají ve [službě Azure Blob Storage](/azure/storage/blobs/) a poskytují další způsob obnovení databáze v případě problému s replikací streamování z primární repliky.

:::image source="./media/postgresql-ha-overview/architecture-diagram.png" alt-text="Diagram architektury CNPG" lightbox="./media/postgresql-ha-overview/architecture-diagram.png":::

> [!NOTE]
> Operátor CNPG podporuje pouze *jednu databázi na cluster*. Naplánujte odpovídajícím způsobem aplikace, které vyžadují oddělení dat na úrovni databáze.

## Další kroky

> [!div class="nextstepaction"]
> [Vytvoření infrastruktury pro nasazení vysoce dostupné databáze PostgreSQL v AKS pomocí operátoru CNPG][create-infrastructure]

## Přispěvatelé

*Tento článek spravuje Microsoft. Původně byla napsána následujícími přispěvateli*:

* Ken Kilty | Hlavní čip TPM
* Russell de Pina | Hlavní čip TPM
* Adrian Joian | Vedoucí zákaznický inženýr
* Jenny Hayes | Vedoucí vývojář obsahu
* Carol Smith | Vedoucí vývojář obsahu
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
