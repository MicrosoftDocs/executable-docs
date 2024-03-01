---
title: 在 Azure Kubernetes 服务群集中部署 Inspektor Gadget
description: 本教程演示如何在 AKS 群集中部署 Inspektor Gadget
author: josebl
ms.author: josebl
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# 快速入门：在 Azure Kubernetes 服务群集中部署 Inspektor Gadget

欢迎查看本教程，其中我们将逐步介绍如何使用 kubectl 插件 `gadget` 在 Azure Kubernetes 服务 (AKS) 群集中部署 [Inspektor Gadget](https://www.inspektor-gadget.io/)。 本教程假定你已登录到 Azure CLI，并已选择要与 CLI 一起使用的订阅。

## 定义环境变量

本教程的第一步是定义环境变量：

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myResourceGroup$RANDOM_ID"
export REGION="eastus"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
```

## 创建资源组

资源组是相关资源的容器。 所有资源都必须在资源组中部署。 我们将为本教程创建一个资源组。 以下命令创建具有前面定义的 $MY_RESOURCE_GROUP_NAME 和 $REGION 参数的资源组。

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

结果：

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

## 创建 AKS 群集

使用 az aks create 命令创建 AKS 群集。

这需要几分钟时间。

```bash
az aks create \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --name $MY_AKS_CLUSTER_NAME \
  --location $REGION \
  --no-ssh-key
```

## 连接到群集

若要管理 Kubernetes 群集，请使用 Kubernetes 命令行客户端 kubectl。 如果使用的是 Azure Cloud Shell，则 kubectl 已安装。

1. 使用 az aks install-cli 命令在本地安装 az aks CLI

    ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
    ```

2. 使用 az aks get-credentials 命令将 kubectl 配置为连接到 Kubernetes 群集。 以下命令：
    - 下载凭据，并将 Kubernetes CLI 配置为使用这些凭据。
    - 使用 ~/.kube/config，这是 Kubernetes 配置文件的默认位置。 使用 --file 参数指定 Kubernetes 配置文件的其他位置。

    > [!WARNING]
    > 这将覆盖具有相同条目的任何现有凭据

    ```bash
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
    ```

3. 使用 kubectl get 命令验证与群集之间的连接。 此命令将返回群集节点的列表。

    ```bash
    kubectl get nodes
    ```

## 安装 Inspektor Gadget

Inspektor Gadget 安装分两步进行：

1. 在用户的系统中安装 kubectl 插件。
2. 在群集中安装 Inspektor Gadget。

    > [!NOTE]
    > 还有其他机制可用于部署和使用 Inspektor Gadget，每种机制都是针对特定用例和要求定制的。 使用 `kubectl gadget` 插件可涵盖其中许多场景，但并非全部。 例如，使用 `kubectl gadget` 插件部署 Inspektor Gadget 取决于 Kubernetes API 服务器的可用性。 因此，如果由于此类组件有时可能遭到入侵而不能依赖它们，则建议不要使用 `kubectl gadget` 部署机制。 请查看 [ig 文档](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/ig.md)，了解在该用例和其他用例中的做法。

### 安装 kubectl 插件：`gadget`

从发布页安装最新版本的 kubectl 插件，取消压缩，并将 `kubectl-gadget` 可执行文件移动到 `$HOME/.local/bin`：

> [!NOTE]
> 如果要使用 [`krew`](https://sigs.k8s.io/krew) 安装它或从源进行编译，请遵循官方文档：[安装 kubectl gadget](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-kubectl-gadget)。

```bash
IG_VERSION=$(curl -s https://api.github.com/repos/inspektor-gadget/inspektor-gadget/releases/latest | jq -r .tag_name)
IG_ARCH=amd64
mkdir -p $HOME/.local/bin
export PATH=$PATH:$HOME/.local/bin
curl -sL https://github.com/inspektor-gadget/inspektor-gadget/releases/download/${IG_VERSION}/kubectl-gadget-linux-${IG_ARCH}-${IG_VERSION}.tar.gz  | tar -C $HOME/.local/bin -xzf - kubectl-gadget
```

现在，让我们运行 `version` 命令来验证安装：

```bash
kubectl gadget version
```

`version` 命令将显示客户端的版本（kubectl gadget 插件），并显示它尚未安装在服务器（群集）：

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: not installed$"-->
```text
Client version: vX.Y.Z
Server version: not installed
```

### 在群集中安装 Inspektor Gadget

以下命令将部署 DaemonSet：

> [!NOTE]
> 有多个选项可用来自定义部署：使用特定的容器映像、部署到特定节点等等。 若要全部了解，请查看官方文档：[在群集中安装](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-in-the-cluster)。

```bash
kubectl gadget deploy
```

现在，让我们再次运行 `version` 命令来验证安装：

```bash
kubectl gadget version
```

这一次，客户端和服务器将正确安装：

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: v\d+\.\d+\.\d+$"-->
```text
Client version: vX.Y.Z
Server version: vX.Y.Z
```

现在可以开始运行小工具：

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

## 后续步骤
- [Inspektor Gadget 可为你提供帮助的真实场景](https://go.microsoft.com/fwlink/p/?linkid=2260402#use-cases)
- [探索可用的小工具](https://go.microsoft.com/fwlink/p/?linkid=2260070)
- [运行自己的 eBPF 程序](https://go.microsoft.com/fwlink/p/?linkid=2259865)
