---
title: aks kümesini iş yükü kimliğiyle dağıtma ve yapılandırma
description: Bu Azure Kubernetes Service (AKS) makalesinde bir Azure Kubernetes Service kümesi dağıtıp bir Microsoft Entra İş Yükü Kimliği ile yapılandıracaksınız.
author: tamram
ms.topic: article
ms.subservice: aks-security
ms.custom: devx-track-azurecli
ms.date: 05/28/2024
ms.author: tamram
---

# Azure Kubernetes Service (AKS) kümesinde iş yükü kimliğini dağıtma ve yapılandırma

Azure Kubernetes Service (AKS), Kubernetes kümelerini hızla dağıtmanızı ve yönetmenizi sağlayan yönetilen bir Kubernetes hizmetidir. Bu makalede aşağıdaki işlemler hakkında bilgi edinirsiniz:

* OpenID Connect veren ve bir Microsoft Entra İş Yükü Kimliği ile Azure CLI kullanarak aks kümesi dağıtın.
* bir Microsoft Entra İş Yükü Kimliği ve Kubernetes hizmet hesabı oluşturun.
* Belirteç federasyonu için yönetilen kimliği yapılandırın.
* İş yükünü dağıtın ve iş yükü kimliğiyle kimlik doğrulamasını doğrulayın.
* İsteğe bağlı olarak kümedeki bir pod'a Azure anahtar kasasında gizli dizilere erişim izni verin.

Bu makalede Kubernetes kavramları hakkında temel bilgilere sahip olduğunuz varsayılır. Daha fazla bilgi için bkz [. Azure Kubernetes Service (AKS)][kubernetes-concepts] için Kubernetes temel kavramları. Microsoft Entra İş Yükü Kimliği hakkında bilginiz yoksa aşağıdaki [Genel Bakış][workload-identity-overview] makalesine bakın.

## Önkoşullar

* [!INCLUDE [quickstarts-free-trial-note](~/reusable-content/ce-skilling/azure/includes/quickstarts-free-trial-note.md)]
* Bu makale, Azure CLI'nın 2.47.0 veya sonraki bir sürümünü gerektirir. Azure Cloud Shell kullanılıyorsa en son sürüm zaten yüklüdür.
* Kümenizi oluşturmak için kullandığınız kimliğin uygun minimum izinlere sahip olduğundan emin olun. AKS'ye erişim ve kimlik hakkında daha fazla bilgi için bkz [. Azure Kubernetes Service (AKS)][aks-identity-concepts] için erişim ve kimlik seçenekleri.
* Birden çok Azure aboneliğiniz varsa az account set[ komutu kullanılarak ][az-account-set]kaynakların faturalandırılacağı uygun abonelik kimliğini seçin.

> [!NOTE]
> Bazı adımları otomatik olarak yapılandırmanıza yardımcı olması için Service Connector'ı_ kullanabilirsiniz_. Ayrıca bkz: Öğretici: [İş yükü kimliğini][tutorial-python-aks-storage-workload-identity] kullanarak Hizmet Bağlayıcısı ile Azure Kubernetes Service'te (AKS) Azure depolama hesabına bağlanma.

## Kaynak grubu oluşturma

[Azure kaynak grubu][azure-resource-group], Azure kaynaklarının dağıtıldığı ve yönetildiği mantıksal bir grupdur. Bir kaynak grubu oluşturduğunuzda, bir konum belirtmeniz istenir. Bu konum, kaynak grubu meta verilerinizin depolama konumudur ve kaynak oluşturma sırasında başka bir bölge belirtmezseniz kaynaklarınızın Azure'da çalıştırıldığı konumdur.

az group create komutunu çağırarak [bir kaynak grubu oluşturun][az-group-create] :

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export RESOURCE_GROUP="myResourceGroup$RANDOM_ID"
export LOCATION="centralindia"
az group create --name "${RESOURCE_GROUP}" --location "${LOCATION}"
```

Aşağıdaki çıkış örneği, bir kaynak grubunun başarıyla oluşturulmasını gösterir:

Sonuçlar:
<!-- expected_similarity=0.3 -->
```json
{
  "id": "/subscriptions/<guid>/resourceGroups/myResourceGroup",
  "location": "eastus",
  "managedBy": null,
  "name": "myResourceGroup",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## AKS kümesi oluşturma

OIDC vereni [etkinleştirmek için parametresiyle `--enable-oidc-issuer` az aks create][az-aks-create] komutunu kullanarak bir AKS kümesi oluşturun. Aşağıdaki örnek, tek düğümlü bir küme oluşturur:

```azurecli-interactive
export CLUSTER_NAME="myAKSCluster$RANDOM_ID"
az aks create \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity \
    --generate-ssh-keys
```

Birkaç dakika sonra komut tamamlanıp kümeyle ilgili JSON biçimli bilgileri döndürür.

> [!NOTE]
> AKS kümesi oluşturduğunuzda, AKS kaynaklarını depolamak için otomatik olarak ikinci bir kaynak grubu oluşturulur. Daha fazla bilgi için bkz. [AKS ile neden iki kaynak grubu oluşturulur?][aks-two-resource-groups].

## Mevcut AKS kümesini güncelleştirme

bir AKS kümesini OIDC vereni kullanacak şekilde güncelleştirebilir ve ve `--enable-workload-identity` parametreleriyle `--enable-oidc-issuer` az aks update[ komutunu çağırarak ][az aks update]iş yükü kimliğini etkinleştirebilirsiniz. Aşağıdaki örnek mevcut bir kümeyi güncelleştirir:

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity
```

## OIDC veren URL'sini alma

OIDC veren URL'sini almak ve bir ortam değişkenine kaydetmek için aşağıdaki komutu çalıştırın:

```azurecli-interactive
export AKS_OIDC_ISSUER="$(az aks show --name "${CLUSTER_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --query "oidcIssuerProfile.issuerUrl" \
    --output tsv)"
```

Ortam değişkeni, aşağıdaki örneğe benzer şekilde veren URL'yi içermelidir:

```output
https://eastus.oic.prod-aks.azure.com/00000000-0000-0000-0000-000000000000/11111111-1111-1111-1111-111111111111/
```

Veren varsayılan olarak, değerinin AKS kümesinin dağıtıldığı konumla eşleştiği `{region}` temel URL'yi `https://{region}.oic.prod-aks.azure.com/{tenant_id}/{uuid}`kullanacak şekilde ayarlanır. değeri `{uuid}` , sabit olan her küme için rastgele oluşturulan bir guid olan OIDC anahtarını temsil eder.

## Yönetilen kimlik oluşturma

[Yönetilen kimlik oluşturmak için az identity create][az-identity-create] komutunu çağırın.

```azurecli-interactive
export SUBSCRIPTION="$(az account show --query id --output tsv)"
export USER_ASSIGNED_IDENTITY_NAME="myIdentity$RANDOM_ID"
az identity create \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --location "${LOCATION}" \
    --subscription "${SUBSCRIPTION}"
```

Aşağıdaki çıkış örneğinde yönetilen kimliğin başarıyla oluşturulduğu gösterilmektedir:

Sonuçlar:
<!-- expected_similarity=0.3 -->
```output
{
  "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourcegroups/myResourceGroupxxxxxx/providers/Microsoft.ManagedIdentity/userAssignedIdentities/myIdentityxxxxxx",
  "location": "centralindia",
  "name": "myIdentityxxxxxx",
  "principalId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "resourceGroup": "myResourceGroupxxxxxx",
  "systemData": null,
  "tags": {},
  "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "type": "Microsoft.ManagedIdentity/userAssignedIdentities"
}
```

Ardından yönetilen kimliğin istemci kimliği için bir değişken oluşturun.

```azurecli-interactive
export USER_ASSIGNED_CLIENT_ID="$(az identity show \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --query 'clientId' \
    --output tsv)"
```

## Kubernetes hizmet hesabı oluşturma

Bir Kubernetes hizmet hesabı oluşturun ve önceki adımda oluşturulan yönetilen kimliğin istemci kimliğiyle buna ek açıklama ekleyin. [az aks get-credentials][az-aks-get-credentials] komutunu kullanın ve küme adı ile kaynak grubu adı değerlerini değiştirin.

```azurecli-interactive
az aks get-credentials --name "${CLUSTER_NAME}" --resource-group "${RESOURCE_GROUP}"
```

Aşağıdaki çok satırlı girişi kopyalayıp Azure CLI'ye yapıştırın.

```azurecli-interactive
export SERVICE_ACCOUNT_NAMESPACE="default"
export SERVICE_ACCOUNT_NAME="workload-identity-sa$RANDOM_ID"
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  annotations:
    azure.workload.identity/client-id: "${USER_ASSIGNED_CLIENT_ID}"
  name: "${SERVICE_ACCOUNT_NAME}"
  namespace: "${SERVICE_ACCOUNT_NAMESPACE}"
EOF
```

Aşağıdaki çıkışta iş yükü kimliğinin başarıyla oluşturulduğu gösterilmektedir:

```output
serviceaccount/workload-identity-sa created
```

## Federasyon kimliği kimlik bilgilerini oluşturma

[Yönetilen kimlik, hizmet hesabı veren ve konu arasında federasyon kimliği kimlik bilgilerini oluşturmak için az identity federated-credential create][az-identity-federated-credential-create] komutunu çağırın. Microsoft Entra'daki federasyon kimlik bilgileri hakkında daha fazla bilgi için bkz [. Microsoft Entra Id'de][federated-identity-credential] federasyon kimlik bilgilerine genel bakış.

```azurecli-interactive
export FEDERATED_IDENTITY_CREDENTIAL_NAME="myFedIdentity$RANDOM_ID"
az identity federated-credential create \
    --name ${FEDERATED_IDENTITY_CREDENTIAL_NAME} \
    --identity-name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --issuer "${AKS_OIDC_ISSUER}" \
    --subject system:serviceaccount:"${SERVICE_ACCOUNT_NAMESPACE}":"${SERVICE_ACCOUNT_NAME}" \
    --audience api://AzureADTokenExchange
```

> [!NOTE]
> Federasyon kimliği kimlik bilgilerinin eklendikten sonra yayılması birkaç saniye sürer. Federasyon kimliği kimlik bilgileri eklendikten hemen sonra bir belirteç isteği yapılırsa, önbellek yenilenene kadar istek başarısız olabilir. Bu sorunu önlemek için, federasyon kimliği kimlik bilgilerini ekledikten sonra biraz gecikme ekleyebilirsiniz.

## Uygulamanızı dağıtma

Uygulama podlarınızı dağıttığınızda bildirim, Kubernetes hizmet hesabı oluşturma adımında **oluşturulan hizmet hesabına** başvurmalıdır. Aşağıdaki bildirimde hesaba, özellikle metadata\namespace_ ve _spec\serviceAccountName_ özelliklerine _nasıl başvuracakları gösterilmektedir. için bir görüntü ve için `<image>` `<containerName>`kapsayıcı adı belirttiğinizden emin olun:

```bash
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: sample-workload-identity
  namespace: ${SERVICE_ACCOUNT_NAMESPACE}  # Replace with your namespace
  labels:
    azure.workload.identity/use: "true"  # Required. Only pods with this label can use workload identity.
spec:
  serviceAccountName: ${SERVICE_ACCOUNT_NAME}  # Replace with your service account name
  containers:
    - name: rabbitmq  # Replace with your container name
      image: mcr.microsoft.com/mirror/docker/library/rabbitmq:3.10-management-alpine  # Replace with your Docker image
      ports:
        - containerPort: 5672
          name: rabbitmq-amqp
        - containerPort: 15672
          name: rabbitmq-http
      env:
        - name: RABBITMQ_DEFAULT_USER
          value: "username"
        - name: RABBITMQ_DEFAULT_PASS
          value: "password"
      resources:
        requests:
          cpu: 10m
          memory: 128Mi
        limits:
          cpu: 250m
          memory: 256Mi
EOF
```

> [!IMPORTANT]
> İş yükü kimliği kullanan uygulama podlarının etiketi `azure.workload.identity/use: "true"` pod belirtiminde içerdiğinden emin olun. Aksi takdirde podlar yeniden başlatıldıktan sonra başarısız olur.

## Azure Key Vault'a erişim izinleri verme

Bu adımdaki yönergelerde, poddan azure anahtar kasasında gizli dizilere, anahtarlara veya sertifikalara nasıl erişirsiniz gösterilmektedir. Bu bölümdeki örnekler, iş yükü kimliği için anahtar kasasında gizli dizilere erişimi yapılandırabilir, ancak anahtarlara veya sertifikalara erişimi yapılandırmak için benzer adımları gerçekleştirebilirsiniz.

Aşağıdaki örnekte, anahtar kasasına pod erişimi vermek için Azure rol tabanlı erişim denetimi (Azure RBAC) izin modelinin nasıl kullanılacağı gösterilmektedir. Azure Key Vault için Azure RBAC izin modeli hakkında daha fazla bilgi için bkz [. Azure RBAC](/azure/key-vault/general/rbac-guide) kullanarak uygulamalara Azure anahtar kasasına erişim izni verme.

1. Temizleme koruması ve RBAC yetkilendirmesi etkinleştirilmiş bir anahtar kasası oluşturun. Hem temizleme koruması hem de RBAC yetkilendirmesi için yapılandırılmışsa mevcut bir anahtar kasasını da kullanabilirsiniz:

    ```azurecli-interactive
    export KEYVAULT_NAME="keyvault-workload-id$RANDOM_ID"
    # Ensure the key vault name is between 3-24 characters
    if [ ${#KEYVAULT_NAME} -gt 24 ]; then
        KEYVAULT_NAME="${KEYVAULT_NAME:0:24}"
    fi
    az keyvault create \
        --name "${KEYVAULT_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --location "${LOCATION}" \
        --enable-purge-protection \
        --enable-rbac-authorization 
    ```

1. Yeni anahtar kasasında gizli dizi oluşturabilmek için kendinize RBAC [Key Vault Gizli Dizileri Yetkilisi](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-officer) rolünü atayın:

    ```azurecli-interactive
    export KEYVAULT_RESOURCE_ID=$(az keyvault show --resource-group "${KEYVAULT_RESOURCE_GROUP}" \
        --name "${KEYVAULT_NAME}" \
        --query id \
        --output tsv)

    export CALLER_OBJECT_ID=$(az ad signed-in-user show --query objectId -o tsv)

    az role assignment create --assignee "${CALLER_OBJECT_ID}" \
    --role "Key Vault Secrets Officer" \
    --scope "${KEYVAULT_RESOURCE_ID}"
    ```

1. Anahtar kasasında gizli dizi oluşturma:

    ```azurecli-interactive
    export KEYVAULT_SECRET_NAME="my-secret$RANDOM_ID"
    az keyvault secret set \
        --vault-name "${KEYVAULT_NAME}" \
        --name "${KEYVAULT_SECRET_NAME}" \
        --value "Hello\!"
    ```

1. [Key Vault Gizli Dizileri Kullanıcı](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-user) rolünü daha önce oluşturduğunuz kullanıcı tarafından atanan yönetilen kimliğe atayın. Bu adım, yönetilen kimliğe anahtar kasasından gizli dizileri okuma izni verir:

    ```azurecli-interactive
    export IDENTITY_PRINCIPAL_ID=$(az identity show \
        --name "${USER_ASSIGNED_IDENTITY_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --query principalId \
        --output tsv)
    
    az role assignment create \
        --assignee-object-id "${IDENTITY_PRINCIPAL_ID}" \
        --role "Key Vault Secrets User" \
        --scope "${KEYVAULT_RESOURCE_ID}" \
        --assignee-principal-type ServicePrincipal
    ```

1. Anahtar kasası URL'si için bir ortam değişkeni oluşturun:

    ```azurecli-interactive
    export KEYVAULT_URL="$(az keyvault show \
        --resource-group ${RESOURCE_GROUP} \
        --name ${KEYVAULT_NAME} \
        --query properties.vaultUri \
        --output tsv)"
    ```

1. Hizmet hesabına ve anahtar kasası URL'sine başvuran bir pod dağıtın:

    ```bash
    cat <<EOF | kubectl apply -f -
    apiVersion: v1
    kind: Pod
    metadata:
    name: sample-workload-identity-key-vault
    namespace: ${SERVICE_ACCOUNT_NAMESPACE}
    labels:
        azure.workload.identity/use: "true"
    spec:
    serviceAccountName: ${SERVICE_ACCOUNT_NAME}
    containers:
        - image: ghcr.io/azure/azure-workload-identity/msal-go
        name: oidc
        env:
            - name: KEYVAULT_URL
            value: ${KEYVAULT_URL}
            - name: SECRET_NAME
            value: ${KEYVAULT_SECRET_NAME}
    nodeSelector:
        kubernetes.io/os: linux
    EOF
    ```

Tüm özelliklerin web kancası tarafından düzgün eklenip eklenmediğini denetlemek için kubectl describe[ komutunu kullanın][kubectl-describe]:

```azurecli-interactive
kubectl describe pod sample-workload-identity-key-vault | grep "SECRET_NAME:"
```

Başarılı olursa, çıkış aşağıdakine benzer olmalıdır:

```output
      SECRET_NAME:                 ${KEYVAULT_SECRET_NAME}
```

Pod'un belirteç alıp kaynağa erişebildiğini doğrulamak için kubectl logs komutunu kullanın:

```azurecli-interactive
kubectl logs sample-workload-identity-key-vault
```

Başarılı olursa, çıkış aşağıdakine benzer olmalıdır:

```output
I0114 10:35:09.795900       1 main.go:63] "successfully got secret" secret="Hello\\!"
```

> [!IMPORTANT]
> Azure RBAC rol atamalarının yayılması on dakika kadar sürebilir. Pod gizli diziye erişemezse rol atamasının yayılmasını beklemeniz gerekebilir. Daha fazla bilgi için bkz [. Azure RBAC](/azure/role-based-access-control/troubleshooting#) sorunlarını giderme.

## İş yükü kimliğini devre dışı bırakma

Etkinleştirildiği ve yapılandırıldığı AKS kümesinde Microsoft Entra İş Yükü Kimliği devre dışı bırakmak için aşağıdaki komutu çalıştırabilirsiniz:

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --disable-workload-identity
```

## Sonraki adımlar

Bu makalede bir Kubernetes kümesi dağıttınız ve bu kümeyi uygulama iş yüklerinin bu kimlik bilgileriyle kimlik doğrulaması için hazırlığında bir iş yükü kimliği kullanacak şekilde yapılandırdıysanız. Artık uygulamanızı dağıtmaya ve Azure Identity[ istemci kitaplığının en son sürümüyle iş yükü kimliğini kullanacak şekilde yapılandırmaya ][azure-identity-libraries]hazırsınız. Uygulamanızı en son istemci kitaplığı sürümünü kullanacak şekilde yeniden yazamıyorsanız, uygulama podunuzu[ kısa vadeli bir geçiş çözümü olarak iş yükü kimliğiyle yönetilen kimlik kullanarak kimlik doğrulaması yapmak üzere ayarlayabilirsiniz][workload-identity-migration].

[Hizmet Bağlayıcısı tümleştirmesi](/azure/service-connector/overview), AKS iş yükleri ve Azure yedekleme hizmetleri için bağlantı yapılandırmasını basitleştirmeye yardımcı olur. Kimlik doğrulaması ve ağ yapılandırmalarını güvenli bir şekilde işler ve Azure hizmetlerine bağlanmak için en iyi yöntemleri izler. Daha fazla bilgi için bkz [. İş Yükü Kimliğini](/azure/service-connector/tutorial-python-aks-openai-workload-identity) kullanarak AKS'de Azure OpenAI Hizmetine bağlanma ve Hizmet Bağlayıcısı'na [giriş](https://azure.github.io/AKS/2024/05/23/service-connector-intro).

<!-- EXTERNAL LINKS -->
[kubectl-describe]: https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#describe

<!-- INTERNAL LINKS -->
[kubernetes-concepts]: concepts-clusters-workloads.md
[workload-identity-overview]: workload-identity-overview.md
[azure-resource-group]: /azure/azure-resource-manager/management/overview
[az-group-create]: /cli/azure/group#az-group-create
[aks-identity-concepts]: concepts-identity.md
[federated-identity-credential]: /graph/api/resources/federatedidentitycredentials-overview
[tutorial-python-aks-storage-workload-identity]: /azure/service-connector/tutorial-python-aks-storage-workload-identity
[az-aks-create]: /cli/azure/aks#az-aks-create
[az aks update]: /cli/azure/aks#az-aks-update
[aks-two-resource-groups]: faq.yml
[az-account-set]: /cli/azure/account#az-account-set
[az-identity-create]: /cli/azure/identity#az-identity-create
[az-aks-get-credentials]: /cli/azure/aks#az-aks-get-credentials
[az-identity-federated-credential-create]: /cli/azure/identity/federated-credential#az-identity-federated-credential-create
[workload-identity-migration]: workload-identity-migrate-from-pod-identity.md
[azure-identity-libraries]: /azure/active-directory/develop/reference-v2-libraries