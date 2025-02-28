---
title: 'Quickstart: Use the Azure CLI to create a Batch account and run a job'
description: Follow this quickstart to use the Azure CLI to create a Batch account, a pool of compute nodes, and a job that runs basic tasks on the pool.
ms.topic: quickstart
ms.date: 04/12/2023
author: azurecli
ms.author: azurecli
ms.custom: mvc, devx-track-azurecli, mode-api, linux-related-content, innovation-engine
---

# Quickstart: Use the Azure CLI to create a Batch account and run a job

This quickstart shows you how to get started with Azure Batch by using Azure CLI commands and scripts to create and manage Batch resources. You create a Batch account that has a pool of virtual machines (compute nodes). You then create and run a job with tasks that run on the pool nodes.

After you complete this quickstart, you will understand the [key concepts of the Batch service](batch-service-workflow-features.md) and be ready to use Batch with more realistic, larger scale workloads.

## Prerequisites

- [!INCLUDE [quickstarts-free-trial-note](~/reusable-content/ce-skilling/azure/includes/quickstarts-free-trial-note.md)]

- Azure Cloud Shell or Azure CLI.

  You can run the Azure CLI commands in this quickstart interactively in Azure Cloud Shell. To run the commands in Cloud Shell, select **Open Cloudshell** at the upper-right corner of a code block. Select **Copy** to copy the code, and paste it into Cloud Shell to run it. You can also [run Cloud Shell from within the Azure portal](https://shell.azure.com). Cloud Shell always uses the latest version of the Azure CLI.

  Alternatively, you can [install Azure CLI locally](/cli/azure/install-azure-cli) to run the commands. The steps in this article require Azure CLI version 2.0.20 or later. Run [az version](/cli/azure/reference-index?#az-version) to see your installed version and dependent libraries, and run [az upgrade](/cli/azure/reference-index?#az-upgrade) to upgrade. If you use a local installation, ensure you are already signed in to Azure.

>[!NOTE]
>For some regions and subscription types, quota restrictions might cause Batch account or node creation to fail or not complete. In this situation, you can request a quota increase at no charge. For more information, see [Batch service quotas and limits](batch-quota-limit.md).

## Create a resource group

In this section, we create an Azure resource group that will serve as a logical container for all the resources used in this quickstart. To ensure uniqueness, a random suffix is appended to the resource group name. We use the location "centralindia" consistently across all resources.

```bash
export RANDOM_SUFFIX=$(openssl rand -hex 3)
export RESOURCE_GROUP="qsBatch$RANDOM_SUFFIX"
export LOCATION="centralindia"
az group create --name $RESOURCE_GROUP --location $LOCATION
```

<!-- expected_similarity=0.3 -->
```JSON
{
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/qsBatchxxx",
  "location": "centralindia",
  "managedBy": null,
  "name": "qsBatchxxx",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Create a storage account

Next, create an Azure Storage account to be linked with your Batch account. Although this quickstart doesn't directly use the storage account, real-world Batch workloads typically link a storage account to deploy applications and manage data.

```bash
export STORAGE_ACCOUNT="mybatchstorage$RANDOM_SUFFIX"
az storage account create \
    --resource-group $RESOURCE_GROUP \
    --name $STORAGE_ACCOUNT \
    --location $LOCATION \
    --sku Standard_LRS
```

<!-- expected_similarity=0.3 -->
```JSON
{
  "sku": {
    "name": "Standard_LRS"
  },
  "kind": "Storage",
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/qsBatchxxx/providers/Microsoft.Storage/storageAccounts/mybatchstoragexxx",
  "location": "centralindia",
  "name": "mybatchstoragexxx",
  "type": "Microsoft.Storage/storageAccounts",
  "statusOfPrimary": "available"
}
```

## Create a Batch account

Create a Batch account in your resource group and link it with the storage account created earlier. Note that we are using the "centralindia" location to ensure consistency across resources.

```bash
export BATCH_ACCOUNT="mybatchaccount$RANDOM_SUFFIX"
az batch account create \
    --name $BATCH_ACCOUNT \
    --storage-account $STORAGE_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION
```

<!-- expected_similarity=0.3 -->
```JSON
{
  "accountEndpoint": "mybatchaccountxxx.centralindia.batch.azure.com",
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/qsBatchxxx/providers/Microsoft.Batch/batchAccounts/mybatchaccountxxx",
  "location": "centralindia",
  "name": "mybatchaccountxxx",
  "resourceGroup": "qsBatchxxx",
  "type": "Microsoft.Batch/batchAccounts"
}
```

Before proceeding with further Batch operations, sign in to your Batch account so that subsequent commands use the correct account context. A brief delay is introduced to ensure the account has propagated fully.

```bash
az batch account login \
    --name $BATCH_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --shared-key-auth
sleep 30
```

<!-- expected_similarity=0.3 -->
```JSON
{
  "message": "Login to Batch account mybatchaccountxxx in resource group qsBatchxxx was successful."
}
```

## Create a pool of compute nodes

Now, create a pool of Linux compute nodes within your Batch account. In this example, we create a pool with two Standard_A1_v2 VMs running Ubuntu 20.04 LTS. This configuration provides a balance between performance and cost for this quickstart.

```bash
export POOL_ID="myPool$RANDOM_SUFFIX"
az batch pool create \
    --id $POOL_ID \
    --image canonical:0001-com-ubuntu-server-focal:20_04-lts \
    --node-agent-sku-id "batch.node.ubuntu 20.04" \
    --target-dedicated-nodes 2 \
    --vm-size Standard_A1_v2
```

<!-- expected_similarity=0.3 -->
```JSON
{
  "id": "myPoolxxx",
  "allocationState": "resizing",
  "vmSize": "Standard_A1_v2",
  "targetDedicatedNodes": 2,
  "provisioningState": "InProgress"
}
```

Batch immediately begins creating the pool, although it may take a few minutes to allocate and start the compute nodes. To check the pool allocation state reliably and avoid JSON parsing errors, query only the allocationState property:

```bash
az batch pool show --pool-id $POOL_ID --query "allocationState" --output json
```

<!-- expected_similarity=0.3 -->
```JSON
"resizing"
```

## Create a job

Create a Batch job that will run on the pool. A job logically groups one or more tasks and specifies common settings such as the target pool.

```bash
export JOB_ID="myJob$RANDOM_SUFFIX"
az batch job create \
    --id $JOB_ID \
    --pool-id $POOL_ID
```

<!-- expected_similarity=0.3 -->
```JSON
{
  "id": "myJobxxx",
  "poolInfo": {
    "poolId": "myPoolxxx"
  },
  "priority": 0,
  "onAllTasksComplete": "noAction"
}
```

## Create job tasks

Batch provides several methods to deploy applications and scripts to compute nodes. In the following loop, four parallel tasks (named myTask1 through myTask4) are created. Each task runs a command that prints Batch environment variables on the compute node and then waits for 90 seconds.

```bash
for i in {1..4}
do
   az batch task create \
    --task-id myTask$i \
    --job-id $JOB_ID \
    --command-line "/bin/bash -c 'printenv | grep AZ_BATCH; sleep 90s'"
done
```

Each task's output will display the environment settings specific to the node where it is executed.

## View task status

After creating the tasks, they are queued for execution. When a compute node becomes available, the task will run. Use the following command to view the status of a specific task (for example, myTask1):

```bash
az batch task show \
    --job-id $JOB_ID \
    --task-id myTask1
```

<!-- expected_similarity=0.3 -->
```JSON
{
  "id": "myTask1",
  "state": "active",
  "executionInfo": {
    "startTime": "2023-xx-xxTxx:xx:xxZ",
    "endTime": null,
    "retryCount": 0,
    "exitCode": null
  },
  "nodeInfo": {
    "nodeId": "tvm-xxxxxxxx"
  }
}
```

An exitCode of 0 in the output indicates that the task completed successfully. The nodeId property indicates the compute node where the task ran.

## View task output

To display the file output generated by a task on a compute node, list the files produced by the task. In the following example, the files generated by myTask1 are listed:

```bash
az batch task file list \
    --job-id $JOB_ID \
    --task-id myTask1 \
    --output table
```

<!-- expected_similarity=0.3 -->
```JSON
[
  {
    "Name": "stdout.txt",
    "URL": "https://mybatchaccountxxx.centralindia.batch.azure.com/jobs/myJobxxx/tasks/myTask1/files/stdout.txt",
    "Is Directory": false,
    "Content Length": 695
  },
  {
    "Name": "certs",
    "URL": "https://mybatchaccountxxx.centralindia.batch.azure.com/jobs/myJobxxx/tasks/myTask1/files/certs",
    "Is Directory": true
  },
  {
    "Name": "wd",
    "URL": "https://mybatchaccountxxx.centralindia.batch.azure.com/jobs/myJobxxx/tasks/myTask1/files/wd",
    "Is Directory": true
  },
  {
    "Name": "stderr.txt",
    "URL": "https://mybatchaccountxxx.centralindia.batch.azure.com/jobs/myJobxxx/tasks/myTask1/files/stderr.txt",
    "Is Directory": false,
    "Content Length": 0
  }
]
```

To download the standard output file (stdout.txt) to your local directory, run the following command:

```bash
az batch task file download \
    --job-id $JOB_ID \
    --task-id myTask1 \
    --file-path stdout.txt \
    --destination ./stdout.txt
```

You can then open the downloaded stdout.txt in a text editor. Typically, the file contains the Batch environment variables set on the compute node, such as:

```text
AZ_BATCH_TASK_DIR=/mnt/batch/tasks/workitems/myJob/job-1/myTask1
AZ_BATCH_NODE_STARTUP_DIR=/mnt/batch/tasks/startup
AZ_BATCH_CERTIFICATES_DIR=/mnt/batch/tasks/workitems/myJob/job-1/myTask1/certs
AZ_BATCH_ACCOUNT_URL=https://mybatchaccountxxx.centralindia.batch.azure.com/
AZ_BATCH_TASK_WORKING_DIR=/mnt/batch/tasks/workitems/myJob/job-1/myTask1/wd
AZ_BATCH_NODE_SHARED_DIR=/mnt/batch/tasks/shared
AZ_BATCH_TASK_USER=_azbatch
AZ_BATCH_NODE_ROOT_DIR=/mnt/batch/tasks
AZ_BATCH_JOB_ID=myJobxxx
AZ_BATCH_NODE_IS_DEDICATED=true
AZ_BATCH_NODE_ID=tvm-xxxxxxxx_2-20180703t215033z
AZ_BATCH_POOL_ID=myPoolxxx
AZ_BATCH_TASK_ID=myTask1
AZ_BATCH_ACCOUNT_NAME=mybatchaccountxxx
AZ_BATCH_TASK_USER_IDENTITY=PoolNonAdmin
```

## Clean up resources

If you want to continue with Batch tutorials and samples, you can keep the Batch account and linked storage account that you created in this quickstart. There is no charge for the Batch account itself. Pools and nodes do incur charges while running, even if no jobs are active. To avoid accidental deletions during automated execution, deletion commands have been removed from this document. When you no longer need these resources, please delete the resource group and its related resources manually.

## Next steps

In this quickstart, you created a Batch account and a compute pool, created and ran a Batch job with tasks, and viewed task outputs generated on the compute nodes. Now that you understand the key concepts of the Batch service, you're ready to use Batch for more realistic, larger scale workloads. To dive deeper into Azure Batch, continue with the Batch tutorials.

> [!div class="nextstepaction"]
> [Tutorial: Run a parallel workload with Azure Batch](./tutorial-parallel-python.md)