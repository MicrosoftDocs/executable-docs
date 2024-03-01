---
title: Implante uma instância escalonável e segura do WordPress no AKS
description: Este tutorial mostra como implantar uma instância escalonável e segura do WordPress no AKS por meio da CLI
author: adrian.joian
ms.author: adrian.joian
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Início Rápido: Implantar uma instância escalonável e segura do WordPress no AKS

Bem-vindo a este tutorial, onde o orientaremos passo a passo na criação de um Aplicativo Web do Azure Kubernetes protegido por https. Este tutorial pressupõe que você já esteja conectado à CLI do Azure e tenha selecionado uma assinatura para usar com a CLI. Também pressupõe que você tenha o Helm instalado ([As instruções podem ser encontradas aqui](https://helm.sh/docs/intro/install/)).

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

Um grupo de recursos é um contêiner para recursos relacionados. Todos os recursos devem ser colocados em um grupo de recursos. Criaremos um para esse tutorial. O comando a seguir cria um grupo de recursos com os parâmetros $MY_RESOURCE_GROUP_NAME e $REGION definidos anteriormente.

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

## Criar um Banco de Dados do Azure para MySQL – Servidor Flexível

O Banco de Dados do Azure para MySQL - Servidor Flexível é um serviço gerenciado que você pode usar para executar, gerenciar e escalar servidores MySQL altamente disponíveis na nuvem. Crie um servidor flexível com o comando [az mysql flexible-server create](https://learn.microsoft.com/cli/azure/mysql/flexible-server#az-mysql-flexible-server-create). Um servidor pode conter vários bancos de dados. O comando a seguir cria um servidor usando padrões de serviço e valores de variáveis do ambiente local da CLI do Azure:

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

O servidor criado terá os atributos abaixo:

- O nome do servidor, o nome de usuário do administrador, a senha do administrador, o nome do grupo de recursos, o local já estão especificados no ambiente de contexto local do shell de nuvem e serão criados no mesmo local que você é o grupo de recursos e os outros componentes do Azure.
- Padrões de serviço para configurações de servidor restantes: camada de computação (com capacidade de intermitência), tamanho da computação/SKU (Standard_B2s), período de retenção de backup (7 dias) e versão do MySQL (8.0.21)
- O método de conectividade padrão é Acesso privado (Integração de rede virtual) com uma rede virtual vinculada e uma sub-rede gerada automaticamente.

> [!NOTE]
> O método de conectividade não poderá ser alterado após a criação do servidor. Por exemplo, se você selecionou `Private access (VNet Integration)` durante a criação, não poderá alterar para `Public access (allowed IP addresses)` após a criação. Recomendamos criar um servidor com acesso Privado para que seja possível acessar seu servidor com segurança usando a Integração VNet. Saiba mais sobre o acesso Privado no [artigo sobre conceitos](https://learn.microsoft.com/azure/mysql/flexible-server/concepts-networking-vnet).

Se você quiser alterar os padrões, confira a [documentação de referência](https://learn.microsoft.com/cli/azure//mysql/flexible-server) da CLI do Azure para obter a lista completa de parâmetros da CLI configuráveis.

## Verificar o status do Banco de Dados do Azure para MySQL - Servidor Flexível

Leva alguns minutos para criar o Banco de Dados do Azure para MySQL - Servidor Flexível e recursos de suporte.

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## Configurar parâmetros de servidor no Banco de Dados do Azure para MySQL - Servidor Flexível

Você pode gerenciar a configuração do Banco de Dados do Azure para MySQL – Servidor Flexível usando os parâmetros de servidor. Os parâmetros de servidor são configurados com o valor padrão e recomendado quando você cria o servidor.

Mostrar detalhes do parâmetro do servidor Para mostrar detalhes sobre um parâmetro específico para um servidor, execute o comando [az mysql flexible-server parameter show](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter).

### Desabilitar o Banco de Dados do Azure para MySQL - Parâmetro de conexão SSL do Servidor Flexível para integração com o WordPress

Você também pode modificar o valor de determinados parâmetros de configuração, que atualiza o valor da configuração subjacente para o mecanismo do servidor MySQL. Para atualizar o parâmetro de servidor, use o comando [az mysql flexível-server parameter set](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set).

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

## Criar um cluster do AKS

Crie um cluster AKS usando o comando az aks create com o parâmetro --enable-addons monitoring para habilitar os insights de contêiner. O exemplo a seguir cria um cluster habilitado para zona de disponibilidade com dimensionamento automático chamado myAKSCluster:

Isso levará alguns minutos

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

## Instalar o Controlador de Entrada do NGINX

Você pode configurar seu controlador de entrada com um endereço IP público estático. O endereço IP público estático permanecerá, se você excluir seu controlador de entrada. O endereço IP não permanecerá, se você excluir o cluster do AKS.
Ao atualizar o controlador de entrada, você deve passar um parâmetro para a versão do Helm, para garantir que o serviço do controlador de entrada esteja ciente do balanceador de carga que será alocado a ele. Para que os certificados HTTPS funcionem corretamente, você usará um rótulo DNS para configurar um FQDN para o endereço IP do controlador de entrada.
O FQDN deve seguir este formulário: $MY_DNS_LABEL. AZURE_REGION_NAME.cloudapp.azure.com.

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

Adicione o parâmetro --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"="<DNS_LABEL>". O rótulo DNS pode ser definido quando o controlador de entrada é implantado pela primeira vez ou mais tarde. Adicione o parâmetro --set controller.service.loadBalancerIP="<STATIC_IP>". Especifique seu próprio endereço IP público que foi criado na etapa anterior.

1. Adicionar o repositório Helm ingress-nginx

    ```bash
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    ```

2. Atualizar o cache do repositório do Gráfico do Helm local

    ```bash
    helm repo update
    ```

3. Instale o suplemento ingress-nginx por meio do Helm executando o seguinte:

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic ingress-nginx ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --create-namespace \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"=$MY_DNS_LABEL \
        --set controller.service.loadBalancerIP=$MY_STATIC_IP \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
        --wait --timeout 10m0s
    ```

## Adicionar terminação HTTPS ao domínio personalizado

Neste ponto do tutorial, você tem um aplicativo Web do AKS com o NGINX como Controlador de entrada e um domínio personalizado que pode usar para acessar seu aplicativo. A próxima etapa é adicionar um certificado SSL ao domínio para que os usuários possam acessar seu aplicativo com segurança por meio do https.

## Configurar o Gerenciador de Certificados

Para adicionar o HTTPS, usaremos o Gerenciador de Certificados. O Gerenciador de Certificados é uma ferramenta de software livre usada para obter e gerenciar o certificado SSL para implantações do Kubernetes. O Gerenciador de Certificado obterá certificados de vários Emissores, tanto Emissores públicos populares quanto Emissores privados, e garantirá que os certificados sejam válidos e atualizados, e tentará renovar os certificados em um horário configurado antes de expirarem.

1. Para instalar o cert-manager, devemos primeiro criar um namespace para executá-lo. Este tutorial instalará o cert-manager no namespace do cert-manager. É possível executar o cert-manager em um namespace diferente, embora você precise fazer modificações nos manifestos de implantação.

    ```bash
    kubectl create namespace cert-manager
    ```

2. Agora podemos instalar o cert-manager. Todos os recursos são incluídos em um único arquivo de manifesto YAML. Isso pode ser instalado executando o seguinte:

    ```bash
    kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
    ```

3. Adicione o rótulo certmanager.k8s.io/disable-validation: "true" ao namespace do cert-manager executando o seguinte. Isso permitirá que os recursos do sistema que o cert-manager requer para inicializar o TLS sejam criados em seu próprio namespace.

    ```bash
    kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
    ```

## Obter certificado por meio de Gráficos do Helm

O Helm é uma ferramenta de implantação do Kubernetes para automatizar a criação, empacotamento, configuração e implantação de aplicativos e serviços em clusters do Kubernetes.

O cert-manager fornece gráficos do Helm como um método de instalação de primeira classe no Kubernetes.

1. Adicionar o repositório do Helm da Jetstack

    Esse repositório é a única fonte com suporte de gráficos do cert-manager. Há alguns outros espelhos e cópias na Internet, mas são totalmente não oficiais e podem representar um risco à segurança.

    ```bash
    helm repo add jetstack https://charts.jetstack.io
    ```

2. Atualizar o cache do repositório do Gráfico do Helm local

    ```bash
    helm repo update
    ```

3. Instale o complemento Cert-Manager por meio do Helm executando o seguinte:

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. Aplicar o Arquivo YAML do Emissor de Certificado

    ClusterIssuers são recursos do Kubernetes que representam autoridades de certificação (CAs) capazes de gerar certificados assinados honrando as solicitações de assinatura do certificado. Todos os certificados cert-manager exigem um emissor referenciado que esteja em condições de tentar atender a solicitação.
    O emissor que estamos usando pode ser encontrado no `cluster-issuer-prod.yml file`

    ```bash
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## Criar uma classe de armazenamento personalizada

As classes de armazenamento padrão se adaptam aos cenários mais comuns, mas não a todos. Para alguns casos, talvez você queira ter a própria classe de armazenamento personalizada com os próprios parâmetros. Por exemplo, use o manifesto a seguir para configurar as mountOptions do compartilhamento de arquivos.
O valor padrão para fileMode e dirMode é 0755 para compartilhamentos de arquivos montados pelo Kubernetes. Você pode especificar as opções de montagem diferentes no objeto de classe de armazenamento.

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## Implantar o WordPress no cluster do AKS

Para este documento, estamos usando um Gráfico do Helm existente para WordPress criado pelo Bitnami. Por exemplo, o gráfico do Bitnami Helm usa MariaDB local como o banco de dados e precisamos substituir esses valores para usar o aplicativo com o Banco de Dados do Azure para MySQL. Todos os valores de substituição Você pode substituir os valores e as configurações personalizadas podem ser encontradas no arquivo `helm-wp-aks-values.yaml`

1. Adicionar o repositório Wordpress Bitnami Helm

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. Atualizar o cache do repositório do Gráfico do Helm local

    ```bash
    helm repo update
    ```

3. Instale a carga de trabalho do Wordpress por meio do Helm executando o seguinte:

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

## Procurar sua implantação do AKS protegida por HTTPS

Execute o seguinte comando para obter o ponto de extremidade HTTPS para seu aplicativo:

> [!NOTE]
> Geralmente, leva de 2 a 3 minutos para que o certificado SSL seja proposto e cerca de 5 minutos para ter todas as réplicas POD do WordPress prontas e que o site seja totalmente acessível por meio de https.

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

Verificando se o conteúdo do WordPress está sendo entregue corretamente.

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

O site pode ser visitado seguindo a URL abaixo:

```bash
echo "You can now visit your web server at https://$FQDN"
```
