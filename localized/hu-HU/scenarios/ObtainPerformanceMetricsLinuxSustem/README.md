---
title: Teljesítménymetrikák beszerzése Linux-rendszerből
description: 'Megtudhatja, hogyan szerezhet be teljesítménymetrikákat Linux-rendszerből.'
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

# Teljesítménymetrikák beszerzése Linux-rendszerből

**A következőre vonatkozik:** :heavy_check_mark: Linux rendszerű virtuális gépek

Ez a cikk a teljesítménymetrikák linuxos rendszerből való gyors beszerzésének módját ismerteti.

Linuxon több parancs is használható teljesítményszámlálók beszerzésére. Az olyan parancsok, mint a `vmstat` és `uptime`, általános rendszermetrikákat biztosítanak, például a processzorhasználatot, a rendszermemóriát és a rendszerterhelést.
A parancsok többsége alapértelmezés szerint már telepítve van, és mások is könnyen elérhetők az alapértelmezett adattárakban.
A parancsok a következőre oszthatók:

* CPU
* Memory (Memória)
* Lemez I/O
* Folyamatok

## Sysstat-segédprogramok telepítése

<!-- Commenting out these entries as this information should be selected by the user along with the corresponding subscription and region

The First step in this tutorial is to define environment variables, and install the corresponding package, if necessary.

```azurecli-interactive
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup89f292"
export MY_VM_NAME="myVM89f292"
```
-->

> [!NOTE]
> Néhány parancsot futtatni kell, hogy `root` összegyűjthesse az összes releváns részletet.

> [!NOTE]
> Egyes parancsok a `sysstat` csomag részét képezik, amelyek alapértelmezés szerint nem telepíthetők. A csomag egyszerűen telepíthető, `sudo apt install sysstat``dnf install sysstat` vagy `zypper install sysstat` a népszerű disztribúciókhoz.

A csomag néhány népszerű disztribúcióra való telepítésének `sysstat` teljes parancsa a következő:

```bash
az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "/bin/bash -c 'OS=\$(cat /etc/os-release|grep NAME|head -1|cut -d= -f2 | sed \"s/\\\"//g\"); if [[ \$OS =~ \"Ubuntu\" ]] || [[ \$OS =~ \"Debian\" ]]; then sudo apt install sysstat -y; elif [[ \$OS =~ \"Red Hat\" ]]; then sudo dnf install sysstat -y; elif [[ \$OS =~ \"SUSE\" ]]; then sudo zypper install sysstat --non-interactive; else echo \"Unknown distribution\"; fi'"
```

## CPU

### <a id="mpstat"></a>mpstat

A `mpstat` segédprogram a `sysstat` csomag része. Cpu-kihasználtságonként és átlagonként jelenik meg, ami hasznos a processzorhasználat gyors azonosításához. `mpstat` Áttekintést nyújt a cpu-kihasználtságról a rendelkezésre álló processzorok között, segít azonosítani a kihasználtság egyensúlyát, valamint azt, hogy egy processzor nagy terheléssel rendelkezik-e.

A teljes parancs a következő:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

A beállítások és az argumentumok a következők:

* `-P`: Azt jelzi, hogy a processzor megjelenítse-e a statisztikákat, az ALL argumentum pedig azt jelzi, hogy a rendszer összes online CPU-jának statisztikáit jeleníti meg.
* `1`: Az első numerikus argumentum azt jelzi, hogy milyen gyakran frissítse a kijelzőt másodpercek alatt.
* `2`: A második numerikus argumentum azt jelzi, hogy hányszor frissül az adat.

A parancs által megjelenített adatok hányszor `mpstat` módosíthatók a második numerikus argumentum növelésével, hogy hosszabb adatgyűjtési időhöz igazodjanak. Ideális esetben 3 vagy 5 másodpercnek elegendőnek kell lennie, a megnövekedett magszámú rendszerek esetében 2 másodperccel csökkenthető a megjelenített adatok mennyisége.
A kimenetből:

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

Van néhány fontos dolog, amit fel kell jegyezni. Az első sor hasznos információkat jelenít meg:

* Kernel és kiadás: `5.14.0-362.8.1.el9_3.x86_64`
* Állomásnév: `alma9`
* Dátum: `02/21/24`
* Építészet: `_x86_64_`
* Cpu-k teljes mennyisége (ez az információ hasznos a többi parancs kimenetének értelmezéséhez): `(8 CPU)`

Ezután megjelennek a CPU-k metrikái az egyes oszlopok magyarázatához:

* `Time`: A minta gyűjtésének időpontja
* `CPU`: A CPU numerikus azonosítója, az ALL azonosító az összes PROCESSZOR átlaga.
* `%usr`: A felhasználói terület, általában a felhasználói alkalmazások processzorhasználatának százalékos aránya.
* `%nice`: A felhasználóitér-folyamatok cpu-kihasználtságának százalékos aránya szép (prioritási) értékkel.
* `%sys`: A kerneltérfolyamatok processzorhasználatának százalékos aránya.
* `%iowait`: A processzorhasználati időnek a kiugró I/O-ra való várakozással töltött idő százalékos aránya.
* `%irq`: A hardveres megszakítások kiszolgálásával töltött processzoridő százalékos aránya.
* `%soft`: A szoftveres megszakítások kiszolgálásával töltött processzoridő százalékos aránya.
* `%steal`: A más virtuális gépek kiszolgálásával töltött processzoridő százalékos aránya (az Azure-ra nem vonatkozik a processzor túlterjedése miatt).
* `%guest`: A virtuális processzorok kiszolgálásával töltött processzoridő százalékos aránya (az Azure-ra nem vonatkozik, csak a virtuális gépeket futtató operációs rendszerekre).
* `%gnice`: A virtuális processzorok szép értékkel való kiszolgálásával töltött processzoridő százalékos aránya (az Azure-ra nem vonatkozik, csak a virtuális gépeket futtató operációs rendszerekre vonatkozik).
* `%idle`: Az inaktív processzoridő százalékos aránya, és az I/O-kérelmekre való várakozás nélkül.

#### Azokra a dolgokra, amelyeket érdemes figyelni

A következőhöz tartozó kimenet áttekintésekor figyelembe kell venni néhány részletet `mpstat`:

* Ellenőrizze, hogy az összes processzor megfelelően van-e betöltve, és hogy egyetlen processzor sem szolgálja-e ki az összes terhelést. Ez az információ egyetlen szálas alkalmazást jelezhet.
* Keresse meg a megfelelő egyensúlyt a között `%usr` , és `%sys` mivel az ellenkezője azt jelzi, több időt töltött a tényleges számítási feladat, mint a kiszolgáló kernel folyamatok.
* Keresse meg a `%iowait` százalékos értékeket, mert a magas értékek olyan rendszert jelezhetnek, amely folyamatosan vár az I/O-kérelmekre.
* A magas `%soft` használat nagy hálózati forgalmat jelezhet.

### `vmstat`

A `vmstat` segédprogram széles körben elérhető a legtöbb Linux-disztribúcióban, és magas szintű áttekintést nyújt a processzor, a memória és a lemez I/O-kihasználtságról egyetlen panelen.
A parancs a `vmstat` következő:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'vmstat -w 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

A beállítások és az argumentumok a következők:

* `-w`: Használjon széles nyomtatást a konzisztens oszlopok megtartásához.
* `1`: Az első numerikus argumentum azt jelzi, hogy milyen gyakran frissítse a kijelzőt másodpercek alatt.
* `5`: A második numerikus argumentum azt jelzi, hogy hányszor frissül az adat.

A kimenet:

```output
--procs-- -----------------------memory---------------------- ---swap-- -----io---- -system-- --------cpu--------
   r    b         swpd         free         buff        cache   si   so    bi    bo   in   cs  us  sy  id  wa  st
  14    0            0     26059408          164       137468    0    0    89  3228   56  122   3   1  95   1   0
  14    1            0     24388660          164       145468    0    0     0  7811 3264 13870  76  24   0   0   0
  18    1            0     23060116          164       155272    0    0    44  8075 3704 15129  78  22   0   0   0
  18    1            0     21078640          164       165108    0    0   295  8837 3742 15529  73  27   0   0   0
  15    2            0     19015276          164       175960    0    0     9  8561 3639 15177  73  27   0   0   0
```

`vmstat` a kimenetet hat csoportban osztja el:

* `procs`: folyamatok statisztikái.
* `memory`: a rendszermemória statisztikái.
* `swap`: a felcserélés statisztikái.
* `io`: a lemez io-jának statisztikái.
* `system`: a környezeti kapcsolók és megszakítások statisztikái.
* `cpu`: a processzorhasználat statisztikái.

>Megjegyzés: `vmstat` a teljes rendszer általános statisztikáit jeleníti meg (azaz az összes CPU-t, az összes blokkeszközt összesítve).

#### `procs`

A `procs` szakasz két oszlopból áll:

* `r`: A futtatható folyamatok száma a futtatási sorban.
* `b`: Az I/O-ra várakozó folyamatok száma.

Ez a szakasz azonnal megmutatja, hogy van-e szűk keresztmetszet a rendszeren. Az oszlopok egyikén magas számok jelzik az erőforrásokra várakozó folyamatokat.

Az `r` oszlop azoknak a folyamatoknak a számát jelzi, amelyek a processzoridő futtatására várnak. Ennek a számnak a értelmezéséhez a következő egyszerű módszer a következő: ha az üzenetsor folyamatainak `r` száma nagyobb, mint a teljes CPU-k száma, akkor arra lehet következtetni, hogy a rendszer nagy terheléssel rendelkezik, és nem tud processzoridőt lefoglalni a futtatásra váró összes folyamathoz.

Az `b` oszlop az I/O-kérések által blokkolt futtatásra váró folyamatok számát jelzi. Az oszlopban szereplő magas szám azt jelzi, hogy a rendszer magas I/O-t tapasztal, és a folyamatok nem futhatnak, mert más folyamatok várnak a befejezett I/O-kérelmekre. Ami nagy lemezkéséseket is jelezhet.

#### `memory`

A memóriaszakasz négy oszlopból áll:

* `swpd`: A felhasznált memória felcserélése.
* `free`: A memória szabad mennyisége.
* `buff`: A pufferekhez használt memória mennyisége.
* `cache`: A gyorsítótárhoz használt memória mennyisége.

> [!NOTE]
> Az értékek bájtban jelennek meg.

Ez a szakasz magas szintű áttekintést nyújt a memóriahasználatról.

#### `swap`

A felcserélés szakasz két oszlopból áll:

* `si`: A felcserélt memória mennyisége (a rendszermemória helyett a felcserélés) másodpercenként.
* `so`: A felcserélt memória mennyisége (a felcserélésről a rendszermemóriára áthelyezve) másodpercenként.

Ha magas `si` érték figyelhető meg, az olyan rendszert jelenthet, amely elfogy a rendszer memóriájában, és lapokat helyez át a felcserélésre (felcserélésre).

#### `io`

A `io` szakasz két oszlopból áll:

* `bi`: A blokkeszköztől kapott blokkok száma (a blokkok másodpercenkénti olvasása) másodpercenként.
* `bo`: A blokkeszközre küldött blokkok száma (írás másodpercenként) másodpercenként.

> [!NOTE]
> Ezek az értékek másodpercenként blokkokban vannak.

#### `system`

A `system` szakasz két oszlopból áll:

* `in`: A másodpercenkénti megszakítások száma.
* `cs`: A környezeti kapcsolók száma másodpercenként.

A másodpercenkénti nagy számú megszakítás olyan rendszert jelezhet, amely hardvereszközökkel van elfoglalva (például hálózati műveletek).

A környezeti kapcsolók nagy száma azt jelezheti, hogy egy foglalt rendszer sok rövid futó folyamattal rendelkezik, itt nincs jó vagy rossz szám.

#### `cpu`

Ez a szakasz öt oszlopból áll:

* `us`: Felhasználói terület százalékos kihasználtsága.
* `sy`: Rendszer (kerneltér) százalékos kihasználtsága.
* `id`: A processzor üresjárati idejének százalékos kihasználtsága.
* `wa`: A processzor által az I/O-val rendelkező folyamatokra várakozó inaktív idő százalékos kihasználtsága.
* `st`: A processzor által más virtuális PROCESSZORok kiszolgálásával töltött idő százalékos kihasználtsága (az Azure-ra nem alkalmazható).

Az értékek százalékos arányban jelennek meg. Ezek az értékek megegyeznek a `mpstat` segédprogram által bemutatott értékekkel, és magas szintű áttekintést nyújtanak a processzorhasználatról. Az értékek áttekintésekor kövesse az "[Átnézendő](#mpstat) dolgok" `mpstat` hasonló folyamatát.

### `uptime`

Végül a processzorral kapcsolatos metrikák esetében a `uptime` segédprogram átfogó áttekintést nyújt a rendszer terheléséről a terhelés átlagértékeivel.

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'uptime')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

```output
16:55:53 up 9 min,  2 users,  load average: 9.26, 2.91, 1.18
```

A terhelési átlag három számot jelenít meg. Ezek a számok a `1`rendszer terhelésének perc `5` - és `15` időintervallumai.

Ezeknek az értékeknek az értelmezéséhez fontos tudni, hogy hány processzor érhető el a rendszerben, amelyeket korábban a `mpstat` kimenetből szereztek be. Az érték a teljes CPU-tól függ, így a kimenet példájaként a `mpstat` rendszer 8 CPU-val rendelkezik, a 8-as terhelési átlag azt jelenti, hogy az ÖSSZES mag 100%-ra van betöltve.

Az érték `4` azt jelentené, hogy a processzorok fele 100%-os terheléssel lett betöltve (vagy az összes CPU-ra 50%-os terhelést jelent). Az előző kimenetben a terhelés átlaga `9.26`, ami azt jelenti, hogy a processzor betöltése körülbelül 115%.

A `1m`, `5m`intervallumok segítenek megállapítani, `15m` hogy a terhelés növekszik vagy csökken-e az idő során.

> [MEGJEGYZÉS] A `nproc` parancs a CPU-k számának lekérésére is használható.

## Memory (Memória)

A memóriához két parancs használható a használat részleteinek lekéréséhez.

### `free`

A `free` parancs megjeleníti a rendszermemória-kihasználtságot.

A futtatásához:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'free -h')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

A beállítások és az argumentumok a következők:

* `-h`: Értékeket jeleníthet meg dinamikusan olvashatóként (például: Mib, Gib, Tib)

A kimenet:

```output
               total        used        free      shared  buff/cache   available
Mem:            31Gi        19Gi        12Gi        23Mi        87Mi        11Gi
Swap:           23Gi          0B        23Gi
```

A kimenetben keresse meg a teljes rendszermemória és a rendelkezésre álló, valamint a használt és a teljes felcserélés közötti arányt. A rendelkezésre álló memória figyelembe veszi a gyorsítótár számára lefoglalt memóriát, amely a felhasználói alkalmazások számára visszaadható.

A modern kernelekben bizonyos felcserélési használat normális, mivel néhány ritkábban használt memórialap áthelyezhető a felcseréléshez.

### `swapon`

A `swapon` parancs megjeleníti a felcserélés konfigurálásának helyét és a felcserélési eszközök vagy fájlok megfelelő prioritásait.

A parancs futtatásához:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'swapon -s')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

A kimenet:

```output
Filename      Type          Size          Used   Priority
/dev/zram0    partition     16G           0B      100
/mnt/swapfile file          8G            0B      -2
```

Ez az információ fontos annak ellenőrzéséhez, hogy a felcserélés olyan helyen van-e konfigurálva, amely nem ideális, például egy adat- vagy operációsrendszer-lemezen. Az Azure referenciakeretében a felcserélést a rövid élettartamú meghajtón kell konfigurálni, mivel az a legjobb teljesítményt nyújtja.

### Azokra a dolgokra, amelyeket érdemes figyelni

* Ne feledje, hogy a memória véges erőforrás, ha a rendszermemória (RAM) és a felcserélés is kimerül, a folyamatokat az Out Of Memorry killer (OOM) öli meg.
* Ellenőrizze, hogy a felcserélés nincs-e konfigurálva adatlemezen vagy operációsrendszer-lemezen, mivel ez problémákat okozna az I/O-val a késési különbségek miatt. A felcserélést a rövid élettartamú meghajtón kell konfigurálni.
* Vegye figyelembe azt is, hogy a kimeneten gyakran látható, hogy az `free -h` ingyenes értékek közel állnak a nullához, ez a viselkedés a lapgyorsítótárnak köszönhető, a kernel szükség szerint felszabadítja ezeket a lapokat.

## I/O

A lemez I/O egyike azon területeknek, ahol az Azure szenved a legtöbbet szabályozás esetén, mivel a lemezek késéseket érhetnek el `100ms+` . Az alábbi parancsok segítenek azonosítani ezeket a forgatókönyveket.

### `iostat`

A `iostat` segédprogram a `sysstat` csomag része. Blokkalapú eszközhasználati statisztikákat jelenít meg, és segít azonosítani a blokkokkal kapcsolatos teljesítményproblémákat.

A `iostat` segédprogram olyan metrikák részleteit tartalmazza, mint az átviteli sebesség, a késés és az üzenetsor mérete. Ezek a metrikák segítenek megérteni, hogy a lemez I/O-jának korlátozásai tényezővé válnak-e.
A futtatáshoz használja a következő parancsot:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'iostat -dxtm 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

A beállítások és az argumentumok a következők:

* `-d`: Eszközhasználati jelentésenként.
* `-x`: Kiterjesztett statisztikák.
* `-t`: Az egyes jelentések időbélyegének megjelenítése.
* `-m`: Megjelenítés MB/s-ban.
* `1`: Az első numerikus argumentum azt jelzi, hogy milyen gyakran frissítse a kijelzőt másodpercek alatt.
* `2`: A második numerikus argumentum azt jelzi, hogy hányszor frissül az adat.

A kimenet:

```output
Linux 5.14.0-362.8.1.el9_3.x86_64 (alma9)       02/21/24        _x86_64_        (8 CPU)

02/21/24 16:55:50
Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
sda              1.07      0.02     0.00   0.00    1.95    20.40   23.25     24.55     3.30  12.42  113.75  1081.06    0.26    537.75     0.26  49.83    0.03 2083250.04    0.00    0.00    2.65   2.42
sdb             16.99      0.67     0.36   2.05    2.00    40.47   65.26      0.44     1.55   2.32    1.32     6.92    0.00      0.00     0.00   0.00    0.00     0.00   30.56    1.30    0.16   7.16
zram0            0.51      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.00   0.00

```

A kimenet több olyan oszlopot tartalmaz, amelyek nem fontosak (a `-x` beállítás miatt további oszlopok), a fontos oszlopok közül néhány a következők:

* `r/s`: Olvasási műveletek másodpercenként (IOPS).
* `rMB/s`: Másodpercenkénti megabájt olvasása.
* `r_await`: Olvasási késés ezredmásodpercben.
* `rareq-sz`: Az olvasási kérelem átlagos mérete kilobájtban.
* `w/s`: Írási műveletek másodpercenként (IOPS).
* `wMB/s`: Másodpercenként megabájt írása.
* `w_await`: Írási késés ezredmásodpercben.
* `wareq-size`: Az írási kérelem átlagos mérete kilobájtban.
* `aqu-sz`: Az üzenetsor átlagos mérete.

#### Azokra a dolgokra, amelyeket érdemes figyelni

* Keresse meg `r/s` és `w/s` (IOPS), `rMB/s` és `wMB/s` ellenőrizze, hogy ezek az értékek az adott lemez korlátain belül vannak-e. Ha az értékek közel vannak vagy magasabbak a korlátoknál, a lemez szabályozva lesz, ami nagy késéshez vezet. Ez az információ a metrika metrikájával `mpstat`is alátámasztható.`%iowait`
* A késés kiváló mérőszám annak ellenőrzésére, hogy a lemez a várt módon működik-e. Általában a PremiumSSD várt késésénél `9ms` kisebb, más ajánlatok eltérő késési célokkal rendelkeznek.
* Az üzenetsor mérete kiválóan jelzi a telítettséget. A kérések általában közel valós időben lesznek kézbesítve, és a szám az egyhez közeli marad (mivel az üzenetsor soha nem nő). A nagyobb szám a lemez telítettségét jelezheti (vagyis a kérelmek sorba állítását). Ehhez a metrikahoz nincs jó vagy rossz szám. Annak megértése, hogy az egynél magasabb érték azt jelenti, hogy a kérések sorban állnak, segít megállapítani, hogy van-e lemeztelítettség.

### `lsblk`

A `lsblk` segédprogram a rendszerhez csatlakoztatott blokkeszközöket jeleníti meg, bár nem biztosít teljesítménymetrikákat, gyors áttekintést tesz lehetővé az eszközök konfigurálásának és a használt csatlakoztatási pontoknak a gyors áttekintéséről.

A futtatáshoz használja a következő parancsot:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'lsblk')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

A kimenet:

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

#### Azokra a dolgokra, amelyeket érdemes figyelni

* Keresse meg az eszközök csatlakoztatásának helyét.
* Ellenőrizze, hogy nincs-e konfigurálva adatlemezen vagy operációsrendszer-lemezen belül, ha engedélyezve van.

> Megjegyzés: A blokkeszköz azure-beli lunhoz való összekapcsolásának egyszerű módja a futtatás `ls -lr /dev/disk/azure`.

## Feldolgozás

A részletek folyamatonkénti összegyűjtése segít megérteni, hogy honnan származik a rendszer terhelése.

A folyamatstatisztika gyűjtésének fő segédprogramja az `pidstat` , hogy folyamatonként részletezi a cpu-, memória- és I/O-statisztikákat.

Végül egy egyszerű `ps` rendezési folyamat a legfelső CPU szerint, és a memóriahasználat befejezi a metrikákat.

> [!NOTE]
> Mivel ezek a parancsok a futtatási folyamatok részleteit jelenítik meg, gyökérként kell futtatniuk őket.`sudo` Ez a parancs lehetővé teszi az összes folyamat megjelenítését, és nem csak a felhasználóé.

### `pidstat`

A `pidstat` segédprogram is része a `sysstat` csomagnak. Ez olyan, mint `mpstat` vagy iostat, ahol metrikákat jelenít meg egy adott ideig. Alapértelmezés szerint `pidstat` csak a tevékenységgel rendelkező folyamatok mérőszámait jeleníti meg.

A többi `sysstat` segédprogram argumentumai `pidstat` megegyeznek:

* 1: Az első numerikus argumentum azt jelzi, hogy milyen gyakran frissítse a kijelzőt másodpercek alatt.
* 2: A második numerikus argumentum azt jelzi, hogy az adatok hányszor frissülnek.

> [!NOTE]
> A kimenet jelentősen növekedhet, ha sok tevékenységgel rendelkező folyamat van.

#### Cpu-statisztikák feldolgozása

A folyamat CPU-statisztikáinak gyűjtéséhez futtassa `pidstat` a következő lehetőségek nélkül:

A következő parancsok használhatók, ha az Azure CLI-ből szeretné végrehajtani:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

A kimenet:

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

A parancs megjeleníti a folyamatonkénti használatot `%usr`a , `%system`, `%guest` (az Azure-ra nem alkalmazható) `%wait`és a teljes `%CPU` használatot.

##### Azokra a dolgokra, amelyeket érdemes figyelni

* Olyan folyamatokat keressen, amelyek %wait (iowait) százalékban vannak megadva, mivel az olyan folyamatokat jelezhet, amelyek blokkolva vannak az I/O-ra való várakozásra, ami a lemez telítettségét is jelezheti.
* Ellenőrizze, hogy egyetlen folyamat sem használja-e fel a processzor 100%-át, mivel az egyetlen szálas alkalmazást jelezhet.

#### Folyamatmemória-statisztikák

A folyamatmemória-statisztikák gyűjtéséhez használja a `-r` következő lehetőséget:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -r 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

A kimenet:

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

Az összegyűjtött metrikák a következők:

* `minflt/s`: Kisebb hibák másodpercenként, ez a metrika a rendszermemória (RAM) által betöltött lapok számát jelzi.
* `mjflt/s`: Nagyobb hibák másodpercenként, ez a metrika a lemezről betöltött lapok számát (SWAP) jelzi.
* `VSZ`: Bájtban használt virtuális memória.
* `RSS`: A használt rezidens memória (tényleges lefoglalt memória) bájtban.
* `%MEM`: A felhasznált memória százalékos aránya.
* `Command`: A folyamat neve.

##### Azokra a dolgokra, amelyeket érdemes figyelni

* Keresse meg a másodpercenkénti nagyobb hibákat, mivel ez az érték egy olyan folyamatot jelez, amely az oldalakat lemezre vagy lemezről cseréli le. Ez a viselkedés memóriakimerülést jelezhet, és a lassabb felcserélés miatt eseményekhez `OOM` vagy teljesítménycsökkenéshez vezethet.
* Ellenőrizze, hogy egyetlen folyamat nem használja-e fel a rendelkezésre álló memória 100%-át. Ez a viselkedés memóriavesztést jelezhet.

> [!NOTE]
> a `--human` beállítással a számok olvasható formátumban jeleníthetők meg (azaz `Kb`, `Mb`). `GB`

#### Folyamat I/O-statisztikái

A folyamatmemória-statisztikák gyűjtéséhez használja a `-d` következő lehetőséget:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -d 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

A kimenet:

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

Az összegyűjtött metrikák a következők:

* `kB_rd/s`: Másodpercenkénti kilobájt olvasása.
* `kB_wr/s`: Kilobájt/másodperc írása.
* `Command`: A folyamat neve.

##### Azokra a dolgokra, amelyeket érdemes figyelni

* Keresse meg a másodpercenként magas olvasási/írási sebességgel rendelkező önálló folyamatokat. Ezek az információk útmutatást nyújtanak az I/O-val rendelkező folyamatokhoz, mint a problémák azonosításához.
Megjegyzés: a `--human` beállítással a számok olvasható formátumban (azaz `Kb`, `Mb`, `GB`) jeleníthetők meg.

### `ps`

Végül `ps` a parancs megjeleníti a rendszerfolyamatokat, és cpu vagy memória szerint rendezhető.

A rendezés cpu szerint és a 10 legjobb folyamat beszerzése:

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

Az első 10 folyamat rendezése `MEM%` és beszerzése:

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

## Az összes összehozás

Egy egyszerű bash-szkript egyetlen futtatás során összegyűjti az összes részletet, és hozzáfűzi a kimenetet egy fájlhoz későbbi használatra:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2 && vmstat -w 1 5 && uptime && free -h && swapon && iostat -dxtm 1 1 && lsblk && ls -l /dev/disk/azure && pidstat 1 1 -h --human && pidstat -r 1 1 -h --human && pidstat -d 1 1 -h --human && ps aux --sort=-%cpu | head -20 && ps aux --sort=-%mem | head -20')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```

A futtatáshoz létrehozhat egy fájlt a fenti tartalommal, végrehajtási engedélyeket adhat hozzá a futtatáshoz `chmod +x gather.sh`, és futtathatja a következővel `sudo ./gather.sh`: .

Ez a szkript a parancsok kimenetét ugyanabban a könyvtárban található fájlba menti, ahol a szkriptet meghívták.

Ezenkívül a dokumentumban szereplő bash-blokkkódok összes parancsa futtatható `az-cli` a run-command bővítmény használatával, és elemezheti a kimenetet `jq` , hogy hasonló kimenetet kapjon a parancsok helyi futtatásához: '

```azurecli-interactive
output=$(az vm run-command invoke -g $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "ls -l /dev/disk/azure")
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```