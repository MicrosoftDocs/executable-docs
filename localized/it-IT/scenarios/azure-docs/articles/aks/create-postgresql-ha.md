---
title: Creare un'infrastruttura per la distribuzione di un database PostgreSQL a disponibilità elevata nel servizio Azure Kubernetes
description: Creare l'infrastruttura necessaria per distribuire un database PostgreSQL a disponibilità elevata nel servizio Azure Kubernetes usando l'operatore CloudNativePG.
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# Creare un'infrastruttura per la distribuzione di un database PostgreSQL a disponibilità elevata nel servizio Azure Kubernetes

In questo articolo viene creata l'infrastruttura necessaria per distribuire un database PostgreSQL a disponibilità elevata nel servizio Azure Kubernetes usando l'operatore [CloudNativePG (CNPG)](https://cloudnative-pg.io/).

## Operazioni preliminari

* Controllare la panoramica della distribuzione e assicurarsi che siano soddisfatti tutti i prerequisiti in descritti in [Come distribuire un database PostgreSQL a disponibilità elevata nel servizio Azure Kubernetes con l'interfaccia della riga di comando di Azure][postgresql-ha-deployment-overview].
* [Impostare le variabili di ambiente](#set-environment-variables) da usare in questa guida.
* [Installare le estensioni necessarie](#install-required-extensions).

## Impostare le variabili di ambiente

Impostare le variabili di ambiente seguenti da usare in questa guida:

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

## Installare le estensioni necessarie

Le estensioni `aks-preview`, `k8s-extension` e `amg` offrono altre funzionalità per la gestione dei cluster Kubernetes e l'esecuzione di query sulle risorse di Azure. Installare queste estensioni usando i comandi [`az extension add`][az-extension-add] seguenti:

```bash
az extension add --upgrade --name aks-preview --yes --allow-preview true
az extension add --upgrade --name k8s-extension --yes --allow-preview false
az extension add --upgrade --name amg --yes --allow-preview false
```

Come prerequisito per l'uso di kubectl, è essenziale installare prima [Krew][install-krew], seguito dall'installazione del [plug-in CNPG][cnpg-plugin]. In questo modo verrà abilitata la gestione dell'operatore PostgreSQL usando i comandi successivi.

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

## Creare un gruppo di risorse

Creare un gruppo di risorse per contenere le risorse create in questa guida usando il comando [`az group create`][az-group-create].

```bash
az group create \
    --name $RESOURCE_GROUP_NAME \
    --location $PRIMARY_CLUSTER_REGION \
    --tags $TAGS \
    --query 'properties.provisioningState' \
    --output tsv
```

## Creare un'identità gestita assegnata dall'utente

In questa sezione viene creata un'identità gestita assegnata dall'utente per consentire al CNPG PostgreSQL di usare un'identità del carico di lavoro del servizio Azure Kubernetes per accedere ad Archiviazione BLOB di Azure. Questa configurazione consente al cluster PostgreSQL nel servizio Azure Kubernetes di connettersi all'archiviazione BLOB di Azure senza un segreto.

1. Creare un'identità gestita assegnata dall'utente usando il comando [`az identity create`][az-identity-create].

    ```bash
    AKS_UAMI_WI_IDENTITY=$(az identity create \
        --name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --output json)
    ```

1. Abilitare l'identità del carico di lavoro del servizio Azure Kubernetes e generare un account del servizio da usare in seguito in questa guida usando i comandi seguenti:

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

L'ID oggetto è un identificatore univoco dell'ID client (noto anche come ID applicazione) che identifica in modo univoco un'entità di sicurezza di tipo *Applicazione* all'interno del tenant Entra ID. L'ID risorsa è un identificatore univoco che consente di gestire e individuare una risorsa in Azure. Questi valori sono necessari per abilitare l'identità del carico di lavoro del servizio Azure Kubernetes.

L'operatore CNPG genera automaticamente un account di servizio denominato *postgres* che verrà usato in seguito nella guida per creare credenziali federate che consentano l'accesso OAuth da PostgreSQL ad Archiviazione di Azure.

## Creare un account di archiviazione nell'area primaria

1. Creare un account di archiviazione oggetti per archiviare i backup PostgreSQL nell'area primaria usando il comando [`az storage account create`][az-storage-account-create].

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

1. Creare il contenitore di archiviazione per archiviare i log write-ahead (WAL) e i normali backup di PostgreSQL su richiesta e pianificati usando il comando [`az storage container create`][az-storage-container-create].

    ```bash
    az storage container create \
        --name $PG_STORAGE_BACKUP_CONTAINER_NAME \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --auth-mode login
    ```

    Output di esempio:

    ```output
    {
        "created": true
    }
    ```

    > [!NOTE]
    > Se viene visualizzato il messaggio di errore: `The request may be blocked by network rules of storage account. Please check network rule set using 'az storage account show -n accountname --query networkRuleSet'. If you want to change the default action to apply when no rule matches, please use 'az storage account update'`. Verificare le autorizzazioni utente per Archiviazione BLOB di Azure e, se **necessario**, elevare il ruolo a `Storage Blob Data Owner` usando i comandi forniti di seguito e dopo aver rieseguito il comando [`az storage container create`][az-storage-container-create].

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

## Assegnare il controllo degli accessi in base al ruolo agli account di archiviazione

Per abilitare i backup, il cluster PostgreSQL deve leggere e scrivere in un archivio oggetti. Il cluster PostgreSQL in esecuzione nel servizio Azure Kubernetes usa un'identità del carico di lavoro per accedere all'account di archiviazione tramite il parametro [`inheritFromAzureAD`][inherit-from-azuread] di configurazione dell'operatore CNPG .

1. Ottenere l'ID risorsa primaria dell'account di archiviazione usando il comando [`az storage account show`][az-storage-account-show].

    ```bash
    export STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID=$(az storage account show \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "id" \
        --output tsv)

    echo $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID
    ````

1. Assegnare il ruolo predefinito di Azure "Collaboratore ai dati del BLOB di archiviazione" all'ID oggetto con l'ambito dell'ID risorsa dell'account di archiviazione per l'UAMI associato all'identità gestita per ogni cluster del servizio Azure Kubernetes usando il comando [`az role assignment create`][az-role-assignment-create].

    ```bash
    az role assignment create \
        --role "Storage Blob Data Contributor" \
        --assignee-object-id $AKS_UAMI_WORKLOAD_OBJECTID \
        --assignee-principal-type ServicePrincipal \
        --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID \
        --query "id" \
        --output tsv
    ```

## Configurare l'infrastruttura di monitoraggio

In questa sezione si distribuisce un'istanza di Grafana con gestione Azure, un'area di lavoro di Monitoraggio di Azure e un'area di lavoro Log Analytics di Monitoraggio di Azure per abilitare il monitoraggio del cluster PostgreSQL. Si archiviano anche i riferimenti all'infrastruttura di monitoraggio creata da usare come input durante il processo di creazione del cluster del servizio Azure Kubernetes in seguito nella guida. Il completamento di questa sezione potrebbe richiedere un po’ di tempo.

> [!NOTE]
> Le istanze di Grafana con gestione Azure e i cluster del servizio Azure Kubernetes vengono fatturati in modo indipendente. Per altre informazioni sui prezzi, vedere [Prezzi di Grafana con gestione Azure][azure-managed-grafana-pricing].

1. Creare un'istanza di Grafana con gestione Azure usando il comando [`az grafana create`][az-grafana-create].

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

1. Creare un'area di lavoro di Monitoraggio di Azure usando il comando [`az monitor account create`][az-monitor-account-create].

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

1. Creare un'area di lavoro Log Analytics di Monitoraggio di Azure usando il comando [`az monitor log-analytics workspace create`][az-monitor-log-analytics-workspace-create].

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

## Creare il cluster del servizio Azure Kubernetes per ospitare il cluster PostgreSQL

In questa sezione viene creato un cluster servizio Azure Kubernetes multi-zone con un pool di nodi di sistema. Il cluster del servizio Azure Kubernetes ospita la replica primaria del cluster PostgreSQL e due repliche di standby, ognuna allineata a una zona di disponibilità diversa per abilitare la ridondanza della zona.

È inoltre possibile aggiungere un pool di nodi utente al cluster del servizio Azure Kubernetes per ospitare il cluster PostgreSQL. L'uso di un pool di nodi separato consente di controllare gli SKU delle macchine virtuali di Azure usati per PostgreSQL e consente al pool di sistema del servizio Azure Kubernetes di ottimizzare costi e prestazioni. Si applica un'etichetta al pool di nodi utente a cui è possibile fare riferimento per la selezione del nodo durante la distribuzione dell'operatore CNPG più avanti in questa guida. Il completamento di questa sezione potrebbe richiedere un po’ di tempo.

1. Creare un cluster del servizio Azure Kubernetes usando il comando [`az aks create`][az-aks-create].

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

2. Aggiungere un pool di nodi utente al cluster del servizio Azure Kubernetes usando il comando [`az aks nodepool add`][az-aks-node-pool-add].

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
> Se viene visualizzato il messaggio di errore `"(OperationNotAllowed) Operation is not allowed: Another operation (Updating) is in progress, please wait for it to finish before starting a new operation."` quando si aggiunge il pool di nodi del servizio Azure Kubernetes, attendere alcuni minuti fino al completamento delle operazioni del cluster del servizio Azure Kubernetes, quindi eseguire il comando `az aks nodepool add`.

## Connettersi al cluster del servizio Azure Kubernetes e creare spazi dei nomi

In questa sezione si ottengono le credenziali del cluster del servizio Azure Kubernetes, che fungono da chiavi che consentono di eseguire l'autenticazione e l'interazione con il cluster. Dopo la connessione, si creano due spazi dei nomi: uno per i servizi di gestione controller CNPG e uno per il cluster PostgreSQL e i relativi servizi.

1. Ottenere le credenziali del cluster del servizio Azure Kubernetes usando il comando [`az aks get-credentials`][az-aks-get-credentials].

    ```bash
    az aks get-credentials \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --output none
     ```

2. Creare lo spazio dei nomi per i servizi di gestione controller CNPG, il cluster PostgreSQL e i relativi servizi usando il comando [`kubectl create namespace`][kubectl-create-namespace].

    ```bash
    kubectl create namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    kubectl create namespace $PG_SYSTEM_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## Aggiornare l'infrastruttura di monitoraggio

Le aree di lavoro di Monitoraggio di Azure per Prometheus gestito e Grafana con gestione Azure vengono collegate automaticamente al cluster del servizio Azure Kubernetes per le metriche e la visualizzazione durante il processo di creazione del cluster. In questa sezione si abilitata la raccolta di log con informazioni dettagliate sui contenitori del servizio Azure Kubernetes e si verifica che Prometheus gestito stia scorporando le metriche e che le informazioni dettagliate stiano inserendo i log.

1. Abilitare il monitoraggio delle informazioni dettagliate sui contenitori nel cluster del servizio Azure Kubernetes usando il comando [`az aks enable-addons`][az-aks-enable-addons].

    ```bash
    az aks enable-addons \
        --addon monitoring \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --workspace-resource-id $ALA_RESOURCE_ID \
        --output table
    ```

2. Verificare che Prometheus gestito stia scorporando le metriche e che le informazioni dettagliate sui contenitori stiano inserendo i log del cluster del servizio Azure Kubernetes esaminando il DaemonSet tramite il comando [`kubectl get`][kubectl-get] e il comando [`az aks show`][az-aks-show].

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

    L'output dovrebbe essere simile all'output di esempio seguente, con *sei* nodi totali (tre per il pool di nodi di sistema e tre per il pool di nodi PostgreSQL) e le informazioni dettagliate sui contenitori che mostrano `"enabled": true`:

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

## Creare un indirizzo IP statico pubblico per il cluster PostgreSQL in ingresso

Per convalidare la distribuzione del cluster PostgreSQL e usare gli strumenti PostgreSQL client, ad esempio *psql* e *PgAdmin*, è necessario esporre le repliche primarie e di sola lettura in ingresso. In questa sezione viene creata una risorsa IP pubblica di Azure fornita successivamente a un servizio di bilanciamento del carico di Azure per esporre gli endpoint PostgreSQL per la query.

1. Ottenere il nome del gruppo di risorse del nodo del cluster del servizio Azure Kubernetes usando il comando [`az aks show`][az-aks-show].

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME=$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query nodeResourceGroup \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME
    ```

2. Creare l'indirizzo IP pubblico usando il comando [`az network public-ip create`][az-network-public-ip-create].

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

3. Ottenere l'indirizzo IP pubblico appena creato usando il comando [`az network public-ip show`][az-network-public-ip-show].

    ```bash
    export AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS=$(az network public-ip show \
        --resource-group $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --name $AKS_PRIMARY_CLUSTER_PUBLICIP_NAME \
        --query ipAddress \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS
    ```

4. Ottenere l'ID risorsa del gruppo di risorse del nodo usando il comando [`az group show`][az-group-show].

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE=$(az group show --name \
        $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --query id \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE
    ```

5. Assegnare il ruolo "Collaboratore rete" all'ID oggetto UAMI usando l'ambito del gruppo di risorse del nodo tramite il comando [`az role assignment create`][az-role-assignment-create].

    ```bash
    az role assignment create \
        --assignee-object-id ${AKS_UAMI_WORKLOAD_OBJECTID} \
        --assignee-principal-type ServicePrincipal \
        --role "Network Contributor" \
        --scope ${AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE}
    ```

## Installare l'operatore CNPG nel cluster del servizio Azure Kubernetes

In questa sezione si installa l'operatore CNPG nel cluster del servizio Azure Kubernetes usando Helm o un manifesto YAML.

### [Helm](#tab/helm)

1. Aggiungere il repository Helm CNPG usando il comando [`helm repo add`][helm-repo-add].

    ```bash
    helm repo add cnpg https://cloudnative-pg.github.io/charts
    ```

2. Aggiornare il repository Helm CNPG e installarlo nel cluster del servizio Azure Kubernetes usando il comando [`helm upgrade`][helm-upgrade] con il flag `--install`.

    ```bash
    helm upgrade --install cnpg \
        --namespace $PG_SYSTEM_NAMESPACE \
        --create-namespace \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME \
        cnpg/cloudnative-pg
    ```

3. Verificare l'installazione dell'operatore nel cluster del servizio Azure Kubernetes usando il comando [`kubectl get`][kubectl-get].

    ```bash
    kubectl get deployment \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-cloudnative-pg
    ```

### [YAML](#tab/yaml)

1. Installare l'operatore CNPG nel cluster del servizio Azure Kubernetes usando il comando [`kubectl apply`][kubectl-apply].

    ```bash
    kubectl apply --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE \
        --server-side -f \
        https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.23/releases/cnpg-1.23.1.yaml
    ```

2. Verificare l'installazione dell'operatore nel cluster del servizio Azure Kubernetes usando il comando [`kubectl get`][kubectl-get].

    ```bash
    kubectl get deployment \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-controller-manager \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

---

## Passaggi successivi

> [!div class="nextstepaction"]
> [Distribuire un database PostgreSQL a disponibilità elevata nel cluster del servizio Azure Kubernetes][deploy-postgresql]

## Collaboratori

*Questo articolo viene gestito da Microsoft. Originariamente è stato scritto dai collaboratori* seguenti:

* Ken Kilty | Responsabile TPM
* Russell de Pina | Responsabile TPM
* Adrian Joian | Senior Customer Engineer
* Jenny Hayes | Sviluppatore di contenuti senior
* Carol Smith | Sviluppatore di contenuti senior
* Erin Schaffer | Sviluppatore di contenuti 2

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
