---
title: 'Quickstart: Deploy an AKS cluster with confidential computing Intel SGX agent nodes by using the Azure CLI'
description: Learn how to create an Azure Kubernetes Service (AKS) cluster with enclave confidential containers a Hello World app by using the Azure CLI.
author: angarg05
ms.service: azure-virtual-machines
ms.subservice: azure-confidential-computing
ms.topic: quickstart
ms.date: 11/06/2023
ms.author: ananyagarg
ms.custom: devx-track-azurecli, mode-api, innovation-engine
---

# Quickstart: Deploy an AKS cluster with confidential computing Intel SGX agent nodes by using the Azure CLI

In this quickstart, you'll use the Azure CLI to deploy an Azure Kubernetes Service (AKS) cluster with enclave-aware (DCsv2/DCSv3) VM nodes. You'll then run a simple Hello World application in an enclave.

AKS is a managed Kubernetes service that enables developers or cluster operators to quickly deploy and manage clusters. To learn more, read the AKS introduction and the overview of AKS confidential nodes.

Features of confidential computing nodes include:

- Linux worker nodes supporting Linux containers.
- Generation 2 virtual machine (VM) with Ubuntu 18.04 VM nodes.
- Intel SGX capable CPU to help run your containers in confidentiality protected enclave leveraging Encrypted Page Cache (EPC) memory. For more information, see Frequently asked questions for Azure confidential computing.
- Intel SGX DCAP Driver preinstalled on the confidential computing nodes. For more information, see Frequently asked questions for Azure confidential computing.

> [!NOTE]
> DCsv2/DCsv3 VMs use specialized hardware that's subject to region availability. For more information, see the available SKUs and supported regions.

## Prerequisites

This quickstart requires:

- A minimum of eight DCsv2/DCSv3/DCdsv3 cores available in your subscription.

  By default, there is no pre-assigned quota for Intel SGX VM sizes for your Azure subscriptions. You should follow these instructions to request for VM core quota for your subscriptions.

## Create an AKS cluster with enclave-aware confidential computing nodes and Intel SGX add-on

Use the following instructions to create an AKS cluster with the Intel SGX add-on enabled, add a node pool to the cluster, and verify what you created with a Hello World enclave application.

### Create an AKS cluster with a system node pool and AKS Intel SGX Addon

> [!NOTE]
> If you already have an AKS cluster that meets the prerequisite criteria listed earlier, skip to the next section to add a confidential computing node pool.

Intel SGX AKS Addon "confcom" exposes the Intel SGX device drivers to your containers to avoid added changes to your pod YAML.

First, create a resource group for the cluster by using the `az group create` command.

```bash
export RANDOM_SUFFIX="$(openssl rand -hex 3)"
export RESOURCE_GROUP="myResourceGroup$RANDOM_SUFFIX"
export LOCATION="eastus2"
az group create --name $RESOURCE_GROUP --location $LOCATION
```

Results:

<!-- expected_similarity=0.3 -->

```json
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myResourceGroupxxxxxx",
  "location": "eastus2",
  "managedBy": null,
  "name": "myResourceGroupxxxxxx",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

Now create an AKS cluster with the confidential computing add-on enabled.

```bash
export AKS_CLUSTER="myAKSCluster$RANDOM_SUFFIX"
az aks create -g $RESOURCE_GROUP --name $AKS_CLUSTER --generate-ssh-keys --enable-addons confcom
```

This command deploys a new AKS cluster with a system node pool of non-confidential computing nodes. Confidential computing Intel SGX nodes are not recommended for system node pools.

### Add a user node pool with confidential computing capabilities to the AKS cluster<a id="add-a-user-node-pool-with-confidential-computing-capabilities-to-the-aks-cluster"></a>

Run the following command to add a user node pool of `Standard_DC4s_v3` size with two nodes to the AKS cluster.

```bash
az aks nodepool add --cluster-name $AKS_CLUSTER --name confcompool1 --resource-group $RESOURCE_GROUP --node-vm-size Standard_DC4s_v3 --node-count 2
```

After you run the command, a new node pool with DCsv3 should be visible with confidential computing add-on DaemonSets.

### Verify the node pool and add-on

Get the credentials for your AKS cluster.

```bash
az aks get-credentials --resource-group $RESOURCE_GROUP --name $AKS_CLUSTER
```

Use the `kubectl get pods` command to verify that the nodes are created properly and the SGX-related DaemonSets are running on DCsv3 node pools:

```bash
kubectl get pods --all-namespaces
```

Results:

<!-- expected_similarity=0.3 -->

```text
NAMESPACE     NAME                                 READY   STATUS    RESTARTS   AGE
kube-system   sgx-device-plugin-xxxxx              1/1     Running   0          5m
```

If the output matches the preceding code, your AKS cluster is now ready to run confidential applications.

You can go to the Deploy Hello World from an isolated enclave application section in this quickstart to test an app in an enclave.

## Add a confidential computing node pool to an existing AKS cluster<a id="existing-cluster"></a>

This section assumes you're already running an AKS cluster that meets the prerequisite criteria listed earlier in this quickstart.

### Enable the confidential computing AKS add-on on the existing cluster

To enable the confidential computing add-on, use the `az aks enable-addons` command with the `confcom` add-on, specifying your existing AKS cluster name and resource group.

### Add a DCsv3 user node pool to the cluster
> [!NOTE]
> To use the confidential computing capability, your existing AKS cluster needs to have a minimum of one node pool that's based on a DCsv2/DCsv3 VM SKU. To learn more about DCsv2/DCsv3 VM SKUs for confidential computing, see the available SKUs and supported regions.

To create a node pool, add a new node pool to your existing AKS cluster with the name *confcompool1*. Ensure that this node pool has two nodes and uses the `Standard_DC4s_v3` VM size.

Verify that the new node pool with the name *confcompool1* has been created by listing the node pools in your AKS cluster.

### Verify that DaemonSets are running on confidential node pools

Sign in to your existing AKS cluster to perform the following verification:

```bash
kubectl get nodes
```

Results:

<!-- expected_similarity=0.3 -->

```text
NAME                                STATUS   ROLES   AGE     VERSION
aks-confcompool1-xxxxx-vmss000000   Ready    agent   5m      v1.xx.x
```

You might also see other DaemonSets.

```bash
kubectl get pods --all-namespaces
```

Results:

<!-- expected_similarity=0.3 -->

```text
NAMESPACE     NAME                                 READY   STATUS    RESTARTS   AGE
kube-system   sgx-device-plugin-xxxxx              1/1     Running   0          5m
```

If the output matches the preceding code, your AKS cluster is now ready to run confidential applications.

## Deploy Hello World from an isolated enclave application <a id="deploy-hello-world-from-an-isolated-enclave-application"></a>

You're now ready to deploy a test application.

Create a file named `hello-world-enclave.yaml` and paste in the following YAML manifest. This deployment assumes that you've deployed the *confcom* add-on.

```bash
cat <<EOF > hello-world-enclave.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: oe-helloworld
  namespace: default
spec:
  template:
    metadata:
      labels:
        app: oe-helloworld
    spec:
      containers:
      - name: oe-helloworld
        image: mcr.microsoft.com/acc/samples/oe-helloworld:latest
        resources:
          limits:
            sgx.intel.com/epc: "10Mi"
          requests:
            sgx.intel.com/epc: "10Mi"
        volumeMounts:
        - name: var-run-aesmd
          mountPath: /var/run/aesmd
      restartPolicy: "Never"
      volumes:
      - name: var-run-aesmd
        hostPath:
          path: /var/run/aesmd
  backoffLimit: 0
EOF
```

Now use the `kubectl apply` command to create a sample job that will run in a secure enclave.

```bash
kubectl apply -f hello-world-enclave.yaml
```

Results:

<!-- expected_similarity=0.3 -->

```text
job.batch/oe-helloworld created
```

You can confirm that the workload successfully created a Trusted Execution Environment (enclave) by running the following commands:

```bash
kubectl get jobs -l app=oe-helloworld
```

Results:

<!-- expected_similarity=0.3 -->

```text
NAME            COMPLETIONS   DURATION   AGE
oe-helloworld   1/1           1s         23s
```

```bash
kubectl get pods -l app=oe-helloworld
```

Results:

<!-- expected_similarity=0.3 -->

```text
NAME                 READY   STATUS      RESTARTS   AGE
oe-helloworld-xxxxx  0/1     Completed   0          25s
```

```bash
kubectl logs -l app=oe-helloworld
```

Results:

<!-- expected_similarity=0.3 -->

```text
Hello world from the enclave
Enclave called into host to print: Hello World!
```

If the output matches the preceding code, your application is running successfully in a confidential computing environment.

## Next steps

- Run Python, Node, or other applications through confidential containers using ISV/OSS SGX wrapper software. Review [confidential container samples in GitHub](https://github.com/Azure-Samples/confidential-container-samples).

- Run enclave-aware applications by using the [enclave-aware Azure container samples in GitHub](https://github.com/Azure-Samples/confidential-computing/blob/main/containersamples/).

<!-- LINKS -->
[az-group-create]: /cli/azure/group#az_group_create

[az-aks-create]: /cli/azure/aks#az_aks_create

[az-aks-get-credentials]: /cli/azure/aks#az_aks_get_credentials