---
title: 從 Linux 系統取得效能計量
description: 瞭解如何從Linux系統取得效能計量。
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

# 從 Linux 系統取得效能計量

**適用於：：** heavy_check_mark：Linux VM

本文將討論如何快速從Linux系統取得效能計量的指示。

有數個命令可用來在Linux上取得性能計數器。 和 `vmstat` `uptime`之類的命令提供一般系統計量，例如CPU使用量、系統記憶體和系統負載。
大部分的命令預設都已安裝，而其他命令則可供預設存放庫中使用。
命令可以分成：

* CPU
* 記憶體
* 磁碟 I/O
* 程序

## Sysstat 公用程式安裝

<!-- Commenting out these entries as this information should be selected by the user along with the corresponding subscription and region

The First step in this tutorial is to define environment variables, and install the corresponding package, if necessary.

```azurecli-interactive
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup89f292"
export MY_VM_NAME="myVM89f292"
```
-->

> [!NOTE]
> 其中一些命令必須執行， `root` 才能收集所有相關詳細數據。

> [!NOTE]
> 某些命令是套件的一部分， `sysstat` 預設可能未安裝。 套件可以輕鬆地與 一起 `sudo apt install sysstat`安裝， `dnf install sysstat` 或 `zypper install sysstat` 適用於那些熱門發行版。

在 `sysstat` 一些熱門散發版本上安裝套件的完整命令如下：

```bash
az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "/bin/bash -c 'OS=\$(cat /etc/os-release|grep NAME|head -1|cut -d= -f2 | sed \"s/\\\"//g\"); if [[ \$OS =~ \"Ubuntu\" ]] || [[ \$OS =~ \"Debian\" ]]; then sudo apt install sysstat -y; elif [[ \$OS =~ \"Red Hat\" ]]; then sudo dnf install sysstat -y; elif [[ \$OS =~ \"SUSE\" ]]; then sudo zypper install sysstat --non-interactive; else echo \"Unknown distribution\"; fi'"
```

## CPU

### <a id="mpstat"></a>mpstat

公用 `mpstat` 程式是封裝的 `sysstat` 一部分。 它會顯示每個CPU使用率和平均值，有助於快速識別CPU使用量。 `mpstat` 提供跨可用 CPU 的 CPU 使用率概觀，協助識別使用量平衡，以及單一 CPU 是否負載過重。

完整的命令為：

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

選項與自變數如下：

* `-P`：表示要顯示統計數據的處理器，ALL 自變數表示顯示系統中所有在線 CPU 的統計數據。
* `1`：第一個數值自變數會指出以秒為單位重新整理顯示的頻率。
* `2`：第二個數值自變數會指出數據重新整理的次數。

命令顯示數據的次數 `mpstat` 可以藉由增加第二個數值自變數來容納較長的數據收集時間來變更數據。 在理想情況下，對於核心計數增加 2 秒的系統而言，應該足夠 3 或 5 秒，以減少顯示的數據量。
從輸出：

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

有幾個重要事項需要注意。 第一行會顯示有使用的資訊：

* 核心和版本： `5.14.0-362.8.1.el9_3.x86_64`
* 主機名稱： `alma9`
* 日期： `02/21/24`
* 建築： `_x86_64_`
* CPU 總數（此資訊有助於解譯來自其他命令的輸出）： `(8 CPU)`

然後會顯示 CPU 的計量，以說明每個資料列：

* `Time`：收集樣本的時間
* `CPU`：CPU 數值識別碼，ALL 標識碼是所有 CPU 的平均值。
* `%usr`：用戶空間的CPU使用率百分比，通常是使用者應用程式。
* `%nice`：具有良好（優先順序）值之用戶空間進程的CPU使用率百分比。
* `%sys`：核心空間進程的CPU使用率百分比。
* `%iowait`：閑置等待未完成 I/O 的 CPU 時間百分比。
* `%irq`：服務硬體中斷所花費的CPU時間百分比。
* `%soft`：服務軟體中斷所花費的CPU時間百分比。
* `%steal`：為其他虛擬機服務所花費的CPU時間百分比（不適用於 Azure，因為沒有過度布建 CPU）。
* `%guest`：服務虛擬 CPU 所花費的 CPU 時間百分比（不適用於 Azure，僅適用於執行虛擬機的裸機系統）。
* `%gnice`：為虛擬 CPU 提供良好值的 CPU 時間百分比（不適用於 Azure，僅適用於執行虛擬機器的裸機系統）。
* `%idle`：閑置的CPU時間百分比，而不需等候I/O要求。

#### 需要留意的事項

檢閱的輸出 `mpstat`時要記住的一些詳細資料：

* 確認所有 CPU 都已正確載入，而不是單一 CPU 會提供所有負載。 此資訊可能表示單個線程應用程式。
* 在和 `%sys` 之間`%usr`尋找狀況良好的平衡，因為相反的會指出實際工作負載所花費的時間比提供核心進程還要多。
* 尋找 `%iowait` 高值百分比可能表示系統持續等候 I/O 要求。
* 高 `%soft` 使用量可能表示高網路流量。

### `vmstat`

此 `vmstat` 公用程式可在大部分的 Linux 散發套件中廣泛提供，可在單一窗格中提供 CPU、記憶體和磁碟 I/O 使用率的高階概觀。
的命令 `vmstat` 為：

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'vmstat -w 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

選項與自變數如下：

* `-w`：使用寬角列印來保留一致的欄。
* `1`：第一個數值自變數會指出以秒為單位重新整理顯示的頻率。
* `5`：第二個數值自變數會指出數據重新整理的次數。

輸出如下：

```output
--procs-- -----------------------memory---------------------- ---swap-- -----io---- -system-- --------cpu--------
   r    b         swpd         free         buff        cache   si   so    bi    bo   in   cs  us  sy  id  wa  st
  14    0            0     26059408          164       137468    0    0    89  3228   56  122   3   1  95   1   0
  14    1            0     24388660          164       145468    0    0     0  7811 3264 13870  76  24   0   0   0
  18    1            0     23060116          164       155272    0    0    44  8075 3704 15129  78  22   0   0   0
  18    1            0     21078640          164       165108    0    0   295  8837 3742 15529  73  27   0   0   0
  15    2            0     19015276          164       175960    0    0     9  8561 3639 15177  73  27   0   0   0
```

`vmstat` 分割六個群組中的輸出：

* `procs`：進程的統計數據。
* `memory`：系統記憶體的統計數據。
* `swap`：交換的統計數據。
* `io`：磁碟 io 的統計數據。
* `system`：內容切換和中斷的統計數據。
* `cpu`：CPU 使用量的統計數據。

>注意： `vmstat` 顯示整個系統的整體統計數據（也就是所有 CPU、匯總的所有區塊裝置）。

#### `procs`

區 `procs` 段有兩個數據行：

* `r`：執行佇列中可執行的進程數目。
* `b`：已封鎖等候 I/O 的進程數目。

本節會立即顯示系統上是否有任何瓶頸。 任一數據行上的高數位表示等候資源的進程佇列。

數據 `r` 行指出等候 CPU 時間能夠執行的進程數目。 解譯這個數字的簡單方式如下：如果佇列中的 `r` 進程數目高於 CPU 總數，則可以推斷系統已大量載入 CPU，而且無法配置所有等候執行的進程 CPU 時間。

數據 `b` 行會指出等待 I/O 要求封鎖執行的進程數目。 此數據行中的高數位表示遇到高 I/O 的系統，而且進程因為其他進程等待完成 I/O 要求而無法執行。 這也表示磁碟延遲很高。

#### `memory`

記憶體區段有四個資料列：

* `swpd`：使用的交換記憶體數量。
* `free`：可用記憶體數量。
* `buff`：用於緩衝區的記憶體數量。
* `cache`：用於快取的記憶體數量。

> [!NOTE]
> 這些值會以位元組顯示。

本節提供記憶體使用量的高階概觀。

#### `swap`

swap 區段有兩個數據行：

* `si`：每秒交換的記憶體數量（從系統記憶體移至交換）。
* `so`：每秒交換的記憶體數量（從交換移至系統記憶體）。

如果觀察到高 `si` ，它可能代表系統記憶體用盡，而且正在移動頁面來交換（swapping）。

#### `io`

區 `io` 段有兩個數據行：

* `bi`：每秒從區塊裝置接收的區塊數目（每秒讀取區塊數）。
* `bo`：每秒傳送至區塊裝置的區塊數目（每秒寫入數）。

> [!NOTE]
> 這些值以每秒的區塊為單位。

#### `system`

區 `system` 段有兩個數據行：

* `in`：每秒中斷的次數。
* `cs`：每秒的內容切換數目。

每秒大量中斷可能表示忙碌於硬體裝置的系統（例如網路作業）。

大量內容切換可能表示具有許多短期執行進程的忙碌系統，此處沒有良好或錯誤的數位。

#### `cpu`

本節有五個數據行：

* `us`：用戶空間百分比使用率。
* `sy`：系統（核心空間）使用率百分比。
* `id`：CPU 閑置時間的使用率百分比。
* `wa`：CPU 閑置等候 I/O 進程的時間百分比使用率。
* `st`：CPU 用於服務其他虛擬 CPU 所花費時間的百分比使用率（不適用於 Azure）。

這些值會以百分比呈現。 這些值與公用程式所呈現 `mpstat` 的值相同，並提供 CPU 使用量的高階概觀。 檢閱這些值時，請遵循類似「要留意[的專案」`mpstat`程式](#mpstat)。

### `uptime`

最後，針對 CPU 相關計量，公用 `uptime` 程式會提供系統負載與負載平均值的廣泛概觀。

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'uptime')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

```output
16:55:53 up 9 min,  2 users,  load average: 9.26, 2.91, 1.18
```

負載平均值會顯示三個數位。 這些數位適用於 `1`系統負載的， `5` 以及 `15` 分鐘間隔。

若要解譯這些值，請務必知道系統中可用的CPU數目，從之前從 `mpstat` 輸出取得。 值取決於 CPU 總數，因此，當輸出的範例 `mpstat` 中，系統有 8 個 CPU，負載平均值 8 表示所有核心都載入到 100%。

值為 `4` 表示 CPU 的一半已載入 100% （或所有 CPU 的總負載 50%） 。 在上一個輸出中，負載平均為 `9.26`，這表示 CPU 會載入約 115%。

`1m`、 `5m``15m` 間隔有助於識別負載是否隨著時間增加或減少。

> [注意]命令 `nproc` 也可以用來取得 CPU 數目。

## 記憶體

針對記憶體，有兩個命令可以取得使用量的詳細數據。

### `free`

命令 `free` 會顯示系統記憶體使用率。

若要執行它：

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'free -h')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

選項與自變數如下：

* `-h`：以動態方式將值顯示為人類可讀的 （例如：Mib、Gib、Tib）

輸出如下：

```output
               total        used        free      shared  buff/cache   available
Mem:            31Gi        19Gi        12Gi        23Mi        87Mi        11Gi
Swap:           23Gi          0B        23Gi
```

從輸出中，尋找系統記憶體總計與可用，以及所使用的與總交換。 可用的記憶體會考慮配置給快取的記憶體，而該記憶體可以針對使用者應用程式傳回。

某些交換使用量在新式核心中很正常，因為一些較不常使用的記憶體頁面可以移至交換。

### `swapon`

此命令 `swapon` 會顯示已設定交換的位置，以及交換裝置或檔案的個別優先順序。

若要執行命令：

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'swapon -s')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

輸出如下：

```output
Filename      Type          Size          Used   Priority
/dev/zram0    partition     16G           0B      100
/mnt/swapfile file          8G            0B      -2
```

此資訊對於確認交換是否設定在不適合的位置上非常重要，例如在數據或OS磁碟上。 在 Azure 參考框架中，交換應該在暫時磁碟驅動器上設定，因為它可提供最佳效能。

### 需要留意的事項

* 請記住，記憶體是有限的資源，一旦系統記憶體（RAM）和交換用盡，進程就會被記憶體不足的殺手（OOM）殺死。
* 確認數據磁碟或 OS 磁碟上未設定交換，因為因為延遲差異而造成 I/O 問題。 交換應該在暫時磁碟驅動器上設定。
* 請記住，在輸出上 `free -h` 通常會看到自由值接近零，此行為是由於頁面快取，核心會視需要釋放這些頁面。

## I/O

磁碟 I/O 是 Azure 節流時最遭受的區域之一，因為磁碟可能會達到 `100ms+` 延遲。 下列命令有助於識別這些案例。

### `iostat`

公用 `iostat` 程式是封裝的 `sysstat` 一部分。 其會顯示每個區塊裝置使用量統計數據，並協助識別區塊相關的效能問題。

公用 `iostat` 程式會提供計量的詳細數據，例如輸送量、延遲和佇列大小。 這些計量有助於瞭解磁碟 I/O 是否成為限制因素。
若要執行，請使用 命令：

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'iostat -dxtm 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

選項與自變數如下：

* `-d`：每個裝置使用量報告。
* `-x`：擴充的統計數據。
* `-t`：顯示每個報表的時間戳。
* `-m`：以 MB/秒顯示。
* `1`：第一個數值自變數會指出以秒為單位重新整理顯示的頻率。
* `2`：第二個數值自變數會指出數據重新整理的次數。

輸出如下：

```output
Linux 5.14.0-362.8.1.el9_3.x86_64 (alma9)       02/21/24        _x86_64_        (8 CPU)

02/21/24 16:55:50
Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
sda              1.07      0.02     0.00   0.00    1.95    20.40   23.25     24.55     3.30  12.42  113.75  1081.06    0.26    537.75     0.26  49.83    0.03 2083250.04    0.00    0.00    2.65   2.42
sdb             16.99      0.67     0.36   2.05    2.00    40.47   65.26      0.44     1.55   2.32    1.32     6.92    0.00      0.00     0.00   0.00    0.00     0.00   30.56    1.30    0.16   7.16
zram0            0.51      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.00   0.00

```

輸出有數個數據行並不重要（由於 選項而 `-x` 額外數據行），其中一些重要數據行如下：

* `r/s`：每秒讀取作業數（IOPS）。
* `rMB/s`：每秒讀取 MB。
* `r_await`：以毫秒為單位讀取延遲。
* `rareq-sz`：以 KB 為單位的平均讀取要求大小。
* `w/s`：每秒寫入作業數（IOPS）。
* `wMB/s`：每秒寫入 MB。
* `w_await`：以毫秒為單位寫入延遲。
* `wareq-size`：平均寫入要求大小以 KB 為單位。
* `aqu-sz`：平均佇列大小。

#### 需要留意的事項

* 尋找 `r/s` 和 `w/s` （IOPS） 和 `rMB/s` ，並 `wMB/s` 確認這些值位於指定磁碟的限制內。 如果值接近或更高限制，磁碟將會受到節流，導致高延遲。 這項資訊也可以與 來自`mpstat`的`%iowait`計量進行證實。
* 延遲是確認磁碟是否如預期般執行的絕佳計量。 一般而言，PremiumSSD 的預期延遲少於 `9ms` 預期，其他供應專案有不同的延遲目標。
* 佇列大小是飽和度的絕佳指標。 一般而言，要求會近乎即時地提供，而且數目仍接近一個（因為佇列永遠不會成長）。 較高的數位可能表示磁碟飽和度（也就是要求佇列）。 此計量沒有好壞的數位。 了解高於一項的任何專案表示要求佇列有助於判斷是否有磁碟飽和度。

### `lsblk`

公用 `lsblk` 程式會顯示連結至系統的區塊裝置，雖然它未提供效能計量，但它可讓您快速概觀這些裝置的設定方式，以及所使用的裝入點。

若要執行，請使用 命令：

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'lsblk')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

輸出如下：

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

#### 需要留意的事項

* 尋找掛接裝置的位置。
* 如果啟用，請確認交換未在數據磁碟或 OS 磁碟內設定。

> 注意：將區塊裝置與 Azure 中的 LUN 相互關聯的簡單方式是執行 `ls -lr /dev/disk/azure`。

## 處理

根據每個程式收集詳細數據有助於了解系統負載的來源。

收集進程靜態的主要公用程式是 `pidstat` 因為它會針對 CPU、記憶體和 I/O 統計數據提供每個進程的詳細數據。

最後，依最上層 CPU 排序程序的簡單 `ps` 方式，記憶體使用量會完成計量。

> [!NOTE]
> 由於這些命令會顯示執行中進程的詳細數據，因此需要使用 以root `sudo`身分執行。 此命令允許顯示所有進程，而不只是使用者。

### `pidstat`

公用 `pidstat` 程式也是封裝的 `sysstat` 一部分。 它就像 `mpstat` 或 iostat，它會在指定時間內顯示計量。 根據預設， `pidstat` 只會顯示具有活動的處理程式計量。

`pidstat`的`sysstat`自變數與其他公用程式相同：

* 1：第一個數值自變數指出以秒為單位重新整理顯示的頻率。
* 2：第二個數值自變數指出數據重新整理的次數。

> [!NOTE]
> 如果有許多具有活動的處理程序，輸出可能會大幅增加。

#### 處理 CPU 統計數據

若要收集行程 CPU 統計數據，請執行 `pidstat` 而不使用任何選項：

如果您要從 Azure CLI 執行命令，可以使用下列命令：

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

輸出如下：

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

此命令會顯示、、 `%guest` `%system`（不適用於 Azure）、`%wait`和總`%CPU`使用量的每個進程使用量`%usr`。

##### 需要留意的事項

* 尋找高 %wait （iowait） 百分比的進程，因為它可能表示已封鎖等候 I/O 的進程，這可能也表示磁碟飽和。
* 確認沒有單一進程耗用 100% 的 CPU，因為它可能表示單個線程的應用程式。

#### 處理記憶體統計數據

若要收集進程記憶體統計數據，請使用 `-r` 選項：

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -r 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

輸出如下：

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

收集的計量如下：

* `minflt/s`：每秒發生次要錯誤，此計量會指出從系統記憶體 （RAM） 載入的頁面數目。
* `mjflt/s`：每秒發生重大錯誤，此計量會指出從磁碟載入的頁面數目（SWAP）。
* `VSZ`：位元組中使用的虛擬記憶體。
* `RSS`：以位元組為單位使用的常駐記憶體（實際配置的記憶體）。
* `%MEM`：所用記憶體總數的百分比。
* `Command`：進程的名稱。

##### 需要留意的事項

* 尋找每秒的主要錯誤，因為此值會指出將頁面交換至磁碟或從磁碟交換的進程。 此行為可能表示記憶體耗盡，而且可能會導致 `OOM` 事件或效能降低，因為交換速度較慢。
* 確認單一進程不會耗用 100% 的可用記憶體。 此行為可能表示記憶體流失。

> [!NOTE]
> `--human`選項可用來以人類可讀格式顯示數位（也就是`Kb`、、 `Mb``GB`。

#### 處理 I/O 統計數據

若要收集進程記憶體統計數據，請使用 `-d` 選項：

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -d 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

輸出如下：

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

收集的計量如下：

* `kB_rd/s`：每秒讀取 KB。
* `kB_wr/s`：每秒寫入 KB。
* `Command`：進程的名稱。

##### 需要留意的事項

* 尋找每秒高讀取/寫入率的單一進程。 這項資訊是 I/O 程式比識別問題更多的指引。
注意：`--human`選項可用來以人類可讀格式顯示數位（也就是、 `Kb`、 `Mb``GB`

### `ps`

`ps`最後，命令會顯示系統進程，而且可以依 CPU 或記憶體排序。

若要依 CPU 排序並取得前 10 個進程：

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

若要依 `MEM%` 序排序並取得前10個進程：

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

## 將所有組合在一起

簡單的Bash腳本可以在單一執行中收集所有詳細數據，並將輸出附加至檔案以供稍後使用：

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2 && vmstat -w 1 5 && uptime && free -h && swapon && iostat -dxtm 1 1 && lsblk && ls -l /dev/disk/azure && pidstat 1 1 -h --human && pidstat -r 1 1 -h --human && pidstat -d 1 1 -h --human && ps aux --sort=-%cpu | head -20 && ps aux --sort=-%mem | head -20')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```

若要執行，您可以建立具有上述內容的檔案、藉由執行 `chmod +x gather.sh`來新增執行許可權，並使用 執行 `sudo ./gather.sh`。

此文稿會將命令的輸出儲存在叫用腳本的相同目錄中的檔案中。

此外，本檔涵蓋的bash區塊代碼中的所有命令都可以 `az-cli` 使用 run-command 擴充功能來執行，並剖析輸出 `jq` ，以取得與在本機執行命令類似的輸出： '

```azurecli-interactive
output=$(az vm run-command invoke -g $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "ls -l /dev/disk/azure")
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```