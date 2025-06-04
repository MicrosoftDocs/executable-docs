---
title: 'TCP 10250 I/O timeout errors when connecting to a node''s Kubelet for log retrieval'
description: Learn how to troubleshoot TCP 10250 I/O timeout errors that occur when retrieving kubectl logs from a pod in an Azure Kubernetes Service (AKS) cluster.
ms.topic: article
ms.date: 09/19/2024
author: ''
ms.author: ''
ms.custom: sap:Connectivity, innovation-engine
---

# 10250 I/O timeouts error when running kubectl log command

TCP timeouts can be caused by blockages of internal traffic that runs between nodes. To investigate TCP time-outs, verify that this traffic isn't being blocked, for example, by [network security groups](/azure/aks/concepts-security#azure-network-security-groups) (NSGs) on the subnet for your cluster nodes.

## Symptoms
Tunnel functionalities, such as `kubectl logs` and code execution, work only for pods that are hosted on nodes on which tunnel service pods are deployed. Pods on other nodes that have no tunnel service pods cannot reach to the tunnel. When viewing the logs of these pods, you receive the following error message:

```bash
kubectl logs <pod>
```

Results:

<!-- expected_similarity=0.3 -->

```output
Error from server: Get "https://aks-agentpool-xxxxxxxxx-vmssxxxxxxxxx:10250/containerLogs/vsm-mba-prod/mba-api-app-xxxxxxxxxx/technosvc": dial tcp <IP-Address>:10250: i/o timeout
```

## Solution

To resolve this issue, allows traffic on port 10250 as described in this [article](tunnel-connectivity-issues.md).

[!INCLUDE [Azure Help Support](../../../includes/azure-help-support.md)]
