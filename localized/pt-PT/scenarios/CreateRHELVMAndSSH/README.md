---
title: 'Guia de início rápido: use a CLI do Azure para criar uma máquina virtual Red Hat Enterprise Linux'
description: 'Neste início rápido, você aprenderá a usar a CLI do Azure para criar uma máquina virtual Red Hat Enterprise Linux'
author: namanparikh
ms.service: virtual-machines
ms.collection: linux
ms.topic: quickstart
ms.date: 05/03/2024
ms.author: namanparikh
ms.custom: 'mvc, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Guia de início rápido: criar uma máquina virtual Red Hat Enterprise Linux com a CLI do Azure no Azure

**Aplica-se a:** :heavy_check_mark: VMs Linux

[![Implementar no Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262692)

Este guia de início rápido mostra como usar a CLI do Azure para implantar uma máquina virtual (VM) Red Hat Enterprise Linux no Azure. A CLI do Azure é usada para criar e gerenciar recursos do Azure por meio da linha de comando ou scripts.

Se não tiver uma subscrição do Azure, crie uma [conta gratuita](https://azure.microsoft.com/free/?WT.mc_id=A261C142F) antes de começar.

## Iniciar o Azure Cloud Shell

O Azure Cloud Shell é um shell interativo gratuito que pode utilizar para executar os passos neste artigo. Tem as ferramentas comuns do Azure pré-instaladas e configuradas para utilização com a sua conta. 

Para abrir o Cloud Shell, basta selecionar **Experimentar** no canto superior direito de um bloco de código. Você também pode abrir o Cloud Shell em uma guia separada do navegador acessando .[https://shell.azure.com/bash](https://shell.azure.com/bash) Selecione **Copiar** para copiar os blocos de código, cole-o no Cloud Shell e selecione **Enter** para executá-lo.

Se preferir instalar e utilizar a CLI localmente, este início rápido requer a versão 2.0.30 ou posterior da CLI do Azure. Executar `az --version` para localizar a versão. Se precisar de instalar ou atualizar, veja [Install Azure CLI (Instalar o Azure CLI)]( /cli/azure/install-azure-cli).

## Definir variáveis de ambiente

O primeiro passo é definir as variáveis de ambiente. As variáveis de ambiente são comumente usadas no Linux para centralizar os dados de configuração para melhorar a consistência e a capacidade de manutenção do sistema. Crie as seguintes variáveis de ambiente para especificar os nomes dos recursos que você cria posteriormente neste tutorial:

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="RedHat:RHEL:8-LVM:latest"
```

## Faça logon no Azure usando a CLI

Para executar comandos no Azure usando a CLI, você precisa fazer logon primeiro. Faça login usando o `az login` comando.

## Criar um grupo de recursos

Um grupo de recursos é um contêiner para recursos relacionados. Todos os recursos devem ser colocados em um grupo de recursos. O [comando az group create](/cli/azure/group) cria um grupo de recursos com os parâmetros $MY_RESOURCE_GROUP_NAME e $REGION definidos anteriormente.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Resultados:

<!-- expected_similarity=0.3 -->
```json
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMResourceGroup",
  "location": "eastus",
  "managedBy": null,
  "name": "myVMResourceGroup",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Criar a máquina virtual

Para criar uma VM neste grupo de recursos, use o `vm create` comando. 

O exemplo a seguir cria uma VM e adiciona uma conta de usuário. O `--generate-ssh-keys` parâmetro faz com que a CLI procure uma chave ssh disponível no `~/.ssh`. Se uma for encontrada, essa chave é usada. Se não, um é gerado e armazenado em `~/.ssh`. O `--public-ip-sku Standard` parâmetro garante que a máquina seja acessível através de um endereço IP público. Finalmente, implantamos a imagem mais recente `Ubuntu 22.04` .

Todos os outros valores são configurados usando variáveis de ambiente.

```bash
az vm create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_VM_NAME \
    --image $MY_VM_IMAGE \
    --admin-username $MY_USERNAME \
    --assign-identity \
    --generate-ssh-keys \
    --public-ip-sku Standard
```

São necessários alguns minutos para criar a VM e os recursos de suporte. O seguinte resultado de exemplo mostra que a operação de criação da VM foi concluída com êxito.

Resultados:
<!-- expected_similarity=0.3 -->
```json
{
  "fqdns": "",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMResourceGroup/providers/Microsoft.Compute/virtualMachines/myVM",
  "location": "eastus",
  "macAddress": "00-0D-3A-10-4F-70",
  "powerState": "VM running",
  "privateIpAddress": "10.0.0.4",
  "publicIpAddress": "52.147.208.85",
  "resourceGroup": "myVMResourceGroup",
  "zones": ""
}
```

## Habilitar o Logon do Azure AD para uma máquina virtual Linux no Azure

O exemplo de código a seguir implanta uma VM Linux e instala a extensão para habilitar um Logon do Azure AD para uma VM Linux. As extensões de VM são pequenos aplicativos que fornecem tarefas de configuração e automação pós-implantação em máquinas virtuais do Azure.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

## Armazene o endereço IP da VM para SSH

Execute o seguinte comando para armazenar o endereço IP da VM como uma variável de ambiente:

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

## SSH na VM

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Log in to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

Agora você pode SSH na VM executando a saída do seguinte comando no cliente ssh de sua escolha:

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

## Passos Seguintes

* [Saiba mais sobre máquinas virtuais](../index.yml)
* [Use o Cloud-Init para inicializar uma VM Linux na primeira inicialização](tutorial-automate-vm-deployment.md)
* [Criar imagens de VM personalizadas](tutorial-custom-images.md)
* [VMs de balanceamento de carga](../../load-balancer/quickstart-load-balancer-standard-public-cli.md)
