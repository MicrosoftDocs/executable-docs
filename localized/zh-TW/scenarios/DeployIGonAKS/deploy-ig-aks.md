---
title: 在 Azure Kubernetes Service 叢集中部署 Inspektor 小工具
description: 本教學課程示範如何在 AKS 叢集中部署 Inspektor 小工具
author: josebl
ms.author: josebl
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# 快速入門：在 Azure Kubernetes Service 叢集中部署 Inspektor 小工具

[![部署至 Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262844)

歡迎使用本教學課程 [，在 Azure Kubernetes Service （AKS） 叢集中部署 Inspektor 小工具](https://www.inspektor-gadget.io/) 與 kubectl 外掛程式： `gadget`。 本教學課程假設您已登入 Azure CLI，並已選取要搭配 CLI 使用的訂用帳戶。

## 定義環境變數

本教學課程的第一個步驟是定義環境變數：

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myResourceGroup$RANDOM_ID"
export REGION="eastus"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
```

## 建立資源群組

資源群組是相關資源的容器。 所有資源都必須放置在資源群組中。 我們將為此教學課程建立一個。 下列命令會使用先前定義的 $MY_RESOURCE_GROUP_NAME 和 $REGION 參數來建立資源群組。

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

結果：

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

## 建立 AKS 叢集

使用 az aks create 命令來建立 AKS 叢集。

這需要幾分鐘的時間。

```bash
az aks create \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --name $MY_AKS_CLUSTER_NAME \
  --location $REGION \
  --no-ssh-key
```

## 連線至叢集

若要管理 Kubernetes 叢集，請使用 Kubernetes 命令列用戶端 kubectl。 如果您使用 Azure Cloud Shell，則已安裝 kubectl。

1. 使用 az aks install-cli 命令在本機安裝 az aks CLI

    ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
    ```

2. 將 kubectl 設定為使用 az aks get-credentials 命令連線到 Kubernetes 叢集。 下列命令：
    - 下載憑證並設定 Kubernetes CLI 以供使用。
    - 使用 ~/.kube/config，這是 Kubernetes 組態檔的預設位置。 使用 --file 引數，為您的 Kubernetes 組態檔指定不同的位置。

    > [!WARNING]
    > 這會以相同的專案覆寫任何現有的認證

    ```bash
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
    ```

3. 使用 kubectl get nodes 命令來確認與叢集的連線。 此命令會傳回叢集節點的清單。

    ```bash
    kubectl get nodes
    ```

## 安裝 Inspektor 小工具

Inspektor 小工具安裝是由兩個步驟所組成：

1. 在用戶的系統中安裝 kubectl 外掛程式。
2. 在叢集中安裝 Inspektor 小工具。

    > [!NOTE]
    > 有額外的機制可用來部署和使用 Inspektor 小工具，每個機制都針對特定使用案例和需求量身打造。 `kubectl gadget`使用外掛程式涵蓋許多外掛程式，但並非全部。 例如，使用 `kubectl gadget` 外掛程式部署 Inspektor 小工具取決於 Kubernetes API 伺服器的可用性。 因此，如果您無法依賴這類元件，因為其可用性有時會遭到入侵，則建議不要使用 `kubectl gadget`部署機制。 請檢查 [ig 檔](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/ig.md) 以瞭解該怎麼做，以及其他使用案例。

### 安裝 kubectl 外掛程式： `gadget`

從發行頁面安裝最新版本的 kubectl 外掛程式，解壓縮可執行檔， `kubectl-gadget` 並將可執行檔案移至 `$HOME/.local/bin`：

> [!NOTE]
> 如果您想要使用 [`krew`](https://sigs.k8s.io/krew) 或從來源進行編譯，請遵循官方文件：[安裝 kubectl 小工具。](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-kubectl-gadget)

```bash
IG_VERSION=$(curl -s https://api.github.com/repos/inspektor-gadget/inspektor-gadget/releases/latest | jq -r .tag_name)
IG_ARCH=amd64
mkdir -p $HOME/.local/bin
export PATH=$PATH:$HOME/.local/bin
curl -sL https://github.com/inspektor-gadget/inspektor-gadget/releases/download/${IG_VERSION}/kubectl-gadget-linux-${IG_ARCH}-${IG_VERSION}.tar.gz  | tar -C $HOME/.local/bin -xzf - kubectl-gadget
```

現在，讓我們執行 `version` 命令來確認安裝：

```bash
kubectl gadget version
```

此命令 `version` 會顯示用戶端版本（kubectl 小工具外掛程式），並顯示尚未安裝在伺服器中 （叢集）：

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: not installed$"-->
```text
Client version: vX.Y.Z
Server version: not installed
```

### 在叢集中安裝 Inspektor 小工具

下列命令會部署 DaemonSet：

> [!NOTE]
> 有數個選項可用來自定義部署：使用特定的容器映像、部署到特定節點，以及其他許多選項。 若要瞭解所有內容，請查看官方檔： [在叢集中](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-in-the-cluster)安裝。

```bash
kubectl gadget deploy
```

現在，讓我們再次執行 `version` 命令來確認安裝：

```bash
kubectl gadget version
```

這次，客戶端和伺服器將會正確安裝：

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: v\d+\.\d+\.\d+$"-->
```text
Client version: vX.Y.Z
Server version: vX.Y.Z
```

您現在可以開始執行小工具：

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

## 後續步驟
- [Inspektor 小工具可協助您的實際案例](https://go.microsoft.com/fwlink/p/?linkid=2260402#use-cases)
- [探索可用的小工具](https://go.microsoft.com/fwlink/p/?linkid=2260070)
- [執行您自己的 eBPF 程式](https://go.microsoft.com/fwlink/p/?linkid=2259865)
