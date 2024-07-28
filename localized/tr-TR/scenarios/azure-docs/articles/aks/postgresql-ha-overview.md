---
title: Azure CLI ile AKS'de yüksek oranda kullanılabilir bir PostgreSQL veritabanı dağıtmaya genel bakış
description: Azure CLI ile CloudNativePG işlecini kullanarak AKS üzerinde yüksek oranda kullanılabilir bir PostgreSQL veritabanı dağıtmayı öğrenin.
ms.topic: overview
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---
# Azure CLI ile AKS üzerinde yüksek oranda kullanılabilir bir PostgreSQL veritabanı dağıtma

Bu kılavuzda, Azure CLI ile AKS üzerinde birden çok Azure kullanılabilirlik alanına yayılan yüksek oranda kullanılabilir bir PostgreSQL kümesi dağıtacaksınız.

Bu makalede, Azure Kubernetes Service'te [(AKS)][what-is-aks] PostgreSQL kümesi ayarlama önkoşulları açıklanmaktadır ve tüm dağıtım sürecine ve mimarisine genel bir bakış sağlanmaktadır.

## Önkoşullar

* Bu kılavuzda temel Kubernetes kavramları[ ve [PostgreSQL][postgresql] hakkında temel bilgiler yer ][core-kubernetes-concepts]alır.
* Azure hesabınızdaki **bir abonelikte Sahip** veya **Kullanıcı Erişimi Yöneticisi** ve **Katkıda Bulunan** [Azure yerleşik rolleri][azure-roles] gerekir.

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

* Aşağıdaki kaynakların da yüklü olması gerekir:

  * [Azure CLI](/cli/azure/install-azure-cli) sürüm 2.56 veya üzeri.
  * [Azure Kubernetes Service (AKS) önizleme uzantısı][aks-preview].
  * [jq][jq], sürüm 1.5 veya üzeri.
  * [kubectl][install-kubectl] sürüm 1.21.0 veya üzeri.
  * [Helm][install-helm] sürüm 3.0.0 veya üzeri.
  * [openssl][install-openssl] sürüm 3.3.0 veya üzeri.
  * [Visual Studio Code][install-vscode] veya eşdeğeri.
  * [Krew][install-krew] sürüm 0.4.4 veya üzeri.
  * [kubectl CloudNativePG (CNPG) Eklentisi][cnpg-plugin].

## Dağıtım işlemi

Bu kılavuzda şunların nasıl yapıldığını öğrenirsiniz:

* Çok bölgeli aks kümesi oluşturmak için Azure CLI'yi kullanın.
* CNPG işlecini[ kullanarak yüksek oranda kullanılabilir bir PostgreSQL kümesi ve veritabanı dağıtın][cnpg-plugin].
* Prometheus ve Grafana kullanarak PostgreSQL için izlemeyi ayarlayın.
* PostgreSQL veritabanına örnek veri kümesi dağıtma.
* PostgreSQL ve AKS kümesi yükseltmeleri gerçekleştirin.
* Küme kesintisi ve PostgreSQL çoğaltma yük devretme benzetimi.
* PostgreSQL veritabanını yedekleme ve geri yükleme gerçekleştirme.

## Dağıtım mimarisi

Bu diyagramda, CloudNativePG (CNPG)[ işleci tarafından ](https://cloudnative-pg.io/)yönetilen bir birincil çoğaltma ve iki okuma çoğaltması ile postgreSQL kümesi kurulumu gösterilmektedir. Mimari, aks kümesinde çalışan ve çoğaltmalar arasında yük devretme yaparak bölge kesintisine dayanabilen yüksek oranda kullanılabilir bir PostgreSQL sağlar.

Yedeklemeler Azure Blob Depolama[ depolanır ](/azure/storage/blobs/)ve birincil çoğaltmadan akış çoğaltmasıyla ilgili bir sorun olması durumunda veritabanını geri yüklemek için başka bir yol sağlar.

:::image source="./media/postgresql-ha-overview/architecture-diagram.png" alt-text="CNPG mimarisinin diyagramı." lightbox="./media/postgresql-ha-overview/architecture-diagram.png":::

> [!NOTE]
> CNPG işleci küme* başına yalnızca *bir veritabanını destekler. Veritabanı düzeyinde veri ayrımı gerektiren uygulamalar için uygun şekilde plan yapın.

## Sonraki adımlar

> [!div class="nextstepaction"]
> [CNPG işlecini kullanarak AKS üzerinde yüksek oranda kullanılabilir bir PostgreSQL veritabanı dağıtmak için altyapı oluşturma][create-infrastructure]

## Katkıda Bulunanlar

*Bu makale Microsoft tarafından yönetilir. Başlangıçta aşağıdaki katkıda bulunanlar* tarafından yazılmıştır:

* Ken Kilty | Asıl TPM
* Russell de Pina | Asıl TPM
* Adrian Joian | Kıdemli Müşteri Mühendisi
* Jenny Hayes | Kıdemli İçerik Geliştirici
* Carol Smith | Kıdemli İçerik Geliştirici
* Erin Schaffer | İçerik Geliştirici 2
* Adem Şerif | Müşteri Mühendisi 2

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
