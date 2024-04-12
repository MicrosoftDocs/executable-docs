---
title: 'Início Rápido: Como criar seu primeiro site estático com os Aplicativos Web Estáticos do Azure usando a CLI'
description: Aprenda a implantar um site estático nos Aplicativos Web Estáticos do Azure com a CLI do Azure.
services: static-web-apps
author: craigshoemaker
ms.service: static-web-apps
ms.topic: quickstart
ms.date: 03/21/2024
ms.author: cshoe
ms.custom: 'mode-api, devx-track-azurecli, innovation-engine, linux-related-content'
ms.devlang: azurecli
---

# Início Rápido: Como criar seu primeiro site estático usando a CLI do Azure

[![Implantar no Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262845)

Os Aplicativos Web Estáticos do Azure publicam um site para produção pela criação de aplicativos por meio de um repositório de código.

Neste guia de início rápido, você implantará um aplicativo Web nos Aplicativos Web Estáticos do Azure usando a CLI do Azure.

## Pré-requisitos

- Conta do [GitHub](https://github.com).
- Conta do [Azure](https://portal.azure.com).
  - Se você não tem uma assinatura do Azure, poderá [criar uma conta de avaliação gratuita](https://azure.microsoft.com/free).
- [CLI do Azure](/cli/azure/install-azure-cli) instalada (versão 2.29.0 ou superior).
- [Uma configuração do Git](https://www.git-scm.com/downloads). 

## Definir variáveis de ambiente

A primeira etapa neste início rápido é definir variáveis de ambiente.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myStaticWebAppResourceGroup$RANDOM_ID"
export REGION=EastUS2
export MY_STATIC_WEB_APP_NAME="myStaticWebApp$RANDOM_ID"
```

## Criar um repositório (opcional)

(Opcional) Esse artigo usa um repositório de modelos GitHub como outra maneira de facilitar os primeiros passos. O modelo apresenta um aplicativo inicial para implantar nos Aplicativos Web Estáticos do Azure.

1. Navegue até a seguinte localização para criar um novo repositório: https://github.com/staticwebdev/vanilla-basic/generate.
2. Nomeie seu repositório `my-first-static-web-app`.

> [!NOTE]
> Os Aplicativos Web Estáticos do Azure requerem pelo menos um arquivo HTML para criar um aplicativo Web. O repositório criado nessa etapa inclui um único arquivo `index.html`.

3. Selecione **Criar repositório**.

## Implantar um aplicativo Web estático

Implante o aplicativo como um aplicativo Web estático na CLI do Azure.

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

## Usar um modelo do GitHub

Você implantou com êxito um aplicativo Web estático nos Aplicativos Web Estáticos do Azure usando a CLI do Azure. Agora que tem uma compreensão básica de como implementar uma aplicação web estática, pode explorar funcionalidades e funcionalidades mais avançadas das Aplicativos Web Estáticos do Azure.

Caso queira usar o repositório de modelos do GitHub, siga estas etapas:

Navegue até https://github.com/login/device e insira o código que você obtém do GitHub para ativar e recuperar o token de acesso pessoal do GitHub.

1. Ir para https://github.com/login/device.
2. Digite o código do usuário conforme exibido na mensagem do seu console.
3. Selecione `Continue`.
4. Selecione `Authorize AzureAppServiceCLI`.

### Exibir o Site via Git

1. Ao obter o URL do repositório ao executar o script, copie o URL do repositório e cole-o em seu navegador.
2. Selecione a guia `Actions`.

   Neste ponto, o Azure está criando os recursos para dar suporte ao seu aplicativo Web estático. Aguarde até que o ícone ao lado do fluxo de trabalho em execução se transforme em uma marca de seleção com fundo verde. Essa operação pode demorar alguns minutos para ser executada.

3. Quando o ícone de sucesso aparecer, o fluxo de trabalho estará concluído e você poderá retornar à janela do console.
4. Execute o seguinte comando para consultar o URL do seu site.
```bash
   az staticwebapp show \
     --name $MY_STATIC_WEB_APP_NAME \
     --query "defaultHostname"
```
5. Copie a URL no navegador e acesse o site.

## Limpar recursos (opcional)

Se você não continuar a usar este aplicativo, exclua o grupo de recursos e o aplicativo Web estático com o comando [az group delete](/cli/azure/group#az-group-delete).

## Próximas etapas

> [!div class="nextstepaction"]
> [Adicionar uma API](add-api.md)