---
title: Wdrażanie gadżetu Inspektor w klastrze usługi Azure Kubernetes Service
description: 'W tym samouczku pokazano, jak wdrożyć gadżet Inspektora w klastrze usługi AKS'
author: josebl
ms.author: josebl
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Szybki start: wdrażanie gadżetu Inspektor w klastrze usługi Azure Kubernetes Service

[![Wdróż na platformie Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262844)

Witamy w tym samouczku, w którym wykonamy krok po kroku wdrażanie [gadżetu](https://www.inspektor-gadget.io/) Inspektora w klastrze usługi Azure Kubernetes Service (AKS) za pomocą wtyczki kubectl: `gadget`. W tym samouczku założono, że zalogowano się już do interfejsu wiersza polecenia platformy Azure i wybrano subskrypcję do użycia z interfejsem wiersza polecenia.

## Definiowanie zmiennych środowiskowych

Pierwszym krokiem w tym samouczku jest zdefiniowanie zmiennych środowiskowych:

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myResourceGroup$RANDOM_ID"
export REGION="eastus"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
```

## Tworzenie grupy zasobów

Grupa zasobów to kontener powiązanych zasobów. Wszystkie zasoby należy umieścić w grupie zasobów. Utworzymy go na potrzeby tego samouczka. Następujące polecenie tworzy grupę zasobów z wcześniej zdefiniowanymi parametrami $MY_RESOURCE_GROUP_NAME i $REGION.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Wyniki:

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

## Tworzenie klastra usługi AKS

Utwórz klaster usługi AKS przy użyciu polecenia az aks create.

Operacja potrwa kilka minut.

```bash
az aks create \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --name $MY_AKS_CLUSTER_NAME \
  --location $REGION \
  --no-ssh-key
```

## Łączenie z klastrem

Aby zarządzać klastrem Kubernetes, użyj klienta wiersza polecenia kubernetes kubectl. Narzędzie kubectl jest już zainstalowane, jeśli używasz usługi Azure Cloud Shell.

1. Zainstaluj interfejs wiersza polecenia az aks lokalnie przy użyciu polecenia az aks install-cli

    ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
    ```

2. Skonfiguruj narzędzie kubectl, aby nawiązać połączenie z klastrem Kubernetes przy użyciu polecenia az aks get-credentials. Następujące polecenie:
    - Pobiera poświadczenia i konfiguruje interfejs wiersza polecenia platformy Kubernetes do ich używania.
    - Używa polecenia ~/.kube/config, domyślnej lokalizacji pliku konfiguracji kubernetes. Określ inną lokalizację pliku konfiguracji platformy Kubernetes przy użyciu argumentu --file.

    > [!WARNING]
    > Spowoduje to zastąpienie wszystkich istniejących poświadczeń przy użyciu tego samego wpisu

    ```bash
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
    ```

3. Sprawdź połączenie z klastrem przy użyciu polecenia kubectl get. To polecenie zwraca listę węzłów klastra.

    ```bash
    kubectl get nodes
    ```

## Instalowanie gadżetu Inspektor

Instalacja gadżetu Inspektor składa się z dwóch kroków:

1. Instalowanie wtyczki kubectl w systemie użytkownika.
2. Instalowanie gadżetu Inspektor w klastrze.

    > [!NOTE]
    > Istnieją dodatkowe mechanizmy wdrażania i używania gadżetu Inspektor, z których każdy jest dostosowany do konkretnych przypadków użycia i wymagań. Użycie wtyczki `kubectl gadget` obejmuje wiele z nich, ale nie wszystkie. Na przykład wdrożenie gadżetu `kubectl gadget` Inspektora za pomocą wtyczki zależy od dostępności serwera interfejsu API Kubernetes. Jeśli więc nie możesz zależeć od takiego składnika, ponieważ jego dostępność może być czasami naruszona, zaleca się, aby nie używać `kubectl gadget`mechanizmu wdrażania. [Zapoznaj się z dokumentacją](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/ig.md) ig, aby dowiedzieć się, co należy zrobić w tym i innych przypadkach użycia.

### Instalowanie wtyczki kubectl: `gadget`

Zainstaluj najnowszą wersję wtyczki kubectl ze strony wydań, co powoduje odłączenie pliku wykonywalnego i przeniesienie pliku `kubectl-gadget` wykonywalnego do `$HOME/.local/bin`programu :

> [!NOTE]
> Jeśli chcesz go zainstalować przy użyciu [`krew`](https://sigs.k8s.io/krew) lub skompilować ze źródła, postępuj zgodnie z oficjalną dokumentacją: [instalowanie gadżetu](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-kubectl-gadget) kubectl.

```bash
IG_VERSION=$(curl -s https://api.github.com/repos/inspektor-gadget/inspektor-gadget/releases/latest | jq -r .tag_name)
IG_ARCH=amd64
mkdir -p $HOME/.local/bin
export PATH=$PATH:$HOME/.local/bin
curl -sL https://github.com/inspektor-gadget/inspektor-gadget/releases/download/${IG_VERSION}/kubectl-gadget-linux-${IG_ARCH}-${IG_VERSION}.tar.gz  | tar -C $HOME/.local/bin -xzf - kubectl-gadget
```

Teraz zweryfikujmy instalację, uruchamiając `version` polecenie :

```bash
kubectl gadget version
```

Polecenie `version` wyświetli wersję klienta (wtyczkę gadżetu kubectl) i pokaże, że nie jest jeszcze zainstalowany na serwerze (klastrze):

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: not installed$"-->
```text
Client version: vX.Y.Z
Server version: not installed
```

### Instalowanie gadżetu Inspektor w klastrze

Następujące polecenie spowoduje wdrożenie elementu DaemonSet:

> [!NOTE]
> Dostępnych jest kilka opcji dostosowywania wdrożenia: użyj określonego obrazu kontenera, wdróż go w określonych węzłach i wielu innych. Aby poznać wszystkie te elementy, zapoznaj się z oficjalną dokumentacją: [instalowanie w klastrze](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-in-the-cluster).

```bash
kubectl gadget deploy
```

Teraz zweryfikujmy instalację, uruchamiając `version` ponownie polecenie:

```bash
kubectl gadget version
```

Tym razem klient i serwer zostaną poprawnie zainstalowane:

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: v\d+\.\d+\.\d+$"-->
```text
Client version: vX.Y.Z
Server version: vX.Y.Z
```

Teraz możesz zacząć uruchamiać gadżety:

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

## Następne kroki
- [Rzeczywiste scenariusze, w których inspektor gadżet może ci pomóc](https://go.microsoft.com/fwlink/p/?linkid=2260402#use-cases)
- [Eksplorowanie dostępnych gadżetów](https://go.microsoft.com/fwlink/p/?linkid=2260070)
- [Uruchamianie własnego programu eBPF](https://go.microsoft.com/fwlink/p/?linkid=2259865)
