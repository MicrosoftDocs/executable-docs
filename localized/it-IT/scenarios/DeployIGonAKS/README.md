---
title: Distribuire Inspektor Gadget in un cluster servizio Azure Kubernetes
description: Questa esercitazione illustra come distribuire Inspektor Gadget in un cluster del servizio Azure Kubernetes
author: josebl
ms.author: josebl
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Guida introduttiva: Distribuire Inspektor Gadget in un cluster servizio Azure Kubernetes

[![Distribuzione in Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262844)

Questa esercitazione illustra come distribuire [Inspektor Gadget](https://www.inspektor-gadget.io/) in un cluster servizio Azure Kubernetes del servizio Azure Kubernetes con il plug-in kubectl: `gadget`. Questa esercitazione presuppone che l'utente sia già connesso all'interfaccia della riga di comando di Azure e abbia selezionato una sottoscrizione da usare con l'interfaccia della riga di comando.

## Definire le variabili di ambiente

Il primo passaggio di questa esercitazione consiste nel definire le variabili di ambiente:

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myResourceGroup$RANDOM_ID"
export REGION="eastus"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
```

## Creare un gruppo di risorse

Un gruppo di risorse è un contenitore per le risorse correlate. Tutte le risorse devono essere inserite in un gruppo di risorse. Ne verrà creata una per questa esercitazione. Il comando seguente crea un gruppo di risorse con i parametri $MY_RESOURCE_GROUP_NAME definiti in precedenza e $REGION.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Risultati:

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

## Creare un cluster del servizio Azure Kubernetes

Creare un cluster del servizio Azure Kubernetes usando il comando az aks create.

L'operazione richiederà qualche minuto.

```bash
az aks create \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --name $MY_AKS_CLUSTER_NAME \
  --location $REGION \
  --no-ssh-key
```

## Stabilire la connessione al cluster

Per gestire un cluster Kubernetes, usare il client da riga di comando kubernetes kubectl. kubectl è già installato se si usa Azure Cloud Shell.

1. Installare l'interfaccia della riga di comando del servizio Azure Kubernetes in locale usando il comando az aks install-cli

    ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
    ```

2. Per configurare kubectl per la connessione al cluster Kubernetes, usare il comando az aks get-credentials. Con il comando seguente:
    - Scarica le credenziali e configura l'interfaccia della riga di comando di Kubernetes per usarle.
    - Usa ~/.kube/config, il percorso predefinito per il file di configurazione di Kubernetes. Specificare un percorso diverso per il file di configurazione di Kubernetes usando l'argomento --file.

    > [!WARNING]
    > Verrà sovrascritto qualsiasi credenziale esistente con la stessa voce

    ```bash
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
    ```

3. Verificare la connessione al cluster usando il comando kubectl get. Questo comando restituisce un elenco dei nodi del cluster.

    ```bash
    kubectl get nodes
    ```

## Installare Inspektor Gadget

L'installazione di Inspektor Gadget è costituita da due passaggi:

1. Installazione del plug-in kubectl nel sistema dell'utente.
2. Installazione di Inspektor Gadget nel cluster.

    > [!NOTE]
    > Esistono meccanismi aggiuntivi per la distribuzione e l'utilizzo di Inspektor Gadget, ognuno personalizzato per casi d'uso e requisiti specifici. L'uso del plug-in `kubectl gadget` copre molti di loro, ma non tutti. Ad esempio, la distribuzione di Inspektor Gadget con il `kubectl gadget` plug-in dipende dalla disponibilità del server API Kubernetes. Pertanto, se non è possibile dipendere da tale componente perché la disponibilità potrebbe essere talvolta compromessa, è consigliabile non usare il `kubectl gadget`meccanismo di distribuzione. [Consultare la documentazione](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/ig.md) ig per sapere cosa fare in questo caso e altri casi d'uso.

### Installazione del plug-in kubectl: `gadget`

Installare la versione più recente del plug-in kubectl dalla pagina delle versioni, decomprimere e spostare il `kubectl-gadget` file eseguibile in `$HOME/.local/bin`:

> [!NOTE]
> Se si vuole installarlo usando [`krew`](https://sigs.k8s.io/krew) o compilarlo dall'origine, seguire la documentazione ufficiale: [installazione di kubectl gadget.](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-kubectl-gadget)

```bash
IG_VERSION=$(curl -s https://api.github.com/repos/inspektor-gadget/inspektor-gadget/releases/latest | jq -r .tag_name)
IG_ARCH=amd64
mkdir -p $HOME/.local/bin
export PATH=$PATH:$HOME/.local/bin
curl -sL https://github.com/inspektor-gadget/inspektor-gadget/releases/download/${IG_VERSION}/kubectl-gadget-linux-${IG_ARCH}-${IG_VERSION}.tar.gz  | tar -C $HOME/.local/bin -xzf - kubectl-gadget
```

A questo punto, verificare l'installazione eseguendo il `version` comando :

```bash
kubectl gadget version
```

Il `version` comando visualizzerà la versione del client (plug-in kubectl gadget) e mostrerà che non è ancora installato nel server (il cluster):

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: not installed$"-->
```text
Client version: vX.Y.Z
Server version: not installed
```

### Installazione di Inspektor Gadget nel cluster

Il comando seguente distribuirà DaemonSet:

> [!NOTE]
> Sono disponibili diverse opzioni per personalizzare la distribuzione: usare un'immagine del contenitore specifica, eseguire la distribuzione in nodi specifici e molte altre. Per conoscerli tutti, consultare la documentazione ufficiale: [installazione nel cluster](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-in-the-cluster).

```bash
kubectl gadget deploy
```

A questo punto, verificare l'installazione eseguendo di nuovo il `version` comando :

```bash
kubectl gadget version
```

Questa volta, il client e il server verranno installati correttamente:

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: v\d+\.\d+\.\d+$"-->
```text
Client version: vX.Y.Z
Server version: vX.Y.Z
```

È ora possibile avviare l'esecuzione dei gadget:

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

## Passaggi successivi
- [Scenari reali in cui Inspektor Gadget può aiutarti](https://go.microsoft.com/fwlink/p/?linkid=2260402#use-cases)
- [Esplora i gadget disponibili](https://go.microsoft.com/fwlink/p/?linkid=2260070)
- [Eseguire il proprio programma eBPF](https://go.microsoft.com/fwlink/p/?linkid=2259865)
