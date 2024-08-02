---
title: Získání metrik výkonu ze systému Linux
description: 'Zjistěte, jak získat metriky výkonu ze systému Linux.'
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

# Získání metrik výkonu ze systému Linux

**Platí pro:** :heavy_check_mark: virtuální počítače s Linuxem

Tento článek se zabývá pokyny k určení, jak rychle získat metriky výkonu ze systému Linux.

K získání čítačů výkonu v Linuxu je možné použít několik příkazů. Příkazy jako `vmstat` a `uptime`poskytují obecné systémové metriky, jako je využití procesoru, systémová paměť a zatížení systému.
Většina příkazů je už ve výchozím nastavení nainstalovaná s tím, že ostatní jsou snadno dostupné ve výchozích úložištích.
Příkazy je možné rozdělit na:

* Procesor
* Memory (Paměť)
* Vstupně-výstupní operace disku
* Procesy

## Instalace nástrojů Sysstat

<!-- Commenting out these entries as this information should be selected by the user along with the corresponding subscription and region

The First step in this tutorial is to define environment variables, and install the corresponding package, if necessary.

```azurecli-interactive
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup89f292"
export MY_VM_NAME="myVM89f292"
```
-->

> [!NOTE]
> Některé z těchto příkazů je potřeba spustit, aby `root` bylo možné shromáždit všechny relevantní podrobnosti.

> [!NOTE]
> Některé příkazy jsou součástí `sysstat` balíčku, který nemusí být ve výchozím nastavení nainstalován. Balíček lze snadno nainstalovat s `sudo apt install sysstat`, `dnf install sysstat` nebo `zypper install sysstat` pro ty oblíbené distribuce.

Úplný příkaz pro instalaci `sysstat` balíčku na některé oblíbené distribuce je:

```bash
az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "/bin/bash -c 'OS=\$(cat /etc/os-release|grep NAME|head -1|cut -d= -f2 | sed \"s/\\\"//g\"); if [[ \$OS =~ \"Ubuntu\" ]] || [[ \$OS =~ \"Debian\" ]]; then sudo apt install sysstat -y; elif [[ \$OS =~ \"Red Hat\" ]]; then sudo dnf install sysstat -y; elif [[ \$OS =~ \"SUSE\" ]]; then sudo zypper install sysstat --non-interactive; else echo \"Unknown distribution\"; fi'"
```

## Procesor

### <a id="mpstat"></a>mpstat

Nástroj `mpstat` je součástí `sysstat` balíčku. Zobrazuje využití procesoru a průměry, což je užitečné k rychlé identifikaci využití procesoru. `mpstat` poskytuje přehled využití procesoru napříč dostupnými procesory, pomáhá identifikovat zůstatek využití a v případě velkého zatížení jednoho procesoru.

Úplný příkaz je:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Možnosti a argumenty jsou:

* `-P`: Označuje procesor k zobrazení statistiky, argument ALL označuje zobrazení statistiky pro všechny online procesory v systému.
* `1`: První číselný argument označuje, jak často se má zobrazení aktualizovat v sekundách.
* `2`: Druhý číselný argument označuje, kolikrát se data aktualizují.

`mpstat` Počet zobrazení dat příkazem lze změnit zvýšením druhého číselného argumentu tak, aby vyhovoval delším časům shromažďování dat. V ideálním případě by mělo stačit 3 nebo 5 sekund, pro systémy se zvýšenými počty jader 2 sekundy lze použít ke snížení množství zobrazených dat.
Z výstupu:

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

Je potřeba si uvědomit několik důležitých věcí. První řádek zobrazuje užitečné informace:

* Jádro a vydání: `5.14.0-362.8.1.el9_3.x86_64`
* Název hostitele: `alma9`
* Rande: `02/21/24`
* Architektura: `_x86_64_`
* Celkové množství procesorů (tyto informace jsou užitečné k interpretaci výstupu z jiných příkazů): `(8 CPU)`

Pak se zobrazí metriky procesorů, které vysvětlují jednotlivé sloupce:

* `Time`: Čas shromáždění vzorku
* `CPU`: Číselný identifikátor procesoru je identifikátor ALL průměrem pro všechny procesory.
* `%usr`: Procento využití procesoru pro uživatelský prostor, obvykle uživatelské aplikace.
* `%nice`: Procento využití procesoru pro procesy uživatelského prostoru s pěknou (prioritou) hodnotou.
* `%sys`: Procento využití procesoru pro procesy prostoru jádra.
* `%iowait`: Procento času stráveného nečinností stráveného čekáním na nevyužité vstupně-výstupní operace.
* `%irq`: Procento času stráveného obsluhou přerušení hardwaru.
* `%soft`: Procento času stráveného obsluhou softwarového přerušení.
* `%steal`: Procento času procesoru stráveného obsluhou jiných virtuálních počítačů (nevztahuje se na Azure kvůli žádnému nadměrnému zřízení procesoru).
* `%guest`: Procento času procesoru stráveného obsluhou virtuálních procesorů (nevztahuje se na Azure, platí pouze pro holé počítače, na kterých běží virtuální počítače).
* `%gnice`: Procento času procesoru stráveného obsluhou virtuálních procesorů s pěknou hodnotou (neplatí pro Azure, platí pouze pro holé počítače, na kterých běží virtuální počítače).
* `%idle`: Procento času procesoru strávilo nečinně a bez čekání na vstupně-výstupní požadavky.

#### Co je potřeba hledat

Při kontrole výstupu `mpstat`je potřeba mít na paměti některé podrobnosti:

* Ověřte, že jsou všechny procesory správně načtené, a ne jeden procesor obsluhuje veškeré zatížení. Tyto informace můžou indikovat jednu aplikaci s vlákny.
* Hledejte v pořádku rovnováhu mezi `%usr` jednotlivými procesy jádra a `%sys` jako naopak, což znamená více času stráveného na skutečné úloze než obsluha procesů jádra.
* `%iowait` Hledejte procenta, protože vysoké hodnoty můžou indikovat systém, který neustále čeká na vstupně-výstupní požadavky.
* Vysoké `%soft` využití může znamenat vysoký síťový provoz.

### `vmstat`

Nástroj `vmstat` je široce dostupný ve většině distribucí Linuxu, poskytuje základní přehled o využití procesoru, paměti a vstupně-výstupních operací disku v jednom podokně.
Příkaz pro `vmstat` :

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'vmstat -w 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Možnosti a argumenty jsou:

* `-w`: Používejte široký tisk k zachování konzistentních sloupců.
* `1`: První číselný argument označuje, jak často se má zobrazení aktualizovat v sekundách.
* `5`: Druhý číselný argument označuje, kolikrát se data aktualizují.

Výstup:

```output
--procs-- -----------------------memory---------------------- ---swap-- -----io---- -system-- --------cpu--------
   r    b         swpd         free         buff        cache   si   so    bi    bo   in   cs  us  sy  id  wa  st
  14    0            0     26059408          164       137468    0    0    89  3228   56  122   3   1  95   1   0
  14    1            0     24388660          164       145468    0    0     0  7811 3264 13870  76  24   0   0   0
  18    1            0     23060116          164       155272    0    0    44  8075 3704 15129  78  22   0   0   0
  18    1            0     21078640          164       165108    0    0   295  8837 3742 15529  73  27   0   0   0
  15    2            0     19015276          164       175960    0    0     9  8561 3639 15177  73  27   0   0   0
```

`vmstat` rozdělí výstup do šesti skupin:

* `procs`: statistiky pro procesy.
* `memory`: statistiky pro systémovou paměť.
* `swap`: statistika pro prohození.
* `io`: statistika pro vstupně-výstupní operace disku.
* `system`: statistika pro kontextové přepínače a přerušení.
* `cpu`: statistika využití procesoru.

>Poznámka: `vmstat` Zobrazuje celkové statistiky pro celý systém (to znamená všechny procesory, všechna bloková zařízení agregovaná).

#### `procs`

Oddíl `procs` má dva sloupce:

* `r`: Počet spuštěných procesů ve frontě spuštění.
* `b`: Počet procesů blokovaných čekání na vstupně-výstupní operace.

Tato část okamžitě ukazuje, jestli v systému nedochází k nějakým kritickým bodům. Vysoká čísla u některého ze sloupců označují procesy, které čekají na prostředky do fronty.

Sloupec `r` označuje počet procesů, které čekají na spuštění procesoru. Jednoduchý způsob, jak toto číslo interpretovat, je následující: pokud je počet procesů ve `r` frontě vyšší než celkový počet procesorů, je možné odvodit, že systém má procesor silně načtený a nemůže přidělit čas procesoru pro všechny procesy čekající na spuštění.

Sloupec `b` označuje počet procesů čekajících na spuštění, které jsou blokované vstupně-výstupními požadavky. Vysoké číslo v tomto sloupci označuje systém, u kterého dochází k vysokému počtu vstupně-výstupních operací a procesy se nedají spustit kvůli jiným procesům čekajících na dokončené vstupně-výstupní požadavky. To může také znamenat vysokou latenci disku.

#### `memory`

Oddíl paměti má čtyři sloupce:

* `swpd`: Využitá paměť pro prohození množství.
* `free`: Množství volné paměti.
* `buff`: Množství paměti používané pro vyrovnávací paměti.
* `cache`: Množství paměti použité pro mezipaměť.

> [!NOTE]
> Hodnoty se zobrazují v bajtech.

Tato část obsahuje základní přehled využití paměti.

#### `swap`

Oddíl prohození má dva sloupce:

* `si`: Množství paměti prohozené (přesunuto ze systémové paměti na prohození) za sekundu.
* `so`: Množství prohozené paměti (přesunuto z prohození do systémové paměti) za sekundu.

Pokud je pozorováno vysoké `si` , může představovat systém, který nemá systém paměti systému a přesouvá stránky na prohození (prohození).

#### `io`

Oddíl `io` má dva sloupce:

* `bi`: Počet bloků přijatých z blokového zařízení (bloky čtení za sekundu) za sekundu.
* `bo`: Počet bloků odeslaných do blokového zařízení (zápisy za sekundu) za sekundu.

> [!NOTE]
> Tyto hodnoty jsou v blocích za sekundu.

#### `system`

Oddíl `system` má dva sloupce:

* `in`: Počet přerušení za sekundu.
* `cs`: Počet přepínačů kontextu za sekundu.

Velký počet přerušení za sekundu může znamenat systém, který je zaneprázdněn hardwarovými zařízeními (například síťovými operacemi).

Velký počet kontextových přepínačů může znamenat zaneprázdněný systém s mnoha krátkými spuštěnými procesy, tady není žádné dobré nebo špatné číslo.

#### `cpu`

V této části je pět sloupců:

* `us`: Procento využití uživatelského prostoru
* `sy`: Procento využití systému (prostoru jádra)
* `id`: Procento využití doby nečinnosti procesoru
* `wa`: Procento využití doby, po kterou je procesor nečinný, čeká na procesy s vstupně-výstupními operacemi.
* `st`: Procento využití množství času stráveného procesorem obsluhou jiných virtuálních procesorů (neplatí pro Azure).

Hodnoty se zobrazují v procentech. Tyto hodnoty jsou stejné jako u `mpstat` nástroje a slouží k poskytování základního přehledu využití procesoru. Při kontrole těchto hodnot postupujte podle podobného postupu:[ "Věci, které je potřeba hledat](#mpstat)" `mpstat` .

### `uptime`

V případě metrik `uptime` souvisejících s procesorem poskytuje nástroj obecný přehled zatížení s průměrnými hodnotami zatížení.

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'uptime')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

```output
16:55:53 up 9 min,  2 users,  load average: 9.26, 2.91, 1.18
```

Průměr zatížení zobrazuje tři čísla. Tato čísla jsou určená pro `1``5` minutové `15` intervaly zatížení systému.

Aby bylo možné tyto hodnoty interpretovat, je důležité znát počet dostupných procesorů v systému získaný z výstupu `mpstat` dříve. Hodnota závisí na celkovém procesoru, takže jako příklad výstupu `mpstat` má systém 8 procesorů, průměr zatížení 8 by znamenal načtení všech jader na 100 %.

Hodnota `4` by znamenala, že polovina procesorů byla načtena na 100 % (nebo celkem 50% zatížení všech procesorů). V předchozím výstupu je `9.26`průměr zatížení , což znamená, že procesor se načte přibližně na 115 %.

Intervaly `1m`, `15m` `5m`pomáhají identifikovat, jestli se zatížení v průběhu času zvyšuje nebo snižuje.

> [POZNÁMKA] Příkaz `nproc` lze také použít k získání počtu procesorů.

## Memory (Paměť)

Pro paměť existují dva příkazy, které můžou získat podrobnosti o využití.

### `free`

Příkaz `free` zobrazuje využití systémové paměti.

Spustíte ho následujícím způsobem:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'free -h')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Možnosti a argumenty jsou:

* `-h`: Dynamické zobrazení hodnot jako čitelné člověkem (například: Mib, Gib, Tib)

Výstup:

```output
               total        used        free      shared  buff/cache   available
Mem:            31Gi        19Gi        12Gi        23Mi        87Mi        11Gi
Swap:           23Gi          0B        23Gi
```

Ve výstupu vyhledejte celkovou systémovou paměť vs. dostupnou a použitou a celkovou prohození. Dostupná paměť bere v úvahu paměť přidělenou pro mezipaměť, kterou je možné vrátit pro uživatelské aplikace.

Některé využití prohození je v moderních jádrech normální, protože některé méně často používané paměťové stránky je možné přesunout do prohození.

### `swapon`

Příkaz `swapon` zobrazí, kde se konfiguruje prohození, a odpovídající priority prohození zařízení nebo souborů.

Spuštění příkazu:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'swapon -s')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Výstup:

```output
Filename      Type          Size          Used   Priority
/dev/zram0    partition     16G           0B      100
/mnt/swapfile file          8G            0B      -2
```

Tyto informace jsou důležité k ověření, jestli je prohození nakonfigurované v umístění, které není ideální, například na datovém nebo operačním disku. V referenčním rámečku Azure by měl být prohození nakonfigurované na dočasné jednotce, protože poskytuje nejlepší výkon.

### Co je potřeba hledat

* Mějte na paměti, že paměť je konečný prostředek, jakmile dojde k vyčerpání systémové paměti (RAM) a prohození, procesy se mají zabít vrahem Out Of Memorry (OOM).
* Ověřte, že prohození není nakonfigurované na datovém disku nebo na disku s operačním systémem, protože by to způsobovalo problémy s vstupně-výstupními operacemi kvůli rozdílům latence. Prohození by mělo být nakonfigurované na dočasné jednotce.
* Mějte také na paměti, že je běžné vidět na výstupu `free -h` , že se volné hodnoty blíží nule, toto chování je způsobeno mezipamětí stránky, jádro tyto stránky uvolní podle potřeby.

## I/O

Vstupně-výstupní operace disku jsou jednou z oblastí, které Azure nejvíce trpí omezováním, protože disky můžou dosáhnout `100ms+` latencí. Následující příkazy vám pomůžou tyto scénáře identifikovat.

### `iostat`

Nástroj `iostat` je součástí `sysstat` balíčku. Zobrazuje statistiky využití jednotlivých blokových zařízení a pomáhá identifikovat problémy s výkonem související s blokem.

Nástroj `iostat` poskytuje podrobnosti o metrikách, jako je propustnost, latence a velikost fronty. Tyto metriky pomáhají pochopit, jestli se vstupně-výstupní operace disku stanou omezujícím faktorem.
Ke spuštění použijte příkaz:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'iostat -dxtm 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Možnosti a argumenty jsou:

* `-d`: Sestava využití jednotlivých zařízení.
* `-x`: Rozšířené statistiky.
* `-t`: Zobrazí časové razítko pro každou sestavu.
* `-m`: Zobrazení v MB/s.
* `1`: První číselný argument označuje, jak často se má zobrazení aktualizovat v sekundách.
* `2`: Druhý číselný argument označuje, kolikrát se data aktualizují.

Výstup:

```output
Linux 5.14.0-362.8.1.el9_3.x86_64 (alma9)       02/21/24        _x86_64_        (8 CPU)

02/21/24 16:55:50
Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
sda              1.07      0.02     0.00   0.00    1.95    20.40   23.25     24.55     3.30  12.42  113.75  1081.06    0.26    537.75     0.26  49.83    0.03 2083250.04    0.00    0.00    2.65   2.42
sdb             16.99      0.67     0.36   2.05    2.00    40.47   65.26      0.44     1.55   2.32    1.32     6.92    0.00      0.00     0.00   0.00    0.00     0.00   30.56    1.30    0.16   7.16
zram0            0.51      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.00   0.00

```

Výstup obsahuje několik sloupců, které nejsou důležité (kvůli možnosti navíc `-x` ), mezi nejdůležitější patří:

* `r/s`: Operace čtení za sekundu (IOPS).
* `rMB/s`: Čtení megabajtů za sekundu.
* `r_await`: Latence čtení v milisekundách
* `rareq-sz`: Průměrná velikost žádosti o čtení v kilobajtech.
* `w/s`: Operace zápisu za sekundu (IOPS).
* `wMB/s`: Zápis megabajtů za sekundu.
* `w_await`: Latence zápisu v milisekundách
* `wareq-size`: Průměrná velikost žádosti o zápis v kilobajtech.
* `aqu-sz`: Průměrná velikost fronty

#### Co je potřeba hledat

* `r/s` Vyhledejte a `w/s` (IOPS) a `rMB/s` `wMB/s` ověřte, že tyto hodnoty jsou v mezích daného disku. Pokud jsou hodnoty zavřené nebo vyšší, dojde k omezení disku, což vede k vysoké latenci. Tyto informace lze také korrobovat metrikou `%iowait` z `mpstat`.
* Latence je vynikající metrika pro ověření, jestli disk funguje podle očekávání. Za normálních okolností platí, že menší než `9ms` očekávaná latence pro PremiumSSD mají jiné nabídky různé cíle latence.
* Velikost fronty je skvělým indikátorem sytosti. Za normálních okolností by se žádosti obsloužily téměř v reálném čase a číslo zůstává blízko jedné (protože fronta nikdy nevyroste). Vyšší číslo může znamenat sytost disku (to znamená řazení požadavků do fronty). Pro tuto metriku neexistuje žádné dobré nebo špatné číslo. Když pochopíte, že cokoli vyššího než jedna znamená, že požadavky jsou ve frontě, pomáhají určit, jestli je disk sytý.

### `lsblk`

Nástroj `lsblk` zobrazuje bloková zařízení připojená k systému, zatímco neposkytuje metriky výkonu, umožňuje rychlý přehled konfigurace těchto zařízení a používaných přípojných bodů.

Ke spuštění použijte příkaz:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'lsblk')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Výstup:

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

#### Co je potřeba hledat

* Vyhledejte, kde jsou zařízení připojená.
* Ověřte, že prohození není nakonfigurované uvnitř datového disku nebo disku s operačním systémem, pokud je povoleno.

> Poznámka: Snadný způsob, jak korelovat blokové zařízení s logickou jednotkou v Azure, je spuštěním `ls -lr /dev/disk/azure`příkazu .

## Zpracovat

Shromažďování podrobností o jednotlivých procesech pomáhá pochopit, odkud pochází zatížení systému.

Hlavním nástrojem pro shromažďování statických procesů je `pidstat` , jak poskytuje podrobnosti o procesu pro statistiky procesoru, paměti a vstupně-výstupních operací.

Nakonec se metriky dokončí jednoduchým `ps` řazením podle nejvyššího využití procesoru a využití paměti.

> [!NOTE]
> Vzhledem k tomu, že tyto příkazy zobrazují podrobnosti o spuštěných procesech, musí běžet jako kořen s `sudo`. Tento příkaz umožňuje zobrazit všechny procesy, nejen uživatele.

### `pidstat`

Nástroj `pidstat` je také součástí `sysstat` balíčku. Je to podobné `mpstat` nebo iostat, kde zobrazuje metriky po danou dobu. Ve výchozím nastavení `pidstat` zobrazuje metriky pouze pro procesy s aktivitou.

Argumenty pro `pidstat` jiné nástroje jsou stejné `sysstat` :

* 1: První číselný argument označuje, jak často se má zobrazení aktualizovat v sekundách.
* 2: Druhý číselný argument označuje, kolikrát se data aktualizují.

> [!NOTE]
> Výstup se může výrazně zvětšit, pokud existuje mnoho procesů s aktivitou.

#### Statistika zpracování procesoru

Pokud chcete shromáždit statistiky procesoru procesu, spusťte `pidstat` bez jakýchkoliv možností:

Pokud ho chcete spustit z Azure CLI, můžete použít následující příkazy:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Výstup:

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

Příkaz zobrazí využití jednotlivých procesů pro `%usr`, , `%system``%guest` (nevztahuje se na Azure) `%wait`a celkové `%CPU` využití.

##### Co je potřeba hledat

* Hledejte procesy s vysokým procentem čekání (iowait), protože to může znamenat, že procesy blokované čekají na vstupně-výstupní operace, což může také znamenat sytost disku.
* Ověřte, že žádný proces nevyužívají 100 % procesoru, protože může indikovat jednu aplikaci s vlákny.

#### Statistika paměti procesu

Pokud chcete shromáždit statistiku paměti procesu, použijte tuto `-r` možnost:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -r 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Výstup:

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

Shromažďované metriky:

* `minflt/s`: Menší chyby za sekundu, tato metrika označuje počet stránek načtených ze systémové paměti (RAM).
* `mjflt/s`: Hlavní chyby za sekundu, tato metrika označuje počet stránek načtených z disku (SWAP).
* `VSZ`: Virtuální paměť používaná v bajtech.
* `RSS`: Využitá rezidentní paměť (skutečná přidělená paměť) v bajtech.
* `%MEM`: Procento využité celkové paměti.
* `Command`: Název procesu.

##### Co je potřeba hledat

* Hledejte hlavní chyby za sekundu, protože tato hodnota označuje proces prohození stránek na disk nebo z disku. Toto chování může značit vyčerpání paměti a mohlo by vést k `OOM` událostem nebo snížení výkonu kvůli pomalejšímu prohození.
* Ověřte, že jeden proces nevyužívají 100 % dostupné paměti. Toto chování může značit nevracení paměti.

> [!NOTE]
> `--human` možnost lze použít k zobrazení čísel v čitelném formátu člověka (to znamená , `Kb`, `Mb`, `GB`).

#### Statistika vstupně-výstupních operací procesu

Pokud chcete shromáždit statistiku paměti procesu, použijte tuto `-d` možnost:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -d 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Výstup:

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

Shromažďované metriky:

* `kB_rd/s`: Čtení kilobajtů za sekundu
* `kB_wr/s`: Zápis kilobajtů za sekundu
* `Command`: Název procesu.

##### Co je potřeba hledat

* Hledejte jednotlivé procesy s vysokou rychlostí čtení a zápisu za sekundu. Tyto informace jsou pokyny pro procesy s více vstupně-výstupními operacemi, než je identifikace problémů.
Poznámka: `--human` Možnost lze použít k zobrazení čísel v čitelném formátu člověka (to znamená , `Kb`, `Mb`, `GB`).

### `ps`

`ps` Poslední příkaz zobrazí systémové procesy a může být seřazený podle procesoru nebo paměti.

Řazení podle procesoru a získání prvních 10 procesů:

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

Seřazení `MEM%` a získání prvních 10 procesů:

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

## Seskupování všech

Jednoduchý skript Bash může shromáždit všechny podrobnosti v jednom spuštění a připojit výstup k souboru pro pozdější použití:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2 && vmstat -w 1 5 && uptime && free -h && swapon && iostat -dxtm 1 1 && lsblk && ls -l /dev/disk/azure && pidstat 1 1 -h --human && pidstat -r 1 1 -h --human && pidstat -d 1 1 -h --human && ps aux --sort=-%cpu | head -20 && ps aux --sort=-%mem | head -20')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```

Ke spuštění můžete vytvořit soubor s výše uvedeným obsahem, přidat oprávnění ke spuštění spuštěním `chmod +x gather.sh`a spuštěním .`sudo ./gather.sh`

Tento skript uloží výstup příkazů do souboru umístěného ve stejném adresáři, ve kterém byl skript vyvolán.

Kromě toho lze všechny příkazy v kódech bloků Bash popsané v tomto dokumentu spustit pomocí `az-cli` rozšíření příkazu run a parsováním výstupu `jq` získat podobný výstup pro místní spuštění příkazů:

```azurecli-interactive
output=$(az vm run-command invoke -g $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "ls -l /dev/disk/azure")
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```