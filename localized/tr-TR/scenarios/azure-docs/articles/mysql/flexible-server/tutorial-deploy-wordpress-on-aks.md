---
title: 'Öğretici: Azure CLI kullanarak AKS kümesinde WordPress''i dağıtma'
description: MySQL için Azure Veritabanı - Esnek Sunucu ile AKS üzerinde WordPress'i hızlı bir şekilde oluşturmayı ve dağıtmayı öğrenin.
ms.service: mysql
ms.subservice: flexible-server
author: mksuni
ms.author: sumuth
ms.topic: tutorial
ms.date: 3/20/2024
ms.custom: 'vc, devx-track-azurecli, innovation-engine, linux-related-content'
---

# Öğretici: MySQL için Azure Veritabanı - Esnek Sunucu ile AKS'de WordPress uygulaması dağıtma

[!INCLUDE[applies-to-mysql-flexible-server](../includes/applies-to-mysql-flexible-server.md)]

[![Azure’a dağıtın](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262843)

Bu öğreticide, Azure CLI kullanarak esnek MySQL için Azure Veritabanı sunucuya sahip bir Azure Kubernetes Service (AKS) kümesinde HTTPS aracılığıyla güvenliği sağlanan ölçeklenebilir bir WordPress uygulaması dağıtacaksınız.
**[AKS](../../aks/intro-kubernetes.md)** , kümeleri hızla dağıtmanıza ve yönetmenize olanak tanıyan yönetilen bir Kubernetes hizmetidir. **[esnek sunucu](overview.md)** MySQL için Azure Veritabanı , veritabanı yönetimi işlevleri ve yapılandırma ayarları üzerinde daha ayrıntılı denetim ve esneklik sağlamak için tasarlanmış tam olarak yönetilen bir veritabanı hizmetidir.

> [!NOTE]
> Bu öğreticide Kubernetes kavramları, WordPress ve MySQL hakkında temel bilgiler edinirsiniz.

[!INCLUDE [flexible-server-free-trial-note](../includes/flexible-server-free-trial-note.md)]

## Önkoşullar 

Başlamadan önce Azure CLI'da oturum açtığınızdan ve CLI ile kullanmak üzere bir abonelik seçtiğinizden emin olun. Helm'in [yüklü](https://helm.sh/docs/intro/install/) olduğundan emin olun.

> [!NOTE]
> Bu öğreticideki komutları Azure Cloud Shell yerine yerel olarak çalıştırıyorsanız, komutları yönetici olarak çalıştırın.

## Kaynak grubu oluşturma

Azure kaynak grubu, Azure kaynaklarının dağıtıldığı ve yönetildiği mantıksal bir gruptur. Tüm kaynaklar bir kaynak grubuna yerleştirilmelidir. Aşağıdaki komut, önceden tanımlanmış `$MY_RESOURCE_GROUP_NAME` ve `$REGION` parametreleriyle bir kaynak grubu oluşturur.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myWordPressAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION
```

Sonuçlar:
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
> Kaynak grubunun konumu, kaynak grubu meta verilerinin depolandığı yerdir. Ayrıca kaynak oluşturma sırasında başka bir bölge belirtmezseniz kaynaklarınızın Azure'da çalıştığı yerdir.

## Sanal ağ ve alt ağ oluşturma

Sanal ağ, Azure'daki özel ağlar için temel yapı taşıdır. Azure Sanal Ağ, VM'ler gibi Azure kaynaklarının birbirleriyle ve İnternet ile güvenli bir şekilde iletişim kurmasını sağlar.

```bash
export NETWORK_PREFIX="$(($RANDOM % 253 + 1))"
export MY_VNET_PREFIX="10.$NETWORK_PREFIX.0.0/16"
export MY_SN_PREFIX="10.$NETWORK_PREFIX.0.0/22"
export MY_VNET_NAME="myVNet$RANDOM_ID"
export MY_SN_NAME="mySN$RANDOM_ID"
az network vnet create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --name $MY_VNET_NAME \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefixes $MY_SN_PREFIX
```

Sonuçlar:
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

## MySQL için Azure Veritabanı esnek sunucu örneği oluşturma

MySQL için Azure Veritabanı esnek sunucu, bulutta yüksek oranda kullanılabilir MySQL sunucularını çalıştırmak, yönetmek ve ölçeklendirmek için kullanabileceğiniz yönetilen bir hizmettir. az mysql flexible-server create komutuyla [MySQL için Azure Veritabanı esnek sunucu örneği oluşturun](/cli/azure/mysql/flexible-server). Bir sunucu birden çok veritabanı içerebilir. Aşağıdaki komut, Azure CLI'nızın yerel bağlamındaki hizmet varsayılanlarını ve değişken değerlerini kullanarak bir sunucu oluşturur:

```bash
export MY_MYSQL_ADMIN_USERNAME="dbadmin$RANDOM_ID"
export MY_WP_ADMIN_PW="$(openssl rand -base64 32)"
echo "Your MySQL user $MY_MYSQL_ADMIN_USERNAME password is: $MY_WP_ADMIN_PW" 
```

```bash
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
export MY_MYSQL_DB_NAME="mydb$RANDOM_ID"
export MY_MYSQL_ADMIN_PW="$(openssl rand -base64 32)"
export MY_MYSQL_SN_NAME="myMySQLSN$RANDOM_ID"
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

Sonuçlar:
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

Oluşturulan sunucu aşağıdaki özniteliklere sahiptir:

- Sunucu ilk kez sağlandığında yeni bir boş veritabanı oluşturulur.
- Sunucu adı, yönetici kullanıcı adı, yönetici parolası, kaynak grubu adı ve konum, bulut kabuğunun yerel bağlam ortamında zaten belirtilmiştir ve kaynak grubunuzla ve diğer Azure bileşenleriyle aynı konumdadır.
- Kalan sunucu yapılandırmaları için hizmet varsayılanları işlem katmanı (Serileştirilebilir), işlem boyutu/SKU (Standard_B2s), yedekleme saklama süresi (yedi gün) ve MySQL sürümü (8.0.21) şeklindedir.
- Varsayılan bağlantı yöntemi, bağlı bir sanal ağ ve otomatik oluşturulan bir alt ağ ile Özel erişim (sanal ağ tümleştirmesi) yöntemidir.

> [!NOTE]
> Sunucu oluşturulduktan sonra bağlantı yöntemi değiştirilemez. Örneğin, oluşturma sırasında seçtiyseniz `Private access (VNet Integration)` , oluşturulduktan sonra olarak `Public access (allowed IP addresses)` değiştiremezsiniz. Sanal Ağ Tümleştirmesi'ni kullanarak sunucunuza güvenli bir şekilde erişmek için Özel erişimli bir sunucu oluşturmanızı kesinlikle öneririz. Kavramlar makalesinde [](./concepts-networking-vnet.md)Özel erişim hakkında daha fazla bilgi edinin.

Varsayılan değerleri değiştirmek isterseniz, yapılandırılabilir CLI parametrelerinin tam listesi için Azure CLI [başvuru belgelerine bakın](/cli/azure//mysql/flexible-server) .

## MySQL için Azure Veritabanı - Esnek Sunucu durumunu denetleyin

MySQL için Azure Veritabanı Esnek Sunucu ve destekleyici kaynakların oluşturulması birkaç dakika sürer.

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## MySQL için Azure Veritabanı - Esnek Sunucuda sunucu parametrelerini yapılandırma

Sunucu parametrelerini kullanarak MySQL için Azure Veritabanı - Esnek Sunucu yapılandırmasını yönetebilirsiniz. Sunucu parametreleri, sunucuyu oluşturduğunuzda varsayılan ve önerilen değerle yapılandırılır.

Sunucunun belirli bir parametresiyle ilgili ayrıntıları göstermek için az mysql flexible-server parameter show[ komutunu çalıştırın](/cli/azure/mysql/flexible-server/parameter).

### MySQL için Azure Veritabanı devre dışı bırakma - WordPress tümleştirmesi için Esnek Sunucu SSL bağlantı parametresi

Ayrıca, MySQL sunucu altyapısının temel yapılandırma değerlerini güncelleştirmek için belirli sunucu parametrelerinin değerini değiştirebilirsiniz. Sunucu parametresini güncelleştirmek için az mysql flexible-server parameter set[ komutunu kullanın](/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set).

```bash
az mysql flexible-server parameter set \
    -g $MY_RESOURCE_GROUP_NAME \
    -s $MY_MYSQL_DB_NAME \
    -n require_secure_transport -v "OFF" -o JSON
```

Sonuçlar:
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

## AKS kümesi oluşturma

Container Insights ile aks kümesi oluşturmak için az aks create[ komutunu --enable-addons** monitoring parametresiyle **kullanın](/cli/azure/aks#az-aks-create). Aşağıdaki örnek myAKSCluster** adlı **otomatik ölçeklendirme, kullanılabilirlik alanı etkin bir küme oluşturur:

Bu işlem birkaç dakika sürer.

```bash
export MY_SN_ID=$(az network vnet subnet list --resource-group $MY_RESOURCE_GROUP_NAME --vnet-name $MY_VNET_NAME --query "[0].id" --output tsv)
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"

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
> AKS kümesi oluştururken AKS kaynaklarını depolamak için otomatik olarak ikinci bir kaynak grubu oluşturulur. Bkz. [AKS ile neden iki kaynak grubu oluşturulur?](../../aks/faq.md#why-are-two-resource-groups-created-with-aks)

## Kümeye bağlanma

Kubernetes kümesini yönetmek için Kubernetes komut satırı istemcisi [kubectl](https://kubernetes.io/docs/reference/kubectl/overview/)’i kullanın. Azure Cloud Shell kullanıyorsanız zaten `kubectl` yüklüdür. Aşağıdaki örnek az aks install-cli[ komutunu kullanarak ](/cli/azure/aks#az-aks-install-cli)yerel olarak yüklenir`kubectl`. 

 ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
```

Ardından az aks get-credentials[ komutunu kullanarak ](/cli/azure/aks#az-aks-get-credentials)Kubernetes kümenize bağlanacak şekilde yapılandırın`kubectl`. Bu komut kimlik bilgilerini indirir ve Kubernetes CLI'yi bunları kullanacak şekilde yapılandırmaktadır. komutu Kubernetes yapılandırma dosyası[ için ](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/)varsayılan konumu kullanır`~/.kube/config`. --file** bağımsız değişkenini kullanarak **Kubernetes yapılandırma dosyanız için farklı bir konum belirtebilirsiniz.

> [!WARNING]
> Bu komut, aynı girişe sahip tüm mevcut kimlik bilgilerinin üzerine yazar.

```bash
az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
```

Kümenize bağlantıyı doğrulamak için [kubectl get]( https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#get) komutunu kullanarak küme düğümleri listesini alın.

```bash
kubectl get nodes
```

## NGINX giriş denetleyicisini yükleme

Giriş denetleyicinizi statik genel IP adresiyle yapılandırabilirsiniz. Giriş denetleyicinizi silerseniz statik genel IP adresi kalır. AKS kümenizi silerseniz IP adresi kalmaz.
Giriş denetleyicinizi yükselttiğinizde, giriş denetleyicisi hizmetinin ona ayrılacak yük dengeleyiciyi tanımasını sağlamak için Helm sürümüne bir parametre geçirmeniz gerekir. HTTPS sertifikalarının düzgün çalışması için, giriş denetleyicisi IP adresi için tam etki alanı adı (FQDN) yapılandırmak üzere bir DNS etiketi kullanın. FQDN'niz şu formu izlemelidir: $MY_DNS_LABEL. AZURE_REGION_NAME.cloudapp.azure.com.

```bash
export MY_PUBLIC_IP_NAME="myPublicIP$RANDOM_ID"
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

Ardından, ingress-nginx Helm deposunu ekler, yerel Helm Grafiği depo önbelleğini güncelleştirir ve Helm aracılığıyla ingress-nginx eklentisini yüklersiniz. DNS etiketini --set controller.service.annotations ile **ayarlayabilirsiniz." service\.beta\.kubernetes\.io/azure-dns-label-name"="<DNS_LABEL>"** parametresi, giriş denetleyicisini veya sonraki bir sürümü ilk kez dağıttığınızda. Bu örnekte, önceki adımda oluşturduğunuz kendi genel IP adresinizi --set controller.service.loadBalancerIP="<STATIC_IP>" parametresiyle **** belirtirsiniz.

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

## Özel etki alanına HTTPS sonlandırma ekleme

Öğreticinin bu noktasında, giriş denetleyicisi olarak NGINX içeren bir AKS web uygulamanız ve uygulamanıza erişmek için kullanabileceğiniz özel bir etki alanınız vardır. Sonraki adım, kullanıcıların https üzerinden uygulamanıza güvenli bir şekilde ulaşabilmesi için etki alanına bir SSL sertifikası eklemektir.

### Sertifika Yöneticisini Ayarlama

HTTPS eklemek için Cert Manager'ı kullanacağız. Cert Manager, Kubernetes dağıtımları için SSL sertifikalarını almak ve yönetmek için açık kaynak bir araçtır. Cert Manager, popüler genel verenlerden ve özel verenlerden sertifika alır, sertifikaların geçerli ve güncel olmasını sağlar ve sertifikaları süresi dolmadan önce yapılandırılmış bir zamanda yenilemeye çalışır.

1. cert-manager'ı yüklemek için önce içinde çalıştırılacak bir ad alanı oluşturmamız gerekir. Bu öğretici cert-manager ad alanına cert-manager yükler. cert-manager'ı farklı bir ad alanında çalıştırabilirsiniz, ancak dağıtım bildirimlerinde değişiklik yapmanız gerekir.

    ```bash
    kubectl create namespace cert-manager
    ```

2. Artık cert-manager'ı yükleyebiliriz. Tüm kaynaklar tek bir YAML bildirim dosyasına eklenir. Bildirim dosyasını aşağıdaki komutla yükleyin:

    ```bash
    kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
    ```

3. `certmanager.k8s.io/disable-validation: "true"` Aşağıdakileri çalıştırarak etiketi cert-manager ad alanına ekleyin. Bu, cert-manager'ın kendi ad alanında oluşturulması için TLS'yi önyüklemesini gerektiren sistem kaynaklarını sağlar.

    ```bash
    kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
    ```

## Helm Charts aracılığıyla sertifika alma

Helm, kubernetes kümelerine uygulama ve hizmet oluşturma, paketleme, yapılandırma ve dağıtım işlemlerini otomatikleştirmeye yönelik bir Kubernetes dağıtım aracıdır.

Cert-manager, Kubernetes'te birinci sınıf bir yükleme yöntemi olarak Helm grafikleri sağlar.

1. Jetstack Helm deposunu ekleyin. Bu depo, cert-manager grafiklerinin desteklenen tek kaynağıdır. İnternet'te başka aynalar ve kopyalar vardır, ancak bunlar resmi değildir ve bir güvenlik riski sunabilir.

    ```bash
    helm repo add jetstack https://charts.jetstack.io
    ```

2. Yerel Helm Grafiği depo önbelleğini güncelleştirin.

    ```bash
    helm repo update
    ```

3. Helm aracılığıyla Cert-Manager eklentisini yükleyin.

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. Sertifika veren YAML dosyasını uygulayın. ClusterIssuers, sertifika imzalama isteklerine göre imzalı sertifikalar oluşturabilen sertifika yetkililerini (CA) temsil eden Kubernetes kaynaklarıdır. Tüm sertifika yöneticisi sertifikaları, isteği yerine getirme girişiminde bulunmak için hazır durumda olan, başvuruda bulunu olan bir veren gerektirir. içinde olduğumuz vereni `cluster-issuer-prod.yml file`bulabilirsiniz.

    ```bash
    export SSL_EMAIL_ADDRESS="$(az account show --query user.name --output tsv)"
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## Özel depolama sınıfı oluşturma

Varsayılan depolama sınıfları en yaygın senaryolara uygundur, ancak tümüne uygun değildir. Bazı durumlarda kendi depolama sınıfınızın kendi parametrelerinizle özelleştirilmesini isteyebilirsiniz. Örneğin, dosya paylaşımının **mountOptions'larını** yapılandırmak için aşağıdaki bildirimi kullanın.
FileMode ve dirMode**** için **varsayılan değer Kubernetes'e bağlı dosya paylaşımları için 0755'tir****.** Depolama sınıfı nesnesinde farklı bağlama seçeneklerini belirtebilirsiniz.

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## WORDPress'i AKS kümesine dağıtma

Bu öğreticide, Bitnami tarafından oluşturulan WordPress için mevcut bir Helm grafiğini kullanıyoruz. Bitnami Helm grafiği veritabanı olarak yerel bir MariaDB kullandığından, uygulamayı MySQL için Azure Veritabanı kullanmak için bu değerleri geçersiz kılmamız gerekir. Değerleri ve dosyanın özel ayarlarını `helm-wp-aks-values.yaml` geçersiz kılabilirsiniz.

1. Wordpress Bitnami Helm deposunu ekleyin.

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. Yerel Helm grafiği depo önbelleğini güncelleştirin.

    ```bash
    helm repo update
    ```

3. Helm aracılığıyla Wordpress iş yükünü yükleyin.

    ```bash
    export MY_MYSQL_HOSTNAME="$MY_MYSQL_DB_NAME.mysql.database.azure.com"
    export MY_WP_ADMIN_USER="wpcliadmin"
    export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
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

Sonuçlar:
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

## HTTPS aracılığıyla güvenliği sağlanan AKS dağıtımınıza göz atın

Uygulamanızın HTTPS uç noktasını almak için aşağıdaki komutu çalıştırın:

> [!NOTE]
> SSL sertifikasının yayılması genellikle 2-3 dakika ve tüm WordPress POD çoğaltmalarının hazır olması ve sitenin https üzerinden tam olarak ulaşılabilir olması yaklaşık 5 dakika sürer.

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

Aşağıdaki komutu kullanarak WordPress içeriğinin doğru teslimi olup olmadığını denetleyin:

```bash
if curl -I -s -f https://$FQDN > /dev/null ; then 
    curl -L -s -f https://$FQDN 2> /dev/null | head -n 9
else 
    exit 1
fi;
```

Sonuçlar:
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

Aşağıdaki URL aracılığıyla web sitesini ziyaret edin:

```bash
echo "You can now visit your web server at https://$FQDN"
```

## Kaynakları temizleme (isteğe bağlı)

Azure ücretlerinden kaçınmak için gereksiz kaynakları temizlemeniz gerekir. Kümeye artık ihtiyacınız kalmadığında az group delete[ komutunu kullanarak ](/cli/azure/group#az-group-delete)kaynak grubunu, kapsayıcı hizmetini ve tüm ilgili kaynakları kaldırın. 

> [!NOTE]
> Kümeyi sildiğinizde AKS kümesi tarafından kullanılan Microsoft Entra hizmet sorumlusu kaldırılmaz. Hizmet sorumlusunu kaldırma adımları için bkz. [AKS hizmet sorumlusuyla ilgili önemli noktalar ve silme](../../aks/kubernetes-service-principal.md#other-considerations). Yönetilen kimlik kullandıysanız, kimlik platform tarafından yönetilir ve kaldırılması gerekmez.

## Sonraki adımlar

- AKS kümeniz için Kubernetes web panosuna[ erişmeyi ](../../aks/kubernetes-dashboard.md)öğrenin
- Kümenizi ölçeklendirmeyi [öğrenin](../../aks/tutorial-kubernetes-scale.md)
- MySQL için Azure Veritabanı esnek sunucu örneğinizi [yönetmeyi öğrenin](./quickstart-create-server-cli.md)
- Veritabanı sunucunuz için sunucu parametrelerini[ yapılandırmayı ](./how-to-configure-server-parameters-cli.md)öğrenin
