---
title: Create a Linux virtual machines in Azure using Ansible
description: Learn how to create a Linux virtual machine in Azure using Ansible
keywords: ansible, azure, devops, virtual machine
ms.topic: tutorial
ms.date: 08/14/2024
ms.custom: devx-track-ansible, linux-related-content, innovation-engine
author: <your GitHub username>
ms.author: <your GitHub username>
---

# Create a Linux virtual machines in Azure using Ansible

This article presents a sample Ansible playbook for configuring a Linux virtual machine.

In this article, you learn how to:

> [!div class="checklist"]
> * Create a resource group
> * Create a virtual network
> * Create a public IP address
> * Create a network security group
> * Create a virtual network interface card
> * Create a virtual machine

## Configure your environment

- **Azure subscription**: If you don't have an Azure subscription, create a [free account](https://azure.microsoft.com/free/?ref=microsoft.com&utm_source=microsoft.com&utm_medium=docs&utm_campaign=visualstudio) before you begin.
- **Install Ansible**: Do one of the following options:

    - [Install](/azure/ansible/ansible-install-configure#install-ansible-on-an-azure-linux-virtual-machine) and [configure](/azure/ansible/ansible-install-configure#create-azure-credentials) Ansible on a Linux virtual machine
    - [Configure Azure Cloud Shell](/azure/cloud-shell/quickstart)

## Implement the Ansible playbook

1. Create a directory in which to test and run the sample Ansible code and make it the current directory.

2. Create a file named main.yml and insert the following code. In the playbook below the resource group name and other relevant properties use environment variables so that they are unique for each run. 

```bash
export RANDOM_SUFFIX=$(openssl rand -hex 3)
export REGION="eastus2"
export MY_RESOURCE_GROUP="myResourceGroup$RANDOM_SUFFIX"
export MY_VM_NAME="myVM$RANDOM_SUFFIX"
export MY_VNET_NAME="myVnet$RANDOM_SUFFIX"
export MY_SUBNET_NAME="mySubnet$RANDOM_SUFFIX"
export MY_NIC_NAME="myNIC$RANDOM_SUFFIX"
export MY_PUBLIC_IP_NAME="myPublicIP$RANDOM_SUFFIX"
export MY_NSG_NAME="myNetworkSecurityGroup$RANDOM_SUFFIX"

cat > main.yml <<'EOF'
- name: Create Azure VM
  hosts: localhost
  connection: local
  tasks:
  - name: Create resource group
    azure_rm_resourcegroup:
      name: "{{ lookup('env', 'MY_RESOURCE_GROUP') }}"
      location: "{{ lookup('env', 'REGION') }}"
  - name: Create virtual network
    azure_rm_virtualnetwork:
      resource_group: "{{ lookup('env', 'MY_RESOURCE_GROUP') }}"
      name: "{{ lookup('env', 'MY_VNET_NAME') }}"
      address_prefixes: "10.0.0.0/16"
  - name: Add subnet
    azure_rm_subnet:
      resource_group: "{{ lookup('env', 'MY_RESOURCE_GROUP') }}"
      name: "{{ lookup('env', 'MY_SUBNET_NAME') }}"
      address_prefix: "10.0.1.0/24"
      virtual_network: "{{ lookup('env', 'MY_VNET_NAME') }}"
  - name: Create public IP address
    azure_rm_publicipaddress:
      resource_group: "{{ lookup('env', 'MY_RESOURCE_GROUP') }}"
      allocation_method: Static
      name: "{{ lookup('env', 'MY_PUBLIC_IP_NAME') }}"
    register: output_ip_address
  - name: Public IP of VM
    debug:
      msg: "The public IP is {{ output_ip_address.state.ip_address }}."
  - name: Create Network Security Group that allows SSH
    azure_rm_securitygroup:
      resource_group: "{{ lookup('env', 'MY_RESOURCE_GROUP') }}"
      name: "{{ lookup('env', 'MY_NSG_NAME') }}"
      rules:
        - name: SSH
          protocol: Tcp
          destination_port_range: 22
          access: Allow
          priority: 1001
          direction: Inbound
  - name: Create virtual network interface card
    azure_rm_networkinterface:
      resource_group: "{{ lookup('env', 'MY_RESOURCE_GROUP') }}"
      name: "{{ lookup('env', 'MY_NIC_NAME') }}"
      virtual_network: "{{ lookup('env', 'MY_VNET_NAME') }}"
      subnet_name: "{{ lookup('env', 'MY_SUBNET_NAME') }}"
      security_group: "{{ lookup('env', 'MY_NSG_NAME') }}"
      ip_configurations:
        - name: ipconfig1
          public_ip_address_name: "{{ lookup('env', 'MY_PUBLIC_IP_NAME') }}"
          primary: yes
  - name: Create VM
    azure_rm_virtualmachine:
      resource_group: "{{ lookup('env', 'MY_RESOURCE_GROUP') }}"
      name: "{{ lookup('env', 'MY_VM_NAME') }}"
      vm_size: Standard_DS1_v2
      admin_username: azureuser
      ssh_password_enabled: false
      generate_ssh_keys: yes  # This will automatically generate keys if they don't exist
      network_interfaces: "{{ lookup('env', 'MY_NIC_NAME') }}"
      image:
        offer: 0001-com-ubuntu-server-jammy
        publisher: Canonical
        sku: 22_04-lts
        version: latest
EOF
```

## Run the playbook

Run the Ansible playbook using the ansible-playbook command.

```bash
ansible-playbook main.yml
```

## Verify the results

Run the following command to verify the VM was created. This command filters the VMs by name.

```azurecli
az vm list -d -o table --query "[?name=='${MY_VM_NAME}']"
```

<!-- expected_similarity=0.3 -->
```JSON
[
  {
    "name": "myVM",
    "powerState": "running",
    "publicIps": "xxx.xxx.xxx.xxx"
  }
]
```

## Connect to the VM

Run the SSH command to connect to your new Linux VM. Replace the <ip_address> placeholder with the IP address obtained from the previous step.

```bash
ssh -o StrictHostKeyChecking=no azureuser@$MY_PUBLIC_IP_NAME
```

## Next steps

> [!div class="nextstepaction"]
> [Manage a Linux virtual machine in Azure using Ansible](./vm-manage.md)