---
title: Linux VM boots to GRUB rescue
description: Provides troubleshooting guidance for GRUB rescue issues with Linux virtual machines.
services: virtual-machines
documentationcenter: ''
author: divargas
ms.service: azure-virtual-machines
ms.collection: linux
ms.workload: infrastructure-services
ms.tgt_pltfrm: vm-linux
ms.custom: sap:My VM is not booting, linux-related-content
ms.topic: troubleshooting
ms.date: 02/25/2025
ms.author: divargas
ms.reviewer: ekpathak, v-leedennis, v-weizhu
---

# Linux virtual machine boots to GRUB rescue

**Applies to:** :heavy_check_mark: Linux VMs

<!-- Commenting out these entries as this information should be selected by the user along with the corresponding subscription and region

The First step in this tutorial is to define environment variables.

```azurecli-interactive
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup89f292"
export MY_VM_NAME="myVM89f292"
```
-->



This article discusses multiple conditions that cause GRUB rescue issues and provides troubleshooting guidance.

During the boot process, the boot loader tries to locate the Linux kernel and hand off the boot control. If this handoff can't be performed, the virtual machine (VM) enters a GRUB rescue console. The GRUB rescue console prompt isn't shown in the Azure serial console log, but it can be shown in the [Azure boot diagnostics screenshot](/azure/virtual-machines/boot-diagnostics#boot-diagnostics-view).

## <a id="identify-grub-rescue-issue"></a>Identify GRUB rescue issue

[View a boot diagnostics screenshot](/azure/virtual-machines/boot-diagnostics#boot-diagnostics-view) in the VM **Boot diagnostics** page of the Azure portal. This screenshot helps diagnose the GRUB rescue issue and determine if a boot error causes the issue.

The following text is an example of a GRUB rescue issue:

```output
error: file '/boot/grub2/i386-pc/normal.mod' not found.  
Entering rescue mode...  
grub rescue>
```

## <a id="offline-troubleshooting"></a>Troubleshoot GRUB rescue issue offline

1. To troubleshoot a GRUB rescue issue, a rescue/repair VM is required. Use [vm repair commands](repair-linux-vm-using-azure-virtual-machine-repair-commands.md) to create a repair VM that has a copy of the affected VM's OS disk attached. Mount the copy of the OS file systems in the repair VM by using [chroot](chroot-environment-linux.md).

    > [!NOTE]
    > Alternatively, you can create a rescue VM manually by using the Azure portal. For more information, see [Troubleshoot a Linux VM by attaching the OS disk to a recovery VM using the Azure portal](troubleshoot-recovery-disks-portal-linux.md).

2. [Identify GRUB rescue issue](#identify-grub-rescue-issue). When you encounter one of the following GRUB rescue issues, go to the corresponding section to resolve it:

    * [Error: unknown filesystem](#unknown-filesystem)
    * [Error 15: File not found](#error15)
    * [Error: file '/boot/grub2/i386-pc/normal.mod' not found](#normal-mod-file-not-found)
    * [Error: no such partition](#no-such-partition)
    * [Error: symbol 'grub_efi_get_secure_boot' not found](#grub_efi_get_secure_boot)
    * [Other GRUB rescue errors](#other-grub-rescue-errors)

3. After the GRUB rescue issue is resolved, perform the following actions:

    1. Unmount the copy of the file systems from the rescue/repair VM.

    2. Run the `az vm repair restore` command to swap the repaired OS disk with the original OS disk of the VM. For more information, see Step 5 in [Repair a Linux VM by using the Azure Virtual Machine repair commands](repair-linux-vm-using-azure-virtual-machine-repair-commands.md).

    3. Check whether the VM can start by taking a look at the Azure serial console or by trying to connect to the VM.

4. If the entire /boot partition or other important contents are missing and can't be recovered, we recommend restoring the VM from a backup. For more information, see [How to restore Azure VM data in Azure portal](/azure/backup/backup-azure-arm-restore-vms).

See the following sections for detailed errors, possible causes, and solutions.

> [!NOTE]
> In the commands mentioned in the following sections, replace `/dev/sdX` with the corresponding Operating System (OS) disk device.

### <a id="offline-troubleshooting"></a> Reinstall GRUB and regenerate GRUB configuration file using Auto Repair (ALAR)

Azure Linux Auto Repair (ALAR) scripts are part of the VM repair extension described in [Use Azure Linux Auto Repair (ALAR) to fix a Linux VM](./repair-linux-vm-using-alar.md). ALAR covers the automation of multiple repair scenarios, including GRUB rescue issues.

The ALAR scripts use the repair extension `repair-button` to fix GRUB issues by specifying `--button-command grubfix` for Generation 1 VMs, or `--button-command efifix` for Generation 2 VMs. This parameter triggers the automated recovery. Implement the following step to automate the fix of common GRUB errors that could be fixed by reinstalling GRUB and regenerating the corresponding configuration file:

```azurecli-interactive
GEN=$(az vm get-instance-view --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query "instanceView.hyperVGeneration" --output tsv)
if [[ "$GEN" =~ "[Vv]?2" ]]; then   ALAR="efifix"; else   ALAR="grubfix"; fi
output=$(az extension add -n vm-repair; az extension update -n vm-repair; az vm repair repair-button --button-command $ALAR --verbose --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME)
value=$(echo "$output" | jq -r '.message')
extracted=$(echo $value)
echo "$extracted"
```

The repair VM script, in conjunction with the ALAR script, temporarily creates a resource group, a repair VM, and a copy of the affected VM's OS disk. It reinstalls GRUB and regenerates the corresponding GRUB configuration file and then it swaps the OS disk of the broken VM with the copied fixed disk. Finally, the `repair-button` script will automatically delete the resource group containing the temporary repair VM.

## Next steps

If the specific boot error isn't a GRUB rescue issue, refer to [Troubleshoot Azure Linux Virtual Machines boot errors](boot-error-troubleshoot-linux.md) for further troubleshooting options.

[!INCLUDE [Third-party disclaimer](../../../includes/third-party-disclaimer.md)]

[!INCLUDE [Third-party contact disclaimer](../../../includes/third-party-contact-disclaimer.md)]