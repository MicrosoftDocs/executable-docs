---
title: Prestatiegegevens verkrijgen van een Linux-systeem
description: Meer informatie over het verkrijgen van metrische prestatiegegevens van een Linux-systeem.
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

# Prestatiegegevens verkrijgen van een Linux-systeem

**Van toepassing op:** :heavy_check_mark: Virtuele Linux-machines

In dit artikel vindt u instructies om te bepalen hoe u snel metrische prestatiegegevens kunt verkrijgen van een Linux-systeem.

Er zijn verschillende opdrachten die kunnen worden gebruikt om prestatiemeteritems op Linux te verkrijgen. Opdrachten zoals `vmstat` en `uptime`, bieden algemene systeemgegevens, zoals CPU-gebruik, systeemgeheugen en systeembelasting.
De meeste opdrachten zijn standaard al geïnstalleerd, terwijl anderen direct beschikbaar zijn in standaardopslagplaatsen.
De opdrachten kunnen worden onderverdeeld in:

* CPU
* Geheugen
* Schijf-I/O
* Processen

## Installatie van Sysstat-hulpprogramma's

<!-- Commenting out these entries as this information should be selected by the user along with the corresponding subscription and region

The First step in this tutorial is to define environment variables, and install the corresponding package, if necessary.

```azurecli-interactive
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup89f292"
export MY_VM_NAME="myVM89f292"
```
-->

> [!NOTE]
> Sommige van deze opdrachten moeten worden uitgevoerd `root` om alle relevante details te kunnen verzamelen.

> [!NOTE]
> Sommige opdrachten maken deel uit van het `sysstat` pakket dat mogelijk niet standaard wordt geïnstalleerd. Het pakket kan eenvoudig worden geïnstalleerd met `sudo apt install sysstat`, `dnf install sysstat` of `zypper install sysstat` voor die populaire distributies.

De volledige opdracht voor de installatie van het `sysstat` pakket op een aantal populaire distributies is:

```bash
az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "/bin/bash -c 'OS=\$(cat /etc/os-release|grep NAME|head -1|cut -d= -f2 | sed \"s/\\\"//g\"); if [[ \$OS =~ \"Ubuntu\" ]] || [[ \$OS =~ \"Debian\" ]]; then sudo apt install sysstat -y; elif [[ \$OS =~ \"Red Hat\" ]]; then sudo dnf install sysstat -y; elif [[ \$OS =~ \"SUSE\" ]]; then sudo zypper install sysstat --non-interactive; else echo \"Unknown distribution\"; fi'"
```

## CPU

### <a id="mpstat"></a>mpstat

Het `mpstat` hulpprogramma maakt deel uit van het `sysstat` pakket. Het geeft per CPU-gebruik en gemiddelden weer, wat handig is om het CPU-gebruik snel te identificeren. `mpstat` biedt een overzicht van het CPU-gebruik voor de beschikbare CPU's, om het gebruiksbalans te identificeren en of één CPU zwaar wordt belast.

De volledige opdracht is:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

De opties en argumenten zijn:

* `-P`: Geeft de processor aan om statistieken weer te geven, het argument ALL geeft aan om statistieken weer te geven voor alle online CPU's in het systeem.
* `1`: Het eerste numerieke argument geeft aan hoe vaak de weergave in seconden moet worden vernieuwd.
* `2`: Het tweede numerieke argument geeft aan hoe vaak de gegevens worden vernieuwd.

Het aantal keren dat de `mpstat` opdracht gegevens weergeeft, kan worden gewijzigd door het tweede numerieke argument te verhogen om langere gegevensverzamelingstijden mogelijk te maken. In het ideale geval is 3 of 5 seconden voldoende, voor systemen met een verhoogd aantal kernen kan 2 seconden worden gebruikt om de hoeveelheid weergegeven gegevens te verminderen.
Uit de uitvoer:

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

Er zijn enkele belangrijke dingen die u moet noteren. Op de eerste regel wordt nuttige informatie weergegeven:

* Kernel en release: `5.14.0-362.8.1.el9_3.x86_64`
* Hostnaam: `alma9`
* Datum: `02/21/24`
* Architectuur: `_x86_64_`
* Totale hoeveelheid CPU's (deze informatie is handig om de uitvoer van andere opdrachten te interpreteren): `(8 CPU)`

Vervolgens worden de metrische gegevens voor de CPU's weergegeven om elk van de kolommen uit te leggen:

* `Time`: Het tijdstip waarop de steekproef is verzameld
* `CPU`: De CPU-numerieke id, de ALL-id is een gemiddelde voor alle CPU's.
* `%usr`: Het percentage CPU-gebruik voor gebruikersruimte, normaal gesproken gebruikerstoepassingen.
* `%nice`: Het percentage CPU-gebruik voor gebruikersruimteprocessen met een mooie waarde (prioriteit).
* `%sys`: Het percentage CPU-gebruik voor kernelruimteprocessen.
* `%iowait`: Het percentage CPU-tijd dat inactief is besteed aan wachten op openstaande I/O.
* `%irq`: Het percentage CPU-tijd dat wordt besteed aan het leveren van hardwareonderbreken.
* `%soft`: Het percentage CPU-tijd dat is besteed aan het leveren van softwareonderbreken.
* `%steal`: Het percentage CPU-tijd dat is besteed aan het leveren van andere virtuele machines (niet van toepassing op Azure vanwege een overprovisioning van CPU).
* `%guest`: Het percentage CPU-tijd dat wordt besteed aan het leveren van virtuele CPU's (niet van toepassing op Azure, alleen van toepassing op bare-metalsystemen waarop virtuele machines worden uitgevoerd).
* `%gnice`: Het percentage CPU-tijd dat wordt besteed aan het bedienen van virtuele CPU's met een mooie waarde (niet van toepassing op Azure, alleen van toepassing op bare-metalsystemen waarop virtuele machines worden uitgevoerd).
* `%idle`: Het percentage cpu-tijd dat inactief is besteed en zonder te wachten op I/O-aanvragen.

#### Dingen om uit te zoeken

Enkele details waarmee u rekening moet houden bij het controleren van de uitvoer voor `mpstat`:

* Controleer of alle CPU's correct zijn geladen en niet één CPU alle belasting verwerkt. Deze informatie kan duiden op één threaded toepassing.
* Zoek naar een gezonde balans tussen `%usr` en `%sys` naarmate het tegenovergestelde meer tijd aangeeft aan de werkelijke workload dan het leveren van kernelprocessen.
* `%iowait` Zoek naar percentages als hoge waarden kunnen duiden op een systeem dat voortdurend wacht op I/O-aanvragen.
* Hoog `%soft` gebruik kan duiden op hoog netwerkverkeer.

### `vmstat`

Het `vmstat` hulpprogramma is algemeen beschikbaar in de meeste Linux-distributies, het biedt een overzicht op hoog niveau voor CPU-, geheugen- en schijf-I/O-gebruik in één deelvenster.
De opdracht hiervoor `vmstat` is:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'vmstat -w 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

De opties en argumenten zijn:

* `-w`: Gebruik breed afdrukken om consistente kolommen te behouden.
* `1`: Het eerste numerieke argument geeft aan hoe vaak de weergave in seconden moet worden vernieuwd.
* `5`: Het tweede numerieke argument geeft aan hoe vaak de gegevens worden vernieuwd.

De uitvoer:

```output
--procs-- -----------------------memory---------------------- ---swap-- -----io---- -system-- --------cpu--------
   r    b         swpd         free         buff        cache   si   so    bi    bo   in   cs  us  sy  id  wa  st
  14    0            0     26059408          164       137468    0    0    89  3228   56  122   3   1  95   1   0
  14    1            0     24388660          164       145468    0    0     0  7811 3264 13870  76  24   0   0   0
  18    1            0     23060116          164       155272    0    0    44  8075 3704 15129  78  22   0   0   0
  18    1            0     21078640          164       165108    0    0   295  8837 3742 15529  73  27   0   0   0
  15    2            0     19015276          164       175960    0    0     9  8561 3639 15177  73  27   0   0   0
```

`vmstat` splitst de uitvoer in zes groepen:

* `procs`: statistieken voor processen.
* `memory`: statistieken voor systeemgeheugen.
* `swap`: statistieken voor wisselen.
* `io`: statistieken voor schijf-io.
* `system`: statistieken voor contextswitches en interrupts.
* `cpu`: statistieken voor CPU-gebruik.

>Opmerking: `vmstat` toont algemene statistieken voor het hele systeem (dat wil gezegd, alle CPU's, alle blokapparaten samengevoegd).

#### `procs`

De `procs` sectie heeft twee kolommen:

* `r`: Het aantal runnable processen in de uitvoeringswachtrij.
* `b`: Het aantal processen dat wacht op I/O.

In deze sectie wordt onmiddellijk weergegeven of er een knelpunt in het systeem is. Hoge getallen in een van de kolommen geven processen aan die wachten op resources.

De `r` kolom geeft het aantal processen aan dat wacht tot de CPU-tijd kan worden uitgevoerd. Een eenvoudige manier om dit aantal te interpreteren is als volgt: als het aantal processen in de `r` wachtrij hoger is dan het totale aantal CPU's, kan worden afgeleid dat het systeem de CPU zwaar heeft geladen en kan er geen CPU-tijd worden toegewezen voor alle processen die wachten om te worden uitgevoerd.

De `b` kolom geeft het aantal processen aan dat wacht op uitvoering die worden geblokkeerd door I/O-aanvragen. Een hoog getal in deze kolom geeft een systeem aan dat een hoge I/O heeft en processen niet kunnen worden uitgevoerd vanwege andere processen die wachten op voltooide I/O-aanvragen. Dit kan ook duiden op hoge schijflatentie.

#### `memory`

De geheugensectie heeft vier kolommen:

* `swpd`: het gebruikte geheugen voor het wisselen van hoeveelheid.
* `free`: De hoeveelheid geheugen vrij.
* `buff`: De hoeveelheid geheugen die wordt gebruikt voor buffers.
* `cache`: De hoeveelheid geheugen die wordt gebruikt voor cache.

> [!NOTE]
> De waarden worden weergegeven in bytes.

Deze sectie bevat een algemeen overzicht van het geheugengebruik.

#### `swap`

De wisselsectie heeft twee kolommen:

* `si`: De hoeveelheid geheugen die is gewisseld in (verplaatst van systeemgeheugen naar wissel) per seconde.
* `so`: De hoeveelheid geheugen die is verwisseld (verplaatst van wissel naar systeemgeheugen) per seconde.

Als hoog `si` wordt waargenomen, kan het een systeem vertegenwoordigen dat onvoldoende systeemgeheugen heeft en pagina's verplaatst om te wisselen (wisselen).

#### `io`

De `io` sectie heeft twee kolommen:

* `bi`: Het aantal blokken dat is ontvangen van een blokapparaat (leesblokken per seconde) per seconde.
* `bo`: Het aantal blokken dat per seconde naar een blokapparaat wordt verzonden (schrijfbewerkingen per seconde).

> [!NOTE]
> Deze waarden bevinden zich in blokken per seconde.

#### `system`

De `system` sectie heeft twee kolommen:

* `in`: Het aantal interrupts per seconde.
* `cs`: Het aantal contextswitches per seconde.

Een groot aantal interrupts per seconde kan duiden op een systeem dat bezig is met hardwareapparaten (bijvoorbeeld netwerkbewerkingen).

Een groot aantal contextswitches kan duiden op een bezet systeem met veel kortlopende processen, er is hier geen goed of slecht nummer.

#### `cpu`

Deze sectie heeft vijf kolommen:

* `us`: Gebruikspercentage gebruikersruimte.
* `sy`: Systeem (kernelruimte) percentage gebruik.
* `id`: Percentage gebruik van de hoeveelheid tijd die de CPU inactief is.
* `wa`: Percentage gebruik van de hoeveelheid tijd die de CPU niet-actief wacht op processen met I/O.
* `st`: Percentage gebruik van de hoeveelheid tijd die de CPU heeft besteed aan andere virtuele CPU's (niet van toepassing op Azure).

De waarden worden weergegeven in percentage. Deze waarden zijn hetzelfde als die worden gepresenteerd door het `mpstat` hulpprogramma en dienen om een overzicht van het CPU-gebruik op hoog niveau te bieden. Volg een vergelijkbaar proces voor '[Dingen waar u op moet letten](#mpstat)' voor `mpstat` bij het controleren van deze waarden.

### `uptime`

Ten slotte biedt het `uptime` hulpprogramma voor cpu-gerelateerde metrische gegevens een breed overzicht van de systeembelasting met de gemiddelde waarden voor de belasting.

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'uptime')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

```output
16:55:53 up 9 min,  2 users,  load average: 9.26, 2.91, 1.18
```

Het gemiddelde van de belasting geeft drie getallen weer. Deze getallen zijn voor `1`en `5` `15` minuten van systeembelasting.

Als u deze waarden wilt interpreteren, is het belangrijk om het aantal beschikbare CPU's in het systeem te weten, dat u eerder hebt verkregen uit de `mpstat` uitvoer. De waarde is afhankelijk van het totale AANTAL CPU's, dus als voorbeeld van de `mpstat` uitvoer heeft het systeem 8 CPU's, betekent een belastinggemiddelde van 8 dat ALLE kernen worden geladen tot een 100%.

Een waarde van `4` deze waarde betekent dat de helft van de CPU's met 100% is geladen (of een totaal van 50% belasting op ALLE CPU's). In de vorige uitvoer is `9.26`het laadgemiddelde, wat betekent dat de CPU ongeveer 115% wordt geladen.

`5m``15m` Met `1m`de intervallen kunt u bepalen of de belasting na verloop van tijd toeneemt of afneemt.

> [OPMERKING] De `nproc` opdracht kan ook worden gebruikt om het aantal CPU's te verkrijgen.

## Geheugen

Voor geheugen zijn er twee opdrachten die details over gebruik kunnen verkrijgen.

### `free`

De `free` opdracht toont het geheugengebruik van het systeem.

Ga als volgende te werk om het uit te voeren:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'free -h')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

De opties en argumenten zijn:

* `-h`: Waarden dynamisch weergeven als leesbaar voor mensen (bijvoorbeeld: Mib, Gib, Tib)

De uitvoer:

```output
               total        used        free      shared  buff/cache   available
Mem:            31Gi        19Gi        12Gi        23Mi        87Mi        11Gi
Swap:           23Gi          0B        23Gi
```

Zoek in de uitvoer naar het totale systeemgeheugen versus de beschikbare en de gebruikte vs total swap. Het beschikbare geheugen houdt rekening met het geheugen dat is toegewezen voor de cache, die kan worden geretourneerd voor gebruikerstoepassingen.

Sommige wisselgebruik is normaal in moderne kernels, omdat sommige minder vaak gebruikte geheugenpagina's kunnen worden verplaatst naar wisselen.

### `swapon`

De `swapon` opdracht geeft weer waar wisselen is geconfigureerd en de respectieve prioriteiten van de wisselapparaten of bestanden.

Voer de volgende opdracht uit:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'swapon -s')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

De uitvoer:

```output
Filename      Type          Size          Used   Priority
/dev/zram0    partition     16G           0B      100
/mnt/swapfile file          8G            0B      -2
```

Deze informatie is belangrijk om te controleren of wisselen is geconfigureerd op een locatie die niet ideaal is, bijvoorbeeld op een gegevens- of besturingssysteemschijf. In het Referentieframe van Azure moet wisselen worden geconfigureerd op het kortstondige station, omdat deze de beste prestaties biedt.

### Dingen om uit te zoeken

* Houd er rekening mee dat het geheugen een eindige resource is, zodra zowel systeemgeheugen (RAM) als wisselen is uitgeput, moeten de processen worden gedood door de OOM (Out Of Memorry Killer).
* Controleer of wisselen niet is geconfigureerd op een gegevensschijf of de besturingssysteemschijf, omdat hierdoor problemen met I/O ontstaan vanwege latentieverschillen. Wisselen moet worden geconfigureerd op het tijdelijke station.
* Houd er ook rekening mee dat het gebruikelijk is om te zien in de `free -h` uitvoer dat de gratis waarden dicht bij nul liggen. Dit gedrag wordt veroorzaakt door de paginacache. De kernel publiceert deze pagina's indien nodig.

## I/O

Schijf-I/O is een van de gebieden waar Azure het meest last van heeft wanneer deze wordt beperkt, omdat schijven latenties kunnen bereiken `100ms+` . Met de volgende opdrachten kunt u deze scenario's identificeren.

### `iostat`

Het `iostat` hulpprogramma maakt deel uit van het `sysstat` pakket. Er worden statistieken over apparaatgebruik per blok weergegeven en helpt bij het identificeren van prestatieproblemen met betrekking tot blokkeringen.

Het `iostat` hulpprogramma biedt details voor metrische gegevens, zoals doorvoer, latentie en wachtrijgrootte. Deze metrische gegevens helpen te begrijpen of schijf-I/O een beperkende factor wordt.
Gebruik de volgende opdracht om uit te voeren:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'iostat -dxtm 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

De opties en argumenten zijn:

* `-d`: per apparaatgebruiksrapport.
* `-x`: Uitgebreide statistieken.
* `-t`: De tijdstempel voor elk rapport weergeven.
* `-m`: Weergeven in MB/s.
* `1`: Het eerste numerieke argument geeft aan hoe vaak de weergave in seconden moet worden vernieuwd.
* `2`: Het tweede numerieke argument geeft aan hoe vaak de gegevens worden vernieuwd.

De uitvoer:

```output
Linux 5.14.0-362.8.1.el9_3.x86_64 (alma9)       02/21/24        _x86_64_        (8 CPU)

02/21/24 16:55:50
Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
sda              1.07      0.02     0.00   0.00    1.95    20.40   23.25     24.55     3.30  12.42  113.75  1081.06    0.26    537.75     0.26  49.83    0.03 2083250.04    0.00    0.00    2.65   2.42
sdb             16.99      0.67     0.36   2.05    2.00    40.47   65.26      0.44     1.55   2.32    1.32     6.92    0.00      0.00     0.00   0.00    0.00     0.00   30.56    1.30    0.16   7.16
zram0            0.51      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.00   0.00

```

De uitvoer heeft verschillende kolommen die niet belangrijk zijn (extra kolommen vanwege de `-x` optie), enkele van de belangrijke kolommen zijn:

* `r/s`: Leesbewerkingen per seconde (IOPS).
* `rMB/s`: lees megabytes per seconde.
* `r_await`: Leeslatentie in milliseconden.
* `rareq-sz`: Gemiddelde grootte van leesaanvragen in kilobytes.
* `w/s`: Schrijfbewerkingen per seconde (IOPS).
* `wMB/s`: Megabytes per seconde schrijven.
* `w_await`: Schrijflatentie in milliseconden.
* `wareq-size`: Gemiddelde grootte van schrijfaanvragen in kilobytes.
* `aqu-sz`: Gemiddelde wachtrijgrootte.

#### Dingen om uit te zoeken

* `r/s` Zoek en `w/s` (IOPS) en `rMB/s` controleer of `wMB/s` deze waarden binnen de grenzen van de opgegeven schijf vallen. Als de waarden dicht of hoger zijn, wordt de schijf beperkt, wat leidt tot een hoge latentie. Deze informatie kan ook worden bevestigd met de `%iowait` metrische waarde van `mpstat`.
* De latentie is een uitstekende metrische waarde om te controleren of de schijf werkt zoals verwacht. Normaal gesproken `9ms` hebben andere aanbiedingen andere latentiedoelen dan de verwachte latentie voor PremiumSSD.
* De wachtrijgrootte is een uitstekende indicator van verzadiging. Normaal gesproken worden aanvragen bijna in realtime verwerkt en blijft het aantal dicht bij één (naarmate de wachtrij nooit groeit). Een hoger getal kan duiden op schijfverzadiging (dat wil gezegd aanvragen in de wachtrij plaatsen). Er is geen goed of ongeldig getal voor deze metrische waarde. Als u weet dat er iets hoger is dan één, betekent dat aanvragen in de wachtrij staan, kunt u bepalen of er sprake is van schijfverzadiging.

### `lsblk`

Het `lsblk` hulpprogramma toont de blokapparaten die zijn gekoppeld aan het systeem, terwijl het geen prestatiemetrieken biedt, het biedt een snel overzicht van hoe deze apparaten worden geconfigureerd en welke koppelpunten worden gebruikt.

Gebruik de volgende opdracht om uit te voeren:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'lsblk')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

De uitvoer:

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

#### Dingen om uit te zoeken

* Zoek waar de apparaten zijn gekoppeld.
* Controleer of wisselen niet is geconfigureerd binnen een gegevensschijf of besturingssysteemschijf, indien ingeschakeld.

> Opmerking: Een eenvoudige manier om het blokapparaat te correleren met een LUN in Azure is door uit te voeren `ls -lr /dev/disk/azure`.

## Proces

Het verzamelen van details per proces helpt inzicht te krijgen in waar de belasting van het systeem vandaan komt.

Het belangrijkste hulpprogramma voor het verzamelen van processtatistiek is `pidstat` omdat het details per proces biedt voor cpu-, geheugen- en I/O-statistieken.

Ten slotte voltooit een eenvoudig `ps` te sorteren proces op het hoogste CPU-gebruik en het geheugengebruik voltooit de metrische gegevens.

> [!NOTE]
> Omdat deze opdrachten details over het uitvoeren van processen weergeven, moeten ze worden uitgevoerd als root met `sudo`. Met deze opdracht kunnen alle processen worden weergegeven en niet alleen de gebruikers.

### `pidstat`

Het `pidstat` hulpprogramma maakt ook deel uit van het `sysstat` pakket. Het is net als `mpstat` of iostat waar metrische gegevens gedurende een bepaalde tijd worden weergegeven. `pidstat` Standaard worden alleen metrische gegevens weergegeven voor processen met activiteit.

Argumenten voor `pidstat` zijn hetzelfde voor andere `sysstat` hulpprogramma's:

* 1: Het eerste numerieke argument geeft aan hoe vaak de weergave in seconden moet worden vernieuwd.
* 2: Het tweede numerieke argument geeft aan hoe vaak de gegevens worden vernieuwd.

> [!NOTE]
> De uitvoer kan aanzienlijk toenemen als er veel processen met activiteit zijn.

#### CPU-statistieken verwerken

Als u proces-CPU-statistieken wilt verzamelen, voert u deze uit `pidstat` zonder opties:

De volgende opdrachten kunnen worden gebruikt als u deze wilt uitvoeren vanuit Azure CLI:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

De uitvoer:

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

De opdracht geeft per procesgebruik weer voor `%usr`, `%guest` `%system`(niet van toepassing op Azure) `%wait`en het totale `%CPU` gebruik.

##### Dingen om uit te zoeken

* Zoek naar processen met een hoog percentage %wait (iowait), omdat dit kan duiden op processen die worden geblokkeerd op I/O, wat ook kan duiden op schijfverzadiging.
* Controleer of er geen enkel proces 100% van de CPU verbruikt, omdat dit kan duiden op één threaded toepassing.

#### Geheugenstatistieken verwerken

Als u procesgeheugenstatistieken wilt verzamelen, gebruikt u de `-r` volgende optie:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -r 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

De uitvoer:

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

De verzamelde metrische gegevens zijn:

* `minflt/s`: Kleine fouten per seconde, deze metrische waarde geeft het aantal pagina's aan dat is geladen vanuit het systeemgeheugen (RAM).
* `mjflt/s`: Belangrijke fouten per seconde, deze metrische waarde geeft het aantal pagina's aan dat is geladen vanaf schijf (SWAP).
* `VSZ`: Virtueel geheugen dat wordt gebruikt in bytes.
* `RSS`: Ingezet geheugen gebruikt (werkelijk toegewezen geheugen) in bytes.
* `%MEM`: Percentage van het totale gebruikte geheugen.
* `Command`: De naam van het proces.

##### Dingen om uit te zoeken

* Zoek naar belangrijke fouten per seconde, omdat deze waarde een proces aangeeft dat pagina's verwisselt naar of van schijf. Dit gedrag kan duiden op geheugenuitputting en kan leiden tot `OOM` gebeurtenissen of prestatievermindering als gevolg van tragere swap.
* Controleer of één proces niet 100% van het beschikbare geheugen verbruikt. Dit gedrag kan duiden op een geheugenlek.

> [!NOTE]
> de `--human` optie kan worden gebruikt om getallen weer te geven in een leesbare indeling (dat wil `Kb`gezegd, `Mb`, , ). `GB`

#### I/O-statistieken verwerken

Als u procesgeheugenstatistieken wilt verzamelen, gebruikt u de `-d` volgende optie:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -d 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

De uitvoer:

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

De verzamelde metrische gegevens zijn:

* `kB_rd/s`: kilobytes per seconde lezen.
* `kB_wr/s`: kilobytes per seconde schrijven.
* `Command`: Naam van het proces.

##### Dingen om uit te zoeken

* Zoek naar afzonderlijke processen met een hoge lees-/schrijfsnelheid per seconde. Deze informatie is een richtlijn voor processen met I/O meer dan het identificeren van problemen.
Opmerking: de `--human` optie kan worden gebruikt om getallen weer te geven in de leesbare notatie (dat wil `Kb`gezegd, `Mb`, , ). `GB`

### `ps`

`ps` Ten slotte geeft de opdracht systeemprocessen weer en kan worden gesorteerd op CPU of geheugen.

Om te sorteren op CPU en de top 10 processen te verkrijgen:

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

De top 10 processen sorteren `MEM%` en ophalen:

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

## Alles samenstellen

Een eenvoudig bash-script kan alle details in één uitvoering verzamelen en de uitvoer toevoegen aan een bestand voor later gebruik:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2 && vmstat -w 1 5 && uptime && free -h && swapon && iostat -dxtm 1 1 && lsblk && ls -l /dev/disk/azure && pidstat 1 1 -h --human && pidstat -r 1 1 -h --human && pidstat -d 1 1 -h --human && ps aux --sort=-%cpu | head -20 && ps aux --sort=-%mem | head -20')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```

Als u wilt uitvoeren, kunt u een bestand maken met de bovenstaande inhoud, uitvoeringsmachtigingen toevoegen door uit te voeren `chmod +x gather.sh`en uit te voeren met `sudo ./gather.sh`.

Met dit script wordt de uitvoer van de opdrachten opgeslagen in een bestand in dezelfde map waarin het script is aangeroepen.

Daarnaast kunnen alle opdrachten in de bash-blokcodes die in dit document worden behandeld, worden uitgevoerd `az-cli` met behulp van de run-command-extensie en het parseren van de uitvoer `jq` om een vergelijkbare uitvoer te verkrijgen als het lokaal uitvoeren van de opdrachten: '

```azurecli-interactive
output=$(az vm run-command invoke -g $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "ls -l /dev/disk/azure")
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```