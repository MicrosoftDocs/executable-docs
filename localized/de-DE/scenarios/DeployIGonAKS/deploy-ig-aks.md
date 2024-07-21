---
title: Bereitstellen von Inspektor Gadget in einem Azure Kubernetes Service-Cluster
description: 'In diesem Tutorial wird gezeigt, wie Inspektor Gadget in einem AKS-Cluster bereitgestellt wird'
author: josebl
ms.author: josebl
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Schnellstart: Bereitstellen von Inspektor Gadget in einem Azure Kubernetes Service-Cluster

[![Bereitstellung in Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262844)

Willkommen zu diesem Tutorial, in dem wir Sie Schritt für Schritt durch die Bereitstellung von [Inspektor Gadget](https://www.inspektor-gadget.io/) in einem Azure Kubernetes Service (AKS) Cluster mit dem kubectl Plugin führen: `gadget`. In diesem Tutorial wird davon ausgegangen, dass Sie bereits bei der Azure CLI angemeldet sind und ein Abonnement ausgewählt haben, das mit der CLI verwendet werden soll.

## Umgebungsvariablen definieren

Der erste Schritt in diesem Tutorial besteht darin, Umgebungsvariablen zu definieren:

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myResourceGroup$RANDOM_ID"
export REGION="eastus"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
```

## Erstellen einer Ressourcengruppe

Eine Ressourcengruppe ist ein Container für zugehörige Ressourcen. Alle Ressourcen müssen in einer Ressourcengruppe platziert werden. In diesem Tutorial erstellen wir eine Ressourcengruppe. Mit dem folgenden Befehl wird eine Ressourcengruppe mit den zuvor definierten Parametern $MY_RESOURCE_GROUP_NAME und $REGION erstellt.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Ergebnisse:

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

## Create AKS Cluster

Erstellen Sie mit dem Befehl az aks create einen AKS-Cluster.

Dieser Vorgang nimmt einige Minuten in Anspruch.

```bash
az aks create \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --name $MY_AKS_CLUSTER_NAME \
  --location $REGION \
  --no-ssh-key
```

## Herstellen einer Verbindung mit dem Cluster

Verwenden Sie zum Verwalten eines Kubernetes-Clusters den Kubernetes-Befehlszeilenclient kubectl. Bei Verwendung von Azure Cloud Shell ist kubectl bereits installiert.

1. Verwenden Sie für die lokale Installation von „az aks CLI“ den Befehl „az aks install-cli“.

    ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
    ```

2. Konfigurieren Sie kubectl mit dem Befehl „az aks get-credentials“, um eine Verbindung mit Ihrem Kubernetes-Cluster herzustellen. Der unten angegebene Befehl bewirkt Folgendes:
    - Herunterladen von Anmeldeinformationen und Konfigurieren der Kubernetes-Befehlszeilenschnittstelle für ihre Verwendung
    - Verwenden von „~/.kube/config“ (Standardspeicherort für die Kubernetes-Konfigurationsdatei). Geben Sie mit dem --file-Argument einen anderen Speicherort für Ihre Kubernetes-Konfigurationsdatei an.

    > [!WARNING]
    > Dadurch werden alle vorhandenen Anmeldeinformationen mit demselben Eintrag überschrieben.

    ```bash
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
    ```

3. Überprüfen Sie die Verbindung mit dem Cluster mithilfe des Befehls kubectl get. Dieser Befehl gibt eine Liste der Clusterknoten zurück.

    ```bash
    kubectl get nodes
    ```

## Installieren von Inspektor Gadget

Die Inspektor Gadget-Installation besteht aus zwei Schritten:

1. Installieren des kubectl-Plug-Ins im System des Benutzers bzw. der Benutzerin.
2. Installieren von Inspektor Gadget im Cluster.

    > [!NOTE]
    > Es gibt zusätzliche Mechanismen für die Bereitstellung und Nutzung von Inspektor Gadget, die jeweils auf bestimmte Anwendungsfälle und Anforderungen zugeschnitten sind. Die Verwendung des `kubectl gadget`-Plug-Ins deckt viele davon ab, aber nicht alle. Beispielsweise hängt die Bereitstellung von Inspektor Gadget mit dem `kubectl gadget`-Plug-In von der Verfügbarkeit des Kubernetes-API-Servers ab. Wenn Sie also nicht von einer solchen Komponente abhängig sein können, da deren Verfügbarkeit manchmal gefährdet sein könnte, dann sollten Sie den `kubectl gadget`-Bereitstellungsmechanismus nicht verwenden. Bitte überprüfen Sie [ig-Dokumentation](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/ig.md), um zu erfahren, was in diesem und anderen Anwendungsfällen zu tun ist.

### Installieren des kubectl-Plug-Ins: `gadget`

Installieren Sie die neueste Version des kubectl-Plug-Ins von der Versionsseite, dekomprimieren und verschieben Sie die ausführbare `kubectl-gadget`-Datei nach `$HOME/.local/bin`:

> [!NOTE]
> Wenn Sie es mit [`krew`](https://sigs.k8s.io/krew) installieren oder aus der Quelle kompilieren möchten, folgen Sie bitte der offiziellen Dokumentation: [Installieren des kubectl-Gadget](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-kubectl-gadget).

```bash
IG_VERSION=$(curl -s https://api.github.com/repos/inspektor-gadget/inspektor-gadget/releases/latest | jq -r .tag_name)
IG_ARCH=amd64
mkdir -p $HOME/.local/bin
export PATH=$PATH:$HOME/.local/bin
curl -sL https://github.com/inspektor-gadget/inspektor-gadget/releases/download/${IG_VERSION}/kubectl-gadget-linux-${IG_ARCH}-${IG_VERSION}.tar.gz  | tar -C $HOME/.local/bin -xzf - kubectl-gadget
```

Überprüfen Sie nun die Installation, indem Sie den Befehl `version` ausführen:

```bash
kubectl gadget version
```

Der Befehl `version` zeigt die Version des Clients (kubectl Gadget-Plug-In) an und weist darauf hin, dass es noch nicht auf dem Server (dem Cluster) installiert ist:

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: not installed$"-->
```text
Client version: vX.Y.Z
Server version: not installed
```

### Installieren von Inspektor Gadget im Cluster

Mit dem folgenden Befehl erstellen Sie das DaemonSet:

> [!NOTE]
> Sie haben mehrere Optionen, um die Bereitstellung anzupassen: Verwendung eines bestimmten Container-Images, Bereitstellung auf bestimmten Knoten und viele andere. Alle Möglichkeiten finden Sie in der offiziellen Dokumentation: [Installation im Cluster](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-in-the-cluster).

```bash
kubectl gadget deploy
```

Überprüfen Sie nun die Installation, indem Sie den Befehl `version` erneut ausführen:

```bash
kubectl gadget version
```

Diesmal wird angezeigt, dass der Client und der Server ordnungsgemäß installiert sind:

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: v\d+\.\d+\.\d+$"-->
```text
Client version: vX.Y.Z
Server version: vX.Y.Z
```

Sie können jetzt mit der Ausführung der Gadgets beginnen:

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

## Nächste Schritte
- [Szenarien in echter Sprache, in denen Inspektor Gadget Ihnen helfen kann](https://go.microsoft.com/fwlink/p/?linkid=2260402#use-cases)
- [Erkunden der verfügbaren Gadgets](https://go.microsoft.com/fwlink/p/?linkid=2260070)
- [Ausführen eines eigenen eBPF-Programms](https://go.microsoft.com/fwlink/p/?linkid=2259865)
