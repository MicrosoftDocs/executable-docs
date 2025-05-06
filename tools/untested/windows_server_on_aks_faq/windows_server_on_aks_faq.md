### YamlMime:FAQ
metadata:
  title: "Windows Server on AKS FAQ"
  description: Frequently asked questions about Windows Server containers on Azure Kubernetes Service (AKS).
  keywords: frequently asked questions, faq
  ms.service: azure-kubernetes-service
  ms.topic: faq
  ms.date: 11/06/2023
title: "Frequently asked questions about Windows Server on AKS"
summary: |
    This article provides answers to some of the most common questions about using Windows Server containers on Azure Kubernetes Service (AKS).
  

sections:
  - name: General questions
    questions:
      - question:  |
          Why can't I create new Windows Server 2019 node pools?
        answer:  |
          Windows Server 2019 isn't supported in Kubernetes version 1.33 and above. Use a supported Windows Server version such as Windows Server 2022.

      - question:  |
          Why can't I upgrade my Windows Server 2019 node pools to Kubernetes version 1.33?
        answer:  |
          Windows Server 2019 isn't supported in Kubernetes version 1.33 and above. Use a supported Windows Server version such as Windows Server 2022.

      - question: |
          What kind of disks are supported for Windows?
        answer: |
          Azure Disks and Azure Files are the supported volume types, and are accessed as New Technology File System (NTFS) volumes in the Windows Server container.
          
      - question: |
          Does Windows support generation 2 virtual machines (VMs)?
        answer: |
          Generation 2 VMs are supported on Windows starting with Windows Server 2022.
          
          For more information, see [Support for generation 2 VMs on Azure](/azure/virtual-machines/generation-2).
          
      - question: |
          How do I patch my Windows nodes?
        answer: |
          To get the latest patches for Windows nodes, you can either [upgrade the node pool](./manage-node-pools.md#upgrade-a-single-node-pool) or [upgrade the node image](./node-image-upgrade.md).

      - question: |
          Is preserving the client source IP supported?
        answer: |
          At this time, [client source IP preservation](./concepts-network-ingress.md#ingress-controllers) isn't supported with Windows nodes.

      - question: |
          Can I change the maximum number of pods per node?
        answer: |
          Yes. For more information, see [Maximum number of pods](./concepts-network-ip-address-planning.md#maximum-pods-per-node).
          
      - question: |
          What is the default transmission control protocol (TCP) time-out in Windows OS?
        answer: |
          The default TCP time-out in Windows OS is four minutes. This value isn't configurable. When an application uses a longer time-out, the TCP connections between different containers in the same node close after four minutes.
          
      - question: |
          Why am I seeing an error when I try to create a new Windows agent pool?
        answer: |
          If you created your cluster before February 2020 and didn't perform any upgrade operations, the cluster still uses an old Windows image. You might see an error that resembles the following example:

          "The following list of images referenced from the deployment template isn't found: Publisher: MicrosoftWindowsServer, Offer: WindowsServer, Sku: 2019-datacenter-core-smalldisk-2004, Version: latest. Refer to [Find and use Azure Marketplace Virtual Machine images with Azure PowerShell](/azure/virtual-machines/windows/cli-ps-findimage) for instructions on finding available images."

          To fix this issue, you need to perform the following steps:

          1. Upgrade the [cluster control plane](./manage-node-pools.md#upgrade-a-cluster-control-plane-with-multiple-node-pools), which updates the image offer and publisher.
          2. Create new Windows agent pools.
          3. Move Windows pods from existing Windows agent pools to new Windows agent pools.
          4. Delete old Windows agent pools.

      - question: |
          Why am I seeing an error when I try to deploy Windows pods?
        answer: |
          If you specify a value in `--max-pods` less than the number of pods you want to create, you might see the `No available addresses` error.

          To fix this error, use the `az aks nodepool add` command with a high enough `--max-pods` value. For example:

          ```azurecli
          az aks nodepool add \
              --cluster-name $CLUSTER_NAME \
              --resource-group $RESOURCE_GROUP \
              --name $NODEPOOL_NAME \
              --max-pods 3
          ```

          For more details, see the [`--max-pods` documentation](/cli/azure/aks/nodepool#az-aks-nodepool-add).
          
      - question: |
          Why is there an unexpected user named "sshd" on my virtual machine node?
        answer: |
          AKS adds a user named "sshd" when installing the OpenSSH service. This user isn't malicious. We recommend that customers update their alerts to ignore this unexpected user account.

      - question: |
          How do I rotate the service principal for my Windows node pool?
        answer: |
          Windows node pools don't support service principal rotation. To update the service principal, create a new Windows node pool and migrate your pods from the older pool to the new one. After your pods are migrated to the new pool, delete the older node pool.

          Instead of service principals, you can use managed identities. For more information, see [Use managed identities in AKS](./use-managed-identity.md).

      - question: |
          How do I change the administrator password for Windows Server nodes on my cluster?
        answer: |
          To change the administrator password using the Azure CLI, use the `az aks update` command with the `--admin-password` parameter. For example:

          ```azurecli
          az aks update \
              --resource-group $RESOURCE_GROUP \
              --name $CLUSTER_NAME \
              --admin-password <new-password>
          ```

          To change the password using Azure PowerShell, use the `Set-AzAksCluster` cmdlet with the `-AdminPassword` parameter. For example:
            
            ```azurepowershell
            Set-AzAksCluster `
                -ResourceGroupName $RESOURCE_GROUP `
                -Name $CLUSTER_NAME `
                -AdminPassword <new-password>
            ```

          Keep in mind that performing a cluster update causes a restart and only updates the Windows Server node pools. For information about Windows Server password requirements, see [Windows Server password requirements](/windows/security/threat-protection/security-policy-settings/password-must-meet-complexity-requirements#reference).

      - question: |
          How many node pools can I create?
        answer: |
          AKS clusters with Windows node pools have the same resource limits as the default limits specified for the AKS service. For more information, see [Quotas, virtual machine size restrictions, and region availability in Azure Kubernetes Service (AKS)](./quotas-skus-regions.md).

      - question: |
          Can I run ingress controllers on Windows nodes?
        answer: |
          Yes, you can run ingress controllers that support Windows Server containers.

      - question: |
          Can my Windows Server containers use gMSA?
        answer: |
          Yes. Group-managed service account (gMSA) support is generally available (GA) for Windows on AKS. For more information, see [Enable Group Managed Service Accounts (GMSA) for your Windows Server nodes on your Azure Kubernetes Service (AKS) cluster](./use-group-managed-service-accounts.md)
      - question: |
          Are there any limitations on the number of services on a cluster with Windows nodes?
        answer: |
          A cluster with Windows nodes can have approximately 500 services (sometimes less) before it encounters port exhaustion. This limitation applies to a Kubernetes Service with External Traffic Policy set to "Cluster". 

          When the external traffic policy on a Service is configured as a Cluster, the traffic undergoes an extra Source NAT on the node. This process also results in reservation of a port from the TCPIP dynamic port pool. This port pool is a limited resource (~16K ports by default) and many active connections to a Service can lead to dynamic port pool exhaustion resulting in connection drops.

          If the Kubernetes Service is configured with External Traffic Policy set to "Local", port exhaustion problems aren't likely to occur at 500 services.

      - question: |
          How do I change the time zone of a running container?
        answer: |
          To change the time zone of a running Windows Server container, connect to the running container with a PowerShell session. For example:
    
          ```azurecli
          kubectl exec -it CONTAINER-NAME -- PowerShell
          ```

          In the running container, use [Set-TimeZone](/powershell/module/microsoft.powershell.management/set-timezone) to set the time zone of the running container. For example:

          ```azurepowershell
          Set-TimeZone -Id "Russian Standard Time"
          ```

          To see the current time zone of the running container or an available list of time zones, use [Get-TimeZone](/powershell/module/microsoft.powershell.management/get-timezone).
