---
title: 'Hızlı Başlangıç: CLI kullanarak Azure Static Web Apps ile ilk statik sitenizi oluşturma'
description: Azure CLI ile Azure Static Web Apps'e statik site dağıtmayı öğrenin.
services: static-web-apps
author: craigshoemaker
ms.service: static-web-apps
ms.topic: quickstart
ms.date: 03/21/2024
ms.author: cshoe
ms.custom: 'mode-api, devx-track-azurecli, innovation-engine, linux-related-content'
ms.devlang: azurecli
---

# Hızlı Başlangıç: Azure CLI kullanarak ilk statik sitenizi oluşturma

[![Azure’a dağıtın](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262845)

Azure Static Web Apps, bir kod deposundan uygulama oluşturarak web sitelerini üretim ortamında yayımlar.

Bu hızlı başlangıçta, Azure CLI kullanarak Azure Statik Web uygulamalarına bir web uygulaması dağıtacaksınız.

## Önkoşullar

- [GitHub](https://github.com) hesabı.
- [Azure hesabı](https://portal.azure.com).
  - Azure aboneliğiniz yoksa ücretsiz deneme hesabı[ oluşturabilirsiniz](https://azure.microsoft.com/free).
- [Azure CLI](/cli/azure/install-azure-cli) yüklü (sürüm 2.29.0 veya üzeri).
- [Git kurulumu](https://www.git-scm.com/downloads). 

## Ortam değişkenlerini tanımlama

Bu hızlı başlangıcın ilk adımı ortam değişkenlerini tanımlamaktır.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myStaticWebAppResourceGroup$RANDOM_ID"
export REGION=EastUS2
export MY_STATIC_WEB_APP_NAME="myStaticWebApp$RANDOM_ID"
```

## Depo oluşturma (isteğe bağlı)

(İsteğe bağlı) Bu makalede, kullanmaya başlamanızı kolaylaştırmak için başka bir yol olarak GitHub şablon deposu kullanılmaktadır. Şablonda Azure Static Web Apps'e dağıtılacak bir başlangıç uygulaması bulunur.

1. Yeni bir depo oluşturmak için aşağıdaki konuma gidin: https://github.com/staticwebdev/vanilla-basic/generate.
2. Deponuza adını verin `my-first-static-web-app`.

> [!NOTE]
> Azure Static Web Apps web uygulaması oluşturmak için en az bir HTML dosyası gerektirir. Bu adımda oluşturduğunuz depo tek `index.html` bir dosya içerir.

3. **Create repository** (Depo oluştur) öğesine tıklayın.

## Statik Web Uygulaması Dağıtma

Uygulamayı Azure CLI'dan statik bir web uygulaması olarak dağıtın.

1. Kaynak grubu oluşturun.

```bash
az group create \
  --name $MY_RESOURCE_GROUP_NAME \
  --location $REGION
```

Sonuçlar:
<!-- expected_similarity=0.3 -->
```json
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/my-swa-group",
  "location": "eastus2",
  "managedBy": null,
  "name": "my-swa-group",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

2. Deponuzdan yeni bir statik web uygulaması dağıtın.

```bash
az staticwebapp create \
    --name $MY_STATIC_WEB_APP_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION 
```

Statik uygulama dağıtmanın iki yönü vardır. İlk işlem, uygulamanızı oluşturan temel Azure kaynaklarını oluşturur. İkincisi, uygulamanızı derleyen ve yayımlayan bir iş akışıdır.

Yeni statik sitenize gidebilmeniz için önce dağıtım derlemesinin çalıştırılmasını tamamlamanız gerekir.

3. Konsol pencerenize dönün ve web sitesinin URL'sini listelemek için aşağıdaki komutu çalıştırın.

```bash
export MY_STATIC_WEB_APP_URL=$(az staticwebapp show --name  $MY_STATIC_WEB_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "defaultHostname" -o tsv)
```

```bash
runtime="1 minute";
endtime=$(date -ud "$runtime" +%s);
while [[ $(date -u +%s) -le $endtime ]]; do
    if curl -I -s $MY_STATIC_WEB_APP_URL > /dev/null ; then 
        curl -L -s $MY_STATIC_WEB_APP_URL 2> /dev/null | head -n 9
        break
    else 
        sleep 10
    fi;
done
```

Sonuçlar:
<!-- expected_similarity=0.3 -->
```HTML
<!DOCTYPE html>
<html lang=en>
<head>
<meta charset=utf-8 />
<meta name=viewport content="width=device-width, initial-scale=1.0" />
<meta http-equiv=X-UA-Compatible content="IE=edge" />
<title>Azure Static Web Apps - Welcome</title>
<link rel="shortcut icon" href=https://appservice.azureedge.net/images/static-apps/v3/favicon.svg type=image/x-icon />
<link rel=stylesheet href=https://ajax.aspnetcdn.com/ajax/bootstrap/4.1.1/css/bootstrap.min.css crossorigin=anonymous />
```

```bash
echo "You can now visit your web server at https://$MY_STATIC_WEB_APP_URL"
```

## GitHub şablonu kullanma

Azure CLI kullanarak Azure Static Web Apps'e başarıyla statik bir web uygulaması dağıttınız. Artık statik web uygulamasının nasıl dağıtılacağı hakkında temel bilgilere sahip olduğunuz için, Azure Static Web Apps'in daha gelişmiş özelliklerini ve işlevselliğini keşfedebilirsiniz.

GitHub şablon deposunu kullanmak istiyorsanız şu adımları izleyin:

https://github.com/login/device GitHub kişisel erişim belirtecinizi etkinleştirmek ve almak için GitHub'dan aldığınız kodu girin.

1. Şuraya git: https://github.com/login/device.
2. Konsolunuzun iletisinin görüntülendiği kullanıcı kodunu girin.
3. `Continue` öğesini seçin.
4. `Authorize AzureAppServiceCLI` öğesini seçin.

### Web Sitesini Git aracılığıyla görüntüleme

1. Betiği çalıştırırken depo URL'sini aldığınızda, depo URL'sini kopyalayın ve tarayıcınıza yapıştırın.
2. `Actions` sekmesini seçin.

   Bu noktada Azure, statik web uygulamanızı desteklemek için kaynaklar oluşturmuştur. Çalışan iş akışının yanındaki simge yeşil arka planlı bir onay işaretine dönüşene kadar bekleyin. Bu işlemin yürütülmesi birkaç dakika sürebilir.

3. Başarı simgesi görüntülendiğinde iş akışı tamamlanır ve konsol pencerenize geri dönebilirsiniz.
4. Web sitenizin URL'sini sorgulamak için aşağıdaki komutu çalıştırın.
```bash
   az staticwebapp show \
     --name $MY_STATIC_WEB_APP_NAME \
     --query "defaultHostname"
```
5. Web sitenize gitmek için URL'yi tarayıcınıza kopyalayın.

## Kaynakları temizleme (isteğe bağlı)

Bu uygulamayı kullanmaya devam etmeyecekseniz az group delete komutunu kullanarak [kaynak grubunu ve statik web uygulamasını silin](/cli/azure/group#az-group-delete) .

## Sonraki adımlar

> [!div class="nextstepaction"]
> [API ekleme](add-api.md)
