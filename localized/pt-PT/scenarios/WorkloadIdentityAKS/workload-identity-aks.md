---
title: Implantar e configurar um cluster AKS com identidade de carga de trabalho
description: 'Neste artigo do Serviço Kubernetes do Azure (AKS), você implanta um cluster do Serviço Kubernetes do Azure e o configura com uma ID de Carga de Trabalho do Microsoft Entra.'
author: tamram
ms.topic: article
ms.subservice: aks-security
ms.custom: devx-track-azurecli
ms.date: 05/28/2024
ms.author: tamram
---

# Implantar e configurar a identidade da carga de trabalho em um cluster do Serviço Kubernetes do Azure (AKS)

O Serviço Kubernetes do Azure (AKS) é um serviço Kubernetes gerenciado que permite implantar e gerenciar clusters Kubernetes rapidamente. Este artigo mostra-lhe como:

* Implante um cluster AKS usando a CLI do Azure com o emissor do OpenID Connect e uma ID de carga de trabalho do Microsoft Entra.
* Crie um ID de carga de trabalho do Microsoft Entra e uma conta de serviço do Kubernetes.
* Configure a identidade gerenciada para federação de tokens.
* Implante a carga de trabalho e verifique a autenticação com a identidade da carga de trabalho.
* Opcionalmente, conceda a um pod no cluster acesso a segredos em um cofre de chaves do Azure.

Este artigo pressupõe que você tenha uma compreensão básica dos conceitos do Kubernetes. Para obter mais informações, consulte [Conceitos principais do Kubernetes para o Serviço Kubernetes do Azure (AKS).][kubernetes-concepts] Se você não estiver familiarizado com o ID de carga de trabalho do Microsoft Entra, consulte o seguinte [artigo Visão geral][workload-identity-overview] .

## Pré-requisitos

* [!INCLUDE [quickstarts-free-trial-note](~/reusable-content/ce-skilling/azure/includes/quickstarts-free-trial-note.md)]
* Este artigo requer a versão 2.47.0 ou posterior da CLI do Azure. Se estiver usando o Azure Cloud Shell, a versão mais recente já está instalada.
* Verifique se a identidade que você está usando para criar seu cluster tem as permissões mínimas apropriadas. Para obter mais informações sobre acesso e identidade para AKS, consulte [Opções de acesso e identidade para o Serviço Kubernetes do Azure (AKS).][aks-identity-concepts]
* Se você tiver várias assinaturas do Azure, selecione a ID de assinatura apropriada na qual os recursos devem ser cobrados usando o [comando az account set][az-account-set] .

> [!NOTE]
> Você pode usar _o Service Connector_ para ajudá-lo a configurar algumas etapas automaticamente. Consulte também: [Tutorial: Conectar-se à conta de armazenamento do Azure no Serviço Kubernetes do Azure (AKS) com o Service Connector usando a identidade][tutorial-python-aks-storage-workload-identity] da carga de trabalho.

## Criar um grupo de recursos

Um [grupo][azure-resource-group] de recursos do Azure é um grupo lógico no qual os recursos do Azure são implantados e gerenciados. Ao criar um grupo de recursos, você será solicitado a especificar um local. Esse local é o local de armazenamento dos metadados do grupo de recursos e onde os recursos são executados no Azure se você não especificar outra região durante a criação do recurso.

Crie um grupo de recursos chamando o [comando az group create][az-group-create] :

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export RESOURCE_GROUP="myResourceGroup$RANDOM_ID"
export LOCATION="centralindia"
az group create --name "${RESOURCE_GROUP}" --location "${LOCATION}"
```

O exemplo de saída a seguir mostra a criação bem-sucedida de um grupo de recursos:

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

## Criar um cluster do AKS

Crie um cluster AKS usando o [comando az aks create][az-aks-create] com o `--enable-oidc-issuer` parâmetro para habilitar o emissor OIDC. O exemplo a seguir cria um cluster com um único nó:

```azurecli-interactive
export CLUSTER_NAME="myAKSCluster$RANDOM_ID"
az aks create \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity \
    --generate-ssh-keys
```

Após alguns minutos, o comando conclui e retorna informações formatadas em JSON sobre o cluster.

> [!NOTE]
> Quando você cria um cluster AKS, um segundo grupo de recursos é criado automaticamente para armazenar os recursos do AKS. Para obter mais informações, consulte [Por que dois grupos de recursos são criados com o AKS?][aks-two-resource-groups].

## Atualizar um cluster AKS existente

Você pode atualizar um cluster AKS para usar o emissor OIDC e habilitar a identidade da carga de trabalho chamando o [comando az aks update][az aks update] com os `--enable-oidc-issuer` parâmetros e `--enable-workload-identity` . O exemplo a seguir atualiza um cluster existente:

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity
```

## Recuperar o URL do emissor OIDC

Para obter a URL do emissor OIDC e salvá-la em uma variável ambiental, execute o seguinte comando:

```azurecli-interactive
export AKS_OIDC_ISSUER="$(az aks show --name "${CLUSTER_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --query "oidcIssuerProfile.issuerUrl" \
    --output tsv)"
```

A variável de ambiente deve conter a URL do emissor, semelhante ao exemplo a seguir:

```output
https://eastus.oic.prod-aks.azure.com/00000000-0000-0000-0000-000000000000/11111111-1111-1111-1111-111111111111/
```

Por padrão, o emissor é definido para usar a URL `https://{region}.oic.prod-aks.azure.com/{tenant_id}/{uuid}`base, onde o valor for `{region}` corresponde ao local no qual o cluster AKS está implantado. O valor `{uuid}` representa a chave OIDC, que é um guid gerado aleatoriamente para cada cluster que é imutável.

## Criar uma identidade gerenciada

Chame o [comando az identity create][az-identity-create] para criar uma identidade gerenciada.

```azurecli-interactive
export SUBSCRIPTION="$(az account show --query id --output tsv)"
export USER_ASSIGNED_IDENTITY_NAME="myIdentity$RANDOM_ID"
az identity create \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --location "${LOCATION}" \
    --subscription "${SUBSCRIPTION}"
```

O exemplo de saída a seguir mostra a criação bem-sucedida de uma identidade gerenciada:

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

Em seguida, crie uma variável para o ID do cliente da identidade gerenciada.

```azurecli-interactive
export USER_ASSIGNED_CLIENT_ID="$(az identity show \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --query 'clientId' \
    --output tsv)"
```

## Criar uma conta de serviço do Kubernetes

Crie uma conta de serviço Kubernetes e anote-a com o ID do cliente da identidade gerenciada criada na etapa anterior. Use o [comando az aks get-credentials][az-aks-get-credentials] e substitua os valores do nome do cluster e do nome do grupo de recursos.

```azurecli-interactive
az aks get-credentials --name "${CLUSTER_NAME}" --resource-group "${RESOURCE_GROUP}"
```

Copie e cole a seguinte entrada de várias linhas na CLI do Azure.

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

A saída a seguir mostra a criação bem-sucedida da identidade da carga de trabalho:

```output
serviceaccount/workload-identity-sa created
```

## Criar a credencial de identidade federada

Chame o [comando az identity federated-credential create][az-identity-federated-credential-create] para criar a credencial de identidade federada entre a identidade gerenciada, o emissor da conta de serviço e o assunto. Para obter mais informações sobre credenciais de identidade federada no Microsoft Entra, consulte [Visão geral das credenciais de identidade federada no Microsoft Entra ID][federated-identity-credential].

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
> Leva alguns segundos para que a credencial de identidade federada se propague depois de ser adicionada. Se uma solicitação de token for feita imediatamente após a adição da credencial de identidade federada, a solicitação poderá falhar até que o cache seja atualizado. Para evitar esse problema, você pode adicionar um pequeno atraso após adicionar a credencial de identidade federada.

## Implementar a sua aplicação

Quando você implanta seus pods de aplicativo, o manifesto deve fazer referência à **conta de serviço criada na etapa Criar conta** de serviço do Kubernetes. O manifesto a seguir mostra como fazer referência à conta, especificamente as _propriedades metadata\namespace_ e _spec\serviceAccountName_ . Certifique-se de especificar uma imagem para `<image>` e um nome de contêiner para `<containerName>`:

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
> Certifique-se de que os pods de aplicativo que usam a identidade da carga de trabalho incluam o rótulo `azure.workload.identity/use: "true"` na especificação do pod. Caso contrário, os pods falharão depois de serem reiniciados.

## Conceder permissões para acessar o Azure Key Vault

As instruções nesta etapa mostram como acessar segredos, chaves ou certificados em um cofre de chaves do Azure a partir do pod. Os exemplos nesta seção configuram o acesso a segredos no cofre de chaves para a identidade da carga de trabalho, mas você pode executar etapas semelhantes para configurar o acesso a chaves ou certificados.

O exemplo a seguir mostra como usar o modelo de permissão de controle de acesso baseado em função do Azure (Azure RBAC) para conceder acesso ao pod ao cofre de chaves. Para obter mais informações sobre o modelo de permissão do Azure RBAC para o Azure Key Vault, consulte [Conceder permissão a aplicativos para acessar um cofre de chaves do Azure usando o Azure RBAC.](/azure/key-vault/general/rbac-guide)

1. Crie um cofre de chaves com proteção contra limpeza e autorização RBAC habilitada. Você também pode usar um cofre de chaves existente se ele estiver configurado para proteção contra limpeza e autorização RBAC:

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

1. Atribua a si mesmo a função de Oficial[ de Segredos do Cofre de Chaves RBAC ](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-officer)para que você possa criar um segredo no novo cofre de chaves:

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

1. Crie um segredo no cofre de chaves:

    ```azurecli-interactive
    export KEYVAULT_SECRET_NAME="my-secret$RANDOM_ID"
    az keyvault secret set \
        --vault-name "${KEYVAULT_NAME}" \
        --name "${KEYVAULT_SECRET_NAME}" \
        --value "Hello\!"
    ```

1. Atribua a [função Usuário](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-user) de Segredos do Cofre de Chaves à identidade gerenciada atribuída pelo usuário que você criou anteriormente. Esta etapa dá à identidade gerenciada permissão para ler segredos do cofre de chaves:

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

1. Crie uma variável de ambiente para o URL do cofre de chaves:

    ```azurecli-interactive
    export KEYVAULT_URL="$(az keyvault show \
        --resource-group ${RESOURCE_GROUP} \
        --name ${KEYVAULT_NAME} \
        --query properties.vaultUri \
        --output tsv)"
    ```

1. Implante um pod que faça referência à conta de serviço e ao URL do cofre de chaves:

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

Para verificar se todas as propriedades são injetadas corretamente pelo webhook, use o [comando kubectl describe][kubectl-describe] :

```azurecli-interactive
kubectl describe pod sample-workload-identity-key-vault | grep "SECRET_NAME:"
```

Se for bem-sucedida, a saída deve ser semelhante à seguinte:

```output
      SECRET_NAME:                 ${KEYVAULT_SECRET_NAME}
```

Para verificar se o pod é capaz de obter um token e acessar o recurso, use o comando kubectl logs:

```azurecli-interactive
kubectl logs sample-workload-identity-key-vault
```

Se for bem-sucedida, a saída deve ser semelhante à seguinte:

```output
I0114 10:35:09.795900       1 main.go:63] "successfully got secret" secret="Hello\\!"
```

> [!IMPORTANT]
> As atribuições de função do RBAC do Azure podem levar até dez minutos para se propagar. Se o pod não conseguir acessar o segredo, talvez seja necessário aguardar a propagação da atribuição de função. Para obter mais informações, consulte [Solucionar problemas do Azure RBAC.](/azure/role-based-access-control/troubleshooting#)

## Desabilitar a identidade da carga de trabalho

Para desativar o ID de carga de trabalho do Microsoft Entra no cluster AKS onde ele foi habilitado e configurado, você pode executar o seguinte comando:

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --disable-workload-identity
```

## Próximos passos

Neste artigo, você implantou um cluster Kubernetes e o configurou para usar uma identidade de carga de trabalho em preparação para cargas de trabalho de aplicativo para autenticação com essa credencial. Agora você está pronto para implantar seu aplicativo e configurá-lo para usar a identidade da carga de trabalho com a versão mais recente da [biblioteca de cliente do Azure Identity][azure-identity-libraries] . Se não for possível reescrever seu aplicativo para usar a versão mais recente da biblioteca do cliente, você poderá [configurar seu pod][workload-identity-migration] de aplicativo para autenticar usando identidade gerenciada com identidade de carga de trabalho como uma solução de migração de curto prazo.

A [integração do Service Connector](/azure/service-connector/overview) ajuda a simplificar a configuração de conexão para cargas de trabalho AKS e serviços de suporte do Azure. Ele lida com segurança com autenticação e configurações de rede e segue as práticas recomendadas para se conectar aos serviços do Azure. Para obter mais informações, consulte [Conectar-se ao Serviço OpenAI do Azure no AKS usando a Identidade da Carga de Trabalho](/azure/service-connector/tutorial-python-aks-openai-workload-identity) e a introdução[ do ](https://azure.github.io/AKS/2024/05/23/service-connector-intro)Service Connector.

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