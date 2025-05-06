---
title: "Set up Container Network Observability for Azure Kubernetes Service (AKS) - Azure managed Prometheus and Grafana"
description: Get started with Container Network Observability for your AKS cluster using Azure managed Prometheus and Grafana.
author: Khushbu-Parekh
ms.author: kparekh
ms.service: azure-kubernetes-service
ms.subservice: aks-networking
ms.topic: how-to
ms.date: 05/10/2024
ms.custom: template-how-to-pattern, devx-track-azurecli
---

# Set up Container Network Observability for Azure Kubernetes Service (AKS) - Azure managed Prometheus and Grafana

This article shows you how to set up Container Network Observability for Azure Kubernetes Service (AKS) using Managed Prometheus and Grafana and BYO Prometheus and Grafana and to visualize the scraped metrics

You can use Container Network Observability to collect data about the network traffic of your AKS clusters. It enables a centralized platform for monitoring application and network health. Currently, metrics are stored in Prometheus and Grafana can be used to visualize them. Container Network Observability also offers the ability to enable Hubble. These capabilities are supported for both Cilium and non-Cilium clusters. 

Container Network Observability is one of the features of Advanced Container Networking Services. For more information about Advanced Container Networking Services for Azure Kubernetes Service (AKS), see [What is Advanced Container Networking Services for Azure Kubernetes Service (AKS)?](advanced-container-networking-services-overview.md).

## Prerequisites

* An Azure account with an active subscription. If you don't have one, create a [free account](https://azure.microsoft.com/free/?WT.mc_id=A261C142F) before you begin.
[!INCLUDE [azure-CLI-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

* The minimum version of Azure CLI required for the steps in this article is 2.56.0. Run `az --version` to find the version. If you need to install or upgrade, see [Install Azure CLI](/cli/azure/install-azure-cli).

### Enable Advanced Container Networking Services

To proceed, you must have an AKS cluster with [Advanced Container Networking Services](./advanced-container-networking-services-overview.md) enabled.

The `az aks create` command with the Advanced Container Networking Services flag, `--enable-acns`, creates a new AKS cluster with all Advanced Container Networking Services features. These features encompass:
* **Container Network Observability:**  Provides insights into your network traffic. To learn more visit [Container Network Observability](./container-network-observability-concepts.md).

* **Container Network Security:** Offers security features like FQDN filtering. To learn more visit  [Container Network Security](./advanced-container-networking-services-overview.md#container-network-security).

#### [**Cilium**](#tab/cilium)

> [!NOTE]
> Clusters with the Cilium data plane support Container Network Observability and Container Network security starting with Kubernetes version 1.29.

```azurecli-interactive
# Set an environment variable for the AKS cluster name. Make sure to replace the placeholder with your own value.
export CLUSTER_NAME="<aks-cluster-name>"

# Create an AKS cluster
az aks create \
    --name $CLUSTER_NAME \
    --resource-group $RESOURCE_GROUP \
    --generate-ssh-keys \
    --location eastus \
    --max-pods 250 \
    --network-plugin azure \
    --network-plugin-mode overlay \
    --network-dataplane cilium \
    --node-count 2 \
    --pod-cidr 192.168.0.0/16 \
    --kubernetes-version 1.29 \
    --enable-acns
```

#### [**Non-Cilium**](#tab/non-cilium)

> [!NOTE]
> [Container Network Security](./advanced-container-networking-services-overview.md#container-network-security) feature is not available for Non-cilium clusters

```azurecli-interactive
# Set an environment variable for the AKS cluster name. Make sure to replace the placeholder with your own value.
export CLUSTER_NAME="<aks-cluster-name>"

# Create an AKS cluster
az aks create \
    --name $CLUSTER_NAME \
    --resource-group $RESOURCE_GROUP \
    --generate-ssh-keys \
    --network-plugin azure \
    --network-plugin-mode overlay \
    --pod-cidr 192.168.0.0/16 \
    --enable-acns
```

---

### Enable Advanced Container Networking Services on an existing cluster

The [`az aks update`](/cli/azure/aks#az_aks_update) command with the Advanced Container Networking Services flag, `--enable-acns`, updates an existing AKS cluster with all Advanced Container Networking Services features which includes [Container Network Observability](./container-network-observability-concepts.md) and the [Container Network Security](./advanced-container-networking-services-overview.md#container-network-security) feature.


> [!NOTE]
> Only clusters with the Cilium data plane support Container Network Security features of Advanced Container Networking Services.

```azurecli-interactive
az aks update \
    --resource-group $RESOURCE_GROUP \
    --name $CLUSTER_NAME \
    --enable-acns
```

---    

## Get cluster credentials 

Once you have Get your cluster credentials using the [`az aks get-credentials`](/cli/azure/aks#az_aks_get_credentials) command.

```azurecli-interactive
az aks get-credentials --name $CLUSTER_NAME --resource-group $RESOURCE_GROUP
```

## Azure managed Prometheus and Grafana 

Skip this Section if using BYO Prometheus and Grafana

Use the following example to install and enable Prometheus and Grafana for your AKS cluster.

### Create Azure Monitor resource

```azurecli-interactive
#Set an environment variable for the Grafana name. Make sure to replace the placeholder with your own value.
export AZURE_MONITOR_NAME="<azure-monitor-name>"

# Create Azure monitor resource
az resource create \
    --resource-group $RESOURCE_GROUP \
    --namespace microsoft.monitor \
    --resource-type accounts \
    --name $AZURE_MONITOR_NAME \
    --location eastus \
    --properties '{}'
```

### Create Azure Managed Grafana instance

Use [az grafana create](/cli/azure/grafana#az-grafana-create) to create a Grafana instance. The name of the Grafana instance must be unique.

```azurecli-interactive
# Set an environment variable for the Grafana name. Make sure to replace the placeholder with your own value.
export GRAFANA_NAME="<grafana-name>"

# Create Grafana instance
az grafana create \
    --name $GRAFANA_NAME \
    --resource-group $RESOURCE_GROUP 
```

### Place the Azure Managed Grafana and Azure Monitor resource IDs in variables

Use [az grafana show](/cli/azure/grafana#az-grafana-show) to place the Grafana resource ID in a variable. Use [az resource show](/cli/azure/resource#az-resource-show) to place the Azure Monitor resource ID in a variable. Replace **myGrafana** with the name of your Grafana instance.

```azurecli-interactive
grafanaId=$(az grafana show \
                --name $GRAFANA_NAME \
                --resource-group $RESOURCE_GROUP \
                --query id \
                --output tsv)
azuremonitorId=$(az resource show \
                    --resource-group $RESOURCE_GROUP \
                    --name $AZURE_MONITOR_NAME \
                    --resource-type "Microsoft.Monitor/accounts" \
                    --query id \
                    --output tsv)
```

### Link Azure Monitor and Azure Managed Grafana to the AKS cluster

Use [az aks update](/cli/azure/aks#az-aks-update) to link the Azure Monitor and Grafana resources to your AKS cluster.

```azurecli-interactive
az aks update \
    --name $CLUSTER_NAME \
    --resource-group $RESOURCE_GROUP \
    --enable-azure-monitor-metrics \
    --azure-monitor-workspace-resource-id $azuremonitorId \
    --grafana-resource-id $grafanaId
```

## Visualization

### Visualization using Azure Managed Grafana

Skip this step if using BYO Grafana

> [!NOTE]
> The `hubble_flows_processed_total` metric isn't scraped by default due to high metric cardinality in large scale clusters. 
> Because of this, the *Pods Flows* dashboards have panels with missing data. To enable this metric and populate the missing data, you need to modify the ama-metrics-settings-configmap. Specifically, update the default-targets-metrics-keep-list section. Follow the below steps to update the configmap :
> 1. Get the latest ama-metrics-settings-configmap.(https://github.com/Azure/prometheus-collector/blob/main/otelcollector/configmaps/ama-metrics-settings-configmap.yaml)  
> 1. Locate the networkobservabilityHubble = "" 
> 1. Change it to networkobservabilityHubble = "hubble.*"
> 1. Now the Pod flow metrics should populate.
> 
> To learn more about what minimal ingestion, see the [Minimal Ingestion Documentation](/azure/azure-monitor/containers/prometheus-metrics-scrape-configuration-minimal).
> 

--- 

1. Make sure the Azure Monitor pods are running using the `kubectl get pods` command.

    ```azurecli-interactive
    kubectl get pods -o wide -n kube-system | grep ama-
    ```
    
    Your output should look similar to the following example output:
    
    ```output
    ama-metrics-5bc6c6d948-zkgc9          2/2     Running   0 (21h ago)   26h
    ama-metrics-ksm-556d86b5dc-2ndkv      1/1     Running   0 (26h ago)   26h
    ama-metrics-node-lbwcj                2/2     Running   0 (21h ago)   26h
    ama-metrics-node-rzkzn                2/2     Running   0 (21h ago)   26h
    ama-metrics-win-node-gqnkw            2/2     Running   0 (26h ago)   26h
    ama-metrics-win-node-tkrm8            2/2     Running   0 (26h ago)   26h
    ```

1. We have created sample dashboards. They can be found under the **Dashboards > Azure Managed Prometheus** folder. They have names like **"Kubernetes / Networking / `<name>`"**. The suite of dashboards includes:
      * **Clusters:** shows Node-level metrics for your clusters.
      * **DNS (Cluster):** shows DNS metrics on a cluster or selection of Nodes.
      * **DNS (Workload):** shows DNS metrics for the specified workload (e.g. Pods of a DaemonSet or Deployment such as CoreDNS).
      * **Drops (Workload):** shows drops to/from the specified workload (e.g. Pods of a Deployment or DaemonSet).
      * **Pod Flows (Namespace):** shows L4/L7 packet flows to/from the specified namespace (i.e. Pods in the
      Namespace).
      * **Pod Flows (Workload):** shows L4/L7 packet flows to/from the specified workload (e.g. Pods of a Deployment or DaemonSet).

### Visualization using BYO Grafana

Skip this step if using Azure managed Grafana

1. Add the following scrape job to your existing Prometheus configuration and restart your Prometheus server:

    ```yml
    - job_name: networkobservability-hubble
      kubernetes_sd_configs:
        - role: pod
      relabel_configs:
        - target_label: cluster
          replacement: myAKSCluster
          action: replace
        - source_labels: [__meta_kubernetes_namespace, __meta_kubernetes_pod_label_k8s_app]
          regex: kube-system;(retina|cilium)
          action: keep
        - source_labels: [__address__]
          action: replace
          regex: ([^:]+)(?::\d+)?
          replacement: $1:9965
          target_label: __address__
        - source_labels: [__meta_kubernetes_pod_node_name]
          target_label: instance
          action: replace
      metric_relabel_configs:
        - source_labels: [__name__]
          regex: '|hubble_dns_queries_total|hubble_dns_responses_total|hubble_drop_total|hubble_tcp_flags_total' # if desired, add |hubble_flows_processed_total
          action: keep
    ``` 

1. In **Targets** of Prometheus, verify the **network-obs-pods** are present.

1. Sign in to Grafana and import following example dashboards using the following IDs:
      * **Clusters:** shows Node-level metrics for your clusters. (ID: [18814](https://grafana.com/grafana/dashboards/18814-kubernetes-networking-clusters/))
      * **DNS (Cluster):** shows DNS metrics on a cluster or selection of Nodes.(ID: [20925](https://grafana.com/grafana/dashboards/20925-kubernetes-networking-dns-cluster/))
      * **DNS (Workload):** shows DNS metrics for the specified workload (e.g. Pods of a DaemonSet or Deployment such as CoreDNS). (ID: [20926] https://grafana.com/grafana/dashboards/20926-kubernetes-networking-dns-workload/)
      * **Drops (Workload):** shows drops to/from the specified workload (e.g. Pods of a Deployment or DaemonSet).(ID: [20927](https://grafana.com/grafana/dashboards/20927-kubernetes-networking-drops-workload/)). 
      * **Pod Flows (Namespace):** shows L4/L7 packet flows to/from the specified namespace (i.e. Pods in the
      Namespace). (ID: [20928](https://grafana.com/grafana/dashboards/20928-kubernetes-networking-pod-flows-namespace/))
      * **Pod Flows (Workload):** shows L4/L7 packet flows to/from the specified workload (e.g. Pods of a Deployment or DaemonSet).(ID: [20929](https://grafana.com/grafana/dashboards/20929-kubernetes-networking-pod-flows-workload/))

    > [!NOTE] 
    > * Depending on your Prometheus/Grafana instances’ settings, some dashboard panels may require tweaks to display all data.
    > * Cilium does not currently support DNS metrics/dashboards.

## Install Hubble CLI

Install the Hubble CLI to access the data it collects using the following commands:

```azurecli-interactive
# Set environment variables
export HUBBLE_VERSION=v1.16.3
export HUBBLE_ARCH=amd64

#Install Hubble CLI
if [ "$(uname -m)" = "aarch64" ]; then HUBBLE_ARCH=arm64; fi
curl -L --fail --remote-name-all https://github.com/cilium/hubble/releases/download/$HUBBLE_VERSION/hubble-linux-${HUBBLE_ARCH}.tar.gz{,.sha256sum}
sha256sum --check hubble-linux-${HUBBLE_ARCH}.tar.gz.sha256sum
sudo tar xzvfC hubble-linux-${HUBBLE_ARCH}.tar.gz /usr/local/bin
rm hubble-linux-${HUBBLE_ARCH}.tar.gz{,.sha256sum}
```

## Visualize the Hubble Flows

1. Make sure the Hubble pods are running using the `kubectl get pods` command.

    ```azurecli-interactive
    kubectl get pods -o wide -n kube-system -l k8s-app=hubble-relay
    ```
    
    Your output should look similar to the following example output:
    
    ```output
    hubble-relay-7ddd887cdb-h6khj     1/1  Running     0       23h 
    ```
    
1. Port forward Hubble Relay using the `kubectl port-forward` command.
    
    ```azurecli-interactive
    kubectl port-forward -n kube-system svc/hubble-relay --address 127.0.0.1 4245:443
    ```
    
1. Mutual TLS (mTLS) ensures the security of the Hubble Relay server. To enable the Hubble client to retrieve flows, you need to get the appropriate certificates and configure the client with them. Apply the certificates using the following commands:

    ```azurecli-interactive
    #!/usr/bin/env bash
    
    set -euo pipefail
    set -x
    
    # Directory where certificates will be stored
    CERT_DIR="$(pwd)/.certs"
    mkdir -p "$CERT_DIR"
    
    declare -A CERT_FILES=(
      ["tls.crt"]="tls-client-cert-file"
      ["tls.key"]="tls-client-key-file"
      ["ca.crt"]="tls-ca-cert-files"
    )
    
    for FILE in "${!CERT_FILES[@]}"; do
      KEY="${CERT_FILES[$FILE]}"
      JSONPATH="{.data['${FILE//./\\.}']}"
    
      # Retrieve the secret and decode it
      kubectl get secret hubble-relay-client-certs -n kube-system \
        -o jsonpath="${JSONPATH}" | \
        base64 -d > "$CERT_DIR/$FILE"
    
      # Set the appropriate hubble CLI config
      hubble config set "$KEY" "$CERT_DIR/$FILE"
    done
        
    hubble config set tls true
    hubble config set tls-server-name instance.hubble-relay.cilium.io
    ```

1. Verify the secrets were generated using the following `kubectl get secrets` command:
    ```azurecli-interactive
    kubectl get secrets -n kube-system | grep hubble-
    ```

    Your output should look similar to the following example output:

    ```output
    kube-system     hubble-relay-client-certs     kubernetes.io/tls     3     9d
    
    kube-system     hubble-relay-server-certs     kubernetes.io/tls     3     9d
    
    kube-system     hubble-server-certs           kubernetes.io/tls     3     9d    
    ```

2. Make sure the Hubble Relay pod is running using the `hubble observe` command.

    ```azurecli-interactive
    hubble observe --pod hubble-relay-7ddd887cdb-h6khj
    ```

## Visualize using Hubble UI

1. To use Hubble UI, save the following into hubble-ui.yaml
    ```yml
    apiVersion: v1
    kind: ServiceAccount
    metadata:
      name: hubble-ui
      namespace: kube-system
    ---
    kind: ClusterRole
    apiVersion: rbac.authorization.k8s.io/v1
    metadata:
      name: hubble-ui
      labels:
        app.kubernetes.io/part-of: retina
    rules:
      - apiGroups:
          - networking.k8s.io
        resources:
          - networkpolicies
        verbs:
          - get
          - list
          - watch
      - apiGroups:
          - ""
        resources:
          - componentstatuses
          - endpoints
          - namespaces
          - nodes
          - pods
          - services
        verbs:
          - get
          - list
          - watch
      - apiGroups:
          - apiextensions.k8s.io
        resources:
          - customresourcedefinitions
        verbs:
          - get
          - list
          - watch
      - apiGroups:
          - cilium.io
        resources:
          - "*"
        verbs:
          - get
          - list
          - watch
    ---
    apiVersion: rbac.authorization.k8s.io/v1
    kind: ClusterRoleBinding
    metadata:
      name: hubble-ui
      labels:
        app.kubernetes.io/part-of: retina
    roleRef:
      apiGroup: rbac.authorization.k8s.io
      kind: ClusterRole
      name: hubble-ui
    subjects:
      - kind: ServiceAccount
        name: hubble-ui
        namespace: kube-system
    ---
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: hubble-ui-nginx
      namespace: kube-system
    data:
      nginx.conf: |
        server {
            listen       8081;
            server_name  localhost;
            root /app;
            index index.html;
            client_max_body_size 1G;
            location / {
                proxy_set_header Host $host;
                proxy_set_header X-Real-IP $remote_addr;
                # CORS
                add_header Access-Control-Allow-Methods "GET, POST, PUT, HEAD, DELETE, OPTIONS";
                add_header Access-Control-Allow-Origin *;
                add_header Access-Control-Max-Age 1728000;
                add_header Access-Control-Expose-Headers content-length,grpc-status,grpc-message;
                add_header Access-Control-Allow-Headers range,keep-alive,user-agent,cache-control,content-type,content-transfer-encoding,x-accept-content-transfer-encoding,x-accept-response-streaming,x-user-agent,x-grpc-web,grpc-timeout;
                if ($request_method = OPTIONS) {
                    return 204;
                }
                # /CORS
                location /api {
                    proxy_http_version 1.1;
                    proxy_pass_request_headers on;
                    proxy_hide_header Access-Control-Allow-Origin;
                    proxy_pass http://127.0.0.1:8090;
                }
                location / {
                    try_files $uri $uri/ /index.html /index.html;
                }
                # Liveness probe
                location /healthz {
                    access_log off;
                    add_header Content-Type text/plain;
                    return 200 'ok';
                }
            }
        }
    ---
    kind: Deployment
    apiVersion: apps/v1
    metadata:
      name: hubble-ui
      namespace: kube-system
      labels:
        k8s-app: hubble-ui
        app.kubernetes.io/name: hubble-ui
        app.kubernetes.io/part-of: retina
    spec:
      replicas: 1
      selector:
        matchLabels:
          k8s-app: hubble-ui
      template:
        metadata:
          labels:
            k8s-app: hubble-ui
            app.kubernetes.io/name: hubble-ui
            app.kubernetes.io/part-of: retina
        spec:
          serviceAccountName: hubble-ui
          automountServiceAccountToken: true
          containers:
          - name: frontend
            image: mcr.microsoft.com/oss/cilium/hubble-ui:v0.12.2   
            imagePullPolicy: Always
            ports:
            - name: http
              containerPort: 8081
            livenessProbe:
              httpGet:
                path: /healthz
                port: 8081
            readinessProbe:
              httpGet:
                path: /
                port: 8081
            resources: {}
            volumeMounts:
            - name: hubble-ui-nginx-conf
              mountPath: /etc/nginx/conf.d/default.conf
              subPath: nginx.conf
            - name: tmp-dir
              mountPath: /tmp
            terminationMessagePolicy: FallbackToLogsOnError
            securityContext: {}
          - name: backend
            image: mcr.microsoft.com/oss/cilium/hubble-ui-backend:v0.12.2
            imagePullPolicy: Always
            env:
            - name: EVENTS_SERVER_PORT
              value: "8090"
            - name: FLOWS_API_ADDR
              value: "hubble-relay:443"
            - name: TLS_TO_RELAY_ENABLED
              value: "true"
            - name: TLS_RELAY_SERVER_NAME
              value: ui.hubble-relay.cilium.io
            - name: TLS_RELAY_CA_CERT_FILES
              value: /var/lib/hubble-ui/certs/hubble-relay-ca.crt
            - name: TLS_RELAY_CLIENT_CERT_FILE
              value: /var/lib/hubble-ui/certs/client.crt
            - name: TLS_RELAY_CLIENT_KEY_FILE
              value: /var/lib/hubble-ui/certs/client.key
            livenessProbe:
              httpGet:
                path: /healthz
                port: 8090
            readinessProbe:
              httpGet:
                path: /healthz
                port: 8090
            ports:
            - name: grpc
              containerPort: 8090
            resources: {}
            volumeMounts:
            - name: hubble-ui-client-certs
              mountPath: /var/lib/hubble-ui/certs
              readOnly: true
            terminationMessagePolicy: FallbackToLogsOnError
            securityContext: {}
          nodeSelector:
            kubernetes.io/os: linux 
          volumes:
          - configMap:
              defaultMode: 420
              name: hubble-ui-nginx
            name: hubble-ui-nginx-conf
          - emptyDir: {}
            name: tmp-dir
          - name: hubble-ui-client-certs
            projected:
              defaultMode: 0400
              sources:
              - secret:
                  name: hubble-relay-client-certs
                  items:
                    - key: tls.crt
                      path: client.crt
                    - key: tls.key
                      path: client.key
                    - key: ca.crt
                      path: hubble-relay-ca.crt
    ---
    kind: Service
    apiVersion: v1
    metadata:
      name: hubble-ui
      namespace: kube-system
      labels:
        k8s-app: hubble-ui
        app.kubernetes.io/name: hubble-ui
        app.kubernetes.io/part-of: retina
    spec:
      type: ClusterIP
      selector:
        k8s-app: hubble-ui
      ports:
        - name: http
          port: 80
          targetPort: 8081
    ```

1. Apply the hubble-ui.yaml manifest to your cluster, using the following command 
    ```azurecli-interactive
    kubectl apply -f hubble-ui.yaml
    ```

1. Set up port forwarding for Hubble UI using the `kubectl port-forward` command.

    ```azurecli-interactive
    kubectl -n kube-system port-forward svc/hubble-ui 12000:80
    ```

1. Access Hubble UI by entering `http://localhost:12000/` into your web browser.

---

## Clean up resources

If you don't plan on using this application, delete the other resources you created in this article using the [`az group delete`](/cli/azure/#az_group_delete) command.

```azurecli-interactive
  az group delete --name $RESOURCE_GROUP
```

## Next steps

In this how-to article, you learned how to install and enable Container Network Observability for your AKS cluster.

* For more information about Advanced Container Networking Services for Azure Kubernetes Service (AKS), see [What is Advanced Container Networking Services for Azure Kubernetes Service (AKS)?](advanced-container-networking-services-overview.md).

* For more information on Container Network Security and its capabilities, see [What is Container Network Security?](container-network-security-concepts.md).

