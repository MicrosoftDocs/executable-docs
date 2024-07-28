---
title: Magas rendelkezésre állású PostgreSQL-adatbázis üzembe helyezésének áttekintése az AKS-ben az Azure CLI-vel
description: 'Megtudhatja, hogyan helyezhet üzembe magas rendelkezésre állású PostgreSQL-adatbázist az AKS-en a CloudNativePG operátorral az Azure CLI-vel.'
ms.topic: overview
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---
# Magas rendelkezésre állású PostgreSQL-adatbázis üzembe helyezése az AKS-ben az Azure CLI-vel

Ebben az útmutatóban egy magas rendelkezésre állású PostgreSQL-fürtöt helyez üzembe, amely több Azure rendelkezésre állási zónát is lefed az AKS-ben az Azure CLI-vel.

Ez a cikk bemutatja a PostgreSQL-fürt Azure Kubernetes Service-ben (AKS)[ való ][what-is-aks]beállításának előfeltételeit, és áttekintést nyújt a teljes üzembehelyezési folyamatról és architektúráról.

## Előfeltételek

* Ez az útmutató alapszintű ismereteket feltételez a Kubernetes alapfogalmairól [][core-kubernetes-concepts] és a [PostgreSQL-ről][postgresql].
* Szüksége van a tulajdonosi vagy felhasználói hozzáférési rendszergazdára **, valamint a **közreműködő** [Azure beépített szerepkörére][azure-roles] az Azure-fiókjában lévő előfizetésen.******

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

* A következő erőforrásokat is telepítenie kell:

  * [Az Azure CLI](/cli/azure/install-azure-cli) 2.56-os vagy újabb verziója.
  * [Az Azure Kubernetes Service (AKS) előzetes verziója.][aks-preview]
  * [jq][jq], 1.5-ös vagy újabb verzió.
  * [kubectl][install-kubectl] 1.21.0-s vagy újabb verzió.
  * [Helm][install-helm] 3.0.0-s vagy újabb verziója.
  * [nyitja meg a][install-openssl] 3.3.0-s vagy újabb verziót.
  * [Visual Studio Code][install-vscode] vagy azzal egyenértékű.
  * [A Krew][install-krew] 0.4.4-es vagy újabb verziója.
  * [kubectl CloudNativePG (CNPG) beépülő modul][cnpg-plugin].

## Üzembehelyezési folyamat

Ebből az útmutatóból a következőket tanulhatja meg:

* Többzónás AKS-fürt létrehozása az Azure CLI használatával.
* Helyezzen üzembe egy magas rendelkezésre állású PostgreSQL-fürtöt és -adatbázist a [CNPG operátorral][cnpg-plugin].
* A PostgreSQL monitorozásának beállítása a Prometheus és a Grafana használatával.
* Mintaadatkészlet üzembe helyezése PostgreSQL-adatbázisban.
* PostgreSQL- és AKS-fürtfrissítések végrehajtása.
* Fürtkimaradás és PostgreSQL-replika feladatátvételének szimulálása.
* PostgreSQL-adatbázis biztonsági mentésének és visszaállításának végrehajtása.

## Üzembehelyezési architektúra

Ez az ábra egy PostgreSQL-fürt beállítását mutatja be egy elsődleges replikával és két, a [CloudNativePG (CNPG)](https://cloudnative-pg.io/) operátor által felügyelt olvasási replikával. Az architektúra egy magas rendelkezésre állású PostgreSQL-t biztosít, amely egy AKS-fürtön fut, amely képes ellenállni a zónakimaradásnak a replikák közötti feladatátvételsel.

A biztonsági másolatok az Azure Blob Storage-ban [](/azure/storage/blobs/)vannak tárolva, így az adatbázis visszaállítása az elsődleges replikából történő streamelési replikációval kapcsolatos probléma esetén is lehetséges.

:::image source="./media/postgresql-ha-overview/architecture-diagram.png" alt-text="A CNPG architektúrájának diagramja." lightbox="./media/postgresql-ha-overview/architecture-diagram.png":::

> [!NOTE]
> A CNPG-operátor fürtönként* csak *egy adatbázist támogat. Ennek megfelelően tervezze meg azokat az alkalmazásokat, amelyek adatelkülönítést igényelnek az adatbázis szintjén.

## Következő lépések

> [!div class="nextstepaction"]
> [Hozza létre az infrastruktúrát egy magas rendelkezésre állású PostgreSQL-adatbázis üzembe helyezéséhez az AKS-ben a CNPG-operátor használatával][create-infrastructure]

## Közreműködők

*Ezt a cikket a Microsoft tartja karban. Eredetileg a következő közreműködők* írták:

* Ken Kilty | Egyszerű TPM
* Russell de | Egyszerű TPM
* Adrian Joian | Vezető ügyfélmérnök
* Jenny Hayes | Vezető tartalomfejlesztő
* Carol Smith | Vezető tartalomfejlesztő
* Erin Schaffer | Tartalomfejlesztő 2
* Adam Sharif | 2. ügyfélmérnök

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
