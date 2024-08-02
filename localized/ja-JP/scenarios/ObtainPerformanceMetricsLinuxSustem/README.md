---
title: Linux システムからのパフォーマンス メトリックの取得
description: Linux システムからパフォーマンス メトリックを取得する方法について説明します。
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

# Linux システムからのパフォーマンス メトリックの取得

**適用対象:** :heavy_check_mark: Linux VM

この記事では、Linux システムからパフォーマンス メトリックをすばやく取得する方法を決定する手順について説明します。

Linux でパフォーマンス カウンターを取得するために使用できるコマンドがいくつかあります。 `vmstat`や`uptime`などのコマンドは、CPU 使用率、システム メモリ、システム負荷などの一般的なシステム メトリックを提供します。
ほとんどのコマンドは既定で既にインストールされており、他のコマンドは既定のリポジトリですぐに使用できます。
コマンドは次のように分割できます。

* CPU
* メモリ
* ディスク I/O
* 処理

## Sysstat ユーティリティのインストール

<!-- Commenting out these entries as this information should be selected by the user along with the corresponding subscription and region

The First step in this tutorial is to define environment variables, and install the corresponding package, if necessary.

```azurecli-interactive
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup89f292"
export MY_VM_NAME="myVM89f292"
```
-->

> [!NOTE]
> 関連するすべての詳細を収集するには、これらのコマンドの一部を `root` として実行する必要があります。

> [!NOTE]
> 一部のコマンドは、既定ではインストールされない可能性がある `sysstat` パッケージの一部です。 パッケージは、人気のあるディストリビューションの `sudo apt install sysstat`、 `dnf install sysstat` 、または `zypper install sysstat` で簡単にインストールできます。

一般的なディストリビューションに `sysstat` パッケージをインストールするための完全なコマンドは次のとおりです。

```bash
az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "/bin/bash -c 'OS=\$(cat /etc/os-release|grep NAME|head -1|cut -d= -f2 | sed \"s/\\\"//g\"); if [[ \$OS =~ \"Ubuntu\" ]] || [[ \$OS =~ \"Debian\" ]]; then sudo apt install sysstat -y; elif [[ \$OS =~ \"Red Hat\" ]]; then sudo dnf install sysstat -y; elif [[ \$OS =~ \"SUSE\" ]]; then sudo zypper install sysstat --non-interactive; else echo \"Unknown distribution\"; fi'"
```

## CPU

### <a id="mpstat"></a>mpstat

`mpstat` ユーティリティは、`sysstat` パッケージの一部です。 CPU 使用率と平均ごとに表示されます。これは、CPU 使用率をすばやく識別するのに役立ちます。 `mpstat` では、使用可能な CPU 全体の CPU 使用率の概要が示され、使用量のバランスと、1 つの CPU が大量に読み込まれているかどうかを特定するのに役立ちます。

完全なコマンドは次のとおりです。

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

オプションと引数は次のとおりです。

* `-P`: 統計を表示するプロセッサを示し、ALL 引数はシステム内のすべてのオンライン CPU の統計を表示することを示します。
* `1`: 最初の数値引数は、表示を更新する頻度を秒単位で示します。
* `2`: 2 番目の数値引数は、データが更新される回数を示します。

`mpstat` コマンドでデータを表示する回数は、2 番目の数値引数を増やしてデータ収集時間を長くすることで変更できます。 コア数が 2 秒増加したシステムでは、表示されるデータの量を減らすために使用できる場合、理想的には 3 秒または 5 秒で十分です。
出力から:

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

注意すべき重要な点がいくつかあります。 最初の行には、有用な情報が表示されます。

* カーネルとリリース: `5.14.0-362.8.1.el9_3.x86_64`
* ホスト名: `alma9`
* 日付： `02/21/24`
* 建築： `_x86_64_`
* CPU の総量 (この情報は、他のコマンドからの出力を解釈するのに役立ちます)。 `(8 CPU)`

次に、各列について説明するために、CPU のメトリックが表示されます。

* `Time`: サンプルが収集された時刻
* `CPU`: CPU 数値識別子。ALL 識別子は、すべての CPU の平均です。
* `%usr`: ユーザー領域 (通常はユーザー アプリケーション) の CPU 使用率の割合。
* `%nice`: 良好な (優先順位) 値を持つユーザー空間プロセスの CPU 使用率の割合。
* `%sys`: カーネル 空間プロセスの CPU 使用率の割合。
* `%iowait`: 未処理の I/O の待機中にアイドル状態に費やされた CPU 時間の割合。
* `%irq`: ハードウェア割り込みの処理に費やされた CPU 時間の割合。
* `%soft`: ソフトウェア割り込みの処理に費やされた CPU 時間の割合。
* `%steal`:他の仮想マシンのサービスに費やされた CPU 時間の割合 (CPU のオーバープロビジョニングがないため、Azure には適用されません)。
* `%guest`: 仮想 CPU の提供に費やされた CPU 時間の割合 (Azure には適用されず、仮想マシンを実行するベア メタル システムにのみ適用されます)。
* `%gnice`: 適切な値で仮想 CPU の提供に費やされた CPU 時間の割合 (Azure には適用されず、仮想マシンを実行するベア メタル システムにのみ適用されます)。
* `%idle`: I/O 要求を待機せずにアイドル状態に費やされた CPU 時間の割合。

#### 注意事項

`mpstat`の出力を確認する際に留意すべきいくつかの詳細:

* すべての CPU が正しく読み込まれ、1 つの CPU ですべての負荷が処理されていないことを確認します。 この情報は、シングル スレッド アプリケーションを示している可能性があります。
* `%usr`と`%sys`の間の正常なバランスを探します。逆の場合は、カーネル プロセスにサービスを提供するよりも実際のワークロードに費やされた時間が長くなります。
* 高い値が I/O 要求を常に待機しているシステムを示している可能性がある `%iowait` パーセンテージを探します。
* `%soft`使用率が高い場合は、ネットワーク トラフィックが多い可能性があります。

### `vmstat`

`vmstat` ユーティリティは、ほとんどの Linux ディストリビューションで広く使用でき、CPU、メモリ、ディスク I/O 使用率の概要を 1 つのウィンドウで提供します。
`vmstat`のコマンドは次のとおりです。

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'vmstat -w 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

オプションと引数は次のとおりです。

* `-w`: 幅の広い印刷を使用して、一貫性のある列を維持します。
* `1`: 最初の数値引数は、表示を更新する頻度を秒単位で示します。
* `5`: 2 番目の数値引数は、データが更新される回数を示します。

出力は次のようになります。

```output
--procs-- -----------------------memory---------------------- ---swap-- -----io---- -system-- --------cpu--------
   r    b         swpd         free         buff        cache   si   so    bi    bo   in   cs  us  sy  id  wa  st
  14    0            0     26059408          164       137468    0    0    89  3228   56  122   3   1  95   1   0
  14    1            0     24388660          164       145468    0    0     0  7811 3264 13870  76  24   0   0   0
  18    1            0     23060116          164       155272    0    0    44  8075 3704 15129  78  22   0   0   0
  18    1            0     21078640          164       165108    0    0   295  8837 3742 15529  73  27   0   0   0
  15    2            0     19015276          164       175960    0    0     9  8561 3639 15177  73  27   0   0   0
```

`vmstat` では、出力が 6 つのグループに分割されます。

* `procs`: プロセスの統計。
* `memory`: システム メモリの統計。
* `swap`: スワップの統計。
* `io`: ディスク io の統計。
* `system`: コンテキスト スイッチと割り込みの統計。
* `cpu`: CPU 使用率の統計。

>注: `vmstat` は、システム全体の全体的な統計 (つまり、すべての CPU、集計されたすべてのブロック デバイス) を示します。

#### `procs`

`procs` セクションには、次の 2 つの列があります。

* `r`: 実行キュー内の実行可能なプロセスの数。
* `b`: I/O の待機中にブロックされたプロセスの数。

このセクションでは、システムにボトルネックがあるかどうかをすぐに示します。 いずれかの列で大きい数値は、リソースを待機しているプロセスを示しています。

`r`列は、CPU 時間の実行を待機しているプロセスの数を示します。 この数を解釈する簡単な方法は次のとおりです。 `r` キュー内のプロセスの数が CPU の合計数より多い場合は、システムに CPU が大量に読み込まれており、実行を待機しているすべてのプロセスに CPU 時間を割り当てることができないと推定できます。

`b`列は、I/O 要求によってブロックされている実行を待機しているプロセスの数を示します。 この列の数値が大きいと、I/O が高いシステムが発生し、完了した I/O 要求を待機している他のプロセスが原因でプロセスを実行できないことを示します。 これは、ディスクの待ち時間が長くなることも示している可能性があります。

#### `memory`

memory セクションには、次の 4 つの列があります。

* `swpd`: 使用されるスワップ メモリの量。
* `free`: 空きメモリの量。
* `buff`: バッファーに使用されるメモリの量。
* `cache`: キャッシュに使用されるメモリの量。

> [!NOTE]
> 値はバイト単位で表示されます。

このセクションでは、メモリ使用量の概要について説明します。

#### `swap`

swap セクションには、次の 2 つの列があります。

* `si`: 1 秒あたりにスワップされた (システム メモリからスワップに移動された) メモリの量。
* `so`: 1 秒あたりにスワップアウトされたメモリの量 (スワップからシステム メモリに移動)。

`si`が高い場合は、システム メモリが不足しており、ページをスワップ (スワップ) に移動しているシステムを表している可能性があります。

#### `io`

`io` セクションには、次の 2 つの列があります。

* `bi`: 1 秒あたりにブロック デバイスから受信したブロックの数 (1 秒あたりのブロックの読み取り)。
* `bo`: 1 秒あたりにブロック デバイスに送信されるブロックの数 (1 秒あたりの書き込み)。

> [!NOTE]
> これらの値は、1 秒あたりのブロック単位です。

#### `system`

`system` セクションには、次の 2 つの列があります。

* `in`: 1 秒あたりの割り込みの数。
* `cs`: 1 秒あたりのコンテキスト スイッチの数。

1 秒あたりの割り込みの数が多い場合は、ハードウェア デバイス (ネットワーク操作など) でビジー状態になっているシステムを示している可能性があります。

コンテキスト スイッチの数が多い場合は、実行中のプロセスが多数あるビジー状態のシステムを示している可能性があります。ここには適切な数も悪い数もありません。

#### `cpu`

このセクションには、次の 5 つの列があります。

* `us`: ユーザー領域の使用率。
* `sy`: システム (カーネル領域) 使用率。
* `id`: CPU がアイドル状態である時間の使用率の割合。
* `wa`: CPU が I/O を使用するプロセスを待機しているアイドル時間の使用率の割合。
* `st`: CPU が他の仮想 CPU の提供に費やした時間の使用率 (Azure には適用されません)。

値はパーセンテージで表示されます。 これらの値は、 `mpstat` ユーティリティによって提示される値と同じであり、CPU 使用率の概要を提供するのに役立ちます。 これらの値を確認するときに、`mpstat`の "[Things to look out for look out](#mpstat)" の同様のプロセスに従います。

### `uptime`

最後に、CPU 関連のメトリックの場合、 `uptime` ユーティリティは、負荷の平均値を使用したシステム負荷の概要を提供します。

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'uptime')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

```output
16:55:53 up 9 min,  2 users,  load average: 9.26, 2.91, 1.18
```

負荷平均には 3 つの数値が表示されます。 これらの数値は、システム負荷の `1`、 `5` 、 `15` 分間隔を対象とします。

これらの値を解釈するには、前に `mpstat` 出力から取得したシステム内の使用可能な CPU の数を把握することが重要です。 この値は CPU の合計に依存するため、 `mpstat` 出力の例として、システムには 8 個の CPU があり、負荷平均 8 は、すべてのコアが 100% に読み込まれることを意味します。

`4`の値は、CPU の半分が 100% (またはすべての CPU で合計 50% の負荷) で読み込まれたことを意味します。 前の出力では、負荷平均は `9.26`です。つまり、CPU は約 115% で読み込まれます。

`1m`、`5m`、`15m`間隔は、時間の経過と同時に負荷が増加または減少しているかどうかを識別するのに役立ちます。

> [注] `nproc` コマンドを使用して、CPU の数を取得することもできます。

## [メモリ]

メモリの場合、使用状況に関する詳細を取得できる 2 つのコマンドがあります。

### `free`

`free` コマンドは、システム メモリ使用率を示します。

これを実行するには:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'free -h')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

オプションと引数は次のとおりです。

* `-h`: 値を人間が判読できるものとして動的に表示します (例: Mib、Gib、Tib)

出力は次のようになります。

```output
               total        used        free      shared  buff/cache   available
Mem:            31Gi        19Gi        12Gi        23Mi        87Mi        11Gi
Swap:           23Gi          0B        23Gi
```

出力から、システム メモリの合計と使用可能なメモリ、および使用されたスワップと合計スワップを探します。 使用可能なメモリは、キャッシュに割り当てられたメモリを考慮に入れ、ユーザー アプリケーションに対して返すことができます。

スワップの一部は、スワップに移動できるメモリ ページの使用頻度が低いため、最新のカーネルでは通常の使用です。

### `swapon`

`swapon` コマンドは、スワップが構成されている場所と、スワップ デバイスまたはファイルのそれぞれの優先順位を表示します。

コマンドを実行するには、次の手順を実行します。

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'swapon -s')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

出力は次のようになります。

```output
Filename      Type          Size          Used   Priority
/dev/zram0    partition     16G           0B      100
/mnt/swapfile file          8G            0B      -2
```

この情報は、データや OS ディスクなど、理想的ではない場所でスワップが構成されているかどうかを確認するために重要です。 Azure の参照フレームでは、最適なパフォーマンスを提供するエフェメラル ドライブでスワップを構成する必要があります。

### 注意事項

* メモリは有限のリソースであることに注意してください。システム メモリ (RAM) とスワップの両方が使い果たされると、プロセスは Out Of Memorry キラー (OOM) によって強制終了されます。
* データ ディスクまたは OS ディスクでスワップが構成されていないことを確認します。これは、待機時間の違いにより I/O に問題が発生するためです。 スワップはエフェメラル ドライブで構成する必要があります。
* また、空き値が 0 に近い `free -h` 出力で表示されるのが一般的であることに注意してください。この動作はページ キャッシュが原因で、カーネルは必要に応じてそれらのページを解放します。

## I/O

ディスク I/O は、ディスクが `100ms+` 待機時間に達する可能性があり、調整されたときに Azure が最も苦しむ領域の 1 つです。 次のコマンドは、これらのシナリオを識別するのに役立ちます。

### `iostat`

`iostat` ユーティリティは、`sysstat` パッケージの一部です。 ブロック デバイスごとの使用状況の統計情報が表示され、ブロック関連のパフォーマンスの問題を特定するのに役立ちます。

`iostat` ユーティリティは、スループット、待機時間、キュー サイズなどのメトリックの詳細を提供します。 これらのメトリックは、ディスク I/O が制限要因になるかどうかを理解するのに役立ちます。
実行するには、次のコマンドを使用します。

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'iostat -dxtm 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

オプションと引数は次のとおりです。

* `-d`: デバイスごとの使用状況レポート。
* `-x`: 拡張統計。
* `-t`: 各レポートのタイムスタンプを表示します。
* `-m`: MB/秒で表示します。
* `1`: 最初の数値引数は、表示を更新する頻度を秒単位で示します。
* `2`: 2 番目の数値引数は、データが更新される回数を示します。

出力は次のようになります。

```output
Linux 5.14.0-362.8.1.el9_3.x86_64 (alma9)       02/21/24        _x86_64_        (8 CPU)

02/21/24 16:55:50
Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
sda              1.07      0.02     0.00   0.00    1.95    20.40   23.25     24.55     3.30  12.42  113.75  1081.06    0.26    537.75     0.26  49.83    0.03 2083250.04    0.00    0.00    2.65   2.42
sdb             16.99      0.67     0.36   2.05    2.00    40.47   65.26      0.44     1.55   2.32    1.32     6.92    0.00      0.00     0.00   0.00    0.00     0.00   30.56    1.30    0.16   7.16
zram0            0.51      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.00   0.00

```

出力には、重要ではない列がいくつか含まれています ( `-x` オプションにより追加の列)、重要な列の一部は次のとおりです。

* `r/s`: 1 秒あたりの読み取り操作数 (IOPS)。
* `rMB/s`: 1 秒あたりの読み取りメガバイト数。
* `r_await`: 読み取り待機時間 (ミリ秒単位)。
* `rareq-sz`: 平均読み取り要求サイズ (KB 単位)。
* `w/s`: 1 秒あたりの書き込み操作数 (IOPS)。
* `wMB/s`: 1 秒あたりの書き込みメガバイト数。
* `w_await`: 書き込み待機時間 (ミリ秒単位)。
* `wareq-size`: 書き込み要求の平均サイズ (KB 単位)。
* `aqu-sz`: 平均キュー サイズ。

#### 注意事項

* `r/s`と`w/s` (IOPS) と`rMB/s`と`wMB/s`を探し、これらの値が指定されたディスクの制限内にあることを確認します。 値が制限に近いか大きい場合は、ディスクが調整され、待機時間が長くなります。 この情報は、`mpstat`の`%iowait`メトリックで補強することもできます。
* 待機時間は、ディスクが期待どおりに実行されているかどうかを確認するための優れたメトリックです。 通常、PremiumSSD の待ち時間は `9ms` 未満で、他のオファリングの待機時間ターゲットは異なります。
* キュー サイズは、飽和状態を示す優れたインジケーターです。 通常、要求はほぼリアルタイムで処理され、数は 1 に近いままです (キューが増えることはありません)。 数値が大きいほど、ディスクの飽和状態 (つまり、要求のキューアップ) を示している可能性があります。 このメトリックの良い数値も悪い数値もありません。 1 つ以上の値を指定すると、要求がキューに入っていることを意味し、ディスクの飽和状態が発生しているかどうかを判断するのに役立ちます。

### `lsblk`

`lsblk` ユーティリティは、システムに接続されているブロック デバイスを示しますが、パフォーマンス メトリックは提供されませんが、これらのデバイスの構成方法と使用されているマウントポイントの概要を簡単に確認できます。

実行するには、次のコマンドを使用します。

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'lsblk')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

出力は次のようになります。

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

#### 注意事項

* デバイスがマウントされている場所を探します。
* 有効になっている場合は、スワップがデータ ディスクまたは OS ディスク内で構成されていないことを確認します。

> 注: ブロック デバイスを Azure の LUN に関連付ける簡単な方法は、 `ls -lr /dev/disk/azure`を実行することです。

## プロセス

プロセスごとに詳細を収集すると、システムの負荷の発生元を把握するのに役立ちます。

プロセス静的を収集する主なユーティリティは、CPU、メモリ、および I/O 統計のプロセスごとの詳細を提供するため、 `pidstat` です。

最後に、上位の CPU でプロセスを並べ替える単純な `ps` で、メモリ使用量によってメトリックが完了します。

> [!NOTE]
> これらのコマンドは実行中のプロセスに関する詳細を表示するため、 `sudo`を使用して root として実行する必要があります。 このコマンドを使用すると、ユーザーだけでなく、すべてのプロセスを表示できます。

### `pidstat`

`pidstat` ユーティリティは、`sysstat` パッケージの一部でもあります。 これは、特定の時間のメトリックを表示する `mpstat` や iostat のようなものです。 既定では、 `pidstat` にはアクティビティを含むプロセスのメトリックのみが表示されます。

`pidstat`の引数は、他の`sysstat` ユーティリティでも同じです。

* 1: 最初の数値引数は、表示を更新する頻度を秒単位で示します。
* 2: 2 番目の数値引数は、データが更新される回数を示します。

> [!NOTE]
> アクティビティを含むプロセスが多数ある場合、出力は大幅に増加する可能性があります。

#### CPU 統計の処理

プロセス CPU 統計を収集するには、オプションを指定せずに `pidstat` を実行します。

Azure CLI から実行する場合は、次のコマンドを使用できます。

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

出力は次のようになります。

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

このコマンドは、 `%usr`、 `%system`、 `%guest` (Azure には適用されません)、 `%wait`、および合計 `%CPU` 使用量のプロセスごとの使用状況を表示します。

##### 注意事項

* I/O の待機中にブロックされているプロセスを示している可能性があるため、%wait (アイオワイト) の割合が高いプロセスを探します。これは、ディスクの飽和も示している可能性があります。
* シングル スレッド アプリケーションを示す可能性があるため、CPU の 100% を消費するプロセスが 1 つないことを確認します。

#### プロセス メモリの統計情報

プロセス メモリ統計を収集するには、 `-r` オプションを使用します。

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -r 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

出力は次のようになります。

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

収集されるメトリックは次のとおりです。

* `minflt/s`: 1 秒あたりの軽微な障害。このメトリックは、システム メモリ (RAM) から読み込まれたページの数を示します。
* `mjflt/s`: 1 秒あたりの重大な障害。このメトリックは、ディスク (SWAP) から読み込まれたページの数を示します。
* `VSZ`: バイト単位で使用される仮想メモリ。
* `RSS`: 使用された常駐メモリ (実際に割り当てられたメモリ) (バイト単位)。
* `%MEM`: 使用されたメモリの合計に対する割合。
* `Command`: プロセスの名前。

##### 注意事項

* この値はディスクとの間でページをスワップしているプロセスを示すので、1 秒あたりの重大な障害を探します。 この動作はメモリ不足を示す可能性があり、 `OOM` イベントや、スワップの速度低下によるパフォーマンスの低下につながる可能性があります。
* 1 つのプロセスが使用可能なメモリの 100% を消費していないことを確認します。 この動作は、メモリ リークを示している可能性があります。

> [!NOTE]
> `--human` オプションを使用すると、人間が判読できる形式 (つまり、`Kb`、`Mb`、`GB`) で数値を表示できます。

#### I/O 統計の処理

プロセス メモリ統計を収集するには、 `-d` オプションを使用します。

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -d 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

出力は次のようになります。

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

収集されるメトリックは次のとおりです。

* `kB_rd/s`: 1 秒あたりキロバイトを読み取ります。
* `kB_wr/s`: 1 秒あたりキロバイトを書き込みます。
* `Command`: プロセスの名前。

##### 注意事項

* 1 秒あたりの読み取り/書き込み率が高い 1 つのプロセスを探します。 この情報は、問題を特定する以上の I/O を使用するプロセスのガイダンスです。
注: `--human` オプションを使用すると、人間が判読できる形式 (つまり、 `Kb`、 `Mb`、 `GB`) で数値を表示できます。

### `ps`

最後に、 `ps` コマンドはシステム プロセスを表示し、CPU またはメモリで並べ替えることができます。

CPU で並べ替えて上位 10 個のプロセスを取得するには:

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

`MEM%`で並べ替え、上位 10 個のプロセスを取得するには:

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

## すべてをまとめる

単純な bash スクリプトでは、1 回の実行ですべての詳細を収集し、後で使用するために出力をファイルに追加できます。

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2 && vmstat -w 1 5 && uptime && free -h && swapon && iostat -dxtm 1 1 && lsblk && ls -l /dev/disk/azure && pidstat 1 1 -h --human && pidstat -r 1 1 -h --human && pidstat -d 1 1 -h --human && ps aux --sort=-%cpu | head -20 && ps aux --sort=-%mem | head -20')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```

実行するには、上記の内容のファイルを作成し、 `chmod +x gather.sh`を実行して実行アクセス許可を追加し、 `sudo ./gather.sh`で実行できます。

このスクリプトは、コマンドの出力を、スクリプトが呼び出されたのと同じディレクトリにあるファイルに保存します。

さらに、このドキュメントで説明する bash ブロック コード内のすべてのコマンドは、run-command 拡張機能を使用して `az-cli` を実行し、 `jq` を介して出力を解析して、コマンドをローカルで実行するのと同様の出力を取得できます。

```azurecli-interactive
output=$(az vm run-command invoke -g $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "ls -l /dev/disk/azure")
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```