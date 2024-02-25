---
title: Criar um site estático usando a CLI do Azure
description: Este tutorial mostra como criar um Site Estático no Azure.
author: namanparikh
ms.author: namanparikh
ms.topic: article
ms.date: 02/06/2024
ms.custom: innovation-engine
ms.service: Azure
---

# Guia de início rápido dos aplicativos Web estáticos do Azure: criando seu primeiro site estático usando a CLI do Azure

Os Aplicativos Web Estáticos do Azure publicam sites para produção criando aplicativos a partir de um repositório de código. Neste início rápido, você implanta um aplicativo Web nos Aplicativos Web Estáticos do Azure usando a CLI do Azure.

## Definir variáveis de ambiente

O primeiro passo neste tutorial é definir variáveis de ambiente.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myStaticWebAppResourceGroup$RANDOM_ID"
export REGION=EastUS2
export MY_STATIC_WEB_APP_NAME="myStaticWebApp$RANDOM_ID"
```

## Criar um repositório (opcional)

(Opcional) Este artigo usa um repositório de modelos do GitHub como outra maneira de facilitar os primeiros passos. O modelo apresenta um aplicativo inicial para implantar nos Aplicativos Web Estáticos do Azure.

- Navegue até o seguinte local para criar um novo repositório: https://github.com/staticwebdev/vanilla-basic/generate
- Nomeie seu repositório `my-first-static-web-app`

> **Observação:** os Aplicativos Web Estáticos do Azure exigem pelo menos um arquivo HTML para criar um aplicativo Web. O repositório criado nesta etapa inclui um único `index.html` arquivo.

Selecione `Create repository`.

## Implantar um aplicativo Web estático

Você pode implantar o aplicativo como um aplicativo Web estático da CLI do Azure.

1. Crie um grupo de recursos.

```bash
az group create \
  --name $MY_RESOURCE_GROUP_NAME \
  --location $REGION
```

Resultados:

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

2. Implante um novo aplicativo Web estático a partir do repositório.

```bash
az staticwebapp create \
    --name $MY_STATIC_WEB_APP_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION 
```

Há dois aspetos na implantação de um aplicativo estático. A primeira operação cria os recursos subjacentes do Azure que compõem seu aplicativo. O segundo é um fluxo de trabalho que cria e publica seu aplicativo.

Antes de poder ir para o novo site estático, a compilação de implantação deve primeiro concluir a execução.

3. Retorne à janela do console e execute o seguinte comando para listar o URL do site.

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

Resultados:

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

## Passos Seguintes

Parabéns! Você implantou com êxito um aplicativo Web estático nos Aplicativos Web Estáticos do Azure usando a CLI do Azure. Agora que você tem uma compreensão básica de como implantar um aplicativo Web estático, pode explorar recursos e funcionalidades mais avançados dos Aplicativos Web Estáticos do Azure.

Caso você queira usar o repositório de modelos do GitHub, siga as etapas adicionais abaixo.

Vá e https://github.com/login/device insira o código de usuário 329B-3945 para ativar e recuperar seu token de acesso pessoal do GitHub.

1. Aceder a https://github.com/login/device.
2. Insira o código de usuário conforme exibido na mensagem do console.
3. Selecione `Continue`.
4. Selecione `Authorize AzureAppServiceCLI`.

### Ver o site via Git

1. À medida que você obtém a URL do repositório enquanto executa o script, copie a URL do repositório e cole-a em seu navegador.
2. Selecione o separador `Actions`.

   Neste ponto, o Azure está criando os recursos para dar suporte ao seu aplicativo Web estático. Aguarde até que o ícone ao lado do fluxo de trabalho em execução se transforme em uma marca de seleção com fundo verde ( ). Esta operação pode levar alguns minutos para ser concluída.

3. Quando o ícone de sucesso aparecer, o fluxo de trabalho estará concluído e você poderá retornar à janela do console.
4. Execute o seguinte comando para consultar o URL do seu site.

   AZ StaticWebApp Mostrar \
     --name $MY_STATIC_WEB_APP_NAME \
     --consulta "defaultHostname"

5. Copie o URL para o seu navegador para ir para o seu site.
