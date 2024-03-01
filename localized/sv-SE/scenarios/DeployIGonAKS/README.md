---
title: Distribuera Inspektor Gadget i ett Azure Kubernetes Service-kluster
description: Den här självstudien visar hur du distribuerar Inspektor Gadget i ett AKS-kluster
author: josebl
ms.author: josebl
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Snabbstart: Distribuera Inspektor Gadget i ett Azure Kubernetes Service-kluster

Välkommen till den här självstudien där vi tar dig steg för steg när du distribuerar [Inspektor Gadget](https://www.inspektor-gadget.io/) i ett AkS-kluster (Azure Kubernetes Service) med kubectl-plugin-programmet: `gadget`. Den här självstudien förutsätter att du redan är inloggad i Azure CLI och har valt en prenumeration som ska användas med CLI.

## Definiera miljövariabler

Det första steget i den här självstudien är att definiera miljövariabler:

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myResourceGroup$RANDOM_ID"
export REGION="eastus"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
```

## Skapa en resursgrupp

En resursgrupp är en container för relaterade resurser. Alla resurser måste placeras i en resursgrupp. Vi skapar en för den här självstudien. Följande kommando skapar en resursgrupp med de tidigare definierade parametrarna $MY_RESOURCE_GROUP_NAME och $REGION.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Resultat:

<!-- expected_similarity=0.3 -->
```JSON
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myResourceGroup210",
  "location": "eastus",
  "managedBy": null,
  "name": "testResourceGroup",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Skapa AKS-kluster

Skapa ett AKS-kluster med kommandot az aks create.

Det tar bara några minuter.

```bash
az aks create \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --name $MY_AKS_CLUSTER_NAME \
  --location $REGION \
  --no-ssh-key
```

## Anslut till klustret

Om du vill hantera ett Kubernetes-kluster använder du Kubernetes-kommandoradsklienten kubectl. kubectl är redan installerat om du använder Azure Cloud Shell.

1. Installera az aks CLI lokalt med kommandot az aks install-cli

    ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
    ```

2. Konfigurera kubectl för att ansluta till ditt Kubernetes-kluster med kommandot az aks get-credentials. Följande kommando:
    - Laddar ned autentiseringsuppgifter och konfigurerar Kubernetes CLI för att använda dem.
    - Använder ~/.kube/config, standardplatsen för Kubernetes-konfigurationsfilen. Ange en annan plats för kubernetes-konfigurationsfilen med argumentet --file.

    > [!WARNING]
    > Detta skriver över alla befintliga autentiseringsuppgifter med samma post

    ```bash
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
    ```

3. Kontrollera anslutningen till klustret med kommandot kubectl get. Det här kommandot returnerar en lista över klusternoderna.

    ```bash
    kubectl get nodes
    ```

## Installera Inspektor Gadget

Installationen av Inspektor Gadget består av två steg:

1. Installera kubectl-plugin-programmet i användarens system.
2. Installera Inspektor Gadget i klustret.

    > [!NOTE]
    > Det finns ytterligare mekanismer för att distribuera och använda Inspektor Gadget, som var och en är skräddarsydd för specifika användningsfall och krav. Att använda plugin-programmet `kubectl gadget` täcker många av dem, men inte alla. Distributionen av Inspektor Gadget med `kubectl gadget` plugin-programmet beror till exempel på Kubernetes API-serverns tillgänglighet. Om du inte kan vara beroende av en sådan komponent eftersom dess tillgänglighet ibland kan komprometteras rekommenderar vi att du inte använder distributionsmekanismen `kubectl gadget`. Kontrollera [ig-dokumentationen](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/ig.md) för att veta vad du ska göra i det och andra användningsfall.

### Installera kubectl-plugin-programmet: `gadget`

Installera den senaste versionen av kubectl-plugin-programmet från versionssidan, avkomprimera och flytta den `kubectl-gadget` körbara filen till `$HOME/.local/bin`:

> [!NOTE]
> Om du vill installera den med eller [`krew`](https://sigs.k8s.io/krew) kompilera den från källan följer du den officiella dokumentationen: [installera kubectl-gadget](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-kubectl-gadget).

```bash
IG_VERSION=$(curl -s https://api.github.com/repos/inspektor-gadget/inspektor-gadget/releases/latest | jq -r .tag_name)
IG_ARCH=amd64
mkdir -p $HOME/.local/bin
export PATH=$PATH:$HOME/.local/bin
curl -sL https://github.com/inspektor-gadget/inspektor-gadget/releases/download/${IG_VERSION}/kubectl-gadget-linux-${IG_ARCH}-${IG_VERSION}.tar.gz  | tar -C $HOME/.local/bin -xzf - kubectl-gadget
```

Nu ska vi kontrollera installationen genom att `version` köra kommandot:

```bash
kubectl gadget version
```

Kommandot `version` visar versionen av klienten (plugin-programmet kubectl gadget) och visar att den ännu inte har installerats på servern (klustret):

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: not installed$"-->
```text
Client version: vX.Y.Z
Server version: not installed
```

### Installera Inspektor Gadget i klustret

Följande kommando distribuerar DaemonSet:

> [!NOTE]
> Det finns flera alternativ för att anpassa distributionen: använd en specifik containeravbildning, distribuera till specifika noder och många andra. Om du vill veta alla kan du läsa den officiella dokumentationen: [installera i klustret](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-in-the-cluster).

```bash
kubectl gadget deploy
```

Nu ska vi kontrollera installationen genom att `version` köra kommandot igen:

```bash
kubectl gadget version
```

Den här gången installeras klienten och servern korrekt:

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: v\d+\.\d+\.\d+$"-->
```text
Client version: vX.Y.Z
Server version: vX.Y.Z
```

Nu kan du börja köra gadgetarna:

```bash
kubectl gadget help
```

<!--
## Clean Up

### Undeploy Inspektor Gadget

```bash
kubectl gadget undeploy
```

### Clean up Azure resources

When no longer needed, you can use `az group delete` to remove the resource group, cluster, and all related resources as follows. The `--no-wait` parameter returns control to the prompt without waiting for the operation to complete. The `--yes` parameter confirms that you wish to delete the resources without an additional prompt to do so.

```bash
az group delete --name $MY_RESOURCE_GROUP_NAME --no-wait --yes
```
-->

## Nästa steg
- [Verkliga scenarier där Inspektor Gadget kan hjälpa dig](https://go.microsoft.com/fwlink/p/?linkid=2260402#use-cases)
- [Utforska tillgängliga prylar](https://go.microsoft.com/fwlink/p/?linkid=2260070)
- [Kör ett eget eBPF-program](https://go.microsoft.com/fwlink/p/?linkid=2259865)
