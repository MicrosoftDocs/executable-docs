---
title: Configure Azure Kubernetes Service (AKS) nodes with an HTTP proxy
description: Use the HTTP proxy configuration feature for Azure Kubernetes Service (AKS) nodes.
ms.subservice: aks-networking
ms.custom: devx-track-arm-template, devx-track-azurecli
author: allyford
ms.topic: how-to
ms.date: 03/07/2025
ms.author: allyford
---

# HTTP proxy support in Azure Kubernetes Service (AKS)

In this article, you learn how to configure Azure Kubernetes Service (AKS) clusters to use an HTTP proxy for outbound internet access.

AKS clusters deployed into managed or custom virtual networks have certain outbound dependencies that are necessary to function properly, which created problems in environments requiring internet access to be routed through HTTP proxies. Nodes had no way of bootstrapping the configuration, environment variables, and certificates necessary to access internet services.

The HTTP proxy feature adds HTTP proxy support to AKS clusters, exposing a straightforward interface that you can use to secure AKS-required network traffic in proxy-dependent environments. With this feature, both AKS nodes and pods are configured to use the HTTP proxy. The feature also enables installation of a trusted certificate authority onto the nodes as part of bootstrapping a cluster. More complex solutions might require creating a chain of trust to establish secure communications across the network.

## Limitations and considerations

The following scenarios are **not** supported:

* Different proxy configurations per node pool
* User/Password authentication
* Custom certificate authorities (CAs) for API server communication
* AKS clusters with Windows node pools
* Node pools using Virtual Machine Availability Sets (VMAS)
* Using * as wildcard attached to a domain suffix for noProxy

`httpProxy`, `httpsProxy`, and `trustedCa` have no value by default. Pods are injected with the following environment variables:

* `HTTP_PROXY`
* `http_proxy`
* `HTTPS_PROXY`
* `https_proxy`
* `NO_PROXY`
* `no_proxy`

To disable the injection of the proxy environment variables, you need to annotate the Pod with `"kubernetes.azure.com/no-http-proxy-vars":"true"`.

## Before you begin

* You need the latest version of the Azure CLI. Run `az --version` to find the version, and run `az upgrade` to upgrade the version. If you need to install or upgrade, see [Install Azure CLI][install-azure-cli].
* [Check for available AKS cluster upgrades](./upgrade-aks-cluster.md#check-for-available-aks-cluster-upgrades) to ensure you're running the latest version of AKS. If you need to upgrade, see [Upgrade an AKS cluster](./upgrade-aks-cluster.md#upgrade-an-aks-cluster).

## [Configure an HTTP proxy using the Azure CLI](#tab/use-azure-cli)

You can configure an AKS cluster with an HTTP proxy during cluster creation using the [`az aks create`][az-aks-create] command and passing in configuration as a JSON file.

1. Create a file and provide values for `httpProxy`, `httpsProxy`, and `noProxy`. If your environment requires it, provide a value for `trustedCa`.

The schema for the config file looks like this:

```json
{
  "httpProxy": "string",
  "httpsProxy": "string",
  "noProxy": [
    "string"
  ],
  "trustedCa": "string"
}
```

Review requirements for each parameter:

* `httpProxy`: A proxy URL to use for creating HTTP connections outside the cluster. The URL scheme must be `http`.
* `httpsProxy`: A proxy URL to use for creating HTTPS connections outside the cluster. If not specified, then `httpProxy` is used for both HTTP and HTTPS connections.
* `noProxy`: A list of destination domain names, domains, IP addresses, or other network CIDRs to exclude proxying.
* `trustedCa`: A string containing the `base64 encoded` alternative CA certificate content. Currently only the `PEM` format is supported.

> [!IMPORTANT]
> For compatibility with Go-based components that are part of the Kubernetes system, the certificate **must** support `Subject Alternative Names(SANs)` instead of the deprecated Common Name certs.
>
> There are differences in applications on how to comply with the environment variable `http_proxy`, `https_proxy`, and `no_proxy`. Curl and Python don't support CIDR in `no_proxy`, but Ruby does.

Example input:

```json
{
  "httpProxy": "http://myproxy.server.com:8080/", 
  "httpsProxy": "https://myproxy.server.com:8080/", 
  "noProxy": [
    "localhost",
    "127.0.0.1"
  ],
  "trustedCA": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUgvVENDQmVXZ0F3SUJB...b3Rpbk15RGszaWFyCkYxMFlscWNPbWVYMXVGbUtiZGkvWG9yR2xrQ29NRjNURHg4cm1wOURCaUIvCi0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0="
}
```

2.  Create a cluster using the [`az aks create`][az-aks-create] command with the `--http-proxy-config` parameter set to the file you created. 

```azurecli-interactive
az aks create \
    --name $clusterName \
    --resource-group $resourceGroup \
    --http-proxy-config aks-proxy-config.json \
    --generate-ssh-keys
```
Your cluster should initialize with the HTTP proxy configured on the nodes.

## [Configure an HTTP proxy using an Azure Resource Manager (ARM) template](#tab/use-arm)

You can deploy an AKS cluster with an HTTP proxy using an ARM template. 

1. In your template, provide values for `httpProxy`, `httpsProxy`, and `noProxy`. If necessary, provide a value for `trustedCa`. 

The same schema used for CLI deployment exists in the `Microsoft.ContainerService/managedClusters` definition under `"properties"`, as shown in the following example:

```json
"properties": {
    ...,
    "httpProxyConfig": {
        "httpProxy": "string",
        "httpsProxy": "string",
        "noProxy": [
            "string"
        ],
        "trustedCa": "string"
    }
}
```

2. Deploy your ARM template with the HTTP Proxy configuration

Next, you can deploy the template. Your cluster should initialize with your HTTP proxy configured on the nodes.

## [Istio Add-On HTTP Proxy for External Services](#tab/use-Istio-add-on)

If you are using the [Istio-based service mesh add-on for AKS][istio-add-on-docs], you must create a Service Entry to enable your applications in the mesh to access non-cluster or external resources via the HTTP proxy. For example:
```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: proxy
spec:
  hosts:
  - my-company-proxy.com # ignored
  addresses:
  - $PROXY_IP/32
  ports:
  - number: $PROXY_PORT
    name: tcp
    protocol: TCP
  location: MESH_EXTERNAL
```
1. Create a file and provide values for `PROXY_IP` and `PROXY_PORT`. 

2. You can deploy the Service Entry using:

```bash
kubectl apply -f service_proxy.yaml
```
---

## Update cluster to enable or update http proxy configuration

> [!NOTE]
> If switching to a new proxy, the new proxy must already exist for the update to be successful. After the upgrade is completed, you can delete the old proxy.

HTTP Proxy configuration can be enabled or updated on an existing cluster using the [`az aks update`][az-aks-update] command. The `--http-proxy-config` parameter should be set to a new JSON file with updated values for `httpProxy`, `httpsProxy`, `noProxy`, and `trustedCa` if necessary. The update injects new environment variables into pods with the new `httpProxy`, `httpsProxy`, or `noProxy` values.

> [!CAUTION]
> AKS will automatically reimage all node pools in the cluster when you update the proxy configuration on your cluster using the [`az aks update`][az-aks-update] command. You can use [Pod Disruption Budgets (PDBs)][operator-best-practices-scheduler] to safeguard disruption to critical pods during reimage. 

For example, let's say you created a new file with the base64 encoded string of the new CA cert called *aks-proxy-config-2.json*. You can update the proxy configuration on your cluster with the following command:

```azurecli-interactive
az aks update --name $clusterName --resource-group $resourceGroup --http-proxy-config aks-proxy-config-2.json
```

## Monitoring add-on configuration

HTTP proxy with the monitoring add-on supports the following configurations:

* Outbound proxy without authentication
* Outbound proxy with username & password authentication
* Outbound proxy with trusted cert for Log Analytics endpoint

The following configurations aren't supported:

* Custom Metrics and Recommended Alerts features when using a proxy with trusted certificates

## Next steps

For more information regarding the network requirements of AKS clusters, see [Control egress traffic for cluster nodes in AKS][aks-egress].

<!-- LINKS - internal -->
[aks-egress]: ./limit-egress-traffic.md
[az-aks-create]: /cli/azure/aks#az_aks_create
[az-aks-update]: /cli/azure/aks#az_aks_update
[install-azure-cli]: /cli/azure/install-azure-cli
[istio-add-on-docs]: ./istio-about.md
[operator-best-practices-scheduler]: ./operator-best-practices-scheduler.md

