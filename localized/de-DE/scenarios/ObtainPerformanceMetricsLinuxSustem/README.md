---
title: Abrufen von Leistungsmetriken aus einem Linux-System
description: 'Erfahren Sie, wie Sie Leistungsmetriken aus einem Linux-System abrufen.'
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

# Abrufen von Leistungsmetriken aus einem Linux-System

**Gilt für**: :heavy_check_mark: Linux-VMs

In diesem Artikel werden Anweisungen behandelt, um zu bestimmen, wie Sie schnell Leistungsmetriken aus einem Linux-System abrufen können.

Es gibt mehrere Befehle, die zum Abrufen von Leistungsindikatoren unter Linux verwendet werden können. Befehle wie `vmstat` und `uptime`, stellen allgemeine Systemmetriken wie CPU-Auslastung, Systemspeicher und Systemlast bereit.
Die meisten Befehle sind standardmäßig bereits installiert, da andere standardmäßig in Standardrepositorys verfügbar sind.
Die Befehle können in:

* CPU
* Arbeitsspeicher
* Datenträger-E/A
* Prozesse

## Installation von Sysstat-Dienstprogrammen

<!-- Commenting out these entries as this information should be selected by the user along with the corresponding subscription and region

The First step in this tutorial is to define environment variables, and install the corresponding package, if necessary.

```azurecli-interactive
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup89f292"
export MY_VM_NAME="myVM89f292"
```
-->

> [!NOTE]
> Einige dieser Befehle müssen ausgeführt werden, damit `root` alle relevanten Details erfasst werden können.

> [!NOTE]
> Einige Befehle sind Teil des `sysstat` Pakets, das möglicherweise nicht standardmäßig installiert ist. Das Paket kann einfach mit `sudo apt install sysstat`oder `dnf install sysstat` `zypper install sysstat` für diese beliebten Distros installiert werden.

Der vollständige Befehl für die Installation des `sysstat` Pakets auf einigen beliebten Distros ist:

```bash
az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "/bin/bash -c 'OS=\$(cat /etc/os-release|grep NAME|head -1|cut -d= -f2 | sed \"s/\\\"//g\"); if [[ \$OS =~ \"Ubuntu\" ]] || [[ \$OS =~ \"Debian\" ]]; then sudo apt install sysstat -y; elif [[ \$OS =~ \"Red Hat\" ]]; then sudo dnf install sysstat -y; elif [[ \$OS =~ \"SUSE\" ]]; then sudo zypper install sysstat --non-interactive; else echo \"Unknown distribution\"; fi'"
```

## CPU

### <a id="mpstat"></a>mpstat

Das `mpstat` Hilfsprogramm ist Teil des `sysstat` Pakets. Es zeigt pro CPU-Auslastung und Mittelwerte an, was hilfreich ist, um die CPU-Auslastung schnell zu identifizieren. `mpstat` bietet einen Überblick über die CPU-Auslastung über die verfügbaren CPUs hinweg, um das Nutzungsgleichgewicht zu identifizieren und zu ermitteln, ob eine einzelne CPU stark geladen ist.

Der vollständige Befehl lautet:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Die Optionen und Argumente sind:

* `-P`: Gibt den Prozessor an, der Statistiken anzeigt, das ARGUMENT ALL gibt an, statistiken für alle Online-CPUs im System anzuzeigen.
* `1`: Das erste numerische Argument gibt an, wie oft die Anzeige in Sekunden aktualisiert werden soll.
* `2`: Das zweite numerische Argument gibt an, wie oft die Daten aktualisiert werden.

Die Häufigkeit, mit der der `mpstat` Befehl Daten anzeigt, indem das zweite numerische Argument erhöht wird, um längere Datensammlungszeiten zu berücksichtigen. Idealerweise sollten 3 oder 5 Sekunden ausreichen, damit Systeme mit erhöhten Kernanzahlen 2 Sekunden verwendet werden können, um die angezeigte Datenmenge zu reduzieren.
Aus der Ausgabe:

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

Es gibt ein paar wichtige Dinge zu beachten. In der ersten Zeile werden nützliche Informationen angezeigt:

* Kernel und Release: `5.14.0-362.8.1.el9_3.x86_64`
* Hostname: `alma9`
* Datum: `02/21/24`
* Architektur: `_x86_64_`
* Gesamtmenge der CPUs (diese Informationen sind nützlich, um die Ausgabe aus anderen Befehlen zu interpretieren): `(8 CPU)`

Anschließend werden die Metriken für die CPUs angezeigt, um die einzelnen Spalten zu erläutern:

* `Time`: Die Zeit, zu der die Probe gesammelt wurde
* `CPU`: Der NUMERISCHE CPU-Bezeichner, der ALL-Bezeichner ist ein Mittelwert für alle CPUs.
* `%usr`: Der Prozentsatz der CPU-Auslastung für den Benutzerraum, normalerweise Benutzeranwendungen.
* `%nice`: Der Prozentsatz der CPU-Auslastung für Benutzerraumprozesse mit einem schönen Wert (Priorität).
* `%sys`: Der Prozentsatz der CPU-Auslastung für Kernelraumprozesse.
* `%iowait`: Der Prozentsatz der CPU-Zeit, die im Leerlauf auf ausstehende E/A wartet.
* `%irq`: Der Prozentsatz der CPU-Zeit, die für die Bereitstellung von Hardwareunterbrechungen aufgewendet wurde.
* `%soft`: Der Prozentsatz der CPU-Zeit, die für die Bereitstellung von Softwareunterbrechungen aufgewendet wurde.
* `%steal`: Der Prozentsatz der CPU-Zeit, die für die Bereitstellung anderer virtueller Computer aufgewendet wurde (gilt nicht für Azure aufgrund einer überlastenden CPU-Bereitstellung).
* `%guest`: Der Prozentsatz der CPU-Zeit, die für die Bereitstellung virtueller CPUs aufgewendet wurde (gilt nicht für Azure, gilt nur für Bare-Metal-Systeme, auf denen virtuelle Computer ausgeführt werden).
* `%gnice`: Der Prozentsatz der CPU-Zeit für die Bereitstellung virtueller CPUs mit einem guten Wert (gilt nicht für Azure, gilt nur für Bare-Metal-Systeme, auf denen virtuelle Computer ausgeführt werden).
* `%idle`: Der Prozentsatz der CPU-Zeit, die im Leerlauf verbracht wurde, und ohne auf E/A-Anforderungen zu warten.

#### Dinge, die Sie suchen sollten

Einige Details, die Sie beim Überprüfen der Ausgabe `mpstat`beachten sollten für:

* Stellen Sie sicher, dass alle CPUs ordnungsgemäß geladen sind und nicht eine einzelne CPU die gesamte Last bedient. Diese Informationen können auf eine einzelne Threadanwendung hinweisen.
* Suchen Sie nach einem gesunden Gleichgewicht zwischen `%usr` und `%sys` dem Gegenteil, da mehr Zeit für die tatsächliche Workload aufgewendet wird als die Bereitstellung von Kernelprozessen.
* Suchen Sie nach `%iowait` Prozentsätzen, da hohe Werte auf ein System hinweisen können, das ständig auf E/A-Anforderungen wartet.
* Hohe `%soft` Nutzung kann auf hohen Netzwerkdatenverkehr hinweisen.

### `vmstat`

Das `vmstat` Hilfsprogramm ist in den meisten Linux-Verteilungen weit verbreitet und bietet einen allgemeinen Überblick über die CPU-, Arbeitsspeicher- und Datenträger-E/A-Auslastung in einem einzigen Bereich.
Der Befehl für `vmstat` Folgendes:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'vmstat -w 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Die Optionen und Argumente sind:

* `-w`: Verwenden Sie den breiten Druck, um konsistente Spalten beizubehalten.
* `1`: Das erste numerische Argument gibt an, wie oft die Anzeige in Sekunden aktualisiert werden soll.
* `5`: Das zweite numerische Argument gibt an, wie oft die Daten aktualisiert werden.

Die Ausgabe ist:

```output
--procs-- -----------------------memory---------------------- ---swap-- -----io---- -system-- --------cpu--------
   r    b         swpd         free         buff        cache   si   so    bi    bo   in   cs  us  sy  id  wa  st
  14    0            0     26059408          164       137468    0    0    89  3228   56  122   3   1  95   1   0
  14    1            0     24388660          164       145468    0    0     0  7811 3264 13870  76  24   0   0   0
  18    1            0     23060116          164       155272    0    0    44  8075 3704 15129  78  22   0   0   0
  18    1            0     21078640          164       165108    0    0   295  8837 3742 15529  73  27   0   0   0
  15    2            0     19015276          164       175960    0    0     9  8561 3639 15177  73  27   0   0   0
```

`vmstat` teilt die Ausgabe in sechs Gruppen auf:

* `procs`: Statistiken für Prozesse.
* `memory`: Statistiken für den Systemspeicher.
* `swap`: Statistiken für Tausch.
* `io`: Statistiken für Datenträger io.
* `system`: Statistiken für Kontextschalter und Unterbrechungen.
* `cpu`: Statistiken für die CPU-Auslastung.

>Hinweis: `vmstat` Zeigt allgemeine Statistiken für das gesamte System an (d. a. alle CPUs, alle Blockgeräte aggregiert).

#### `procs`

Der `procs` Abschnitt weist zwei Spalten auf:

* `r`: Die Anzahl der ausgeführten Prozesse in der Ausführungswarteschlange.
* `b`: Die Anzahl der blockierten Prozesse, die auf E/A warten.

Dieser Abschnitt zeigt sofort an, ob es einen Engpass auf dem System gibt. Hohe Zahlen in einer der Spalten deuten darauf hin, dass prozesse auf Ressourcen warten.

Die `r` Spalte gibt die Anzahl der Prozesse an, die auf die CPU-Zeit warten, um in der Lage zu sein, ausgeführt zu werden. Eine einfache Möglichkeit, diese Zahl zu interpretieren, ist wie folgt: Wenn die Anzahl der Prozesse in der `r` Warteschlange höher ist als die Anzahl der gesamten CPUs, kann daraus abgeleitet werden, dass das System die CPU stark geladen hat, und es kann keine CPU-Zeit für alle Prozesse zuordnen, die auf die Ausführung warten.

Die `b` Spalte gibt die Anzahl der Prozesse an, die auf die Ausführung warten, die von E/A-Anforderungen blockiert werden. Eine hohe Zahl in dieser Spalte würde auf ein System hinweisen, das hohe E/A-Vorgänge hat, und Prozesse können aufgrund anderer Prozesse, die auf abgeschlossene E/A-Anforderungen warten, nicht ausgeführt werden. Dies kann auch auf eine hohe Datenträgerlatenz hinweisen.

#### `memory`

Der Speicherabschnitt weist vier Spalten auf:

* `swpd`: Der verwendete Speicher für den Tausch.
* `free`: Die Menge des freien Arbeitsspeichers.
* `buff`: Die Für Puffer verwendete Arbeitsspeichermenge.
* `cache`: Die Für den Cache verwendete Arbeitsspeichermenge.

> [!NOTE]
> Die Werte werden in Byte angezeigt.

Dieser Abschnitt bietet eine allgemeine Übersicht über die Speicherauslastung.

#### `swap`

Der Tauschabschnitt hat zwei Spalten:

* `si`: Die Menge des speichertauschten Speichers (vom Systemspeicher in den Austausch verschoben) pro Sekunde.
* `so`: Die Menge des ausgelagerten Speichers (vom Austausch in den Systemspeicher verschoben) pro Sekunde.

Wenn ein hoher `si` Wert beobachtet wird, kann es ein System darstellen, das nicht genügend Systemspeicher aufweist und Seiten in den Austausch (Swapping) verschiebt.

#### `io`

Der `io` Abschnitt weist zwei Spalten auf:

* `bi`: Die Anzahl der von einem Blockgerät empfangenen Blöcke (liest Blöcke pro Sekunde) pro Sekunde.
* `bo`: Die Anzahl der an ein Blockgerät gesendeten Blöcke (Schreibvorgänge pro Sekunde) pro Sekunde.

> [!NOTE]
> Diese Werte befinden sich in Blöcken pro Sekunde.

#### `system`

Der `system` Abschnitt weist zwei Spalten auf:

* `in`: Die Anzahl der Unterbrechungen pro Sekunde.
* `cs`: Die Anzahl der Kontextoptionen pro Sekunde.

Eine hohe Anzahl von Unterbrechungen pro Sekunde kann auf ein System hinweisen, das mit Hardwaregeräten beschäftigt ist (z. B. Netzwerkvorgänge).

Eine hohe Anzahl von Kontextoptionen kann auf ein beschäftigtes System mit vielen kurzen Ausgeführten Prozessen hinweisen, es gibt hier keine gute oder schlechte Zahl.

#### `cpu`

Dieser Abschnitt enthält fünf Spalten:

* `us`: Prozentuale Auslastung des Benutzerraums.
* `sy`: Systemauslastung (Kernelraum) Prozentauslastung.
* `id`: Prozentsatz der Auslastung der Zeit, die die CPU im Leerlauf ist.
* `wa`: Prozentsatz der Auslastung der Zeit, die die CPU im Leerlauf auf Prozesse mit E/A wartet.
* `st`: Prozentsatz der Auslastung der Zeit, die die CPU für andere virtuelle CPUs aufgewendet hat (gilt nicht für Azure).

Die Werte werden in Prozent dargestellt. Diese Werte sind identisch mit der Darstellung des `mpstat` Dienstprogramms und dienen dazu, eine allgemeine Übersicht über die CPU-Auslastung bereitzustellen. Folgen Sie einem ähnlichen Prozess für "[Dinge, nach denen sie suchen](#mpstat)" `mpstat` bei der Überprüfung dieser Werte.

### `uptime`

Schließlich bietet das `uptime` Hilfsprogramm für CPU-bezogene Metriken einen umfassenden Überblick über die Systemlast mit den Werten für den Ladedurchschnitt.

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'uptime')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

```output
16:55:53 up 9 min,  2 users,  load average: 9.26, 2.91, 1.18
```

Der Lastdurchschnitt zeigt drei Zahlen an. Diese Zahlen gelten für `1`systemlastende `5` Intervalle und `15` Minutenintervalle.

Um diese Werte zu interpretieren, ist es wichtig, die Anzahl der verfügbaren CPUs im System zu kennen, die aus der `mpstat` Ausgabe vorher abgerufen wurden. Der Wert hängt von den gesamten CPUs ab, sodass das System als Beispiel für die `mpstat` Ausgabe 8 CPUs aufweist, würde ein Lastdurchschnitt von 8 bedeuten, dass ALLE Kerne auf 100 % geladen werden.

Ein Wert würde `4` bedeuten, dass die Hälfte der CPUs mit 100 % geladen wurden (oder insgesamt 50 % last auf ALL CPUs). In der vorherigen Ausgabe lautet `9.26`der Lastdurchschnitt , was bedeutet, dass die CPU bei ca. 115 % geladen wird.

Mit `1m`den `5m``15m` Intervallen können Sie ermitteln, ob die Last im Laufe der Zeit zunimmt oder verringert wird.

> [HINWEIS] Der `nproc` Befehl kann auch verwendet werden, um die Anzahl der CPUs abzurufen.

## Arbeitsspeicher

Für den Arbeitsspeicher gibt es zwei Befehle, die Details zur Verwendung abrufen können.

### `free`

Der `free` Befehl zeigt die Systemspeicherauslastung an.

Informationen zur Ausführung:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'free -h')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Die Optionen und Argumente sind:

* `-h`: Dynamisches Anzeigen von Werten als lesbare Menschen (z. B. Mib, Gib, Tib)

Die Ausgabe ist:

```output
               total        used        free      shared  buff/cache   available
Mem:            31Gi        19Gi        12Gi        23Mi        87Mi        11Gi
Swap:           23Gi          0B        23Gi
```

Suchen Sie aus der Ausgabe nach dem gesamten Systemspeicher und dem verfügbaren Speicher und dem verwendeten vs. Gesamttausch. Der verfügbare Arbeitsspeicher berücksichtigt den für den Cache zugewiesenen Speicher, der für Benutzeranwendungen zurückgegeben werden kann.

Einige Swap-Verwendung ist in modernen Kerneln normal, da einige weniger häufig verwendete Speicherseiten in den Austausch verschoben werden können.

### `swapon`

Der `swapon` Befehl zeigt an, wo swap konfiguriert ist und welche Prioritäten die Swap-Geräte oder Dateien haben.

So führen Sie den Befehl aus:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'swapon -s')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Die Ausgabe ist:

```output
Filename      Type          Size          Used   Priority
/dev/zram0    partition     16G           0B      100
/mnt/swapfile file          8G            0B      -2
```

Diese Informationen sind wichtig, um zu überprüfen, ob der Tausch an einem Speicherort konfiguriert ist, der nicht ideal ist, z. B. auf einem Daten- oder Betriebssystemdatenträger. Im Azure-Referenzframe sollte swap auf dem kurzlebigen Laufwerk konfiguriert werden, da er die beste Leistung bietet.

### Dinge, die Sie suchen sollten

* Denken Sie daran, dass der Speicher eine endliche Ressource ist, sobald sowohl der Systemspeicher (RAM) als auch der Austausch erschöpft ist, die Prozesse vom Out Of Memorry Killer (OOM) getötet werden sollen.
* Überprüfen Sie, ob der Swap nicht auf einem Datenträger oder Betriebssystemdatenträger konfiguriert ist, da dadurch Aufgrund von Latenzunterschieden Probleme mit E/A auftreten. Swap sollte auf dem kurzlebigen Laufwerk konfiguriert werden.
* Denken Sie auch daran, dass es üblich ist, in der `free -h` Ausgabe zu sehen, dass die freien Werte nahe null sind, dieses Verhalten liegt auf seitencache, der Kernel gibt diese Seiten nach Bedarf frei.

## E/A

Datenträger-E/A ist einer der Bereiche, in denen Azure am meisten leidet, wenn sie gedrosselt werden, da Datenträger Latenzen erreichen `100ms+` können. Die folgenden Befehle helfen, diese Szenarien zu identifizieren.

### `iostat`

Das `iostat` Hilfsprogramm ist Teil des `sysstat` Pakets. Es wird pro Blockgerätenutzungsstatistik angezeigt und hilft, verwandte Leistungsprobleme zu blockieren.

Das `iostat` Hilfsprogramm enthält Details zu Metriken wie Durchsatz, Latenz und Warteschlangengröße. Diese Metriken helfen zu verstehen, ob Datenträger-E/A zu einem grenzwertigen Faktor wird.
Verwenden Sie zum Ausführen den Befehl:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'iostat -dxtm 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Die Optionen und Argumente sind:

* `-d`: Pro Gerätenutzungsbericht.
* `-x`: Erweiterte Statistiken.
* `-t`: Zeigt den Zeitstempel für jeden Bericht an.
* `-m`: In MB/s anzeigen.
* `1`: Das erste numerische Argument gibt an, wie oft die Anzeige in Sekunden aktualisiert werden soll.
* `2`: Das zweite numerische Argument gibt an, wie oft die Daten aktualisiert werden.

Die Ausgabe ist:

```output
Linux 5.14.0-362.8.1.el9_3.x86_64 (alma9)       02/21/24        _x86_64_        (8 CPU)

02/21/24 16:55:50
Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
sda              1.07      0.02     0.00   0.00    1.95    20.40   23.25     24.55     3.30  12.42  113.75  1081.06    0.26    537.75     0.26  49.83    0.03 2083250.04    0.00    0.00    2.65   2.42
sdb             16.99      0.67     0.36   2.05    2.00    40.47   65.26      0.44     1.55   2.32    1.32     6.92    0.00      0.00     0.00   0.00    0.00     0.00   30.56    1.30    0.16   7.16
zram0            0.51      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.00   0.00

```

Die Ausgabe enthält mehrere Spalten, die aufgrund der `-x` Option nicht wichtig sind (zusätzliche Spalten), einige der wichtigen Spalten sind:

* `r/s`: Lesevorgänge pro Sekunde (IOPS).
* `rMB/s`: Megabyte pro Sekunde lesen.
* `r_await`: Leselatenz in Millisekunden.
* `rareq-sz`: Durchschnittliche Leseanforderungsgröße in Kilobyte.
* `w/s`: Schreibvorgänge pro Sekunde (IOPS).
* `wMB/s`: Schreiben Sie Megabyte pro Sekunde.
* `w_await`: Schreiblatenz in Millisekunden.
* `wareq-size`: Durchschnittliche Schreibanforderungsgröße in Kilobyte.
* `aqu-sz`: Durchschnittliche Warteschlangengröße.

#### Dinge, die Sie suchen sollten

* `r/s` Suchen und `w/s` (IOPS) und `rMB/s` überprüfen `wMB/s` Sie, ob diese Werte innerhalb der Grenzwerte des angegebenen Datenträgers liegen. Wenn die Werte geschlossen oder höher sind, wird der Datenträger gedrosselt, was zu einer hohen Latenz führt. Diese Informationen können auch mit der `%iowait` Metrik bestätigt werden.`mpstat`
* Die Latenz ist eine hervorragende Metrik, um zu überprüfen, ob der Datenträger erwartungsgemäß ausgeführt wird. Normalerweise haben andere Angebote unterschiedliche Latenzziele als `9ms` die erwartete Latenz für PremiumSSD.
* Die Warteschlangengröße ist ein hervorragender Indikator für die Sättigung. Normalerweise werden Anforderungen nahezu in Echtzeit bereitgestellt, und die Zahl bleibt in der Nähe eines (da die Warteschlange nie wächst). Eine höhere Zahl könnte auf die Datenträgersättigung hinweisen (d. r. Anforderungen, die anstehen). Für diese Metrik gibt es keine gute oder schlechte Zahl. Das Verständnis, dass alles höher als eins bedeutet, dass Anforderungen in der Warteschlange stehen, hilft zu ermitteln, ob die Datenträgersättigung besteht.

### `lsblk`

Das `lsblk` Hilfsprogramm zeigt die an das System angeschlossenen Blockgeräte an, während sie keine Leistungsmetriken bereitstellt, ermöglicht es einen schnellen Überblick darüber, wie diese Geräte konfiguriert sind und welche Mountpoints verwendet werden.

Verwenden Sie zum Ausführen den Befehl:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'lsblk')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Die Ausgabe ist:

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

#### Dinge, die Sie suchen sollten

* Suchen Sie, wo die Geräte montiert sind.
* Stellen Sie sicher, dass sie nicht innerhalb eines Datenträgers oder Betriebssystemdatenträgers konfiguriert ist, falls aktiviert.

> Hinweis: Eine einfache Möglichkeit, das Blockgerät mit einem LUN in Azure zu korrelieren, wird ausgeführt `ls -lr /dev/disk/azure`.

## Prozess

Das Sammeln von Details pro Prozess hilft zu verstehen, woher die Last des Systems kommt.

Das Haupthilfsprogramm zum Sammeln von Prozessstatiken besteht `pidstat` darin, dass sie Details pro Prozess für CPU-, Arbeitsspeicher- und E/A-Statistiken bereitstellt.

Schließlich vervollständigen eine einfache `ps` Sortierung nach top CPU und die Arbeitsspeicherauslastung die Metriken.

> [!NOTE]
> Da diese Befehle Details zu ausgeführten Prozessen anzeigen, müssen sie als Stamm ausgeführt werden.`sudo` Mit diesem Befehl können alle Prozesse und nicht nur die Benutzer angezeigt werden.

### `pidstat`

Das `pidstat` Hilfsprogramm ist auch Teil des `sysstat` Pakets. Es ist wie `mpstat` oder iostat, wo Metriken für einen bestimmten Zeitraum angezeigt werden. Zeigt standardmäßig `pidstat` nur Metriken für Prozesse mit Aktivität an.

Argumente für `pidstat` andere `sysstat` Hilfsprogramme sind identisch:

* 1: Das erste numerische Argument gibt an, wie oft die Anzeige in Sekunden aktualisiert wird.
* 2: Das zweite numerische Argument gibt an, wie oft die Daten aktualisiert werden.

> [!NOTE]
> Die Ausgabe kann erheblich wachsen, wenn es viele Prozesse mit Aktivität gibt.

#### Cpu-Statistik verarbeiten

Führen Sie zum Sammeln von CPU-Statistiken `pidstat` ohne Optionen die folgenden Schritte aus:

Die folgenden Befehle können verwendet werden, wenn Sie sie über Azure CLI ausführen möchten:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Die Ausgabe ist:

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

Der Befehl zeigt die Verwendung pro Prozess für `%usr`, `%system`, `%guest` (nicht anwendbar für Azure) `%wait`und die Gesamtnutzung `%CPU` an.

##### Dinge, die Sie suchen sollten

* Suchen Sie nach Prozessen mit hohem %wait (iowait)-Prozentsatz, da sie möglicherweise Auf E/A-Prozesse anzeigt, die auf E/A warten, was auch auf die Datenträgersättigung hindeuten kann.
* Stellen Sie sicher, dass kein einzelner Prozess 100 % der CPU verbraucht, da er auf eine einzelne Threadanwendung hinweisen kann.

#### Prozessspeicherstatistiken

Verwenden Sie die `-r` Folgende Option, um Prozessspeicherstatistiken zu erfassen:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -r 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Die Ausgabe ist:

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

Die gesammelten Metriken sind:

* `minflt/s`: Kleinere Fehler pro Sekunde, diese Metrik gibt die Anzahl der Seiten an, die aus dem Systemspeicher (RAM) geladen wurden.
* `mjflt/s`: Hauptfehler pro Sekunde, diese Metrik gibt die Anzahl der Seiten an, die vom Datenträger (SWAP) geladen wurden.
* `VSZ`: Virtueller Speicher, der in Bytes verwendet wird.
* `RSS`: Verwendeter Speicher (tatsächlich zugewiesener Speicher) in Byte.
* `%MEM`: Prozentsatz des gesamten verwendeten Arbeitsspeichers.
* `Command`: Der Name des Prozesses.

##### Dinge, die Sie suchen sollten

* Suchen Sie pro Sekunde nach hauptfehlern, da dieser Wert auf einen Prozess hinweisen würde, bei dem Seiten auf oder von einem Datenträger ausgetauscht werden. Dieses Verhalten kann auf die Speicherausschöpfung hinweisen und kann zu `OOM` Ereignissen oder Leistungsbeeinträchtigungen führen, die aufgrund eines langsameren Tauschs auftreten.
* Stellen Sie sicher, dass ein einzelner Prozess 100 % des verfügbaren Arbeitsspeichers nicht belegt. Dieses Verhalten könnte auf einen Speicherverlust hinweisen.

> [!NOTE]
> Die `--human` Option kann verwendet werden, um Zahlen im lesbaren Format (d. b `Kb`. , , `Mb`) `GB`anzuzeigen.

#### Prozess-E/A-Statistiken

Verwenden Sie die `-d` Folgende Option, um Prozessspeicherstatistiken zu erfassen:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -d 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Die Ausgabe ist:

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

Die gesammelten Metriken sind:

* `kB_rd/s`: Kilobyte pro Sekunde lesen.
* `kB_wr/s`: Schreiben Sie Kilobyte pro Sekunde.
* `Command`: Name des Prozesses.

##### Dinge, die Sie suchen sollten

* Suchen Sie nach einzelnen Prozessen mit hohen Lese-/Schreibraten pro Sekunde. Diese Informationen sind eine Anleitung für Prozesse mit E/A mehr als das Identifizieren von Problemen.
Hinweis: Die `--human` Option kann verwendet werden, um Zahlen im lesbaren Format (d. b `Kb`. , , , `Mb`) `GB`anzuzeigen.

### `ps`

Der Befehl zeigt schließlich `ps` Systemprozesse an und kann entweder nach CPU oder Arbeitsspeicher sortiert werden.

So sortieren Sie nach CPU und rufen die top 10 Prozesse ab:

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

So sortieren `MEM%` Und abrufen Sie die 10 wichtigsten Prozesse:

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

## Zusammensetzen aller

Ein einfaches Bash-Skript kann alle Details in einer einzelnen Ausführung sammeln und die Ausgabe zur späteren Verwendung an eine Datei anfügen:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2 && vmstat -w 1 5 && uptime && free -h && swapon && iostat -dxtm 1 1 && lsblk && ls -l /dev/disk/azure && pidstat 1 1 -h --human && pidstat -r 1 1 -h --human && pidstat -d 1 1 -h --human && ps aux --sort=-%cpu | head -20 && ps aux --sort=-%mem | head -20')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```

Zum Ausführen können Sie eine Datei mit dem obigen Inhalt erstellen, Ausführungsberechtigungen hinzufügen, indem Sie ausführen `chmod +x gather.sh`und mit `sudo ./gather.sh`.

Dieses Skript speichert die Ausgabe der Befehle in einer Datei im selben Verzeichnis, in dem das Skript aufgerufen wurde.

Darüber hinaus können alle Befehle in den in diesem Dokument behandelten Bash-Blockcodes mithilfe der Ausführungsbefehlserweiterung ausgeführt `az-cli` und die Ausgabe `jq` analysiert werden, um eine ähnliche Ausgabe zu erhalten, um die Befehle lokal auszuführen: '

```azurecli-interactive
output=$(az vm run-command invoke -g $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "ls -l /dev/disk/azure")
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```