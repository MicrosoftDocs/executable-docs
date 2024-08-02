---
title: Obtención de métricas de rendimiento de un sistema Linux
description: Obtenga información sobre cómo obtener métricas de rendimiento de un sistema Linux.
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

# Obtención de métricas de rendimiento de un sistema Linux

**Se aplica a:** :heavy_check_mark: Máquinas virtuales Linux

En este artículo se tratan instrucciones para determinar cómo obtener rápidamente las métricas de rendimiento de un sistema Linux.

Hay varios comandos que se pueden usar para obtener contadores de rendimiento en Linux. Los comandos como `vmstat` y `uptime`, proporcionan métricas generales del sistema, como el uso de CPU, la memoria del sistema y la carga del sistema.
La mayoría de los comandos ya están instalados de forma predeterminada con otros que están disponibles fácilmente en los repositorios predeterminados.
Los comandos se pueden separar en:

* CPU
* Memoria
* E/S de disco
* Procesos

## Instalación de utilidades de Sysstat

<!-- Commenting out these entries as this information should be selected by the user along with the corresponding subscription and region

The First step in this tutorial is to define environment variables, and install the corresponding package, if necessary.

```azurecli-interactive
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup89f292"
export MY_VM_NAME="myVM89f292"
```
-->

> [!NOTE]
> Algunos de estos comandos deben ejecutarse como `root` para poder recopilar todos los detalles pertinentes.

> [!NOTE]
> Algunos comandos forman parte del `sysstat` paquete que podría no instalarse de forma predeterminada. El paquete se puede instalar fácilmente con `sudo apt install sysstat`o `dnf install sysstat` `zypper install sysstat` para esas distribuciones populares.

El comando completo para la instalación del `sysstat` paquete en algunas distribuciones populares es:

```bash
az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "/bin/bash -c 'OS=\$(cat /etc/os-release|grep NAME|head -1|cut -d= -f2 | sed \"s/\\\"//g\"); if [[ \$OS =~ \"Ubuntu\" ]] || [[ \$OS =~ \"Debian\" ]]; then sudo apt install sysstat -y; elif [[ \$OS =~ \"Red Hat\" ]]; then sudo dnf install sysstat -y; elif [[ \$OS =~ \"SUSE\" ]]; then sudo zypper install sysstat --non-interactive; else echo \"Unknown distribution\"; fi'"
```

## CPU

### <a id="mpstat"></a>mpstat

La `mpstat` utilidad forma parte del `sysstat` paquete. Muestra el uso de CPU y los promedios, lo que resulta útil para identificar rápidamente el uso de la CPU. `mpstat` proporciona información general sobre el uso de cpu en las CPU disponibles, lo que ayuda a identificar el equilibrio de uso y si una sola CPU está muy cargada.

El comando completo es:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Las opciones y los argumentos son:

* `-P`: indica el procesador para mostrar las estadísticas, el argumento ALL indica que se muestran las estadísticas de todas las CPU en línea del sistema.
* `1`: el primer argumento numérico indica la frecuencia con la que se actualiza la presentación en segundos.
* `2`: el segundo argumento numérico indica cuántas veces se actualizan los datos.

El número de veces que el `mpstat` comando muestra los datos se puede cambiar aumentando el segundo argumento numérico para dar cabida a tiempos de recopilación de datos más largos. Lo ideal es que 3 o 5 segundos sea suficiente para los sistemas con un mayor número de núcleos 2 segundos para reducir la cantidad de datos mostrados.
Desde la salida:

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

Hay un par de cosas importantes que hay que tener en cuenta. La primera línea muestra información útil:

* Kernel y versión: `5.14.0-362.8.1.el9_3.x86_64`
* Nombre de host: `alma9`
* Fecha: `02/21/24`
* Arquitectura: `_x86_64_`
* Cantidad total de CPU (esta información es útil para interpretar la salida de otros comandos): `(8 CPU)`

A continuación, se muestran las métricas de las CPU para explicar cada una de las columnas:

* `Time`: la hora en que se recopiló la muestra.
* `CPU`: el identificador numérico de CPU, el identificador ALL es un promedio para todas las CPU.
* `%usr`: porcentaje de uso de CPU para el espacio de usuario, normalmente aplicaciones de usuario.
* `%nice`: el porcentaje de uso de CPU para los procesos de espacio de usuario con un buen valor (prioridad).
* `%sys`: el porcentaje de uso de CPU para los procesos de espacio de kernel.
* `%iowait`: porcentaje del tiempo de CPU invertido en espera de E/S pendiente.
* `%irq`: el porcentaje de tiempo de CPU dedicado a atender interrupciones de hardware.
* `%soft`: el porcentaje de tiempo de CPU dedicado a atender interrupciones de software.
* `%steal`: el porcentaje de tiempo de CPU dedicado a atender otras máquinas virtuales (no aplicables a Azure debido a que no se aprovisiona demasiado la CPU).
* `%guest`: el porcentaje de tiempo de CPU dedicado a atender cpu virtuales (no aplicable a Azure, solo aplicable a los sistemas sin sistema operativo que ejecutan máquinas virtuales).
* `%gnice`: el porcentaje de tiempo de CPU dedicado a atender CPU virtuales con un buen valor (no aplicable a Azure, solo aplicable a los sistemas sin sistema operativo que ejecutan máquinas virtuales).
* `%idle`: el porcentaje de tiempo de CPU invertido en inactividad y sin esperar las solicitudes de E/S.

#### Cosas que hay que buscar

Algunos detalles que se deben tener en cuenta al revisar la salida de `mpstat`:

* Compruebe que todas las CPU se cargan correctamente y que no una sola CPU atiende toda la carga. Esta información podría indicar una sola aplicación subprocesada.
* Busque un equilibrio correcto entre `%usr` y `%sys` como lo contrario indicaría más tiempo invertido en la carga de trabajo real que servir procesos de kernel.
* Busque `%iowait` porcentajes como valores altos podría indicar un sistema que está esperando constantemente solicitudes de E/S.
* Un uso elevado `%soft` podría indicar un tráfico de red elevado.

### `vmstat`

La `vmstat` utilidad está ampliamente disponible en la mayoría de las distribuciones de Linux, proporciona información general de alto nivel para el uso de CPU, memoria y E/S de disco en un solo panel.
El comando para `vmstat` es:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'vmstat -w 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Las opciones y los argumentos son:

* `-w`: use la impresión ancha para mantener columnas coherentes.
* `1`: el primer argumento numérico indica la frecuencia con la que se actualiza la presentación en segundos.
* `5`: el segundo argumento numérico indica cuántas veces se actualizan los datos.

Salida:

```output
--procs-- -----------------------memory---------------------- ---swap-- -----io---- -system-- --------cpu--------
   r    b         swpd         free         buff        cache   si   so    bi    bo   in   cs  us  sy  id  wa  st
  14    0            0     26059408          164       137468    0    0    89  3228   56  122   3   1  95   1   0
  14    1            0     24388660          164       145468    0    0     0  7811 3264 13870  76  24   0   0   0
  18    1            0     23060116          164       155272    0    0    44  8075 3704 15129  78  22   0   0   0
  18    1            0     21078640          164       165108    0    0   295  8837 3742 15529  73  27   0   0   0
  15    2            0     19015276          164       175960    0    0     9  8561 3639 15177  73  27   0   0   0
```

`vmstat` divide la salida en seis grupos:

* `procs`: estadísticas para procesos.
* `memory`: estadísticas para la memoria del sistema.
* `swap`: estadísticas de intercambio.
* `io`: estadísticas de disk io.
* `system`: estadísticas de modificadores de contexto e interrupciones.
* `cpu`: estadísticas para el uso de CPU.

>Nota: `vmstat` muestra las estadísticas generales de todo el sistema (es decir, todas las CPU, todos los dispositivos de bloque agregados).

#### `procs`

La `procs` sección tiene dos columnas:

* `r`: número de procesos ejecutables en la cola de ejecución.
* `b`: el número de procesos bloqueados en espera de E/S.

En esta sección se muestra inmediatamente si hay algún cuello de botella en el sistema. Los números altos en cualquiera de las columnas indican los procesos en cola en espera de recursos.

La `r` columna indica el número de procesos que están esperando a que se pueda ejecutar el tiempo de CPU. Una manera fácil de interpretar este número es la siguiente: si el número de procesos de la `r` cola es mayor que el número de CPU totales, se puede deducir que el sistema tiene la CPU muy cargada y no puede asignar tiempo de CPU para todos los procesos que esperan a ejecutarse.

La `b` columna indica el número de procesos que esperan a ejecutarse que están bloqueados por solicitudes de E/S. Un número alto en esta columna indicaría un sistema que está experimentando una E/S elevada y los procesos no se pueden ejecutar debido a otros procesos que esperan a solicitudes de E/S completadas. Lo que también podría indicar una latencia de disco alta.

#### `memory`

La sección memoria tiene cuatro columnas:

* `swpd`: la cantidad de memoria de intercambio usada.
* `free`: cantidad de memoria libre.
* `buff`: la cantidad de memoria usada para los búferes.
* `cache`: la cantidad de memoria usada para la memoria caché.

> [!NOTE]
> Los valores se muestran en bytes.

En esta sección se proporciona información general de alto nivel sobre el uso de memoria.

#### `swap`

La sección swap tiene dos columnas:

* `si`: cantidad de memoria intercambiada en (movido de memoria del sistema a intercambio) por segundo.
* `so`: cantidad de memoria intercambiada (movida de intercambio a memoria del sistema) por segundo.

Si se observa un valor alto `si` , podría representar un sistema que se está quedando sin memoria del sistema y está moviendo páginas para intercambiar (intercambio).

#### `io`

La `io` sección tiene dos columnas:

* `bi`: el número de bloques recibidos de un dispositivo de bloque (lee bloques por segundo) por segundo.
* `bo`: número de bloques enviados a un dispositivo de bloque (escrituras por segundo) por segundo.

> [!NOTE]
> Estos valores están en bloques por segundo.

#### `system`

La `system` sección tiene dos columnas:

* `in`: número de interrupciones por segundo.
* `cs`: número de modificadores de contexto por segundo.

Un gran número de interrupciones por segundo podría indicar un sistema ocupado con dispositivos de hardware (por ejemplo, operaciones de red).

Un gran número de conmutadores de contexto puede indicar un sistema ocupado con muchos procesos de ejecución corta, no hay un número correcto o incorrecto aquí.

#### `cpu`

Esta sección tiene cinco columnas:

* `us`: uso del porcentaje de espacio de usuario.
* `sy`: porcentaje de uso del sistema (espacio del kernel).
* `id`: porcentaje de uso de la cantidad de tiempo que la CPU está inactiva.
* `wa`: porcentaje de uso del tiempo que la CPU está inactiva en espera de procesos con E/S.
* `st`: porcentaje de uso de la cantidad de tiempo que la CPU ha dedicado a atender otras CPU virtuales (no aplicables a Azure).

Los valores se presentan en porcentaje. Estos valores son los mismos que presenta la `mpstat` utilidad y sirven para proporcionar información general de alto nivel sobre el uso de la CPU. Siga un proceso similar para "[Cosas que se deben](#mpstat) buscar" al `mpstat` revisar estos valores.

### `uptime`

Por último, para las métricas relacionadas con la CPU, la `uptime` utilidad proporciona una amplia introducción a la carga del sistema con los valores medios de carga.

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'uptime')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

```output
16:55:53 up 9 min,  2 users,  load average: 9.26, 2.91, 1.18
```

El promedio de carga muestra tres números. Estos números son para `1`intervalos de y `5` `15` minutos de carga del sistema.

Para interpretar estos valores, es importante conocer el número de CPU disponibles en el sistema, obtenidos de la `mpstat` salida antes. El valor depende de las CPU totales, por lo que, como ejemplo de la `mpstat` salida, el sistema tiene 8 CPU, un promedio de carga de 8 significaría que todos los núcleos se cargan en un 100 %.

Un valor de `4` significaría que la mitad de las CPU se cargaron al 100 % (o un total de 50 % de carga en todas las CPU). En la salida anterior, el promedio de carga es `9.26`, lo que significa que la CPU se carga aproximadamente en un 115 %.

Los `1m`intervalos , `5m``15m` ayudan a identificar si la carga aumenta o disminuye con el tiempo.

> [NOTA] El `nproc` comando también se puede usar para obtener el número de CPU.

## Memoria

Para la memoria, hay dos comandos que pueden obtener detalles sobre el uso.

### `free`

El `free` comando muestra el uso de memoria del sistema.

Para ejecutarlo:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'free -h')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Las opciones y los argumentos son:

* `-h`: mostrar valores dinámicamente como legibles humanas (por ejemplo: Mib, Gib, Tib)

Salida:

```output
               total        used        free      shared  buff/cache   available
Mem:            31Gi        19Gi        12Gi        23Mi        87Mi        11Gi
Swap:           23Gi          0B        23Gi
```

En la salida, busque la memoria total del sistema frente a la disponible y el intercambio utilizado frente al total. La memoria disponible tiene en cuenta la memoria asignada para la memoria caché, que se puede devolver para las aplicaciones de usuario.

Algunos usos de intercambio son normales en kernels modernos, ya que algunas páginas de memoria usadas con menos frecuencia se pueden mover al intercambio.

### `swapon`

El `swapon` comando muestra dónde se configura el intercambio y las prioridades respectivas de los dispositivos o archivos de intercambio.

Para ejecutar el comando:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'swapon -s')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Salida:

```output
Filename      Type          Size          Used   Priority
/dev/zram0    partition     16G           0B      100
/mnt/swapfile file          8G            0B      -2
```

Esta información es importante para comprobar si el intercambio está configurado en una ubicación que no es ideal, por ejemplo, en un disco de datos o sistema operativo. En el marco de referencia de Azure, el intercambio debe configurarse en la unidad efímera, ya que proporciona el mejor rendimiento.

### Cosas que hay que buscar

* Tenga en cuenta que la memoria es un recurso finito, una vez que se agota tanto la memoria del sistema (RAM) como el intercambio, los procesos serán eliminados por el asesino out of Memorry (OOM).
* Compruebe que el intercambio no está configurado en un disco de datos o en el disco del sistema operativo, ya que esto crearía problemas con la E/S debido a las diferencias de latencia. El intercambio debe configurarse en la unidad efímera.
* Tenga en cuenta también que es habitual ver en la `free -h` salida que los valores libres están cerca de cero, este comportamiento se debe a la memoria caché de páginas, el kernel libera esas páginas según sea necesario.

## E/S

La E/S de disco es una de las áreas que Azure sufre más cuando se limita, ya que los discos pueden alcanzar `100ms+` latencias. Los siguientes comandos ayudan a identificar estos escenarios.

### `iostat`

La `iostat` utilidad forma parte del `sysstat` paquete. Muestra las estadísticas de uso de dispositivos por bloque y ayuda a identificar problemas de rendimiento relacionados con el bloque.

La `iostat` utilidad proporciona detalles sobre métricas como el rendimiento, la latencia y el tamaño de la cola. Estas métricas ayudan a comprender si la E/S de disco se convierte en un factor de limitación.
Para ejecutarlo, use el comando :

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'iostat -dxtm 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Las opciones y los argumentos son:

* `-d`: por informe de uso de dispositivos.
* `-x`: estadísticas extendidas.
* `-t`: muestra la marca de tiempo de cada informe.
* `-m`: se muestra en MB/s.
* `1`: el primer argumento numérico indica la frecuencia con la que se actualiza la presentación en segundos.
* `2`: el segundo argumento numérico indica cuántas veces se actualizan los datos.

Salida:

```output
Linux 5.14.0-362.8.1.el9_3.x86_64 (alma9)       02/21/24        _x86_64_        (8 CPU)

02/21/24 16:55:50
Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
sda              1.07      0.02     0.00   0.00    1.95    20.40   23.25     24.55     3.30  12.42  113.75  1081.06    0.26    537.75     0.26  49.83    0.03 2083250.04    0.00    0.00    2.65   2.42
sdb             16.99      0.67     0.36   2.05    2.00    40.47   65.26      0.44     1.55   2.32    1.32     6.92    0.00      0.00     0.00   0.00    0.00     0.00   30.56    1.30    0.16   7.16
zram0            0.51      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.00   0.00

```

La salida tiene varias columnas que no son importantes (columnas adicionales debido a la `-x` opción), algunas de las más importantes son:

* `r/s`: Operaciones de lectura por segundo (IOPS).
* `rMB/s`: lectura de megabytes por segundo.
* `r_await`: latencia de lectura en milisegundos.
* `rareq-sz`: tamaño medio de la solicitud de lectura en kilobytes.
* `w/s`: Operaciones de escritura por segundo (IOPS).
* `wMB/s`: escriba megabytes por segundo.
* `w_await`: latencia de escritura en milisegundos.
* `wareq-size`: tamaño medio de la solicitud de escritura en kilobytes.
* `aqu-sz`: tamaño medio de cola.

#### Cosas que hay que buscar

* `r/s` Busque e `w/s` (IOPS) y `rMB/s` y `wMB/s` compruebe que estos valores están dentro de los límites del disco especificado. Si los valores están cerca o superior de los límites, el disco se limitará, lo que conduce a una latencia alta. Esta información también se puede confirmar con la `%iowait` métrica de `mpstat`.
* La latencia es una métrica excelente para comprobar si el disco funciona según lo previsto. Normalmente, menor que `9ms` es la latencia esperada para PremiumSSD, otras ofertas tienen objetivos de latencia diferentes.
* El tamaño de la cola es un gran indicador de saturación. Normalmente, las solicitudes se atenderían casi en tiempo real y el número permanece cerca de uno (a medida que la cola nunca crece). Un número mayor podría indicar la saturación del disco (es decir, solicitudes en cola). No hay ningún número bueno o incorrecto para esta métrica. Comprender que cualquier cosa superior a una significa que las solicitudes están en cola ayudan a determinar si hay saturación del disco.

### `lsblk`

La `lsblk` utilidad muestra los dispositivos de bloque conectados al sistema, mientras que no proporciona métricas de rendimiento, permite una visión general rápida de cómo se configuran estos dispositivos y qué puntos de montaje se usan.

Para ejecutarlo, use el comando :

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'lsblk')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Salida:

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

#### Cosas que hay que buscar

* Busque dónde se montan los dispositivos.
* Compruebe que el intercambio no está configurado dentro de un disco de datos o disco del sistema operativo, si está habilitado.

> Nota: Una manera sencilla de correlacionar el dispositivo de bloque con un LUN en Azure es mediante la ejecución `ls -lr /dev/disk/azure`de .

## Proceso

La recopilación de detalles por proceso ayuda a comprender de dónde procede la carga del sistema.

La utilidad principal para recopilar datos estáticos de procesos es `pidstat` , ya que proporciona detalles por proceso para las estadísticas de CPU, memoria y E/S.

Por último, un proceso sencillo `ps` de ordenar por cpu superior y el uso de memoria completan las métricas.

> [!NOTE]
> Dado que estos comandos muestran detalles sobre los procesos en ejecución, deben ejecutarse como raíz con `sudo`. Este comando permite mostrar todos los procesos y no solo los del usuario.

### `pidstat`

La `pidstat` utilidad también forma parte del `sysstat` paquete. Es como `mpstat` o iostat donde muestra las métricas durante un período de tiempo determinado. De forma predeterminada, `pidstat` solo muestra las métricas de los procesos con actividad.

Los argumentos de `pidstat` son los mismos para otras `sysstat` utilidades:

* 1: El primer argumento numérico indica la frecuencia con la que se actualiza la pantalla en segundos.
* 2: El segundo argumento numérico indica cuántas veces se actualizan los datos.

> [!NOTE]
> La salida puede crecer considerablemente si hay muchos procesos con actividad.

#### Procesar estadísticas de CPU

Para recopilar estadísticas de CPU del proceso, ejecute `pidstat` sin opciones:

Los comandos siguientes se pueden usar si desea ejecutarlos desde la CLI de Azure:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Salida:

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

El comando muestra el uso por proceso de , , (no aplicable a Azure), `%wait`y el uso total`%CPU`. `%guest` `%system``%usr`

##### Cosas que hay que buscar

* Busque procesos con un porcentaje de %wait (iowait) alto, ya que podría indicar procesos bloqueados en espera de E/S, lo que también podría indicar la saturación del disco.
* Compruebe que ningún proceso único consume el 100 % de la CPU, ya que podría indicar una sola aplicación subprocesada.

#### Estadísticas de memoria de proceso

Para recopilar estadísticas de memoria de proceso, use la `-r` opción :

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -r 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Salida:

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

Las métricas recopiladas son:

* `minflt/s`: errores menores por segundo, esta métrica indica el número de páginas cargadas desde la memoria del sistema (RAM).
* `mjflt/s`: errores principales por segundo, esta métrica indica el número de páginas cargadas desde el disco (SWAP).
* `VSZ`: memoria virtual usada en bytes.
* `RSS`: memoria residente usada (memoria asignada real) en bytes.
* `%MEM`: porcentaje de memoria total usada.
* `Command`: nombre del proceso.

##### Cosas que hay que buscar

* Busque errores principales por segundo, ya que este valor indicaría un proceso que intercambia páginas hacia o desde el disco. Este comportamiento podría indicar el agotamiento de memoria y podría provocar `OOM` eventos o degradación del rendimiento debido a un intercambio más lento.
* Compruebe que un único proceso no consume el 100 % de la memoria disponible. Este comportamiento podría indicar una pérdida de memoria.

> [!NOTE]
> la `--human` opción se puede usar para mostrar números en formato legible (es decir, `Kb`, `Mb`, `GB`).

#### Estadísticas de E/S de proceso

Para recopilar estadísticas de memoria de proceso, use la `-d` opción :

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -d 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Salida:

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

Las métricas recopiladas son:

* `kB_rd/s`: kilobytes de lectura por segundo.
* `kB_wr/s`: escriba kilobytes por segundo.
* `Command`: nombre del proceso.

##### Cosas que hay que buscar

* Busque procesos únicos con altas tasas de lectura y escritura por segundo. Esta información es una guía para los procesos con E/S más que identificar problemas.
Nota: la `--human` opción se puede usar para mostrar números en formato legible (es decir, `Kb`, `Mb`, `GB`).

### `ps`

Por último, `ps` el comando muestra los procesos del sistema y se puede ordenar por CPU o Memoria.

Para ordenar por CPU y obtener los 10 procesos principales:

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

Para ordenar por `MEM%` y obtener los 10 procesos principales:

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

## Juntar todo

Un script de Bash simple puede recopilar todos los detalles de una sola ejecución y anexar la salida a un archivo para su uso posterior:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2 && vmstat -w 1 5 && uptime && free -h && swapon && iostat -dxtm 1 1 && lsblk && ls -l /dev/disk/azure && pidstat 1 1 -h --human && pidstat -r 1 1 -h --human && pidstat -d 1 1 -h --human && ps aux --sort=-%cpu | head -20 && ps aux --sort=-%mem | head -20')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```

Para ejecutar, puede crear un archivo con el contenido anterior, agregar permisos de ejecución ejecutando `chmod +x gather.sh`y ejecutándose con `sudo ./gather.sh`.

Este script guarda la salida de los comandos en un archivo ubicado en el mismo directorio donde se invocó el script.

Además, todos los comandos de los códigos de bloque de Bash descritos en este documento se pueden ejecutar `az-cli` mediante la extensión run-command y analizar la salida a través `jq` de para obtener una salida similar a ejecutar los comandos localmente: '

```azurecli-interactive
output=$(az vm run-command invoke -g $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "ls -l /dev/disk/azure")
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```