---
title: Tutorial - Configure dynamic inventories for Azure Virtual Machines using Ansible
description: Learn how to populate your Ansible inventory dynamically from information in Azure
keywords: ansible, azure, devops, bash, cloudshell, dynamic inventory
ms.topic: tutorial
ms.date: 08/14/2024
ms.custom: devx-track-ansible, devx-track-azurecli, devx-track-azurepowershell, linux-related-content
author: ansibleexpert
ms.author: ansibleexpert
---

# Tutorial: Configure dynamic inventories of your Azure resources using Ansible

[!INCLUDE [ansible-28-note.md](includes/ansible-28-note.md)]

Before you begin, ensure that your environment has Ansible installed.

Set the following environment variables. These declarations ensure unique resource names and provide needed configuration so that the Exec Doc runs non-interactively.

```bash
export RANDOM_SUFFIX=$(openssl rand -hex 3)
export RESOURCE_GROUP="ansibleinventorytestrg${RANDOM_SUFFIX}"
export REGION="centralindia"
export ADMIN_PASSWORD="P@ssw0rd123!"
```

The [Ansible dynamic inventory](https://docs.ansible.com/ansible/latest/user_guide/intro_dynamic_inventory.html) feature removes the burden of maintaining static inventory files.

In this tutorial, you use Azure's dynamic-inventory plug-in to populate your Ansible inventory.

In this article, you learn how to:

> [!div class="checklist"]
> * Configure two test virtual machines.
> * Add tags to Azure virtual machines.
> * Generate a dynamic inventory.
> * Use conditional and keyed groups to populate group memberships.
> * Run playbooks against groups within the dynamic inventory.

## Prerequisites

[!INCLUDE [open-source-devops-prereqs-azure-subscription.md](../includes/open-source-devops-prereqs-azure-subscription.md)]
[!INCLUDE [open-source-devops-prereqs-create-service-principal.md](../includes/open-source-devops-prereqs-create-service-principal.md)]
[!INCLUDE [ansible-prereqs-cloudshell-use-or-vm-creation2.md](includes/ansible-prereqs-cloudshell-use-or-vm-creation2.md)]

## Create Azure VMs

1. Sign in to the [Azure portal](https://go.microsoft.com/fwlink/p/?LinkID=525040).

2. Open [Cloud Shell](/azure/cloud-shell/overview).

3. Create an Azure resource group to hold the virtual machines for this tutorial.

    > [!IMPORTANT]
    > The Azure resource group you create in this step must have a name that is entirely lower-case. Otherwise, the generation of the dynamic inventory will fail.

    # [Azure CLI](#tab/azure-cli)
    ```azurecli-interactive
    az group create --resource-group $RESOURCE_GROUP --location $REGION
    ```
    # [Azure PowerShell]
    ```azurepowershell
    New-AzResourceGroup -Name $RESOURCE_GROUP -Location $REGION
    ```

4. Create two virtual machines on Azure using one of the following techniques:

    - **Ansible playbook** – The articles [Create a basic Linux virtual machine in Azure with Ansible](./vm-configure.md) and [Create a basic Windows virtual machine in Azure with Ansible](./vm-configure-windows.md) illustrate how to create a virtual machine from an Ansible playbook.

    - **Azure CLI** – Issue each of the following commands in Cloud Shell to create the two virtual machines. Note that the --size parameter is provided to avoid unavailable SKU errors.
    
        # [Azure CLI](#tab/azure-cli)
        ```azurecli-interactive
        az vm create \
          --resource-group $RESOURCE_GROUP \
          --name win-vm \
          --image MicrosoftWindowsServer:WindowsServer:2019-Datacenter:latest \
          --size Standard_B1s \
          --admin-username azureuser \
          --admin-password $ADMIN_PASSWORD

        az vm create \
          --resource-group $RESOURCE_GROUP \
          --name linux-vm \
          --image Ubuntu2204 \
          --size Standard_B1s \
          --admin-username azureuser \
          --admin-password $ADMIN_PASSWORD
        ```
    
        # [Azure PowerShell]
        ```azurepowershell
        $adminUsername = "azureuser"
        $adminPassword = ConvertTo-SecureString $env:ADMIN_PASSWORD -AsPlainText -Force
        $credential = New-Object System.Management.Automation.PSCredential ($adminUsername, $adminPassword);

        New-AzVM `
          -ResourceGroupName $RESOURCE_GROUP `
          -Location $REGION `
          -Image MicrosoftWindowsServer:WindowsServer:2019-Datacenter:latest `
          -Name win-vm `
          -Size Standard_B1s `
          -OpenPorts 3389 `
          -Credential $credential

        New-AzVM `
          -ResourceGroupName $RESOURCE_GROUP `
          -Location $REGION `
          -Image Ubuntu2204 `
          -Name linux-vm `
          -Size Standard_B1s `
          -OpenPorts 22 `
          -Credential $credential
        ```
        (Replace any password placeholders with the variable ADMIN_PASSWORD.)

## Add application role tags

Tags are used to organize and categorize Azure resources. Assigning the Azure VMs an application role allows you to use the tags as group names within the Azure dynamic inventory.

Run the following commands to update the VM tags:

# [Azure CLI](#tab/azure-cli)
```azurecli-interactive
az vm update \
  --resource-group $RESOURCE_GROUP \
  --name linux-vm \
  --set tags.applicationRole='message-broker'

az vm update \
  --resource-group $RESOURCE_GROUP \
  --name win-vm \
  --set tags.applicationRole='web-server'
```

# [Azure PowerShell]
```azurepowershell
Update-AzVM -VM (Get-AzVM -Name win-vm -ResourceGroupName $RESOURCE_GROUP) -Tag @{applicationRole="web-server"}
Update-AzVM -VM (Get-AzVM -Name linux-vm -ResourceGroupName $RESOURCE_GROUP) -Tag @{applicationRole="message-broker"}
```

Learn more about Azure tagging strategies at [Define your tagging strategy](/azure/cloud-adoption-framework/ready/azure-best-practices/resource-tagging).

## Generate a dynamic inventory

Ansible provides an [Azure dynamic-inventory plug-in](https://github.com/ansible/ansible/blob/stable-2.9/lib/ansible/plugins/inventory/azure_rm.py). 

The following steps walk you through using the plug-in:

1. Create a dynamic inventory named "myazure_rm.yml" with the basic configuration.

```bash
cat <<EOF > myazure_rm.yml
plugin: azure_rm
include_vm_resource_groups:
  - ${RESOURCE_GROUP}
auth_source: auto
EOF
```

2. Run the following command to query the VMs within the resource group.

```bash
ansible-inventory -i myazure_rm.yml --graph
```

Results:

<!-- expected_similarity=0.3 -->
```text
@all:
  |--@ungrouped:
      |--linux-vm_abc123
      |--win-vm_def456
```

## Find Azure VM hostvars

Run the following command to view all the hostvars:

```bash
ansible-inventory -i myazure_rm.yml --list
```

Results:

<!-- expected_similarity=0.3 -->
```json
{
  "_meta": {
    "hostvars": {
      "linux-vm_abc123": {
         "ansible_host": "x.x.x.x"
      },
      "win-vm_def456": {
         "ansible_host": "x.x.x.x"
      }
    }
  }
}
```

## Assign group membership with conditional_groups

Each conditional group is made of two parts: the name of the group and the condition for adding a member to the group.

Use the property image.offer to create conditional group membership for the linux-vm.

Open the myazure_rm.yml dynamic inventory and update it to include the following conditional_groups section. This overwrites the previous file.

```bash
cat <<EOF > myazure_rm.yml
plugin: azure_rm
include_vm_resource_groups:
  - ${RESOURCE_GROUP}
auth_source: auto
conditional_groups:
  linux: "'ubuntu' in image.offer"
  windows: "'WindowsServer' in image.offer"
EOF
```

Run the ansible-inventory command with the --graph option:

```bash
ansible-inventory -i myazure_rm.yml --graph
```

Results:

<!-- expected_similarity=0.3 -->
```text
@all:
  |--@linux:
      |--linux-vm_abc123
  |--@ungrouped:
  |--@windows:
      |--win-vm_def456
```

From the output, you can see the VMs are no longer associated with the "ungrouped" group. Instead, each VM is assigned to a new group created by the dynamic inventory.

## Assign group membership with keyed_groups

Keyed groups assign group membership in a similar manner as conditional groups, but the group name is dynamically populated based on the resource tag.

Update the myazure_rm.yml dynamic inventory to include the keyed_groups section. This overwrites the previous file.

```bash
cat <<EOF > myazure_rm.yml
plugin: azure_rm
include_vm_resource_groups:
  - ${RESOURCE_GROUP}
auth_source: auto
conditional_groups:
  linux: "'ubuntu' in image.offer"
  windows: "'WindowsServer' in image.offer"
keyed_groups:
  - key: tags.applicationRole
EOF
```

Run the ansible-inventory command with the --graph option:

```bash
ansible-inventory -i myazure_rm.yml --graph
```

Results:

<!-- expected_similarity=0.3 -->
```text
@all:
  |--@_message_broker:
      |--linux-vm_abc123
  |--@_web_server:
      |--win-vm_def456
  |--@linux:
      |--linux-vm_abc123
  |--@ungrouped:
  |--@windows:
      |--win-vm_def456
```

From the output, you see two more groups _message_broker and _web_server. By using a keyed group, the applicationRole tag populates the group names and group memberships.

## Run playbooks with group name patterns

Use the groups created by the dynamic inventory to target subgroups.

1. Create a playbook called win_ping.yml with the following contents. Predefined variables are provided so that no interactive prompts occur.

```bash
cat <<EOF > win_ping.yml
---
- hosts: windows
  gather_facts: false

  vars:
    username: "azureuser"
    password: "${ADMIN_PASSWORD}"
    ansible_user: "{{ username }}"
    ansible_password: "{{ password }}"
    ansible_connection: winrm
    ansible_winrm_transport: ntlm
    ansible_winrm_server_cert_validation: ignore

  tasks:
    - name: run win_ping
      win_ping:
EOF
```

2. Run the win_ping.yml playbook.

```bash
ansible-playbook win_ping.yml -i myazure_rm.yml
```

Results:

<!-- expected_similarity=0.3 -->
```text
PLAY [windows] *************************************************************

TASK [run win_ping] *******************************************************
ok: [win-vm_def456]

PLAY RECAP ***************************************************************
win-vm_def456              : ok=1    changed=0    unreachable=0    failed=0
```

If you get the error "winrm or requests is not installed: No module named 'winrm'", install pywinrm with the following command:

```bash
pip install "pywinrm>=0.3.0"
```

3. Create a second playbook named ping.yml with the following contents. Predefined variables are provided so that no interactive prompts occur.

```bash
cat <<EOF > ping.yml
---
- hosts: all
  gather_facts: false

  vars:
    username: "azureuser"
    password: "${ADMIN_PASSWORD}"
    ansible_user: "{{ username }}"
    ansible_password: "{{ password }}"
    ansible_ssh_common_args: '-o StrictHostKeyChecking=no'

  tasks:
    - name: run ping
      ping:
EOF
```

4. Run the ping.yml playbook.

```bash
ansible-playbook ping.yml -i myazure_rm.yml
```

Results:

<!-- expected_similarity=0.3 -->
```text
PLAY [all] *************************************************************
TASK [run ping] *******************************************************
ok: [linux-vm_abc123]

PLAY RECAP *************************************************************
linux-vm_abc123            : ok=1    changed=0    unreachable=0    failed=0
```

## Clean up resources

(Note: In Exec Docs, deletion commands that remove resources are omitted to prevent accidental deletion during automated execution.)

---

## Next steps

> [!div class="nextstepaction"]
> [Quickstart: Configure Linux virtual machines in Azure using Ansible](./vm-configure.md)