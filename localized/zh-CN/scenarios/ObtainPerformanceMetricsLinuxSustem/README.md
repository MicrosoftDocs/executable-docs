---
title: 从 Linux 系统获取性能指标
description: 了解如何从 Linux 系统获取性能指标。
author: divargas-msft
ms.author: esflores
editor: divargas-msft
ms.reviewer: divargas
ms.service: virtual-machines
ms.collection: linux
ms.topic: troubleshooting-general
ms.workload: infrastructure-services
ms.tgt_pltfrm: vm-linux
ms.date: 07/16/2024
ms.custom: 'devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# 从 Linux 系统获取性能指标

适用于：:heavy_check_mark: Linux VM****

本文将介绍有关如何快速从 Linux 系统获取性能指标的说明。

可以使用多个命令在 Linux 上获取性能计数器。 命令（如 `vmstat` 和 `uptime`）提供常规系统指标，例如 CPU 使用率、系统内存和系统负载。
默认情况下，大多数命令都已安装，其他命令在默认存储库中随时可用。
这些命令可以分为：

* CPU
* 内存
* 磁盘 I/O
* 进程

## Sysstat 实用工具安装

<!-- Commenting out these entries as this information should be selected by the user along with the corresponding subscription and region

The First step in this tutorial is to define environment variables, and install the corresponding package, if necessary.

```azurecli-interactive
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup89f292"
export MY_VM_NAME="myVM89f292"
```
-->

> [!NOTE]
> 需要运行 `root` 其中一些命令才能收集所有相关的详细信息。

> [!NOTE]
> 某些命令是默认情况下可能未安装的包的 `sysstat` 一部分。 可以使用这些`zypper install sysstat`常用发行版轻松安装`sudo apt install sysstat``dnf install sysstat`包。

在 `sysstat` 一些常用发行版上安装包的完整命令是：

```bash
az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "/bin/bash -c 'OS=\$(cat /etc/os-release|grep NAME|head -1|cut -d= -f2 | sed \"s/\\\"//g\"); if [[ \$OS =~ \"Ubuntu\" ]] || [[ \$OS =~ \"Debian\" ]]; then sudo apt install sysstat -y; elif [[ \$OS =~ \"Red Hat\" ]]; then sudo dnf install sysstat -y; elif [[ \$OS =~ \"SUSE\" ]]; then sudo zypper install sysstat --non-interactive; else echo \"Unknown distribution\"; fi'"
```

## CPU

### <a id="mpstat"></a>mpstat

该 `mpstat` 实用工具是包的 `sysstat` 一部分。 它显示每个 CPU 利用率和平均值，这有助于快速识别 CPU 使用率。 `mpstat` 概述可用 CPU 中的 CPU 使用率，帮助确定使用情况均衡以及单个 CPU 是否负载过大。

完整命令为：

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

选项和参数为：

* `-P`：指示要显示统计信息的处理器，ALL 参数指示显示系统中所有联机 CPU 的统计信息。
* `1`：第一个数值参数指示刷新显示的频率（以秒为单位）。
* `2`：第二个数值参数指示数据刷新次数。

命令显示数据的次数 `mpstat` 可以通过增加第二个数值参数以适应更长的数据收集时间来更改数据。 理想情况下，3 或 5 秒应该足够，对于核心计数增加 2 秒的系统，可用于减少显示的数据量。
从输出中：

```output
Linux 5.14.0-362.8.1.el9_3.x86_64 (alma9)       02/21/24        _x86_64_        (8 CPU)

16:55:50     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
16:55:51     all   69.09    0.00   30.16    0.00    0.38    0.38    0.00    0.00    0.00    0.00
16:55:51       0   77.23    0.00   21.78    0.00    0.99    0.00    0.00    0.00    0.00    0.00
16:55:51       1   97.03    0.00    0.99    0.00    0.99    0.99    0.00    0.00    0.00    0.00
16:55:51       2   11.11    0.00   88.89    0.00    0.00    0.00    0.00    0.00    0.00    0.00
16:55:51       3   11.00    0.00   88.00    0.00    0.00    1.00    0.00    0.00    0.00    0.00
16:55:51       4   83.84    0.00   16.16    0.00    0.00    0.00    0.00    0.00    0.00    0.00
16:55:51       5   76.00    0.00   23.00    0.00    1.00    0.00    0.00    0.00    0.00    0.00
16:55:51       6   96.00    0.00    3.00    0.00    0.00    1.00    0.00    0.00    0.00    0.00
16:55:51       7  100.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00
[...]

Average:     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
Average:     all   74.02    0.00   25.52    0.00    0.25    0.21    0.00    0.00    0.00    0.00
Average:       0   63.00    0.00   36.67    0.00    0.33    0.00    0.00    0.00    0.00    0.00
Average:       1   97.33    0.00    1.67    0.00    0.33    0.67    0.00    0.00    0.00    0.00
Average:       2   42.33    0.00   57.33    0.00    0.33    0.00    0.00    0.00    0.00    0.00
Average:       3   34.33    0.00   65.00    0.00    0.33    0.33    0.00    0.00    0.00    0.00
Average:       4   88.63    0.00   11.04    0.00    0.00    0.33    0.00    0.00    0.00    0.00
Average:       5   71.33    0.00   28.33    0.00    0.33    0.00    0.00    0.00    0.00    0.00
Average:       6   95.65    0.00    4.01    0.00    0.00    0.33    0.00    0.00    0.00    0.00
Average:       7   99.67    0.00    0.00    0.00    0.33    0.00    0.00    0.00    0.00    0.00
```

需要注意几个重要事项。 第一行显示有用的信息：

* 内核和发布： `5.14.0-362.8.1.el9_3.x86_64`
* 主机名： `alma9`
* 日期： `02/21/24`
* 建筑： `_x86_64_`
* CPU 总数（此信息可用于解释来自其他命令的输出）： `(8 CPU)`

然后显示 CPU 的指标，以解释每个列：

* `Time`：收集样本的时间
* `CPU`：CPU 数字标识符，ALL 标识符是所有 CPU 的平均值。
* `%usr`：用户空间（通常是用户应用程序）的 CPU 使用率百分比。
* `%nice`：具有良好（优先级）值的用户空间进程的 CPU 使用率百分比。
* `%sys`：内核空间进程的 CPU 使用率百分比。
* `%iowait`：空闲等待未完成 I/O 的 CPU 时间百分比。
* `%irq`：为硬件中断提供服务的 CPU 时间百分比。
* `%soft`：为软件中断提供服务的 CPU 时间百分比。
* `%steal`：为其他虚拟机提供服务的 CPU 时间百分比（由于没有过度预配 CPU 而不适用于 Azure）。
* `%guest`：为虚拟 CPU 提供服务的 CPU 时间百分比（不适用于 Azure，仅适用于运行虚拟机的裸机系统）。
* `%gnice`：为虚拟 CPU 提供服务的 CPU 时间百分比（不适用于 Azure，仅适用于运行虚拟机的裸机系统）。
* `%idle`：空闲的 CPU 时间百分比，无需等待 I/O 请求。

#### 需要注意的事项

查看以下项的输出 `mpstat`时要记住的一些详细信息：

* 验证是否已正确加载所有 CPU，而不是单个 CPU 为所有负载提供服务。 此信息可能指示单个线程应用程序。
* 在实际工作负荷上花费的时间比为内核进程提供服务的时间要多，因此，寻找一个正常的平衡点`%usr``%sys`，因为相反，这表示花费的时间比提供内核进程的时间要多。
* `%iowait`查找百分比，因为高值可能指示一个持续等待 I/O 请求的系统。
* 高 `%soft` 使用率可能表示网络流量较高。

### `vmstat`

该 `vmstat` 实用工具在大多数 Linux 分发版中广泛使用，它在单个窗格中提供 CPU、内存和磁盘 I/O 利用率的高级概述。
其命令 `vmstat` 为：

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'vmstat -w 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

选项和参数为：

* `-w`：使用宽打印来保持一致的列。
* `1`：第一个数值参数指示刷新显示的频率（以秒为单位）。
* `5`：第二个数值参数指示数据刷新次数。

输出：

```output
--procs-- -----------------------memory---------------------- ---swap-- -----io---- -system-- --------cpu--------
   r    b         swpd         free         buff        cache   si   so    bi    bo   in   cs  us  sy  id  wa  st
  14    0            0     26059408          164       137468    0    0    89  3228   56  122   3   1  95   1   0
  14    1            0     24388660          164       145468    0    0     0  7811 3264 13870  76  24   0   0   0
  18    1            0     23060116          164       155272    0    0    44  8075 3704 15129  78  22   0   0   0
  18    1            0     21078640          164       165108    0    0   295  8837 3742 15529  73  27   0   0   0
  15    2            0     19015276          164       175960    0    0     9  8561 3639 15177  73  27   0   0   0
```

`vmstat` 拆分六个组中的输出：

* `procs`：进程的统计信息。
* `memory`：系统内存的统计信息。
* `swap`：交换的统计信息。
* `io`：磁盘 io 的统计信息。
* `system`：上下文切换和中断的统计信息。
* `cpu`：CPU 使用率的统计信息。

>注意： `vmstat` 显示整个系统的总体统计信息（即所有 CPU、聚合的所有块设备）。

#### `procs`

该 `procs` 部分包含两列：

* `r`：运行队列中的可运行进程数。
* `b`：等待 I/O 的进程数。

本部分会立即显示系统上是否存在任何瓶颈。 任一列上的高数字表示等待资源的进程排队。

该 `r` 列指示等待 CPU 时间能够运行的进程数。 解释此数字的一种简单方法是：如果队列中的 `r` 进程数高于总 CPU 数，则可以推断系统已大量加载 CPU，并且无法为等待运行的所有进程分配 CPU 时间。

该 `b` 列指示等待 I/O 请求阻止运行的进程数。 此列中的高数字表示遇到高 I/O 的系统，由于等待完成的 I/O 请求的其他进程无法运行进程。 这也可能表示磁盘延迟较高。

#### `memory`

内存部分有四列：

* `swpd`：使用的交换内存量。
* `free`：可用内存量。
* `buff`：用于缓冲区的内存量。
* `cache`：用于缓存的内存量。

> [!NOTE]
> 这些值以字节为单位显示。

本部分简要概述了内存使用情况。

#### `swap`

交换节有两列：

* `si`：交换的内存量（从系统内存移到交换）/秒。
* `so`：每秒交换的内存量（从交换移动到系统内存）。

如果观察到高 `si` ，它可能表示系统内存不足且正在移动页面以交换（交换）。

#### `io`

该 `io` 部分包含两列：

* `bi`：每秒从块设备接收的块数（每秒读取块数）。
* `bo`：每秒发送到块设备的块数（每秒写入数）。

> [!NOTE]
> 这些值以每秒块为单位。

#### `system`

该 `system` 部分包含两列：

* `in`：每秒中断数。
* `cs`：每秒上下文切换数。

每秒大量中断可能表示正忙于硬件设备的系统（例如网络操作）。

大量上下文切换可能表示具有许多短运行进程的繁忙系统，此处没有好坏的数字。

#### `cpu`

本部分包含五列：

* `us`：用户空间利用率百分比。
* `sy`：系统（内核空间）利用率百分比。
* `id`：CPU 空闲时间的利用率百分比。
* `wa`：CPU 空闲等待 I/O 进程的时间的利用率百分比。
* `st`：CPU 为其他虚拟 CPU 所花费的时间（不适用于 Azure）的利用率百分比。

这些值以百分比形式显示。 这些值与实用工具提供 `mpstat` 的值相同，用于提供 CPU 使用率的高级概述。 查看这些值时，请遵循类似的过程来了解“[需要注意](#mpstat)的事项”。`mpstat`

### `uptime`

最后，对于与 CPU 相关的指标，该 `uptime` 实用工具提供了系统负载的大致概述，其中包含负载平均值。

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'uptime')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

```output
16:55:53 up 9 min,  2 users,  load average: 9.26, 2.91, 1.18
```

负载平均值显示三个数字。 这些数字用于`1``5`系统`15`负载的分钟间隔。

若要解释这些值，请务必知道系统中可用 CPU 的数量，这些 CPU 是从之前从输出获取的 `mpstat` 。 该值取决于总 CPU，因此，作为系统 8 个 CPU 的输出示例 `mpstat` ，负载平均值为 8 表示所有核心都加载到 100%。

值为 `4` 意味着一半的 CPU 加载为 100%（或所有 CPU 上的总负载为 50%） 。 在上一个输出中，负载平均值 `9.26`为，这意味着 CPU 的加载率约为 115%。

间隔`1m``5m``15m`有助于确定负载是否随时间推移而增加或减少。

> [注意]该 `nproc` 命令还可用于获取 CPU 数。

## 内存

对于内存，有两个命令可以获取有关使用情况的详细信息。

### `free`

该 `free` 命令显示系统内存利用率。

运行它：

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'free -h')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

选项和参数为：

* `-h`：以人类可读方式动态显示值（例如：Mib、Gib、Tib）

输出：

```output
               total        used        free      shared  buff/cache   available
Mem:            31Gi        19Gi        12Gi        23Mi        87Mi        11Gi
Swap:           23Gi          0B        23Gi
```

在输出中，查找系统内存总量与可用内存，以及使用的与总交换。 可用内存会考虑为缓存分配的内存，该内存可以返回给用户应用程序。

一些交换使用在现代内核中很正常，因为一些不太常使用的内存页可以移动到交换。

### `swapon`

该 `swapon` 命令显示交换配置的位置以及交换设备或文件的相应优先级。

若要运行命令，请执行以下命令：

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'swapon -s')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

输出：

```output
Filename      Type          Size          Used   Priority
/dev/zram0    partition     16G           0B      100
/mnt/swapfile file          8G            0B      -2
```

此信息对于验证交换是否在不理想位置（例如数据或 OS 磁盘）上配置交换非常重要。 在 Azure 参考帧中，应在临时驱动器上配置交换，因为它可提供最佳性能。

### 需要注意的事项

* 请记住，内存是有限的资源，一旦系统内存（RAM）和交换都耗尽，进程将被内存外杀手（OOM）。
* 验证交换是否未在数据磁盘或 OS 磁盘上配置，因为由于延迟差异，这会导致 I/O 出现问题。 应在临时驱动器上配置交换。
* 另请注意，在输出中看到 `free -h` 免费值接近零是常见的，此行为是由于页面缓存，内核会根据需要释放这些页面。

## I/O

磁盘 I/O 是 Azure 受限制时遭受的最大区域之一，因为磁盘可能会达到 `100ms+` 延迟。 以下命令有助于识别这些方案。

### `iostat`

该 `iostat` 实用工具是包的 `sysstat` 一部分。 它显示每个块设备使用情况统计信息，并帮助识别与块相关的性能问题。

该 `iostat` 实用工具提供有关吞吐量、延迟和队列大小等指标的详细信息。 这些指标有助于了解磁盘 I/O 是否成为限制因素。
若要运行，请使用以下命令：

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'iostat -dxtm 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

选项和参数为：

* `-d`：按设备使用情况报告。
* `-x`：扩展统计信息。
* `-t`：显示每个报表的时间戳。
* `-m`：以 MB/秒为单位显示。
* `1`：第一个数值参数指示刷新显示的频率（以秒为单位）。
* `2`：第二个数值参数指示数据刷新次数。

输出：

```output
Linux 5.14.0-362.8.1.el9_3.x86_64 (alma9)       02/21/24        _x86_64_        (8 CPU)

02/21/24 16:55:50
Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
sda              1.07      0.02     0.00   0.00    1.95    20.40   23.25     24.55     3.30  12.42  113.75  1081.06    0.26    537.75     0.26  49.83    0.03 2083250.04    0.00    0.00    2.65   2.42
sdb             16.99      0.67     0.36   2.05    2.00    40.47   65.26      0.44     1.55   2.32    1.32     6.92    0.00      0.00     0.00   0.00    0.00     0.00   30.56    1.30    0.16   7.16
zram0            0.51      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.00   0.00

```

输出包含几个不重要的列（由于 `-x` 选项导致的额外列），其中一些重要列包括：

* `r/s`：每秒读取操作数（IOPS）。
* `rMB/s`：每秒读取兆字节。
* `r_await`：读取延迟（以毫秒为单位）。
* `rareq-sz`：读取请求的平均大小（以 KB 为单位）。
* `w/s`：每秒写入操作数（IOPS）。
* `wMB/s`：每秒写入兆字节。
* `w_await`：写入延迟（以毫秒为单位）。
* `wareq-size`：平均写入请求大小（以 KB 为单位）。
* `aqu-sz`：平均队列大小。

#### 需要注意的事项

* 查找 `r/s` 和 `w/s` （IOPS）， `rMB/s` 并 `wMB/s` 验证这些值是否在给定磁盘的限制范围内。 如果值接近或更高的限制，磁盘将受到限制，从而导致高延迟。 此信息也可以与来自`mpstat`的`%iowait`指标进行证实。
* 延迟是一个很好的指标，用于验证磁盘是否按预期执行。 通常，低于 `9ms` PremiumSSD 的预期延迟，其他产品/服务具有不同的延迟目标。
* 队列大小是饱和度的主要指标。 通常，请求将近乎实时地提供，并且该数字仍接近一个（因为队列永远不会增长）。 较高的数字可能表示磁盘饱和（即请求排队）。 此指标没有好坏的数字。 了解高于 1 的任何内容意味着请求排队有助于确定磁盘是否饱和。

### `lsblk`

该 `lsblk` 实用工具显示附加到系统的块设备，虽然它不提供性能指标，但它允许快速概述如何配置这些设备以及正在使用哪些装入点。

若要运行，请使用以下命令：

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'lsblk')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

输出：

```output
NAME   MAJ:MIN RM  SIZE RO TYPE MOUNTPOINTS
sda      8:0    0  300G  0 disk
└─sda1   8:1    0  300G  0 part /mnt
sdb      8:16   0   30G  0 disk
├─sdb1   8:17   0    1M  0 part
├─sdb2   8:18   0  200M  0 part /boot/efi
├─sdb3   8:19   0    1G  0 part /boot
└─sdb4   8:20   0 28.8G  0 part /
zram0  252:0    0   16G  0 disk [SWAP]
```

#### 需要注意的事项

* 查找设备装载的位置。
* 验证是否未在数据磁盘或 OS 磁盘内配置交换（如果已启用）。

> 注意：将块设备关联到 Azure 中的 LUN 的一种简单方法是运行 `ls -lr /dev/disk/azure`。

## 处理

收集每个进程的详细信息有助于了解系统负载的来源。

收集进程静态的主要实用工具是 `pidstat` 因为它提供每个进程的详细信息，用于 CPU、内存和 I/O 统计信息。

最后，按最高 CPU 对进程进行排序的简单 `ps` 方法，内存使用率完成指标。

> [!NOTE]
> 由于这些命令显示有关运行进程的详细信息，因此它们需要以根 `sudo`身份运行。 此命令允许显示所有进程，而不仅仅是用户。

### `pidstat`

该 `pidstat` 实用工具也是包的 `sysstat` 一部分。 它类似于 `mpstat` 或 iostat，其中显示给定时间的指标。 默认情况下， `pidstat` 仅显示具有活动的进程的指标。

`pidstat`其他`sysstat`实用工具的参数相同：

* 1：第一个数值参数指示刷新显示的频率（以秒为单位）。
* 2：第二个数值参数指示数据刷新次数。

> [!NOTE]
> 如果有许多进程具有活动，则输出可能会大幅增长。

#### 进程 CPU 统计信息

若要收集进程 CPU 统计信息，请在没有任何选项的情况下运行 `pidstat` ：

如果要从 Azure CLI 执行以下命令，可以使用以下命令：

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

输出：

```output
Linux 5.14.0-362.8.1.el9_3.x86_64 (alma9)       02/21/24        _x86_64_        (8 CPU)

# Time        UID       PID    %usr %system  %guest   %wait    %CPU   CPU  Command
16:55:48        0        66    0.0%    1.0%    0.0%    0.0%    1.0%     0  kworker/u16:2-xfs-cil/sdb4
16:55:48        0        70    0.0%    1.0%    0.0%    0.0%    1.0%     0  kworker/u16:6-xfs-cil/sdb4
16:55:48        0        92    0.0%    1.0%    0.0%    0.0%    1.0%     3  kworker/3:1H-kblockd
16:55:48        0       308    0.0%    1.0%    0.0%    0.0%    1.0%     1  kworker/1:1H-kblockd
16:55:48        0      2068    0.0%    1.0%    0.0%    0.0%    1.0%     1  kworker/1:3-xfs-conv/sdb4
16:55:48        0      2181   63.1%    1.0%    0.0%   35.9%   64.1%     5  stress-ng-cpu
16:55:48        0      2182   28.2%    0.0%    0.0%   70.9%   28.2%     6  stress-ng-cpu
16:55:48        0      2183   28.2%    0.0%    0.0%   69.9%   28.2%     7  stress-ng-cpu
16:55:48        0      2184   62.1%    0.0%    0.0%   36.9%   62.1%     0  stress-ng-cpu
16:55:48        0      2185   43.7%    0.0%    0.0%   54.4%   43.7%     2  stress-ng-cpu
16:55:48        0      2186   30.1%    0.0%    0.0%   68.0%   30.1%     7  stress-ng-cpu
16:55:48        0      2187   64.1%    0.0%    0.0%   34.0%   64.1%     3  stress-ng-cpu
```

该命令显示每个进程使用情况`%usr`（ `%system``%guest` 不适用于 Azure）`%wait`和总`%CPU`使用量。

##### 需要注意的事项

* 查找百分比较高的进程（iowait），因为它可能指示阻止等待 I/O 的进程，这也可能表示磁盘饱和度。
* 验证单个进程是否不使用 100% 的 CPU，因为它可能指示单个线程应用程序。

#### 进程内存统计信息

若要收集进程内存统计信息，请使用 `-r` 以下选项：

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -r 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

输出：

```output
Linux 5.14.0-362.8.1.el9_3.x86_64 (alma9)       02/21/24        _x86_64_        (8 CPU)

# Time        UID       PID  minflt/s  majflt/s     VSZ     RSS   %MEM  Command
16:55:49        0      2199 119244.12      0.00   13.6G    7.4G  23.5%  stress-ng-vm
16:55:49        0      2200 392911.76      0.00   13.6G    9.3G  29.7%  stress-ng-vm
16:55:49        0      2211   1129.41      0.00   72.3M    3.2M   0.0%  stress-ng-iomix
16:55:49        0      2220      0.98      0.00   71.8M    2.4M   0.0%  stress-ng-iomix
16:55:49        0      2239   1129.41      0.00   72.3M    3.2M   0.0%  stress-ng-iomix
16:55:49        0      2240   1129.41      0.00   72.3M    3.2M   0.0%  stress-ng-iomix
16:55:49        0      2256      0.98      0.00   71.8M    2.4M   0.0%  stress-ng-iomix
16:55:49        0      2265   1129.41      0.00   72.3M    3.2M   0.0%  stress-ng-iomix
```

收集的指标包括：

* `minflt/s`：每秒出现轻微故障，此指标指示从系统内存（RAM）加载的页数。
* `mjflt/s`：每秒出现重大故障，此指标指示从磁盘加载的页数（SWAP）。
* `VSZ`：以字节为单位使用的虚拟内存。
* `RSS`：已用内存（实际分配的内存）（以字节为单位）。
* `%MEM`：已用内存总量的百分比。
* `Command`：进程的名称。

##### 需要注意的事项

* 查找每秒发生的主要故障，因为此值将指示将页面交换到磁盘或从磁盘交换的进程。 此行为可能表示内存耗尽，并可能导致 `OOM` 事件或性能下降，因为交换速度较慢。
* 验证单个进程是否不使用 100% 的可用内存。 此行为可能指示内存泄漏。

> [!NOTE]
> 该 `--human` 选项可用于以人类可读格式显示数字（即， `Kb`， `Mb`， `GB`）。

#### 进程 I/O 统计信息

若要收集进程内存统计信息，请使用 `-d` 以下选项：

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -d 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

输出：

```outputLinux 5.14.0-362.8.1.el9_3.x86_64 (alma9)       02/21/24        _x86_64_        (8 CPU)

# Time        UID       PID   kB_rd/s   kB_wr/s kB_ccwr/s iodelay  Command
16:55:50        0        86     55.4k      0.0B      0.0B       0  kworker/1:1-xfs-conv/sdb4
16:55:50        0      2201      4.0k    194.1k      0.0B       0  stress-ng-iomix
16:55:50        0      2202      0.0B     99.0k      0.0B       0  stress-ng-iomix
16:55:50        0      2203      0.0B     23.8k      0.0B       0  stress-ng-iomix
16:55:50        0      2204      0.0B     15.8k      0.0B       0  stress-ng-iomix
16:55:50        0      2212      0.0B    103.0k      0.0B       0  stress-ng-iomix
16:55:50        0      2213      4.0k     99.0k      0.0B       0  stress-ng-iomix
16:55:50        0      2215      0.0B    178.2k      0.0B       0  stress-ng-iomix
16:55:50        0      2216      7.9k    237.6k      0.0B       0  stress-ng-iomix
16:55:50        0      2218      0.0B     95.0k      0.0B       0  stress-ng-iomix
16:55:50        0      2221      0.0B     15.8k      0.0B       0  stress-ng-iomix
```

收集的指标包括：

* `kB_rd/s`：每秒读取千字节。
* `kB_wr/s`：每秒写入千字节。
* `Command`：进程的名称。

##### 需要注意的事项

* 查找每秒读取/写入速率较高的单个进程。 此信息是 I/O 流程的指南，不仅仅是识别问题。
注意：此选项`--human`可用于以人类可读格式显示数字（即，，`Kb``Mb`，`GB`）。

### `ps`

`ps`最后命令显示系统进程，可以按 CPU 或内存进行排序。

按 CPU 排序并获取前 10 个进程：

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'ps aux --sort=-%cpu | head -10')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

```output
USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root        2190 94.8  0.0  73524  5588 pts/1    R+   16:55   0:14 stress-ng --cpu 12 --vm 2 --vm-bytes 120% --iomix 4 --timeout 240
root        2200 56.8 43.1 14248092 14175632 pts/1 R+ 16:55   0:08 stress-ng --cpu 12 --vm 2 --vm-bytes 120% --iomix 4 --timeout 240
root        2192 50.6  0.0  73524  5836 pts/1    R+   16:55   0:07 stress-ng --cpu 12 --vm 2 --vm-bytes 120% --iomix 4 --timeout 240
root        2184 50.4  0.0  73524  5836 pts/1    R+   16:55   0:07 stress-ng --cpu 12 --vm 2 --vm-bytes 120% --iomix 4 --timeout 240
root        2182 44.3  0.0  73524  5808 pts/1    R+   16:55   0:06 stress-ng --cpu 12 --vm 2 --vm-bytes 120% --iomix 4 --timeout 240
root        2187 43.4  0.0  73524  5708 pts/1    R+   16:55   0:06 stress-ng --cpu 12 --vm 2 --vm-bytes 120% --iomix 4 --timeout 240
root        2199 42.9 33.0 14248092 10845272 pts/1 R+ 16:55   0:06 stress-ng --cpu 12 --vm 2 --vm-bytes 120% --iomix 4 --timeout 240
root        2186 42.0  0.0  73524  5836 pts/1    R+   16:55   0:06 stress-ng --cpu 12 --vm 2 --vm-bytes 120% --iomix 4 --timeout 240
root        2191 41.2  0.0  73524  5592 pts/1    R+   16:55   0:06 stress-ng --cpu 12 --vm 2 --vm-bytes 120% --iomix 4 --timeout 240
```

按顺序排序 `MEM%` 并获取前 10 个进程：

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'ps aux --sort=-%mem| head -10')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

```output
       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root        2200 57.0 43.1 14248092 14175632 pts/1 R+ 16:55   0:08 stress-ng --cpu 12 --vm 2 --vm-bytes 120% --iomix 4 --timeout 240
root        2199 43.0 33.0 14248092 10871144 pts/1 R+ 16:55   0:06 stress-ng --cpu 12 --vm 2 --vm-bytes 120% --iomix 4 --timeout 240
root        1231  0.2  0.1 336308 33764 ?        Sl   16:46   0:01 /usr/bin/python3 -u bin/WALinuxAgent-2.9.1.1-py3.8.egg -run-exthandlers
root         835  0.0  0.0 127076 24860 ?        Ssl  16:46   0:00 /usr/bin/python3 -s /usr/sbin/firewalld --nofork --nopid
root        1199  0.0  0.0  30164 15600 ?        Ss   16:46   0:00 /usr/bin/python3 -u /usr/sbin/waagent -daemon
root           1  0.2  0.0 173208 12356 ?        Ss   16:46   0:01 /usr/lib/systemd/systemd --switched-root --system --deserialize 31
root         966  0.0  0.0 3102460 10936 ?       Sl   16:46   0:00 /var/lib/waagent/Microsoft.GuestConfiguration.ConfigurationforLinux-1.26.60/GCAgent/GC/gc_linux_service
panzer      1803  0.0  0.0  22360  8220 ?        Ss   16:49   0:00 /usr/lib/systemd/systemd --user
root        2180  0.0  0.0  73524  6968 pts/1    SL+  16:55   0:00 stress-ng --cpu 12 --vm 2 --vm-bytes 120% --iomix 4 --timeout 240
```

## 将所有内容组合在一起

简单的 bash 脚本可以在单个运行中收集所有详细信息，并将输出追加到文件中供以后使用：

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2 && vmstat -w 1 5 && uptime && free -h && swapon && iostat -dxtm 1 1 && lsblk && ls -l /dev/disk/azure && pidstat 1 1 -h --human && pidstat -r 1 1 -h --human && pidstat -d 1 1 -h --human && ps aux --sort=-%cpu | head -20 && ps aux --sort=-%mem | head -20')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```

若要运行，可以创建包含上述内容的文件，通过运行 `chmod +x gather.sh`和运行 `sudo ./gather.sh`来添加执行权限。

此脚本将命令的输出保存在调用脚本的同一目录中的文件中。

此外，可以使用 run-command 扩展运行 `az-cli` bash 块代码中的所有命令，并分析输出 `jq` 以获取与在本地运行命令类似的输出：

```azurecli-interactive
output=$(az vm run-command invoke -g $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "ls -l /dev/disk/azure")
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```