---
title: Mendapatkan metrik Performa dari sistem Linux
description: Pelajari cara mendapatkan metrik Performa dari sistem Linux.
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

# Mendapatkan metrik Performa dari sistem Linux

**Berlaku untuk:** :heavy_check_mark: VM Linux

Artikel ini akan membahas instruksi untuk menentukan cara mendapatkan metrik performa dengan cepat dari Sistem Linux.

Ada beberapa perintah yang dapat digunakan untuk mendapatkan penghitung kinerja di Linux. Perintah seperti `vmstat` dan `uptime`, menyediakan metrik sistem umum seperti penggunaan CPU, Memori Sistem, dan beban Sistem.
Sebagian besar perintah sudah diinstal secara default dengan yang lain tersedia di repositori default.
Perintah dapat dipisahkan menjadi:

* CPU
* Memori
* Disk I/O
* Proses

## Penginstalan utilitas Sysstat

<!-- Commenting out these entries as this information should be selected by the user along with the corresponding subscription and region

The First step in this tutorial is to define environment variables, and install the corresponding package, if necessary.

```azurecli-interactive
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup89f292"
export MY_VM_NAME="myVM89f292"
```
-->

> [!NOTE]
> Beberapa perintah ini perlu dijalankan `root` agar dapat mengumpulkan semua detail yang relevan.

> [!NOTE]
> Beberapa perintah adalah bagian `sysstat` dari paket yang mungkin tidak diinstal secara default. Paket dapat dengan mudah diinstal dengan `sudo apt install sysstat`, `dnf install sysstat` atau `zypper install sysstat` untuk distro populer tersebut.

Perintah lengkap untuk penginstalan `sysstat` paket pada beberapa Distro populer adalah:

```bash
az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "/bin/bash -c 'OS=\$(cat /etc/os-release|grep NAME|head -1|cut -d= -f2 | sed \"s/\\\"//g\"); if [[ \$OS =~ \"Ubuntu\" ]] || [[ \$OS =~ \"Debian\" ]]; then sudo apt install sysstat -y; elif [[ \$OS =~ \"Red Hat\" ]]; then sudo dnf install sysstat -y; elif [[ \$OS =~ \"SUSE\" ]]; then sudo zypper install sysstat --non-interactive; else echo \"Unknown distribution\"; fi'"
```

## CPU

### <a id="mpstat"></a>mpstat

Utilitas `mpstat` adalah bagian `sysstat` dari paket. Ini menampilkan pemanfaatan dan rata-rata CPU, yang berguna untuk mengidentifikasi penggunaan CPU dengan cepat. `mpstat` memberikan gambaran umum pemanfaatan CPU di seluruh CPU yang tersedia, membantu mengidentifikasi saldo penggunaan dan jika satu CPU sangat dimuat.

Perintah lengkapnya adalah:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Opsi dan argumennya adalah:

* `-P`: Menunjukkan prosesor untuk menampilkan statistik, argumen ALL menunjukkan untuk menampilkan statistik untuk semua CPU online dalam sistem.
* `1`: Argumen numerik pertama menunjukkan seberapa sering untuk me-refresh tampilan dalam hitung detik.
* `2`: Argumen numerik kedua menunjukkan berapa kali data di-refresh.

Frekuensi `mpstat` perintah menampilkan data dapat diubah dengan meningkatkan argumen numerik kedua untuk mengakomodasi untuk waktu pengumpulan data yang lebih lama. Idealnya 3 atau 5 detik sudah cukup, untuk sistem dengan jumlah inti yang ditingkatkan 2 detik dapat digunakan untuk mengurangi jumlah data yang ditampilkan.
Dari output:

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

Ada beberapa hal penting yang perlu diperhatikan. Baris pertama menampilkan informasi yang berguna:

* Kernel dan rilis: `5.14.0-362.8.1.el9_3.x86_64`
* Nama host: `alma9`
* Tanggal: `02/21/24`
* Arsitektur: `_x86_64_`
* Jumlah total CPU (informasi ini berguna untuk menginterpretasikan output dari perintah lain): `(8 CPU)`

Kemudian metrik untuk CPU ditampilkan, untuk menjelaskan setiap kolom:

* `Time`: Waktu sampel dikumpulkan
* `CPU`: Pengidentifikasi numerik CPU, pengidentifikasi ALL adalah rata-rata untuk semua CPU.
* `%usr`: Persentase pemanfaatan CPU untuk ruang pengguna, biasanya aplikasi pengguna.
* `%nice`: Persentase pemanfaatan CPU untuk proses ruang pengguna dengan nilai (prioritas) yang bagus.
* `%sys`: Persentase pemanfaatan CPU untuk proses ruang kernel.
* `%iowait`: Persentase waktu CPU yang dihabiskan diam menunggu I/O yang luar biasa.
* `%irq`: Persentase waktu CPU yang dihabiskan untuk melayani gangguan perangkat keras.
* `%soft`: Persentase waktu CPU yang dihabiskan untuk melayani interupsi perangkat lunak.
* `%steal`: Persentase waktu CPU yang dihabiskan untuk melayani komputer virtual lainnya (tidak berlaku untuk Azure karena tidak ada provisi CPU yang berlebihan).
* `%guest`: Persentase waktu CPU yang dihabiskan untuk melayani CPU virtual (tidak berlaku untuk Azure, hanya berlaku untuk sistem bare metal yang menjalankan komputer virtual).
* `%gnice`: Persentase waktu CPU yang dihabiskan untuk melayani CPU virtual dengan nilai yang bagus (tidak berlaku untuk Azure, hanya berlaku untuk sistem bare metal yang menjalankan komputer virtual).
* `%idle`: Persentase waktu CPU dihabiskan diam, dan tanpa menunggu permintaan I/O.

#### Hal-hal yang harus diwaspadai

Beberapa detail yang perlu diingat saat meninjau output untuk `mpstat`:

* Verifikasi bahwa semua CPU dimuat dengan benar dan tidak satu CPU melayani semua beban. Informasi ini dapat menunjukkan satu aplikasi utas.
* Cari keseimbangan yang sehat antara `%usr` dan `%sys` karena sebaliknya akan menunjukkan lebih banyak waktu yang dihabiskan pada beban kerja aktual daripada melayani proses kernel.
* Cari `%iowait` persentase sebagai nilai tinggi dapat menunjukkan sistem yang terus menunggu permintaan I/O.
* Penggunaan tinggi `%soft` dapat menunjukkan lalu lintas jaringan yang tinggi.

### `vmstat`

`vmstat` Utilitas ini tersedia secara luas di sebagian besar distribusi Linux, ini memberikan gambaran umum tingkat tinggi untuk pemanfaatan CPU, Memori, dan I/O Disk dalam satu panel.
Perintah untuk `vmstat` adalah:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'vmstat -w 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Opsi dan argumennya adalah:

* `-w`: Gunakan pencetakan lebar untuk mempertahankan kolom yang konsisten.
* `1`: Argumen numerik pertama menunjukkan seberapa sering untuk me-refresh tampilan dalam hitung detik.
* `5`: Argumen numerik kedua menunjukkan berapa kali data di-refresh.

Outputnya:

```output
--procs-- -----------------------memory---------------------- ---swap-- -----io---- -system-- --------cpu--------
   r    b         swpd         free         buff        cache   si   so    bi    bo   in   cs  us  sy  id  wa  st
  14    0            0     26059408          164       137468    0    0    89  3228   56  122   3   1  95   1   0
  14    1            0     24388660          164       145468    0    0     0  7811 3264 13870  76  24   0   0   0
  18    1            0     23060116          164       155272    0    0    44  8075 3704 15129  78  22   0   0   0
  18    1            0     21078640          164       165108    0    0   295  8837 3742 15529  73  27   0   0   0
  15    2            0     19015276          164       175960    0    0     9  8561 3639 15177  73  27   0   0   0
```

`vmstat` membagi output dalam enam grup:

* `procs`: statistik untuk proses.
* `memory`: statistik untuk memori sistem.
* `swap`: statistik untuk pertukaran.
* `io`: statistik untuk disk io.
* `system`: statistik untuk sakelar konteks dan interupsi.
* `cpu`: statistik untuk penggunaan CPU.

>Catatan: `vmstat` menunjukkan statistik keseluruhan untuk seluruh sistem (yaitu, semua CPU, semua perangkat blok dikumpulkan).

#### `procs`

Bagian `procs` ini memiliki dua kolom:

* `r`: Jumlah proses yang dapat dijalankan dalam antrean eksekusi.
* `b`: Jumlah proses yang diblokir menunggu I/O.

Bagian ini segera menunjukkan apakah ada hambatan pada sistem. Angka tinggi pada salah satu kolom menunjukkan proses antrean menunggu sumber daya.

Kolom `r` menunjukkan jumlah proses yang menunggu waktu CPU untuk dapat dijalankan. Cara mudah untuk menginterpretasikan angka ini adalah sebagai berikut: jika jumlah proses dalam `r` antrean lebih tinggi dari jumlah total CPU, maka dapat disimpulkan bahwa sistem memiliki CPU yang sangat dimuat, dan tidak dapat mengalokasikan waktu CPU untuk semua proses yang menunggu untuk dijalankan.

Kolom `b` menunjukkan jumlah proses yang menunggu untuk dijalankan yang sedang diblokir oleh permintaan I/O. Angka tinggi dalam kolom ini akan menunjukkan sistem yang mengalami I/O tinggi, dan proses tidak dapat berjalan karena proses lain yang menunggu permintaan I/O selesai. Yang juga dapat menunjukkan latensi disk yang tinggi.

#### `memory`

Bagian memori memiliki empat kolom:

* `swpd`: Jumlah memori pertukaran yang digunakan.
* `free`: Jumlah memori bebas.
* `buff`: Jumlah memori yang digunakan untuk buffer.
* `cache`: Jumlah memori yang digunakan untuk cache.

> [!NOTE]
> Nilai diperlihatkan dalam byte.

Bagian ini memberikan gambaran umum penggunaan memori tingkat tinggi.

#### `swap`

Bagian pertukaran memiliki dua kolom:

* `si`: Jumlah memori yang ditukar (dipindahkan dari memori sistem ke pertukaran) per detik.
* `so`: Jumlah memori yang ditukar (dipindahkan dari pertukaran ke memori sistem) per detik.

Jika tinggi `si` diamati, mungkin mewakili sistem yang kehabisan memori sistem dan memindahkan halaman untuk bertukar (bertukar).

#### `io`

Bagian `io` ini memiliki dua kolom:

* `bi`: Jumlah blok yang diterima dari perangkat blok (membaca blok per detik) per detik.
* `bo`: Jumlah blok yang dikirim ke perangkat blok (tulis per detik) per detik.

> [!NOTE]
> Nilai-nilai ini berada dalam blok per detik.

#### `system`

Bagian `system` ini memiliki dua kolom:

* `in`: Jumlah interupsi per detik.
* `cs`: Jumlah sakelar konteks per detik.

Sejumlah besar gangguan per detik mungkin menunjukkan sistem yang sibuk dengan perangkat keras (misalnya operasi jaringan).

Sejumlah besar sakelar konteks mungkin menunjukkan sistem sibuk dengan banyak proses yang berjalan singkat, tidak ada angka yang baik atau buruk di sini.

#### `cpu`

Bagian ini memiliki lima kolom:

* `us`: Pemanfaatan persen ruang pengguna.
* `sy`: Pemanfaatan persen sistem (ruang kernel).
* `id`: Pemanfaatan persen dari jumlah waktu CPU diam.
* `wa`: Pemanfaatan persen dari jumlah waktu CPU menganggur menunggu proses dengan I/O.
* `st`: Pemanfaatan persen dari jumlah waktu yang dihabiskan CPU untuk melayani CPU virtual lainnya (tidak berlaku untuk Azure).

Nilai disajikan dalam persentase. Nilai-nilai ini sama dengan yang disajikan oleh `mpstat` utilitas dan berfungsi untuk memberikan gambaran umum penggunaan CPU tingkat tinggi. Ikuti proses serupa untuk "[Hal-hal yang perlu diwaspadai](#mpstat)" `mpstat` saat meninjau nilai-nilai ini.

### `uptime`

Terakhir, untuk metrik terkait CPU, `uptime` utilitas memberikan gambaran umum yang luas tentang beban sistem dengan nilai rata-rata beban.

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'uptime')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

```output
16:55:53 up 9 min,  2 users,  load average: 9.26, 2.91, 1.18
```

Rata-rata beban menampilkan tiga angka. Angka-angka ini untuk `1``5` , dan `15` interval menit beban sistem.

Untuk menafsirkan nilai-nilai ini, penting untuk mengetahui jumlah CPU yang tersedia dalam sistem, yang diperoleh dari `mpstat` output sebelumnya. Nilai tergantung pada total CPU, sehingga sebagai contoh `mpstat` output sistem memiliki 8 CPU, rata-rata beban 8 berarti bahwa SEMUA inti dimuat ke 100%.

Nilai `4` berarti bahwa setengah dari CPU dimuat pada 100% (atau total beban 50% pada SEMUA CPU). Pada output sebelumnya, rata-rata beban adalah `9.26`, yang berarti CPU dimuat sekitar 115%.

`1m`Interval , `5m`, `15m` membantu mengidentifikasi apakah beban meningkat atau menurun dari waktu ke waktu.

> [CATATAN] `nproc` Perintah juga dapat digunakan untuk mendapatkan jumlah CPU.

## Memori

Untuk memori, ada dua perintah yang dapat memperoleh detail tentang penggunaan.

### `free`

Perintah menunjukkan `free` pemanfaatan memori sistem.

Untuk menjalankannya:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'free -h')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Opsi dan argumennya adalah:

* `-h`: Menampilkan nilai secara dinamis sebagai dapat dibaca manusia (misalnya: Mib, Gib, Tib)

Outputnya:

```output
               total        used        free      shared  buff/cache   available
Mem:            31Gi        19Gi        12Gi        23Mi        87Mi        11Gi
Swap:           23Gi          0B        23Gi
```

Dari output, cari total memori sistem vs yang tersedia, dan pertukaran total yang digunakan vs total. Memori yang tersedia mempertimbangkan memori yang dialokasikan untuk cache, yang dapat dikembalikan untuk aplikasi pengguna.

Beberapa penggunaan pertukaran normal dalam kernel modern karena beberapa halaman memori yang kurang sering digunakan dapat dipindahkan ke pertukaran.

### `swapon`

Perintah `swapon` menampilkan tempat pertukaran dikonfigurasi dan prioritas masing-masing dari perangkat atau file pertukaran.

Untuk menjalankan perintah:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'swapon -s')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Outputnya:

```output
Filename      Type          Size          Used   Priority
/dev/zram0    partition     16G           0B      100
/mnt/swapfile file          8G            0B      -2
```

Informasi ini penting untuk memverifikasi apakah pertukaran dikonfigurasi pada lokasi yang tidak ideal, misalnya pada data atau disk OS. Dalam bingkai referensi Azure, pertukaran harus dikonfigurasi pada drive sementara karena memberikan performa terbaik.

### Hal-hal yang harus diwaspadai

* Perlu diingat memori adalah sumber daya terbatas, setelah memori sistem (RAM) dan pertukaran habis, prosesnya akan dimatikan oleh pembunuh Out Of Memorry (OOM).
* Pastikan pertukaran tidak dikonfigurasi pada disk data atau disk OS, karena itu akan membuat masalah dengan I/O karena perbedaan latensi. Pertukaran harus dikonfigurasi pada drive ephemeral.
* Perhatikan juga bahwa umum untuk melihat output `free -h` bahwa nilai gratis mendekati nol, perilaku ini disebabkan oleh cache halaman, kernel merilis halaman tersebut sesuai kebutuhan.

## I/O

I/O Disk adalah salah satu area yang paling diderita Azure saat dibatasi, karena disk dapat mencapai `100ms+` latensi. Perintah berikut membantu mengidentifikasi skenario ini.

### `iostat`

Utilitas `iostat` adalah bagian `sysstat` dari paket. Ini menampilkan statistik penggunaan perangkat per blok dan membantu mengidentifikasi masalah performa terkait blok.

`iostat` Utilitas ini menyediakan detail untuk metrik seperti throughput, latensi, dan ukuran antrean. Metrik ini membantu memahami apakah I/O disk menjadi faktor pembatas.
Untuk menjalankan, gunakan perintah :

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'iostat -dxtm 1 5')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Opsi dan argumennya adalah:

* `-d`: Per laporan penggunaan perangkat.
* `-x`: Statistik yang diperluas.
* `-t`: Tampilkan tanda waktu untuk setiap laporan.
* `-m`: Tampilkan dalam MB/dtk.
* `1`: Argumen numerik pertama menunjukkan seberapa sering untuk me-refresh tampilan dalam hitung detik.
* `2`: Argumen numerik kedua menunjukkan berapa kali data di-refresh.

Outputnya:

```output
Linux 5.14.0-362.8.1.el9_3.x86_64 (alma9)       02/21/24        _x86_64_        (8 CPU)

02/21/24 16:55:50
Device            r/s     rMB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wMB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dMB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
sda              1.07      0.02     0.00   0.00    1.95    20.40   23.25     24.55     3.30  12.42  113.75  1081.06    0.26    537.75     0.26  49.83    0.03 2083250.04    0.00    0.00    2.65   2.42
sdb             16.99      0.67     0.36   2.05    2.00    40.47   65.26      0.44     1.55   2.32    1.32     6.92    0.00      0.00     0.00   0.00    0.00     0.00   30.56    1.30    0.16   7.16
zram0            0.51      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     4.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.00   0.00

```

Output memiliki beberapa kolom yang tidak penting (kolom tambahan karena `-x` opsi ), beberapa kolom penting adalah:

* `r/s`: Membaca operasi per detik (IOPS).
* `rMB/s`: Baca megabyte per detik.
* `r_await`: Membaca latensi dalam milidetik.
* `rareq-sz`: Ukuran permintaan baca rata-rata dalam kilobyte.
* `w/s`: Operasi tulis per detik (IOPS).
* `wMB/s`: Tulis megabyte per detik.
* `w_await`: Tulis latensi dalam milidetik.
* `wareq-size`: Ukuran permintaan tulis rata-rata dalam kilobyte.
* `aqu-sz`: Ukuran antrean rata-rata.

#### Hal-hal yang harus diwaspadai

* Cari `r/s` dan `w/s` (IOPS) dan `rMB/s` dan dan `wMB/s` verifikasi bahwa nilai-nilai ini berada dalam batas disk yang diberikan. Jika nilai mendekati atau lebih tinggi batasnya, disk akan dibatasi, yang mengarah ke latensi tinggi. Informasi ini juga dapat dikuatkan dengan `%iowait` metrik dari `mpstat`.
* Latensi adalah metrik yang sangat baik untuk memverifikasi apakah disk berfungsi seperti yang diharapkan. Biasanya, kurang dari `9ms` latensi yang diharapkan untuk PremiumSSD, penawaran lain memiliki target latensi yang berbeda.
* Ukuran antrean adalah indikator jenuh yang bagus. Biasanya, permintaan akan dilayani mendekati real time dan jumlahnya tetap dekat dengan satu (karena antrean tidak pernah tumbuh). Angka yang lebih tinggi dapat menunjukkan saturasi disk (yaitu, permintaan mengantre). Tidak ada angka yang baik atau buruk untuk metrik ini. Memahami bahwa apa pun yang lebih tinggi dari satu berarti bahwa permintaan mengantre membantu menentukan apakah ada saturasi disk.

### `lsblk`

`lsblk` Utilitas menunjukkan perangkat blok yang melekat pada sistem, meskipun tidak menyediakan metrik performa, utilitas ini memungkinkan gambaran umum singkat tentang bagaimana perangkat ini dikonfigurasi dan titik pemasangan mana yang digunakan.

Untuk menjalankan, gunakan perintah :

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'lsblk')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Outputnya:

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

#### Hal-hal yang harus diwaspadai

* Cari tempat perangkat dipasang.
* Verifikasi bahwa swap tidak dikonfigurasi di dalam disk data atau disk OS, jika diaktifkan.

> Catatan: Cara mudah untuk menghubungkan perangkat blok dengan LUN di Azure adalah dengan menjalankan `ls -lr /dev/disk/azure`.

## Proses

Mengumpulkan detail berdasarkan per proses membantu memahami dari mana beban sistem berasal.

Utilitas utama untuk mengumpulkan statis proses adalah `pidstat` karena menyediakan detail per proses untuk statistik CPU, Memori, dan I/O.

Terakhir, proses yang mudah `ps` diurutkan berdasarkan CPU teratas, dan penggunaan memori menyelesaikan metrik.

> [!NOTE]
> Karena perintah ini menampilkan detail tentang proses yang sedang berjalan, perintah tersebut perlu dijalankan sebagai root dengan `sudo`. Perintah ini memungkinkan semua proses ditampilkan dan bukan hanya pengguna.

### `pidstat`

Utilitas `pidstat` juga merupakan bagian `sysstat` dari paket. Ini seperti `mpstat` atau iostat di mana ia menampilkan metrik untuk jumlah waktu tertentu. Secara default, `pidstat` hanya menampilkan metrik untuk proses dengan aktivitas.

Argumen untuk `pidstat` sama untuk utilitas lain `sysstat` :

* 1: Argumen numerik pertama menunjukkan seberapa sering untuk me-refresh tampilan dalam detik.
* 2: Argumen numerik kedua menunjukkan berapa kali data di-refresh.

> [!NOTE]
> Output dapat tumbuh cukup besar jika ada banyak proses dengan aktivitas.

#### Memproses statistik CPU

Untuk mengumpulkan statistik CPU proses, jalankan `pidstat` tanpa opsi apa pun:

Perintah berikut dapat digunakan jika Anda ingin menjalankannya dari Azure CLI:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Outputnya:

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

Perintah menampilkan penggunaan per proses untuk `%usr`, , `%guest` `%system`(tidak berlaku untuk Azure), `%wait`, dan total `%CPU` penggunaan.

##### Hal-hal yang harus diwaspadai

* Cari proses dengan persentase %wait (iowait) tinggi karena mungkin menunjukkan proses yang diblokir menunggu I/O, yang mungkin juga menunjukkan saturasi disk.
* Verifikasi bahwa tidak ada satu proses pun yang mengonsumsi 100% CPU karena mungkin menunjukkan satu aplikasi berulir.

#### Statistik Memori Proses

Untuk mengumpulkan statistik memori proses, gunakan `-r` opsi :

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -r 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Outputnya:

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

Metrik yang dikumpulkan adalah:

* `minflt/s`: Kesalahan kecil per detik, metrik ini menunjukkan jumlah halaman yang dimuat dari memori sistem (RAM).
* `mjflt/s`: Kesalahan utama per detik, metrik ini menunjukkan jumlah halaman yang dimuat dari disk (SWAP).
* `VSZ`: Memori virtual yang digunakan dalam byte.
* `RSS`: Memori residen yang digunakan (memori aktual yang dialokasikan) dalam byte.
* `%MEM`: Persentase total memori yang digunakan.
* `Command`: Nama proses.

##### Hal-hal yang harus diwaspadai

* Cari kesalahan utama per detik, karena nilai ini akan menunjukkan proses yang menukar halaman ke atau dari disk. Perilaku ini dapat menunjukkan kelelahan `OOM` memori, dan dapat menyebabkan peristiwa atau penurunan performa karena pertukaran yang lebih lambat.
* Verifikasi bahwa satu proses tidak menggunakan 100% dari memori yang tersedia. Perilaku ini dapat menunjukkan kebocoran memori.

> [!NOTE]
> `--human` opsi dapat digunakan untuk menampilkan angka dalam format yang dapat dibaca manusia (yaitu, , `Kb``Mb`, `GB`).

#### Statistik I/O Proses

Untuk mengumpulkan statistik memori proses, gunakan `-d` opsi :

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'pidstat -d 1 2')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted"
```

Outputnya:

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

Metrik yang dikumpulkan adalah:

* `kB_rd/s`: Baca kilobyte per detik.
* `kB_wr/s`: Tulis kilobyte per detik.
* `Command`: Nama proses.

##### Hal-hal yang harus diwaspadai

* Cari proses tunggal dengan tingkat baca/tulis yang tinggi per detik. Informasi ini adalah panduan untuk proses dengan I/O lebih dari mengidentifikasi masalah.
Catatan: `--human` opsi dapat digunakan untuk menampilkan angka dalam format yang dapat dibaca manusia (yaitu, , `Kb``Mb`, `GB`).

### `ps`

`ps` Perintah terakhir menampilkan proses sistem, dan dapat diurutkan menurut CPU atau Memori.

Untuk mengurutkan menurut CPU dan mendapatkan 10 proses teratas:

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

Untuk mengurutkan menurut `MEM%` dan mendapatkan 10 proses teratas:

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

## Menggabungkan semua

Skrip bash sederhana dapat mengumpulkan semua detail dalam satu eksekusi, dan menambahkan output ke file untuk digunakan nanti:

```azurecli-interactive
output=$(az vm run-command invoke --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts 'mpstat -P ALL 1 2 && vmstat -w 1 5 && uptime && free -h && swapon && iostat -dxtm 1 1 && lsblk && ls -l /dev/disk/azure && pidstat 1 1 -h --human && pidstat -r 1 1 -h --human && pidstat -d 1 1 -h --human && ps aux --sort=-%cpu | head -20 && ps aux --sort=-%mem | head -20')
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```

Untuk menjalankan, Anda dapat membuat file dengan konten di atas, menambahkan izin eksekusi dengan menjalankan `chmod +x gather.sh`, dan menjalankan dengan `sudo ./gather.sh`.

Skrip ini menyimpan output perintah dalam file yang terletak di direktori yang sama tempat skrip dipanggil.

Selain itu, semua perintah dalam kode blok bash yang tercakup dalam dokumen ini, dapat dijalankan menggunakan `az-cli` ekstensi run-command, dan mengurai output `jq` untuk mendapatkan output serupa untuk menjalankan perintah secara lokal: '

```azurecli-interactive
output=$(az vm run-command invoke -g $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --command-id RunShellScript --scripts "ls -l /dev/disk/azure")
value=$(echo "$output" | jq -r '.value[0].message')
extracted=$(echo "$value" | awk '/\[stdout\]/,/\[stderr\]/' | sed '/\[stdout\]/d' | sed '/\[stderr\]/d')
echo "$extracted" 
```