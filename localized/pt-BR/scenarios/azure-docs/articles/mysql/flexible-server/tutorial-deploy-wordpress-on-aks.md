---
title: 'Tutorial: Implantar o WordPress em um cluster do AKS usando a CLI do Azure'
description: Saiba como criar e implantar rapidamente o WordPress no AKS com o Banco de Dados do Azure para MySQL – Servidor Flexível.
ms.service: mysql
ms.subservice: flexible-server
author: mksuni
ms.author: sumuth
ms.topic: tutorial
ms.date: 3/20/2024
ms.custom: 'vc, devx-track-azurecli, innovation-engine, linux-related-content'
---

# Tutorial: Implantar o aplicativo WordPress no AKS com o Banco de Dados do Azure para MySQL – Servidor Flexível

[!INCLUDE[applies-to-mysql-flexible-server](../includes/applies-to-mysql-flexible-server.md)]

[![Implantar no Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262843)

Neste tutorial, você implantará um aplicativo WordPress escalonável protegido por HTTPS em um cluster do AKS (Serviço de Kubernetes do Azure) com o servidor flexível do Banco de Dados do Azure para MySQL usando a CLI do Azure.
O **[AKS](../../aks/intro-kubernetes.md)** é um serviço de Kubernetes gerenciado que permite a implantação e o gerenciamento de clusters rapidamente. O **[Banco de Dados do Azure para MySQL – Servidor Flexível](overview.md)** é um serviço de banco de dados totalmente gerenciado, projetado para fornecer controle e flexibilidade mais granulares em relação às funções de gerenciamento de banco de dados e definições de configuração.

> [!NOTE]
> Este tutorial pressupõe uma compreensão básica dos conceitos do Kubernetes, WordPress e MySQL.

[!INCLUDE [flexible-server-free-trial-note](../includes/flexible-server-free-trial-note.md)]

## Pré-requisitos 

Antes de começar, verifique se você está conectado à CLI do Azure e selecionou uma assinatura para usar com a CLI. Verifique se o [Helm está instalado](https://helm.sh/docs/intro/install/).

> [!NOTE]
> Se você estiver executando os comandos neste tutorial localmente em vez do Azure Cloud Shell, execute os comandos como administrador.

## Definir Variáveis de Ambiente

A primeira etapa desse tutorial é definir as variáveis de ambiente.

```bash
export SSL_EMAIL_ADDRESS="$(az account show --query user.name --output tsv)"
export NETWORK_PREFIX="$(($RANDOM % 253 + 1))"
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myWordPressAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_PUBLIC_IP_NAME="myPublicIP$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
export MY_VNET_NAME="myVNet$RANDOM_ID"
export MY_VNET_PREFIX="10.$NETWORK_PREFIX.0.0/16"
export MY_SN_NAME="mySN$RANDOM_ID"
export MY_SN_PREFIX="10.$NETWORK_PREFIX.0.0/22"
export MY_MYSQL_DB_NAME="mydb$RANDOM_ID"
export MY_MYSQL_ADMIN_USERNAME="dbadmin$RANDOM_ID"
export MY_MYSQL_ADMIN_PW="$(openssl rand -base64 32)"
export MY_MYSQL_SN_NAME="myMySQLSN$RANDOM_ID"
export MY_MYSQL_HOSTNAME="$MY_MYSQL_DB_NAME.mysql.database.azure.com"
export MY_WP_ADMIN_PW="$(openssl rand -base64 32)"
export MY_WP_ADMIN_USER="wpcliadmin"
export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
```

## Criar um grupo de recursos

Um grupo de recursos do Azure é um grupo lógico no qual os recursos do Azure são implantados e gerenciados. Todos os recursos devem ser colocados em um grupo de recursos. O comando a seguir cria um grupo de recursos com os parâmetros `$MY_RESOURCE_GROUP_NAME` e `$REGION` definidos anteriormente.

```bash
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION
```

Resultados:
<!-- expected_similarity=0.3 -->
```json
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX",
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

> [!NOTE]
> A localização do grupo de recursos é onde os metadados do grupo de recursos são armazenados. Também é onde seus recursos são executados no Azure se você não especificar outra região durante a criação de recursos.

## Criar a rede virtual e a sub-rede

A rede virtual é o bloco de construção fundamental para redes privadas no Azure. A Rede Virtual do Azure permite que os recursos do Azure, como VMs, se comuniquem com segurança entre si e com a Internet.

```bash
az network vnet create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --name $MY_VNET_NAME \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefixes $MY_SN_PREFIX
```

Resultados:
<!-- expected_similarity=0.3 -->
```json
{
  "newVNet": {
    "addressSpace": {
      "addressPrefixes": [
        "10.210.0.0/16"
      ]
    },
    "enableDdosProtection": false,
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/myWordPressAKSResourceGroupXXX/providers/Microsoft.Network/virtualNetworks/myVNetXXX",
    "location": "eastus",
    "name": "myVNet210",
    "provisioningState": "Succeeded",
    "resourceGroup": "myWordPressAKSResourceGroupXXX",
    "subnets": [
      {
        "addressPrefix": "10.210.0.0/22",
        "delegations": [],
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/myWordPressAKSResourceGroupXXX/providers/Microsoft.Network/virtualNetworks/myVNetXXX/subnets/mySNXXX",
        "name": "mySN210",
        "privateEndpointNetworkPolicies": "Disabled",
        "privateLinkServiceNetworkPolicies": "Enabled",
        "provisioningState": "Succeeded",
        "resourceGroup": "myWordPressAKSResourceGroupXXX",
        "type": "Microsoft.Network/virtualNetworks/subnets"
      }
    ],
    "type": "Microsoft.Network/virtualNetworks",
    "virtualNetworkPeerings": []
  }
}
```

## Criar uma instância do servidor flexível do Banco de Dados do Azure para MySQL

O servidor flexível do Banco de Dados do Azure para MySQL é um serviço gerenciado que você pode usar para executar, gerenciar e escalar servidores MySQL altamente disponíveis na nuvem. Crie uma instância do Banco de Dados do Azure para MySQL – Servidor Flexível com o comando [az mysql flexible-server create](/cli/azure/mysql/flexible-server). Um servidor pode conter vários bancos de dados. O comando a seguir cria um servidor usando padrões de serviço e valores variáveis do contexto local da CLI do Azure:

```bash
echo "Your MySQL user $MY_MYSQL_ADMIN_USERNAME password is: $MY_WP_ADMIN_PW" 
```

```bash
az mysql flexible-server create \
    --admin-password $MY_MYSQL_ADMIN_PW \
    --admin-user $MY_MYSQL_ADMIN_USERNAME \
    --auto-scale-iops Disabled \
    --high-availability Disabled \
    --iops 500 \
    --location $REGION \
    --name $MY_MYSQL_DB_NAME \
    --database-name wordpress \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --sku-name Standard_B2s \
    --storage-auto-grow Disabled \
    --storage-size 20 \
    --subnet $MY_MYSQL_SN_NAME \
    --private-dns-zone $MY_DNS_LABEL.private.mysql.database.azure.com \
    --tier Burstable \
    --version 8.0.21 \
    --vnet $MY_VNET_NAME \
    --yes -o JSON
```

Resultados:
<!-- expected_similarity=0.3 -->
```json
{
  "databaseName": "wordpress",
  "host": "mydbxxx.mysql.database.azure.com",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX/providers/Microsoft.DBforMySQL/flexibleServers/mydbXXX",
  "location": "East US",
  "resourceGroup": "myWordPressAKSResourceGroupXXX",
  "skuname": "Standard_B2s",
  "subnetId": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX/providers/Microsoft.Network/virtualNetworks/myVNetXXX/subnets/myMySQLSNXXX",
  "username": "dbadminxxx",
  "version": "8.0.21"
}
```

O servidor criado tem os seguintes atributos:

- Um novo banco de dados vazio é criado quando o servidor é provisionado pela primeira vez.
- O nome do servidor, o nome de usuário do administrador, a senha do administrador, o nome do grupo de recursos e o local já estão especificados no ambiente de contexto local do cloud shell e estão no mesmo local que o grupo de recursos e outros componentes do Azure.
- Os padrões de serviço para as configurações de servidor restantes são a camada de computação (Com capacidade de intermitência), o tamanho da computação/SKU (Standard_B2s), o período de retenção de backup (sete dias) e a versão MySQL (8.0.21).
- O método de conectividade padrão é o acesso privado (integração de rede virtual) com uma rede virtual vinculada e uma sub-rede gerada automaticamente.

> [!NOTE]
> O método de conectividade não poderá ser alterado após a criação do servidor. Por exemplo, se você tiver selecionado `Private access (VNet Integration)` durante a criação, não poderá alterar para `Public access (allowed IP addresses)` depois da criação. Recomendamos criar um servidor com acesso Privado para que seja possível acessar seu servidor com segurança usando a Integração VNet. Saiba mais sobre o acesso Privado no [artigo sobre conceitos](./concepts-networking-vnet.md).

Se você quer alterar os padrões, consulte a [documentação de referência](/cli/azure//mysql/flexible-server) da CLI do Azure para obter a lista completa de parâmetros da CLI configuráveis.

## Verificar o status do Banco de Dados do Azure para MySQL - Servidor Flexível

Leva alguns minutos para criar o Banco de Dados do Azure para MySQL - Servidor Flexível e recursos de suporte.

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## Configurar parâmetros de servidor no Banco de Dados do Azure para MySQL - Servidor Flexível

Você pode gerenciar a configuração do Banco de Dados do Azure para MySQL – Servidor Flexível usando os parâmetros de servidor. Os parâmetros de servidor são configurados com o valor padrão e recomendado quando você cria o servidor.

Para mostrar os detalhes de um parâmetro específico para um servidor, execute o comando [az mysql flexible-server parameter show](/cli/azure/mysql/flexible-server/parameter).

### Desabilitar o Banco de Dados do Azure para MySQL - Parâmetro de conexão SSL do Servidor Flexível para integração com o WordPress

Você também pode modificar o valor de determinados parâmetros de servidor para atualizar os valores de configuração subjacentes para o mecanismo de servidor MySQL. Para atualizar o parâmetro de servidor, use o comando [az mysql flexível-server parameter set](/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set).

```bash
az mysql flexible-server parameter set \
    -g $MY_RESOURCE_GROUP_NAME \
    -s $MY_MYSQL_DB_NAME \
    -n require_secure_transport -v "OFF" -o JSON
```

Resultados:
<!-- expected_similarity=0.3 -->
```json
{
  "allowedValues": "ON,OFF",
  "currentValue": "OFF",
  "dataType": "Enumeration",
  "defaultValue": "ON",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX/providers/Microsoft.DBforMySQL/flexibleServers/mydbXXX/configurations/require_secure_transport",
  "isConfigPendingRestart": "False",
  "isDynamicConfig": "True",
  "isReadOnly": "False",
  "name": "require_secure_transport",
  "resourceGroup": "myWordPressAKSResourceGroupXXX",
  "source": "user-override",
  "systemData": null,
  "type": "Microsoft.DBforMySQL/flexibleServers/configurations",
  "value": "OFF"
}
```

## Criar cluster AKS

Para criar um cluster do AKS com Insights do contêiner, use o comando [az aks create](/cli/azure/aks#az-aks-create) com o parâmetro de monitoramento **--enable-addons**. O exemplo a seguir cria um cluster habilitado para zona de disponibilidade e dimensionamento automático chamado **myAKSCluster**:

Essa ação leva alguns minutos.

```bash
export MY_SN_ID=$(az network vnet subnet list --resource-group $MY_RESOURCE_GROUP_NAME --vnet-name $MY_VNET_NAME --query "[0].id" --output tsv)

az aks create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_AKS_CLUSTER_NAME \
    --auto-upgrade-channel stable \
    --enable-cluster-autoscaler \
    --enable-addons monitoring \
    --location $REGION \
    --node-count 1 \
    --min-count 1 \
    --max-count 3 \
    --network-plugin azure \
    --network-policy azure \
    --vnet-subnet-id $MY_SN_ID \
    --no-ssh-key \
    --node-vm-size Standard_DS2_v2 \
    --service-cidr 10.255.0.0/24 \
    --dns-service-ip 10.255.0.10 \
    --zones 1 2 3
```
> [!NOTE]
> Durante a criação de um cluster do AKS, um segundo grupo de recursos é criado automaticamente para armazenar os recursos do AKS. Confira [Por que são criados dois grupos de recursos com o AKS?](../../aks/faq.md#why-are-two-resource-groups-created-with-aks)

## Conectar-se ao cluster

Para gerenciar um cluster Kubernetes, use [kubectl](https://kubernetes.io/docs/reference/kubectl/overview/), o cliente de linha de comando Kubernetes. Se você usar o Azure Cloud Shell, o `kubectl` já estará instalado. O exemplo a seguir instala `kubectl` localmente usando o comando [az aks install-cli](/cli/azure/aks#az-aks-install-cli). 

 ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
```

Em seguida, configure `kubectl` para se conectar ao cluster do Kubernetes usando o comando [az aks get-credentials](/cli/azure/aks#az-aks-get-credentials). Este comando baixa as credenciais e configura a CLI do Kubernetes para usá-las. O comando usa `~/.kube/config`, o local padrão para o [arquivo de configuração do Kubernetes](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/). Você pode especificar outro local para seu arquivo de configuração do Kubernetes usando o argumento **--file**.

> [!WARNING]
> Esse comando substituirá todas as credenciais existentes com a mesma entrada.

```bash
az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
```

Para verificar a conexão com o cluster, use o comando [kubectl get]( https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#get) para retornar uma lista dos nós de cluster.

```bash
kubectl get nodes
```

## Instalar o controlador de entrada NGINX

Você pode configurar seu controlador de entrada com um endereço IP público estático. O endereço IP público estático permanecerá, se você excluir seu controlador de entrada. O endereço IP não permanecerá, se você excluir o cluster do AKS.
Ao atualizar o controlador de entrada, você deve passar um parâmetro para a versão do Helm, para garantir que o serviço do controlador de entrada esteja ciente do balanceador de carga que será alocado a ele. Para que os certificados HTTPS funcionem corretamente, use um rótulo DNS para configurar um FQDN (nome de domínio totalmente qualificado) para o endereço IP do controlador de entrada. O FQDN deve seguir este formulário: $MY_DNS_LABEL. AZURE_REGION_NAME.cloudapp.azure.com.

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

Em seguida, adicione o repositório Helm ingress-nginx, atualize o cache do repositório do Gráfico do Helm local e instale o suplemento ingress-nginx via Helm. Você pode definir o rótulo DNS com o **--set controller.service.annotations.". service\.beta\.kubernetes\.io/azure-dns-label-name parâmetro "="DNS_LABEL"** ao implantar pela primeira vez o controlador de entrada ou posterior. Neste exemplo, você especifica seu próprio endereço IP público que criou na etapa anterior com o **parâmetro --set controller.service.loadBalancerIP="<STATIC_IP>"**.

```bash
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    helm repo update
    helm upgrade --install --cleanup-on-fail --atomic ingress-nginx ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --create-namespace \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"=$MY_DNS_LABEL \
        --set controller.service.loadBalancerIP=$MY_STATIC_IP \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
        --wait --timeout 10m0s
```

## Adicionar terminação HTTPS ao domínio personalizado

Neste ponto do tutorial, você tem um aplicativo Web AKS com o NGINX como o controlador de entrada e um domínio personalizado que você pode usar para acessar seu aplicativo. A próxima etapa é adicionar um certificado SSL ao domínio para que os usuários possam acessar seu aplicativo com segurança por meio do https.

### Configurar o Gerenciador de Certificados

Para adicionar HTTPS, vamos usar o Gerenciador de Certificados. O Cert Manager é uma ferramenta de software livre para obter e gerenciar certificados SSL para implantações do Kubernetes. O Cert Manager obtém certificados de emissores públicos populares e emissores privados, garante que os certificados sejam válidos e atualizados e tente renovar certificados em um momento configurado antes de expirarem.

1. Para instalar o cert-manager, devemos primeiro criar um namespace para executá-lo. Este tutorial instala o gerenciador de certificados no namespace do gerenciador de certificados. Você pode executar o gerenciador de certificados em um namespace diferente, mas deve fazer modificações nos manifestos de implantação.

    ```bash
    kubectl create namespace cert-manager
    ```

2. Agora podemos instalar o cert-manager. Todos os recursos são incluídos em um único arquivo de manifesto YAML. Instale o arquivo de manifesto com o seguinte comando:

    ```bash
    kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
    ```

3. Adicione o rótulo `certmanager.k8s.io/disable-validation: "true"` ao namespace do gerenciador de certificados executando o seguinte. Isso permite que os recursos do sistema que o cert-manager requer para inicializar o TLS sejam criados em seu próprio namespace.

    ```bash
    kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
    ```

## Obter certificado por meio de Gráficos do Helm

O Helm é uma ferramenta de implantação do Kubernetes para automatizar a criação, empacotamento, configuração e implantação de aplicativos e serviços em clusters do Kubernetes.

O cert-manager fornece gráficos do Helm como um método de instalação de primeira classe no Kubernetes.

1. Adicione o repositório Jetstack do Helm. Esse repositório é a única fonte com suporte de gráficos do cert-manager. Há outros espelhos e cópias em toda a Internet, mas eles não são oficiais e podem apresentar um risco à segurança.

    ```bash
    helm repo add jetstack https://charts.jetstack.io
    ```

2. Atualize o cache do repositório local do Helm Chart.

    ```bash
    helm repo update
    ```

3. Instale o complemento do Cert-Manager por meio do Helm.

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. Aplique o arquivo YAML do emissor do certificado. ClusterIssuers são recursos do Kubernetes que representam autoridades de certificação (ACs) que podem gerar certificados assinados respeitando solicitações de assinatura de certificado. Todos os certificados cert-manager exigem um emissor referenciado que esteja em condições de tentar atender a solicitação. Você pode encontrar o emissor que estamos no `cluster-issuer-prod.yml file`.

    ```bash
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## Criar uma classe de armazenamento personalizada

As classes de armazenamento padrão se adaptam aos cenários mais comuns, mas não a todos. Para alguns casos, talvez você queira ter a própria classe de armazenamento personalizada com os próprios parâmetros. Por exemplo, use o manifesto a seguir para configurar as **mountOptions** do compartilhamento de arquivos.
O valor padrão para **fileMode** e **dirMode** é **0755** para compartilhamentos de arquivos montados pelo Kubernetes. Você pode especificar as opções de montagem diferentes no objeto de classe de armazenamento.

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## Implantar o WordPress no cluster do AKS

Para este tutorial, estamos usando um gráfico do Helm existente para WordPress criado pelo Bitnami. O gráfico do Helm do Bitnami usa um MariaDB local como o banco de dados, portanto, precisamos substituir esses valores para usar o aplicativo com o Banco de Dados do Azure para MySQL. Você pode substituir os valores e as configurações personalizadas do arquivo `helm-wp-aks-values.yaml`.

1. Adicione o repositório Wordpress Bitnami Helm.

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. Atualize o cache do repositório de gráficos do Helm local.

    ```bash
    helm repo update
    ```

3. Instale a carga de trabalho do Wordpress por meio do Helm.

    ```bash
    helm upgrade --install --cleanup-on-fail \
        --wait --timeout 10m0s \
        --namespace wordpress \
        --create-namespace \
        --set wordpressUsername="$MY_WP_ADMIN_USER" \
        --set wordpressPassword="$MY_WP_ADMIN_PW" \
        --set wordpressEmail="$SSL_EMAIL_ADDRESS" \
        --set externalDatabase.host="$MY_MYSQL_HOSTNAME" \
        --set externalDatabase.user="$MY_MYSQL_ADMIN_USERNAME" \
        --set externalDatabase.password="$MY_MYSQL_ADMIN_PW" \
        --set ingress.hostname="$FQDN" \
        --values helm-wp-aks-values.yaml \
        wordpress bitnami/wordpress
    ```

Resultados:
<!-- expected_similarity=0.3 -->
```text
Release "wordpress" does not exist. Installing it now.
NAME: wordpress
LAST DEPLOYED: Tue Oct 24 16:19:35 2023
NAMESPACE: wordpress
STATUS: deployed
REVISION: 1
TEST SUITE: None
NOTES:
CHART NAME: wordpress
CHART VERSION: 18.0.8
APP VERSION: 6.3.2

** Please be patient while the chart is being deployed **

Your WordPress site can be accessed through the following DNS name from within your cluster:

    wordpress.wordpress.svc.cluster.local (port 80)

To access your WordPress site from outside the cluster follow the steps below:

1. Get the WordPress URL and associate WordPress hostname to your cluster external IP:

   export CLUSTER_IP=$(minikube ip) # On Minikube. Use: `kubectl cluster-info` on others K8s clusters
   echo "WordPress URL: https://mydnslabelxxx.eastus.cloudapp.azure.com/"
   echo "$CLUSTER_IP  mydnslabelxxx.eastus.cloudapp.azure.com" | sudo tee -a /etc/hosts
    export CLUSTER_IP=$(minikube ip) # On Minikube. Use: `kubectl cluster-info` on others K8s clusters
    echo "WordPress URL: https://mydnslabelxxx.eastus.cloudapp.azure.com/"
    echo "$CLUSTER_IP  mydnslabelxxx.eastus.cloudapp.azure.com" | sudo tee -a /etc/hosts

2. Open a browser and access WordPress using the obtained URL.

3. Login with the following credentials below to see your blog:

    echo Username: wpcliadmin
    echo Password: $(kubectl get secret --namespace wordpress wordpress -o jsonpath="{.data.wordpress-password}" | base64 -d)
```

## Navegue pela implantação do AKS protegida via HTTPS

Execute o seguinte comando para obter o ponto de extremidade HTTPS para seu aplicativo:

> [!NOTE]
> Geralmente, leva de 2 a 3 minutos para que o certificado SSL seja propagado e cerca de 5 minutos para que todas as réplicas POD do WordPress estejam prontas e o site seja totalmente acessível por meio de https.

```bash
runtime="5 minute"
endtime=$(date -ud "$runtime" +%s)
while [[ $(date -u +%s) -le $endtime ]]; do
    export DEPLOYMENT_REPLICAS=$(kubectl -n wordpress get deployment wordpress -o=jsonpath='{.status.availableReplicas}');
    echo Current number of replicas "$DEPLOYMENT_REPLICAS/3";
    if [ "$DEPLOYMENT_REPLICAS" = "3" ]; then
        break;
    else
        sleep 10;
    fi;
done
```

Verifique se o conteúdo do WordPress é entregue corretamente usando o seguinte comando:

```bash
if curl -I -s -f https://$FQDN > /dev/null ; then 
    curl -L -s -f https://$FQDN 2> /dev/null | head -n 9
else 
    exit 1
fi;
```

Resultados:
<!-- expected_similarity=0.3 -->
```HTML
{
<!DOCTYPE html>
<html lang="en-US">
<head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name='robots' content='max-image-preview:large' />
<title>WordPress on AKS</title>
<link rel="alternate" type="application/rss+xml" title="WordPress on AKS &raquo; Feed" href="https://mydnslabelxxx.eastus.cloudapp.azure.com/feed/" />
<link rel="alternate" type="application/rss+xml" title="WordPress on AKS &raquo; Comments Feed" href="https://mydnslabelxxx.eastus.cloudapp.azure.com/comments/feed/" />
}
```

Visite o site por meio da seguinte URL:

```bash
echo "You can now visit your web server at https://$FQDN"
```

## Limpar os recursos (opcional)

Para evitar cobranças do Azure, limpe recursos desnecessários. Quando você não precisar mais do cluster, use o comando [az group delete](/cli/azure/group#az-group-delete) para remover o grupo de recursos, o serviço de contêiner e todos os recursos relacionados. 

> [!NOTE]
> Quando você excluir o cluster, a entidade de serviço do Microsoft Entra usada pelo cluster do AKS não será removida. Para obter as etapas para remover a entidade de serviço, confira [Considerações sobre a entidade de serviço do AKS e sua exclusão](../../aks/kubernetes-service-principal.md#other-considerations). Se você tiver usado uma identidade gerenciada, ela será gerenciada pela plataforma e não exigirá remoção.

## Próximas etapas

- Saiba como [acessar o painel da Web do Kubernetes](../../aks/kubernetes-dashboard.md) para seu cluster do AKS
- Saiba como [escalar seu cluster](../../aks/tutorial-kubernetes-scale.md)
- Saiba como gerenciar sua [instância do Banco de Dados do Azure para MySQL – Servidor Flexível](./quickstart-create-server-cli.md)
- Saiba como [configurar parâmetros de servidor](./how-to-configure-server-parameters-cli.md) para o servidor de banco de dados
