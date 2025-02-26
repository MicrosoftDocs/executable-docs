---
title: Recover Azure Linux VM from kernel panic due to missing initramfs
description: Provides solutions to an issue in which a Linux virtual machine (VM) can't boot after applying kernel changes.
author: divargas-msft
ms.author: divargas
ms.date: 02/25/2025
ms.reviewer: jofrance
ms.service: azure-virtual-machines
ms.custom: sap:Cannot start or stop my VM, devx-track-azurecli, mode-api, innovation-engine, linux-related-content
ms.workload: infrastructure-services
ms.tgt_pltfrm: vm-linux
ms.collection: linux
ms.topic: troubleshooting
---

# Azure Linux virtual machine fails to boot after applying kernel changes

**Applies to:** :heavy_check_mark: Linux VMs

<!-- Commenting out these entries as this information should be selected by the user along with the corresponding subscription and region

The First step in this tutorial is to define environment variables, and install the corresponding package, if necessary.

```azurecli-interactive
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup89f292"
export MY_VM_NAME="myVM89f292"
```
-->


## Prerequisites

Make sure the [serial console](serial-console-linux.md) is enabled and functional in the Linux VM.

## <a id="missing-initramfs"></a>Kernel panic - not syncing: VFS: Unable to mount root fs on unknown-block(0,0)

This error occurs because of a recent system update (kernel). It's most commonly seen in RHEL-based distributions.
You can [identify this issue from the Azure serial console](#identify-kernel-boot-issue). You'll see any of the following error messages:

1. "Kernel panic - not syncing: VFS: Unable to mount root fs on unknown-block(0,0)"

    ```output
    [  301.026129] Kernel panic - not syncing: VFS: Unable to mount root fs on unknown-block(0,0)
    [  301.027122] CPU: 0 PID: 1 Comm: swapper/0 Tainted: G               ------------ T 3.10.0-1160.36.2.el7.x86_64 #1
    [  301.027122] Hardware name: Microsoft Corporation Virtual Machine/Virtual Machine, BIOS 090008  12/07/2018
    [  301.027122] Call Trace:
    [  301.027122]  [<ffffffff82383559>] dump_stack+0x19/0x1b
    [  301.027122]  [<ffffffff8237d261>] panic+0xe8/0x21f
    [  301.027122]  [<ffffffff8298b794>] mount_block_root+0x291/0x2a0
    [  301.027122]  [<ffffffff8298b7f6>] mount_root+0x53/0x56
    [  301.027122]  [<ffffffff8298b935>] prepare_namespace+0x13c/0x174
    [  301.027122]  [<ffffffff8298b412>] kernel_init_freeable+0x222/0x249
    [  301.027122]  [<ffffffff8298ab28>] ? initcall_blcklist+0xb0/0xb0
    [  301.027122]  [<ffffffff82372350>] ? rest_init+0x80/0x80
    [  301.027122]  [<ffffffff8237235e>] kernel_init+0xe/0x100
    [  301.027122]  [<ffffffff82395df7>] ret_from_fork_nospec_begin+0x21/0x21
    [  301.027122]  [<ffffffff82372350>] ? rest_init+0x80/0x80
    [  301.027122] Kernel Offset: 0xc00000 from 0xffffffff81000000 (relocation range: 0xffffffff80000000-0xffffffffbfffffff)
    ```

2. "error: file '/initramfs-*.img' not found"

    > error: file '/initramfs-3.10.0-1160.36.2.el7.x86_64.img' not found.

This kind of error indicates that the initramfs file isn't generated, the GRUB configuration file has the initrd entry missing after a patching process, or a GRUB manual misconfiguration.

### <a id="missing-initramfs-alar"></a>Regenerate missing initramfs by using Azure Repair VM ALAR scripts

1. Create a repair VM by running the following Bash command line with [Azure Cloud Shell](/azure/cloud-shell/overview). For more information, see [Use Azure Linux Auto Repair (ALAR) to fix a Linux VM - initrd option](repair-linux-vm-using-ALAR.md#initrd). This command will regenerate the initrd/initramfs image, regenerate the GRUB configuration file if it has the initrd entry missing, and swap the OS disk

```azurecli-interactive
output=$(az extension add -n vm-repair; az extension update -n vm-repair; az vm repair repair-button --button-command 'initrd' --verbose --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME)
value=$(echo "$output" | jq -r '.message')
extracted=$(echo $value)
echo "$extracted"
```

2. Once the repair VM command has been executed, restart the original VM and validate that it's able to boot up.

## Next steps

If the specific boot error isn't a kernel related boot issue, see [Troubleshoot Azure Linux Virtual Machines boot errors](./boot-error-troubleshoot-linux.md) for further troubleshooting options.

[!INCLUDE [Azure Help Support](../../../includes/azure-help-support.md)]