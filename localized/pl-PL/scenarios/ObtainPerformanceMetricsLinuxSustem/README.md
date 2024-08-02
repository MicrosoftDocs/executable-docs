---
title: Uzyskiwanie metryk wydajności z systemu Linux
description: 'Dowiedz się, jak uzyskać metryki wydajności z systemu Linux.'
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

# Uzyskiwanie metryk wydajności z systemu Linux

**Dotyczy:** :heavy_check_mark: Maszyny wirtualne z systemem Linux

Ten artykuł zawiera instrukcje dotyczące szybkiego uzyskiwania metryk wydajności z systemu Linux.

Istnieje kilka poleceń, których można użyć do uzyskania liczników wydajności w systemie Linux. Polecenia, takie jak `vmstat` i `uptime`, udostępniają ogólne metryki systemowe, takie jak użycie procesora CPU, pamięć systemowa i obciążenie systemu.
Większość poleceń jest już instalowana domyślnie, a inne są łatwo dostępne w domyślnych repozytoriach.
Polecenia można rozdzielić na:

* Procesor CPU
* Memory (Pamięć)
* We/Wy dysku
* Procesy

## Instalacja narzędzi sysstat

<!-- Commenting out these entries as this information should be selected by the user along with the corresponding subscription and region

The First step in this tutorial is to define environment variables, and install the corresponding package, if necessary.

```azurecli-interactive
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup89f292"
export MY_VM_NAME="myVM89f292"
```
-->

> [!NOTE]
> Niektóre z tych poleceń muszą być uruchamiane, `root` aby móc zebrać wszystkie istotne szczegóły.

> [!NOTE]
> Niektóre polecenia są częścią `sysstat` pakietu, który może nie być instalowany domyślnie. Pakiet można łatwo zainstalować za pomocą `sudo apt install sysstat`programu lub `dnf install sysstat` `zypper install sysstat` dla tych popularnych dystrybucji.

Pełne polecenie instalacji `sysstat` pakietu w niektórych popularnych dystrybucjach to:

```bash
az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "/bin/bash -c 'OS=\$(cat /etc/os-release|grep NAME|head -1|cut -d= -f2 | sed \"s/\\\"//g\"); if [[ \$OS =~ \"Ubuntu\" ]] || [[ \$OS =~ \"Debian\" ]]; then sudo apt install sysstat -y; elif [[ \$OS =~ \"Red Hat\" ]]; then sudo dnf install sysstat -y; elif [[ \$OS =~ \"SUSE\" ]]; then sudo zypper install sysstat --non-interactive; else echo \"Unknown distribution\"; fi'"
```

## Procesor CPU

### <a id="mpstat"></a>mpstat

Narzędzie `mpstat` jest częścią `sysstat` pakietu. Wyświetla on użycie procesora CPU i średnie, co jest przydatne do szybkiego identyfikowania użycia procesora CPU. `mpstat` Zawiera omówienie wykorzystania procesora CPU w dostępnych procesorach CPU, pomagając zidentyfikować saldo użycia i jeśli pojedynczy procesor CPU jest mocno obciążony.

Pełne polecenie to:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Opcje i argumenty to:

* `-P`: wskazuje procesor do wyświetlania statystyk, argument ALL wskazuje, aby wyświetlić statystyki dla wszystkich procesorów online w systemie.
* `1`: pierwszy argument liczbowy wskazuje, jak często odświeżać ekran w sekundach.
* `2`: drugi argument liczbowy wskazuje, ile razy dane są odświeżane.

Liczba wyświetleń `mpstat` danych w poleceniu może zostać zmieniona przez zwiększenie drugiego argumentu liczbowego w celu uwzględnienia dłuższych czasów zbierania danych. Najlepiej 3 lub 5 sekund wystarczy, aby systemy o zwiększonej liczbie rdzeni 2 sekundy mogły zmniejszyć ilość wyświetlanych danych.
Z danych wyjściowych:

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

Należy pamiętać o kilku ważnych kwestiach. Pierwszy wiersz wyświetla przydatne informacje:

* Jądro i wydanie: `5.14.0-362.8.1.el9_3.x86_64`
* Nazwa hosta: `alma9`
* Data: `02/21/24`
* Architektura: `_x86_64_`
* Łączna ilość procesorów CPU (te informacje są przydatne do interpretowania danych wyjściowych z innych poleceń): `(8 CPU)`

Następnie zostaną wyświetlone metryki dla procesorów CPU, aby wyjaśnić każdą z kolumn:

* `Time`: czas zbierania próbki
* `CPU`: identyfikator liczbowy procesora CPU, identyfikator ALL jest średnią dla wszystkich procesorów CPU.
* `%usr`: procent wykorzystania procesora CPU dla miejsca użytkownika, zwykle aplikacji użytkownika.
* `%nice`: Procent wykorzystania procesora CPU dla procesów przestrzeni użytkownika z ładną (priorytetową) wartością.
* `%sys`: procent wykorzystania procesora CPU dla procesów przestrzeni jądra.
* `%iowait`: Procent czasu procesora CPU poświęcanego na bezczynność oczekujących na zaległe we/wy.
* `%irq`: procent czasu procesora CPU poświęcanego na obsługę przerwań sprzętowych.
* `%soft`: procent czasu poświęcanego na obsługę przerwań oprogramowania.
* `%steal`: Procent czasu procesora CPU poświęcanego na obsługę innych maszyn wirtualnych (nie dotyczy platformy Azure z powodu braku nadmiernej aprowizacji procesora CPU).
* `%guest`: Procent czasu procesora CPU poświęcanego na obsługę wirtualnych procesorów CPU (nie dotyczy platformy Azure, dotyczy tylko systemów bez systemu operacyjnego z uruchomionymi maszynami wirtualnymi).
* `%gnice`: Procent czasu procesora CPU poświęcanego na obsługę wirtualnych procesorów CPU z dobrą wartością (nie dotyczy platformy Azure, dotyczy tylko systemów bez systemu operacyjnego z uruchomionymi maszynami wirtualnymi).
* `%idle`: procent czasu procesora CPU spędzony bezczynności i bez oczekiwania na żądania we/wy.

#### Rzeczy, dla których należy zwrócić uwagę

Niektóre szczegóły, które należy wziąć pod uwagę podczas przeglądania danych wyjściowych dla `mpstat`elementu :

* Sprawdź, czy wszystkie procesory CPU są prawidłowo załadowane, a nie jeden procesor obsługuje wszystkie obciążenia. Te informacje mogą wskazywać na jedną aplikację wątkową.
* Poszukaj równowagi w dobrej kondycji między `%usr` i `%sys` , ponieważ odwrotnie oznaczałoby więcej czasu poświęcanego na rzeczywiste obciążenie niż obsługa procesów jądra.
* `%iowait` Poszukaj wartości procentowych, ponieważ wysokie wartości mogą wskazywać system, który stale czeka na żądania we/wy.
* Wysokie `%soft` użycie może wskazywać na duży ruch sieciowy.

### `vmstat`

Narzędzie `vmstat` jest powszechnie dostępne w większości dystrybucji systemu Linux, zawiera ogólne omówienie wykorzystania procesora CPU, pamięci i operacji we/wy dysku w jednym okienku.
Polecenie dla `vmstat` polecenia to:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'vmstat -w 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Opcje i argumenty to:

* `-w`: Użyj szerokiego drukowania, aby zachować spójne kolumny.
* `1`: pierwszy argument liczbowy wskazuje, jak często odświeżać ekran w sekundach.
* `5`: drugi argument liczbowy wskazuje, ile razy dane są odświeżane.

Dane wyjściowe:

```output
--procs-- -----------------------memory---------------------- ---swap-- -----io---- -system-- --------cpu--------
   r    b         swpd         free         buff        cache   si   so    bi    bo   in   cs  us  sy  id  wa  st
  14    0            0     26059408          164       137468    0    0    89  3228   56  122   3   1  95   1   0
  14    1            0     24388660          164       145468    0    0     0  7811 3264 13870  76  24   0   0   0
  18    1            0     23060116          164       155272    0    0    44  8075 3704 15129  78  22   0   0   0
  18    1            0     21078640          164       165108    0    0   295  8837 3742 15529  73  27   0   0   0
  15    2            0     19015276          164       175960    0    0     9  8561 3639 15177  73  27   0   0   0
```

`vmstat` dzieli dane wyjściowe w sześciu grupach:

* `procs`: statystyki dotyczące procesów.
* `memory`: statystyki pamięci systemowej.
* `swap`: statystyki dotyczące zamiany.
* `io`: statystyki dla operacji we/wy dysku.
* `system`: statystyki przełączników kontekstowych i przerwań.
* `cpu`: statystyki użycia procesora CPU.

>Uwaga: `vmstat` przedstawia ogólne statystyki dla całego systemu (czyli wszystkie procesory CPU, wszystkie urządzenia blokowe agregowane).

#### `procs`

Sekcja `procs` zawiera dwie kolumny:

* `r`: liczba procesów możliwych do uruchomienia w kolejce uruchamiania.
* `b`: liczba zablokowanych procesów oczekujących na we/wy.

Ta sekcja natychmiast pokazuje, czy w systemie występuje jakiekolwiek wąskie gardło. Duże liczby w jednej z kolumn wskazują procesy kolejkowania oczekujących na zasoby.

Kolumna `r` wskazuje liczbę procesów oczekujących na uruchomienie procesora CPU. Prosty sposób interpretowania tej liczby jest następujący: jeśli liczba procesów w `r` kolejce jest większa niż liczba całkowitych procesorów CPU, można wywnioskować, że system ma mocno załadowany procesor CPU i nie może przydzielić czasu procesora CPU dla wszystkich procesów oczekujących na uruchomienie.

Kolumna `b` wskazuje liczbę procesów oczekujących na uruchomienie, które są blokowane przez żądania we/wy. Duża liczba w tej kolumnie wskazuje system, w którym występuje wysokie we/wy, a procesy nie mogą być uruchamiane z powodu innych procesów oczekujących na ukończenie żądań we/wy. Co może również wskazywać na duże opóźnienie dysku.

#### `memory`

Sekcja pamięci zawiera cztery kolumny:

* `swpd`: użyta ilość pamięci wymiany.
* `free`: ilość wolnej pamięci.
* `buff`: ilość pamięci używanej dla.
* `cache`: ilość pamięci używanej do buforowania.

> [!NOTE]
> Wartości są wyświetlane w bajtach.

Ta sekcja zawiera ogólne omówienie użycia pamięci.

#### `swap`

Sekcja zamiany zawiera dwie kolumny:

* `si`: ilość pamięci zamienionej (przeniesiona z pamięci systemowej na zamianę) na sekundę.
* `so`: ilość pamięci zamienionej (przeniesiona z zamiany na pamięć systemowa) na sekundę.

W przypadku zaobserwowania wysokiego `si` poziomu może to oznaczać system, w którym brakuje pamięci systemowej i przenosi strony do zamiany (zamiana).

#### `io`

Sekcja `io` zawiera dwie kolumny:

* `bi`: liczba bloków odebranych z urządzenia blokowego (bloki odczytu na sekundę) na sekundę.
* `bo`: liczba bloków wysyłanych do urządzenia blokowego (zapisy na sekundę) na sekundę.

> [!NOTE]
> Te wartości znajdują się w blokach na sekundę.

#### `system`

Sekcja `system` zawiera dwie kolumny:

* `in`: liczba przerwań na sekundę.
* `cs`: liczba przełączników kontekstowych na sekundę.

Duża liczba przerwań na sekundę może wskazywać na system zajęty urządzeniami sprzętowymi (na przykład operacje sieciowe).

Duża liczba przełączników kontekstowych może wskazywać na ruchliwy system z wieloma krótkimi procesami, w tym miejscu nie ma dobrej lub złej liczby.

#### `cpu`

Ta sekcja zawiera pięć kolumn:

* `us`: wykorzystanie procentu miejsca użytkownika.
* `sy`: Wykorzystanie procentowe systemu (miejsca na jądro).
* `id`: Procentowe wykorzystanie czasu bezczynności procesora CPU.
* `wa`: Procent wykorzystania czasu bezczynności procesora CPU w oczekiwaniu na procesy z we/wy.
* `st`: Procentowe wykorzystanie czasu, przez jaki procesor cpu obsługiwał inne procesory wirtualne (nie dotyczy platformy Azure).

Wartości są prezentowane w procentach. Te wartości są takie same jak przedstawione przez `mpstat` narzędzie i służą do zapewnienia wysokiego poziomu przeglądu użycia procesora CPU. Postępuj zgodnie z podobnym procesem dla opcji "[Rzeczy, dla których należy zwrócić uwagę](#mpstat)" `mpstat` podczas przeglądania tych wartości.

### `uptime`

Na koniec w przypadku metryk `uptime` związanych z procesorem CPU narzędzie udostępnia szeroki przegląd obciążenia systemu ze średnimi wartościami obciążenia.

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'uptime')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

```output
16:55:53 up 9 min,  2 users,  load average: 9.26, 2.91, 1.18
```

Średnia obciążenia wyświetla trzy liczby. Są to liczby dla `1`interwałów czasu `5` `15` ładowania systemu i minut.

Aby zinterpretować te wartości, ważne jest, aby znać liczbę dostępnych procesorów CPU w systemie uzyskanych z danych wyjściowych `mpstat` przed. Wartość zależy od całkowitej liczby procesorów CPU, więc jako przykład `mpstat` danych wyjściowych system ma 8 procesorów CPU, średnie obciążenie 8 oznaczałoby, że wszystkie rdzenie są ładowane do 100%.

Wartość oznaczałaby, że połowa procesorów `4` CPU została załadowana na 100% (lub łącznie 50% obciążenia dla wszystkich procesorów CPU). W poprzednich danych wyjściowych średnia obciążenia wynosi `9.26`, co oznacza, że procesor CPU jest ładowany na około 115%.

Interwały `1m`, `5m``15m` pomagają określić, czy obciążenie rośnie lub zmniejsza się wraz z upływem czasu.

> [UWAGA] Za `nproc` pomocą polecenia można również uzyskać liczbę procesorów CPU.

## Pamięć

W przypadku pamięci istnieją dwa polecenia, które mogą uzyskać szczegółowe informacje o użyciu.

### `free`

Polecenie `free` pokazuje wykorzystanie pamięci systemowej.

Aby go uruchomić:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'free -h')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Opcje i argumenty to:

* `-h`: Dynamiczne wyświetlanie wartości jako czytelnych dla człowieka (na przykład: Mib, Gib, Tib)

Dane wyjściowe:

```output
               total        used        free      shared  buff/cache   available
Mem:            31Gi        19Gi        12Gi        23Mi        87Mi        11Gi
Swap:           23Gi          0B        23Gi
```

W danych wyjściowych poszukaj całkowitej pamięci systemowej a dostępnej oraz użytej zamiany całkowitej. Dostępna pamięć uwzględnia pamięć przydzieloną do pamięci podręcznej, którą można zwrócić dla aplikacji użytkowników.

Niektóre użycie zamiany jest normalne w nowoczesnych jądrach, ponieważ niektóre rzadziej używane strony pamięci można przenieść do zamiany.

### `swapon`

Polecenie `swapon` wyświetla lokalizację, w której jest skonfigurowana zamiana, oraz odpowiednie priorytety urządzeń lub plików wymiany.

Aby uruchomić polecenie:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'swapon -s')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Dane wyjściowe:

```output
Filename      Type          Size          Used   Priority
/dev/zram0    partition     16G           0B      100
/mnt/swapfile file          8G            0B      -2
```

Te informacje są ważne, aby sprawdzić, czy zamiana jest skonfigurowana w lokalizacji, która nie jest idealna, na przykład na dysku danych lub dysku systemu operacyjnego. W ramce referencyjnej platformy Azure zamiana powinna być skonfigurowana na dysku efemerycznym, ponieważ zapewnia najlepszą wydajność.

### Rzeczy, dla których należy zwrócić uwagę

* Należy pamiętać, że pamięć jest zasobem skończonym, gdy pamięć systemowa (RAM) i wymiana zostaną wyczerpane, procesy zostaną zabite przez zabójcę Out Of Memorry (OOM).
* Sprawdź, czy zamiana nie jest skonfigurowana na dysku danych lub dysku systemu operacyjnego, ponieważ spowodowałoby to problemy z we/wy z powodu różnic opóźnienia. Zamiana powinna być skonfigurowana na dysku efemerycznym.
* Należy również pamiętać, że często można zobaczyć w `free -h` danych wyjściowych, że wartości bezpłatne są zbliżone do zera, to zachowanie jest spowodowane pamięcią podręczną strony, jądro zwalnia te strony zgodnie z potrzebami.

## WE/WY

We/Wy dysku jest jednym z obszarów, w których platforma Azure najbardziej cierpi podczas ograniczania przepustowości, ponieważ dyski mogą osiągać `100ms+` opóźnienia. Poniższe polecenia pomagają zidentyfikować te scenariusze.

### `iostat`

Narzędzie `iostat` jest częścią `sysstat` pakietu. Wyświetla statystyki użycia urządzeń blokowych i pomaga zidentyfikować problemy z wydajnością związane z blokiem.

Narzędzie `iostat` zawiera szczegółowe informacje dotyczące metryk, takich jak przepływność, opóźnienie i rozmiar kolejki. Te metryki pomagają zrozumieć, czy we/wy dysku stają się czynnikiem ograniczającym.
Aby uruchomić polecenie , użyj polecenia :

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'iostat -dxtm 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Opcje i argumenty to:

* `-d`: na raport użycia urządzenia.
* `-x`: Rozszerzone statystyki.
* `-t`: Wyświetla znacznik czasu dla każdego raportu.
* `-m`: Wyświetl w MB/s.
* `1`: pierwszy argument liczbowy wskazuje, jak często odświeżać ekran w sekundach.
* `2`: drugi argument liczbowy wskazuje, ile razy dane są odświeżane.

Dane wyjściowe:

```output
Linux 5.14.0-362.8.1.el9_3.x86_64 (alma9)       02/21/24        _x86_64_        (8 CPU)

02/21/24 16:55:50
Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
sda              1.07      0.02     0.00   0.00    1.95    20.40   23.25     24.55     3.30  12.42  113.75  1081.06    0.26    537.75     0.26  49.83    0.03 2083250.04    0.00    0.00    2.65   2.42
sdb             16.99      0.67     0.36   2.05    2.00    40.47   65.26      0.44     1.55   2.32    1.32     6.92    0.00      0.00     0.00   0.00    0.00     0.00   30.56    1.30    0.16   7.16
zram0            0.51      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.00   0.00

```

Dane wyjściowe zawierają kilka kolumn, które nie są ważne (dodatkowe kolumny ze względu na `-x` opcję), niektóre z nich są następujące:

* `r/s`: Operacje odczytu na sekundę (IOPS).
* `rMB/s`: Odczytaj megabajty na sekundę.
* `r_await`: Opóźnienie odczytu w milisekundach.
* `rareq-sz`: średni rozmiar żądania odczytu w kilobajtach.
* `w/s`: Operacje zapisu na sekundę (IOPS).
* `wMB/s`: Zapisuj megabajty na sekundę.
* `w_await`: Opóźnienie zapisu w milisekundach.
* `wareq-size`: średni rozmiar żądania zapisu w kilobajtach.
* `aqu-sz`: Średni rozmiar kolejki.

#### Rzeczy, dla których należy zwrócić uwagę

* `r/s` Wyszukaj wartości i `w/s` (IOPS) i `rMB/s` `wMB/s` i sprawdź, czy te wartości znajdują się w granicach danego dysku. Jeśli wartości są bliskie lub wyższe limity, dysk będzie ograniczany, co prowadzi do dużego opóźnienia. Te informacje można również potwierdzić za `%iowait` pomocą metryki z .`mpstat`
* Opóźnienie to doskonała metryka do sprawdzenia, czy dysk działa zgodnie z oczekiwaniami. Zwykle mniejsze niż `9ms` oczekiwane opóźnienie dla usługi PremiumSSD, inne oferty mają różne cele opóźnienia.
* Rozmiar kolejki jest doskonałym wskaźnikiem nasycenia. Zwykle żądania będą obsługiwane niemal w czasie rzeczywistym, a liczba pozostaje blisko jednej (ponieważ kolejka nigdy się nie zwiększa). Większa liczba może wskazywać na nasycenie dysku (czyli żądania kolejkowania). Nie ma dobrej ani złej liczby dla tej metryki. Zrozumienie, że cokolwiek wyższe niż jedno oznacza, że żądania są kolejkowane, pomaga określić, czy istnieje nasycenie dysku.

### `lsblk`

Narzędzie `lsblk` pokazuje urządzenia blokowe dołączone do systemu, chociaż nie udostępnia metryk wydajności, umożliwia szybkie omówienie sposobu konfigurowania tych urządzeń i używanych punktów instalacji.

Aby uruchomić polecenie , użyj polecenia :

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'lsblk')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Dane wyjściowe:

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

#### Rzeczy, dla których należy zwrócić uwagę

* Poszukaj miejsca, w którym są zainstalowane urządzenia.
* Sprawdź, czy zamiana nie jest skonfigurowana wewnątrz dysku danych lub dysku systemu operacyjnego, jeśli jest włączona.

> Uwaga: łatwym sposobem skorelowania urządzenia blokowego z numerem LUN na platformie Azure jest uruchomienie polecenia `ls -lr /dev/disk/azure`.

## Przetwarzaj

Zbieranie szczegółów na podstawie procesu pomaga zrozumieć, skąd pochodzi obciążenie systemu.

Głównym narzędziem do zbierania danych statycznych procesów jest `pidstat` to, że udostępnia szczegółowe informacje dotyczące poszczególnych procesów dotyczących statystyk procesora CPU, pamięci i operacji we/wy.

Na koniec prosty `ps` proces sortowania według najwyższego użycia procesora CPU i pamięci kończy metryki.

> [!NOTE]
> Ponieważ te polecenia zawierają szczegółowe informacje na temat uruchamiania procesów, muszą być uruchamiane jako katalog główny za pomocą polecenia `sudo`. To polecenie umożliwia wyświetlanie wszystkich procesów, a nie tylko użytkowników.

### `pidstat`

Narzędzie `pidstat` jest również częścią `sysstat` pakietu. Jest to jak `mpstat` lub iostat, w którym wyświetla metryki dla danego czasu. Domyślnie `pidstat` wyświetla tylko metryki dla procesów z działaniem.

Argumenty dla programu `pidstat` są takie same w przypadku innych `sysstat` narzędzi:

* 1: Pierwszy argument liczbowy wskazuje, jak często odświeżać ekran w sekundach.
* 2: Drugi argument liczbowy wskazuje, ile razy dane są odświeżane.

> [!NOTE]
> Dane wyjściowe mogą znacznie rosnąć, jeśli istnieje wiele procesów z działaniem.

#### Przetwarzanie statystyk procesora CPU

Aby zebrać statystyki procesora CPU, uruchom polecenie `pidstat` bez żadnych opcji:

Jeśli chcesz wykonać je z poziomu interfejsu wiersza polecenia platformy Azure, można użyć następujących poleceń:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Dane wyjściowe:

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

Polecenie wyświetla użycie poszczególnych procesów dla `%usr`, , `%guest` `%system`(nie dotyczy platformy Azure), `%wait`i całkowitego `%CPU` użycia.

##### Rzeczy, dla których należy zwrócić uwagę

* Poszukaj procesów o dużej wartości procentowej %wait (iowait), ponieważ może wskazywać na procesy, które są zablokowane oczekujące na operacje we/wy, co może również wskazywać na nasycenie dysku.
* Sprawdź, czy żaden pojedynczy proces nie zużywa 100% procesora CPU, ponieważ może wskazywać na jedną aplikację wątkową.

#### Statystyka pamięci procesu

Aby zebrać statystyki pamięci procesu, użyj `-r` opcji:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -r 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Dane wyjściowe:

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

Zebrane metryki to:

* `minflt/s`: Drobne błędy na sekundę, ta metryka wskazuje liczbę stron załadowanych z pamięci systemowej (RAM).
* `mjflt/s`: Główne błędy na sekundę, ta metryka wskazuje liczbę stron załadowanych z dysku (SWAP).
* `VSZ`: pamięć wirtualna używana w bajtach.
* `RSS`: pamięć rezydentna używana (rzeczywista przydzielona pamięć) w bajtach.
* `%MEM`: procent całkowitej używanej pamięci.
* `Command`: nazwa procesu.

##### Rzeczy, dla których należy zwrócić uwagę

* Poszukaj głównych błędów na sekundę, ponieważ ta wartość wskazuje proces wymiany stron na dysk lub z dysku. To zachowanie może wskazywać na wyczerpanie pamięci i może prowadzić do `OOM` zdarzeń lub obniżenia wydajności z powodu wolniejszej wymiany.
* Sprawdź, czy pojedynczy proces nie zużywa 100% dostępnej pamięci. To zachowanie może wskazywać na wyciek pamięci.

> [!NOTE]
> `--human` opcji można użyć do wyświetlania liczb w formacie czytelnym dla człowieka (czyli , `Kb`, `Mb``GB`).

#### Statystyka operacji we/wy procesu

Aby zebrać statystyki pamięci procesu, użyj `-d` opcji:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -d 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Dane wyjściowe:

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

Zebrane metryki to:

* `kB_rd/s`: Odczyt kilobajtów na sekundę.
* `kB_wr/s`: Zapisuj kilobajty na sekundę.
* `Command`: nazwa procesu.

##### Rzeczy, dla których należy zwrócić uwagę

* Poszukaj pojedynczych procesów o wysokich szybkościach odczytu/zapisu na sekundę. Te informacje są wskazówkami dotyczącymi procesów z we/wy więcej niż identyfikowaniem problemów.
Uwaga: `--human` opcja może służyć do wyświetlania liczb w formacie czytelnym dla człowieka (czyli , `Kb`, `Mb``GB`).

### `ps`

`ps` Na koniec polecenie wyświetla procesy systemowe i może być sortowane według procesora CPU lub pamięci.

Aby posortować według procesora CPU i uzyskać 10 najważniejszych procesów:

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

Aby posortować według `MEM%` i uzyskać 10 najważniejszych procesów:

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

## Łączenie wszystkich

Prosty skrypt powłoki bash może zbierać wszystkie szczegóły w jednym przebiegu i dołączać dane wyjściowe do pliku do późniejszego użycia:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2 && vmstat -w 1 5 && uptime && free -h && swapon && iostat -dxtm 1 1 && lsblk && ls -l /dev/disk/azure && pidstat 1 1 -h --human && pidstat -r 1 1 -h --human && pidstat -d 1 1 -h --human && ps aux --sort=-%cpu | head -20 && ps aux --sort=-%mem | head -20')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```

Aby uruchomić polecenie , możesz utworzyć plik z powyższą zawartością, dodać uprawnienia wykonywania, uruchamiając `chmod +x gather.sh`polecenie i uruchamiając polecenie za `sudo ./gather.sh`pomocą polecenia .

Ten skrypt zapisuje dane wyjściowe poleceń w pliku znajdującym się w tym samym katalogu, w którym został wywołany skrypt.

Ponadto wszystkie polecenia w kodach bloków powłoki bash omówione w tym dokumencie można uruchamiać `az-cli` za pomocą rozszerzenia run-command i analizować dane wyjściowe, aby uzyskać podobne dane wyjściowe `jq` do uruchamiania poleceń lokalnie: "

```azurecli-interactive
output=$(az vm run-command invoke -g $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "ls -l /dev/disk/azure")
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```