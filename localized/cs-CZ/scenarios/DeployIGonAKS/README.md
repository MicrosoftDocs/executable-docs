---
title: Nasazení miniaplikace Inspektor v clusteru Azure Kubernetes Service
description: 'V tomto kurzu se dozvíte, jak nasadit Miniaplikaci Inspektor v clusteru AKS.'
author: josebl
ms.author: josebl
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Rychlý start: Nasazení miniaplikace Inspektor v clusteru Azure Kubernetes Service

[![Nasazení do Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262844)

Vítejte v tomto kurzu, kde vás provedeme krok za krokem při nasazování [Miniaplikace](https://www.inspektor-gadget.io/) Inspektor v clusteru Azure Kubernetes Service (AKS) s modulem plug-in kubectl: `gadget`. V tomto kurzu se předpokládá, že jste už přihlášení k Azure CLI a vybrali jste předplatné, které se má použít s rozhraním příkazového řádku.

## Definování proměnných prostředí

Prvním krokem v tomto kurzu je definování proměnných prostředí:

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myResourceGroup$RANDOM_ID"
export REGION="eastus"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
```

## Vytvoření skupiny zdrojů

Skupina prostředků je kontejner pro související prostředky. Všechny prostředky musí být umístěné ve skupině prostředků. Pro účely tohoto kurzu ho vytvoříme. Následující příkaz vytvoří skupinu prostředků s dříve definovanými parametry $MY_RESOURCE_GROUP_NAME a $REGION.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Výsledky:

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

## Vytvoření clusteru AKS

Vytvořte cluster AKS pomocí příkazu az aks create.

Bude to několik minut trvat.

```bash
az aks create \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --name $MY_AKS_CLUSTER_NAME \
  --location $REGION \
  --no-ssh-key
```

## Připojení ke clusteru

Ke správě clusteru Kubernetes použijte klienta příkazového řádku Kubernetes kubectl. Kubectl je už nainstalovaný, pokud používáte Azure Cloud Shell.

1. Místní instalace az aks CLI pomocí příkazu az aks install-cli

    ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
    ```

2. Pomocí příkazu az aks get-credentials nakonfigurujte kubectl pro připojení ke clusteru Kubernetes. Následující příkaz:
    - Stáhne přihlašovací údaje a nakonfiguruje rozhraní příkazového řádku Kubernetes tak, aby je používalo.
    - Používá ~/.kube/config, výchozí umístění konfiguračního souboru Kubernetes. Pomocí argumentu --file zadejte jiné umístění konfiguračního souboru Kubernetes.

    > [!WARNING]
    > Tím se přepíše všechny existující přihlašovací údaje se stejnou položkou.

    ```bash
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
    ```

3. Pomocí příkazu kubectl get ověřte připojení ke clusteru. Tento příkaz vrátí seznam uzlů clusteru.

    ```bash
    kubectl get nodes
    ```

## Instalace miniaplikace Inspektor

Instalace Inspektor Miniaplikace se skládá ze dvou kroků:

1. Instalace modulu plug-in kubectl v systému uživatele
2. Instalace Miniaplikace Inspektor v clusteru

    > [!NOTE]
    > Existují další mechanismy pro nasazení a využití miniaplikace Inspektor, které jsou přizpůsobené konkrétním případům použití a požadavkům. Použití modulu `kubectl gadget` plug-in pokrývá mnoho z nich, ale ne všechny. Nasazení miniaplikace Inspektor s modulem `kubectl gadget` plug-in například závisí na dostupnosti serveru rozhraní API Kubernetes. Pokud tedy nemůžete na takové komponentě záviset, protože její dostupnost může být někdy ohrožená, doporučuje se nepoužívat `kubectl gadget`mechanismus nasazení. Projděte si [dokumentaci](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/ig.md) ig a zjistěte, co v tom dělat, a další případy použití.

### Instalace modulu plug-in kubectl: `gadget`

Nainstalujte nejnovější verzi modulu plug-in kubectl ze stránky vydaných verzí, odkomentujte a přesuňte `kubectl-gadget` spustitelný soubor do `$HOME/.local/bin`:

> [!NOTE]
> Pokud ho chcete nainstalovat nebo [`krew`](https://sigs.k8s.io/krew) zkompilovat ze zdroje, postupujte podle oficiální dokumentace: [instalace miniaplikace](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-kubectl-gadget) kubectl.

```bash
IG_VERSION=$(curl -s https://api.github.com/repos/inspektor-gadget/inspektor-gadget/releases/latest | jq -r .tag_name)
IG_ARCH=amd64
mkdir -p $HOME/.local/bin
export PATH=$PATH:$HOME/.local/bin
curl -sL https://github.com/inspektor-gadget/inspektor-gadget/releases/download/${IG_VERSION}/kubectl-gadget-linux-${IG_ARCH}-${IG_VERSION}.tar.gz  | tar -C $HOME/.local/bin -xzf - kubectl-gadget
```

Teď ověříme instalaci spuštěním `version` příkazu:

```bash
kubectl gadget version
```

Příkaz `version` zobrazí verzi klienta (modul plug-in kubectl miniaplikace) a zobrazí, že ještě není na serveru (clusteru):

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: not installed$"-->
```text
Client version: vX.Y.Z
Server version: not installed
```

### Instalace Miniaplikace Inspektor v clusteru

Následující příkaz nasadí daemonSet:

> [!NOTE]
> K dispozici je několik možností pro přizpůsobení nasazení: použití konkrétní image kontejneru, nasazení do konkrétních uzlů a mnoho dalších. Pokud chcete znát všechny, projděte si oficiální dokumentaci: [instalaci v clusteru](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-in-the-cluster).

```bash
kubectl gadget deploy
```

Teď ověříme instalaci opětovným spuštěním `version` příkazu:

```bash
kubectl gadget version
```

Tentokrát se klient a server správně nainstalují:

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: v\d+\.\d+\.\d+$"-->
```text
Client version: vX.Y.Z
Server version: vX.Y.Z
```

Teď můžete začít spouštět miniaplikace:

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

## Další kroky
- [Reálné scénáře, ve kterých vám inspektor Miniaplikace může pomoct](https://go.microsoft.com/fwlink/p/?linkid=2260402#use-cases)
- [Prozkoumání dostupných miniaplikací](https://go.microsoft.com/fwlink/p/?linkid=2260070)
- [Spuštění vlastního programu eBPF](https://go.microsoft.com/fwlink/p/?linkid=2259865)
