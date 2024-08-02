---
title: Obtention de métriques de performances à partir d’un système Linux
description: Découvrez comment obtenir des métriques de performances à partir d’un système Linux.
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

# Obtention de métriques de performances à partir d’un système Linux

**S’applique à :** :heavy_check_mark : machines virtuelles Linux

Cet article décrit les instructions permettant de déterminer comment obtenir rapidement des métriques de performances à partir d’un système Linux.

Il existe plusieurs commandes qui peuvent être utilisées pour obtenir des compteurs de performances sur Linux. Les commandes telles que `vmstat` et `uptime`, fournissent des métriques système générales telles que l’utilisation du processeur, la mémoire système et la charge système.
La plupart des commandes sont déjà installées par défaut et d’autres sont facilement disponibles dans les référentiels par défaut.
Les commandes peuvent être séparées en :

* UC
          
* Mémoire
* E/S disque
* Processus

## Installation des utilitaires Sysstat

<!-- Commenting out these entries as this information should be selected by the user along with the corresponding subscription and region

The First step in this tutorial is to define environment variables, and install the corresponding package, if necessary.

```azurecli-interactive
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup89f292"
export MY_VM_NAME="myVM89f292"
```
-->

> [!NOTE]
> Certaines de ces commandes doivent être exécutées pour `root` pouvoir collecter tous les détails pertinents.

> [!NOTE]
> Certaines commandes font partie du `sysstat` package qui peut ne pas être installée par défaut. Le package peut être facilement installé avec `sudo apt install sysstat`, `dnf install sysstat` ou `zypper install sysstat` pour ces distributions populaires.

La commande complète pour l’installation du `sysstat` package sur certaines distributions populaires est la suivante :

```bash
az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "/bin/bash -c 'OS=\$(cat /etc/os-release|grep NAME|head -1|cut -d= -f2 | sed \"s/\\\"//g\"); if [[ \$OS =~ \"Ubuntu\" ]] || [[ \$OS =~ \"Debian\" ]]; then sudo apt install sysstat -y; elif [[ \$OS =~ \"Red Hat\" ]]; then sudo dnf install sysstat -y; elif [[ \$OS =~ \"SUSE\" ]]; then sudo zypper install sysstat --non-interactive; else echo \"Unknown distribution\"; fi'"
```

## UC
          

### <a id="mpstat"></a>mpstat

L’utilitaire `mpstat` fait partie du `sysstat` package. Il affiche l’utilisation de l’UC et les moyennes, ce qui est utile pour identifier rapidement l’utilisation du processeur. `mpstat` fournit une vue d’ensemble de l’utilisation du processeur sur les processeurs disponibles, ce qui permet d’identifier l’équilibre d’utilisation et si un seul processeur est fortement chargé.

La commande complète est :

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Les options et les arguments sont les suivants :

* `-P`: indique le processeur pour afficher les statistiques, l’argument ALL indique d’afficher des statistiques pour toutes les UC en ligne dans le système.
* `1`: Le premier argument numérique indique la fréquence à laquelle actualiser l’affichage en secondes.
* `2`: le deuxième argument numérique indique le nombre de fois où les données sont actualisées.

Le nombre de fois où la `mpstat` commande affiche des données peut être modifié en augmentant le deuxième argument numérique pour prendre en charge les temps de collecte de données plus longs. Idéalement, 3 ou 5 secondes doivent suffire, pour que les systèmes dont le nombre de cœurs augmente 2 secondes puissent être utilisés pour réduire la quantité de données affichées.
À partir de la sortie :

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

Il y a quelques points importants à noter. La première ligne affiche des informations utiles :

* Noyau et mise en production : `5.14.0-362.8.1.el9_3.x86_64`
* Nom d’hôte : `alma9`
* Date: `02/21/24`
* Architecture: `_x86_64_`
* Quantité totale de processeurs (ces informations sont utiles pour interpréter la sortie à partir d’autres commandes) : `(8 CPU)`

Ensuite, les métriques des PROCESSEURs sont affichées pour expliquer chacune des colonnes :

* `Time`: heure à laquelle l’échantillon a été collecté
* `CPU`: identificateur numérique de l’UC, l’identificateur ALL est une moyenne pour tous les processeurs.
* `%usr`: pourcentage d’utilisation du processeur pour l’espace utilisateur, normalement des applications utilisateur.
* `%nice`: pourcentage d’utilisation du processeur pour les processus d’espace utilisateur avec une valeur agréable (priorité).
* `%sys`: pourcentage d’utilisation du processeur pour les processus d’espace noyau.
* `%iowait`: pourcentage de temps processeur passé en attente d’E/S en attente d’E/S en attente.
* `%irq`: pourcentage de temps processeur passé à traiter les interruptions matérielles.
* `%soft`: pourcentage de temps processeur consacré aux interruptions logicielles.
* `%steal`: pourcentage de temps processeur passé à servir d’autres machines virtuelles (non applicables à Azure en raison d’une surprovisionnement de l’UC).
* `%guest`: pourcentage de temps processeur consacré au service des processeurs virtuels (non applicables à Azure, applicable uniquement aux systèmes nus exécutant des machines virtuelles).
* `%gnice`: pourcentage de temps processeur passé à servir des processeurs virtuels avec une bonne valeur (non applicable à Azure, applicable uniquement aux systèmes nus exécutant des machines virtuelles).
* `%idle`: pourcentage de temps processeur passé inactif et sans attendre les demandes d’E/S.

#### Éléments à rechercher

Quelques détails à garder à l’esprit lors de l’examen de la sortie pour `mpstat`:

* Vérifiez que tous les processeurs sont correctement chargés et qu’aucun processeur unique ne sert toute la charge. Ces informations peuvent indiquer une application thread unique.
* Recherchez un équilibre sain entre `%usr` et `%sys` comme le contraire indiquerait plus de temps consacré à la charge de travail réelle que le traitement des processus de noyau.
* `%iowait` Recherchez des pourcentages comme des valeurs élevées peuvent indiquer un système qui attend constamment les demandes d’E/S.
* Une utilisation élevée `%soft` peut indiquer un trafic réseau élevé.

### `vmstat`

L’utilitaire `vmstat` est largement disponible dans la plupart des distributions Linux, il fournit une vue d’ensemble générale de l’utilisation du processeur, de la mémoire et des E/S disque dans un seul volet.
La commande est `vmstat` la suivante :

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'vmstat -w 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Les options et les arguments sont les suivants :

* `-w`: utilisez l’impression large pour conserver des colonnes cohérentes.
* `1`: Le premier argument numérique indique la fréquence à laquelle actualiser l’affichage en secondes.
* `5`: le deuxième argument numérique indique le nombre de fois où les données sont actualisées.

La sortie est la suivante :

```output
--procs-- -----------------------memory---------------------- ---swap-- -----io---- -system-- --------cpu--------
   r    b         swpd         free         buff        cache   si   so    bi    bo   in   cs  us  sy  id  wa  st
  14    0            0     26059408          164       137468    0    0    89  3228   56  122   3   1  95   1   0
  14    1            0     24388660          164       145468    0    0     0  7811 3264 13870  76  24   0   0   0
  18    1            0     23060116          164       155272    0    0    44  8075 3704 15129  78  22   0   0   0
  18    1            0     21078640          164       165108    0    0   295  8837 3742 15529  73  27   0   0   0
  15    2            0     19015276          164       175960    0    0     9  8561 3639 15177  73  27   0   0   0
```

`vmstat` fractionne la sortie en six groupes :

* `procs`: statistiques pour les processus.
* `memory`: statistiques pour la mémoire système.
* `swap`: statistiques pour l’échange.
* `io`: statistiques pour l’io disque.
* `system`: statistiques pour les commutateurs de contexte et les interruptions.
* `cpu`: statistiques relatives à l’utilisation du processeur.

>Remarque : `vmstat` affiche des statistiques globales pour l’ensemble du système (autrement dit, tous les processeurs, tous les périphériques de bloc agrégés).

#### `procs`

La `procs` section comporte deux colonnes :

* `r`: nombre de processus exécutables dans la file d’attente d’exécution.
* `b`: nombre de processus bloqués en attente d’E/S.

Cette section indique immédiatement s’il existe un goulot d’étranglement sur le système. Les nombres élevés sur l’une ou l’autre des colonnes indiquent que les processus attendent des ressources.

La `r` colonne indique le nombre de processus qui attendent que le temps processeur puisse s’exécuter. Un moyen simple d’interpréter ce nombre est le suivant : si le nombre de processus dans la `r` file d’attente est supérieur au nombre total de processeurs, il peut être déduit que le système dispose du processeur fortement chargé et qu’il ne peut pas allouer de temps processeur pour tous les processus en attente d’exécution.

La `b` colonne indique le nombre de processus en attente d’exécution qui sont bloqués par les demandes d’E/S. Un nombre élevé dans cette colonne indique un système qui rencontre des E/S élevées, et les processus ne peuvent pas s’exécuter en raison d’autres processus en attente de demandes d’E/S terminées. Ce qui peut également indiquer une latence de disque élevée.

#### `memory`

La section mémoire comporte quatre colonnes :

* `swpd`: mémoire d’échange de quantité utilisée.
* `free`: quantité de mémoire libre.
* `buff`: quantité de mémoire utilisée pour les mémoires tampons.
* `cache`: quantité de mémoire utilisée pour le cache.

> [!NOTE]
> Les valeurs sont affichées en octets.

Cette section fournit une vue d’ensemble générale de l’utilisation de la mémoire.

#### `swap`

La section d’échange comporte deux colonnes :

* `si`: quantité de mémoire permutée (déplacée de la mémoire système à l’échange) par seconde.
* `so`: quantité de mémoire permutée (déplacée de l’échange vers la mémoire système) par seconde.

Si la valeur est élevée `si` , elle peut représenter un système qui manque de mémoire système et déplace les pages pour échanger (permutation).

#### `io`

La `io` section comporte deux colonnes :

* `bi`: nombre de blocs reçus d’un appareil de bloc (blocs de lecture par seconde) par seconde.
* `bo`: nombre de blocs envoyés à un appareil de bloc (écritures par seconde) par seconde.

> [!NOTE]
> Ces valeurs sont en blocs par seconde.

#### `system`

La `system` section comporte deux colonnes :

* `in`: nombre d’interruptions par seconde.
* `cs`: nombre de commutateurs de contexte par seconde.

Un nombre élevé d’interruptions par seconde peut indiquer un système occupé avec des périphériques matériels (par exemple, des opérations réseau).

Un nombre élevé de commutateurs de contexte peut indiquer un système occupé avec de nombreux processus court, il n’y a pas de bon ou mauvais nombre ici.

#### `cpu`

Cette section comporte cinq colonnes :

* `us`: utilisation de pourcentage d’espace utilisateur.
* `sy`: pourcentage d’utilisation du système (espace noyau).
* `id`: pourcentage d’utilisation du temps d’inactivité du processeur.
* `wa`: pourcentage d’utilisation du temps pendant lequel le processeur est inactif en attente de processus avec E/S.
* `st`: pourcentage d’utilisation du temps passé par l’UC à servir d’autres processeurs virtuels (non applicables à Azure).

Les valeurs sont présentées en pourcentage. Ces valeurs sont identiques à celles présentées par l’utilitaire `mpstat` et servent à fournir une vue d’ensemble générale de l’utilisation du processeur. Suivez un processus similaire pour «[ Éléments à rechercher](#mpstat) » lors `mpstat` de l’examen de ces valeurs.

### `uptime`

Enfin, pour les métriques liées au processeur, l’utilitaire `uptime` fournit une vue d’ensemble générale de la charge système avec les valeurs moyennes de charge.

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'uptime')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

```output
16:55:53 up 9 min,  2 users,  load average: 9.26, 2.91, 1.18
```

La moyenne de charge affiche trois nombres. Ces nombres concernent `1`les `5` intervalles de charge système et `15` les minutes.

Pour interpréter ces valeurs, il est important de connaître le nombre de processeurs disponibles dans le système, obtenus à partir de la `mpstat` sortie précédente. La valeur dépend du nombre total de processeurs. Par conséquent, comme exemple de sortie, `mpstat` le système comporte 8 processeurs, une moyenne de charge de 8 signifie que tous les cœurs sont chargés à 100 %.

La valeur d’une `4` valeur signifie que la moitié des PROCESSEURs ont été chargées à 100 % (ou un total de 50 % de charge sur tous les processeurs). Dans la sortie précédente, la moyenne de charge est `9.26`, ce qui signifie que le processeur est chargé à environ 115 %.

Les `1m`intervalles , `5m``15m` permettent d’identifier si la charge augmente ou diminue au fil du temps.

> [REMARQUE] La `nproc` commande peut également être utilisée pour obtenir le nombre de processeurs.

## Mémoire

Pour la mémoire, il existe deux commandes qui peuvent obtenir des détails sur l’utilisation.

### `free`

La `free` commande affiche l’utilisation de la mémoire système.

Pour l’exécuter :

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'free -h')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Les options et les arguments sont les suivants :

* `-h`: Afficher dynamiquement les valeurs en tant que lisibles par l’homme (par exemple : Mib, Gib, Tib)

La sortie est la suivante :

```output
               total        used        free      shared  buff/cache   available
Mem:            31Gi        19Gi        12Gi        23Mi        87Mi        11Gi
Swap:           23Gi          0B        23Gi
```

À partir de la sortie, recherchez la mémoire système totale par rapport à la mémoire disponible, et l’échange total utilisé ou total. La mémoire disponible prend en compte la mémoire allouée pour le cache, qui peut être retournée pour les applications utilisateur.

Certaines utilisations de l’échange sont normales dans les noyaux modernes, car certaines pages de mémoire moins souvent utilisées peuvent être déplacées pour échanger.

### `swapon`

La `swapon` commande affiche l’emplacement où l’échange est configuré et les priorités respectives des appareils ou fichiers d’échange.

Pour exécuter la commande :

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'swapon -s')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

La sortie est la suivante :

```output
Filename      Type          Size          Used   Priority
/dev/zram0    partition     16G           0B      100
/mnt/swapfile file          8G            0B      -2
```

Ces informations sont importantes pour vérifier si l’échange est configuré sur un emplacement qui n’est pas idéal, par exemple sur un disque de données ou de système d’exploitation. Dans la trame de référence Azure, l’échange doit être configuré sur le lecteur éphémère, car il offre les meilleures performances.

### Éléments à rechercher

* Gardez à l’esprit que la mémoire est une ressource finie, une fois que la mémoire système (RAM) et l’échange sont épuisées, les processus doivent être tués par le tueur out Of Memorry (OOM).
* Vérifiez que l’échange n’est pas configuré sur un disque de données ou sur le disque du système d’exploitation, car cela créerait des problèmes d’E/S en raison de différences de latence. L’échange doit être configuré sur le lecteur éphémère.
* Gardez également en considération qu’il est courant de voir sur la `free -h` sortie que les valeurs libres sont proches de zéro, ce comportement est dû au cache de pages, le noyau libère ces pages selon les besoins.

## E/S

Les E/S de disque sont l’une des zones où Azure souffre le plus lorsqu’ils sont limités, car les disques peuvent atteindre `100ms+` des latences. Les commandes suivantes permettent d’identifier ces scénarios.

### `iostat`

L’utilitaire `iostat` fait partie du `sysstat` package. Il affiche les statistiques d’utilisation des appareils par bloc et permet d’identifier les problèmes de performances liés aux blocs.

L’utilitaire `iostat` fournit des détails sur les métriques telles que le débit, la latence et la taille de la file d’attente. Ces métriques permettent de comprendre si les E/S de disque deviennent un facteur de limitation.
Pour exécuter, utilisez la commande suivante :

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'iostat -dxtm 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Les options et les arguments sont les suivants :

* `-d`: rapport d’utilisation par appareil.
* `-x`: statistiques étendues.
* `-t`: affiche l’horodatage pour chaque rapport.
* `-m`: affichage en Mo/s.
* `1`: Le premier argument numérique indique la fréquence à laquelle actualiser l’affichage en secondes.
* `2`: le deuxième argument numérique indique le nombre de fois où les données sont actualisées.

La sortie est la suivante :

```output
Linux 5.14.0-362.8.1.el9_3.x86_64 (alma9)       02/21/24        _x86_64_        (8 CPU)

02/21/24 16:55:50
Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
sda              1.07      0.02     0.00   0.00    1.95    20.40   23.25     24.55     3.30  12.42  113.75  1081.06    0.26    537.75     0.26  49.83    0.03 2083250.04    0.00    0.00    2.65   2.42
sdb             16.99      0.67     0.36   2.05    2.00    40.47   65.26      0.44     1.55   2.32    1.32     6.92    0.00      0.00     0.00   0.00    0.00     0.00   30.56    1.30    0.16   7.16
zram0            0.51      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.00   0.00

```

La sortie comporte plusieurs colonnes qui ne sont pas importantes (colonnes supplémentaires en raison de l’option `-x` ), certaines des colonnes importantes sont les suivantes :

* `r/s`: Opérations de lecture par seconde (IOPS).
* `rMB/s`: Lecture de mégaoctets par seconde.
* `r_await`: latence de lecture en millisecondes.
* `rareq-sz`: Taille moyenne de la demande de lecture en kilo-octets.
* `w/s`: opérations d’écriture par seconde (IOPS).
* `wMB/s`: écrire des mégaoctets par seconde.
* `w_await`: latence d’écriture en millisecondes.
* `wareq-size`: Taille moyenne de la demande d’écriture en kilo-octets.
* `aqu-sz`: Taille moyenne de la file d’attente.

#### Éléments à rechercher

* `r/s` Recherchez et `w/s` (IOPS) et `rMB/s` `wMB/s` vérifiez que ces valeurs se trouvent dans les limites du disque donné. Si les valeurs sont proches ou supérieures aux limites, le disque va être limité, ce qui entraîne une latence élevée. Ces informations peuvent également être corroborées par la `%iowait` métrique de `mpstat`.
* La latence est une excellente métrique pour vérifier si le disque fonctionne comme prévu. Normalement, moins que `9ms` la latence attendue pour PremiumSSD, d’autres offres ont des cibles de latence différentes.
* La taille de la file d’attente est un excellent indicateur de saturation. Normalement, les demandes seraient traitées en quasi temps réel et le nombre reste proche d’un (car la file d’attente ne croît jamais). Un nombre plus élevé peut indiquer la saturation du disque (autrement dit, les requêtes en file d’attente). Il n’y a pas de bon ou de mauvais nombre pour cette métrique. Comprendre que tout ce qui est supérieur à un signifie que les requêtes sont mises en file d’attente permet de déterminer s’il existe une saturation du disque.

### `lsblk`

L’utilitaire `lsblk` montre les appareils de bloc attachés au système, alors qu’il ne fournit pas de métriques de performances, il permet une vue d’ensemble rapide de la façon dont ces appareils sont configurés et quels points de montage sont utilisés.

Pour exécuter, utilisez la commande suivante :

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'lsblk')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

La sortie est la suivante :

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

#### Éléments à rechercher

* Recherchez l’emplacement où les appareils sont montés.
* Vérifiez qu’il n’est pas configuré à l’intérieur d’un disque de données ou d’un disque de système d’exploitation, s’il est activé.

> Remarque : Un moyen simple de mettre en corrélation l’appareil de bloc à un numéro d’unité logique dans Azure est en cours d’exécution `ls -lr /dev/disk/azure`.

## Process

La collecte de détails par processus permet de comprendre où provient la charge du système.

L’utilitaire principal pour collecter des statiques de processus est `pidstat` qu’il fournit des détails par processus pour les statistiques d’UC, de mémoire et d’E/S.

Enfin, un processus simple `ps` à trier par processeur principal et l’utilisation de la mémoire terminent les métriques.

> [!NOTE]
> Étant donné que ces commandes affichent des détails sur les processus en cours d’exécution, elles doivent s’exécuter en tant que racine avec `sudo`. Cette commande permet à tous les processus d’être affichés et pas seulement de l’utilisateur.

### `pidstat`

L’utilitaire `pidstat` fait également partie du `sysstat` package. Il est semblable `mpstat` ou iostat où il affiche des métriques pendant une période donnée. Par défaut, `pidstat` affiche uniquement les métriques pour les processus avec l’activité.

Les arguments correspondants `pidstat` sont les mêmes pour les autres `sysstat` utilitaires :

* 1 : Le premier argument numérique indique la fréquence d’actualisation de l’affichage en secondes.
* 2 : Le deuxième argument numérique indique le nombre de fois où les données sont actualisées.

> [!NOTE]
> La sortie peut croître considérablement s’il existe de nombreux processus avec l’activité.

#### Traiter les statistiques du processeur

Pour collecter les statistiques du processeur de processus, exécutez `pidstat` sans aucune option :

Les commandes suivantes peuvent être utilisées si vous souhaitez l’exécuter à partir d’Azure CLI :

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

La sortie est la suivante :

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

La commande affiche l’utilisation par processus pour `%usr`, `%system``%guest` (non applicable à Azure) `%wait`et l’utilisation totale`%CPU`.

##### Éléments à rechercher

* Recherchez des processus avec un pourcentage %wait (iowait) élevé, car il peut indiquer les processus qui sont bloqués en attente d’E/S, ce qui peut également indiquer la saturation du disque.
* Vérifiez qu’aucun processus unique ne consomme 100 % de l’UC, car il peut indiquer une application thread unique.

#### Traiter les statistiques de mémoire

Pour collecter les statistiques de mémoire du processus, utilisez l’option `-r` suivante :

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -r 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

La sortie est la suivante :

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

Les métriques collectées sont les suivantes :

* `minflt/s`: Erreurs mineures par seconde, cette métrique indique le nombre de pages chargées à partir de la mémoire système (RAM).
* `mjflt/s`: erreurs majeures par seconde, cette métrique indique le nombre de pages chargées à partir du disque (SWAP).
* `VSZ`: mémoire virtuelle utilisée en octets.
* `RSS`: mémoire résidente utilisée (mémoire allouée réelle) en octets.
* `%MEM`: pourcentage de mémoire totale utilisée.
* `Command`: nom du processus.

##### Éléments à rechercher

* Recherchez les principales erreurs par seconde, car cette valeur indiquerait un processus qui échange des pages vers ou depuis le disque. Ce comportement peut indiquer l’épuisement de la mémoire et entraîner une `OOM` dégradation des événements ou des performances en raison d’un échange plus lent.
* Vérifiez qu’un seul processus ne consomme pas 100 % de la mémoire disponible. Ce comportement peut indiquer une fuite de mémoire.

> [!NOTE]
> l’option `--human` peut être utilisée pour afficher des nombres au format lisible par l’homme (autrement dit, `Kb`, `Mb`, `GB`).

#### Traiter les statistiques d’E/S

Pour collecter les statistiques de mémoire du processus, utilisez l’option `-d` suivante :

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -d 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

La sortie est la suivante :

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

Les métriques collectées sont les suivantes :

* `kB_rd/s`: Lecture de kilo-octets par seconde.
* `kB_wr/s`: écrire des kilo-octets par seconde.
* `Command`: Nom du processus.

##### Éléments à rechercher

* Recherchez des processus uniques avec des taux élevés de lecture/écriture par seconde. Ces informations sont des conseils pour les processus avec des E/S plus que l’identification des problèmes.
Remarque : l’option `--human` peut être utilisée pour afficher des nombres au format lisible par l’homme (autrement dit, , `Kb``Mb`, `GB`).

### `ps`

Enfin, `ps` la commande affiche les processus système et peut être triée par processeur ou mémoire.

Pour trier par processeur et obtenir les 10 principaux processus :

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

Pour trier `MEM%` et obtenir les 10 premiers processus :

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

## Mise en place de tous les ensembles

Un script bash simple peut collecter tous les détails d’une seule exécution et ajouter la sortie à un fichier pour une utilisation ultérieure :

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2 && vmstat -w 1 5 && uptime && free -h && swapon && iostat -dxtm 1 1 && lsblk && ls -l /dev/disk/azure && pidstat 1 1 -h --human && pidstat -r 1 1 -h --human && pidstat -d 1 1 -h --human && ps aux --sort=-%cpu | head -20 && ps aux --sort=-%mem | head -20')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```

Pour exécuter, vous pouvez créer un fichier avec le contenu ci-dessus, ajouter des autorisations d’exécution en exécutant `chmod +x gather.sh`et exécuter avec `sudo ./gather.sh`.

Ce script enregistre la sortie des commandes dans un fichier situé dans le même répertoire que celui où le script a été appelé.

En outre, toutes les commandes des codes de bloc bash abordés dans ce document peuvent être exécutées à `az-cli` l’aide de l’extension run-command et analysent la sortie `jq` pour obtenir une sortie similaire à l’exécution des commandes localement :

```azurecli-interactive
output=$(az vm run-command invoke -g $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "ls -l /dev/disk/azure")
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```