---
title: Linux 시스템에서 성능 메트릭 가져오기
description: Linux 시스템에서 성능 메트릭을 가져오는 방법을 알아봅니다.
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

# Linux 시스템에서 성능 메트릭 가져오기

**적용 대상:** :heavy_check_mark: Linux VM

이 문서에서는 Linux 시스템에서 성능 메트릭을 빠르게 가져오는 방법을 결정하는 지침을 다룹니다.

Linux에서 성능 카운터를 가져오는 데 사용할 수 있는 몇 가지 명령이 있습니다. 명령(예: `vmstat` `uptime`및 )은 CPU 사용량, 시스템 메모리 및 시스템 로드와 같은 일반적인 시스템 메트릭을 제공합니다.
대부분의 명령은 기본적으로 이미 설치되어 있으며 다른 명령은 기본 리포지토리에서 쉽게 사용할 수 있습니다.
명령을 다음으로 구분할 수 있습니다.

* CPU
* 메모리
* 디스크 I/O
* 프로세스

## Sysstat 유틸리티 설치

<!-- Commenting out these entries as this information should be selected by the user along with the corresponding subscription and region

The First step in this tutorial is to define environment variables, and install the corresponding package, if necessary.

```azurecli-interactive
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup89f292"
export MY_VM_NAME="myVM89f292"
```
-->

> [!NOTE]
> 이러한 명령 중 일부는 모든 관련 세부 정보를 수집할 수 있도록 실행 `root` 해야 합니다.

> [!NOTE]
> 일부 명령은 기본적으로 설치되지 않을 수 있는 패키지의 `sysstat` 일부입니다. 패키지는 또는 인기 있는 배포판과 함께 `sudo apt install sysstat``dnf install sysstat` `zypper install sysstat` 쉽게 설치할 수 있습니다.

인기 있는 배포판에 패키지를 설치하기 `sysstat` 위한 전체 명령은 다음과 같습니다.

```bash
az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "/bin/bash -c 'OS=\$(cat /etc/os-release|grep NAME|head -1|cut -d= -f2 | sed \"s/\\\"//g\"); if [[ \$OS =~ \"Ubuntu\" ]] || [[ \$OS =~ \"Debian\" ]]; then sudo apt install sysstat -y; elif [[ \$OS =~ \"Red Hat\" ]]; then sudo dnf install sysstat -y; elif [[ \$OS =~ \"SUSE\" ]]; then sudo zypper install sysstat --non-interactive; else echo \"Unknown distribution\"; fi'"
```

## CPU

### <a id="mpstat"></a>mpstat

유틸리티 `mpstat` 는 패키지의 `sysstat` 일부입니다. CPU 사용률 및 평균별로 표시되므로 CPU 사용량을 빠르게 식별하는 데 도움이 됩니다. `mpstat` 에서는 사용 가능한 CPU 전체의 CPU 사용률에 대한 개요를 제공하여 사용량 균형을 식별하고 단일 CPU가 많이 로드되는지 여부를 식별할 수 있습니다.

전체 명령은 다음과 같습니다.

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

옵션 및 인수는 다음과 같습니다.

* `-P`: 통계를 표시하는 프로세서를 나타내며, ALL 인수는 시스템의 모든 온라인 CPU에 대한 통계를 표시하도록 나타냅니다.
* `1`: 첫 번째 숫자 인수는 디스플레이를 새로 고치는 빈도(초)를 나타냅니다.
* `2`: 두 번째 숫자 인수는 데이터가 새로 고쳐진 횟수를 나타냅니다.

두 번째 숫자 인수를 `mpstat` 늘려 더 긴 데이터 수집 시간을 수용하여 명령에서 데이터를 표시하는 횟수를 변경할 수 있습니다. 이상적으로는 3초 또는 5초로 충분합니다. 코어 수가 2초 증가한 시스템의 경우 표시되는 데이터의 양을 줄이는 데 사용할 수 있습니다.
출력에서:

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

몇 가지 중요한 사항에 유의해야 합니다. 첫 번째 줄에는 유용한 정보가 표시됩니다.

* 커널 및 릴리스: `5.14.0-362.8.1.el9_3.x86_64`
* 호스트 이름: `alma9`
* 날짜: `02/21/24`
* 건축학: `_x86_64_`
* 총 CPU 양(이 정보는 다른 명령의 출력을 해석하는 데 유용합니다.) `(8 CPU)`

그런 다음 CPU에 대한 메트릭이 표시되어 각 열을 설명합니다.

* `Time`: 샘플이 수집된 시간
* `CPU`: CPU 숫자 식별자, ALL 식별자는 모든 CPU의 평균입니다.
* `%usr`: 사용자 공간, 일반적으로 사용자 애플리케이션에 대한 CPU 사용률 비율입니다.
* `%nice`: 좋은(우선 순위) 값을 가진 사용자 공간 프로세스의 CPU 사용률 비율입니다.
* `%sys`: 커널 공간 프로세스의 CPU 사용률 비율입니다.
* `%iowait`: 미해결 I/O를 기다리는 동안 유휴 상태로 소요된 CPU 시간의 백분율입니다.
* `%irq`: 하드웨어 인터럽트 처리에 소요된 CPU 시간의 백분율입니다.
* `%soft`: 소프트웨어 인터럽트 처리에 소요된 CPU 시간의 비율입니다.
* `%steal`: 다른 가상 머신을 제공하는 데 소요된 CPU 시간의 비율입니다(CPU의 과잉 프로비전이 없어 Azure에는 적용되지 않음).
* `%guest`: 가상 CPU를 제공하는 데 소요된 CPU 시간의 비율입니다(Azure에는 적용되지 않으며 가상 머신을 실행하는 운영 체제에만 적용됨).
* `%gnice`: 좋은 값으로 가상 CPU를 제공하는 데 소요된 CPU 시간의 비율입니다(Azure에는 적용되지 않으며 가상 머신을 실행하는 운영 체제에만 적용 가능).
* `%idle`: I/O 요청을 기다리지 않고 유휴 상태로 소요된 CPU 시간의 비율입니다.

#### 알아야 할 사항

출력을 검토할 `mpstat`때 유의해야 할 몇 가지 세부 사항은 다음과 같습니다.

* 모든 CPU가 제대로 로드되고 단일 CPU가 모든 부하를 처리하지 않는지 확인합니다. 이 정보는 단일 스레드 애플리케이션을 나타낼 수 있습니다.
* 커널 프로세스를 처리하는 것보다 실제 워크로드에 더 많은 시간을 소비하는 것을 나타내기 때문에 둘 사이의 `%usr` `%sys` 정상 균형을 찾습니다.
* `%iowait` 높은 값이 I/O 요청을 지속적으로 기다리는 시스템을 나타낼 수 있으므로 백분율을 찾습니다.
* `%soft` 높은 사용량은 높은 네트워크 트래픽을 나타낼 수 있습니다.

### `vmstat`

이 `vmstat` 유틸리티는 대부분의 Linux 배포판에서 널리 사용할 수 있으며, 단일 창에서 CPU, 메모리 및 디스크 I/O 사용률에 대한 개략적인 개요를 제공합니다.
에 대한 `vmstat` 명령은 다음과 같습니다.

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'vmstat -w 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

옵션 및 인수는 다음과 같습니다.

* `-w`: 와이드 인쇄를 사용하여 일관된 열을 유지합니다.
* `1`: 첫 번째 숫자 인수는 디스플레이를 새로 고치는 빈도(초)를 나타냅니다.
* `5`: 두 번째 숫자 인수는 데이터가 새로 고쳐진 횟수를 나타냅니다.

출력은 다음과 같습니다.

```output
--procs-- -----------------------memory---------------------- ---swap-- -----io---- -system-- --------cpu--------
   r    b         swpd         free         buff        cache   si   so    bi    bo   in   cs  us  sy  id  wa  st
  14    0            0     26059408          164       137468    0    0    89  3228   56  122   3   1  95   1   0
  14    1            0     24388660          164       145468    0    0     0  7811 3264 13870  76  24   0   0   0
  18    1            0     23060116          164       155272    0    0    44  8075 3704 15129  78  22   0   0   0
  18    1            0     21078640          164       165108    0    0   295  8837 3742 15529  73  27   0   0   0
  15    2            0     19015276          164       175960    0    0     9  8561 3639 15177  73  27   0   0   0
```

`vmstat` 는 출력을 6개의 그룹으로 분할합니다.

* `procs`: 프로세스에 대한 통계입니다.
* `memory`: 시스템 메모리에 대한 통계입니다.
* `swap`: 스왑에 대한 통계입니다.
* `io`: 디스크 io에 대한 통계입니다.
* `system`: 컨텍스트 전환 및 인터럽트 통계입니다.
* `cpu`: CPU 사용량에 대한 통계입니다.

>참고: `vmstat` 전체 시스템(즉, 모든 CPU, 집계된 모든 블록 디바이스)에 대한 전체 통계를 보여 줍니다.

#### `procs`

섹션 `procs` 에는 두 개의 열이 있습니다.

* `r`: 실행 큐의 실행 가능한 프로세스 수입니다.
* `b`: I/O를 기다리는 동안 차단된 프로세스의 수입니다.

이 섹션에서는 시스템에 병목 현상이 있는지 즉시 보여줍니다. 두 열 중 하나의 숫자가 많을수록 리소스를 기다리는 프로세스가 대기 중임을 나타냅니다.

열은 `r` CPU 시간이 실행되기를 기다리는 프로세스 수를 나타냅니다. 이 숫자를 해석하는 쉬운 방법은 다음과 같습니다. 큐의 프로세스 `r` 수가 총 CPU 수보다 크면 시스템에 CPU가 많이 로드되어 실행을 기다리는 모든 프로세스에 CPU 시간을 할당할 수 없다고 유추할 수 있습니다.

열은 `b` I/O 요청에 의해 차단되는 실행 대기 중인 프로세스 수를 나타냅니다. 이 열의 숫자가 많으면 I/O가 높은 시스템을 나타내며 완료된 I/O 요청을 기다리는 다른 프로세스로 인해 프로세스를 실행할 수 없습니다. 디스크 대기 시간이 높음을 나타낼 수도 있습니다.

#### `memory`

메모리 섹션에는 4개의 열이 있습니다.

* `swpd`: 사용된 교환 메모리 양입니다.
* `free`: 사용 가능한 메모리 양입니다.
* `buff`: 버퍼에 사용되는 메모리 양입니다.
* `cache`: 캐시에 사용되는 메모리 양입니다.

> [!NOTE]
> 값은 바이트 단위로 표시됩니다.

이 섹션에서는 메모리 사용량에 대한 개략적인 개요를 제공합니다.

#### `swap`

스왑 섹션에는 두 개의 열이 있습니다.

* `si`: 초당 교환된 메모리 양(시스템 메모리에서 스왑으로 이동)입니다.
* `so`: 초당 교환된 메모리 양(스왑에서 시스템 메모리로 이동)입니다.

높음 `si` 이 관찰되면 시스템 메모리가 부족하고 페이지를 전환(교환)으로 이동하는 시스템을 나타낼 수 있습니다.

#### `io`

섹션 `io` 에는 두 개의 열이 있습니다.

* `bi`: 초당 블록 디바이스에서 수신된 블록 수(초당 블록 읽기)입니다.
* `bo`: 초당 블록 디바이스로 전송된 블록 수(초당 쓰기 수)입니다.

> [!NOTE]
> 이러한 값은 초당 블록 단위입니다.

#### `system`

섹션 `system` 에는 두 개의 열이 있습니다.

* `in`: 초당 인터럽트 수입니다.
* `cs`: 초당 컨텍스트 전환 수입니다.

초당 인터럽트 수가 많을수록 하드웨어 디바이스(예: 네트워크 작업)로 사용 중인 시스템을 나타낼 수 있습니다.

많은 수의 컨텍스트 스위치는 짧은 실행 프로세스가 많은 사용 중인 시스템을 나타낼 수 있으며 여기에 양호하거나 나쁜 숫자가 없습니다.

#### `cpu`

이 섹션에는 5개의 열이 있습니다.

* `us`: 사용자 공간 백분율 사용률입니다.
* `sy`: 시스템(커널 공간) 사용률입니다.
* `id`: CPU가 유휴 상태인 시간의 백분율 사용률입니다.
* `wa`: CPU가 I/O를 사용하여 프로세스를 대기하는 동안 유휴 상태인 시간의 백분율 사용률입니다.
* `st`: CPU가 다른 가상 CPU를 제공하는 데 소요된 시간의 백분율 사용률입니다(Azure에는 적용되지 않음).

값은 백분율로 표시됩니다. 이러한 값은 유틸리티에서 제공하는 `mpstat` 것과 동일하며 CPU 사용량에 대한 개략적인 개요를 제공합니다. 이러한 값을 검토할 때 "[살펴볼](#mpstat) 항목"에 대해 `mpstat` 유사한 프로세스를 따릅니다.

### `uptime`

마지막으로 CPU 관련 메트릭의 `uptime` 경우 이 유틸리티는 부하 평균 값을 사용하여 시스템 부하에 대한 광범위한 개요를 제공합니다.

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'uptime')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

```output
16:55:53 up 9 min,  2 users,  load average: 9.26, 2.91, 1.18
```

부하 평균은 세 개의 숫자를 표시합니다. 이러한 숫자는 시스템 로드의 분 `5` 간격에 `15` 대한 `1`것입니다.

이러한 값을 해석하려면 시스템에서 사용 가능한 CPU의 수를 알고 있는 것이 중요하며, 이전 출력에서 `mpstat` 얻은 것입니다. 값은 총 CPU에 따라 달라지므로 시스템에 CPU가 8개 있는 출력의 `mpstat` 예로, 부하 평균이 8이면 모든 코어가 100%로 로드됩니다.

값 `4` 은 CPU의 절반이 100%(또는 모든 CPU에서 총 50% 부하)로 로드되었음을 의미합니다. 이전 출력에서 부하 평균은 `9.26`CPU가 약 115%로 로드됨을 의미합니다.

, `5m``15m` 간격은 `1m`시간이 지남에 따라 부하가 증가하거나 감소하는지 여부를 식별하는 데 도움이 됩니다.

> [참고] 명령을 `nproc` 사용하여 CPU 수를 가져올 수도 있습니다.

## 메모리

메모리의 경우 사용량에 대한 세부 정보를 가져올 수 있는 두 가지 명령이 있습니다.

### `free`

이 `free` 명령은 시스템 메모리 사용률을 보여줍니다.

실행하려면 다음을 수행합니다.

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'free -h')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

옵션 및 인수는 다음과 같습니다.

* `-h`: 값을 동적으로 사람이 읽을 수 있는 값으로 표시(예: Mib, Gib, Tib)

출력은 다음과 같습니다.

```output
               total        used        free      shared  buff/cache   available
Mem:            31Gi        19Gi        12Gi        23Mi        87Mi        11Gi
Swap:           23Gi          0B        23Gi
```

출력에서 총 시스템 메모리와 사용 가능한 메모리 및 사용된 대 총 스왑을 찾습니다. 사용 가능한 메모리는 사용자 애플리케이션에 대해 반환될 수 있는 캐시에 할당된 메모리를 고려합니다.

일부 스왑 사용은 자주 사용되지 않은 메모리 페이지를 교환으로 이동할 수 있으므로 최신 커널에서 정상입니다.

### `swapon`

이 `swapon` 명령은 스왑이 구성된 위치와 스왑 디바이스 또는 파일의 각 우선 순위를 표시합니다.

명령을 실행하려면 다음을 수행합니다.

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'swapon -s')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

출력은 다음과 같습니다.

```output
Filename      Type          Size          Used   Priority
/dev/zram0    partition     16G           0B      100
/mnt/swapfile file          8G            0B      -2
```

이 정보는 데이터 또는 OS 디스크와 같이 이상적이지 않은 위치에 스왑이 구성되어 있는지 확인하는 데 중요합니다. Azure 참조 프레임에서는 최상의 성능을 제공하므로 임시 드라이브에서 교환을 구성해야 합니다.

### 알아야 할 사항

* 메모리는 유한한 리소스입니다. 일단 시스템 메모리(RAM)와 스왑이 모두 소진되면 OOM(Out Of Memorry Killer)에 의해 프로세스가 종료됩니다.
* 대기 시간 차이로 인해 I/O에 문제가 발생하므로 교환이 데이터 디스크 또는 OS 디스크에 구성되어 있지 않은지 확인합니다. 교환은 임시 드라이브에서 구성해야 합니다.
* 또한 출력에서 사용 가능한 값이 0에 `free -h` 가깝다는 것을 확인하는 것이 일반적이며, 이 동작은 페이지 캐시 때문이며 커널은 필요에 따라 해당 페이지를 해제합니다.

## I/O

디스크 I/O는 디스크가 대기 시간에 도달할 `100ms+` 수 있으므로 Azure에서 제한될 때 가장 많이 발생하는 영역 중 하나입니다. 다음 명령은 이러한 시나리오를 식별하는 데 도움이 됩니다.

### `iostat`

유틸리티 `iostat` 는 패키지의 `sysstat` 일부입니다. 블록별 디바이스 사용 통계를 표시하고 블록 관련 성능 문제를 식별하는 데 도움이 됩니다.

이 유틸리티는 `iostat` 처리량, 대기 시간 및 큐 크기와 같은 메트릭에 대한 세부 정보를 제공합니다. 이러한 메트릭은 디스크 I/O가 제한 요소가 되는지 이해하는 데 도움이 됩니다.
실행하려면 다음 명령을 사용합니다.

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'iostat -dxtm 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

옵션 및 인수는 다음과 같습니다.

* `-d`: 디바이스별 사용량 보고서입니다.
* `-x`: 확장된 통계입니다.
* `-t`: 각 보고서의 타임스탬프를 표시합니다.
* `-m`: MB/s로 표시합니다.
* `1`: 첫 번째 숫자 인수는 디스플레이를 새로 고치는 빈도(초)를 나타냅니다.
* `2`: 두 번째 숫자 인수는 데이터가 새로 고쳐진 횟수를 나타냅니다.

출력은 다음과 같습니다.

```output
Linux 5.14.0-362.8.1.el9_3.x86_64 (alma9)       02/21/24        _x86_64_        (8 CPU)

02/21/24 16:55:50
Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
sda              1.07      0.02     0.00   0.00    1.95    20.40   23.25     24.55     3.30  12.42  113.75  1081.06    0.26    537.75     0.26  49.83    0.03 2083250.04    0.00    0.00    2.65   2.42
sdb             16.99      0.67     0.36   2.05    2.00    40.47   65.26      0.44     1.55   2.32    1.32     6.92    0.00      0.00     0.00   0.00    0.00     0.00   30.56    1.30    0.16   7.16
zram0            0.51      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.00   0.00

```

출력에는 중요하지 않은 여러 열(옵션으로 인한 `-x` 추가 열)이 있으며, 몇 가지 중요한 열은 다음과 같습니다.

* `r/s`: 초당 읽기 작업(IOPS)입니다.
* `rMB/s`: 초당 MB를 읽습니다.
* `r_await`: 읽기 대기 시간(밀리초)입니다.
* `rareq-sz`: 평균 읽기 요청 크기(킬로바이트)입니다.
* `w/s`: 초당 쓰기 작업(IOPS)입니다.
* `wMB/s`: 초당 MB를 씁니다.
* `w_await`: 대기 시간을 밀리초 단위로 작성합니다.
* `wareq-size`: 평균 쓰기 요청 크기(킬로바이트)입니다.
* `aqu-sz`: 평균 큐 크기입니다.

#### 알아야 할 사항

* IOPS(및 IOPS)`rMB/s` `wMB/s` 를 찾아 `r/s` `w/s` 서 해당 값이 지정된 디스크의 한도 내에 있는지 확인합니다. 값이 한도에 가깝거나 높은 경우 디스크가 제한되어 대기 시간이 높아집니다. 이 정보는 .의 `mpstat`메트릭을 사용하여 `%iowait` 확증할 수도 있습니다.
* 대기 시간은 디스크가 예상대로 작동하는지 확인하는 훌륭한 메트릭입니다. 일반적으로 PremiumSSD의 예상 대기 시간보다 `9ms` 작으면 다른 제품에는 대기 시간 목표가 다릅니다.
* 큐 크기는 채도를 나타내는 좋은 지표입니다. 일반적으로 요청은 거의 실시간으로 제공되며 큐가 증가하지 않을 때 숫자는 1에 가깝게 유지됩니다. 숫자가 클수록 디스크 포화를 나타낼 수 있습니다(즉, 요청이 대기 중). 이 메트릭에는 양호하거나 잘못된 숫자가 없습니다. 둘 이상의 항목을 이해한다는 것은 요청이 대기 중임을 의미하며 디스크 채도가 있는지 확인하는 데 도움이 됩니다.

### `lsblk`

이 유틸리티는 `lsblk` 시스템에 연결된 블록 디바이스를 보여 주지만 성능 메트릭을 제공하지는 않지만 이러한 디바이스를 구성하는 방법과 사용 중인 탑재점에 대한 간략한 개요를 제공합니다.

실행하려면 다음 명령을 사용합니다.

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'lsblk')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

출력은 다음과 같습니다.

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

#### 알아야 할 사항

* 디바이스가 탑재되는 위치를 찾습니다.
* 사용하도록 설정된 경우 데이터 디스크 또는 OS 디스크 내에서 구성되지 않은 스왑을 확인합니다.

> 참고: 블록 디바이스를 Azure의 LUN과 쉽게 상호 연결하는 방법은 실행하는 `ls -lr /dev/disk/azure`것입니다.

## Process

프로세스별로 세부 정보를 수집하면 시스템의 부하가 어디에서 오는지 이해하는 데 도움이 됩니다.

프로세스 정적을 수집하는 주요 유틸리티는 `pidstat` CPU, 메모리 및 I/O 통계에 대한 프로세스별 세부 정보를 제공하는 것입니다.

마지막으로, 상위 CPU별로 프로세스를 정렬하는 간단한 `ps` 방법과 메모리 사용량이 메트릭을 완료합니다.

> [!NOTE]
> 이러한 명령은 실행 중인 프로세스에 대한 세부 정보를 표시하므로 `sudo`. 이 명령을 사용하면 사용자뿐만 아니라 모든 프로세스를 표시할 수 있습니다.

### `pidstat`

유틸리티 `pidstat` 도 패키지의 `sysstat` 일부입니다. 지정된 시간 동안 메트릭을 표시하는 것과 같 `mpstat` 거나 iostat입니다. 기본적으로 `pidstat` 활동이 있는 프로세스에 대한 메트릭만 표시합니다.

`pidstat` 인수는 다른 `sysstat` 유틸리티에 대해 동일합니다.

* 1: 첫 번째 숫자 인수는 디스플레이를 새로 고치는 빈도(초)를 나타냅니다.
* 2: 두 번째 숫자 인수는 데이터가 새로 고쳐진 횟수를 나타냅니다.

> [!NOTE]
> 작업이 있는 프로세스가 많으면 출력이 상당히 증가할 수 있습니다.

#### CPU 통계 처리

프로세스 CPU 통계를 수집하려면 옵션 없이 실행 `pidstat` 합니다.

Azure CLI에서 실행하려는 경우 다음 명령을 사용할 수 있습니다.

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

출력은 다음과 같습니다.

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

이 명령은 프로세스별 사용량, `%system``%guest` (Azure에 `%usr`적용되지 않음) `%wait`및 총 `%CPU` 사용량을 표시합니다.

##### 알아야 할 사항

* I/O 대기가 차단된 프로세스를 나타낼 수 있으므로 %wait(iowait) 비율이 높은 프로세스를 찾습니다. 이는 디스크 포화도를 나타낼 수도 있습니다.
* 단일 스레드 애플리케이션을 나타낼 수 있으므로 단일 프로세스가 CPU의 100%를 사용하지 않는지 확인합니다.

#### 메모리 통계 처리

프로세스 메모리 통계를 수집하려면 다음 `-r` 옵션을 사용합니다.

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -r 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

출력은 다음과 같습니다.

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

수집된 메트릭은 다음과 같습니다.

* `minflt/s`: 초당 사소한 오류입니다. 이 메트릭은 RAM(시스템 메모리)에서 로드된 페이지 수를 나타냅니다.
* `mjflt/s`: 초당 주요 오류 수입니다. 이 메트릭은 디스크에서 로드된 페이지 수(SWAP)를 나타냅니다.
* `VSZ`: 바이트 단위로 사용되는 가상 메모리입니다.
* `RSS`: 사용된 상주 메모리(실제 할당된 메모리)(바이트)입니다.
* `%MEM`: 사용된 총 메모리의 백분율입니다.
* `Command`: 프로세스의 이름입니다.

##### 알아야 할 사항

* 이 값은 디스크 간에 페이지를 교환하는 프로세스를 나타내기 때문에 초당 주요 오류를 찾습니다. 이 동작은 메모리 소모를 나타낼 수 있으며, 느린 스왑으로 `OOM` 인해 이벤트 또는 성능 저하가 발생할 수 있습니다.
* 단일 프로세스가 사용 가능한 메모리의 100%를 소비하지 않는지 확인합니다. 이 동작은 메모리 누수일 수 있습니다.

> [!NOTE]
> 이 `--human` 옵션은 사람이 읽을 수 있는 형식(즉, `Kb`, , `Mb``GB`)으로 숫자를 표시하는 데 사용할 수 있습니다.

#### 프로세스 I/O 통계

프로세스 메모리 통계를 수집하려면 다음 `-d` 옵션을 사용합니다.

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -d 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

출력은 다음과 같습니다.

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

수집된 메트릭은 다음과 같습니다.

* `kB_rd/s`: 초당 읽기 킬로바이트입니다.
* `kB_wr/s`: 초당 킬로바이트(KB)를 씁니다.
* `Command`: 프로세스의 이름입니다.

##### 알아야 할 사항

* 초당 읽기/쓰기 속도가 높은 단일 프로세스를 찾습니다. 이 정보는 문제를 식별하는 것 이상의 I/O를 사용하는 프로세스에 대한 지침입니다.
참고: 이 `--human` 옵션을 사용하여 사람이 읽을 수 있는 형식(즉, `Kb`, ,`Mb``GB`)으로 숫자를 표시할 수 있습니다.

### `ps`

마지막으로 `ps` 명령은 시스템 프로세스를 표시하며 CPU 또는 메모리별로 정렬할 수 있습니다.

CPU를 기준으로 정렬하고 상위 10개 프로세스를 가져오려면 다음을 수행합니다.

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

상위 10개 프로세스를 기준으로 `MEM%` 정렬하고 가져오려면 다음을 수행합니다.

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

## 모두 함께 배치

간단한 bash 스크립트는 한 번의 실행으로 모든 세부 정보를 수집하고 나중에 사용할 수 있도록 출력을 파일에 추가할 수 있습니다.

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2 && vmstat -w 1 5 && uptime && free -h && swapon && iostat -dxtm 1 1 && lsblk && ls -l /dev/disk/azure && pidstat 1 1 -h --human && pidstat -r 1 1 -h --human && pidstat -d 1 1 -h --human && ps aux --sort=-%cpu | head -20 && ps aux --sort=-%mem | head -20')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```

실행하려면 위의 내용이 포함된 파일을 만들고 실행 권한을 `chmod +x gather.sh`추가하고 다음을 사용하여 실행할 수 있습니다 `sudo ./gather.sh`.

이 스크립트는 명령의 출력을 스크립트가 호출된 동일한 디렉터리에 있는 파일에 저장합니다.

또한 이 문서에서 다루는 bash 블록 코드의 모든 명령은 run-command 확장을 사용하여 실행하고 `az-cli` 출력 `jq` 을 구문 분석하여 로컬에서 명령을 실행하는 것과 유사한 출력을 얻을 수 있습니다. '

```azurecli-interactive
output=$(az vm run-command invoke -g $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "ls -l /dev/disk/azure")
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```