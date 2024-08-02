---
title: Linux sisteminden Performans ölçümleri alma
description: Linux sisteminden Performans ölçümlerini nasıl edineceğinizi öğrenin.
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

# Linux sisteminden Performans ölçümleri alma

**Şunlar için geçerlidir:** :heavy_check_mark: Linux VM'leri

Bu makalede, Bir Linux Sisteminden performans ölçümlerinin nasıl hızla alınacağını belirlemeye yönelik yönergeler ele alınacak.

Linux'ta performans sayaçlarını almak için kullanılabilecek çeşitli komutlar vardır. ve `uptime`gibi `vmstat` komutlar CPU kullanımı, Sistem Belleği ve Sistem yükü gibi genel sistem ölçümlerini sağlar.
Komutların çoğu varsayılan olarak zaten yüklüdür ve diğerleri varsayılan depolarda kullanılabilir durumdadır.
Komutlar aşağıdakilere ayrılabilir:

* CPU
* Bellek
* Disk G/Ç
* İşlemler

## Sysstat yardımcı programları yüklemesi

<!-- Commenting out these entries as this information should be selected by the user along with the corresponding subscription and region

The First step in this tutorial is to define environment variables, and install the corresponding package, if necessary.

```azurecli-interactive
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup89f292"
export MY_VM_NAME="myVM89f292"
```
-->

> [!NOTE]
> Tüm ilgili ayrıntıları toplayabilmek için bu komutlardan bazılarının çalıştırılması `root` gerekir.

> [!NOTE]
> Bazı komutlar, varsayılan olarak yüklenmemiş olabilecek paketin bir parçasıdır `sysstat` . Paket ile veya bu popüler dağıtımlar için kolayca yüklenebilir `sudo apt install sysstat``dnf install sysstat` `zypper install sysstat`.

Paketin `sysstat` bazı popüler Distro'lara yüklenmesi için tam komut şu şekildedir:

```bash
az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "/bin/bash -c 'OS=\$(cat /etc/os-release|grep NAME|head -1|cut -d= -f2 | sed \"s/\\\"//g\"); if [[ \$OS =~ \"Ubuntu\" ]] || [[ \$OS =~ \"Debian\" ]]; then sudo apt install sysstat -y; elif [[ \$OS =~ \"Red Hat\" ]]; then sudo dnf install sysstat -y; elif [[ \$OS =~ \"SUSE\" ]]; then sudo zypper install sysstat --non-interactive; else echo \"Unknown distribution\"; fi'"
```

## CPU

### <a id="mpstat"></a>mpstat

yardımcı `mpstat` programı paketin `sysstat` bir parçasıdır. CPU kullanımı ve ortalamaları başına görüntülenir ve bu da CPU kullanımını hızlı bir şekilde tanımlamaya yardımcı olur. `mpstat` kullanılabilir CPU'lar genelinde CPU kullanımına genel bir bakış sunarak kullanım bakiyesini ve tek bir CPU'nun yoğun yüklenip yüklenmediğini belirlemeye yardımcı olur.

Tam komut şöyledir:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Seçenekler ve bağımsız değişkenler şunlardır:

* `-P`: İstatistiklerin görüntüleneceği işlemciyi, ALL bağımsız değişkeni ise sistemdeki tüm çevrimiçi CPU'ların istatistiklerini görüntüleneceğini gösterir.
* `1`: İlk sayısal bağımsız değişken, saniyeler içinde ekranın ne sıklıkta yenileneceğini gösterir.
* `2`: İkinci sayısal bağımsız değişken, verilerin kaç kez yenilendiğini gösterir.

Komutun `mpstat` verileri görüntüleme sayısı, daha uzun veri toplama sürelerine uyum sağlamak için ikinci sayısal bağımsız değişken artırılarak değiştirilebilir. İdeal olarak 3 veya 5 saniye yeterlidir, çekirdek sayısı 2 saniye artan sistemlerde görüntülenen veri miktarını azaltmak için kullanılabilir.
Çıkıştan:

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

Dikkat edilmesi gereken birkaç önemli nokta vardır. İlk satırda yararlı bilgiler görüntülenir:

* Çekirdek ve yayın: `5.14.0-362.8.1.el9_3.x86_64`
* Ana bilgisayar adı: `alma9`
* Tarih: `02/21/24`
* Mimarlık: `_x86_64_`
* Toplam CPU miktarı (bu bilgiler diğer komutlardan elde edilen çıkışı yorumlamak için yararlıdır): `(8 CPU)`

Ardından, sütunların her birini açıklamak için CPU'lara yönelik ölçümler görüntülenir:

* `Time`: Örneğin toplandığı zaman
* `CPU`: CPU sayısal tanımlayıcısı olan ALL tanımlayıcısı, tüm CPU'lar için ortalamadır.
* `%usr`: Kullanıcı alanı, normalde kullanıcı uygulamaları için CPU kullanımı yüzdesi.
* `%nice`: Güzel (öncelik) değeri olan kullanıcı alanı işlemleri için CPU kullanımı yüzdesi.
* `%sys`: Çekirdek alanı işlemleri için CPU kullanımı yüzdesi.
* `%iowait`: Bekleyen G/Ç'yi beklerken boşta harcanan CPU süresinin yüzdesi.
* `%irq`: Donanım kesintilerine hizmet etmek için harcanan CPU süresinin yüzdesi.
* `%soft`: Yazılım kesintilerine hizmet etmek için harcanan CPU süresinin yüzdesi.
* `%steal`: Diğer sanal makinelere hizmet vermek için harcanan CPU süresinin yüzdesi (CPU'nun fazla sağlanması olmadığından Azure için geçerli değildir).
* `%guest`: Sanal CPU'lara hizmet vermek için harcanan CPU süresinin yüzdesi (Azure için geçerli değildir, yalnızca sanal makineleri çalıştıran çıplak sistemler için geçerlidir).
* `%gnice`: İyi bir değere sahip sanal CPU'lara hizmet vermek için harcanan CPU süresinin yüzdesi (Azure için geçerli değildir, yalnızca sanal makineleri çalıştıran çıplak sistemler için geçerlidir).
* `%idle`: Boşta ve G/Ç isteklerini beklemeden harcanan CPU süresinin yüzdesi.

#### Dikkate almak için gerekenler

için çıkışı `mpstat`gözden geçirirken göz önünde bulundurulması gereken bazı ayrıntılar:

* Tüm CPU'ların düzgün yüklendiğini ve tüm yükü tek bir CPU'nın sunmadığını doğrulayın. Bu bilgiler tek bir iş parçacıklı uygulamayı gösterebilir.
* ve arasında `%usr` `%sys` iyi durumda bir denge arayın; bunun tersi çekirdek işlemlerine hizmet etmekten daha fazla zaman harcanacağını gösterir.
* `%iowait` Yüksek değerlerin G/Ç isteklerini sürekli bekleyen bir sistemi gösterebileceği için yüzdeleri arayın.
* Yüksek kullanım yüksek `%soft` ağ trafiğini gösterebilir.

### `vmstat`

Yardımcı `vmstat` programı çoğu Linux dağıtımında yaygın olarak kullanılabilir, tek bir bölmede CPU, Bellek ve Disk G/Ç kullanımına üst düzey genel bakış sağlar.
komutu `vmstat` şu şekildedir:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'vmstat -w 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Seçenekler ve bağımsız değişkenler şunlardır:

* `-w`: Tutarlı sütunları korumak için geniş yazdırmayı kullanın.
* `1`: İlk sayısal bağımsız değişken, saniyeler içinde ekranın ne sıklıkta yenileneceğini gösterir.
* `5`: İkinci sayısal bağımsız değişken, verilerin kaç kez yenilendiğini gösterir.

Çıkış:

```output
--procs-- -----------------------memory---------------------- ---swap-- -----io---- -system-- --------cpu--------
   r    b         swpd         free         buff        cache   si   so    bi    bo   in   cs  us  sy  id  wa  st
  14    0            0     26059408          164       137468    0    0    89  3228   56  122   3   1  95   1   0
  14    1            0     24388660          164       145468    0    0     0  7811 3264 13870  76  24   0   0   0
  18    1            0     23060116          164       155272    0    0    44  8075 3704 15129  78  22   0   0   0
  18    1            0     21078640          164       165108    0    0   295  8837 3742 15529  73  27   0   0   0
  15    2            0     19015276          164       175960    0    0     9  8561 3639 15177  73  27   0   0   0
```

`vmstat` Çıktıyı altı gruba böler:

* `procs`: süreçler için istatistikler.
* `memory`: sistem belleği istatistikleri.
* `swap`: değiştirme istatistikleri.
* `io`: disk gç istatistikleri.
* `system`: bağlam anahtarları ve kesmeler için istatistikler.
* `cpu`: CPU kullanımı istatistikleri.

>Not: `vmstat` Sistemin tamamı (tüm CPU'lar, toplanan tüm blok cihazları) için genel istatistikleri gösterir.

#### `procs`

Bölümün `procs` iki sütunu vardır:

* `r`: Çalıştırma kuyruğundaki çalıştırılabilir işlemlerin sayısı.
* `b`: G/Ç beklerken engellenen işlemlerin sayısı.

Bu bölüm, sistemde herhangi bir performans sorunu olup olmadığını hemen gösterir. Sütunlardan herhangi birinde yer alan yüksek sayılar, kaynakları bekleyen işlemlerin sıraya ekli olduğunu gösterir.

sütunu, `r` CPU süresinin çalışabilmesini bekleyen işlem sayısını gösterir. Bu sayıyı yorumlamanın kolay bir yolu şu şekildedir: Kuyruktaki `r` işlem sayısı toplam CPU sayısından yüksekse, sistemde YOĞUN CPU yüklü olduğu ve çalıştırılmayı bekleyen tüm işlemler için CPU zamanı ayıramadığını tespit edebilirsiniz.

`b` sütunu, G/Ç istekleri tarafından engellenen çalıştırılmayı bekleyen işlemlerin sayısını gösterir. Bu sütundaki yüksek bir sayı, yüksek G/Ç ile karşılaşan bir sistemi gösterir ve tamamlanan G/Ç isteklerini bekleyen diğer işlemler nedeniyle işlemler çalıştırılamıyor. Bu da yüksek disk gecikme süresini gösterebilir.

#### `memory`

Bellek bölümünde dört sütun bulunur:

* `swpd`: Kullanılan tutar değiştirme belleği.
* `free`: Boş bellek miktarı.
* `buff`: Arabellekler için kullanılan bellek miktarı.
* `cache`: Önbellek için kullanılan bellek miktarı.

> [!NOTE]
> Değerler bayt cinsinden gösterilir.

Bu bölümde, bellek kullanımına üst düzey bir genel bakış sağlanır.

#### `swap`

Değiştirme bölümünde iki sütun vardır:

* `si`: Saniye başına değiştirilen bellek miktarı (sistem belleğinden takasa taşınır).
* `so`: Saniye başına ayrılan bellek miktarı (değiştirmeden sistem belleğine taşınır).

Yüksek `si` gözlemlenirse, sistem belleği tükenen ve sayfaları takasa (değiştirme) taşıyabilen bir sistemi temsil edebilir.

#### `io`

Bölümün `io` iki sütunu vardır:

* `bi`: Bir blok cihazından alınan blok sayısı (saniye başına blokları okur).
* `bo`: Bir blok cihazına saniyede gönderilen blok sayısı (saniye başına yazma).

> [!NOTE]
> Bu değerler saniye başına blok cinsindendir.

#### `system`

Bölümün `system` iki sütunu vardır:

* `in`: Saniye başına kesme sayısı.
* `cs`: Saniye başına bağlam anahtarı sayısı.

Saniye başına çok sayıda kesme, donanım cihazlarıyla (örneğin ağ işlemleri) meşgul olan bir sistemi gösterebilir.

Çok sayıda bağlam anahtarı, çok sayıda kısa çalışan işlemi olan meşgul bir sistemi gösterebilir; burada iyi veya kötü bir sayı yoktur.

#### `cpu`

Bu bölümde beş sütun vardır:

* `us`: Kullanıcı alanı yüzde kullanımı.
* `sy`: Sistem (çekirdek alanı) yüzde kullanımı.
* `id`: CPU'nun boşta olduğu sürenin yüzde kullanımı.
* `wa`: G/Ç ile işlemleri beklerken CPU'nun boşta olduğu sürenin kullanım yüzdesi.
* `st`: CPU'nun diğer sanal CPU'lara hizmet vermek için harcadığı sürenin kullanım yüzdesi (Azure için geçerli değildir).

Değerler yüzde olarak sunulur. Bu değerler yardımcı program tarafından sunulan değerlerle aynıdır ve CPU kullanımına `mpstat` üst düzey bir genel bakış sağlamaya hizmet eder. Bu değerleri gözden geçirirken "[Dikkate değer](#mpstat) şeyler" için `mpstat` benzer bir işlemi izleyin.

### `uptime`

Son olarak, CPU ile ilgili ölçümler için yardımcı program, `uptime` yük ortalaması değerleriyle sistem yüküne genel bir genel bakış sağlar.

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'uptime')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

```output
16:55:53 up 9 min,  2 users,  load average: 9.26, 2.91, 1.18
```

Yük ortalaması üç sayı görüntüler. Bu sayılar, `5` sistem yükünün dakika aralıkları ve `15` için geçerlidir`1`.

Bu değerleri yorumlamak için, sistemdeki kullanılabilir CPU sayısını bilmek önemlidir ve daha önce çıktıdan `mpstat` elde edilir. Değer toplam CPU'lara bağlıdır, bu nedenle çıkış örneği `mpstat` olarak sistemin 8 CPU'su vardır, yük ortalaması 8 ise TÜM çekirdeklerin %100'e yüklendiği anlamına gelir.

değeri `4` CPU'ların yarısının %100 (veya TÜM CPU'larda toplam %50 yük) yüklendiği anlamına gelir. Önceki çıktıda, yük ortalaması değeridir `9.26`, yani CPU yaklaşık %115 oranında yüklenir.

`1m`, `5m`, `15m` aralıkları, yükün zaman içinde artıp artmadığını veya azaldığını belirlemeye yardımcı olur.

> [NOT] `nproc` Komutu, CPU sayısını almak için de kullanılabilir.

## Bellek

Bellek için, kullanımla ilgili ayrıntıları edinebilen iki komut vardır.

### `free`

`free` komutu sistem belleği kullanımını gösterir.

Çalıştırmak için:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'free -h')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Seçenekler ve bağımsız değişkenler şunlardır:

* `-h`: Değerleri dinamik olarak okunabilir olarak görüntüler (örneğin: Mib, Gib, Tib)

Çıkış:

```output
               total        used        free      shared  buff/cache   available
Mem:            31Gi        19Gi        12Gi        23Mi        87Mi        11Gi
Swap:           23Gi          0B        23Gi
```

Çıktıdan toplam sistem belleği ile kullanılabilir bellek ve kullanılan ile toplam değiştirme karşılaştırmasını bulun. Kullanılabilir bellek, kullanıcı uygulamaları için döndürülebilen önbellek için ayrılan belleği dikkate alır.

Bazı daha az kullanılan bellek sayfaları takasa taşınaabildiği için bazı takas kullanımı modern çekirdeklerde normaldir.

### `swapon`

Komut, `swapon` değiştirmenin yapılandırıldığı yeri ve değiştirme cihazlarının veya dosyalarının ilgili önceliklerini görüntüler.

Komutunu çalıştırmak için:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'swapon -s')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Çıkış:

```output
Filename      Type          Size          Used   Priority
/dev/zram0    partition     16G           0B      100
/mnt/swapfile file          8G            0B      -2
```

Bu bilgiler, değiştirme işleminin ideal olmayan bir konumda (örneğin, bir veride veya işletim sistemi diskinde) yapılandırılıp yapılandırılmadığını doğrulamak için önemlidir. Azure başvuru çerçevesinde, en iyi performansı sağladığından kısa ömürlü sürücüde değiştirme yapılandırılmalıdır.

### Dikkate almak için gerekenler

* Belleğin sınırlı bir kaynak olduğunu unutmayın; hem sistem belleği (RAM) hem de değiştirme işlemi tükendikten sonra, işlemler Ezber Dışı katil (OOM) tarafından öldürülür.
* Değiştirme işleminin veri diskinde veya işletim sistemi diskinde yapılandırılmadığını doğrulayın çünkü bu, gecikme süresi farkları nedeniyle G/Ç ile ilgili sorunlar oluşturur. Değiştirme kısa ömürlü sürücüde yapılandırılmalıdır.
* Çıkışta `free -h` boş değerlerin sıfıra yakın olduğunu görmenin yaygın olduğunu da göz önünde bulundurun; bu davranış sayfa önbelleğinden kaynaklanır ve çekirdek bu sayfaları gerektiği gibi serbest bırakır.

## G/Ç

Disk G/Ç, diskler gecikme sürelerine ulaşaabildiği `100ms+` için Azure'ın kısıtlandığında en çok acı çektiği alanlardan biridir. Aşağıdaki komutlar bu senaryoları tanımlamaya yardımcı olur.

### `iostat`

yardımcı `iostat` programı paketin `sysstat` bir parçasıdır. Blok cihaz kullanımı istatistiklerini görüntüler ve blokla ilgili performans sorunlarını belirlemeye yardımcı olur.

yardımcı `iostat` programı aktarım hızı, gecikme süresi ve kuyruk boyutu gibi ölçümler için ayrıntılar sağlar. Bu ölçümler, disk G/Ç'nin sınırlayıcı bir faktör olup olmadığını anlamanıza yardımcı olur.
Çalıştırmak için komutunu kullanın:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'iostat -dxtm 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Seçenekler ve bağımsız değişkenler şunlardır:

* `-d`: Cihaz kullanım raporu başına.
* `-x`: Genişletilmiş istatistikler.
* `-t`: Her rapor için zaman damgasını görüntüleyin.
* `-m`: MB/sn cinsinden görüntülenir.
* `1`: İlk sayısal bağımsız değişken, saniyeler içinde ekranın ne sıklıkta yenileneceğini gösterir.
* `2`: İkinci sayısal bağımsız değişken, verilerin kaç kez yenilendiğini gösterir.

Çıkış:

```output
Linux 5.14.0-362.8.1.el9_3.x86_64 (alma9)       02/21/24        _x86_64_        (8 CPU)

02/21/24 16:55:50
Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
sda              1.07      0.02     0.00   0.00    1.95    20.40   23.25     24.55     3.30  12.42  113.75  1081.06    0.26    537.75     0.26  49.83    0.03 2083250.04    0.00    0.00    2.65   2.42
sdb             16.99      0.67     0.36   2.05    2.00    40.47   65.26      0.44     1.55   2.32    1.32     6.92    0.00      0.00     0.00   0.00    0.00     0.00   30.56    1.30    0.16   7.16
zram0            0.51      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.00   0.00

```

Çıktının önemli olmayan birkaç sütunu vardır (seçenek nedeniyle `-x` ek sütunlar), önemli sütunlardan bazıları şunlardır:

* `r/s`: Saniye başına okuma işlemleri (IOPS).
* `rMB/s`: Saniyede megabayt okuma.
* `r_await`: Gecikme süresini milisaniye cinsinden okuma.
* `rareq-sz`: Kilobayt cinsinden ortalama okuma isteği boyutu.
* `w/s`: Saniye başına yazma işlemleri (IOPS).
* `wMB/s`: Saniye başına megabayt yazın.
* `w_await`: Milisaniye cinsinden yazma gecikme süresi.
* `wareq-size`: Kilobayt cinsinden ortalama yazma isteği boyutu.
* `aqu-sz`: Ortalama kuyruk boyutu.

#### Dikkate almak için gerekenler

* ve `w/s` (IOPS) `rMB/s` ve değerlerini arayın `r/s` ve `wMB/s` bu değerlerin belirtilen diskin sınırları içinde olduğunu doğrulayın. Değerler sınırlara yakın veya daha yüksekse disk kısıtlanacak ve yüksek gecikme süresine neden olacaktır. Bu bilgiler, 'den alınan `%iowait` `mpstat`ölçümle de ilişkilendirilebilir.
* Gecikme süresi, diskin beklendiği gibi çalıştığını doğrulamak için mükemmel bir ölçümdür. Normalde, PremiumSSD için beklenen gecikme süresinden `9ms` daha azdır, diğer teklifler farklı gecikme süresi hedeflerine sahiptir.
* Kuyruk boyutu, doygunluğun harika bir göstergesidir. Normalde istekler gerçek zamanlıya yakın bir şekilde sunulur ve sayı bire yakın kalır (kuyruk hiç artmadıkça). Daha yüksek bir sayı disk doygunluğunu gösterebilir (yani istekler sıraya alınır). Bu ölçüm için iyi veya kötü sayı yoktur. Birden yüksek bir şeyin isteklerin kuyruğa alma anlamına geldiğini anlamak, disk doygunluğu olup olmadığını belirlemenize yardımcı olur.

### `lsblk`

Yardımcı `lsblk` program, sisteme bağlı blok cihazlarını gösterir, ancak performans ölçümleri sağlamaz, ancak bu cihazların nasıl yapılandırıldığına ve hangi bağlama noktalarının kullanıldığına hızlı bir genel bakış sağlar.

Çalıştırmak için komutunu kullanın:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'lsblk')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Çıkış:

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

#### Dikkate almak için gerekenler

* Cihazların nereye monte edildiğine bakın.
* Değiştir seçeneğinin etkinse veri diskinin veya işletim sistemi diskinin içinde yapılandırılmadığını doğrulayın.

> Not: Blok cihazını Azure'daki bir LUN ile ilişkilendirmenin kolay bir yolu komutunu çalıştırmaktır `ls -lr /dev/disk/azure`.

## İşlem

İşlem başına ayrıntıların toplanması, sistemin yükünün nereden geldiğini anlamanıza yardımcı olur.

İşlem statiklerini toplamanın ana yardımcı programı CPU, Bellek ve G/Ç istatistikleri için işlem başına ayrıntıları sağlamasıdır `pidstat` .

Son olarak, en yüksek CPU'ya göre sıralamak kolay `ps` bir işlemdir ve bellek kullanımı ölçümleri tamamlar.

> [!NOTE]
> Bu komutlar çalıştırma işlemleriyle ilgili ayrıntıları görüntülediğinden, ile `sudo`kök olarak çalıştırılması gerekir. Bu komut, yalnızca kullanıcının değil tüm işlemlerin görüntülenmesini sağlar.

### `pidstat`

Yardımcı `pidstat` programı da paketin `sysstat` bir parçasıdır. Belirli bir süre için ölçümlerin görüntülendiği or iostat gibi `mpstat` bir durumdur. Varsayılan olarak, `pidstat` yalnızca etkinliği olan işlemler için ölçümleri görüntüler.

`pidstat` için bağımsız değişkenler diğer `sysstat` yardımcı programlar için aynıdır:

* 1: İlk sayısal bağımsız değişken, saniyeler içinde ekranın ne sıklıkta yenileneceğini gösterir.
* 2: İkinci sayısal bağımsız değişken, verilerin kaç kez yenilendiğini gösterir.

> [!NOTE]
> Etkinliği olan birçok işlem varsa çıkış önemli ölçüde büyüyebilir.

#### cpu istatistiklerini işleme

İşlem CPU istatistiklerini toplamak için herhangi bir seçenek olmadan çalıştırın `pidstat` :

Azure CLI'dan yürütmek istiyorsanız aşağıdaki komutlar kullanılabilir:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Çıkış:

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

Komut , , `%guest` `%system`(Azure için geçerli değildir) `%wait`ve toplam `%CPU` kullanım için `%usr`işlem başına kullanımı görüntüler.

##### Dikkate almak için gerekenler

* G/Ç beklerken engellenen ve disk doygunluğunu da gösterebilecek işlemleri gösterdiği için yüksek %wait (iowait) yüzdesine sahip işlemleri arayın.
* Tek bir iş parçacıklı uygulamayı gösterebileceğinden tek bir işlemin CPU'nun %100'ünün tüketildiğini doğrulayın.

#### İşlem Belleği istatistikleri

İşlem belleği istatistiklerini toplamak için şu `-r` seçeneği kullanın:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -r 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Çıkış:

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

Toplanan ölçümler şunlardır:

* `minflt/s`: Saniye başına küçük hatalar, bu ölçüm sistem belleğinden (RAM) yüklenen sayfa sayısını gösterir.
* `mjflt/s`: Saniye başına önemli hatalar, bu ölçüm diskten yüklenen sayfa sayısını (SWAP) gösterir.
* `VSZ`: Bayt cinsinden kullanılan sanal bellek.
* `RSS`: Bayt cinsinden kullanılan yerleşik bellek (gerçek ayrılan bellek).
* `%MEM`: Kullanılan toplam belleğin yüzdesi.
* `Command`: İşlemin adı.

##### Dikkate almak için gerekenler

* Bu değer sayfaları diske veya diskten değiştirmeye yönelik bir işlemi gösterdiğinden saniye başına önemli hataları arayın. Bu davranış bellek tükenmesini gösterebilir ve daha yavaş değiştirme nedeniyle olaylara `OOM` veya performans düşüşlerine yol açabilir.
* Tek bir işlemin kullanılabilir belleğin %100'ünün tüketildiğini doğrulayın. Bu davranış bir bellek sızıntısına işaret edebilir.

> [!NOTE]
> `--human` seçeneği, sayıları okunabilir biçimde (, `Kb`, , `Mb``GB`) görüntülemek için kullanılabilir.

#### G/Ç istatistiklerini işleme

İşlem belleği istatistiklerini toplamak için şu `-d` seçeneği kullanın:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -d 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Çıkış:

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

Toplanan ölçümler şunlardır:

* `kB_rd/s`: Saniyede kilobayt okuma.
* `kB_wr/s`: Saniye başına kilobayt yazın.
* `Command`: İşlemin adı.

##### Dikkate almak için gerekenler

* Saniyede yüksek okuma/yazma oranlarına sahip tek işlemleri arayın. Bu bilgiler, sorunları tanımlamaktan çok G/Ç işlemlerine yönelik bir kılavuzdur.
Not: `--human` bu seçenek, sayıları okunabilir biçimde (yani `Kb`, , `Mb``GB`) görüntülemek için kullanılabilir.

### `ps`

Son olarak `ps` komut sistem işlemlerini görüntüler ve CPU veya Belleğe göre sıralanabilir.

CPU'ya göre sıralamak ve ilk 10 işlemi elde etmek için:

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

Sıralama ölçütü `MEM%` olarak ve ilk 10 işlemi elde etmek için:

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

## Hepsini bir araya getirmek

Basit bir bash betiği tüm ayrıntıları tek bir çalıştırmada toplayabilir ve çıkışı daha sonra kullanmak üzere bir dosyaya ekleyebilir:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2 && vmstat -w 1 5 && uptime && free -h && swapon && iostat -dxtm 1 1 && lsblk && ls -l /dev/disk/azure && pidstat 1 1 -h --human && pidstat -r 1 1 -h --human && pidstat -d 1 1 -h --human && ps aux --sort=-%cpu | head -20 && ps aux --sort=-%mem | head -20')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```

Çalıştırmak için yukarıdaki içeriklerle bir dosya oluşturabilir, komutunu çalıştırarak `chmod +x gather.sh`yürütme izinleri ekleyebilir ve ile `sudo ./gather.sh`komutunu çalıştırabilirsiniz.

Bu betik, komutların çıkışını betiğin çağrıldığı dizinde bulunan bir dosyaya kaydeder.

Ayrıca, bu belgede ele alınan bash blok kodlarındaki tüm komutlar run-command uzantısı kullanılarak çalıştırılabilir `az-cli` ve komutları yerel olarak çalıştırmaya benzer bir çıkış elde etmek için çıkışı ayrıştırabilir `jq` : '

```azurecli-interactive
output=$(az vm run-command invoke -g $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "ls -l /dev/disk/azure")
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```