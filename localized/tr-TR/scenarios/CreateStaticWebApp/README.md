---
title: Azure CLI Kullanarak Statik Site Oluşturma
description: Bu öğreticide Azure'da Statik Site oluşturma adımları gösterilmektedir.
author: namanparikh
ms.author: namanparikh
ms.topic: article
ms.date: 02/06/2024
ms.custom: innovation-engine
ms.service: Azure
---

# Azure Static Web Apps Hızlı Başlangıcı: Azure CLI Kullanarak İlk Statik Sitenizi Oluşturma

[![Azure’a dağıtın](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262845)

Azure Static Web Apps, bir kod deposundan uygulama oluşturarak web sitelerini üretim ortamında yayımlar. Bu hızlı başlangıçta, Azure CLI kullanarak Azure Static Web Apps'e bir web uygulaması dağıtacaksınız.

## Ortam Değişkenlerini Tanımlama

Bu öğreticinin ilk adımı ortam değişkenlerini tanımlamaktır.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myStaticWebAppResourceGroup$RANDOM_ID"
export REGION=EastUS2
export MY_STATIC_WEB_APP_NAME="myStaticWebApp$RANDOM_ID"
```

## Depo oluşturma (isteğe bağlı)

(İsteğe bağlı) Bu makalede, kullanmaya başlamanızı kolaylaştırmak için başka bir yol olarak GitHub şablon deposu kullanılmaktadır. Şablonda Azure Static Web Apps'e dağıtılacak bir başlangıç uygulaması bulunur.

- Yeni bir depo oluşturmak için aşağıdaki konuma gidin: https://github.com/staticwebdev/vanilla-basic/generate
- Deponuzu adlandır `my-first-static-web-app`

> **Not:** Azure Static Web Apps web uygulaması oluşturmak için en az bir HTML dosyası gerektirir. Bu adımda oluşturduğunuz depo tek `index.html` bir dosya içerir.

`Create repository` öğesini seçin.

## Statik Web Uygulaması Dağıtma

Uygulamayı Azure CLI'dan statik bir web uygulaması olarak dağıtabilirsiniz.

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

## Sonraki Adımlar

Tebrikler! Azure CLI kullanarak Azure Static Web Apps'e başarıyla statik bir web uygulaması dağıttınız. Artık statik web uygulamasının nasıl dağıtılacağı hakkında temel bilgilere sahip olduğunuz için, Azure Static Web Apps'in daha gelişmiş özelliklerini ve işlevselliğini keşfedebilirsiniz.

GitHub şablon deposunu kullanmak istiyorsanız aşağıdaki ek adımları izleyin.

https://github.com/login/device GitHub kişisel erişim belirtecinizi etkinleştirmek ve almak için adresine gidin ve 329B-3945 kullanıcı kodunu girin.

1. Şuraya git: https://github.com/login/device.
2. Konsolunuzun iletisinin görüntülendiği kullanıcı kodunu girin.
3. `Continue` öğesini seçin.
4. `Authorize AzureAppServiceCLI` öğesini seçin.

### Web Sitesini Git aracılığıyla görüntüleme

1. Betiği çalıştırırken depo URL'sini aldığınızda, depo URL'sini kopyalayın ve tarayıcınıza yapıştırın.
2. `Actions` sekmesini seçin.

   Bu noktada Azure, statik web uygulamanızı desteklemek için kaynaklar oluşturmuştur. Çalışan iş akışının yanındaki simge yeşil arka plan ( ) ile onay işaretine dönüşene kadar bekleyin. Bu işlemin yürütülmesi birkaç dakika sürebilir.

3. Başarı simgesi görüntülendiğinde iş akışı tamamlanır ve konsol pencerenize geri dönebilirsiniz.
4. Web sitenizin URL'sini sorgulamak için aşağıdaki komutu çalıştırın.

   az staticwebapp show \
     --name $MY_STATIC_WEB_APP_NAME \
     --query "defaultHostname"

5. Web sitenize gitmek için URL'yi tarayıcınıza kopyalayın.
