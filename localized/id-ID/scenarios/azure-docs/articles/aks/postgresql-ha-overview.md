---
title: Gambaran umum penyebaran database PostgreSQL yang sangat tersedia di AKS dengan Azure CLI
description: Pelajari cara menyebarkan database PostgreSQL yang sangat tersedia di AKS menggunakan operator CloudNativePG!!
ms.topic: overview
ms.date: 07/24/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---
# Menyebarkan database PostgreSQL yang sangat tersedia di AKS dengan Azure CLI

Dalam panduan ini, Anda menyebarkan kluster PostgreSQL yang sangat tersedia yang mencakup beberapa zona ketersediaan Azure di AKS dengan Azure CLI!

Artikel ini menjelaskan prasyarat untuk menyiapkan kluster PostgreSQL di [Azure Kubernetes Service (AKS)][what-is-aks] dan memberikan gambaran umum tentang proses dan arsitektur penyebaran lengkap.

## Prasyarat

* Panduan ini mengasumsikan pemahaman [dasar tentang konsep][core-kubernetes-concepts] kubernetes inti dan [PostgreSQL][postgresql].
* Anda memerlukan Peran[ bawaan **Pemilik** atau **Administrator** Akses Pengguna dan **Kontributor** ][azure-roles]Azure pada langganan di akun Azure Anda.

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

* Anda juga memerlukan sumber daya berikut yang terinstal:

  * [Azure CLI](/cli/azure/install-azure-cli) versi 2.56 atau yang lebih baru.
  * [Ekstensi][aks-preview] pratinjau Azure Kubernetes Service (AKS).
  * [jq][jq], versi 1.5 atau yang lebih baru.
  * [kubectl][install-kubectl] versi 1.21.0 atau yang lebih baru.
  * [Helm][install-helm] versi 3.0.0 atau yang lebih baru.
  * [openssl][install-openssl] versi 3.3.0 atau yang lebih baru.
  * [Visual Studio Code][install-vscode] atau yang setara.
  * [Krew][install-krew] versi 0.4.4 atau yang lebih baru.
  * [Plugin][cnpg-plugin] kubectl CloudNativePG (CNPG).

## Proses penyebaran

Dalam panduan ini, Anda akan mempelajari cara:

* Gunakan Azure CLI untuk membuat kluster AKS multi-zona.
* Sebarkan kluster dan database PostgreSQL yang sangat tersedia menggunakan [operator][cnpg-plugin] CNPG.
* Siapkan pemantauan untuk PostgreSQL menggunakan Prometheus dan Grafana.
* Sebarkan himpunan data sampel ke database PostgreSQL.
* Lakukan peningkatan kluster PostgreSQL dan AKS.
* Simulasikan gangguan kluster dan failover replika PostgreSQL.
* Lakukan pencadangan dan pemulihan database PostgreSQL.

## Arsitektur Penyebaran

Diagram ini menggambarkan penyiapan kluster PostgreSQL dengan satu replika utama dan dua replika baca yang dikelola oleh [operator CloudNativePG (CNPG).](https://cloudnative-pg.io/) Arsitektur ini menyediakan PostgreSQL yang sangat tersedia yang berjalan pada kluster AKS yang dapat menahan pemadaman zona dengan melakukan failover di seluruh replika.

Cadangan disimpan di [Azure Blob Storage](/azure/storage/blobs/), menyediakan cara lain untuk memulihkan database jika terjadi masalah dengan replikasi streaming dari replika utama.

:::image source="./media/postgresql-ha-overview/architecture-diagram.png" alt-text="Diagram arsitektur CNPG." lightbox="./media/postgresql-ha-overview/architecture-diagram.png":::

> [!NOTE]
> Operator CNPG hanya *mendukung satu database per kluster*. Rencanakan sesuai untuk aplikasi yang memerlukan pemisahan data di tingkat database.

## Langkah berikutnya

> [!div class="nextstepaction"]
> [Buat infrastruktur untuk menyebarkan database PostgreSQL yang sangat tersedia di AKS menggunakan operator CNPG][create-infrastructure]

## Kontributor

*Artikel ini dikelola oleh Microsoft. Awalnya ditulis oleh kontributor* berikut:

* Ken Kilty | TPM Utama
* Russell de Pina | TPM Utama
* Adrian Joian | Insinyur Pelanggan Senior
* Jenny Hayes | Pengembang Konten Senior
* Carol Smith | Pengembang Konten Senior
* Erin Schaffer | Pengembang Konten 2
* Adam Sharif | Teknisi Pelanggan 2

<!-- LINKS -->
[what-is-aks]: ./what-is-aks.md
[postgresql]: https://www.postgresql.org/
[core-kubernetes-concepts]: ./concepts-clusters-workloads.md
[azure-roles]: ../role-based-access-control/built-in-roles.md
[aks-preview]: ./draft.md#install-the-aks-preview-azure-cli-extension
[jq]: https://jqlang.github.io/jq/
[install-kubectl]: https://kubernetes.io/docs/tasks/tools/install-kubectl/
[install-helm]: https://helm.sh/docs/intro/install/
[install-openssl]: https://www.openssl.org/
[install-vscode]: https://code.visualstudio.com/Download
[install-krew]: https://krew.sigs.k8s.io/
[cnpg-plugin]: https://cloudnative-pg.io/documentation/current/kubectl-plugin/#using-krew
[create-infrastructure]: ./create-postgresql-ha.md
