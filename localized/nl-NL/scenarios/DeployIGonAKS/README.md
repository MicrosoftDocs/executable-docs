---
title: Inspektor Gadget implementeren in een Azure Kubernetes Service-cluster
description: Deze zelfstudie laat zien hoe u Inspektor Gadget implementeert in een AKS-cluster
author: josebl
ms.author: josebl
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Quickstart: Inspektor Gadget implementeren in een Azure Kubernetes Service-cluster

Welkom bij deze zelfstudie waarin we u stap voor stap volgen bij het implementeren van [Inspektor Gadget](https://www.inspektor-gadget.io/) in een AKS-cluster (Azure Kubernetes Service) met de kubectl-invoegtoepassing: `gadget`. In deze zelfstudie wordt ervan uitgegaan dat u al bent aangemeld bij Azure CLI en een abonnement hebt geselecteerd voor gebruik met de CLI.

## Omgevingsvariabelen definiëren

De eerste stap in deze zelfstudie is het definiëren van omgevingsvariabelen:

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myResourceGroup$RANDOM_ID"
export REGION="eastus"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
```

## Een brongroep maken

Een resourcegroep is een container voor gerelateerde resources. Alle resources moeten in een resourcegroep worden geplaatst. We maken er een voor deze zelfstudie. Met de volgende opdracht maakt u een resourcegroep met de eerder gedefinieerde parameters $MY_RESOURCE_GROUP_NAME en $REGION parameters.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Resultaten:

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

## AKS-cluster maken

Maak een AKS-cluster met behulp van de opdracht az aks create.

Dit kan enkele minuten duren.

```bash
az aks create \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --name $MY_AKS_CLUSTER_NAME \
  --location $REGION \
  --no-ssh-key
```

## Verbinding maken met het cluster

Als u een Kubernetes-cluster wilt beheren, gebruikt u de Kubernetes-opdrachtregelclient kubectl. kubectl is al geïnstalleerd als u Azure Cloud Shell gebruikt.

1. Installeer az aks CLI lokaal met behulp van de opdracht az aks install-cli

    ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
    ```

2. Configureer kubectl om verbinding te maken met uw Kubernetes-cluster met behulp van de opdracht az aks get-credentials. De volgende opdracht:
    - Hiermee downloadt u referenties en configureert u de Kubernetes CLI om deze te gebruiken.
    - Maakt gebruik van ~/.kube/config, de standaardlocatie voor het Kubernetes-configuratiebestand. Geef een andere locatie op voor uw Kubernetes-configuratiebestand met behulp van het argument --file.

    > [!WARNING]
    > Hiermee worden alle bestaande referenties met dezelfde vermelding overschreven

    ```bash
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
    ```

3. Controleer de verbinding met uw cluster met behulp van de opdracht kubectl get. Met deze opdracht wordt een lijst met de clusterknooppunten geretourneerd.

    ```bash
    kubectl get nodes
    ```

## Inspektor Gadget installeren

De Installatie van de Inspektor Gadget bestaat uit twee stappen:

1. Installeer de kubectl-invoegtoepassing in het systeem van de gebruiker.
2. Inspektor Gadget installeren in het cluster.

    > [!NOTE]
    > Er zijn aanvullende mechanismen voor het implementeren en gebruiken van Inspektor Gadget, die elk zijn afgestemd op specifieke use cases en vereisten. Het gebruik van de `kubectl gadget` invoegtoepassing omvat veel van hen, maar niet allemaal. Het implementeren van Inspektor Gadget met de `kubectl gadget` invoegtoepassing is bijvoorbeeld afhankelijk van de beschikbaarheid van de Kubernetes-API-server. Dus als u niet kunt afhankelijk zijn van een dergelijk onderdeel omdat de beschikbaarheid soms kan worden aangetast, wordt aanbevolen om het `kubectl gadget`implementatiemechanisme niet te gebruiken. Raadpleeg [de ig-documentatie](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/ig.md) om te weten wat u in dat geval moet doen en andere gebruiksvoorbeelden.

### De kubectl-invoegtoepassing installeren: `gadget`

Installeer de nieuwste versie van de kubectl-invoegtoepassing vanaf de releasepagina, uncompress en verplaats het `kubectl-gadget` uitvoerbare bestand naar `$HOME/.local/bin`:

> [!NOTE]
> Als u deze wilt installeren met behulp [`krew`](https://sigs.k8s.io/krew) van of compileer deze vanuit de bron, volgt u de officiële documentatie: [het installeren van kubectl gadget](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-kubectl-gadget).

```bash
IG_VERSION=$(curl -s https://api.github.com/repos/inspektor-gadget/inspektor-gadget/releases/latest | jq -r .tag_name)
IG_ARCH=amd64
mkdir -p $HOME/.local/bin
export PATH=$PATH:$HOME/.local/bin
curl -sL https://github.com/inspektor-gadget/inspektor-gadget/releases/download/${IG_VERSION}/kubectl-gadget-linux-${IG_ARCH}-${IG_VERSION}.tar.gz  | tar -C $HOME/.local/bin -xzf - kubectl-gadget
```

Nu gaan we de installatie controleren door de opdracht uit te `version` voeren:

```bash
kubectl gadget version
```

Met `version` de opdracht wordt de versie van de client (kubectl gadget-invoegtoepassing) weergegeven en wordt aangegeven dat deze nog niet is geïnstalleerd op de server (het cluster):

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: not installed$"-->
```text
Client version: vX.Y.Z
Server version: not installed
```

### Inspektor Gadget installeren in het cluster

Met de volgende opdracht wordt de DaemonSet geïmplementeerd:

> [!NOTE]
> Er zijn verschillende opties beschikbaar om de implementatie aan te passen: gebruik een specifieke containerinstallatiekopieën, implementeer op specifieke knooppunten en vele andere. Als u alles wilt weten, raadpleegt u de officiële documentatie: [installeren in het cluster](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-in-the-cluster).

```bash
kubectl gadget deploy
```

Nu gaan we de installatie controleren door de opdracht opnieuw uit te `version` voeren:

```bash
kubectl gadget version
```

Deze keer worden de client en server correct geïnstalleerd:

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: v\d+\.\d+\.\d+$"-->
```text
Client version: vX.Y.Z
Server version: vX.Y.Z
```

U kunt nu beginnen met het uitvoeren van de gadgets:

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

## Volgende stappen
- [Praktijkscenario's waarbij Inspektor Gadget u kan helpen](https://go.microsoft.com/fwlink/p/?linkid=2260402#use-cases)
- [De beschikbare gadgets verkennen](https://go.microsoft.com/fwlink/p/?linkid=2260070)
- [Uw eigen eBPF-programma uitvoeren](https://go.microsoft.com/fwlink/p/?linkid=2259865)
