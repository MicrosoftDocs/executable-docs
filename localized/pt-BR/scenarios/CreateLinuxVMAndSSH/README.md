---
title: Criar uma VM do Linux e um SSH no Azure
description: Este tutorial mostra como criar uma VM do Linux e um SSH no Azure.
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Criar uma VM do Linux e um SSH no Azure

[![Implantar no Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262692)


## Definir Variáveis de Ambiente

A primeira etapa desse tutorial é definir as variáveis de ambiente.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
```

# Faça logon no Azure usando a CLI

Para executar comandos no Azure usando a CLI, você precisa fazer logon. Isso é feito, muito simplesmente, pelo comando `az login`:

# Criar um grupo de recursos

Um grupo de recursos é um contêiner para recursos relacionados. Todos os recursos devem ser colocados em um grupo de recursos. Criaremos um para esse tutorial. O comando a seguir cria um grupo de recursos com os parâmetros $MY_RESOURCE_GROUP_NAME e $REGION definidos anteriormente.

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

Para criar uma VM neste grupo de recursos, precisamos executar um comando simples, aqui fornecemos o sinalizador `--generate-ssh-keys`, isso fará com que a CLI procure uma chave ssh disponível em `~/.ssh` e, se for encontrada, ela será usada, caso contrário, uma será gerada e armazenada em `~/.ssh`. Também fornecemos o sinalizador `--public-ip-sku Standard` para garantir que o computador esteja acessível por meio de um IP público. Por fim, estamos implantando a imagem de `Ubuntu 22.04` mais recente. 

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

### Habilitar o logon do Azure AD para uma máquina virtual Linux no Azure

O exemplo a seguir implanta uma VM do Linux e instala a extensão para habilitar o logon no Azure AD para uma VM do Linux. As extensões de VM são pequenos aplicativos que fornecem tarefas de configuração e automação pós-implantação nas máquinas virtuais do Azure.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

# Armazenar o endereço IP da VM para SSH
execute o comando a seguir para obter o endereço IP da VM e armazená-lo como uma variável de ambiente

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

# SSH em VM

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Login to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

Agora você pode ter SSH na VM executando a saída do comando a seguir em seu cliente ssh de escolha

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

# Próximas etapas

* [Documentação da VM](https://learn.microsoft.com/azure/virtual-machines/)
* [usar o Cloud-Init para inicializar uma VM do Linux na primeira inicialização](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-automate-vm-deployment)
* [Criar imagens de VM personalizada](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-custom-images)
* [VMs de balanceamento de carga](https://learn.microsoft.com/azure/load-balancer/quickstart-load-balancer-standard-public-cli)
