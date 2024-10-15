---
title: Implementación y configuración de un clúster de AKS con identidad de carga de trabajo
description: 'En este artículo de Azure Kubernetes Service (AKS), implementará un clúster de Azure Kubernetes Service y lo configurará con Microsoft Entra Workload ID.'
author: tamram
ms.topic: article
ms.subservice: aks-security
ms.custom: devx-track-azurecli
ms.date: 05/28/2024
ms.author: tamram
---

# Implementación y configuración de la identidad de carga de trabajo en un clúster de Azure Kubernetes Service (AKS)

Azure Kubernetes Service (AKS) es un servicio de Kubernetes administrado que permite implementar y administrar clústeres de Kubernetes rápidamente. En este artículo aprenderá a:

* Implementación de un clúster de AKS mediante la CLI de Azure con el emisor de OpenID Connect e Id. de carga de trabajo de Microsoft Entra
* Cree un identificador de carga de trabajo de Microsoft Entra y una cuenta de servicio de Kubernetes.
* Configure la identidad administrada para la federación de tokens.
* Implemente la carga de trabajo y compruebe la autenticación con la identidad de carga de trabajo.
* Opcionalmente, conceda a un pod del clúster acceso a los secretos de un almacén de claves de Azure.

En este artículo se presupone un conocimiento básico de los conceptos de Kubernetes. Para más información, consulte [Conceptos básicos de Kubernetes de Azure Kubernetes Service (AKS)][kubernetes-concepts]. Si no está familiarizado con Microsoft Entra Workload ID, consulte el siguiente artículo de [información general][workload-identity-overview].

## Requisitos previos

* [!INCLUDE [quickstarts-free-trial-note](~/reusable-content/ce-skilling/azure/includes/quickstarts-free-trial-note.md)]
* En este artículo se necesita la versión 2.47.0, o versiones posteriores, de la CLI de Azure. Si usa Azure Cloud Shell, ya está instalada la versión más reciente.
* Asegúrese de que la identidad que usará para crear el clúster tenga los permisos mínimos adecuados. Para más información sobre el acceso y la identidad en AKS, consulte [Opciones de acceso e identidad en Azure Kubernetes Service (AKS)][aks-identity-concepts].
* Si tiene varias suscripciones de Azure, seleccione el identificador de suscripción adecuado en el que se deben facturar los recursos con el comando [az account set][az-account-set].

> [!NOTE]
> Puede usar _Service Connector_ para ayudarle a configurar algunos pasos automáticamente. Consulte también: [Tutorial: conexión a la cuenta de almacenamiento de Azure en Azure Kubernetes Service (AKS) con Service Connector mediante la identidad de carga de trabajo][tutorial-python-aks-storage-workload-identity].

## Crear un grupo de recursos

Un [grupo de recursos de Azure][azure-resource-group] es un grupo lógico en el que se implementan y administran recursos de Azure. Cuando crea un grupo de recursos, se le pide que especifique una ubicación. Esta ubicación es la ubicación de almacenamiento de los metadatos del grupo de recursos y donde se ejecutan los recursos en Azure si no se especifica otra región durante la creación de recursos.

Cree un grupo de recursos mediante la llamada al comando [az group create][az-group-create].

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export RESOURCE_GROUP="myResourceGroup$RANDOM_ID"
export LOCATION="centralindia"
az group create --name "${RESOURCE_GROUP}" --location "${LOCATION}"
```

El ejemplo de salida siguiente muestra la creación correcta del grupo de recursos:

Resultados:
<!-- expected_similarity=0.3 -->
```json
{
  "id": "/subscriptions/<guid>/resourceGroups/myResourceGroup",
  "location": "eastus",
  "managedBy": null,
  "name": "myResourceGroup",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Creación de un clúster de AKS

Cree un clúster de AKS con el comando [az aks create][az-aks-create] y el parámetro `--enable-oidc-issuer` para habilitar el emisor de OIDC. En el ejemplo siguiente se crea un clúster con un solo nodo:

```azurecli-interactive
export CLUSTER_NAME="myAKSCluster$RANDOM_ID"
az aks create \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity \
    --generate-ssh-keys
```

Transcurridos unos minutos, el comando se completa y devuelve información en formato JSON sobre el clúster.

> [!NOTE]
> Al crear un clúster de AKS, se crea automáticamente un segundo grupo de recursos para almacenar los recursos de dicho clúster. Para más información, consulte [¿Por qué se crean dos grupos de recursos con AKS?][aks-two-resource-groups]

## Actualización de un clúster de AKS ya existente

Puede actualizar un clúster de AKS para usar el emisor de OIDC y habilitar la identidad de carga de trabajo llamando al comando [az aks update][az aks update] con los parámetros `--enable-oidc-issuer` y `--enable-workload-identity`. En el ejemplo siguiente se actualiza un clúster existente:

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity
```

## Recuperación de la dirección URL del emisor de OIDC

Para obtener la dirección URL del emisor de OIDC y guardarla en una variable de entorno, ejecute el siguiente comando:

```azurecli-interactive
export AKS_OIDC_ISSUER="$(az aks show --name "${CLUSTER_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --query "oidcIssuerProfile.issuerUrl" \
    --output tsv)"
```

La variable de entorno debe contener una dirección URL del emisor similar al ejemplo siguiente:

```output
https://eastus.oic.prod-aks.azure.com/00000000-0000-0000-0000-000000000000/11111111-1111-1111-1111-111111111111/
```

De manera predeterminada, el emisor tiene establecido usar la dirección URL base `https://{region}.oic.prod-aks.azure.com/{tenant_id}/{uuid}`, donde el valor `{region}` coincide con la ubicación en la que se implementa el clúster de AKS. El valor `{uuid}` representa la clave OIDC, que es un guid generado aleatoriamente para cada clúster inmutable.

## Creación de una entidad administrada

Llame al comando [az identity create][az-identity-create] para crear una identidad administrada.

```azurecli-interactive
export SUBSCRIPTION="$(az account show --query id --output tsv)"
export USER_ASSIGNED_IDENTITY_NAME="myIdentity$RANDOM_ID"
az identity create \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --location "${LOCATION}" \
    --subscription "${SUBSCRIPTION}"
```

En el ejemplo de salida siguiente se muestra la creación correcta de una identidad administrada:

Resultados:
<!-- expected_similarity=0.3 -->
```output
{
  "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourcegroups/myResourceGroupxxxxxx/providers/Microsoft.ManagedIdentity/userAssignedIdentities/myIdentityxxxxxx",
  "location": "centralindia",
  "name": "myIdentityxxxxxx",
  "principalId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "resourceGroup": "myResourceGroupxxxxxx",
  "systemData": null,
  "tags": {},
  "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "type": "Microsoft.ManagedIdentity/userAssignedIdentities"
}
```

A continuación, cree una variable para el identificador de cliente de la identidad administrada.

```azurecli-interactive
export USER_ASSIGNED_CLIENT_ID="$(az identity show \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --query 'clientId' \
    --output tsv)"
```

## Creación de una cuenta de servicio de Kubernetes

Cree una cuenta de servicio de Kubernetes y anote en ella el identificador de cliente de la identidad administrada creada en el paso anterior. Use el comando [az aks get-credentials][az-aks-get-credentials] y reemplace los valores del nombre del clúster y el nombre del grupo de recursos.

```azurecli-interactive
az aks get-credentials --name "${CLUSTER_NAME}" --resource-group "${RESOURCE_GROUP}"
```

Copie y pegue la siguiente entrada de varias líneas en la CLI de Azure.

```azurecli-interactive
export SERVICE_ACCOUNT_NAMESPACE="default"
export SERVICE_ACCOUNT_NAME="workload-identity-sa$RANDOM_ID"
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  annotations:
    azure.workload.identity/client-id: "${USER_ASSIGNED_CLIENT_ID}"
  name: "${SERVICE_ACCOUNT_NAME}"
  namespace: "${SERVICE_ACCOUNT_NAMESPACE}"
EOF
```

En la salida siguiente se muestra la creación correcta de la identidad de carga de trabajo:

```output
serviceaccount/workload-identity-sa created
```

## Creación de la credencial de identidad federada

Llame al comando [az identity federated-credential create][az-identity-federated-credential-create] para crear la credencial de identidad federada entre la identidad administrada, el emisor de la cuenta de servicio y el asunto. Para más información sobre las credenciales de identidad federada en Microsoft Entra, consulte [Introducción a las credenciales de identidad federada en Microsoft Entra ID][federated-identity-credential].

```azurecli-interactive
export FEDERATED_IDENTITY_CREDENTIAL_NAME="myFedIdentity$RANDOM_ID"
az identity federated-credential create \
    --name ${FEDERATED_IDENTITY_CREDENTIAL_NAME} \
    --identity-name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --issuer "${AKS_OIDC_ISSUER}" \
    --subject system:serviceaccount:"${SERVICE_ACCOUNT_NAMESPACE}":"${SERVICE_ACCOUNT_NAME}" \
    --audience api://AzureADTokenExchange
```

> [!NOTE]
> La credencial de identidad federada tarda unos segundos en propagarse después de agregarla. Si se realiza una solicitud de token inmediatamente después de agregar la credencial de identidad federada, es posible que se produzca un error en la solicitud hasta que se actualice la memoria caché. Para evitar este problema, puede agregar un ligero retraso después de agregar la credencial de identidad federada.

## Implementación de aplicación

Al implementar los pods de aplicación, el manifiesto debe hacer referencia a la cuenta de servicio creada en el paso **Crear cuenta de servicio de Kubernetes**. En el siguiente manifiesto se muestra cómo hacer referencia a la cuenta, en concreto a las propiedades _metadata\namespace_ y _spec\serviceAccountName_. Asegúrese de especificar una imagen para `<image>` y un nombre de contenedor para `<containerName>`:

```bash
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: sample-workload-identity
  namespace: ${SERVICE_ACCOUNT_NAMESPACE}  # Replace with your namespace
  labels:
    azure.workload.identity/use: "true"  # Required. Only pods with this label can use workload identity.
spec:
  serviceAccountName: ${SERVICE_ACCOUNT_NAME}  # Replace with your service account name
  containers:
    - name: rabbitmq  # Replace with your container name
      image: mcr.microsoft.com/mirror/docker/library/rabbitmq:3.10-management-alpine  # Replace with your Docker image
      ports:
        - containerPort: 5672
          name: rabbitmq-amqp
        - containerPort: 15672
          name: rabbitmq-http
      env:
        - name: RABBITMQ_DEFAULT_USER
          value: "username"
        - name: RABBITMQ_DEFAULT_PASS
          value: "password"
      resources:
        requests:
          cpu: 10m
          memory: 128Mi
        limits:
          cpu: 250m
          memory: 256Mi
EOF
```

> [!IMPORTANT]
> Asegúrese de que los pods de aplicación que usan la identidad de carga de trabajo incluyan la etiqueta `azure.workload.identity/use: "true"` en la especificación del pod. De lo contrario, se produce un error en los pods después de reiniciarse.

## Concesión de permisos para acceder a Azure Key Vault

Las instrucciones de este paso muestran cómo acceder a secretos, claves o certificados en un almacén de claves de Azure desde el pod. Los ejemplos de esta sección configuran el acceso a secretos en el almacén de claves para la identidad de carga de trabajo, pero puede realizar pasos similares para configurar el acceso a claves o certificados.

En el ejemplo siguiente se muestra cómo usar el modelo de permisos de control de acceso basado en rol (RBAC) de Azure para conceder al pod acceso al almacén de claves. Para más información sobre el modelo de permisos RBAC de Azure para Azure Key Vault, consulte [Concesión de permisos a las aplicaciones para que accedan a una instancia de Azure Key Vault mediante RBAC de Azure](/azure/key-vault/general/rbac-guide).

1. Cree un almacén de claves con protección de purga y autorización de RBAC habilitada. También puede usar un almacén de claves existente si está configurado para la protección de purga y la autorización de RBAC:

    ```azurecli-interactive
    export KEYVAULT_NAME="keyvault-workload-id$RANDOM_ID"
    # Ensure the key vault name is between 3-24 characters
    if [ ${#KEYVAULT_NAME} -gt 24 ]; then
        KEYVAULT_NAME="${KEYVAULT_NAME:0:24}"
    fi
    az keyvault create \
        --name "${KEYVAULT_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --location "${LOCATION}" \
        --enable-purge-protection \
        --enable-rbac-authorization 
    ```

1. Asígnese el rol [Oficial de secretos del almacén de claves](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-officer) de RBAC para que pueda crear un secreto en el nuevo almacén de claves:

    ```azurecli-interactive
    export KEYVAULT_RESOURCE_ID=$(az keyvault show --resource-group "${KEYVAULT_RESOURCE_GROUP}" \
        --name "${KEYVAULT_NAME}" \
        --query id \
        --output tsv)

    export CALLER_OBJECT_ID=$(az ad signed-in-user show --query objectId -o tsv)

    az role assignment create --assignee "${CALLER_OBJECT_ID}" \
    --role "Key Vault Secrets Officer" \
    --scope "${KEYVAULT_RESOURCE_ID}"
    ```

1. Cree un secreto en un almacén de claves:

    ```azurecli-interactive
    export KEYVAULT_SECRET_NAME="my-secret$RANDOM_ID"
    az keyvault secret set \
        --vault-name "${KEYVAULT_NAME}" \
        --name "${KEYVAULT_SECRET_NAME}" \
        --value "Hello\!"
    ```

1. Asigne el rol [Usuario de secretos del almacén de claves](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-user) a la identidad administrada asignada por el usuario que creó anteriormente. En este paso se concede el permiso de identidad administrada para leer secretos del almacén de claves:

    ```azurecli-interactive
    export IDENTITY_PRINCIPAL_ID=$(az identity show \
        --name "${USER_ASSIGNED_IDENTITY_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --query principalId \
        --output tsv)
    
    az role assignment create \
        --assignee-object-id "${IDENTITY_PRINCIPAL_ID}" \
        --role "Key Vault Secrets User" \
        --scope "${KEYVAULT_RESOURCE_ID}" \
        --assignee-principal-type ServicePrincipal
    ```

1. Cree una variable de entorno para la dirección URL del almacén de claves:

    ```azurecli-interactive
    export KEYVAULT_URL="$(az keyvault show \
        --resource-group ${RESOURCE_GROUP} \
        --name ${KEYVAULT_NAME} \
        --query properties.vaultUri \
        --output tsv)"
    ```

1. Implemente un pod que haga referencia a la cuenta de servicio y la dirección URL del almacén de claves:

    ```bash
    cat <<EOF | kubectl apply -f -
    apiVersion: v1
    kind: Pod
    metadata:
    name: sample-workload-identity-key-vault
    namespace: ${SERVICE_ACCOUNT_NAMESPACE}
    labels:
        azure.workload.identity/use: "true"
    spec:
    serviceAccountName: ${SERVICE_ACCOUNT_NAME}
    containers:
        - image: ghcr.io/azure/azure-workload-identity/msal-go
        name: oidc
        env:
            - name: KEYVAULT_URL
            value: ${KEYVAULT_URL}
            - name: SECRET_NAME
            value: ${KEYVAULT_SECRET_NAME}
    nodeSelector:
        kubernetes.io/os: linux
    EOF
    ```

Para comprobar si el webhook inserta correctamente todas las propiedades, use el comando [kubectl describe][kubectl-describe]:

```azurecli-interactive
kubectl describe pod sample-workload-identity-key-vault | grep "SECRET_NAME:"
```

Si funciona, la salida debe ser similar a la siguiente:

```output
      SECRET_NAME:                 ${KEYVAULT_SECRET_NAME}
```

Para comprobar que el pod puede obtener un token y acceder al recurso, use el comando kubectl logs:

```azurecli-interactive
kubectl logs sample-workload-identity-key-vault
```

Si funciona, la salida debe ser similar a la siguiente:

```output
I0114 10:35:09.795900       1 main.go:63] "successfully got secret" secret="Hello\\!"
```

> [!IMPORTANT]
> Las asignaciones de roles de RBAC de Azure pueden tardar hasta diez minutos en propagarse. Si el pod no puede acceder al secreto, es posible que tenga que esperar a que se propague la asignación de roles. Para más información, consulte [Solución de problemas de RBAC de Azure](/azure/role-based-access-control/troubleshooting#).

## Deshabilitación de la identidad de la carga de trabajo

Para deshabilitar Microsoft Entra Workload ID en el clúster de AKS donde se ha habilitado y configurado, puede ejecutar el siguiente comando:

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --disable-workload-identity
```

## Pasos siguientes

En este artículo, ha implementado un clúster de Kubernetes y lo ha configurado para usar una identidad de carga de trabajo como preparación para que las cargas de trabajo de la aplicación se autentiquen con esa credencial. Ahora está listo para implementar la aplicación y configurarla para usar la identidad de carga de trabajo con la versión más reciente de la biblioteca cliente de [Azure Identity][azure-identity-libraries]. Si no puede volver a escribir la aplicación para usar la versión más reciente de la biblioteca cliente, puede [configurar el pod de la aplicación][workload-identity-migration] para autenticarse usando la identidad administrada con la identidad de carga de trabajo como solución de migración a corto plazo.

La integración de [Conector de servicio](/azure/service-connector/overview) ayuda a simplificar la configuración de conexión para cargas de trabajo de AKS y servicios de respaldo de Azure. Controla de forma segura la autenticación y las configuraciones de red y sigue los procedimientos recomendados para conectarse a los servicios de Azure. Para más información, consulte [Conexión al Azure OpenAI Service en AKS mediante identidad de carga de trabajo](/azure/service-connector/tutorial-python-aks-openai-workload-identity)y la [Introducción al conector de servicio](https://azure.github.io/AKS/2024/05/23/service-connector-intro).

<!-- EXTERNAL LINKS -->
[kubectl-describe]: https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#describe

<!-- INTERNAL LINKS -->
[kubernetes-concepts]: concepts-clusters-workloads.md
[workload-identity-overview]: workload-identity-overview.md
[azure-resource-group]: /azure/azure-resource-manager/management/overview
[az-group-create]: /cli/azure/group#az-group-create
[aks-identity-concepts]: concepts-identity.md
[federated-identity-credential]: /graph/api/resources/federatedidentitycredentials-overview
[tutorial-python-aks-storage-workload-identity]: /azure/service-connector/tutorial-python-aks-storage-workload-identity
[az-aks-create]: /cli/azure/aks#az-aks-create
[az aks update]: /cli/azure/aks#az-aks-update
[aks-two-resource-groups]: faq.yml
[az-account-set]: /cli/azure/account#az-account-set
[az-identity-create]: /cli/azure/identity#az-identity-create
[az-aks-get-credentials]: /cli/azure/aks#az-aks-get-credentials
[az-identity-federated-credential-create]: /cli/azure/identity/federated-credential#az-identity-federated-credential-create
[workload-identity-migration]: workload-identity-migrate-from-pod-identity.md
[azure-identity-libraries]: /azure/active-directory/develop/reference-v2-libraries