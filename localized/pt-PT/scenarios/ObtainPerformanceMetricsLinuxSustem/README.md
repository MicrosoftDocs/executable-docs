---
title: Obtendo métricas de desempenho de um sistema Linux
description: Saiba como obter métricas de desempenho de um sistema Linux.
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

# Obtendo métricas de desempenho de um sistema Linux

**Aplica-se a:** :heavy_check_mark: VMs Linux

Este artigo abordará instruções para determinar como obter rapidamente métricas de desempenho de um sistema Linux.

Existem vários comandos que podem ser usados para obter contadores de desempenho no Linux. Comandos como `vmstat` e `uptime`, fornecem métricas gerais do sistema, como uso da CPU, memória do sistema e carga do sistema.
A maioria dos comandos já está instalada por padrão, com outros prontamente disponíveis em repositórios padrão.
Os comandos podem ser separados em:

* CPU
* Memória
* E/S de disco
* Processos

## Instalação de utilitários Sysstat

<!-- Commenting out these entries as this information should be selected by the user along with the corresponding subscription and region

The First step in this tutorial is to define environment variables, and install the corresponding package, if necessary.

```azurecli-interactive
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup89f292"
export MY_VM_NAME="myVM89f292"
```
-->

> [!NOTE]
> Alguns desses comandos precisam ser executados `root` para poder reunir todos os detalhes relevantes.

> [!NOTE]
> Alguns comandos fazem parte do `sysstat` pacote que pode não ser instalado por padrão. O pacote pode ser facilmente instalado com `sudo apt install sysstat`, `dnf install sysstat` ou `zypper install sysstat` para as distros populares.

O comando completo para a `sysstat` instalação do pacote em algumas distros populares é:

```bash
az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "/bin/bash -c 'OS=\$(cat /etc/os-release|grep NAME|head -1|cut -d= -f2 | sed \"s/\\\"//g\"); if [[ \$OS =~ \"Ubuntu\" ]] || [[ \$OS =~ \"Debian\" ]]; then sudo apt install sysstat -y; elif [[ \$OS =~ \"Red Hat\" ]]; then sudo dnf install sysstat -y; elif [[ \$OS =~ \"SUSE\" ]]; then sudo zypper install sysstat --non-interactive; else echo \"Unknown distribution\"; fi'"
```

## CPU

### <a id="mpstat"></a>MPSTAT

O `mpstat` utilitário faz parte do `sysstat` pacote. Ele exibe por utilização da CPU e médias, o que é útil para identificar rapidamente o uso da CPU. `mpstat` fornece uma visão geral da utilização da CPU nas CPUs disponíveis, ajudando a identificar o equilíbrio de uso e se uma única CPU está muito carregada.

O comando completo é:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

As opções e os argumentos são:

* `-P`: Indica o processador para exibir estatísticas, o argumento ALL indica para exibir estatísticas para todas as CPUs online no sistema.
* `1`: O primeiro argumento numérico indica a frequência com que a exibição deve ser atualizada em segundos.
* `2`: O segundo argumento numérico indica quantas vezes os dados são atualizados.

O número de vezes que o `mpstat` comando exibe dados pode ser alterado aumentando o segundo argumento numérico para acomodar tempos de coleta de dados mais longos. Idealmente, 3 ou 5 segundos devem ser suficientes, para sistemas com maior contagem de núcleos 2 segundos podem ser usados para reduzir a quantidade de dados exibidos.
Da saída:

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

Há algumas coisas importantes a observar. A primeira linha exibe informações úteis:

* Kernel e lançamento: `5.14.0-362.8.1.el9_3.x86_64`
* Nome do host: `alma9`
* Data: `02/21/24`
* Arquitetura: `_x86_64_`
* Quantidade total de CPUs (esta informação é útil para interpretar a saída de outros comandos): `(8 CPU)`

Em seguida, as métricas para as CPUs são exibidas, para explicar cada uma das colunas:

* `Time`: O momento em que a amostra foi coletada
* `CPU`: O identificador numérico da CPU, o identificador ALL é uma média para todas as CPUs.
* `%usr`: A porcentagem de utilização da CPU para o espaço do usuário, normalmente aplicativos do usuário.
* `%nice`: A porcentagem de utilização da CPU para processos de espaço do usuário com um bom valor (prioridade).
* `%sys`: A porcentagem de utilização da CPU para processos de espaço do kernel.
* `%iowait`: A percentagem de tempo de CPU gasto inativo à espera de E/S pendentes.
* `%irq`: A percentagem de tempo de CPU gasto a servir interrupções de hardware.
* `%soft`: A percentagem de tempo de CPU gasto a servir interrupções de software.
* `%steal`: A percentagem de tempo de CPU gasto a servir outras máquinas virtuais (não aplicável ao Azure devido a não haver sobreaprovisionamento de CPU).
* `%guest`: A percentagem de tempo de CPU gasto a servir CPUs virtuais (não aplicável ao Azure, apenas aplicável a sistemas bare metal que executam máquinas virtuais).
* `%gnice`: A percentagem de tempo de CPU gasto a servir CPUs virtuais com um bom valor (não aplicável ao Azure, apenas aplicável a sistemas bare metal que executam máquinas virtuais).
* `%idle`: A porcentagem de tempo de CPU gasto ocioso e sem esperar por solicitações de E/S.

#### Aspetos a que deve estar atento

Alguns detalhes a ter em mente ao rever a saída para `mpstat`:

* Verifique se todas as CPUs estão carregadas corretamente e se nenhuma CPU está servindo toda a carga. Essas informações podem indicar um único aplicativo encadeado.
* Procure um equilíbrio saudável entre `%usr` e `%sys` como o oposto indicaria mais tempo gasto na carga de trabalho real do que servindo processos do kernel.
* Procure `%iowait` porcentagens, pois valores altos podem indicar um sistema que está constantemente aguardando solicitações de E/S.
* Alto `%soft` uso pode indicar alto tráfego de rede.

### `vmstat`

O `vmstat` utilitário está amplamente disponível na maioria das distribuições Linux, ele fornece visão geral de alto nível para a utilização de CPU, memória e E/S de disco em um único painel.
O comando para `vmstat` é:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'vmstat -w 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

As opções e os argumentos são:

* `-w`: Use a impressão ampla para manter colunas consistentes.
* `1`: O primeiro argumento numérico indica a frequência com que a exibição deve ser atualizada em segundos.
* `5`: O segundo argumento numérico indica quantas vezes os dados são atualizados.

A saída:

```output
--procs-- -----------------------memory---------------------- ---swap-- -----io---- -system-- --------cpu--------
   r    b         swpd         free         buff        cache   si   so    bi    bo   in   cs  us  sy  id  wa  st
  14    0            0     26059408          164       137468    0    0    89  3228   56  122   3   1  95   1   0
  14    1            0     24388660          164       145468    0    0     0  7811 3264 13870  76  24   0   0   0
  18    1            0     23060116          164       155272    0    0    44  8075 3704 15129  78  22   0   0   0
  18    1            0     21078640          164       165108    0    0   295  8837 3742 15529  73  27   0   0   0
  15    2            0     19015276          164       175960    0    0     9  8561 3639 15177  73  27   0   0   0
```

`vmstat` Divide a produção em seis grupos:

* `procs`: estatísticas de processos.
* `memory`: estatísticas para a memória do sistema.
* `swap`: estatísticas para swap.
* `io`: Estatísticas para o Disk IO.
* `system`: estatísticas para comutadores e interrupções de contexto.
* `cpu`: estatísticas para o uso da CPU.

>Nota: `vmstat` mostra estatísticas gerais para todo o sistema (ou seja, todas as CPUs, todos os dispositivos de bloco agregados).

#### `procs`

A `procs` secção tem duas colunas:

* `r`: O número de processos executáveis na fila de execução.
* `b`: O número de processos bloqueados aguardando E/S.

Esta seção mostra imediatamente se há algum gargalo no sistema. Números altos em qualquer uma das colunas indicam processos em fila aguardando recursos.

A `r` coluna indica o número de processos que estão aguardando o tempo da CPU para poder ser executado. Uma maneira fácil de interpretar esse número é a seguinte: se o número de processos na fila `r` for maior do que o número total de CPUs, então pode-se inferir que o sistema tem a CPU muito carregada e não pode alocar o tempo da CPU para todos os processos esperando para serem executados.

A `b` coluna indica o número de processos aguardando execução que estão sendo bloqueados por solicitações de E/S. Um número alto nesta coluna indicaria um sistema com alta E/S e os processos não podem ser executados devido a outros processos aguardando solicitações de E/S concluídas. O que também pode indicar alta latência de disco.

#### `memory`

A seção de memória tem quatro colunas:

* `swpd`: A quantidade de memória de troca usada.
* `free`: A quantidade de memória livre.
* `buff`: A quantidade de memória usada para buffers.
* `cache`: A quantidade de memória usada para cache.

> [!NOTE]
> Os valores são mostrados em bytes.

Esta seção fornece uma visão geral de alto nível do uso de memória.

#### `swap`

A seção de permuta tem duas colunas:

* `si`: A quantidade de memória trocada (movida da memória do sistema para a troca) por segundo.
* `so`: A quantidade de memória trocada (movida da troca para a memória do sistema) por segundo.

Se alto `si` for observado, ele pode representar um sistema que está ficando sem memória do sistema e está movendo páginas para swap (troca).

#### `io`

A `io` secção tem duas colunas:

* `bi`: O número de blocos recebidos de um dispositivo de bloco (lê blocos por segundo) por segundo.
* `bo`: O número de blocos enviados para um dispositivo de bloco (gravações por segundo) por segundo.

> [!NOTE]
> Estes valores estão em blocos por segundo.

#### `system`

A `system` secção tem duas colunas:

* `in`: O número de interrupções por segundo.
* `cs`: O número de opções de contexto por segundo.

Um alto número de interrupções por segundo pode indicar um sistema ocupado com dispositivos de hardware (por exemplo, operações de rede).

Um alto número de opções de contexto pode indicar um sistema ocupado com muitos processos de execução curta, não há um número bom ou ruim aqui.

#### `cpu`

Esta secção tem cinco colunas:

* `us`: Utilização percentual do espaço do usuário.
* `sy`: Utilização percentual do sistema (espaço do kernel).
* `id`: Porcentagem de utilização da quantidade de tempo que a CPU está ociosa.
* `wa`: Utilização percentual da quantidade de tempo que a CPU está ociosa aguardando processos com E/S.
* `st`: Utilização percentual da quantidade de tempo que a CPU gastou servindo outras CPUs virtuais (não aplicável ao Azure).

Os valores são apresentados em percentagem. Esses valores são os mesmos apresentados pelo `mpstat` utilitário e servem para fornecer uma visão geral de alto nível do uso da CPU. Siga um processo semelhante para "[Coisas a procurar](#mpstat)" ao `mpstat` rever estes valores.

### `uptime`

Por fim, para métricas relacionadas à CPU, o `uptime` utilitário fornece uma ampla visão geral da carga do sistema com os valores médios de carga.

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'uptime')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

```output
16:55:53 up 9 min,  2 users,  load average: 9.26, 2.91, 1.18
```

A média de carga exibe três números. Esses números são para `1`, `5` e `15` intervalos de minutos de carga do sistema.

Para interpretar esses valores, é importante saber o número de CPUs disponíveis no sistema, obtido a `mpstat` partir da saída anterior. O valor depende do total de CPUs, portanto, como exemplo da `mpstat` saída o sistema tem 8 CPUs, uma média de carga de 8 significaria que TODOS os núcleos são carregados a 100%.

Um valor de `4` significaria que metade das CPUs foram carregadas a 100% (ou um total de 50% de carga em TODAS as CPUs). Na saída anterior, a média de carga é `9.26`, o que significa que a CPU é carregada em cerca de 115%.

Os `1m`intervalos , `5m`ajudam `15m` a identificar se a carga está aumentando ou diminuindo ao longo do tempo.

> [OBSERVAÇÃO] O `nproc` comando também pode ser usado para obter o número de CPUs.

## Memória

Para memória, há dois comandos que podem obter detalhes sobre o uso.

### `free`

O `free` comando mostra a utilização da memória do sistema.

Para executá-lo:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'free -h')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

As opções e os argumentos são:

* `-h`: Exibir valores dinamicamente como legíveis por humanos (por exemplo: Mib, Gib, Tib)

A saída:

```output
               total        used        free      shared  buff/cache   available
Mem:            31Gi        19Gi        12Gi        23Mi        87Mi        11Gi
Swap:           23Gi          0B        23Gi
```

A partir da saída, procure a memória total do sistema vs a disponível e a troca usada vs total. A memória disponível leva em consideração a memória alocada para cache, que pode ser retornada para aplicativos de usuário.

Algum uso de swap é normal em kernels modernos, pois algumas páginas de memória menos usadas podem ser movidas para swap.

### `swapon`

O `swapon` comando exibe onde o swap está configurado e as respetivas prioridades dos dispositivos ou arquivos de swap.

Para executar o comando:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'swapon -s')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

A saída:

```output
Filename      Type          Size          Used   Priority
/dev/zram0    partition     16G           0B      100
/mnt/swapfile file          8G            0B      -2
```

Essas informações são importantes para verificar se a troca está configurada em um local que não é ideal, por exemplo, em um disco de dados ou sistema operacional. No quadro de referência do Azure, a permuta deve ser configurada na unidade efêmera, pois fornece o melhor desempenho.

### Aspetos a que deve estar atento

* Tenha em mente que a memória é um recurso finito, uma vez que a memória do sistema (RAM) e o swap estão esgotados, os processos devem ser mortos pelo assassino out Of Memorry (OOM).
* Verifique se a troca não está configurada em um disco de dados ou no disco do sistema operacional, pois isso criaria problemas com E/S devido a diferenças de latência. A troca deve ser configurada na unidade efêmera.
* Tenha também em consideração que é comum ver na `free -h` saída que os valores livres estão próximos de zero, este comportamento é devido ao cache de páginas, o kernel libera essas páginas conforme necessário.

## E/S

A E/S de disco é uma das áreas que o Azure mais sofre quando limitada, pois os discos podem atingir `100ms+` latências. Os comandos a seguir ajudam a identificar esses cenários.

### `iostat`

O `iostat` utilitário faz parte do `sysstat` pacote. Ele exibe estatísticas de uso do dispositivo por bloco e ajuda a identificar problemas de desempenho relacionados ao bloco.

O `iostat` utilitário fornece detalhes para métricas como taxa de transferência, latência e tamanho da fila. Essas métricas ajudam a entender se a E/S de disco se torna um fator limitante.
Para executar, use o comando:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'iostat -dxtm 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

As opções e os argumentos são:

* `-d`: Relatório de utilização por dispositivo.
* `-x`: Estatísticas alargadas.
* `-t`: Exiba o carimbo de data/hora de cada relatório.
* `-m`: Ecrã em MB/s.
* `1`: O primeiro argumento numérico indica a frequência com que a exibição deve ser atualizada em segundos.
* `2`: O segundo argumento numérico indica quantas vezes os dados são atualizados.

A saída:

```output
Linux 5.14.0-362.8.1.el9_3.x86_64 (alma9)       02/21/24        _x86_64_        (8 CPU)

02/21/24 16:55:50
Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
sda              1.07      0.02     0.00   0.00    1.95    20.40   23.25     24.55     3.30  12.42  113.75  1081.06    0.26    537.75     0.26  49.83    0.03 2083250.04    0.00    0.00    2.65   2.42
sdb             16.99      0.67     0.36   2.05    2.00    40.47   65.26      0.44     1.55   2.32    1.32     6.92    0.00      0.00     0.00   0.00    0.00     0.00   30.56    1.30    0.16   7.16
zram0            0.51      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.00   0.00

```

A saída tem várias colunas que não são importantes (colunas extras devido à `-x` opção), algumas das mais importantes são:

* `r/s`: Operações de leitura por segundo (IOPS).
* `rMB/s`: Ler megabytes por segundo.
* `r_await`: Latência de leitura em milissegundos.
* `rareq-sz`: Tamanho médio da solicitação de leitura em kilobytes.
* `w/s`: Operações de gravação por segundo (IOPS).
* `wMB/s`: Escreva megabytes por segundo.
* `w_await`: Grave a latência em milissegundos.
* `wareq-size`: Tamanho médio da solicitação de gravação em kilobytes.
* `aqu-sz`: Tamanho médio da fila.

#### Aspetos a que deve estar atento

* Procure `r/s` e `w/s` (IOPS) e `rMB/s` e verifique `wMB/s` se esses valores estão dentro dos limites do disco fornecido. Se os valores estiverem próximos ou acima dos limites, o disco será limitado, levando a alta latência. Esta informação também pode ser corroborada com a `%iowait` métrica de `mpstat`.
* A latência é uma excelente métrica para verificar se o disco está funcionando conforme o esperado. Normalmente, menor do que `9ms` a latência esperada para PremiumSSD, outras ofertas têm alvos de latência diferentes.
* O tamanho da fila é um ótimo indicador de saturação. Normalmente, os pedidos seriam atendidos quase em tempo real e o número permanece próximo de um (já que a fila nunca cresce). Um número maior pode indicar saturação de disco (ou seja, solicitações em fila). Não há um número bom ou ruim para essa métrica. Entender que qualquer coisa maior do que uma significa que as solicitações estão enfileiradas ajuda a determinar se há saturação de disco.

### `lsblk`

O `lsblk` utilitário mostra os dispositivos de bloco conectados ao sistema, embora não forneça métricas de desempenho, permite uma visão geral rápida de como esses dispositivos são configurados e quais pontos de montagem estão sendo usados.

Para executar, use o comando:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'lsblk')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

A saída:

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

#### Aspetos a que deve estar atento

* Procure onde os dispositivos estão montados.
* Verifique se a troca não está configurada dentro de um disco de dados ou de um disco do sistema operacional, se habilitada.

> Observação: uma maneira fácil de correlacionar o dispositivo de bloco a um LUN no Azure é executando `ls -lr /dev/disk/azure`o .

## Processo

Reunir detalhes por processo ajuda a entender de onde vem a carga do sistema.

O principal utilitário para reunir estática de processo é `pidstat` fornecer detalhes por processo para estatísticas de CPU, memória e E/S.

Por fim, um processo simples `ps` de classificar por CPU superior e uso de memória completam as métricas.

> [!NOTE]
> Como esses comandos exibem detalhes sobre processos em execução, eles precisam ser executados como root com `sudo`. Este comando permite que todos os processos sejam exibidos e não apenas os do usuário.

### `pidstat`

O `pidstat` utilitário também faz parte do `sysstat` pacote. É como `mpstat` ou iostat onde exibe métricas para um determinado período de tempo. Por padrão, `pidstat` exibe apenas métricas para processos com atividade.

Os argumentos a favor `pidstat` são os mesmos para outros `sysstat` utilitários:

* 1: O primeiro argumento numérico indica a frequência com que a exibição deve ser atualizada em segundos.
* 2: O segundo argumento numérico indica quantas vezes os dados são atualizados.

> [!NOTE]
> A produção pode crescer consideravelmente se houver muitos processos com atividade.

#### Processar estatísticas da CPU

Para reunir estatísticas de CPU de processo, execute `pidstat` sem opções:

Os seguintes comandos podem ser usados se você quiser executá-lo a partir da CLI do Azure:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

A saída:

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

O comando exibe por uso de processo para `%usr`, `%system`, `%guest` (não aplicável ao Azure) `%wait`e uso total `%CPU` .

##### Aspetos a que deve estar atento

* Procure processos com alta porcentagem de %wait (iowait), pois isso pode indicar processos que estão bloqueados aguardando E/S, o que também pode indicar saturação de disco.
* Verifique se nenhum processo consome 100% da CPU, pois pode indicar um único aplicativo encadeado.

#### Estatísticas de memória de processo

Para reunir estatísticas de memória de processo, use a `-r` opção:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -r 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

A saída:

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

As métricas recolhidas são:

* `minflt/s`: Pequenas falhas por segundo, esta métrica indica o número de páginas carregadas da memória do sistema (RAM).
* `mjflt/s`: Principais falhas por segundo, esta métrica indica o número de páginas carregadas do disco (SWAP).
* `VSZ`: Memória virtual usada em bytes.
* `RSS`: Memória residente usada (memória real alocada) em bytes.
* `%MEM`: Percentagem da memória total utilizada.
* `Command`: O nome do processo.

##### Aspetos a que deve estar atento

* Procure falhas importantes por segundo, pois esse valor indicaria um processo que está trocando páginas de ou para o disco. Esse comportamento pode indicar esgotamento da memória e pode levar a `OOM` eventos ou degradação do desempenho devido a uma troca mais lenta.
* Verifique se um único processo não consome 100% da memória disponível. Esse comportamento pode indicar um vazamento de memória.

> [!NOTE]
> A `--human` opção pode ser usada para exibir números em formato legível por humanos (ou seja, `Kb`, , `Mb``GB`, ).

#### Estatísticas de E/S de processo

Para reunir estatísticas de memória de processo, use a `-d` opção:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -d 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

A saída:

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

As métricas recolhidas são:

* `kB_rd/s`: Leia kilobytes por segundo.
* `kB_wr/s`: Escreva kilobytes por segundo.
* `Command`: Nome do processo.

##### Aspetos a que deve estar atento

* Procure processos únicos com altas taxas de leitura/gravação por segundo. Essas informações são uma orientação para processos com E/S mais do que a identificação de problemas.
Nota: a `--human` opção pode ser usada para exibir números em formato legível por humanos (ou seja, `Kb`, , `Mb``GB`).

### `ps`

`ps` Por fim, o comando exibe os processos do sistema e pode ser classificado por CPU ou Memória.

Para ordenar por CPU e obter os 10 principais processos:

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

Para classificar `MEM%` e obter os 10 principais processos:

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

## Juntando tudo

Um script bash simples pode coletar todos os detalhes em uma única execução e anexar a saída a um arquivo para uso posterior:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2 && vmstat -w 1 5 && uptime && free -h && swapon && iostat -dxtm 1 1 && lsblk && ls -l /dev/disk/azure && pidstat 1 1 -h --human && pidstat -r 1 1 -h --human && pidstat -d 1 1 -h --human && ps aux --sort=-%cpu | head -20 && ps aux --sort=-%mem | head -20')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```

Para executar, você pode criar um arquivo com o conteúdo acima, adicionar permissões de execução executando `chmod +x gather.sh`e executar com `sudo ./gather.sh`.

Esse script salva a saída dos comandos em um arquivo localizado no mesmo diretório onde o script foi invocado.

Além disso, todos os comandos nos códigos de bloco bash abordados neste documento, podem ser executados usando `az-cli` a extensão run-command e analisando a saída para `jq` obter uma saída semelhante à execução dos comandos localmente: '

```azurecli-interactive
output=$(az vm run-command invoke -g $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "ls -l /dev/disk/azure")
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```