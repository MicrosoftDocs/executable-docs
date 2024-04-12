---
title: 'Samouczek: wdrażanie platformy WordPress w klastrze usługi AKS przy użyciu interfejsu wiersza polecenia platformy Azure'
description: 'Dowiedz się, jak szybko kompilować i wdrażać platformę WordPress w usłudze AKS za pomocą usługi Azure Database for MySQL — serwer elastyczny.'
ms.service: mysql
ms.subservice: flexible-server
author: mksuni
ms.author: sumuth
ms.topic: tutorial
ms.date: 3/20/2024
ms.custom: 'vc, devx-track-azurecli, innovation-engine, linux-related-content'
---

# Samouczek: wdrażanie aplikacji WordPress w usłudze AKS przy użyciu usługi Azure Database for MySQL — serwer elastyczny

[!INCLUDE[applies-to-mysql-flexible-server](../includes/applies-to-mysql-flexible-server.md)]

[![Wdróż na platformie Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262843)

W tym samouczku wdrożysz skalowalną aplikację WordPress zabezpieczoną za pośrednictwem protokołu HTTPS w klastrze usługi Azure Kubernetes Service (AKS) przy użyciu elastycznego serwera usługi Azure Database for MySQL przy użyciu interfejsu wiersza polecenia platformy Azure.
**[Usługa AKS](../../aks/intro-kubernetes.md)** to zarządzana usługa Kubernetes, która umożliwia szybkie wdrażanie klastrów i zarządzanie nimi. **[Serwer elastyczny](overview.md)** usługi Azure Database for MySQL to w pełni zarządzana usługa bazy danych, która zapewnia bardziej szczegółową kontrolę i elastyczność funkcji zarządzania bazami danych i ustawień konfiguracji.

> [!NOTE]
> W tym samouczku założono podstawową wiedzę na temat pojęć związanych z platformą Kubernetes, platformą WordPress i bazą danych MySQL.

[!INCLUDE [flexible-server-free-trial-note](../includes/flexible-server-free-trial-note.md)]

## Wymagania wstępne 

Przed rozpoczęciem upewnij się, że zalogowano się do interfejsu wiersza polecenia platformy Azure i wybrano subskrypcję do użycia z interfejsem wiersza polecenia. Upewnij się, że masz [zainstalowany](https://helm.sh/docs/intro/install/) program Helm.

> [!NOTE]
> Jeśli uruchamiasz polecenia w tym samouczku lokalnie zamiast usługi Azure Cloud Shell, uruchom polecenia jako administrator.

## Definiowanie zmiennych środowiskowych

Pierwszym krokiem w tym samouczku jest zdefiniowanie zmiennych środowiskowych.

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

## Tworzenie grupy zasobów

Grupa zasobów platformy Azure to logiczna grupa przeznaczona do wdrażania zasobów platformy Azure i zarządzania nimi. Wszystkie zasoby należy umieścić w grupie zasobów. Następujące polecenie tworzy grupę zasobów z wcześniej zdefiniowanymi `$MY_RESOURCE_GROUP_NAME` parametrami i `$REGION` .

```bash
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION
```

Wyniki:
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
> Lokalizacja grupy zasobów to miejsce przechowywania metadanych grupy zasobów. Jest to również miejsce, w którym zasoby są uruchamiane na platformie Azure, jeśli nie określisz innego regionu podczas tworzenia zasobów.

## Tworzenie sieci wirtualnej i podsieci

Sieć wirtualna to podstawowy blok konstrukcyjny dla sieci prywatnych na platformie Azure. Usługa Azure Virtual Network umożliwia zasobom platformy Azure, takich jak maszyny wirtualne, bezpieczne komunikowanie się ze sobą i Internetem.

```bash
az network vnet create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --name $MY_VNET_NAME \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefixes $MY_SN_PREFIX
```

Wyniki:
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

## Tworzenie wystąpienia elastycznego serwera usługi Azure Database for MySQL

Serwer elastyczny usługi Azure Database for MySQL to usługa zarządzana, której można używać do uruchamiania serwerów MySQL o wysokiej dostępności i zarządzania nimi w chmurze. Utwórz wystąpienie serwera elastycznego usługi Azure Database for MySQL za [pomocą polecenia az mysql flexible-server create](/cli/azure/mysql/flexible-server) . Serwer może zawierać wiele baz danych. Następujące polecenie tworzy serwer przy użyciu wartości domyślnych usługi i zmiennych z lokalnego kontekstu interfejsu wiersza polecenia platformy Azure:

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

Wyniki:
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

Utworzony serwer ma następujące atrybuty:

- Podczas pierwszej aprowizacji serwera jest tworzona nowa pusta baza danych.
- Nazwa serwera, nazwa użytkownika administratora, hasło administratora, nazwa grupy zasobów i lokalizacja są już określone w lokalnym środowisku kontekstowym usługi Cloud Shell i znajdują się w tej samej lokalizacji co grupa zasobów i inne składniki platformy Azure.
- Wartością domyślną usługi dla pozostałych konfiguracji serwera są warstwa obliczeniowa (z możliwością skalowania), rozmiar obliczeniowy/jednostka SKU (Standard_B2s), okres przechowywania kopii zapasowych (siedem dni) i wersja programu MySQL (8.0.21).
- Domyślną metodą łączności jest dostęp prywatny (integracja sieci wirtualnej) z połączoną siecią wirtualną i automatycznie wygenerowaną podsiecią.

> [!NOTE]
> Nie można zmienić metody łączności po utworzeniu serwera. Jeśli na przykład wybrano podczas `Private access (VNet Integration)` tworzenia, nie można zmienić wartości na `Public access (allowed IP addresses)` po utworzeniu. Zdecydowanie zalecamy utworzenie serwera z dostępem prywatnym, aby bezpiecznie uzyskać dostęp do serwera przy użyciu integracji z siecią wirtualną. Dowiedz się więcej o dostępie prywatnym w [artykule](./concepts-networking-vnet.md) pojęcia.

Jeśli chcesz zmienić ustawienia domyślne, zapoznaj się z dokumentacją[ referencyjną interfejsu wiersza polecenia platformy Azure, aby uzyskać pełną listę konfigurowalnych parametrów interfejsu wiersza polecenia](/cli/azure//mysql/flexible-server).

## Sprawdzanie stanu usługi Azure Database for MySQL — serwer elastyczny

Utworzenie usługi Azure Database for MySQL — serwera elastycznego i zasobów pomocniczych trwa kilka minut.

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## Konfigurowanie parametrów serwera w usłudze Azure Database for MySQL — serwer elastyczny

Konfigurację usługi Azure Database for MySQL — serwer elastyczny można zarządzać przy użyciu parametrów serwera. Parametry serwera są konfigurowane z wartością domyślną i zalecaną podczas tworzenia serwera.

Aby wyświetlić szczegółowe informacje na temat określonego parametru dla serwera, uruchom [polecenie az mysql flexible-server parameter show](/cli/azure/mysql/flexible-server/parameter) .

### Wyłączanie parametru połączenia SSL usługi Azure Database for MySQL — serwer elastyczny na potrzeby integracji z platformą WordPress

Można również zmodyfikować wartość niektórych parametrów serwera, aby zaktualizować bazowe wartości konfiguracji aparatu serwera MySQL. Aby zaktualizować parametr serwera, użyj [polecenia az mysql flexible-server parameter set](/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set) .

```bash
az mysql flexible-server parameter set \
    -g $MY_RESOURCE_GROUP_NAME \
    -s $MY_MYSQL_DB_NAME \
    -n require_secure_transport -v "OFF" -o JSON
```

Wyniki:
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

## Tworzenie klastra AKS

Aby utworzyć klaster usługi AKS przy użyciu usługi Container Szczegółowe informacje, użyj [polecenia az aks create](/cli/azure/aks#az-aks-create) z parametrem **monitorowania --enable-addons**. Poniższy przykład tworzy klaster z obsługą skalowania automatycznego z obsługą strefy dostępności o nazwie **myAKSCluster**:

Ta akcja trwa kilka minut.

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
> Podczas tworzenia klastra usługi AKS druga grupa zasobów jest tworzona automatycznie w celu przechowywania zasobów usługi AKS. Zobacz [Dlaczego dwie grupy zasobów są tworzone za pomocą usługi AKS?](../../aks/faq.md#why-are-two-resource-groups-created-with-aks)

## Łączenie z klastrem

Aby zarządzać klastrem Kubernetes, należy użyć klienta wiersza polecenia usługi Kubernetes — narzędzia [kubectl](https://kubernetes.io/docs/reference/kubectl/overview/). Jeśli korzystasz z usługi Azure Cloud Shell, narzędzie `kubectl` jest już zainstalowane. Poniższy przykład instaluje `kubectl` lokalnie przy użyciu [polecenia az aks install-cli](/cli/azure/aks#az-aks-install-cli) . 

 ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
```

Następnie skonfiguruj polecenie `kubectl` az aks get-credentials[, aby nawiązać połączenie z klastrem ](/cli/azure/aks#az-aks-get-credentials)Kubernetes. To polecenie powoduje pobranie poświadczeń i zastosowanie ich w konfiguracji interfejsu wiersza polecenia Kubernetes. W poleceniu jest używana `~/.kube/config`lokalizacja [domyślna pliku](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/) konfiguracji kubernetes. Możesz określić inną lokalizację pliku konfiguracji platformy Kubernetes przy użyciu argumentu **--file** .

> [!WARNING]
> To polecenie spowoduje zastąpienie wszystkich istniejących poświadczeń przy użyciu tego samego wpisu.

```bash
az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
```

Aby sprawdzić połączenie z klastrem, użyj polecenia [kubectl get]( https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#get), aby powrócić do listy węzłów klastra.

```bash
kubectl get nodes
```

## Instalowanie kontrolera ruchu przychodzącego NGINX

Kontroler ruchu przychodzącego można skonfigurować przy użyciu statycznego publicznego adresu IP. Statyczny publiczny adres IP pozostaje w przypadku usunięcia kontrolera ruchu przychodzącego. Adres IP nie pozostanie, jeśli usuniesz klaster usługi AKS.
Podczas uaktualniania kontrolera ruchu przychodzącego należy przekazać parametr do wydania programu Helm, aby upewnić się, że usługa kontrolera ruchu przychodzącego jest świadoma modułu równoważenia obciążenia, który zostanie mu przydzielony. Aby certyfikaty HTTPS działały poprawnie, użyj etykiety DNS, aby skonfigurować w pełni kwalifikowaną nazwę domeny (FQDN) dla adresu IP kontrolera ruchu przychodzącego. Nazwa FQDN powinna mieć następującą postać: $MY_DNS_LABEL. AZURE_REGION_NAME.cloudapp.azure.com.

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

Następnie należy dodać repozytorium ingress-nginx Helm, zaktualizować lokalną pamięć podręczną repozytorium programu Helm Chart i zainstalować dodatek ingress-nginx za pośrednictwem programu Helm. Etykietę DNS można ustawić za **pomocą --set controller.service.annotations". \.parametr\.usługi beta kubernetes\.io/azure-dns-label-name"="<DNS_LABEL>"** podczas pierwszego wdrażania kontrolera ruchu przychodzącego lub nowszego. W tym przykładzie określisz własny publiczny adres IP utworzony w poprzednim kroku za pomocą parametru ****--set controller.service.loadBalancerIP="<STATIC_IP>".

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

## Dodawanie zakończenia protokołu HTTPS do domeny niestandardowej

W tym momencie w samouczku masz aplikację internetową usługi AKS z serwerem NGINX jako kontrolerem ruchu przychodzącego i domeną niestandardową, której można użyć do uzyskiwania dostępu do aplikacji. Następnym krokiem jest dodanie certyfikatu SSL do domeny, aby użytkownicy mogli bezpiecznie uzyskać dostęp do aplikacji za pośrednictwem protokołu HTTPS.

### Konfigurowanie menedżera certyfikatów

Aby dodać protokół HTTPS, użyjemy menedżera certyfikatów. Cert Manager to narzędzie typu open source do uzyskiwania certyfikatów SSL dla wdrożeń platformy Kubernetes i zarządzania nimi. Menedżer certyfikatów uzyskuje certyfikaty od popularnych publicznych wystawców i prywatnych wystawców, zapewnia, że certyfikaty są prawidłowe i aktualne oraz próbuje odnowić certyfikaty w skonfigurowanym czasie przed ich wygaśnięciem.

1. Aby zainstalować program cert-manager, musimy najpierw utworzyć przestrzeń nazw, aby ją uruchomić. W tym samouczku program cert-manager jest instalowany w przestrzeni nazw menedżera certyfikatów. Program cert-manager można uruchomić w innej przestrzeni nazw, ale należy wprowadzić modyfikacje manifestów wdrożenia.

    ```bash
    kubectl create namespace cert-manager
    ```

2. Teraz możemy zainstalować program cert-manager. Wszystkie zasoby znajdują się w jednym pliku manifestu YAML. Zainstaluj plik manifestu za pomocą następującego polecenia:

    ```bash
    kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
    ```

3. Dodaj etykietę `certmanager.k8s.io/disable-validation: "true"` do przestrzeni nazw menedżera certyfikatów, uruchamiając następujące polecenie. Dzięki temu zasoby systemowe wymagane przez menedżera certyfikatów wymagają uruchomienia protokołu TLS do utworzenia we własnej przestrzeni nazw.

    ```bash
    kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
    ```

## Uzyskiwanie certyfikatu za pomocą pakietów Helm

Helm to narzędzie wdrażania platformy Kubernetes służące do automatyzowania tworzenia, tworzenia, pakowania, konfigurowania i wdrażania aplikacji i usług w klastrach Kubernetes.

Narzędzie Cert-manager udostępnia wykresy Helm jako pierwszą klasę instalacji na platformie Kubernetes.

1. Dodaj repozytorium Jetstack Helm. To repozytorium jest jedynym obsługiwanym źródłem wykresów cert-manager. Istnieją inne lustra i kopie w Internecie, ale są one nieoficjalne i mogą stanowić zagrożenie bezpieczeństwa.

    ```bash
    helm repo add jetstack https://charts.jetstack.io
    ```

2. Zaktualizuj lokalną pamięć podręczną repozytorium programu Helm Chart.

    ```bash
    helm repo update
    ```

3. Zainstaluj dodatek Cert-Manager za pośrednictwem programu Helm.

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. Zastosuj plik YAML wystawcy certyfikatu. Klastry są zasobami Kubernetes reprezentującymi urzędy certyfikacji, które mogą generować podpisane certyfikaty, honorując żądania podpisywania certyfikatów. Wszystkie certyfikaty menedżera certyfikatów wymagają wystawcy, do którego odwołuje się odwołanie, który jest w stanie gotowości, aby spróbować rozpoznać żądanie. Możesz znaleźć wystawcę, którego używamy w elemencie `cluster-issuer-prod.yaml file`.

    ```bash
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## Tworzenie niestandardowej klasy magazynu

Domyślne klasy magazynu odpowiadają najbardziej typowym scenariuszom, ale nie wszystkim. W niektórych przypadkach możesz chcieć dostosować własną klasę magazynu z własnymi parametrami. Na przykład użyj następującego manifestu, aby skonfigurować instalacjęOpcje **** udziału plików.
Wartość domyślna dla **funkcji fileMode** i **dirMode** to **0755** dla zainstalowanych udziałów plików platformy Kubernetes. Można określić różne opcje instalacji w obiekcie klasy magazynu.

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## Wdrażanie platformy WordPress w klastrze usługi AKS

W tym samouczku używamy istniejącego wykresu Helm dla platformy WordPress utworzonego przez rozwiązanie Bitnami. Wykres Narzędzia Helm Bitnami używa lokalnej bazy danych MariaDB jako bazy danych, dlatego musimy zastąpić te wartości, aby używać aplikacji z usługą Azure Database for MySQL. Możesz zastąpić wartości i ustawienia `helm-wp-aks-values.yaml` niestandardowe pliku.

1. Dodaj repozytorium Wordpress Bitnami Helm.

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. Zaktualizuj lokalną pamięć podręczną repozytorium pakietów Helm.

    ```bash
    helm repo update
    ```

3. Zainstaluj obciążenie Wordpress za pośrednictwem programu Helm.

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

Wyniki:
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

## Przeglądanie wdrożenia usługi AKS zabezpieczonego za pośrednictwem protokołu HTTPS

Uruchom następujące polecenie, aby uzyskać punkt końcowy HTTPS dla aplikacji:

> [!NOTE]
> Propagacja certyfikatu SSL trwa często 2–3 minuty i około 5 minut, aby wszystkie repliki ZASOBnika WordPress mogły być gotowe, a witryna jest w pełni dostępna za pośrednictwem protokołu https.

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

Sprawdź, czy zawartość platformy WordPress jest dostarczana poprawnie przy użyciu następującego polecenia:

```bash
if curl -I -s -f https://$FQDN > /dev/null ; then 
    curl -L -s -f https://$FQDN 2> /dev/null | head -n 9
else 
    exit 1
fi;
```

Wyniki:
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

Odwiedź witrynę internetową za pomocą następującego adresu URL:

```bash
echo "You can now visit your web server at https://$FQDN"
```

## Czyszczenie zasobów (opcjonalnie)

Aby uniknąć opłat za platformę Azure, należy wyczyścić niepotrzebne zasoby. Gdy klaster nie jest już potrzebny, użyj [polecenia az group delete](/cli/azure/group#az-group-delete) , aby usunąć grupę zasobów, usługę kontenera i wszystkie powiązane zasoby. 

> [!NOTE]
> Po usunięciu klastra jednostka usługi Microsoft Entra używana przez klaster usługi AKS nie zostanie usunięta. Aby sprawdzić, jak usunąć jednostkę usługi, zobacz [AKS service principal considerations and deletion (Uwagi dotyczące jednostki usługi AKS i jej usuwanie)](../../aks/kubernetes-service-principal.md#other-considerations). Jeśli użyto tożsamości zarządzanej, tożsamość jest zarządzana przez platformę i nie wymaga usunięcia.

## Następne kroki

- Dowiedz się, jak uzyskać dostęp do [internetowego pulpitu nawigacyjnego](../../aks/kubernetes-dashboard.md) platformy Kubernetes dla klastra usługi AKS
- Dowiedz się, jak skalować [klaster](../../aks/tutorial-kubernetes-scale.md)
- Dowiedz się, jak zarządzać wystąpieniem serwera elastycznego [usługi Azure Database for MySQL](./quickstart-create-server-cli.md)
- Dowiedz się, jak skonfigurować [parametry](./how-to-configure-server-parameters-cli.md) serwera dla serwera bazy danych