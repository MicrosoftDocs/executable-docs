---
title: Implantar o gadget Inspektor em um cluster do Serviço de Kubernetes do Azure
description: Este tutorial mostra como implantar o Inspektor Gadget em um cluster AKS
author: josebl
ms.author: josebl
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Guia de início rápido: implantar o gadget Inspektor em um cluster do Serviço de Kubernetes do Azure

Bem-vindo a este tutorial, onde vamos levá-lo passo a passo na implantação do [Inspektor Gadget](https://www.inspektor-gadget.io/) em um cluster do Serviço de Kubernetes do Azure (AKS) com o plug-in kubectl: `gadget`. Este tutorial pressupõe que você já esteja conectado à CLI do Azure e tenha selecionado uma assinatura para usar com a CLI.

## Definir Variáveis de Ambiente

A primeira etapa deste tutorial é definir variáveis de ambiente:

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myResourceGroup$RANDOM_ID"
export REGION="eastus"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
```

## Criar um grupo de recursos

Um grupo de recursos é um contêiner para recursos relacionados. Todos os recursos devem ser colocados em um grupo de recursos. Criaremos um para esse tutorial. O comando a seguir cria um grupo de recursos com os parâmetros $MY_RESOURCE_GROUP_NAME e $REGION definidos anteriormente.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Resultados:

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

## Criar um cluster do AKS

Crie um cluster do AKS usando o comando az aks create.

Isto pode levar alguns minutos.

```bash
az aks create \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --name $MY_AKS_CLUSTER_NAME \
  --location $REGION \
  --no-ssh-key
```

## Conectar-se ao cluster

Para gerenciar um cluster do Kubernetes, use o cliente de linha de comando do Kubernetes, kubectl. O kubectl já está instalado se você usa o Azure Cloud Shell.

1. Instale a CLI az aks localmente usando o comando az aks install-cli

    ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
    ```

2. Configure kubectl para se conectar ao cluster de Kubernetes usando o comando az aks get-credentials. O seguinte comando:
    - Baixa credenciais e configura a CLI de Kubernetes para usá-las.
    - Usa ~/.kube/config, o local padrão para o arquivo de configuração do Kubernetes. Especifique outra localização para o arquivo de configuração do Kubernetes usando o argumento --file.

    > [!WARNING]
    > Isso substituirá todas as credenciais existentes com a mesma entrada

    ```bash
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
    ```

3. Verifique a conexão com o cluster usando o comando kubectl get. Esse comando retorna uma lista dos nós de cluster.

    ```bash
    kubectl get nodes
    ```

## Instalar o Inspektor Gadget

A instalação do Inspektor Gadget é composta de duas etapas:

1. Instalando o plugin kubectl no sistema do usuário.
2. Instalando o Inspektor Gadget no cluster.

    > [!NOTE]
    > Existem mecanismos adicionais para implantar e utilizar o Inspektor Gadget, cada um adaptado a casos de uso e requisitos específicos. Usando o plugin `kubectl gadget` cobre muitos deles, mas não todos. Por exemplo, a implantação do Inspektor Gadget com o plug-in `kubectl gadget` depende da disponibilidade do servidor de API do Kubernetes. Portanto, se você não pode depender de tal componente porque sua disponibilidade às vezes pode ser comprometida, é recomendável não usar o mecanismo `kubectl gadget`implantação. Verifique a documentação [ig](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/ig.md) para saber o que fazer nesse e em outros casos de uso.

### Instalando o plugin kubectl: `gadget`

Instale a versão mais recente do plugin kubectl a partir da página de lançamentos, descompacte e mova o executável `kubectl-gadget` para `$HOME/.local/bin`:

> [!NOTE]
> Se você quiser instalá-lo usando [`krew`](https://sigs.k8s.io/krew) ou compilá-lo a partir do código-fonte, siga a documentação oficial: [instalando o gadget kubectl](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-kubectl-gadget).

```bash
IG_VERSION=$(curl -s https://api.github.com/repos/inspektor-gadget/inspektor-gadget/releases/latest | jq -r .tag_name)
IG_ARCH=amd64
mkdir -p $HOME/.local/bin
export PATH=$PATH:$HOME/.local/bin
curl -sL https://github.com/inspektor-gadget/inspektor-gadget/releases/download/${IG_VERSION}/kubectl-gadget-linux-${IG_ARCH}-${IG_VERSION}.tar.gz  | tar -C $HOME/.local/bin -xzf - kubectl-gadget
```

Agora, vamos verificar a instalação executando o comando `version`:

```bash
kubectl gadget version
```

O comando `version` exibirá a versão do cliente (kubectl gadget plugin) e mostrará que ele ainda não está instalado no servidor (o cluster):

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: not installed$"-->
```text
Client version: vX.Y.Z
Server version: not installed
```

### Instalando o gadget Inspektor no cluster

O comando a seguir implantará o DaemonSet:

> [!NOTE]
> Várias opções estão disponíveis para personalizar a implantação: usar uma imagem de contêiner específica, implantar em nós específicos e muitos outros. Para conhecer todos eles, consulte a documentação oficial: [instalar no cluster](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-in-the-cluster).

```bash
kubectl gadget deploy
```

Agora, vamos verificar a instalação executando o comando `version` novamente:

```bash
kubectl gadget version
```

Desta vez, o cliente e o servidor serão instalados corretamente:

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: v\d+\.\d+\.\d+$"-->
```text
Client version: vX.Y.Z
Server version: vX.Y.Z
```

Agora você pode começar a executar os gadgets:

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