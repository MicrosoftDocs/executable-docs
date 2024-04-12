---
title: 'Inicio rápido: creación del primer sitio estático con Azure Static Web Apps mediante la CLI'
description: Aprenda a implementar un sitio estático en Azure Static Web Apps con la CLI de Azure.
services: static-web-apps
author: craigshoemaker
ms.service: static-web-apps
ms.topic: quickstart
ms.date: 03/21/2024
ms.author: cshoe
ms.custom: 'mode-api, devx-track-azurecli, innovation-engine, linux-related-content'
ms.devlang: azurecli
---

# Inicio rápido: creación del primer sitio estático mediante la CLI de Azure

[![Implementación en Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262845)

Azure Static Web Apps publica sitios web en un entorno de producción mediante la creación de aplicaciones desde un repositorio de código.

En este inicio rápido, se implementa una aplicación web en Azure Static Web Apps mediante la CLI de Azure.

## Requisitos previos

- Cuenta de [GitHub](https://github.com).
- Cuenta de [Azure](https://portal.azure.com).
  - Si no tiene una suscripción a Azure, puede [crear una cuenta de evaluación gratuita](https://azure.microsoft.com/free).
- La [CLI de Azure](/cli/azure/install-azure-cli) instalada, (versión 2.29.0 o posterior).
- [Configuración de Git](https://www.git-scm.com/downloads). 

## Definición de las variables de entorno

El primer paso de este inicio rápido es definir variables de entorno.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myStaticWebAppResourceGroup$RANDOM_ID"
export REGION=EastUS2
export MY_STATIC_WEB_APP_NAME="myStaticWebApp$RANDOM_ID"
```

## Creación de un repositorio (opcional)

(Opcional) En este artículo se usa un repositorio de plantillas de GitHub como otra manera de facilitar la introducción. La plantilla incluye una aplicación de inicio que se implementa en Azure Static Web Apps.

1. Vaya a la siguiente ubicación para crear un repositorio: https://github.com/staticwebdev/vanilla-basic/generate.
2. Asigne un nombre al repositorio `my-first-static-web-app`.

> [!NOTE]
> Azure Static Web Apps requiere al menos un archivo HTML para crear una aplicación web. El repositorio que se crea en este paso incluye un solo archivo `index.html`.

3. Seleccione **Create repository** (Crear repositorio).

## Implementación de una aplicación web estática

Implemente la aplicación como una aplicación web estática desde la CLI de Azure.

1. Cree un grupo de recursos.

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

2. Implemente una aplicación web estática desde el repositorio.

```bash
az staticwebapp create \
    --name $MY_STATIC_WEB_APP_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION 
```

Hay dos aspectos para implementar una aplicación estática. La primera operación crea los recursos de Azure subyacentes que componen la aplicación. El segundo es un flujo de trabajo que crea y publica la aplicación.

Para poder ir a un nuevo sitio estático, primero la compilación de implementación debe terminar de ejecutarse.

3. Vuelva a la ventana de la consola y ejecute el siguiente comando para enumerar la dirección URL del sitio web.

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

## Uso de una plantilla de GitHub

Ha implementado correctamente una aplicación web estática en Azure Static Web Apps mediante la CLI de Azure. Ahora que tiene conocimientos básicos sobre cómo implementar una aplicación web estática, puede explorar características y funcionalidades más avanzadas de Azure Static Web Apps.

En caso de que quiera usar el repositorio de plantillas de GitHub, siga estos pasos:

Vaya a https://github.com/login/device y escriba el código que obtiene de GitHub para activar y recuperar el token de acceso personal de GitHub.

1. Ir a https://github.com/login/device.
2. Escriba el código de usuario como se muestra en el mensaje de la consola.
3. Seleccione `Continue`.
4. Seleccione `Authorize AzureAppServiceCLI`.

### Visualización del sitio web a través de Git

1. Cuando obtenga la dirección URL del repositorio mientras ejecuta el script, copie la dirección URL del repositorio y péguela en el explorador.
2. Seleccione la pestaña `Actions`.

   En este momento, Azure crea los recursos para admitir la aplicación web estática. Espere hasta que el icono situado junto al flujo de trabajo en ejecución se convierta en una marca de verificación con fondo verde. Esta operación puede tardar varios minutos en ejecutarse.

3. Una vez que aparezca el icono de acción correcta, el flujo de trabajo se completa y puede volver a la ventana de la consola.
4. Ejecute el siguiente comando para consultar la dirección URL del sitio web.
```bash
   az staticwebapp show \
     --name $MY_STATIC_WEB_APP_NAME \
     --query "defaultHostname"
```
5. Copie la dirección URL en el explorador y vaya al sitio web.

## Limpieza de recursos (opcional)

Si no va a seguir usando esta aplicación, elimine el grupo de recursos y la aplicación web estática mediante el comando [az group delete](/cli/azure/group#az-group-delete).

## Pasos siguientes

> [!div class="nextstepaction"]
> [Adición de una API](add-api.md)