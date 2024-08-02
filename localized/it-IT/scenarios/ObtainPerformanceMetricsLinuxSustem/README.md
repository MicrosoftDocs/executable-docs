---
title: Recupero delle metriche delle prestazioni da un sistema Linux
description: Informazioni su come ottenere le metriche delle prestazioni da un sistema Linux.
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

# Recupero delle metriche delle prestazioni da un sistema Linux

**Si applica a:** :heavy_check_mark: macchine virtuali Linux

Questo articolo illustra le istruzioni per determinare come ottenere rapidamente le metriche delle prestazioni da un sistema Linux.

Esistono diversi comandi che possono essere usati per ottenere i contatori delle prestazioni in Linux. I comandi, `vmstat` ad esempio e `uptime`, forniscono metriche di sistema generali, ad esempio l'utilizzo della CPU, la memoria di sistema e il carico di sistema.
La maggior parte dei comandi è già installata per impostazione predefinita con altri utenti disponibili nei repository predefiniti.
I comandi possono essere separati in:

* CPU
* Memoria
* I/O su disco
* Processi

## Installazione delle utilità Sysstat

<!-- Commenting out these entries as this information should be selected by the user along with the corresponding subscription and region

The First step in this tutorial is to define environment variables, and install the corresponding package, if necessary.

```azurecli-interactive
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup89f292"
export MY_VM_NAME="myVM89f292"
```
-->

> [!NOTE]
> Alcuni di questi comandi devono essere eseguiti per `root` poter raccogliere tutti i dettagli pertinenti.

> [!NOTE]
> Alcuni comandi fanno parte del `sysstat` pacchetto che potrebbe non essere installato per impostazione predefinita. Il pacchetto può essere facilmente installato con `sudo apt install sysstat`o `dnf install sysstat` `zypper install sysstat` per le distribuzioni più diffuse.

Il comando completo per l'installazione del `sysstat` pacchetto in alcune distribuzioni comuni è:

```bash
az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "/bin/bash -c 'OS=\$(cat /etc/os-release|grep NAME|head -1|cut -d= -f2 | sed \"s/\\\"//g\"); if [[ \$OS =~ \"Ubuntu\" ]] || [[ \$OS =~ \"Debian\" ]]; then sudo apt install sysstat -y; elif [[ \$OS =~ \"Red Hat\" ]]; then sudo dnf install sysstat -y; elif [[ \$OS =~ \"SUSE\" ]]; then sudo zypper install sysstat --non-interactive; else echo \"Unknown distribution\"; fi'"
```

## CPU

### <a id="mpstat"></a>mpstat

L'utilità `mpstat` fa parte del `sysstat` pacchetto. Visualizza in base all'utilizzo della CPU e alle medie, che è utile per identificare rapidamente l'utilizzo della CPU. `mpstat` offre una panoramica dell'utilizzo della CPU tra le CPU disponibili, consentendo di identificare il bilanciamento dell'utilizzo e se una singola CPU viene caricata pesantemente.

Il comando completo è:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Le opzioni e gli argomenti sono:

* `-P`: indica il processore per visualizzare le statistiche, l'argomento ALL indica di visualizzare le statistiche per tutte le CPU online nel sistema.
* `1`: il primo argomento numerico indica la frequenza con cui aggiornare la visualizzazione in secondi.
* `2`: il secondo argomento numerico indica quante volte vengono aggiornati i dati.

Il numero di volte in cui il `mpstat` comando visualizza i dati può essere modificato aumentando il secondo argomento numerico in modo da supportare per tempi di raccolta dati più lunghi. Idealmente, 3 o 5 secondi dovrebbero essere sufficienti, per i sistemi con un numero maggiore di core 2 secondi può essere usato per ridurre la quantità di dati visualizzati.
Dall'output:

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

Ci sono un paio di cose importanti da notare. La prima riga visualizza informazioni utili:

* Kernel e versione: `5.14.0-362.8.1.el9_3.x86_64`
* Nome host: `alma9`
* Dattero: `02/21/24`
* Architettura: `_x86_64_`
* Quantità totale di CPU (queste informazioni sono utili per interpretare l'output da altri comandi): `(8 CPU)`

Vengono quindi visualizzate le metriche per le CPU, per spiegare ognuna delle colonne:

* `Time`: ora in cui è stato raccolto l'esempio
* `CPU`: identificatore numerico cpu, l'identificatore ALL è una media per tutte le CPU.
* `%usr`: percentuale di utilizzo della CPU per lo spazio utente, in genere applicazioni utente.
* `%nice`: percentuale di utilizzo della CPU per i processi dello spazio utente con un valore bello (priorità).
* `%sys`: percentuale di utilizzo della CPU per i processi dello spazio del kernel.
* `%iowait`: percentuale di tempo di inattività della CPU in attesa di operazioni di I/O in sospeso.
* `%irq`: percentuale di tempo della CPU impiegato per gestire gli interrupt hardware.
* `%soft`: percentuale di tempo della CPU impiegato per gestire gli interrupt software.
* `%steal`: percentuale di tempo di CPU impiegato per la gestione di altre macchine virtuali (non applicabile ad Azure a causa di nessun overprovisioning della CPU).
* `%guest`: percentuale di tempo della CPU impiegato per la gestione delle CPU virtuali (non applicabile ad Azure, applicabile solo ai sistemi bare metal che eseguono macchine virtuali).
* `%gnice`: percentuale di tempo della CPU impiegato per la gestione delle CPU virtuali con un valore interessante (non applicabile ad Azure, applicabile solo ai sistemi bare metal che eseguono macchine virtuali).
* `%idle`: percentuale di tempo di inattività della CPU e senza attendere le richieste di I/O.

#### Cose da cercare

Alcuni dettagli da tenere presenti quando si esamina l'output per `mpstat`:

* Verificare che tutte le CPU siano caricate correttamente e che non una singola CPU gestisca tutto il carico. Queste informazioni potrebbero indicare un'applicazione a thread singolo.
* Cercare un equilibrio integro tra `%usr` e `%sys` come l'opposto indica più tempo dedicato al carico di lavoro effettivo rispetto alla gestione dei processi del kernel.
* `%iowait` Cercare percentuali come valori elevati potrebbe indicare un sistema in attesa costante delle richieste di I/O.
* Un utilizzo elevato `%soft` potrebbe indicare un traffico di rete elevato.

### `vmstat`

L'utilità `vmstat` è ampiamente disponibile nella maggior parte delle distribuzioni Linux, offre una panoramica di alto livello per l'utilizzo di CPU, memoria e I/O su disco in un singolo riquadro.
Il comando per `vmstat` è:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'vmstat -w 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Le opzioni e gli argomenti sono:

* `-w`: utilizzare la stampa estesa per mantenere le colonne coerenti.
* `1`: il primo argomento numerico indica la frequenza con cui aggiornare la visualizzazione in secondi.
* `5`: il secondo argomento numerico indica quante volte vengono aggiornati i dati.

L'output è:

```output
--procs-- -----------------------memory---------------------- ---swap-- -----io---- -system-- --------cpu--------
   r    b         swpd         free         buff        cache   si   so    bi    bo   in   cs  us  sy  id  wa  st
  14    0            0     26059408          164       137468    0    0    89  3228   56  122   3   1  95   1   0
  14    1            0     24388660          164       145468    0    0     0  7811 3264 13870  76  24   0   0   0
  18    1            0     23060116          164       155272    0    0    44  8075 3704 15129  78  22   0   0   0
  18    1            0     21078640          164       165108    0    0   295  8837 3742 15529  73  27   0   0   0
  15    2            0     19015276          164       175960    0    0     9  8561 3639 15177  73  27   0   0   0
```

`vmstat` suddivide l'output in sei gruppi:

* `procs`: statistiche per i processi.
* `memory`: statistiche per la memoria di sistema.
* `swap`: statistiche per lo scambio.
* `io`: statistiche per io del disco.
* `system`: statistiche per cambi di contesto e interrupt.
* `cpu`: statistiche per l'utilizzo della CPU.

>Nota: `vmstat` mostra le statistiche complessive per l'intero sistema, ovvero tutte le CPU, tutti i dispositivi in blocchi aggregati.

#### `procs`

La `procs` sezione include due colonne:

* `r`: numero di processi eseguibili nella coda di esecuzione.
* `b`: numero di processi bloccati in attesa di I/O.

Questa sezione mostra immediatamente se è presente un collo di bottiglia nel sistema. Numeri elevati in una delle colonne indicano processi in attesa di risorse.

La `r` colonna indica il numero di processi in attesa dell'esecuzione del tempo cpu. Un modo semplice per interpretare questo numero è il seguente: se il numero di processi nella `r` coda è superiore al numero di CPU totali, può essere dedotto che il sistema ha la CPU pesantemente caricata e non può allocare tempo CPU per tutti i processi in attesa di esecuzione.

La `b` colonna indica il numero di processi in attesa di esecuzione bloccati dalle richieste di I/O. Un numero elevato in questa colonna indica un sistema che riscontra un numero elevato di operazioni di I/O e i processi non possono essere eseguiti a causa di altri processi in attesa di richieste di I/O completate. Che potrebbe anche indicare una latenza elevata del disco.

#### `memory`

La sezione memory include quattro colonne:

* `swpd`: quantità di memoria di scambio utilizzata.
* `free`: quantità di memoria libera.
* `buff`: quantità di memoria usata per i buffer.
* `cache`: quantità di memoria usata per la cache.

> [!NOTE]
> I valori vengono visualizzati in byte.

Questa sezione offre una panoramica generale dell'utilizzo della memoria.

#### `swap`

La sezione swap include due colonne:

* `si`: quantità di memoria scambiata in (spostata dalla memoria di sistema allo scambio) al secondo.
* `so`: quantità di memoria scambiata (spostata dallo scambio alla memoria di sistema) al secondo.

Se si osserva un valore elevato `si` , potrebbe rappresentare un sistema che esaurisce la memoria di sistema e sposta le pagine in scambio (scambio).

#### `io`

La `io` sezione include due colonne:

* `bi`: numero di blocchi ricevuti da un dispositivo a blocchi (legge blocchi al secondo) al secondo.
* `bo`: numero di blocchi inviati a un dispositivo a blocchi (scritture al secondo) al secondo.

> [!NOTE]
> Questi valori sono in blocchi al secondo.

#### `system`

La `system` sezione include due colonne:

* `in`: numero di interrupt al secondo.
* `cs`: numero di cambi di contesto al secondo.

Un numero elevato di interrupt al secondo potrebbe indicare un sistema occupato con dispositivi hardware (ad esempio le operazioni di rete).

Un numero elevato di commutatori di contesto potrebbe indicare un sistema occupato con molti processi a esecuzione breve, non esiste un numero valido o negativo qui.

#### `cpu`

Questa sezione include cinque colonne:

* `us`: percentuale di utilizzo dello spazio utente.
* `sy`: percentuale di utilizzo della percentuale di sistema (spazio kernel).
* `id`: percentuale di utilizzo della quantità di tempo in cui la CPU è inattiva.
* `wa`: percentuale di utilizzo della quantità di tempo in cui la CPU è inattiva in attesa di processi con I/O.
* `st`: percentuale di utilizzo della quantità di tempo impiegato dalla CPU per la gestione di altre CPU virtuali (non applicabile ad Azure).

I valori vengono presentati in percentuale. Questi valori sono gli stessi presentati dall'utilità e forniscono una panoramica generale dell'utilizzo `mpstat` della CPU. Seguire un processo simile per "[Elementi da cercare](#mpstat)" per `mpstat` quando si esaminano questi valori.

### `uptime`

Infine, per le metriche correlate alla CPU, l'utilità `uptime` offre una panoramica generale del carico di sistema con i valori medi di carico.

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'uptime')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

```output
16:55:53 up 9 min,  2 users,  load average: 9.26, 2.91, 1.18
```

La media del carico visualizza tre numeri. Questi numeri sono relativi a `1``5` intervalli di minuti e `15` di caricamento del sistema.

Per interpretare questi valori, è importante conoscere il numero di CPU disponibili nel sistema, ottenute dall'output `mpstat` prima. Il valore dipende dalle CPU totali, quindi come esempio di `mpstat` output il sistema ha 8 CPU, una media di carico pari a 8 significa che tutti i core vengono caricati in un 100%.

Un valore indica `4` che la metà delle CPU è stata caricata al 100% (o un totale del 50% di carico su TUTTE le CPU). Nell'output precedente, la media del carico è `9.26`, il che significa che la CPU viene caricata a circa il 115%.

Gli `1m`intervalli , `5m`consentono `15m` di identificare se il carico aumenta o diminuisce nel tempo.

> [NOTA] Il `nproc` comando può essere usato anche per ottenere il numero di CPU.

## Memoria

Per la memoria, sono disponibili due comandi che possono ottenere informazioni dettagliate sull'utilizzo.

### `free`

Il `free` comando mostra l'utilizzo della memoria di sistema.

Per eseguirlo:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'free -h')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Le opzioni e gli argomenti sono:

* `-h`: visualizza i valori in modo dinamico come leggibile dall'utente (ad esempio: Mib, Gib, Tib)

L'output è:

```output
               total        used        free      shared  buff/cache   available
Mem:            31Gi        19Gi        12Gi        23Mi        87Mi        11Gi
Swap:           23Gi          0B        23Gi
```

Dall'output cercare la memoria totale di sistema rispetto a quella disponibile e lo scambio usato rispetto al totale. La memoria disponibile prende in considerazione la memoria allocata per la cache, che può essere restituita per le applicazioni utente.

Alcuni utilizzi di scambio sono normali nei kernel moderni perché alcune pagine di memoria usate meno spesso possono essere spostate per lo scambio.

### `swapon`

Il `swapon` comando visualizza dove viene configurato lo scambio e le rispettive priorità dei dispositivi o dei file di scambio.

Per eseguire il comando:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'swapon -s')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

L'output è:

```output
Filename      Type          Size          Used   Priority
/dev/zram0    partition     16G           0B      100
/mnt/swapfile file          8G            0B      -2
```

Queste informazioni sono importanti per verificare se lo scambio è configurato in una posizione che non è ideale, ad esempio in un disco dati o del sistema operativo. Nel frame di riferimento di Azure, lo scambio deve essere configurato nell'unità temporanea perché offre prestazioni ottimali.

### Cose da cercare

* Tenere presente che la memoria è una risorsa finita, una volta esaurita la memoria di sistema (RAM) e lo scambio, i processi devono essere uccisi dal killer Out Of Memorry (OOM).
* Verificare che lo scambio non sia configurato in un disco dati o nel disco del sistema operativo, perché ciò potrebbe creare problemi di I/O a causa di differenze di latenza. Lo scambio deve essere configurato nell'unità temporanea.
* Tenere anche in considerazione che è comune vedere nell'output `free -h` che i valori liberi sono vicini a zero, questo comportamento è dovuto alla cache delle pagine, il kernel rilascia tali pagine in base alle esigenze.

## I/O

L'I/O del disco è una delle aree più colpite da Azure, perché i dischi possono raggiungere `100ms+` latenze. I comandi seguenti consentono di identificare questi scenari.

### `iostat`

L'utilità `iostat` fa parte del `sysstat` pacchetto. Visualizza le statistiche di utilizzo dei dispositivi per blocco e consente di identificare i problemi di prestazioni correlati al blocco.

L'utilità `iostat` fornisce informazioni dettagliate sulle metriche, ad esempio velocità effettiva, latenza e dimensioni della coda. Queste metriche consentono di comprendere se l'I/O del disco diventa un fattore di limitazione.
Per eseguire, usare il comando :

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'iostat -dxtm 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Le opzioni e gli argomenti sono:

* `-d`: report sull'utilizzo per dispositivo.
* `-x`: statistiche estese.
* `-t`: visualizza il timestamp per ogni report.
* `-m`: visualizzato in MB/s.
* `1`: il primo argomento numerico indica la frequenza con cui aggiornare la visualizzazione in secondi.
* `2`: il secondo argomento numerico indica quante volte vengono aggiornati i dati.

L'output è:

```output
Linux 5.14.0-362.8.1.el9_3.x86_64 (alma9)       02/21/24        _x86_64_        (8 CPU)

02/21/24 16:55:50
Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
sda              1.07      0.02     0.00   0.00    1.95    20.40   23.25     24.55     3.30  12.42  113.75  1081.06    0.26    537.75     0.26  49.83    0.03 2083250.04    0.00    0.00    2.65   2.42
sdb             16.99      0.67     0.36   2.05    2.00    40.47   65.26      0.44     1.55   2.32    1.32     6.92    0.00      0.00     0.00   0.00    0.00     0.00   30.56    1.30    0.16   7.16
zram0            0.51      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.00   0.00

```

L'output include diverse colonne che non sono importanti (colonne aggiuntive a causa dell'opzione `-x` ), alcune delle più importanti sono:

* `r/s`: operazioni di lettura al secondo (IOPS).
* `rMB/s`: lettura di megabyte al secondo.
* `r_await`: latenza di lettura in millisecondi.
* `rareq-sz`: dimensione media delle richieste di lettura in kilobyte.
* `w/s`: operazioni di scrittura al secondo (IOPS).
* `wMB/s`: scrittura di megabyte al secondo.
* `w_await`: latenza di scrittura in millisecondi.
* `wareq-size`: dimensione media della richiesta di scrittura in kilobyte.
* `aqu-sz`: dimensioni medie della coda.

#### Cose da cercare

* `r/s` Cercare e `w/s` (IOPS) e `rMB/s` e `wMB/s` verificare che questi valori siano entro i limiti del disco specificato. Se i valori sono vicini o superiori ai limiti, il disco verrà limitato, causando una latenza elevata. Queste informazioni possono anche essere corroborate con la `%iowait` metrica di `mpstat`.
* La latenza è una metrica eccellente per verificare se il disco funziona come previsto. In genere, minore di `9ms` è la latenza prevista per PremiumSSD, altre offerte hanno destinazioni di latenza diverse.
* Le dimensioni della coda sono un ottimo indicatore di saturazione. In genere, le richieste verrebbero servite quasi in tempo reale e il numero rimane vicino a uno (man mano che la coda non cresce mai). Un numero più elevato potrebbe indicare la saturazione del disco( ovvero le richieste di accodamento). Non esiste un numero valido o negativo per questa metrica. Comprendere che qualsiasi valore superiore a uno significa che le richieste stanno accodando aiuta a determinare se è presente una saturazione del disco.

### `lsblk`

L'utilità `lsblk` mostra i dispositivi in blocchi collegati al sistema, mentre non fornisce metriche delle prestazioni, consente una rapida panoramica del modo in cui questi dispositivi sono configurati e quali punti di montaggio vengono usati.

Per eseguire, usare il comando :

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'lsblk')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

L'output è:

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

#### Cose da cercare

* Cercare dove vengono montati i dispositivi.
* Verificare che lo scambio non sia configurato all'interno di un disco dati o di un disco del sistema operativo, se abilitato.

> Nota: un modo semplice per correlare il dispositivo di blocco a un LUN in Azure consiste nell'eseguire `ls -lr /dev/disk/azure`.

## Processo

La raccolta di dettagli su base di processo consente di comprendere da dove proviene il carico del sistema.

L'utilità principale per raccogliere i dati statici dei processi è `pidstat` che fornisce i dettagli per ogni processo per le statistiche di CPU, memoria e I/O.

Infine, un processo semplice `ps` da ordinare in base alla CPU superiore e l'utilizzo della memoria completa le metriche.

> [!NOTE]
> Poiché questi comandi visualizzano dettagli sui processi in esecuzione, è necessario eseguirli come radice con `sudo`. Questo comando consente la visualizzazione di tutti i processi e non solo dell'utente.

### `pidstat`

L'utilità `pidstat` fa anche parte del `sysstat` pacchetto. È come `mpstat` o iostat in cui vengono visualizzate le metriche per un determinato periodo di tempo. Per impostazione predefinita, `pidstat` visualizza solo le metriche per i processi con attività.

Gli argomenti per `pidstat` sono gli stessi per altre `sysstat` utilità:

* 1: Il primo argomento numerico indica la frequenza con cui aggiornare la visualizzazione in secondi.
* 2: Il secondo argomento numerico indica quante volte vengono aggiornati i dati.

> [!NOTE]
> L'output può aumentare notevolmente se sono presenti molti processi con attività.

#### Elaborare le statistiche della CPU

Per raccogliere le statistiche della CPU del processo, eseguire `pidstat` senza opzioni:

I comandi seguenti possono essere usati se si vuole eseguirlo dall'interfaccia della riga di comando di Azure:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

L'output è:

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

Il comando visualizza l'utilizzo per processo per `%usr`, `%system`, `%guest` (non applicabile ad Azure), `%wait`e l'utilizzo totale `%CPU` .

##### Cose da cercare

* Cercare processi con percentuale di attesa elevata (iowait) perché potrebbe indicare processi bloccati in attesa di I/O, che potrebbero anche indicare la saturazione del disco.
* Verificare che nessun singolo processo consuma il 100% della CPU perché potrebbe indicare un'applicazione a thread singolo.

#### Statistiche sulla memoria del processo

Per raccogliere statistiche di memoria del processo, usare l'opzione `-r` :

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -r 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

L'output è:

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

Le metriche raccolte sono:

* `minflt/s`: errori secondari al secondo, questa metrica indica il numero di pagine caricate dalla memoria di sistema (RAM).
* `mjflt/s`: errori principali al secondo, questa metrica indica il numero di pagine caricate dal disco (SWAP).
* `VSZ`: memoria virtuale usata in byte.
* `RSS`: memoria residente usata (memoria allocata effettiva) in byte.
* `%MEM`: percentuale di memoria totale usata.
* `Command`: nome del processo.

##### Cose da cercare

* Cercare errori principali al secondo, in quanto questo valore indica un processo che scambia le pagine da o verso il disco. Questo comportamento potrebbe indicare l'esaurimento della memoria e potrebbe causare `OOM` eventi o riduzione delle prestazioni a causa di uno scambio più lento.
* Verificare che un singolo processo non consumi il 100% della memoria disponibile. Questo comportamento potrebbe indicare una perdita di memoria.

> [!NOTE]
> L'opzione `--human` può essere usata per visualizzare i numeri in formato leggibile, ovvero , `Mb``Kb`, `GB`.

#### Elaborare le statistiche di I/O

Per raccogliere statistiche di memoria del processo, usare l'opzione `-d` :

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -d 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

L'output è:

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

Le metriche raccolte sono:

* `kB_rd/s`: lettura kilobyte al secondo.
* `kB_wr/s`: kilobyte di scrittura al secondo.
* `Command`: nome del processo.

##### Cose da cercare

* Cercare singoli processi con velocità di lettura/scrittura elevate al secondo. Queste informazioni sono indicazioni per i processi con operazioni di I/O superiori all'identificazione dei problemi.
Nota: l'opzione `--human` può essere usata per visualizzare i numeri in formato leggibile ( ovvero , `Mb``Kb`, `GB`).

### `ps`

`ps` Infine, il comando visualizza i processi di sistema e può essere ordinato in base alla CPU o alla memoria.

Per ordinare in base alla CPU e ottenere i primi 10 processi:

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

Per ordinare `MEM%` e ottenere i primi 10 processi:

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

## Mettere tutti insieme

Uno script bash semplice può raccogliere tutti i dettagli in una singola esecuzione e accodare l'output a un file per usarli in un secondo momento:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2 && vmstat -w 1 5 && uptime && free -h && swapon && iostat -dxtm 1 1 && lsblk && ls -l /dev/disk/azure && pidstat 1 1 -h --human && pidstat -r 1 1 -h --human && pidstat -d 1 1 -h --human && ps aux --sort=-%cpu | head -20 && ps aux --sort=-%mem | head -20')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```

Per eseguire, è possibile creare un file con il contenuto precedente, aggiungere le autorizzazioni di esecuzione eseguendo `chmod +x gather.sh`ed eseguire con `sudo ./gather.sh`.

Questo script salva l'output dei comandi in un file che si trova nella stessa directory in cui è stato richiamato lo script.

Inoltre, tutti i comandi nei codici di blocco bash descritti in questo documento, possono essere eseguiti `az-cli` usando l'estensione run-command e analizzando l'output per `jq` ottenere un output simile all'esecuzione dei comandi in locale: '

```azurecli-interactive
output=$(az vm run-command invoke -g $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "ls -l /dev/disk/azure")
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```