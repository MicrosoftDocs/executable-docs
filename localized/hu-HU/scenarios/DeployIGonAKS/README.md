---
title: Inspektor-minialkalmazás üzembe helyezése Egy Azure Kubernetes Service-fürtben
description: 'Ez az oktatóanyag bemutatja, hogyan helyezhet üzembe inspektor minialkalmazást egy AKS-fürtben'
author: josebl
ms.author: josebl
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Rövid útmutató: Inspektor-minialkalmazás üzembe helyezése egy Azure Kubernetes Service-fürtben

Üdvözöljük ebben az oktatóanyagban, amelyben lépésről lépésre elvégezzük az Inspektor Gadget[ üzembe helyezését ](https://www.inspektor-gadget.io/)egy Azure Kubernetes Service-fürtben (AKS) a kubectl beépülő modullal: `gadget`. Ez az oktatóanyag feltételezi, hogy már bejelentkezett az Azure CLI-be, és kiválasztotta a parancssori felülettel használni kívánt előfizetést.

## Környezeti változók definiálása

Az oktatóanyag első lépése a környezeti változók definiálása:

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myResourceGroup$RANDOM_ID"
export REGION="eastus"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
```

## Erőforráscsoport létrehozása

Az erőforráscsoportok a kapcsolódó erőforrások tárolói. Minden erőforrást egy erőforráscsoportba kell helyezni. Létrehozunk egyet ehhez az oktatóanyaghoz. A következő parancs létrehoz egy erőforráscsoportot a korábban definiált $MY_RESOURCE_GROUP_NAME és $REGION paraméterekkel.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Eredmények:

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

## AKS-fürt létrehozása

Hozzon létre egy AKS-fürtöt az az aks create paranccsal.

Ez eltarthat néhány percig.

```bash
az aks create \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --name $MY_AKS_CLUSTER_NAME \
  --location $REGION \
  --no-ssh-key
```

## Csatlakozás a fürthöz

Kubernetes-fürt kezeléséhez használja a Kubernetes parancssori ügyfelet, a kubectl-et. Az Azure Cloud Shell használata esetén a kubectl már telepítve van.

1. Az az aks CLI helyi telepítése az az aks install-cli paranccsal

    ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
    ```

2. A Kubectl konfigurálása a Kubernetes-fürthöz való csatlakozáshoz az az aks get-credentials paranccsal. A következő parancs:
    - Letölti a hitelesítő adatokat, és konfigurálja a Kubernetes parancssori felületét a használatukhoz.
    - A Kubernetes-konfigurációs fájl alapértelmezett helye a ~/.kube/config. Adjon meg egy másik helyet a Kubernetes-konfigurációs fájlhoz a --file argumentum használatával.

    > [!WARNING]
    > Ez felülírja a meglévő hitelesítő adatokat ugyanazzal a bejegyzéssel

    ```bash
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
    ```

3. Ellenőrizze a fürthöz való kapcsolatot a kubectl get paranccsal. Ez a parancs a fürtcsomópontok listáját adja vissza.

    ```bash
    kubectl get nodes
    ```

## Az Inspektor minialkalmazás telepítése

Az Inspektor Minialkalmazás telepítése két lépésből áll:

1. A kubectl beépülő modul telepítése a felhasználó rendszerében.
2. Az Inspektor minialkalmazás telepítése a fürtbe.

    > [!NOTE]
    > Az Inspektor Gadget üzembe helyezésére és használatára további mechanizmusok is vonatkoznak, amelyek mindegyike adott használati esetekre és követelményekre van szabva. `kubectl gadget` A beépülő modul használata sokukra kiterjed, de nem mindenre. Az Inspektor Gadget beépülő modullal `kubectl gadget` való üzembe helyezése például a Kubernetes API-kiszolgáló elérhetőségétől függ. Ha tehát nem tud függeni egy ilyen összetevőtől, mert a rendelkezésre állása néha sérülhet, akkor ajánlott nem használni az `kubectl gadget`üzembehelyezési mechanizmust. Kérjük, tekintse meg [az ig dokumentációját](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/ig.md) , hogy tudja, mi a teendő ebben az esetben, és egyéb használati eseteket.

### A kubectl beépülő modul telepítése: `gadget`

Telepítse a kubectl beépülő modul legújabb verzióját a kiadási oldalról, törölje a kicsomagolást, és helyezze át a végrehajtható fájlt a `kubectl-gadget` következőre `$HOME/.local/bin`:

> [!NOTE]
> Ha a forrásból [`krew`](https://sigs.k8s.io/krew) szeretné telepíteni vagy lefordítani, kövesse a hivatalos dokumentációt: [kubectl minialkalmazás](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-kubectl-gadget) telepítése.

```bash
IG_VERSION=$(curl -s https://api.github.com/repos/inspektor-gadget/inspektor-gadget/releases/latest | jq -r .tag_name)
IG_ARCH=amd64
mkdir -p $HOME/.local/bin
export PATH=$PATH:$HOME/.local/bin
curl -sL https://github.com/inspektor-gadget/inspektor-gadget/releases/download/${IG_VERSION}/kubectl-gadget-linux-${IG_ARCH}-${IG_VERSION}.tar.gz  | tar -C $HOME/.local/bin -xzf - kubectl-gadget
```

Most ellenőrizze a telepítést a `version` parancs futtatásával:

```bash
kubectl gadget version
```

A `version` parancs megjeleníti az ügyfél verzióját (kubectl minialkalmazás beépülő modul), és megmutatja, hogy még nincs telepítve a kiszolgálón (a fürtben):

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: not installed$"-->
```text
Client version: vX.Y.Z
Server version: not installed
```

### Az Inspektor minialkalmazás telepítése a fürtben

A következő parancs üzembe helyezi a DaemonSetet:

> [!NOTE]
> Az üzembe helyezés testreszabásához több lehetőség is rendelkezésre áll: egy adott tárolórendszerkép használata, üzembe helyezés adott csomópontokon és sok más. Az összes megismeréséhez tekintse meg a hivatalos dokumentációt: [telepítés a fürtön](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-in-the-cluster).

```bash
kubectl gadget deploy
```

Most ellenőrizze a telepítést a `version` parancs ismételt futtatásával:

```bash
kubectl gadget version
```

Ezúttal az ügyfél és a kiszolgáló megfelelően lesz telepítve:

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: v\d+\.\d+\.\d+$"-->
```text
Client version: vX.Y.Z
Server version: vX.Y.Z
```

Most már megkezdheti a minialkalmazások futtatását:

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

## Következő lépések
- [Valós forgatókönyvek, amelyekben az Inspektor Gadget segíthet](https://go.microsoft.com/fwlink/p/?linkid=2260402#use-cases)
- [Az elérhető minialkalmazások felfedezése](https://go.microsoft.com/fwlink/p/?linkid=2260070)
- [Saját eBPF-program futtatása](https://go.microsoft.com/fwlink/p/?linkid=2259865)
