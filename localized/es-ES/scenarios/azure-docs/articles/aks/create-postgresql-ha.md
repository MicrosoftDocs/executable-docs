---
title: Creación de una infraestructura para implementar una base de datos PostgreSQL de alta disponibilidad en AKS
description: Cree la infraestructura necesaria para implementar una base de datos PostgreSQL de alta disponibilidad en AKS mediante el operador CloudNativePG.
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# Creación de una infraestructura para implementar una base de datos PostgreSQL de alta disponibilidad en AKS

En este artículo, creará la infraestructura necesaria para implementar una base de datos PostgreSQL de alta disponibilidad en AKS mediante el operador [CloudNativePG (CNPG)](https://cloudnative-pg.io/).

## Antes de empezar

* Revise la información general sobre la implementación y asegúrese de cumplir todos los requisitos previos que se enumeran en [Procedimiento para implementar una base de datos PostgreSQL de alta disponibilidad en AKS con la CLI de Azure][postgresql-ha-deployment-overview].
* [Establezca variables de entorno](#set-environment-variables) para su uso en esta guía.
* [Instale las extensiones necesarias](#install-required-extensions).

## Establecimiento de variables de entorno

Establezca las siguientes variables de entorno para usarlas en esta guía:

```bash
export SUFFIX=$(cat /dev/urandom | LC_ALL=C tr -dc 'a-z0-9' | fold -w 8 | head -n 1)
export LOCAL_NAME="cnpg"
export TAGS="owner=user"
export RESOURCE_GROUP_NAME="rg-${LOCAL_NAME}-${SUFFIX}"
export PRIMARY_CLUSTER_REGION="westus3"
export AKS_PRIMARY_CLUSTER_NAME="aks-primary-${LOCAL_NAME}-${SUFFIX}"
export AKS_PRIMARY_MANAGED_RG_NAME="rg-${LOCAL_NAME}-primary-aksmanaged-${SUFFIX}"
export AKS_PRIMARY_CLUSTER_FED_CREDENTIAL_NAME="pg-primary-fedcred1-${LOCAL_NAME}-${SUFFIX}"
export AKS_PRIMARY_CLUSTER_PG_DNSPREFIX=$(echo $(echo "a$(openssl rand -hex 5 | cut -c1-11)"))
export AKS_UAMI_CLUSTER_IDENTITY_NAME="mi-aks-${LOCAL_NAME}-${SUFFIX}"
export AKS_CLUSTER_VERSION="1.29"
export PG_NAMESPACE="cnpg-database"
export PG_SYSTEM_NAMESPACE="cnpg-system"
export PG_PRIMARY_CLUSTER_NAME="pg-primary-${LOCAL_NAME}-${SUFFIX}"
export PG_PRIMARY_STORAGE_ACCOUNT_NAME="hacnpgpsa${SUFFIX}"
export PG_STORAGE_BACKUP_CONTAINER_NAME="backups"
export ENABLE_AZURE_PVC_UPDATES="true"
export MY_PUBLIC_CLIENT_IP=$(dig +short myip.opendns.com @resolver3.opendns.com)
```

## Instalación de las extensiones necesarias

Las extensiones `aks-preview`, `k8s-extension` y `amg` proporcionan más funcionalidad para administrar clústeres de Kubernetes y consultar recursos de Azure. Instale estas extensiones mediante los siguientes comandos [`az extension add`][az-extension-add]:

```bash
az extension add --upgrade --name aks-preview --yes --allow-preview true
az extension add --upgrade --name k8s-extension --yes --allow-preview false
az extension add --upgrade --name amg --yes --allow-preview false
```

Como requisito previo para usar kubectl, es esencial instalar primero [Krew][install-krew] y después instalar el [complemento CNPG][cnpg-plugin]. Esto habilitará la administración del operador de PostgreSQL mediante los siguientes comandos.

```bash
(
  set -x; cd "$(mktemp -d)" &&
  OS="$(uname | tr '[:upper:]' '[:lower:]')" &&
  ARCH="$(uname -m | sed -e 's/x86_64/amd64/' -e 's/\(arm\)\(64\)\?.*/\1\2/' -e 's/aarch64$/arm64/')" &&
  KREW="krew-${OS}_${ARCH}" &&
  curl -fsSLO "https://github.com/kubernetes-sigs/krew/releases/latest/download/${KREW}.tar.gz" &&
  tar zxvf "${KREW}.tar.gz" &&
  ./"${KREW}" install krew
)

export PATH="${KREW_ROOT:-$HOME/.krew}/bin:$PATH"

kubectl krew install cnpg
```

## Crear un grupo de recursos

Cree un grupo de recursos para contener los recursos creados en esta guía mediante el comando [`az group create`][az-group-create].

```bash
az group create \
    --name $RESOURCE_GROUP_NAME \
    --location $PRIMARY_CLUSTER_REGION \
    --tags $TAGS \
    --query 'properties.provisioningState' \
    --output tsv
```

## Creación de una identidad administrada asignada por el usuario

En esta sección, creará una identidad administrada asignada por el usuario (UAMI) para permitir que el operador CNPG de PostgreSQL use una identidad de carga de trabajo de AKS para acceder a Azure Blob Storage. Esta configuración permite que el clúster de PostgreSQL en AKS se conecte a Azure Blob Storage sin un secreto.

1. Use el comando [`az identity create`][az-identity-create] para crear una identidad administrada asignada por el usuario.

    ```bash
    AKS_UAMI_WI_IDENTITY=$(az identity create \
        --name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --output json)
    ```

1. Habilite la identidad de carga de trabajo de AKS y genere una cuenta de servicio para usarla más adelante en esta guía mediante los siguientes comandos:

    ```bash
    export AKS_UAMI_WORKLOAD_OBJECTID=$( \
        echo "${AKS_UAMI_WI_IDENTITY}" | jq -r '.principalId')
    export AKS_UAMI_WORKLOAD_RESOURCEID=$( \
        echo "${AKS_UAMI_WI_IDENTITY}" | jq -r '.id')
    export AKS_UAMI_WORKLOAD_CLIENTID=$( \
        echo "${AKS_UAMI_WI_IDENTITY}" | jq -r '.clientId')

    echo "ObjectId: $AKS_UAMI_WORKLOAD_OBJECTID"
    echo "ResourceId: $AKS_UAMI_WORKLOAD_RESOURCEID"
    echo "ClientId: $AKS_UAMI_WORKLOAD_CLIENTID"
    ```

El id. de objeto es un identificador único para el id. de cliente (también conocido como id. de aplicación) que identifica de forma única una entidad de seguridad de tipo *Aplicación* en el inquilino de Entra ID. El id. de recurso es un identificador único para administrar y localizar un recurso en Azure. Estos valores son necesarios para habilitar la identidad de carga de trabajo de AKS.

El operador CNPG genera automáticamente una cuenta de servicio denominada *postgres* que usará más adelante en la guía para crear una credencial federada que permita el acceso OAuth desde PostgreSQL a Azure Storage.

## Creación de una cuenta de almacenamiento en la región principal

1. Cree una cuenta de almacenamiento de objetos para almacenar copias de seguridad de PostgreSQL en la región principal mediante el comando [`az storage account create`][az-storage-account-create].

    ```bash
    az storage account create \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --sku Standard_ZRS \
        --kind StorageV2 \
        --query 'provisioningState' \
        --output tsv
    ```

1. Cree el contenedor de almacenamiento para almacenar los registros de escritura anticipada (WAL) y las copias de seguridad programadas y a petición normales de PostgreSQL mediante el comando [`az storage container create`][az-storage-container-create].

    ```bash
    az storage container create \
        --name $PG_STORAGE_BACKUP_CONTAINER_NAME \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --auth-mode login
    ```

    Ejemplo:

    ```output
    {
        "created": true
    }
    ```

    > [!NOTE]
    > Podría recibir el mensaje de error: `The request may be blocked by network rules of storage account. Please check network rule set using 'az storage account show -n accountname --query networkRuleSet'. If you want to change the default action to apply when no rule matches, please use 'az storage account update'`. En este caso, compruebe los permisos de usuario de Azure Blob Storage y, si es **necesario**, eleve su rol a `Storage Blob Data Owner` mediante los comandos proporcionados a continuación. Después, pruebe de nuevo el comando [`az storage container create`][az-storage-container-create].

    ```bash
    az role assignment list --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID --output table

    export USER_ID=$(az ad signed-in-user show --query id --output tsv)

    export STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID=$(az storage account show \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "id" \
        --output tsv)

    az role assignment create \
        --assignee-object-id $USER_ID \
        --assignee-principal-type User \
        --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID \
        --role "Storage Blob Data Owner" \
        --output tsv
    ```

## Asignación de RBAC a cuentas de almacenamiento

Para habilitar las copias de seguridad, el clúster de PostgreSQL debe leer y escribir en un almacén de objetos. El clúster de PostgreSQL que se ejecuta en AKS usa una identidad de carga de trabajo para acceder a la cuenta de almacenamiento mediante el parámetro [`inheritFromAzureAD`][inherit-from-azuread] de configuración del operador CNPG.

1. Obtenga el id. del recurso principal de la cuenta de almacenamiento mediante el comando [`az storage account show`][az-storage-account-show].

    ```bash
    export STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID=$(az storage account show \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "id" \
        --output tsv)

    echo $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID
    ````

1. Asigne el rol integrado de Azure "Colaborador de datos de Storage Blob" al id. de objeto con el ámbito del id. de recurso de la cuenta de almacenamiento para la UAMI asociada a la identidad administrada para cada clúster de AKS mediante el comando [`az role assignment create`][az-role-assignment-create].

    ```bash
    az role assignment create \
        --role "Storage Blob Data Contributor" \
        --assignee-object-id $AKS_UAMI_WORKLOAD_OBJECTID \
        --assignee-principal-type ServicePrincipal \
        --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID \
        --query "id" \
        --output tsv
    ```

## Configuración de la infraestructura de supervisión

En esta sección, implementará una instancia de Azure Managed Grafana, un área de trabajo de Azure Monitor y un área de trabajo de Log Analytics de Azure Monitor para habilitar la supervisión del clúster de PostgreSQL. También almacenará referencias a la infraestructura de supervisión creada para usarlas como entrada durante el proceso de creación del clúster de AKS más adelante en esta guía. Puede tardar algún tiempo en completar esta sección.

> [!NOTE]
> Las instancias de Azure Managed Grafana y los clústeres de AKS se facturan de forma independiente. Para obtener más información sobre los precios, consulte [Precios de Azure Managed Grafana][azure-managed-grafana-pricing].

1. Cree una instancia de Azure Managed Grafana mediante el comando [`az grafana create`][az-grafana-create].

    ```bash
    export GRAFANA_PRIMARY="grafana-${LOCAL_NAME}-${SUFFIX}"

    export GRAFANA_RESOURCE_ID=$(az grafana create \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $GRAFANA_PRIMARY \
        --location $PRIMARY_CLUSTER_REGION \
        --zone-redundancy Enabled \
        --tags $TAGS \
        --query "id" \
        --output tsv)

    echo $GRAFANA_RESOURCE_ID
    ```

1. Cree un área de trabajo de Azure Monitor mediante el comando [`az monitor account create`][az-monitor-account-create].

    ```bash
    export AMW_PRIMARY="amw-${LOCAL_NAME}-${SUFFIX}"

    export AMW_RESOURCE_ID=$(az monitor account create \
        --name $AMW_PRIMARY \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --tags $TAGS \
        --query "id" \
        --output tsv)

    echo $AMW_RESOURCE_ID
    ```

1. Cree un área de trabajo de Log Analytics de Azure Monitor mediante el comando [`az monitor log-analytics workspace create`][az-monitor-log-analytics-workspace-create].

    ```bash
    export ALA_PRIMARY="ala-${LOCAL_NAME}-${SUFFIX}"

    export ALA_RESOURCE_ID=$(az monitor log-analytics workspace create \
        --resource-group $RESOURCE_GROUP_NAME \
        --workspace-name $ALA_PRIMARY \
        --location $PRIMARY_CLUSTER_REGION \
        --query "id" \
        --output tsv)

    echo $ALA_RESOURCE_ID
    ```

## Creación del clúster de AKS para hospedar el clúster de PostgreSQL

En esta sección, creará un clúster de AKS de varias zonas con un grupo de nodos del sistema. El clúster de AKS hospeda la réplica principal del clúster de PostgreSQL y dos réplicas en espera, cada una alineada con una zona de disponibilidad diferente para habilitar la redundancia zonal.

También agregará un grupo de nodos de usuario al clúster de AKS para hospedar el clúster de PostgreSQL. El uso de un grupo de nodos independiente permite controlar las SKU de máquina virtual de Azure que se usan para PostgreSQL y permite que el grupo del sistema de AKS optimice el rendimiento y los costos. Aplicará una etiqueta al grupo de nodos de usuario al que puede hacer referencia para la selección de nodos al implementar el operador CNPG más adelante en esta guía. Puede tardar algún tiempo en completar esta sección.

1. Cree un clúster de AKS con el comando [`az aks create`][az-aks-create].

    ```bash
    export SYSTEM_NODE_POOL_VMSKU="standard_d2s_v3"
    export USER_NODE_POOL_NAME="postgres"
    export USER_NODE_POOL_VMSKU="standard_d4s_v3"
    
    az aks create \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --tags $TAGS \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --generate-ssh-keys \
        --node-resource-group $AKS_PRIMARY_MANAGED_RG_NAME \
        --enable-managed-identity \
        --assign-identity $AKS_UAMI_WORKLOAD_RESOURCEID \
        --network-plugin azure \
        --network-plugin-mode overlay \
        --network-dataplane cilium \
        --nodepool-name systempool \
        --enable-oidc-issuer \
        --enable-workload-identity \
        --enable-cluster-autoscaler \
        --min-count 2 \
        --max-count 3 \
        --node-vm-size $SYSTEM_NODE_POOL_VMSKU \
        --enable-azure-monitor-metrics \
        --azure-monitor-workspace-resource-id $AMW_RESOURCE_ID \
        --grafana-resource-id $GRAFANA_RESOURCE_ID \
        --api-server-authorized-ip-ranges $MY_PUBLIC_CLIENT_IP \
        --tier standard \
        --kubernetes-version $AKS_CLUSTER_VERSION \
        --zones 1 2 3 \
        --output table
    ```

2. Agregue un grupo de nodos al clúster de AKS mediante el comando [`az aks nodepool add`][az-aks-node-pool-add].

    ```bash
    az aks nodepool add \
        --resource-group $RESOURCE_GROUP_NAME \
        --cluster-name $AKS_PRIMARY_CLUSTER_NAME \
        --name $USER_NODE_POOL_NAME \
        --enable-cluster-autoscaler \
        --min-count 3 \
        --max-count 6 \
        --node-vm-size $USER_NODE_POOL_VMSKU \
        --zones 1 2 3 \
        --labels workload=postgres \
        --output table
    ```

> [!NOTE]
> Si recibe el mensaje de error `"(OperationNotAllowed) Operation is not allowed: Another operation (Updating) is in progress, please wait for it to finish before starting a new operation."` al agregar el grupo de nodos de AKS, espere unos minutos para que se completen las operaciones del clúster de AKS y ejecute el comando `az aks nodepool add`.

## Conexión al clúster de AKS y creación de espacios de nombres

En esta sección, obtendrá las credenciales del clúster de AKS, que sirven como las claves que le permiten autenticarse e interactuar con el clúster. Una vez conectado, cree dos espacios de nombres: uno para los servicios de administrador de controladores de CNPG y otro para el clúster de PostgreSQL y sus servicios relacionados.

1. Obtenga las credenciales del clúster de AKS mediante el comando [`az aks get-credentials`][az-aks-get-credentials].

    ```bash
    az aks get-credentials \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --output none
     ```

2. Cree el espacio de nombres para los servicios de administrador de controladores de CNPG, el clúster de PostgreSQL y sus servicios relacionados mediante el comando [`kubectl create namespace`][kubectl-create-namespace].

    ```bash
    kubectl create namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    kubectl create namespace $PG_SYSTEM_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## Actualización de la infraestructura de supervisión

El área de trabajo de Azure Monitor para Prometheus administrado y Azure Managed Grafana se vinculan automáticamente al clúster de AKS para las métricas y la visualización durante el proceso de creación del clúster. En esta sección, habilitará la recopilación de registros con AKS Container Insights y validará que Prometheus administrado está extrayendo métricas y que Container Insights está ingiriendo registros.

1. Habilite la supervisión de Container Insights en el clúster de AKS mediante el comando [`az aks enable-addons`][az-aks-enable-addons].

    ```bash
    az aks enable-addons \
        --addon monitoring \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --workspace-resource-id $ALA_RESOURCE_ID \
        --output table
    ```

2. Compruebe que Prometheus administrado está extrayendo métricas y Container Insights está ingiriendo registros desde el clúster de AKS; para ello, inspeccione el controlador DaemonSet mediante los comandos [`kubectl get`][kubectl-get] y [`az aks show`][az-aks-show].

    ```bash
    kubectl get ds ama-metrics-node \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace=kube-system

    kubectl get ds ama-logs \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace=kube-system

    az aks show \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --query addonProfiles
    ```

    La salida debería ser similar a la siguiente salida de ejemplo, con *seis* nodos en total (tres para el grupo de nodos del sistema y tres para el grupo de nodos de PostgreSQL), y Container Insights debería mostrar `"enabled": true`:

    ```output
    NAME               DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR
    ama-metrics-node   6         6         6       6            6           <none>       

    NAME               DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR
    ama-logs           6         6         6       6            6           <none>       

    {
      "omsagent": {
        "config": {
          "logAnalyticsWorkspaceResourceID": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-cnpg-9vbin3p8/providers/Microsoft.OperationalInsights/workspaces/ala-cnpg-9vbin3p8",
          "useAADAuth": "true"
        },
        "enabled": true,
        "identity": null
      }
    }
    ```

## Creación de una dirección IP estática pública para la entrada del clúster de PostgreSQL

Para validar la implementación del clúster de PostgreSQL y usar herramientas de PostgreSQL de cliente, como *psql* y *PgAdmin*, debe exponer las réplicas principales y de solo lectura a la entrada. En esta sección, creará un recurso de dirección IP pública de Azure que más adelante proporcionará a un equilibrador de carga de Azure para exponer los puntos de conexión de PostgreSQL para su consulta.

1. Obtenga el nombre del grupo de recursos del nodo de clúster de AKS mediante el comando [`az aks show`][az-aks-show].

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME=$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query nodeResourceGroup \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME
    ```

2. Use el comando [`az network public-ip create`][az-network-public-ip-create] para crear la dirección IP pública.

    ```bash
    export AKS_PRIMARY_CLUSTER_PUBLICIP_NAME="$AKS_PRIMARY_CLUSTER_NAME-pip"

    az network public-ip create \
        --resource-group $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --name $AKS_PRIMARY_CLUSTER_PUBLICIP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --sku Standard \
        --zone 1 2 3 \
        --allocation-method static \
        --output table
    ```

3. Obtenga la dirección IP pública recién creada mediante el comando [`az network public-ip show`][az-network-public-ip-show].

    ```bash
    export AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS=$(az network public-ip show \
        --resource-group $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --name $AKS_PRIMARY_CLUSTER_PUBLICIP_NAME \
        --query ipAddress \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS
    ```

4. Obtenga el id. de recurso del grupo de recursos del nodo mediante el comando [`az group show`][az-group-show].

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE=$(az group show --name \
        $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --query id \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE
    ```

5. Asigne el rol "Colaborador de red" al id. de objeto de la UAMI mediante el ámbito del grupo de recursos del nodo con el comando [`az role assignment create`][az-role-assignment-create].

    ```bash
    az role assignment create \
        --assignee-object-id ${AKS_UAMI_WORKLOAD_OBJECTID} \
        --assignee-principal-type ServicePrincipal \
        --role "Network Contributor" \
        --scope ${AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE}
    ```

## Instalación del operador CNPG en el clúster de AKS

En esta sección, instalará el operador CNPG en el clúster de AKS mediante Helm o un manifiesto YAML.

### [Helm](#tab/helm)

1. Agregue el repositorio de Helm de CNPG mediante el comando [`helm repo add`][helm-repo-add].

    ```bash
    helm repo add cnpg https://cloudnative-pg.github.io/charts
    ```

2. Actualice el repositorio de Helm de CNPG e instálelo en el clúster de AKS mediante el comando [`helm upgrade`][helm-upgrade] con la marca `--install`.

    ```bash
    helm upgrade --install cnpg \
        --namespace $PG_SYSTEM_NAMESPACE \
        --create-namespace \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME \
        cnpg/cloudnative-pg
    ```

3. Compruebe la instalación del operador en el clúster de AKS mediante el comando [`kubectl get`][kubectl-get].

    ```bash
    kubectl get deployment \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-cloudnative-pg
    ```

### [YAML](#tab/yaml)

1. Instale el operador CNPG en el clúster de AKS mediante el comando [`kubectl apply`][kubectl-apply].

    ```bash
    kubectl apply --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE \
        --server-side -f \
        https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.23/releases/cnpg-1.23.1.yaml
    ```

2. Compruebe la instalación del operador en el clúster de AKS mediante el comando [`kubectl get`][kubectl-get].

    ```bash
    kubectl get deployment \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-controller-manager \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

---

## Pasos siguientes

> [!div class="nextstepaction"]
> [Implementación de una base de datos PostgreSQL de alta disponibilidad en el clúster de AKS][deploy-postgresql]

## Colaboradores

*Microsoft mantiene este artículo. Originalmente fue escrito por los siguientes colaboradores*:

* Ken Kilty | TPM de entidad de seguridad
* Russell de Pina | TPM de entidad de seguridad
* Adrian Joian | Ingeniero de clientes sénior
* Jenny Hayes | Desarrollador de contenido sénior
* Carol Smith | Desarrollador de contenido sénior
* Erin Schaffer | Desarrollador de contenido 2

<!-- LINKS -->
[az-identity-create]: /cli/azure/identity#az-identity-create
[az-grafana-create]: /cli/azure/grafana#az-grafana-create
[postgresql-ha-deployment-overview]: ./postgresql-ha-overview.md
[az-extension-add]: /cli/azure/extension#az_extension_add
[az-group-create]: /cli/azure/group#az_group_create
[az-storage-account-create]: /cli/azure/storage/account#az_storage_account_create
[az-storage-container-create]: /cli/azure/storage/container#az_storage_container_create
[inherit-from-azuread]: https://cloudnative-pg.io/documentation/1.23/appendixes/object_stores/#azure-blob-storage
[az-storage-account-show]: /cli/azure/storage/account#az_storage_account_show
[az-role-assignment-create]: /cli/azure/role/assignment#az_role_assignment_create
[az-monitor-account-create]: /cli/azure/monitor/account#az_monitor_account_create
[az-monitor-log-analytics-workspace-create]: /cli/azure/monitor/log-analytics/workspace#az_monitor_log_analytics_workspace_create
[azure-managed-grafana-pricing]: https://azure.microsoft.com/pricing/details/managed-grafana/
[az-aks-create]: /cli/azure/aks#az_aks_create
[az-aks-node-pool-add]: /cli/azure/aks/nodepool#az_aks_nodepool_add
[az-aks-get-credentials]: /cli/azure/aks#az_aks_get_credentials
[kubectl-create-namespace]: https://kubernetes.io/docs/reference/kubectl/generated/kubectl_create/kubectl_create_namespace/
[az-aks-enable-addons]: /cli/azure/aks#az_aks_enable_addons
[kubectl-get]: https://kubernetes.io/docs/reference/kubectl/generated/kubectl_get/
[az-aks-show]: /cli/azure/aks#az_aks_show
[az-network-public-ip-create]: /cli/azure/network/public-ip#az_network_public_ip_create
[az-network-public-ip-show]: /cli/azure/network/public-ip#az_network_public_ip_show
[az-group-show]: /cli/azure/group#az_group_show
[helm-repo-add]: https://helm.sh/docs/helm/helm_repo_add/
[helm-upgrade]: https://helm.sh/docs/helm/helm_upgrade/
[kubectl-apply]: https://kubernetes.io/docs/reference/kubectl/generated/kubectl_apply/
[deploy-postgresql]: ./deploy-postgresql-ha.md
[install-krew]: https://krew.sigs.k8s.io/
[cnpg-plugin]: https://cloudnative-pg.io/documentation/current/kubectl-plugin/#using-krew
