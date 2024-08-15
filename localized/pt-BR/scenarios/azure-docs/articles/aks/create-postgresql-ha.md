---
title: Criar infraestrutura para implantar um banco de dados PostgreSQL altamente disponível no AKS
description: Crie a infraestrutura necessária para implantar um banco de dados PostgreSQL altamente disponível no AKS usando o operador CloudNativePG.
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# Criar infraestrutura para implantar um banco de dados PostgreSQL altamente disponível no AKS

Neste artigo, você criará a infraestrutura necessária para implantar um banco de dados PostgreSQL altamente disponível no AKS usando o operador [CloudNativePG (CNPG)](https://cloudnative-pg.io/).

## Antes de começar

* Examine a visão geral da implantação e verifique se você atende a todos os pré-requisitos em [Como implantar um banco de dados PostgreSQL altamente disponível no AKS com a CLI do Azure][postgresql-ha-deployment-overview].
* [Defina variáveis de ambiente](#set-environment-variables) para uso ao longo deste guia.
* [Instale as extensões necessárias](#install-required-extensions).

## Definir variáveis de ambiente

Defina as seguintes variáveis de ambiente para uso ao longo deste guia:

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

## Instalar extensões necessárias

As extensões `aks-preview`, `k8s-extension` e `amg` fornecem mais funcionalidade para gerenciar clusters do Kubernetes e consultar recursos do Azure. Instale essas extensões usando os seguintes comandos [`az extension add`][az-extension-add]:

```bash
az extension add --upgrade --name aks-preview --yes --allow-preview true
az extension add --upgrade --name k8s-extension --yes --allow-preview false
az extension add --upgrade --name amg --yes --allow-preview false
```

Como pré-requisito para utilizar o kubectl, é essencial primeiro instalar [Krew][install-krew], seguido pela instalação do [plug-in CNPG][cnpg-plugin]. Isso habilitará o gerenciamento do operador PostgreSQL usando os comandos subsequentes.

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

## Criar um grupo de recursos

Crie um grupo de recursos para manter os recursos criados neste guia usando o comando [`az group create`][az-group-create].

```bash
az group create \
    --name $RESOURCE_GROUP_NAME \
    --location $PRIMARY_CLUSTER_REGION \
    --tags $TAGS \
    --query 'properties.provisioningState' \
    --output tsv
```

## Criar uma identidade gerenciada atribuída ao usuário

Nesta seção, você criará uma UAMI (identidade gerenciada) atribuída pelo usuário para permitir que o CNPG PostgreSQL use uma identidade de carga de trabalho do AKS para acessar o Armazenamento de Blobs do Azure. Essa configuração permite que o cluster PostgreSQL no AKS se conecte ao Armazenamento de Blobs do Azure sem segredo.

1. Crie uma identidade gerenciada atribuída pelo usuário usando o comando [`az identity create`][az-identity-create].

    ```bash
    AKS_UAMI_WI_IDENTITY=$(az identity create \
        --name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --output json)
    ```

1. Habilite a identidade da carga de trabalho do AKS e gere uma conta de serviço para usar posteriormente neste guia usando os seguintes comandos:

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

A ID do objeto é um identificador exclusivo para a ID do cliente (também conhecida como ID do aplicativo) que identifica exclusivamente uma entidade de segurança do tipo *Aplicativo* dentro do locatário da ID do Entra. A ID do recurso é um identificador exclusivo para gerenciar e localizar um recurso no Azure. Esses valores são necessários para a identidade de carga de trabalho do AKS habilitada.

O operador CNPG gera automaticamente uma conta de serviço chamada *postgres* que você usa posteriormente no guia para criar uma credencial federada que permite o acesso do OAuth do PostgreSQL ao Armazenamento do Microsoft Azure.

## Criar uma conta de armazenamento na região primária

1. Crie uma conta de armazenamento de objetos para armazenar backups do PostgreSQL na região primária usando o comando [`az storage account create`][az-storage-account-create].

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

1. Crie o contêiner de armazenamento para armazenar o WAL (Write Ahead Logs) e os backups regulares do PostgreSQL sob demanda e agendados usando o comando [`az storage container create`][az-storage-container-create].

    ```bash
    az storage container create \
        --name $PG_STORAGE_BACKUP_CONTAINER_NAME \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --auth-mode login
    ```

    Exemplo de saída:

    ```output
    {
        "created": true
    }
    ```

    > [!NOTE]
    > Se você encontrar a mensagem de erro: `The request may be blocked by network rules of storage account. Please check network rule set using 'az storage account show -n accountname --query networkRuleSet'. If you want to change the default action to apply when no rule matches, please use 'az storage account update'`. Verifique as permissões de usuário para o Armazenamento de Blobs do Azure e, se **necessário**, eleve sua função para `Storage Blob Data Owner` usando os comandos fornecidos abaixo e depois de repetir o comando [`az storage container create`][az-storage-container-create].

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

## Atribuir RBAC a contas de armazenamento

Para habilitar backups, o cluster PostgreSQL precisa ler e gravar em um repositório de objetos. O cluster PostgreSQL em execução no AKS usa uma identidade de carga de trabalho para acessar a conta de armazenamento por meio do parâmetro [`inheritFromAzureAD`][inherit-from-azuread] de configuração do operador CNPG.

1. Obtenha a ID do recurso primário para a conta de armazenamento usando o comando [`az storage account show`][az-storage-account-show].

    ```bash
    export STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID=$(az storage account show \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "id" \
        --output tsv)

    echo $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID
    ````

1. Atribua a função interna "Colaborador de Dados de Blob de Armazenamento" do Azure à ID do objeto com o escopo da ID do recurso da conta de armazenamento para a UAMI associada à identidade gerenciada para cada cluster do AKS usando o comando [`az role assignment create`][az-role-assignment-create].

    ```bash
    az role assignment create \
        --role "Storage Blob Data Contributor" \
        --assignee-object-id $AKS_UAMI_WORKLOAD_OBJECTID \
        --assignee-principal-type ServicePrincipal \
        --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID \
        --query "id" \
        --output tsv
    ```

## Configurar a infraestrutura de monitoramento

Nesta seção, você implantará uma instância do Espaço Gerenciado do Azure para Grafana, um workspace do Azure Monitor e um workspace do Log Analytics do Azure Monitor para habilitar o monitoramento do cluster PostgreSQL. Você também armazena referências à infraestrutura de monitoramento criada para usar como entrada durante o processo de criação do cluster do AKS mais adiante no guia. Esta seção pode levar algum tempo para ser concluída.

> [!NOTE]
> As instâncias do Espaço Gerenciado do Azure para Grafana e os clusters AKS são cobrados de forma independente. Para obter mais informações sobre preços, consulte [preços do Espaço Gerenciado do Azure para Grafana][azure-managed-grafana-pricing].

1. Crie uma instância do Espaço Gerenciado do Azure para Grafana usando o comando [`az grafana create`][az-grafana-create].

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

1. Crie um workspace do Azure Monitor usando o comando [`az monitor account create`][az-monitor-account-create].

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

1. Crie um workspace do Log Analytics do Azure Monitor usando o comando [`az monitor log-analytics workspace create`][az-monitor-log-analytics-workspace-create].

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

## Criar o cluster do AKS para hospedar o cluster PostgreSQL

Nesta seção, você criará um cluster AKS multizone com um pool de nós do sistema. O cluster do AKS hospeda a réplica primária do cluster PostgreSQL e duas réplicas em espera, cada uma alinhada a uma zona de disponibilidade diferente para habilitar a redundância zonal.

Você também adiciona um pool de nós de usuário ao cluster do AKS para hospedar o cluster PostgreSQL. O uso de um pool de nós separado permite o controle sobre as SKUs de VM do Azure usadas para PostgreSQL e permite que o pool de sistemas do AKS otimize o desempenho e os custos. Você aplica um rótulo ao pool de nós de usuário que pode fazer referência à seleção de nós ao implantar o operador CNPG mais adiante neste guia. Esta seção pode levar algum tempo para ser concluída.

1. Crie um cluster do AKS usando o comando [`az aks create`][az-aks-create].

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

2. Adicione um pool de nós de usuário ao cluster do AKS usando o comando [`az aks nodepool add`][az-aks-node-pool-add].

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
> Se você receber a mensagem de erro `"(OperationNotAllowed) Operation is not allowed: Another operation (Updating) is in progress, please wait for it to finish before starting a new operation."` ao adicionar o pool de nós do AKS, aguarde alguns minutos para que as operações de cluster do AKS seja concluídas e execute o comando `az aks nodepool add`.

## Conectar-se ao cluster do AKS e criar namespaces

Nesta seção, você obtém as credenciais de cluster do AKS, que servem como chaves que permitem autenticar e interagir com o cluster. Uma vez conectado, você cria dois namespaces: um para os serviços do gerenciador do controlador CNPG e outro para o cluster PostgreSQL e seus serviços relacionados.

1. Obtenha as credenciais de cluster do AKS usando o comando [`az aks get-credentials`][az-aks-get-credentials].

    ```bash
    az aks get-credentials \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --output none
     ```

2. Crie o namespace para os serviços do gerenciador do controlador CNPG, o cluster PostgreSQL e seus serviços relacionados usando o comando [`kubectl create namespace`][kubectl-create-namespace].

    ```bash
    kubectl create namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    kubectl create namespace $PG_SYSTEM_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## Atualizar a infraestrutura de monitoramento

O workspace do Azure Monitor para o Managed Prometheus e o Espaço Gerenciado do Azure para Grafana são automaticamente vinculados ao cluster do AKS para métricas e visualização durante o processo de criação do cluster. Nesta seção, você habilita a coleta de logs com insights de contêiner do AKS e valida que o Prometheus Gerenciado está raspando métricas e os insights de contêiner estão ingerindo logs.

1. Habilite o monitoramento de insights de contêiner no cluster do AKS usando o comando [`az aks enable-addons`][az-aks-enable-addons].

    ```bash
    az aks enable-addons \
        --addon monitoring \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --workspace-resource-id $ALA_RESOURCE_ID \
        --output table
    ```

2. Valide se o Managed Prometheus está raspando métricas e os insights de contêiner estão ingerindo logs do cluster do AKS inspecionando o DaemonSet usando o comando [`kubectl get`][kubectl-get] e o comando [`az aks show`][az-aks-show].

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

    Sua saída deve ser semelhante à saída de exemplo a seguir, com *seis* nós no total (três para o pool de nós do sistema e três para o pool de nós do PostgreSQL) e os insights de contêiner mostrando `"enabled": true`:

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

## Criar um IP estático público para entrada do cluster PostgreSQL

Para validar a implantação do cluster PostgreSQL e usar as ferramentas postgreSQL do cliente, como *psql* e *PgAdmin*, você precisa expor as réplicas primárias e somente leitura à entrada. Nesta seção, você criará um recurso de IP público do Azure que fornecerá posteriormente a um balanceador de carga do Azure para expor pontos de extremidade postgreSQL para consulta.

1. Obtenha o nome do grupo de recursos do nó de cluster do AKS usando o comando [`az aks show`][az-aks-show].

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME=$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query nodeResourceGroup \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME
    ```

2. Crie o endereço IP público usando o comando [`az network public-ip create`][az-network-public-ip-create].

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

3. Obtenha o endereço IP público recém-criado usando o comando [`az network public-ip show`][az-network-public-ip-show].

    ```bash
    export AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS=$(az network public-ip show \
        --resource-group $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --name $AKS_PRIMARY_CLUSTER_PUBLICIP_NAME \
        --query ipAddress \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS
    ```

4. Obtenha a ID do recurso do grupo de recursos do nó usando o comando [`az group show`][az-group-show].

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE=$(az group show --name \
        $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --query id \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE
    ```

5. Atribua a função "Colaborador de Rede" à ID do objeto UAMI usando o escopo do grupo de recursos do nó usando o comando [`az role assignment create`][az-role-assignment-create].

    ```bash
    az role assignment create \
        --assignee-object-id ${AKS_UAMI_WORKLOAD_OBJECTID} \
        --assignee-principal-type ServicePrincipal \
        --role "Network Contributor" \
        --scope ${AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE}
    ```

## Instalar o operador CNPG no cluster do AKS

Nesta seção, você instalará o operador CNPG no cluster do AKS usando o Helm ou um manifesto YAML.

### [Helm](#tab/helm)

1. Adicione o repositório CNPG Helm usando o comando [`helm repo add`][helm-repo-add].

    ```bash
    helm repo add cnpg https://cloudnative-pg.github.io/charts
    ```

2. Atualize o repositório CNPG Helm e instale-o no cluster do AKS usando o comando [`helm upgrade`][helm-upgrade] com o sinalizador `--install`.

    ```bash
    helm upgrade --install cnpg \
        --namespace $PG_SYSTEM_NAMESPACE \
        --create-namespace \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME \
        cnpg/cloudnative-pg
    ```

3. Verifique a instalação do operador no cluster do AKS usando o comando [`kubectl get`][kubectl-get].

    ```bash
    kubectl get deployment \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-cloudnative-pg
    ```

### [YAML](#tab/yaml)

1. Instale o operador CNPG no cluster do AKS usando o comando [`kubectl apply`][kubectl-apply].

    ```bash
    kubectl apply --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE \
        --server-side -f \
        https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.23/releases/cnpg-1.23.1.yaml
    ```

2. Verifique a instalação do operador no cluster do AKS usando o comando [`kubectl get`][kubectl-get].

    ```bash
    kubectl get deployment \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-controller-manager \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

---

## Próximas etapas

> [!div class="nextstepaction"]
> [Implantar um banco de dados PostgreSQL altamente disponível no cluster do AKS][deploy-postgresql]

## Colaboradores

*Este artigo é mantido pela Microsoft. Foi originalmente escrito pelos seguintes colaboradores*:

* Ken Kilty | Principal TPM
* Russell de Pina | Principal TPM
* Adrian Joian | Engenheiro sênior de clientes
* Jenny Hayes | Desenvolvedora sênior de conteúdo
* Carol Smith | Desenvolvedora sênior de conteúdo
* Erin Schaffer | Desenvolvedora de Conteúdo 2

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
