---
title: AKS'de Ölçeklenebilir ve Güvenli WordPress örneği dağıtma
description: Bu öğreticide CLI aracılığıyla AKS'de Ölçeklenebilir ve Güvenli Bir WordPress örneğinin nasıl dağıtılacağı gösterilmektedir
author: adrian.joian
ms.author: adrian.joian
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Hızlı Başlangıç: AKS'de Ölçeklenebilir ve Güvenli WordPress örneği dağıtma

Https aracılığıyla güvenliği sağlanan bir Azure Kubernetes Web Uygulaması oluşturma adım adım size adım adım izleyebileceğiniz bu öğreticiye hoş geldiniz. Bu öğreticide, Azure CLI'de zaten oturum açtığınız ve CLI ile kullanmak üzere bir abonelik seçtiğiniz varsayılır. Ayrıca Helm'in yüklü olduğu varsayılır ([Yönergeler burada](https://helm.sh/docs/intro/install/) bulunabilir).

## Ortam Değişkenlerini Tanımlama

Bu öğreticinin ilk adımı ortam değişkenlerini tanımlamaktır.

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

## Kaynak grubu oluşturma

Kaynak grubu, ilgili kaynaklar için bir kapsayıcıdır. Tüm kaynaklar bir kaynak grubuna yerleştirilmelidir. Bu öğretici için bir tane oluşturacağız. Aşağıdaki komut, önceden tanımlanmış $MY_RESOURCE_GROUP_NAME ve $REGION parametreleriyle bir kaynak grubu oluşturur.

```bash
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

## Sanal ağ ve alt ağ oluşturma

Sanal ağ, Azure'daki özel ağlar için temel yapı taşıdır. Azure Sanal Ağ, VM'ler gibi Azure kaynaklarının birbirleriyle ve İnternet ile güvenli bir şekilde iletişim kurmasını sağlar.

```bash
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

## MySQL için Azure Veritabanı Oluşturma - Esnek Sunucu

MySQL için Azure Veritabanı - Esnek Sunucu, bulutta yüksek oranda kullanılabilir MySQL sunucularını çalıştırmak, yönetmek ve ölçeklendirmek için kullanabileceğiniz bir yönetilen hizmettir. az mysql flexible-server create komutuyla [esnek bir sunucu oluşturun](https://learn.microsoft.com/cli/azure/mysql/flexible-server#az-mysql-flexible-server-create) . Bir sunucu birden çok veritabanı içerebilir. Aşağıdaki komut, Azure CLI'nızın yerel ortamındaki hizmet varsayılanlarını ve değişken değerlerini kullanarak bir sunucu oluşturur:

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

- Sunucu adı, yönetici kullanıcı adı, yönetici parolası, kaynak grubu adı, konum bulut kabuğunun yerel bağlam ortamında zaten belirtilmiştir ve kaynak grubu ve diğer Azure bileşenleriyle aynı konumda oluşturulur.
- Kalan sunucu yapılandırmaları için hizmet varsayılanları: işlem katmanı (Serileştirilebilir), işlem boyutu/SKU (Standard_B2s), yedekleme saklama süresi (7 gün) ve MySQL sürümü (8.0.21)
- Varsayılan bağlantı yöntemi, bağlı bir sanal ağ ve otomatik olarak oluşturulan bir alt ağ ile Özel erişimdir (VNet Tümleştirmesi).

> [!NOTE]
> Sunucu oluşturulduktan sonra bağlantı yöntemi değiştirilemez. Örneğin, oluşturma sırasında seçtiyseniz `Private access (VNet Integration)` , oluşturma sonrasında olarak `Public access (allowed IP addresses)` değiştiremezsiniz. Sanal Ağ Tümleştirmesi'ni kullanarak sunucunuza güvenli bir şekilde erişmek için Özel erişimli bir sunucu oluşturmanızı kesinlikle öneririz. Kavramlar makalesinde [](https://learn.microsoft.com/azure/mysql/flexible-server/concepts-networking-vnet)Özel erişim hakkında daha fazla bilgi edinin.

Varsayılan değerleri değiştirmek isterseniz yapılandırılabilir CLI parametrelerinin tam listesi için lütfen Azure CLI [başvuru belgelerine bakın](https://learn.microsoft.com/cli/azure//mysql/flexible-server) .

## MySQL için Azure Veritabanı - Esnek Sunucu durumunu denetleyin

MySQL için Azure Veritabanı Esnek Sunucu ve destekleyici kaynakların oluşturulması birkaç dakika sürer.

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## MySQL için Azure Veritabanı - Esnek Sunucuda sunucu parametrelerini yapılandırma

Sunucu parametrelerini kullanarak MySQL için Azure Veritabanı - Esnek Sunucu yapılandırmasını yönetebilirsiniz. Sunucu parametreleri, sunucuyu oluşturduğunuzda varsayılan ve önerilen değerle yapılandırılır.

Sunucu parametresi ayrıntılarını göster Sunucunun [belirli bir parametresi hakkındaki ayrıntıları göstermek için az mysql flexible-server parameter show](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter) komutunu çalıştırın.

### MySQL için Azure Veritabanı devre dışı bırakma - WordPress tümleştirmesi için Esnek Sunucu SSL bağlantı parametresi

Ayrıca, MySQL sunucu altyapısı için temel yapılandırma değerlerini güncelleştiren belirli sunucu parametrelerinin değerini de değiştirebilirsiniz. Sunucu parametresini güncelleştirmek için az mysql flexible-server parameter set[ komutunu kullanın](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set).

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

## AKS Kümesi Oluşturma

Kapsayıcı içgörülerini etkinleştirmek için --enable-addons izleme parametresiyle az aks create komutunu kullanarak bir AKS kümesi oluşturun. Aşağıdaki örnek, myAKSCluster adlı otomatik ölçeklendirme, kullanılabilirlik alanı etkin bir küme oluşturur:

Bu işlem birkaç dakika sürer

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

## Kümeye bağlanma

Kubernetes kümesini yönetmek için kubectl adlı Kubernetes komut satırı istemcisini kullanın. Azure Cloud Shell kullanıyorsanız kubectl zaten yüklüdür.

1. az aks install-cli komutunu kullanarak az aks CLI'yi yerel olarak yükleme

    ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
    ```

2. az aks get-credentials komutunu kullanarak kubectl'yi Kubernetes kümenize bağlanacak şekilde yapılandırın. Aşağıdaki komut:

    - Kimlik bilgilerini indirir ve Kubernetes CLI'sini bunları kullanacak şekilde yapılandırılır.
    - Kubernetes yapılandırma dosyasının varsayılan konumu olan ~/.kube/config kullanır. --file bağımsız değişkenini kullanarak Kubernetes yapılandırma dosyanız için farklı bir konum belirtin.

    > [!WARNING]
    > Bu, aynı girişe sahip mevcut kimlik bilgilerinin üzerine yazar

    ```bash
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
    ```

3. kubectl get komutunu kullanarak kümenize bağlantıyı doğrulayın. Bu komut, küme düğümlerinin listesini döndürür.

    ```bash
    kubectl get nodes
    ```

## NGINX Giriş Denetleyicisini Yükleme

Giriş denetleyicinizi statik genel IP adresiyle yapılandırabilirsiniz. Giriş denetleyicinizi silerseniz statik genel IP adresi kalır. AKS kümenizi silerseniz IP adresi kalmaz.
Giriş denetleyicinizi yükselttiğinizde, giriş denetleyicisi hizmetinin ona ayrılacak yük dengeleyiciyi tanımasını sağlamak için Helm sürümüne bir parametre geçirmeniz gerekir. HTTPS sertifikalarının düzgün çalışması için, giriş denetleyicisi IP adresi için bir FQDN yapılandırmak üzere bir DNS etiketi kullanırsınız.
FQDN'niz şu formu izlemelidir: $MY_DNS_LABEL. AZURE_REGION_NAME.cloudapp.azure.com.

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

--set controller.service.annotations ekleyin." service\.beta\.kubernetes\.io/azure-dns-label-name"="<DNS_LABEL>" parametresi. DNS etiketi, giriş denetleyicisi ilk dağıtıldığında ayarlanabilir veya daha sonra yapılandırılabilir. --set controller.service.loadBalancerIP="<STATIC_IP>" parametresini ekleyin. Önceki adımda oluşturulan kendi genel IP adresinizi belirtin.

1. ingress-nginx Helm deposunu ekleme

    ```bash
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    ```

2. Yerel Helm Grafiği depo önbelleğini güncelleştirme

    ```bash
    helm repo update
    ```

3. Aşağıdakileri çalıştırarak Helm aracılığıyla ingress-nginx eklentisini yükleyin:

    ```bash
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

## Sertifika Yöneticisini Ayarlama

HTTPS eklemek için Cert Manager'ı kullanacağız. Cert Manager, Kubernetes dağıtımları için SSL sertifikası almak ve yönetmek için kullanılan bir açık kaynak aracıdır. Sertifika Yöneticisi, hem popüler genel Verenler hem de özel Verenler olmak üzere çeşitli Verenlerden sertifika alır ve sertifikaların geçerli ve güncel olduğundan emin olur ve sertifikaları süresi dolmadan önce yapılandırılmış bir zamanda yenilemeyi dener.

1. cert-manager'ı yüklemek için önce içinde çalıştırılacak bir ad alanı oluşturmamız gerekir. Bu öğretici cert-manager ad alanına cert-manager yükler. Dağıtım bildirimlerinde değişiklik yapmanız gerekse de cert-manager'ı farklı bir ad alanında çalıştırmak mümkündür.

    ```bash
    kubectl create namespace cert-manager
    ```

2. Artık cert-manager'ı yükleyebiliriz. Tüm kaynaklar tek bir YAML bildirim dosyasına eklenir. Bu, aşağıdakiler çalıştırılarak yüklenebilir:

    ```bash
    kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
    ```

3. Aşağıdakini çalıştırarak cert-manager ad alanına certmanager.k8s.io/disable-validation: "true" etiketini ekleyin. Bu, cert-manager'ın kendi ad alanında oluşturulması için TLS'yi önyüklemesini gerektiren sistem kaynaklarını sağlar.

    ```bash
    kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
    ```

## Helm Charts aracılığıyla sertifika alma

Helm, kubernetes kümelerine uygulama ve hizmet oluşturma, paketleme, yapılandırma ve dağıtımı otomatikleştirmeye yönelik bir Kubernetes dağıtım aracıdır.

Cert-manager, Kubernetes'te birinci sınıf bir yükleme yöntemi olarak Helm grafikleri sağlar.

1. Jetstack Helm deposunu ekleme

    Bu depo, cert-manager grafiklerinin desteklenen tek kaynağıdır. İnternet'te başka aynalar ve kopyalar vardır, ancak bunlar tamamen resmi değildir ve bir güvenlik riski sunabilir.

    ```bash
    helm repo add jetstack https://charts.jetstack.io
    ```

2. Yerel Helm Grafiği depo önbelleğini güncelleştirme

    ```bash
    helm repo update
    ```

3. Aşağıdakileri çalıştırarak Helm aracılığıyla Cert-Manager eklentisini yükleyin:

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. Sertifika Veren YAML Dosyası Uygula

    ClusterIssuers, sertifika imzalama isteklerine göre imzalı sertifikalar oluşturabilen sertifika yetkililerini (CA) temsil eden Kubernetes kaynaklarıdır. Tüm sertifika yöneticisi sertifikaları, isteği yerine getirme girişiminde bulunmak için hazır durumda olan, başvuruda bulunu olan bir veren gerektirir.
    Kullanmakta olduğumuz veren, `cluster-issuer-prod.yml file`

    ```bash
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## Özel depolama sınıfı oluşturma

Varsayılan depolama sınıfları en yaygın senaryolara uygundur, ancak tümüne uygun değildir. Bazı durumlarda kendi depolama sınıfınızın kendi parametrelerinizle özelleştirilmesini isteyebilirsiniz. Örneğin, dosya paylaşımının mountOptions'larını yapılandırmak için aşağıdaki bildirimi kullanın.
FileMode ve dirMode için varsayılan değer Kubernetes'e bağlı dosya paylaşımları için 0755'tir. Depolama sınıfı nesnesinde farklı bağlama seçeneklerini belirtebilirsiniz.

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## WORDPress'i AKS kümesine dağıtma

Bu belge için, Bitnami tarafından oluşturulan wordpress için mevcut helm grafiğini kullanıyoruz. Örneğin Bitnami Helm grafiği veritabanı olarak yerel MariaDB kullanır ve uygulamayı MySQL için Azure Veritabanı kullanmak için bu değerleri geçersiz kılmamız gerekir. Tüm geçersiz kılma değerleri Değerleri geçersiz kılabilirsiniz ve özel ayarlar dosyada bulunabilir `helm-wp-aks-values.yaml`

1. Wordpress Bitnami Helm deposunu ekleme

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. Yerel Helm Grafiği depo önbelleğini güncelleştirme

    ```bash
    helm repo update
    ```

3. Aşağıdakileri çalıştırarak Helm aracılığıyla Wordpress iş yükünü yükleyin:

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

## HTTPS ile Güvenliği Sağlanan AKS Dağıtımınıza Göz Atın

Uygulamanızın HTTPS uç noktasını almak için aşağıdaki komutu çalıştırın:

> [!NOTE]
> SSL sertifikasının kullanıma alınması genellikle 2-3 dakika, tüm WordPress POD çoğaltmalarının hazır olması ve sitenin https üzerinden tam olarak ulaşılabilir olması yaklaşık 5 dakika sürer.

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

WordPress içeriğinin doğru teslim edildiğini denetleme.

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

Web sitesi aşağıdaki URL'ye uyularak ziyaret edilebilir:

```bash
echo "You can now visit your web server at https://$FQDN"
```
