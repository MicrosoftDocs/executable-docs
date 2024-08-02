---
title: Hämta prestandamått från ett Linux-system
description: Lär dig hur du hämtar prestandamått från ett Linux-system.
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

# Hämta prestandamått från ett Linux-system

**Gäller för:** :heavy_check_mark: Virtuella Linux-datorer

Den här artikeln beskriver instruktioner för att fastställa hur du snabbt kan hämta prestandamått från ett Linux-system.

Det finns flera kommandon som kan användas för att hämta prestandaräknare i Linux. Kommandon som `vmstat` och `uptime`ger allmänna systemmått som CPU-användning, systemminne och systembelastning.
De flesta kommandon har redan installerats som standard och andra är lättillgängliga i standardlagringsplatser.
Kommandona kan delas in i:

* Processor
* Minne
* Disk-I/O
* Processer

## Installation av Sysstat-verktyg

<!-- Commenting out these entries as this information should be selected by the user along with the corresponding subscription and region

The First step in this tutorial is to define environment variables, and install the corresponding package, if necessary.

```azurecli-interactive
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup89f292"
export MY_VM_NAME="myVM89f292"
```
-->

> [!NOTE]
> Vissa av dessa kommandon måste köras för `root` att kunna samla in all relevant information.

> [!NOTE]
> Vissa kommandon ingår i `sysstat` paketet som kanske inte installeras som standard. Paketet kan enkelt installeras med `sudo apt install sysstat`, `dnf install sysstat` eller `zypper install sysstat` för de populära distributionerna.

Det fullständiga kommandot för installation av `sysstat` paketet på några populära distributioner är:

```bash
az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "/bin/bash -c 'OS=\$(cat /etc/os-release|grep NAME|head -1|cut -d= -f2 | sed \"s/\\\"//g\"); if [[ \$OS =~ \"Ubuntu\" ]] || [[ \$OS =~ \"Debian\" ]]; then sudo apt install sysstat -y; elif [[ \$OS =~ \"Red Hat\" ]]; then sudo dnf install sysstat -y; elif [[ \$OS =~ \"SUSE\" ]]; then sudo zypper install sysstat --non-interactive; else echo \"Unknown distribution\"; fi'"
```

## Processor

### <a id="mpstat"></a>mpstat

Verktyget `mpstat` är en del av `sysstat` paketet. Den visar per CPU-användning och medelvärden, vilket är användbart för att snabbt identifiera CPU-användning. `mpstat` ger en översikt över CPU-användningen i de tillgängliga processorerna, vilket hjälper till att identifiera användningssaldot och om en enda processor är kraftigt belastad.

Det fullständiga kommandot är:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Alternativen och argumenten är:

* `-P`: Anger processorn för att visa statistik, argumentet ALL anger att statistik ska visas för alla online-processorer i systemet.
* `1`: Det första numeriska argumentet anger hur ofta visningen ska uppdateras i sekunder.
* `2`: Det andra numeriska argumentet anger hur många gånger data uppdateras.

Antalet gånger `mpstat` som kommandot visar data kan ändras genom att öka det andra numeriska argumentet för att hantera längre datainsamlingstider. Helst 3 eller 5 sekunder bör räcka, för system med ökat antal kärnor 2 sekunder kan användas för att minska mängden data som visas.
Från utdata:

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

Det finns ett par viktiga saker att notera. Den första raden visar användbar information:

* Kernel och version: `5.14.0-362.8.1.el9_3.x86_64`
* Värdnamn: `alma9`
* Datum: `02/21/24`
* Arkitektur: `_x86_64_`
* Total mängd processorer (den här informationen är användbar för att tolka utdata från andra kommandon): `(8 CPU)`

Sedan visas måtten för processorerna för att förklara var och en av kolumnerna:

* `Time`: Den tid då exemplet samlades in
* `CPU`: Den numeriska cpu-identifieraren, ALL-identifieraren är ett genomsnitt för alla processorer.
* `%usr`: Procentandelen cpu-användning för användarutrymme, vanligtvis användarprogram.
* `%nice`: Procentandelen cpu-användning för användarutrymmesprocesser med ett trevligt värde (prioritet).
* `%sys`: Procentandelen cpu-användning för kernelutrymmesprocesser.
* `%iowait`: Procentandelen cpu-tid som ägnas åt att vänta på utestående I/O.
* `%irq`: Procentandelen cpu-tid som ägnas åt att hantera maskinvaruavbrott.
* `%soft`: Procentandelen cpu-tid som ägnas åt att hantera programavbrott.
* `%steal`: Procentandelen cpu-tid som ägnas åt att betjäna andra virtuella datorer (gäller inte för Azure på grund av ingen överetablering av CPU).
* `%guest`: Procentandelen cpu-tid som ägnas åt att betjäna virtuella processorer (gäller inte för Azure, gäller endast för bare metal-system som kör virtuella datorer).
* `%gnice`: Procentandelen cpu-tid som ägnas åt att betjäna virtuella processorer med ett fint värde (gäller inte för Azure, gäller endast för bare metal-system som kör virtuella datorer).
* `%idle`: Procentandelen cpu-tid som har lagts på viloläge och utan att vänta på I/O-begäranden.

#### Saker att hålla utkik efter

Lite information att tänka på när du granskar utdata för `mpstat`:

* Kontrollera att alla processorer är korrekt inlästa och att inte en enda processor hanterar all belastning. Den här informationen kan tyda på ett enda trådat program.
* Leta efter en felfri balans mellan `%usr` och `%sys` eftersom motsatsen skulle tyda på mer tid på den faktiska arbetsbelastningen än att hantera kernelprocesser.
* `%iowait` Leta efter procentandelar eftersom höga värden kan tyda på ett system som ständigt väntar på I/O-begäranden.
* Hög `%soft` användning kan tyda på hög nätverkstrafik.

### `vmstat`

Verktyget `vmstat` är allmänt tillgängligt i de flesta Linux-distributioner, det ger översikt på hög nivå för CPU-, minnes- och disk-I/O-användning i ett enda fönster.
Kommandot för `vmstat` är:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'vmstat -w 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Alternativen och argumenten är:

* `-w`: Använd bred utskrift för att behålla konsekventa kolumner.
* `1`: Det första numeriska argumentet anger hur ofta visningen ska uppdateras i sekunder.
* `5`: Det andra numeriska argumentet anger hur många gånger data uppdateras.

Utdata:

```output
--procs-- -----------------------memory---------------------- ---swap-- -----io---- -system-- --------cpu--------
   r    b         swpd         free         buff        cache   si   so    bi    bo   in   cs  us  sy  id  wa  st
  14    0            0     26059408          164       137468    0    0    89  3228   56  122   3   1  95   1   0
  14    1            0     24388660          164       145468    0    0     0  7811 3264 13870  76  24   0   0   0
  18    1            0     23060116          164       155272    0    0    44  8075 3704 15129  78  22   0   0   0
  18    1            0     21078640          164       165108    0    0   295  8837 3742 15529  73  27   0   0   0
  15    2            0     19015276          164       175960    0    0     9  8561 3639 15177  73  27   0   0   0
```

`vmstat` delar upp utdata i sex grupper:

* `procs`: statistik för processer.
* `memory`: statistik för systemminne.
* `swap`: statistik för växling.
* `io`: statistik för disk-io.
* `system`: statistik för kontextväxlar och avbrott.
* `cpu`: statistik för CPU-användning.

>`vmstat` Obs! visar övergripande statistik för hela systemet (d.v.s. alla processorer, alla blockenheter aggregerade).

#### `procs`

Avsnittet `procs` har två kolumner:

* `r`: Antalet körbara processer i körningskön.
* `b`: Antalet processer som blockerats i väntan på I/O.

Det här avsnittet visar omedelbart om det finns någon flaskhals i systemet. Höga tal på någon av kolumnerna anger processer som köar i väntan på resurser.

Kolumnen `r` anger antalet processer som väntar på att CPU-tid ska kunna köras. Ett enkelt sätt att tolka det här talet är följande: om antalet processer i `r` kön är högre än antalet totala processorer kan du dra slutsatsen att systemet har processorn kraftigt inläst och inte kan allokera CPU-tid för alla processer som väntar på att köras.

Kolumnen `b` anger antalet processer som väntar på att köras som blockeras av I/O-begäranden. Ett högt tal i den här kolumnen skulle indikera ett system som har hög I/O och processer kan inte köras på grund av att andra processer väntar på slutförda I/O-begäranden. Vilket också kan tyda på hög diskfördröjning.

#### `memory`

Minnesavsnittet har fyra kolumner:

* `swpd`: Mängden växlingsminne som används.
* `free`: Mängden ledigt minne.
* `buff`: Mängden minne som används för buffertar.
* `cache`: Mängden minne som används för cacheminnet.

> [!NOTE]
> Värdena visas i byte.

Det här avsnittet innehåller en översikt över minnesanvändning på hög nivå.

#### `swap`

Växlingsavsnittet har två kolumner:

* `si`: Mängden minne som växlas in (flyttas från systemminne till växling) per sekund.
* `so`: Mängden minne som växlats ut (flyttats från växling till systemminne) per sekund.

Om hög `si` observeras kan det representera ett system som börjar få slut på systemminne och flyttar sidor till växling (växling).

#### `io`

Avsnittet `io` har två kolumner:

* `bi`: Antalet block som tas emot från en blockenhet (läser block per sekund) per sekund.
* `bo`: Antalet block som skickas till en blockenhet (skrivningar per sekund) per sekund.

> [!NOTE]
> Dessa värden finns i block per sekund.

#### `system`

Avsnittet `system` har två kolumner:

* `in`: Antalet avbrott per sekund.
* `cs`: Antalet kontextväxlar per sekund.

Ett stort antal avbrott per sekund kan tyda på ett system som är upptaget med maskinvaruenheter (till exempel nätverksåtgärder).

Ett stort antal kontextväxlar kan tyda på ett upptaget system med många korta processer, det finns inget bra eller dåligt antal här.

#### `cpu`

Det här avsnittet innehåller fem kolumner:

* `us`: Användning av användarutrymme i procent.
* `sy`: Systemanvändning (kernelutrymme) procent.
* `id`: Procentuell användning av den tid processorn är inaktiv.
* `wa`: Procentuell användning av den tid processorn är inaktiv i väntan på processer med I/O.
* `st`: Procentuell användning av den tid som processorn har lagt ned på att betjäna andra virtuella processorer (gäller inte För Azure).

Värdena visas i procent. Dessa värden är samma som det som presenteras av `mpstat` verktyget och ger en översikt över CPU-användning på hög nivå. Följ en liknande process för "[Saker att hålla utkik](#mpstat) efter" för `mpstat` när du granskar dessa värden.

### `uptime`

För CPU-relaterade mått `uptime` ger verktyget slutligen en bred översikt över systembelastningen med belastningsgenomsnittsvärdena.

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'uptime')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

```output
16:55:53 up 9 min,  2 users,  load average: 9.26, 2.91, 1.18
```

Belastningsgenomsnittet visar tre tal. Dessa tal är för `1`, `5` och `15` minutintervall för systembelastning.

För att tolka dessa värden är det viktigt att känna till antalet tillgängliga processorer i systemet, som hämtats från `mpstat` utdata tidigare. Värdet beror på det totala antalet processorer, så som ett exempel på `mpstat` utdata som systemet har 8 processorer, skulle ett belastningsgenomsnitt på 8 innebära att ALLA kärnor läses in till 100 %.

`4` Värdet skulle innebära att hälften av processorerna lästes in med 100 % (eller totalt 50 % belastning på ALLA processorer). I föregående utdata är `9.26`belastningsgenomsnittet , vilket innebär att processorn läses in med cirka 115 %.

Intervallen `1m`, `5m`hjälper `15m` dig att identifiera om belastningen ökar eller minskar över tid.

> [OBS] Kommandot `nproc` kan också användas för att hämta antalet processorer.

## Minne

För minne finns det två kommandon som kan hämta information om användningen.

### `free`

Kommandot `free` visar systemminnesanvändning.

Så här kör du den:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'free -h')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Alternativen och argumenten är:

* `-h`: Visa värden dynamiskt som läsbara för människor (till exempel: Mib, Gib, Tib)

Utdata:

```output
               total        used        free      shared  buff/cache   available
Mem:            31Gi        19Gi        12Gi        23Mi        87Mi        11Gi
Swap:           23Gi          0B        23Gi
```

Från utdata letar du efter det totala systemminnet jämfört med det tillgängliga och det använda kontra totala växlingen. Det tillgängliga minnet tar hänsyn till det minne som allokerats för cacheminnet, som kan returneras för användarprogram.

En del växlingsanvändning är normalt i moderna kärnor eftersom vissa mindre ofta använda minnessidor kan flyttas till växling.

### `swapon`

Kommandot `swapon` visar var växlingen har konfigurerats och respektive prioritet för växlingsenheterna eller filerna.

Så här kör du kommandot:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'swapon -s')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Utdata:

```output
Filename      Type          Size          Used   Priority
/dev/zram0    partition     16G           0B      100
/mnt/swapfile file          8G            0B      -2
```

Den här informationen är viktig för att kontrollera om växlingen har konfigurerats på en plats som inte är idealisk, till exempel på en data- eller OS-disk. I Referensramen för Azure ska växlingen konfigureras på den tillfälliga enheten eftersom den ger bästa möjliga prestanda.

### Saker att hålla utkik efter

* Tänk på att minnet är en begränsad resurs, när både systemminnet (RAM) och bytet är uttömt, ska processerna avlivas av Out Of Memorry-mördaren (OOM).
* Kontrollera att växlingen inte har konfigurerats på en datadisk eller os-disk, eftersom det skulle skapa problem med I/O på grund av skillnader i svarstid. Växling ska konfigureras på den tillfälliga enheten.
* Tänk också på att det är vanligt att se på `free -h` utdata att de kostnadsfria värdena är nära noll, det här beteendet beror på sidcache, kerneln släpper dessa sidor efter behov.

## I/O

Disk-I/O är ett av de områden som Azure drabbas mest av när den begränsas, eftersom diskar kan nå `100ms+` svarstider. Följande kommandon hjälper dig att identifiera dessa scenarier.

### `iostat`

Verktyget `iostat` är en del av `sysstat` paketet. Den visar användningsstatistik per blockeringsenhet och hjälper till att identifiera blockrelaterade prestandaproblem.

Verktyget `iostat` innehåller information om mått som dataflöde, svarstid och köstorlek. Dessa mått hjälper dig att förstå om disk-I/O blir en begränsande faktor.
Om du vill köra använder du kommandot:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'iostat -dxtm 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Alternativen och argumenten är:

* `-d`: Per enhetsanvändningsrapport.
* `-x`: Utökad statistik.
* `-t`: Visa tidsstämpeln för varje rapport.
* `-m`: Visas i MB/s.
* `1`: Det första numeriska argumentet anger hur ofta visningen ska uppdateras i sekunder.
* `2`: Det andra numeriska argumentet anger hur många gånger data uppdateras.

Utdata:

```output
Linux 5.14.0-362.8.1.el9_3.x86_64 (alma9)       02/21/24        _x86_64_        (8 CPU)

02/21/24 16:55:50
Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
sda              1.07      0.02     0.00   0.00    1.95    20.40   23.25     24.55     3.30  12.42  113.75  1081.06    0.26    537.75     0.26  49.83    0.03 2083250.04    0.00    0.00    2.65   2.42
sdb             16.99      0.67     0.36   2.05    2.00    40.47   65.26      0.44     1.55   2.32    1.32     6.92    0.00      0.00     0.00   0.00    0.00     0.00   30.56    1.30    0.16   7.16
zram0            0.51      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.00   0.00

```

Utdata har flera kolumner som inte är viktiga (extra kolumner på grund av `-x` alternativet), några av de viktiga är:

* `r/s`: Läsåtgärder per sekund (IOPS).
* `rMB/s`: Läs megabyte per sekund.
* `r_await`: Lässvarstid i millisekunder.
* `rareq-sz`: Genomsnittlig storlek på läsbegäran i kilobyte.
* `w/s`: Skrivåtgärder per sekund (IOPS).
* `wMB/s`: Skriv megabyte per sekund.
* `w_await`: Skrivsvarstid i millisekunder.
* `wareq-size`: Genomsnittlig storlek på skrivbegäran i kilobyte.
* `aqu-sz`: Genomsnittlig köstorlek.

#### Saker att hålla utkik efter

* Leta efter och `w/s` (IOPS) och `rMB/s` och och `wMB/s` kontrollera att dessa värden ligger inom gränserna för `r/s` den angivna disken. Om värdena är nära eller högre begränsas disken, vilket leder till hög svarstid. Den här informationen kan också bekräftas med måttet `%iowait` från `mpstat`.
* Svarstiden är ett utmärkt mått för att kontrollera om disken fungerar som förväntat. Normalt sett har mindre än `9ms` den förväntade svarstiden för PremiumSSD andra erbjudanden olika svarstidsmål.
* Köstorleken är en bra indikator på mättnad. Normalt hanteras begäranden nära realtid och antalet förblir nära ett (eftersom kön aldrig växer). Ett högre tal kan tyda på diskmättnad (d.s. begäranden som köar). Det finns inget bra eller dåligt tal för det här måttet. Att förstå att allt som är högre än ett innebär att begäranden köar hjälper till att avgöra om det finns diskmättnad.

### `lsblk`

Verktyget `lsblk` visar de blockenheter som är anslutna till systemet, men det ger inte prestandamått, men ger en snabb översikt över hur dessa enheter konfigureras och vilka monteringspunkter som används.

Om du vill köra använder du kommandot:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'lsblk')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Utdata:

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

#### Saker att hålla utkik efter

* Leta efter var enheterna monteras.
* Kontrollera att växlingen inte har konfigurerats på en datadisk eller os-disk, om den är aktiverad.

> Obs! Ett enkelt sätt att korrelera blockenheten till ett LUN i Azure är att köra `ls -lr /dev/disk/azure`.

## Process

Genom att samla in information per process kan du förstå var belastningen på systemet kommer ifrån.

Det viktigaste verktyget för att samla in processstatik är `pidstat` eftersom det ger information per process för cpu-, minnes- och I/O-statistik.

Slutligen slutförs måtten genom en enkel `ps` sorteringsprocess efter den högsta cpu-användningen och minnesanvändningen.

> [!NOTE]
> Eftersom dessa kommandon visar information om processer som körs måste de köras som rot med `sudo`. Med det här kommandot kan alla processer visas och inte bara användarens.

### `pidstat`

Verktyget `pidstat` är också en del av `sysstat` paketet. Det är som `mpstat` eller iostat där det visar mått under en viss tid. Som standard `pidstat` visar endast mått för processer med aktivitet.

Argument för `pidstat` är desamma för andra `sysstat` verktyg:

* 1: Det första numeriska argumentet anger hur ofta skärmen ska uppdateras i sekunder.
* 2: Det andra numeriska argumentet anger hur många gånger data uppdateras.

> [!NOTE]
> Utdata kan öka avsevärt om det finns många processer med aktivitet.

#### Bearbeta CPU-statistik

Om du vill samla in processorstatistik för processer kör du `pidstat` utan några alternativ:

Följande kommandon kan användas om du vill köra dem från Azure CLI:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Utdata:

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

Kommandot visar per processanvändning för `%usr`, `%system`, `%guest` (gäller inte för Azure), `%wait`och total `%CPU` användning.

##### Saker att hålla utkik efter

* Leta efter processer med hög procentandel %wait (iowait) eftersom det kan tyda på processer som är blockerade och väntar på I/O, vilket också kan tyda på diskmättnad.
* Kontrollera att ingen enskild process förbrukar 100 % av processorn eftersom det kan tyda på ett enda trådat program.

#### Bearbeta minnesstatistik

Om du vill samla in minnesstatistik för processer använder du alternativet `-r` :

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -r 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Utdata:

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

De mått som samlas in är:

* `minflt/s`: Mindre fel per sekund anger det här måttet antalet sidor som lästs in från systemminnet (RAM).
* `mjflt/s`: Större fel per sekund anger det här måttet antalet sidor som lästs in från disken (SWAP).
* `VSZ`: Virtuellt minne som används i byte.
* `RSS`: Hemmaminne som används (faktiskt allokerat minne) i byte.
* `%MEM`: Procentandel av det totala minnet som används.
* `Command`: Namnet på processen.

##### Saker att hålla utkik efter

* Leta efter större fel per sekund, eftersom det här värdet indikerar en process som byter sidor till eller från disk. Det här beteendet kan tyda på minnesöverbelastning och kan leda till `OOM` händelser eller prestandaförsämring på grund av långsammare växling.
* Kontrollera att en enskild process inte förbrukar 100 % av det tillgängliga minnet. Det här beteendet kan tyda på en minnesläcka.

> [!NOTE]
> alternativet `--human` kan användas för att visa tal i mänskligt läsbart format (d.v.s. `Kb`, `Mb`, `GB`).

#### Bearbeta I/O-statistik

Om du vill samla in minnesstatistik för processer använder du alternativet `-d` :

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -d 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Utdata:

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

De mått som samlas in är:

* `kB_rd/s`: Läs kilobyte per sekund.
* `kB_wr/s`: Skriv kilobyte per sekund.
* `Command`: Namnet på processen.

##### Saker att hålla utkik efter

* Leta efter enkla processer med höga läs-/skrivfrekvenser per sekund. Den här informationen är en vägledning för processer med I/O mer än att identifiera problem.
`--human` Obs! Alternativet kan användas för att visa tal i mänskligt läsbart format (d.v.s. , `Kb``Mb`, `GB`).

### `ps`

`ps` Slutligen visar kommandot systemprocesser och kan antingen sorteras efter CPU eller minne.

Så här sorterar du efter CPU och hämtar de 10 främsta processerna:

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

Så här sorterar du efter `MEM%` och hämtar de 10 främsta processerna:

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

## Sätta ihop allt

Ett enkelt bash-skript kan samla in all information i en enda körning och lägga till utdata i en fil för senare användning:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2 && vmstat -w 1 5 && uptime && free -h && swapon && iostat -dxtm 1 1 && lsblk && ls -l /dev/disk/azure && pidstat 1 1 -h --human && pidstat -r 1 1 -h --human && pidstat -d 1 1 -h --human && ps aux --sort=-%cpu | head -20 && ps aux --sort=-%mem | head -20')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```

Om du vill köra kan du skapa en fil med innehållet ovan, lägga till körningsbehörigheter genom att köra `chmod +x gather.sh`och köra med `sudo ./gather.sh`.

Det här skriptet sparar utdata från kommandona i en fil som finns i samma katalog där skriptet anropades.

Dessutom kan alla kommandon i bash-blockkoderna som beskrivs i det här dokumentet köras med `az-cli` hjälp av körningskommandotillägget och parsa utdata för `jq` att få liknande utdata som att köra kommandona lokalt: "

```azurecli-interactive
output=$(az vm run-command invoke -g $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "ls -l /dev/disk/azure")
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```