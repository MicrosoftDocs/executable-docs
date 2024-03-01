---
title: Azure Kubernetes Service kümesinde Inspektor Aracı dağıtma
description: 'Bu öğreticide, AKS kümesinde Inspektor Aracı''nın nasıl dağıtılacağı gösterilmektedir'
author: josebl
ms.author: josebl
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Hızlı Başlangıç: Azure Kubernetes Service kümesinde Inspektor Aracı dağıtma

Kubectl eklentisiyle bir Azure Kubernetes Service (AKS) kümesinde Inspektor Aracı'nı[ dağıtma ](https://www.inspektor-gadget.io/)konusunda adım adım ilerleyeceğiniz bu öğreticiye hoş geldiniz: `gadget`. Bu öğreticide, Azure CLI'de zaten oturum açtığınız ve CLI ile kullanmak üzere bir abonelik seçtiğiniz varsayılır.

## Ortam Değişkenlerini Tanımlama

Bu öğreticinin ilk adımı ortam değişkenlerini tanımlamaktır:

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myResourceGroup$RANDOM_ID"
export REGION="eastus"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
```

## Kaynak grubu oluşturma

Kaynak grubu, ilgili kaynaklar için bir kapsayıcıdır. Tüm kaynaklar bir kaynak grubuna yerleştirilmelidir. Bu öğretici için bir tane oluşturacağız. Aşağıdaki komut, önceden tanımlanmış $MY_RESOURCE_GROUP_NAME ve $REGION parametreleriyle bir kaynak grubu oluşturur.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Sonuçlar:

<!-- expected_similarity=0.3 -->
```JSON
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myResourceGroup210",
  "location": "eastus",
  "managedBy": null,
  "name": "testResourceGroup",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## AKS Kümesi Oluşturma

az aks create komutunu kullanarak bir AKS kümesi oluşturun.

Bu işlem birkaç dakika alır.

```bash
az aks create \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --name $MY_AKS_CLUSTER_NAME \
  --location $REGION \
  --no-ssh-key
```

## Kümeye bağlanma

Kubernetes kümesini yönetmek için kubectl adlı Kubernetes komut satırı istemcisini kullanın. Azure Cloud Shell kullanıyorsanız kubectl zaten yüklüdür.

1. az aks install-cli komutunu kullanarak az aks CLI'yi yerel olarak yükleme

    ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
    ```

2. az aks get-credentials komutunu kullanarak kubectl'yi Kubernetes kümenize bağlanacak şekilde yapılandırın. Aşağıdaki komut:
    - Kimlik bilgilerini indirir ve Kubernetes CLI'sini bunları kullanacak şekilde yapılandırılır.
    - Kubernetes yapılandırma dosyasının varsayılan konumu olan ~/.kube/config kullanır. --file bağımsız değişkenini kullanarak Kubernetes yapılandırma dosyanız için farklı bir konum belirtin.

    > [!WARNING]
    > Bu, aynı girişe sahip mevcut kimlik bilgilerinin üzerine yazar

    ```bash
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
    ```

3. kubectl get komutunu kullanarak kümenize bağlantıyı doğrulayın. Bu komut, küme düğümlerinin listesini döndürür.

    ```bash
    kubectl get nodes
    ```

## Inspektor Aracını Yükleme

Inspektor Aracı yüklemesi iki adımdan oluşur:

1. Kubectl eklentisini kullanıcının sistemine yükleme.
2. Kümeye Inspektor Aracı yükleniyor.

    > [!NOTE]
    > Inspektor Gadget'ı dağıtmak ve kullanmak için her birinin belirli kullanım örneklerine ve gereksinimlere göre uyarlanmış ek mekanizmaları vardır. Eklentiyi `kubectl gadget` kullanmak bunların çoğunu kapsar, ancak tümünü kapsamaz. Örneğin Inspektor Aracı'nı `kubectl gadget` eklentiyle dağıtmak Kubernetes API sunucusunun kullanılabilirliğine bağlıdır. Bu nedenle, kullanılabilirliği bazen tehlikeye atıldığı için böyle bir bileşene bağımlı olamıyorsanız dağıtım mekanizmasını `kubectl gadget`kullanmamanız önerilir. Bu ve diğer kullanım örneklerinde ne yapılıp kullanılmadığını öğrenmek için lütfen ig belgelerine[ bakın](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/ig.md).

### kubectl eklentisini yükleme: `gadget`

Sürümler sayfasından kubectl eklentisinin en son sürümünü yükleyin, yürütülebilir dosyayı açın ve öğesine `$HOME/.local/bin`taşıyın`kubectl-gadget`:

> [!NOTE]
> Kullanarak [`krew`](https://sigs.k8s.io/krew) yüklemek veya kaynaktan derlemek istiyorsanız lütfen resmi belgeleri izleyin: [kubectl aracını](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-kubectl-gadget) yükleme.

```bash
IG_VERSION=$(curl -s https://api.github.com/repos/inspektor-gadget/inspektor-gadget/releases/latest | jq -r .tag_name)
IG_ARCH=amd64
mkdir -p $HOME/.local/bin
export PATH=$PATH:$HOME/.local/bin
curl -sL https://github.com/inspektor-gadget/inspektor-gadget/releases/download/${IG_VERSION}/kubectl-gadget-linux-${IG_ARCH}-${IG_VERSION}.tar.gz  | tar -C $HOME/.local/bin -xzf - kubectl-gadget
```

Şimdi komutunu çalıştırarak `version` yüklemeyi doğrulayalım:

```bash
kubectl gadget version
```

`version` komutu istemcinin sürümünü (kubectl araç eklentisi) görüntüler ve henüz sunucuda (küme) yüklenmediğini gösterir:

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: not installed$"-->
```text
Client version: vX.Y.Z
Server version: not installed
```

### Inspektor Aracı'nı kümeye yükleme

Aşağıdaki komut DaemonSet'i dağıtır:

> [!NOTE]
> Dağıtımı özelleştirmek için çeşitli seçenekler vardır: belirli bir kapsayıcı görüntüsünü kullanın, belirli düğümlere dağıtın ve daha birçok seçenek. Tümünü öğrenmek için lütfen resmi belgelere bakın: [kümeye](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-in-the-cluster) yükleme.

```bash
kubectl gadget deploy
```

Şimdi komutunu yeniden çalıştırarak `version` yüklemeyi doğrulayalım:

```bash
kubectl gadget version
```

Bu kez, istemci ve sunucu doğru şekilde yüklenir:

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: v\d+\.\d+\.\d+$"-->
```text
Client version: vX.Y.Z
Server version: vX.Y.Z
```

Artık araçları çalıştırmaya başlayabilirsiniz:

```bash
kubectl gadget help
```

<!--
## Clean Up

### Undeploy Inspektor Gadget

```bash
kubectl gadget undeploy
```

### Clean up Azure resources

When no longer needed, you can use `az group delete` to remove the resource group, cluster, and all related resources as follows. The `--no-wait` parameter returns control to the prompt without waiting for the operation to complete. The `--yes` parameter confirms that you wish to delete the resources without an additional prompt to do so.

```bash
az group delete --name $MY_RESOURCE_GROUP_NAME --no-wait --yes
```
-->

## Sonraki Adımlar
- [Inspektor Gadget'ın size yardımcı olabileceği gerçek dünya senaryoları](https://go.microsoft.com/fwlink/p/?linkid=2260402#use-cases)
- [Kullanılabilir araçları keşfetme](https://go.microsoft.com/fwlink/p/?linkid=2260070)
- [Kendi eBPF programınızı çalıştırma](https://go.microsoft.com/fwlink/p/?linkid=2259865)
