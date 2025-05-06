---
title: Configure multiple ingress controllers and NGINX ingress annotations with the application routing add-on for Azure Kubernetes Service (AKS)
description: Understand the advanced configuration options that are supported with the application routing add-on with the NGINX ingress controller for Azure Kubernetes Service (AKS). 
ms.subservice: aks-networking
ms.custom: devx-track-azurecli
ms.topic: how-to
ms.date: 11/21/2023
---

# Advanced NGINX ingress controller and ingress configurations with the application routing add-on

The application routing add-on supports two ways to configure ingress controllers and ingress objects:

- [Configuration of the NGINX ingress controller](#configuration-of-the-nginx-ingress-controller) such as creating multiple controllers, configuring private load balancers, and setting static IP addresses.
- [Configuration per ingress resource](#configuration-per-ingress-resource-through-annotations) through annotations.

## Prerequisites

An AKS cluster with the [application routing add-on][app-routing-add-on-basic-configuration].

## Connect to your AKS cluster

To connect to the Kubernetes cluster from your local computer, you use `kubectl`, the Kubernetes command-line client. You can install it locally using the [az aks install-cli][az-aks-install-cli] command. If you use the Azure Cloud Shell, `kubectl` is already installed.

Configure kubectl to connect to your Kubernetes cluster using the [`az aks get-credentials`][az-aks-get-credentials] command.

```azurecli-interactive
az aks get-credentials --resource-group <ResourceGroupName> --name <ClusterName>
```

## Configuration of the NGINX ingress controller

The application routing add-on uses a Kubernetes [custom resource definition (CRD)](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/) called [`NginxIngressController`](https://github.com/Azure/aks-app-routing-operator/blob/main/config/crd/bases/approuting.kubernetes.azure.com_nginxingresscontrollers.yaml) to configure NGINX ingress controllers. You can create more ingress controllers or modify existing configuration.

This table shows a mapping between the application routing operator version and the Kubernetes version.

| Kubernetes version | Operator version |
|---|---|
| <1.30 | 0.2.1-patch-7 |
| >=1.30 | 0.2.3-patch-5 |

This table shows a reference to properties you can set to configure an `NginxIngressController` and the corresponding operator version.

| Property                              | Operator version | Description                                                                                                           |
|---------------------------------------|------------------|-----------------------------------------------------------------------------------------------------------------------|
| **ingressClassName**                  |    [0.1.0](https://github.com/Azure/aks-app-routing-operator/releases/tag/v0.1.0)+   | The name of the `IngressClass` that is used for the NGINX Ingress Controller. Defaults to the name of the `NginxIngressController` if not specified. |
| **controllerNamePrefix**              |   [0.1.0](https://github.com/Azure/aks-app-routing-operator/releases/tag/v0.1.0)+   | A name used to prefix the managed NGINX ingress controller resources. Defaults to `nginx`.                             |
| **loadBalancerAnnotations**           |     [0.1.0](https://github.com/Azure/aks-app-routing-operator/releases/tag/v0.1.0)+    | A set of annotations to control the behavior of the NGINX ingress controller's service by setting [load balancer annotations](load-balancer-standard.md#customizations-via-kubernetes-annotations)  |
| **scaling**                           |                  | Configuration options for how the NGINX Ingress Controller scales.                                                     |
| _scaling.minReplicas_                 |   [0.2.2](https://github.com/Azure/aks-app-routing-operator/releases/tag/v0.2.2)+   | The lower limit for the number of Ingress Controller replicas. It defaults to 2 pods.                                  |
| _scaling.maxReplicas_                 |   [0.2.2](https://github.com/Azure/aks-app-routing-operator/releases/tag/v0.2.2)+   | The upper limit for the number of Ingress Controller replicas. It defaults to 100 pods.                                |
| _scaling.threshold_                   |   [0.2.2](https://github.com/Azure/aks-app-routing-operator/releases/tag/v0.2.2)+   | Defines how quickly the NGINX Ingress Controller pods should scale based on workload. **`Rapid`** means the Ingress Controller scales quickly and aggressively for handling sudden and significant traffic spikes. **`Steady`** prioritizes cost-effectiveness with fewer replicas handling more work. **`Balanced`** is a good mix between the two that works for most use-cases. If unspecified, this field defaults to **`Balanced`**. |
| **defaultSSLCertificate**             |                  | The secret referred to by this property contains the default certificate to be used when accessing the default backend service. If this property is not provided NGINX uses a self-signed certificate. If the `tls:` section is not set on an Ingress, NGINX provides the default certificate but will not force HTTPS redirect.  |                                          
| _defaultSSLCertificate.keyVaultURI_   |     [0.2.2](https://github.com/Azure/aks-app-routing-operator/releases/tag/v0.2.2)+             | The Azure Key Vault URI where the default SSL certificate can be found. The add-on needs to be [configured to use the key vault](app-routing-dns-ssl.md#enable-azure-key-vault-integration). |
| _defaultSSLCertificate.secret_        |   [0.2.2](https://github.com/Azure/aks-app-routing-operator/releases/tag/v0.2.2)+    | Configures the name and namespace where the default SSL secret is on the cluster.                                       |
| _defaultSSLCertificate.secret.name_   |   [0.2.2](https://github.com/Azure/aks-app-routing-operator/releases/tag/v0.2.2)+   | Name of the secret.                                                                                                    |
| _defaultSSLCertificate.secret.namespace_ |   [0.2.2](https://github.com/Azure/aks-app-routing-operator/releases/tag/v0.2.2)+    | Namespace of the secret.                                                                                                |
## Common configurations

### Control the default NGINX ingress controller configuration (preview)

> [!NOTE]
> Controlling the NGINX ingress controller configuration when enabling the add-on is available in `API 2024-06-02-preview`, Kubernetes version 1.30 or later, and the [aks-preview](/cli/azure/aks) Azure CLI extension version `7.0.0b5` or later. To check your AKS cluster version, see [Check for available AKS cluster upgrades][aks-upgrade].

When you enable the application routing add-on with NGINX, it creates an ingress controller called `default` in the `app-routing-namespace` configured with a public facing Azure load balancer. That ingress controller uses an ingress class name of `webapprouting.kubernetes.azure.com`.

You can also control if the default gets a public or an internal IP, or if it gets created at all when enabling the add-on.

Here are the possible configuration options:

- **`None`**: The default Nginx ingress controller is not created and will not be deleted if it already exists. Users should delete the default `NginxIngressController` custom resource manually if desired.
- **`Internal`**: The default Nginx ingress controller is created with an internal load balancer. Any annotations changes on the `NginxIngressController` custom resource to make it external will be overwritten.
- **`External`**: The default Nginx ingress controller created with an external load balancer. Any annotations changes on the `NginxIngressController` custom resource to make it internal will be overwritten.
- **`AnnotationControlled`** (default): The default Nginx ingress controller is created with an external load balancer. Users can edit the default `NginxIngressController` custom resource to configure load balancer annotations.

# [Azure CLI](#tab/azurecli)

#### Control the default ingress controller configuration when creating the cluster

To enable application routing on a new cluster, use the [`az aks create`][az-aks-create] command, specifying the `--enable-app-routing` and the `--app-routing-default-nginx-controller` flags. You need to set the `<DefaultIngressControllerType>` to one of the configuration options described earlier.

```azurecli-interactive
az aks create \
--resource-group <ResourceGroupName> \
--name <ClusterName> \
--location <Location> \
--enable-app-routing \
--app-routing-default-nginx-controller <DefaultIngressControllerType>
```

#### Update the default ingress controller configuration on an existing cluster

To update the application routing default ingress controller configuration on an existing cluster, use the [`az aks approuting update`][az-aks-approuting-update] command, specifying the `--nginx` flag. You need to set the `<DefaultIngressControllerType>` to one of the configuration options described earlier.

```azurecli-interactive
az aks approuting update --resource-group <ResourceGroupName> --name <ClusterName> --nginx <DefaultIngressControllerType>
```

# [Bicep](#tab/bicep)

The `webAppRouting` profile has an optional `nginx` configuration with a `defaultIngressControllerType` property. You need to set the `defaultIngressControllerType` property to one of the configuration options described earlier.

```bicep
"ingressProfile": {
  "webAppRouting": {
    "nginx": {
        "defaultIngressControllerType": "None|Internal|External|AnnotationControlled"
    }
}
```

---

### Create another public facing NGINX ingress controller

To create another NGINX ingress controller with a public facing Azure Load Balancer:

1. Copy the following YAML manifest into a new file named **nginx-public-controller.yaml** and save the file to your local computer.

    ```yml
    apiVersion: approuting.kubernetes.azure.com/v1alpha1
    kind: NginxIngressController
    metadata:
      name: nginx-public
    spec:
      ingressClassName: nginx-public
      controllerNamePrefix: nginx-public
    ```

1. Create the NGINX ingress controller resources using the [`kubectl apply`][kubectl-apply] command.

    ```bash
    kubectl apply -f nginx-public-controller.yaml
    ```

    The following example output shows the created resource:

    ```output
    nginxingresscontroller.approuting.kubernetes.azure.com/nginx-public created
    ```

### Create an internal NGINX ingress controller with a private IP address

To create an NGINX ingress controller with an internal facing Azure Load Balancer with a private IP address:

1. Copy the following YAML manifest into a new file named **nginx-internal-controller.yaml** and save the file to your local computer.

    ```yml
    apiVersion: approuting.kubernetes.azure.com/v1alpha1
    kind: NginxIngressController
    metadata:
      name: nginx-internal
    spec:
      ingressClassName: nginx-internal
      controllerNamePrefix: nginx-internal
      loadBalancerAnnotations: 
        service.beta.kubernetes.io/azure-load-balancer-internal: "true"
    ```

1. Create the NGINX ingress controller resources using the [`kubectl apply`][kubectl-apply] command.

    ```bash
    kubectl apply -f nginx-internal-controller.yaml
    ```

    The following example output shows the created resource:

    ```output
    nginxingresscontroller.approuting.kubernetes.azure.com/nginx-internal created
    ```

### Create an NGINX ingress controller with a static IP address

To create an NGINX ingress controller with a static IP address on the Azure Load Balancer:

1. Create an Azure resource group using the [`az group create`][az-group-create] command.

    ```azurecli-interactive
    az group create --name myNetworkResourceGroup --location eastus
    ```

1. Create a static public IP address using the [`az network public ip create`][az-network-public-ip-create] command.

    ```azurecli-interactive
    az network public-ip create \
        --resource-group myNetworkResourceGroup \
        --name myIngressPublicIP \
        --sku Standard \
        --allocation-method static
    ```

    > [!NOTE]
    > If you're using a *Basic* SKU load balancer in your AKS cluster, use *Basic* for the `--sku` parameter when defining a public IP. Only *Basic* SKU IPs work with the *Basic* SKU load balancer and only *Standard* SKU IPs work with *Standard* SKU load balancers.

1. Ensure the cluster identity used by the AKS cluster has delegated permissions to the public IP's resource group using the [`az role assignment create`][az-role-assignment-create] command.

    > [!NOTE]
    > Update *`<ClusterName>`* and *`<ClusterResourceGroup>`* with your AKS cluster's name and resource group name.

    ```azurecli-interactive
    CLIENT_ID=$(az aks show --name <ClusterName> --resource-group <ClusterResourceGroup> --query identity.principalId -o tsv)
    RG_SCOPE=$(az group show --name myNetworkResourceGroup --query id -o tsv)
    az role assignment create \
        --assignee ${CLIENT_ID} \
        --role "Network Contributor" \
        --scope ${RG_SCOPE}
    ```

1. Copy the following YAML manifest into a new file named **nginx-staticip-controller.yaml** and save the file to your local computer.

    > [!NOTE]
    > You can either use `service.beta.kubernetes.io/azure-pip-name` for public IP name, or use `service.beta.kubernetes.io/azure-load-balancer-ipv4` for an IPv4 address and `service.beta.kubernetes.io/azure-load-balancer-ipv6` for an IPv6 address, as shown in the example YAML. Adding the `service.beta.kubernetes.io/azure-pip-name` annotation ensures the most efficient LoadBalancer creation and is highly recommended to avoid potential throttling. 

    ```yml
    apiVersion: approuting.kubernetes.azure.com/v1alpha1
    kind: NginxIngressController
    metadata:
      name: nginx-static
    spec:
      ingressClassName: nginx-static
      controllerNamePrefix: nginx-static
      loadBalancerAnnotations: 
        service.beta.kubernetes.io/azure-pip-name: "myIngressPublicIP"
        service.beta.kubernetes.io/azure-load-balancer-resource-group: "myNetworkResourceGroup"
    ```

1. Create the NGINX ingress controller resources using the [`kubectl apply`][kubectl-apply] command.

    ```bash
    kubectl apply -f nginx-staticip-controller.yaml
    ```

    The following example output shows the created resource:

    ```output
    nginxingresscontroller.approuting.kubernetes.azure.com/nginx-static created
    ```

### Verify the ingress controller was created

You can verify the status of the NGINX ingress controller using the [`kubectl get nginxingresscontroller`][kubectl-get] command.

> [!NOTE]
> Update *`<IngressControllerName>`* with name you used when creating the `NginxIngressController``.

```bash
kubectl get nginxingresscontroller -n <IngressControllerName>
```

The following example output shows the created resource. It may take a few minutes for the controller to be available:

```output
NAME           INGRESSCLASS   CONTROLLERNAMEPREFIX   AVAILABLE
nginx-public   nginx-public   nginx                  True
```

You can also view the conditions to troubleshoot any issues:

```bash
kubectl get nginxingresscontroller -n <IngressControllerName> -o jsonpath='{range .items[*].status.conditions[*]}{.lastTransitionTime}{"\t"}{.status}{"\t"}{.type}{"\t"}{.message}{"\n"}{end}'
```

The following example output shows the conditions of a healthy ingress controller:

```output
2023-11-29T19:59:24Z    True    IngressClassReady       Ingress Class is up-to-date
2023-11-29T19:59:50Z    True    Available               Controller Deployment has minimum availability and IngressClass is up-to-date
2023-11-29T19:59:50Z    True    ControllerAvailable     Controller Deployment is available
2023-11-29T19:59:25Z    True    Progressing             Controller Deployment has successfully progressed
```

### Use the ingress controller in an ingress

1. Copy the following YAML manifest into a new file named **ingress.yaml** and save the file to your local computer.

    > [!NOTE]
    > Update *`<Hostname>`* with your DNS host name.
    > The *`<IngressClassName>`* is the one you defined when creating the `NginxIngressController`.

    ```yml
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: aks-helloworld
      namespace: hello-web-app-routing
    spec:
      ingressClassName: <IngressClassName>
      rules:
      - host: <Hostname>
        http:
          paths:
          - backend:
              service:
                name: aks-helloworld
                port:
                  number: 80
            path: /
            pathType: Prefix
    ```

3. Create the cluster resources using the [`kubectl apply`][kubectl-apply] command.

    ```bash
    kubectl apply -f ingress.yaml -n hello-web-app-routing
    ```

    The following example output shows the created resource:

    ```output
    ingress.networking.k8s.io/aks-helloworld created
    ```


### Verify the managed Ingress was created

You can verify the managed Ingress was created using the [`kubectl get ingress`][kubectl-get] command.

```bash
kubectl get ingress -n hello-web-app-routing
```

The following example output shows the created managed Ingress. The ingress class, host, and IP address may be different:

```output
NAME             CLASS                                HOSTS               ADDRESS       PORTS     AGE
aks-helloworld   webapprouting.kubernetes.azure.com   myapp.contoso.com   20.51.92.19   80, 443   4m
```

### Clean up of ingress controllers

You can remove the NGINX ingress controller using the [`kubectl delete nginxingresscontroller`][kubectl-delete] command.

> [!NOTE]
> Update *`<IngressControllerName>`* with name you used when creating the `NginxIngressController`.

```bash
kubectl delete nginxingresscontroller -n <IngressControllerName>
```

## Configuration per ingress resource through annotations

The NGINX ingress controller supports adding [annotations to specific Ingress objects](https://kubernetes.github.io/ingress-nginx/user-guide/nginx-configuration/annotations/) to customize their behavior. 

You can [annotate](https://kubernetes.io/docs/concepts/overview/working-with-objects/annotations/) the ingress object by adding the respective annotation in the `metadata.annotations` field.

> [!NOTE]
> Annotation keys and values can only be strings. Other types, such as boolean or numeric values must be quoted, i.e. `"true"`, `"false"`, `"100"`.

Here are some examples annotations for common configurations. Review the [NGINX ingress annotations documentation](https://kubernetes.github.io/ingress-nginx/user-guide/nginx-configuration/annotations/) for a full list.

### Custom max body size

For NGINX, a 413 error is returned to the client when the size in a request exceeds the maximum allowed size of the client request body. To override the default value, use the annotation: 

```yml
nginx.ingress.kubernetes.io/proxy-body-size: 4m
```

Here's an example ingress configuration using this annotation:

> [!NOTE]
> Update *`<Hostname>`* with your DNS host name.
> The *`<IngressClassName>`* is the one you defined when creating the `NginxIngressController`.

```yml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: aks-helloworld
  namespace: hello-web-app-routing
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: 4m
spec:
  ingressClassName: <IngressClassName>
  rules:
  - host: <Hostname>
    http:
      paths:
      - backend:
          service:
            name: aks-helloworld
            port:
              number: 80
        path: /
        pathType: Prefix
```

### Custom connection time out

You can change the time out that the NGINX ingress controller waits to close a connection with your workload. All time out values are unitless and in seconds. To override the default time out, use the following annotation to set a valid 120-seconds proxy read time out:

```yml
nginx.ingress.kubernetes.io/proxy-read-timeout: "120"
```

Review [custom time outs](https://kubernetes.github.io/ingress-nginx/user-guide/nginx-configuration/annotations/#custom-timeouts) for other configuration options.

Here's an example ingress configuration using this annotation:

> [!NOTE]
> Update *`<Hostname>`* with your DNS host name.
> The *`<IngressClassName>`* is the one you defined when creating the `NginxIngressController`.

```yml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: aks-helloworld
  namespace: hello-web-app-routing
  annotations:
    nginx.ingress.kubernetes.io/proxy-read-timeout: "120"
spec:
  ingressClassName: <IngressClassName>
  rules:
  - host: <Hostname>
    http:
      paths:
      - backend:
          service:
            name: aks-helloworld
            port:
              number: 80
        path: /
        pathType: Prefix
```

### Backend protocol

By default the NGINX ingress controller uses `HTTP` to reach the services. To configure alternative backend protocols such as `HTTPS` or `GRPC`, use the annotation:

```yml
nginx.ingress.kubernetes.io/backend-protocol: "HTTPS"
``` 
or
```yml
nginx.ingress.kubernetes.io/backend-protocol: "GRPC"
```

Review [backend protocols](https://kubernetes.github.io/ingress-nginx/user-guide/nginx-configuration/annotations/#backend-protocol) for other configuration options.

Here's an example ingress configuration using this annotation:

> [!NOTE]
> Update *`<Hostname>`* with your DNS host name.
> The *`<IngressClassName>`* is the one you defined when creating the `NginxIngressController`.

```yml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: aks-helloworld
  namespace: hello-web-app-routing
  annotations:
    nginx.ingress.kubernetes.io/backend-protocol: "HTTPS"
spec:
  ingressClassName: <IngressClassName>
  rules:
  - host: <Hostname>
    http:
      paths:
      - backend:
          service:
            name: aks-helloworld
            port:
              number: 80
        path: /
        pathType: Prefix
```

### Cross-Origin Resource Sharing (CORS)

To enable Cross-Origin Resource Sharing (CORS) in an Ingress rule, use the annotation:

```yml
nginx.ingress.kubernetes.io/enable-cors: "true"
```

Review [enable CORS](https://kubernetes.github.io/ingress-nginx/user-guide/nginx-configuration/annotations/#enable-cors) for other configuration options.

Here's an example ingress configuration using this annotation:

> [!NOTE]
> Update *`<Hostname>`* with your DNS host name.
> The *`<IngressClassName>`* is the one you defined when creating the `NginxIngressController`.

```yml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: aks-helloworld
  namespace: hello-web-app-routing
  annotations:
    nginx.ingress.kubernetes.io/enable-cors: "true"
spec:
  ingressClassName: <IngressClassName>
  rules:
  - host: <Hostname>
    http:
      paths:
      - backend:
          service:
            name: aks-helloworld
            port:
              number: 80
        path: /
        pathType: Prefix
```

### Disable SSL redirect

By default the controller redirects (308) to HTTPS if TLS is enabled for an ingress. To disable this feature for specific ingress resources, use the annotation:

```yml
nginx.ingress.kubernetes.io/ssl-redirect: "false"
```

Review [server-side HTTPS enforcement through redirect](https://kubernetes.github.io/ingress-nginx/user-guide/nginx-configuration/annotations/#server-side-https-enforcement-through-redirect) for other configuration options.

Here's an example ingress configuration using this annotation:

> [!NOTE]
> Update *`<Hostname>`* with your DNS host name.
> The *`<IngressClassName>`* is the one you defined when creating the `NginxIngressController`.

```yml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: aks-helloworld
  namespace: hello-web-app-routing
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "false"
spec:
  ingressClassName: <IngressClassName>
  rules:
  - host: <Hostname>
    http:
      paths:
      - backend:
          service:
            name: aks-helloworld
            port:
              number: 80
        path: /
        pathType: Prefix
```

### URL rewriting

In some scenarios, the exposed URL in the backend service differs from the specified path in the Ingress rule. Without a rewrite any request returns 404. This configuration is useful with [path based routing](https://kubernetes.github.io/ingress-nginx/user-guide/ingress-path-matching/) where you can serve two different web applications under the same domain. You can set path expected by the service using the annotation:

```yml
nginx.ingress.kubernetes.io/rewrite-target": /$2
```

Here's an example ingress configuration using this annotation:

> [!NOTE]
> Update *`<Hostname>`* with your DNS host name.
> The *`<IngressClassName>`* is the one you defined when creating the `NginxIngressController`.

```yml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: aks-helloworld
  namespace: hello-web-app-routing
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /$2
    nginx.ingress.kubernetes.io/use-regex: "true"
spec:
  ingressClassName: <IngressClassName>
  rules:
  - host: <Hostname>
    http:
      paths:
      - path: /app-one(/|$)(.*)
        pathType: Prefix 
        backend:
          service:
            name: app-one
            port:
              number: 80
      - path: /app-two(/|$)(.*)
        pathType: Prefix 
        backend:
          service:
            name: app-two
            port:
              number: 80
```

## Next steps

Learn about monitoring the ingress-nginx controller metrics included with the application routing add-on with [with Prometheus in Grafana][prometheus-in-grafana] as part of analyzing the performance and usage of your application.

<!-- LINKS - external -->
[kubectl-apply]: https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#apply
[kubectl-get]: https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#get
[kubectl-delete]: https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#delete

<!-- LINKS - internal -->
[az-network-public-ip-create]: /cli/azure/network/public-ip#az_network_public_ip_create
[az-network-public-ip-list]: /cli/azure/network/public-ip#az_network_public_ip_list
[az-group-create]: /cli/azure/group#az-group-create
[summary-msi]: use-managed-identity.md#summary-of-managed-identities-used-by-aks
[rbac-owner]: ../role-based-access-control/built-in-roles.md#owner
[rbac-classic]: ../role-based-access-control/rbac-and-directory-admin-roles.md#classic-subscription-administrator-roles
[app-routing-add-on-basic-configuration]: app-routing.md
[csi-secrets-store-autorotation]: csi-secrets-store-configuration-options.md#enable-and-disable-auto-rotation
[azure-key-vault-overview]: ../key-vault/general/overview.md
[az-aks-approuting-update]: /cli/azure/aks/approuting#az-aks-approuting-update
[az-aks-approuting-enable]: /cli/azure/aks/approuting#az-aks-approuting-enable
[az-aks-approuting-zone]: /cli/azure/aks/approuting/zone
[az-network-dns-zone-show]: /cli/azure/network/dns/zone#az-network-dns-zone-show
[az-network-dns-zone-create]: /cli/azure/network/dns/zone#az-network-dns-zone-create
[az-keyvault-certificate-import]: /cli/azure/keyvault/certificate#az-keyvault-certificate-import
[az-keyvault-create]: /cli/azure/keyvault#az-keyvault-create
[authorization-systems]: ../key-vault/general/rbac-access-policy.md
[az-aks-install-cli]: /cli/azure/aks#az-aks-install-cli
[az-aks-get-credentials]: /cli/azure/aks#az-aks-get-credentials
[create-and-export-a-self-signed-ssl-certificate]: #create-and-export-a-self-signed-ssl-certificate
[create-an-azure-dns-zone]: #create-a-global-azure-dns-zone
[azure-dns-overview]: ../dns/dns-overview.md
[az-keyvault-certificate-show]: /cli/azure/keyvault/certificate#az-keyvault-certificate-show
[prometheus-in-grafana]: app-routing-nginx-prometheus.md
[az-role-assignment-create]: /cli/azure/role/assignment#az-role-assignment-create
[aks-upgrade]: ./upgrade-cluster.md
[az-aks-create]: /cli/azure/aks#az-aks-create
