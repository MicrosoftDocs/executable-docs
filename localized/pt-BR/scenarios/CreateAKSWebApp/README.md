---
title: Implantar um cluster escalonável e seguro do Serviço de Kubernetes do Azure usando a CLI do Azure
description: 'Neste tutorial, vamos guiá-lo passo a passo na criação de um Aplicativo Web do Azure Kubernetes protegido por HTTPS.'
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Início Rápido: Implantar um cluster escalonável e seguro do Serviço de Kubernetes do Azure usando a CLI do Azure

[![Implantar no Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/?Microsoft_Azure_CloudNative_clientoptimizations=false&feature.canmodifyextensions=true#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateAKSDeployment)

Bem-vindo a este tutorial, onde o orientaremos passo a passo na criação de um Aplicativo Web do Azure Kubernetes protegido por https. Este tutorial pressupõe que você já esteja conectado à CLI do Azure e tenha selecionado uma assinatura para usar com a CLI. Também pressupõe que você tenha o Helm instalado ([As instruções podem ser encontradas aqui](https://helm.sh/docs/intro/install/)).

## Definir Variáveis de Ambiente

A primeira etapa desse tutorial é definir as variáveis de ambiente.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export NETWORK_PREFIX="$(($RANDOM % 254 + 1))"
export SSL_EMAIL_ADDRESS="$(az account show --query user.name --output tsv)"
export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID"
export REGION="eastus"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_PUBLIC_IP_NAME="myPublicIP$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
export MY_VNET_NAME="myVNet$RANDOM_ID"
export MY_VNET_PREFIX="10.$NETWORK_PREFIX.0.0/16"
export MY_SN_NAME="mySN$RANDOM_ID"
export MY_SN_PREFIX="10.$NETWORK_PREFIX.0.0/22"
export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
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
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myAKSResourceGroupxxxxxx",
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

```JSON
{
  "newVNet": {
    "addressSpace": {
      "addressPrefixes": [
        "10.xxx.0.0/16"
      ]
    },
    "enableDdosProtection": false,
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/myAKSResourceGroupxxxxxx/providers/Microsoft.Network/virtualNetworks/myVNetxxx",
    "location": "eastus",
    "name": "myVNetxxx",
    "provisioningState": "Succeeded",
    "resourceGroup": "myAKSResourceGroupxxxxxx",
    "subnets": [
      {
        "addressPrefix": "10.xxx.0.0/22",
        "delegations": [],
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/myAKSResourceGroupxxxxxx/providers/Microsoft.Network/virtualNetworks/myVNetxxx/subnets/mySNxxx",
        "name": "mySNxxx",
        "privateEndpointNetworkPolicies": "Disabled",
        "privateLinkServiceNetworkPolicies": "Enabled",
        "provisioningState": "Succeeded",
        "resourceGroup": "myAKSResourceGroupxxxxxx",
        "type": "Microsoft.Network/virtualNetworks/subnets"
      }
    ],
    "type": "Microsoft.Network/virtualNetworks",
    "virtualNetworkPeerings": []
  }
}
```

## Registre-se nos Provedores de Recursos do Azure AKS

Verifique se os provedores Microsoft.OperationsManagement e Microsoft.OperationalInsights estão registrados em sua assinatura. Esses são os provedores de recursos do Azure necessários para dar suporte aos [insights de contêiner](https://docs.microsoft.com/azure/azure-monitor/containers/container-insights-overview). Para verificar o status do registro, execute os comandos a seguir

```bash
az provider register --namespace Microsoft.Insights
az provider register --namespace Microsoft.OperationsManagement
az provider register --namespace Microsoft.OperationalInsights
```

## Criar um cluster do AKS

Crie um cluster AKS usando o comando az aks create com o parâmetro --enable-addons monitoring para habilitar os insights de contêiner. O exemplo a seguir cria um cluster habilitado para zona de disponibilidade com dimensionamento automático.

Isto pode levar alguns minutos.

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

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"=$MY_DNS_LABEL \
  --set controller.service.loadBalancerIP=$MY_STATIC_IP \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
  --wait
```

## Implantar o aplicativo

Um arquivo de manifesto do Kubernetes define o estado desejado de um cluster, por exemplo, as imagens de contêiner a serem executadas.

Neste início rápido, você usará um manifesto para criar todos os objetos necessários para executar o aplicativo Azure Vote. Esse manifesto inclui duas implantações do Kubernetes:

- Os aplicativos Azure Vote de exemplo em Python.
- Uma instância do Redis.

Dois Serviços Kubernetes também são criados:

- Um serviço interno para a instância do Redis.
- Um serviço externo para acessar o aplicativo Azure Vote da Internet.

Por fim, um recurso de entrada é criado para rotear o tráfego para o aplicativo Azure Vote.

Um arquivo YML do aplicativo de votação de teste já está preparado. Para implantar esse aplicativo, execute o comando a seguir

```bash
kubectl apply -f azure-vote-start.yml
```

## Testar O Aplicativo

Valide se o aplicativo está em execução visitando o IP público ou o URL do aplicativo. O URL do aplicativo pode ser encontrado executando o seguinte comando:

> [!Note]
> Geralmente, leva de 2 a 3 minutos para que os PODs sejam criados e o site seja acessível por HTTP

```bash
runtime="5 minute";
endtime=$(date -ud "$runtime" +%s);
while [[ $(date -u +%s) -le $endtime ]]; do
   STATUS=$(kubectl get pods -l app=azure-vote-front -o 'jsonpath={..status.conditions[?(@.type=="Ready")].status}'); echo $STATUS;
   if [ "$STATUS" == 'True' ]; then
      break;
   else
      sleep 10;
   fi;
done
```

```bash
curl "http://$FQDN"
```

Resultados:

<!-- expected_similarity=0.3 -->

```HTML
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <link rel="stylesheet" type="text/css" href="/static/default.css">
    <title>Azure Voting App</title>

    <script language="JavaScript">
        function send(form){
        }
    </script>

</head>
<body>
    <div id="container">
        <form id="form" name="form" action="/"" method="post"><center>
        <div id="logo">Azure Voting App</div>
        <div id="space"></div>
        <div id="form">
        <button name="vote" value="Cats" onclick="send()" class="button button1">Cats</button>
        <button name="vote" value="Dogs" onclick="send()" class="button button2">Dogs</button>
        <button name="vote" value="reset" onclick="send()" class="button button3">Reset</button>
        <div id="space"></div>
        <div id="space"></div>
        <div id="results"> Cats - 0 | Dogs - 0 </div>
        </form>
        </div>
    </div>
</body>
</html>
```

## Adicionar terminação HTTPS ao domínio personalizado

Neste ponto do tutorial, você tem um aplicativo Web do AKS com o NGINX como Controlador de entrada e um domínio personalizado que pode usar para acessar seu aplicativo. A próxima etapa é adicionar um certificado SSL ao domínio para que os usuários possam acessar seu aplicativo com segurança por meio do HTTPS.

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

3. Instale o complemento Cert-Manager por meio do helm executando o seguinte:

   ```bash
   helm install cert-manager jetstack/cert-manager --namespace cert-manager --version v1.7.0
   ```

4. Aplicar o Arquivo YAML do Emissor de Certificado

   ClusterIssuers são recursos do Kubernetes que representam autoridades de certificação (CAs) capazes de gerar certificados assinados honrando as solicitações de assinatura do certificado. Todos os certificados cert-manager exigem um emissor referenciado que esteja em condições de tentar atender a solicitação.
   O emissor que estamos usando pode ser encontrado no `cluster-issuer-prod.yml file`

   ```bash
   cluster_issuer_variables=$(<cluster-issuer-prod.yml)
   echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
   ```

5. Atualize o aplicativo Voting App para usar o Cert-Manager para obter um certificado SSL.

   O arquivo YAML completo pode ser encontrado no `azure-vote-nginx-ssl.yml`

   ```bash
   azure_vote_nginx_ssl_variables=$(<azure-vote-nginx-ssl.yml)
   echo "${azure_vote_nginx_ssl_variables//\$FQDN/$FQDN}" | kubectl apply -f -
   ```

<!--## Validate application is working

Wait for the SSL certificate to issue. The following command will query the 
status of the SSL certificate for 3 minutes. In rare occasions it may take up to 
15 minutes for Lets Encrypt to issue a successful challenge and 
the ready state to be 'True'

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(kubectl get certificate --output jsonpath={..status.conditions[0].status}); echo $STATUS; if [ "$STATUS" = 'True' ]; then break; else sleep 10; fi; done
```

Validate SSL certificate is True by running the follow command:

```bash
kubectl get certificate --output jsonpath={..status.conditions[0].status}
```

Results:

<!-- expected_similarity=0.3 -->
<!--
```ASCII
True
```
-->

## Procurar sua implantação do AKS protegida por HTTPS

Execute o seguinte comando para obter o ponto de extremidade HTTPS para seu aplicativo:

> [!Note]
> Geralmente, leva de 2 a 3 minutos para que o certificado SSL seja proposto e o site seja acessível por HTTPS.

```bash
runtime="5 minute";
endtime=$(date -ud "$runtime" +%s);
while [[ $(date -u +%s) -le $endtime ]]; do
   STATUS=$(kubectl get svc --namespace=ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}');
   echo $STATUS;
   if [ "$STATUS" == "$MY_STATIC_IP" ]; then
      break;
   else
      sleep 10;
   fi;
done
```

```bash
echo "You can now visit your web server at https://$FQDN"
```

## Próximas etapas

- [Documentação do Serviço de Kubernetes do Azure](https://learn.microsoft.com/azure/aks/)
- [Criar um Registro de Contêiner do Azure](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-prepare-acr?tabs=azure-cli)
- [Dimensionar seu aplicativo no AKS](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-scale?tabs=azure-cli)
- [Atualizar seu aplicativo no AKS](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-app-update?tabs=azure-cli)