---
title: Troubleshoot Linux VM boot issues due to fstab errors | Microsoft Learn
description: Explains why Linux VM cannot start and how to solve the problem.
services: virtual-machines
documentationcenter: ''
author: divargas-msft
ms.author: divargas
manager: dcscontentpm
tags: ''
ms.custom: sap:My VM is not booting, linux-related-content, devx-track-azurecli, mode-api, innovation-engine
ms.service: azure-virtual-machines
ms.collection: linux
ms.topic: troubleshooting
ms.workload: infrastructure-services
ms.tgt_pltfrm: vm-linux
ms.devlang: azurecli
ms.date: 02/25/2025
---


# Troubleshoot Linux VM boot issues due to fstab errors

**Applies to:** :heavy_check_mark: Linux VMs

<!-- Commenting out these entries as this information should be selected by the user along with the corresponding subscription and region
 
The First step in this tutorial is to define environment variables, and install the corresponding package, if necessary.
 
```azurecli-interactive
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup89f292"
export MY_VM_NAME="myVM89f292"
```
-->

The Linux filesystem table, fstab is a configuration table which is designed to configure rules where specific file systems are detected and mounted in an orderly manner during the system boot process.
This article discusses multiple conditions where a wrong fstab configuration can lead to boot issue and provides troubleshooting guidance.

Few common reasons that can lead to Virtual Machine Boot issues due to fstab misconfiguration are listed below:

* Traditional filesystem name is used instead of the Universally Unique Identifier (UUID) of the filesystem.
* An incorrect UUID is used. 
* An entry exists for an unattached device without `nofail` option within fstab configuration.
* Incorrect entry within fstab configuration.
  
## Identify fstab issues

Check the current boot state of the VM in the serial log within the [Boot diagnostics] (/azure/virtual-machines/boot-diagnostics#boot-diagnostics-view) blade in the Azure portal. The VM will be in an Emergency Mode. You see log entries that resemble the following example leading to the Emergency Mode state:

```output
[K[[1;31m TIME [0m] Timed out waiting for device dev-incorrect.device.
[[1;33mDEPEND[0m] Dependency failed for /data.
[[1;33mDEPEND[0m] Dependency failed for Local File Systems.
...
Welcome to emergency mode! After logging in, type "journalctl -xb" to viewsystem logs, "systemctl reboot" to reboot, "systemctl default" to try again to boot into default mode.
Give root password for maintenance
(or type Control-D to continue)
```

 >[!Note]
 > "/data" is an example of mount point used. Dependency failure for filesystem mount point will differ based on the  names used.

## Resolution

There are 2 ways to resolve the issue:

* Repair the VM online
  * [Use the Serial Console](#use-the-serial-console)
* Repair the vm offline
  * [Use Azure Linux Auto Repair (ALAR)](#use-azure-linux-auto-repair-alar)
  * [Use Manual Method](#use-manual-method)

#### Use Azure Linux Auto Repair (ALAR)

Azure Linux Auto Repair (ALAR) scripts is a part of VM repair extension described in [Repair a Linux VM by using the Azure Virtual Machine repair commands](./repair-linux-vm-using-azure-virtual-machine-repair-commands.md). ALAR covers automation of multiple repair scenarios including `/etc/fstab` issues.

The ALAR scripts use the repair extension `run` command and its `--run-id` option. The script-id for the automated recovery is: **linux-alar2**. Implement the following steps to automate fstab errors via offline ALAR approach:

```azurecli-interactive
output=$(az extension add -n vm-repair; az extension update -n vm-repair; az vm repair repair-button --button-command 'fstab' --verbose --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME)
value=$(echo "$output" | jq -r '.message')
extracted=$(echo $value)
echo "$extracted"
```

> [!NOTE]
> The fstab repair script will take a backup of the original file and strip off any lines in the /etc/fstab file which are not needed to boot a system. After successful start of the OS, edit the fstab again and correct any errors which didn't allow a reboot of the system before.

[!INCLUDE [Azure Help Support](../../../includes/azure-help-support.md)]