---
title: Crie um site estático usando a CLI do Azure
description: Esse tutorial mostra como criar um site estático no Azure.
author: namanparikh
ms.author: namanparikh
ms.topic: article
ms.date: 02/06/2024
ms.custom: innovation-engine
ms.service: Azure
---

# Início Rápido dos Aplicativos Web Estáticos do Azure: criando seu primeiro site estático usando a CLI do Azure

[![Implantar no Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262845)

Os Aplicativos Web Estáticos do Azure publicam um site para produção pela criação de aplicativos por meio de um repositório de código. Nesse início rápido, você implanta um aplicativo Web em Aplicativos Web Estáticos do Azure usando a CLI do Azure.

## Definir Variáveis de Ambiente

A primeira etapa desse tutorial é definir as variáveis de ambiente.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myStaticWebAppResourceGroup$RANDOM_ID"
export REGION=EastUS2
export MY_STATIC_WEB_APP_NAME="myStaticWebApp$RANDOM_ID"
```

## Crie um repositório (opcional)

(Opcional) Esse artigo usa um repositório de modelos GitHub como outra maneira de facilitar os primeiros passos. O modelo apresenta um aplicativo inicial para implantar nos Aplicativos Web Estáticos do Azure.

- Navegue até o seguinte local para criar um novo repositório: https://github.com/staticwebdev/vanilla-basic/generate
- Dê um nome ao seu repositório `my-first-static-web-app`

> **Observação:** Os Aplicativos Web Estáticos do Azure exigem pelo menos um arquivo HTML para criar um aplicativo Web. O repositório criado nessa etapa inclui um único arquivo `index.html`.

Selecione `Create repository`.

## Implantar um aplicativo Web estático

Você pode implantar o aplicativo como um aplicativo Web estático na CLI do Azure.

1. Crie um grupos de recursos.

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

2. Implante um novo aplicativo Web estático por meio do seu repositório.

```bash
az staticwebapp create \
    --name $MY_STATIC_WEB_APP_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION 
```

Há dois aspectos na implantação de um aplicativo estático. A primeira operação cria os recursos subjacentes do Azure que compõem seu aplicativo. O segundo é um fluxo de trabalho que compila e publica seu aplicativo.

Para você acessar o novo site estático, primeiro, o build de implantação precisa concluir a execução.

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

## Próximas etapas

Parabéns! Você implantou com êxito um aplicativo Web estático nos Aplicativos Web Estáticos do Azure usando a CLI do Azure. Agora que tem uma compreensão básica de como implementar uma aplicação web estática, pode explorar funcionalidades e funcionalidades mais avançadas das Aplicativos Web Estáticos do Azure.

Caso queira usar o repositório de modelos GitHub, siga as etapas adicionais abaixo.

Navegue até https://github.com/login/device e insira o código de usuário 329B-3945 para ativar e recuperar o token de acesso pessoal do GitHub.

1. Ir para https://github.com/login/device.
2. Digite o código do usuário conforme exibido na mensagem do seu console.
3. Selecione `Continue`.
4. Selecione `Authorize AzureAppServiceCLI`.

### Exibir o Site via Git

1. Ao obter o URL do repositório ao executar o script, copie o URL do repositório e cole-o em seu navegador.
2. Selecione a guia `Actions`.

   Neste ponto, o Azure está criando os recursos para dar suporte ao seu aplicativo Web estático. Aguarde até que o ícone ao lado do fluxo de trabalho em execução se transforme em uma marca de seleção com fundo verde ( ). Essa operação pode demorar alguns minutos para ser executada.

3. Quando o ícone de sucesso aparecer, o fluxo de trabalho estará concluído e você poderá retornar à janela do console.
4. Execute o seguinte comando para consultar o URL do seu site.

   exibição staticwebapp \
     --name $MY_STATIC_WEB_APP_NAME \
     --query "defaultHostname"

5. Copie a URL no navegador e acesse o site.
