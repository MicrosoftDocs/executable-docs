---
title: Implantar uma instância Scalable & Secure WordPress no AKS
description: Este tutorial mostra como implantar uma instância Scalable & Secure WordPress no AKS via CLI
author: adrian.joian
ms.author: adrian.joian
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Guia de início rápido: implantar uma instância Scalable & Secure WordPress no AKS

Bem-vindo a este tutorial, onde iremos levá-lo passo a passo na criação de um Aplicativo Web Kubernetes do Azure que é protegido via https. Este tutorial pressupõe que você já esteja conectado à CLI do Azure e tenha selecionado uma assinatura para usar com a CLI. Também pressupõe que você tenha o Helm instalado ([as instruções podem ser encontradas aqui](https://helm.sh/docs/intro/install/)).

## Definir variáveis de ambiente

O primeiro passo neste tutorial é definir variáveis de ambiente.

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

Um grupo de recursos é um contêiner para recursos relacionados. Todos os recursos devem ser colocados em um grupo de recursos. Vamos criar um para este tutorial. O comando a seguir cria um grupo de recursos com os parâmetros $MY_RESOURCE_GROUP_NAME e $REGION definidos anteriormente.

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

## Criar uma rede virtual e uma sub-rede

Uma rede virtual é o bloco de construção fundamental para redes privadas no Azure. A Rede Virtual do Azure permite que recursos do Azure, como VMs, se comuniquem com segurança entre si e com a Internet.

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

## Criar um Banco de Dados do Azure para MySQL - Servidor Flexível

O Banco de Dados do Azure para MySQL - Servidor Flexível é um serviço gerenciado que você pode usar para executar, gerenciar e dimensionar servidores MySQL altamente disponíveis na nuvem. Crie um servidor flexível com o [comando az mysql flexible-server create](https://learn.microsoft.com/cli/azure/mysql/flexible-server#az-mysql-flexible-server-create) . Cada servidor pode conter várias bases de dados. O comando a seguir cria um servidor usando padrões de serviço e valores variáveis do ambiente local da CLI do Azure:

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

- O nome do servidor, o nome de usuário do administrador, a senha do administrador, o nome do grupo de recursos, o local já estão especificados no ambiente de contexto local do shell de nuvem e serão criados no mesmo local em que você é o grupo de recursos e os outros componentes do Azure.
- Padrões de serviço para configurações de servidor restantes: camada de computação (Burstable), tamanho de computação/SKU (Standard_B2s), período de retenção de backup (7 dias) e versão do MySQL (8.0.21)
- O método de conectividade padrão é o acesso privado (integração VNet) com uma rede virtual vinculada e uma sub-rede gerada automaticamente.

> [!NOTE]
> O método de conectividade não pode ser alterado após a criação do servidor. Por exemplo, se você selecionou `Private access (VNet Integration)` durante a criação, não poderá alterar para `Public access (allowed IP addresses)` depois da criação. É altamente recomendável criar um servidor com acesso privado para acessar seu servidor com segurança usando a integração VNet. Saiba mais sobre Acesso privado no artigo de [conceitos](https://learn.microsoft.com/azure/mysql/flexible-server/concepts-networking-vnet).

Se você quiser alterar quaisquer padrões, consulte a documentação[ de referência da CLI ](https://learn.microsoft.com/cli/azure//mysql/flexible-server)do Azure para obter a lista completa de parâmetros configuráveis da CLI.

## Verifique o status do Banco de Dados do Azure para MySQL - Servidor Flexível

Leva alguns minutos para criar o Banco de Dados do Azure para MySQL - Servidor Flexível e recursos de suporte.

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## Configurar parâmetros de servidor no Banco de Dados do Azure para MySQL - Servidor Flexível

Você pode gerenciar o Banco de Dados do Azure para MySQL - Configuração de Servidor Flexível usando parâmetros de servidor. Os parâmetros do servidor são configurados com o valor padrão e recomendado quando você cria o servidor.

Mostrar detalhes do parâmetro do servidor Para mostrar detalhes sobre um parâmetro específico para um servidor, execute o [comando az mysql flexible-server parameter show](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter) .

### Desabilitar o Banco de Dados do Azure para MySQL - Parâmetro de conexão SSL do Servidor Flexível para integração com WordPress

Você também pode modificar o valor de certos parâmetros do servidor, que atualiza os valores de configuração subjacentes para o mecanismo de servidor MySQL. Para atualizar o parâmetro server, use o [comando az mysql flexible-server parameter set](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set) .

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

Crie um cluster AKS usando o comando az aks create com o parâmetro de monitoramento --enable-addons para habilitar insights de contêiner. O exemplo a seguir cria um cluster habilitado para zona de disponibilidade de dimensionamento automático chamado myAKSCluster:

Isto demorará alguns minutos

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

## Ligar ao cluster

Para gerenciar um cluster Kubernetes, use o cliente de linha de comando Kubernetes, kubectl. kubectl já está instalado se você usar o Azure Cloud Shell.

1. Instale az aks CLI localmente usando o comando az aks install-cli

    ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
    ```

2. Configure o kubectl para se conectar ao cluster do Kubernetes usando o comando az aks get-credentials. O seguinte comando:

    - Baixa credenciais e configura a CLI do Kubernetes para usá-las.
    - Usa ~/.kube/config, o local padrão para o arquivo de configuração do Kubernetes. Especifique um local diferente para o arquivo de configuração do Kubernetes usando o argumento --file.

    > [!WARNING]
    > Isso substituirá quaisquer credenciais existentes com a mesma entrada

    ```bash
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
    ```

3. Verifique a conexão com seu cluster usando o comando kubectl get. Este comando retorna uma lista dos nós do cluster.

    ```bash
    kubectl get nodes
    ```

## Instalar NGINX Ingress Controller

Você pode configurar seu controlador de entrada com um endereço IP público estático. O endereço IP público estático permanecerá se você excluir seu controlador de entrada. O endereço IP não permanece se você excluir seu cluster AKS.
Ao atualizar seu controlador de entrada, você deve passar um parâmetro para a liberação do Helm para garantir que o serviço do controlador de entrada esteja ciente do balanceador de carga que será alocado a ele. Para que os certificados HTTPS funcionem corretamente, use um rótulo DNS para configurar um FQDN para o endereço IP do controlador de entrada.
Seu FQDN deve seguir este formulário: $MY_DNS_LABEL. AZURE_REGION_NAME.cloudapp.azure.com.

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

Adicione o --set controller.service.annotations." serviço\.beta\.kubernetes\.io/azure-dns-label-name"="<DNS_LABEL>" parâmetro. O rótulo DNS pode ser definido quando o controlador de entrada é implantado pela primeira vez ou pode ser configurado posteriormente. Adicione o parâmetro --set controller.service.loadBalancerIP="<STATIC_IP>". Especifique seu próprio endereço IP público que foi criado na etapa anterior.

1. Adicione o repositório ingress-nginx Helm

    ```bash
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    ```

2. Atualizar o cache do repositório Helm Chart local

    ```bash
    helm repo update
    ```

3. Instale o addon ingress-nginx via Helm executando o seguinte:

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

Neste ponto do tutorial, você tem um aplicativo web AKS com NGINX como controlador de ingresso e um domínio personalizado que você pode usar para acessar seu aplicativo. A próxima etapa é adicionar um certificado SSL ao domínio para que os usuários possam acessar seu aplicativo com segurança via https.

## Configurar o Cert Manager

Para adicionar HTTPS, vamos usar o Cert Manager. O Cert Manager é uma ferramenta de código aberto usada para obter e gerenciar o certificado SSL para implantações do Kubernetes. O Cert Manager obterá certificados de uma variedade de Emissores, tanto emissores públicos populares quanto emissores privados, e garantirá que os certificados sejam válidos e atualizados, e tentará renovar certificados em um momento configurado antes do vencimento.

1. Para instalar o cert-manager, devemos primeiro criar um namespace para executá-lo. Este tutorial instalará o cert-manager no namespace cert-manager. É possível executar o cert-manager em um namespace diferente, embora você precise fazer modificações nos manifestos de implantação.

    ```bash
    kubectl create namespace cert-manager
    ```

2. Agora podemos instalar o cert-manager. Todos os recursos são incluídos em um único arquivo de manifesto YAML. Isso pode ser instalado executando o seguinte:

    ```bash
    kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
    ```

3. Adicione o rótulo certmanager.k8s.io/disable-validation: "true" ao namespace cert-manager executando o seguinte. Isso permitirá que os recursos do sistema que o cert-manager requer para inicializar o TLS sejam criados em seu próprio namespace.

    ```bash
    kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
    ```

## Obter certificado via Helm Charts

O Helm é uma ferramenta de implantação do Kubernetes para automatizar a criação, empacotamento, configuração e implantação de aplicativos e serviços para clusters Kubernetes.

O Cert-manager fornece gráficos Helm como um método de instalação de primeira classe no Kubernetes.

1. Adicionar o repositório Jetstack Helm

    Este repositório é a única fonte suportada de gráficos cert-manager. Existem alguns outros espelhos e cópias na Internet, mas estes são totalmente não oficiais e podem representar um risco de segurança.

    ```bash
    helm repo add jetstack https://charts.jetstack.io
    ```

2. Atualizar o cache do repositório Helm Chart local

    ```bash
    helm repo update
    ```

3. Instale o addon Cert-Manager via Helm executando o seguinte:

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. Aplicar arquivo YAML do emissor do certificado

    ClusterIssuers são recursos do Kubernetes que representam autoridades de certificação (CAs) que são capazes de gerar certificados assinados honrando solicitações de assinatura de certificado. Todos os certificados de gestor de certificados requerem um emissor referenciado que esteja em condições de estar pronto para tentar honrar o pedido.
    O emissor que estamos a utilizar pode ser encontrado no `cluster-issuer-prod.yml file`

    ```bash
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## Criar uma classe de armazenamento personalizada

As classes de armazenamento padrão se adequam aos cenários mais comuns, mas não a todos. Para alguns casos, você pode querer ter sua própria classe de armazenamento personalizada com seus próprios parâmetros. Por exemplo, use o manifesto a seguir para configurar as mountOptions do compartilhamento de arquivos.
O valor padrão para fileMode e dirMode é 0755 para compartilhamentos de arquivos montados no Kubernetes. Você pode especificar as diferentes opções de montagem no objeto de classe de armazenamento.

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## Implantar o WordPress no cluster AKS

Para este documento, estamos usando um Helm Chart existente para WordPress construído pela Bitnami. Por exemplo, o gráfico Bitnami Helm usa MariaDB local como o banco de dados e precisamos substituir esses valores para usar o aplicativo com o Banco de Dados do Azure para MySQL. Todos os valores de substituição Você pode substituir os valores e as configurações personalizadas podem ser encontradas no arquivo `helm-wp-aks-values.yaml`

1. Adicione o repositório Wordpress Bitnami Helm

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. Atualizar o cache do repositório Helm Chart local

    ```bash
    helm repo update
    ```

3. Instale a carga de trabalho do Wordpress via Helm executando o seguinte:

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

## Navegue pelo seu AKS Deployment Secured via HTTPS

Execute o seguinte comando para obter o ponto de extremidade HTTPS para seu aplicativo:

> [!NOTE]
> Muitas vezes leva 2-3 minutos para o certificado SSL propor e cerca de 5 minutos para ter todas as réplicas POD WordPress pronto e o site para ser totalmente acessível via https.

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

Verificar se o conteúdo do WordPress está sendo entregue corretamente.

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

O site pode ser visitado seguindo o URL abaixo:

```bash
echo "You can now visit your web server at https://$FQDN"
```
