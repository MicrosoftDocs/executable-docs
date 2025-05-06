---
title: Configure internal NGINX ingress controller for Azure private DNS zone
description: Understand how to configure an ingress controller with a private IP address and an Azure private DNS zone using the application routing add-on for Azure Kubernetes Service. 
ms.subservice: aks-networking
ms.custom: devx-track-azurecli
ms.topic: how-to
ms.date: 10/08/2024
author: asudbring
ms.author: allensu
---

# Configure NGINX ingress controller to support Azure private DNS zone with application routing add-on

This article shows you how to configure an NGINX ingress controller to work with an Azure internal load balancer. It also explains how to configure a private Azure DNS zone to enable DNS resolution for the private endpoints to resolve specific domains.

## Before you begin

- An AKS cluster with the [application routing add-on][app-routing-add-on-basic-configuration].

- To attach an Azure private DNS Zone, you need the [Owner][rbac-owner], [Azure account administrator][rbac-classic], or [Azure coadministrator][rbac-classic] role on your Azure subscription.

## Connect to your AKS cluster

To connect to the Kubernetes cluster from your local computer, you use `kubectl`, the Kubernetes command-line client. You can install it locally using the [az aks install-cli][az-aks-install-cli] command. If you use the Azure Cloud Shell, `kubectl` is already installed.

The following example configures connecting to your cluster named *aks-cluster* in the *test-rg* using the [`az aks get-credentials`][az-aks-get-credentials] command.

```azurecli-interactive
az aks get-credentials \
    --resource-group test-rg \
    --name aks-cluster
```

## Create a virtual network

To publish a private DNS zone to your virtual network, specify a list of virtual networks that are allowed to resolve records within the zone with [virtual network links][virtual-network-links].

The following example creates a virtual network named *vnet-1* in the *test-rg* resource group, and one subnet named *subnet-1* to create within the virtual network with a specific address prefix.

```azurecli-interactive
az network vnet create \
  --name vnet-1 \
  --resource-group test-rg \
  --location eastus \
  --address-prefix 10.2.0.0/16 \
  --subnet-name subnet-1 \
  --subnet-prefixes 10.2.0.0/24
```

## Create an Azure private DNS zone

> [!NOTE]
> You can configure the application routing add-on to automatically create records on one or more Azure global and private DNS zones for hosts defined on ingress resources. All global Azure DNS zones and all private Azure DNS zones must be in the same resource group.

Create a DNS zone using the [az network private-dns zone create][az-network-private-dns-zone-create] command, specifying the name of the zone and the resource group to create it in. The following example creates a DNS zone named *private.contoso.com* in the *test-rg* resource group.

```azurecli-interactive
az network private-dns zone create \
    --resource-group test-rg \
    --name private.contoso.com
```

You create a virtual network link to the DNS zone created earlier using the [az network private-dns link vnet create][az-network-private-dns-link-vnet-create] command. The following example creates a link named *dns-link* to the zone *private.contoso.com* for the virtual network *vnet-1*. Include the `--registration-enabled` parameter to specify the link isn't registration enabled.

```azurecli-interactive
az network private-dns link vnet create \
    --resource-group test-rg \
    --name dns-link \
    --zone-name private.contoso.com \
    --virtual-network vnet-1 \
    --registration-enabled false
```

The Azure DNS private zone auto registration feature manages DNS records for virtual machines deployed in a virtual network. When you link a virtual network with a private DNS zone with this setting enabled, a DNS record gets created for each Azure virtual machine for your AKS node deployed in the virtual network.

## Attach an Azure private DNS zone to the application routing add-on

> [!NOTE]
> The `az aks approuting zone add` command uses the permissions of the user running the command to create the [Azure DNS Zone][azure-dns-zone-role] role assignment. The **Private DNS Zone Contributor** role is a built-in role for managing private DNS resources and is assigned to the add-on's managed identity. For more information on AKS managed identities, see [Summary of managed identities][summary-msi].

1. Retrieve the resource ID for the DNS zone using the [`az network dns zone show`][az-network-dns-zone-show] command and set the output to a variable named `ZONEID`. The following example queries the zone *private.contoso.com* in the resource group *test-rg*.

    ```azurecli-interactive
    ZONEID=$(az network private-dns zone show \
    --resource-group test-rg \
    --name private.contoso.com \
    --query "id" \
    --output tsv)
    ```

1. Update the add-on to enable integration with Azure DNS using the [`az aks approuting zone`][az-aks-approuting-zone] command. You can pass a comma-separated list of DNS zone resource IDs. The following example updates the AKS cluster *aks-cluster* in the resource group *test-rg*.

    ```azurecli-interactive
    az aks approuting zone add \
    --resource-group test-rg \
    --name aks-cluster \
    --ids=${ZONEID} \
    --attach-zones
    ```

## Create an NGINX ingress controller with a private IP address and an internal load balancer

The application routing add-on uses a Kubernetes [custom resource definition (CRD)][k8s-crds] called [`NginxIngressController`][app-routing-crds] to configure NGINX ingress controllers. You can create more ingress controllers or modify an existing configuration.

`NginxIngressController` CRD has a `loadBalancerAnnotations` field to control the behavior of the NGINX ingress controller's service by setting load balancer annotations. For more information about load balancer annotations, see [Customizations via Kubernetes annotations](load-balancer-standard.md#customizations-via-kubernetes-annotations).

Perform the following steps to create an NGINX ingress controller with an internal facing Azure Load Balancer with a private IP address.

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

1. Verify the ingress controller was created

    You can verify the status of the NGINX ingress controller using the [`kubectl get nginxingresscontroller`][kubectl-get] command.

    ```bash
    kubectl get nginxingresscontroller
    ```

    The following example output shows the created resource. It might take a few minutes for the controller to be available:

    ```output
    NAME             INGRESSCLASS                         CONTROLLERNAMEPREFIX   AVAILABLE
    default          webapprouting.kubernetes.azure.com   nginx                  True
    nginx-internal   nginx-internal                       nginx-internal         True
    ```

## Deploy an application

The application routing add-on uses annotations on Kubernetes Ingress objects to create the appropriate resources.

1. Create the application namespace called `aks-store` to run the example pods using the `kubectl create namespace` command.

    ```bash
    kubectl create namespace aks-store
    ```

2. Deploy the AKS store application using the following YAML manifest file:

    ```yaml
    kubectl apply -f https://raw.githubusercontent.com/Azure-Samples/aks-store-demo/main/sample-manifests/docs/app-routing/aks-store-deployments-and-services.yaml -n aks-store
    ```

  This manifest creates the necessary deployments and services for the AKS store application.

## Create the Ingress resource that uses a host name on the Azure private DNS zone and a private IP address

Update **`host`** with the name of your DNS host, for example, **store-front.private.contoso.com**. Verify you're specifying nginx-internal for the ingressClassName.

1. Copy the following YAML manifest into a new file named **ingress.yaml** and save the file to your local computer.

    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: store-front
      namespace: aks-store
    spec:
      ingressClassName: nginx-internal
      rules:
      - host: store-front.private.contoso.com
        http:
          paths:
          - backend:
              service:
                name: store-front
                port:
                  number: 80
            path: /
            pathType: Prefix
    ```

2. Create the ingress resource using the [`kubectl apply`][kubectl-apply] command.


    ```bash
    kubectl apply -f ingress.yaml -n aks-store
    ```

    The following example output shows the created resource:

    ```output
    ingress.networking.k8s.io/store-front created
    ```

## Verify the managed Ingress was created

You can verify the managed Ingress was created using the [`kubectl get ingress`][kubectl-get] command.

```bash
kubectl get ingress -n aks-store
```

The following example output shows the created managed Ingress:

```output
NAME          CLASS            HOSTS                             ADDRESS   PORTS   AGE
store-front   nginx-internal   store-front.private.contoso.com             80      10s
```

## Verify the Azure private DNS zone was updated

In a few minutes, run the [az network private-dns record-set a list][az-network-private-dns-record-set-a-list] command to view the A records for your Azure private DNS zone. Specify the name of the resource group and the name of the DNS zone. In this example, the resource group is *test-rg* and DNS zone is *private.contoso.com*.

```azurecli-interactive
az network private-dns record-set a list \
    --resource-group test-rg \
    --zone-name private.contoso.com
```

The following example output shows the created record:

```output
[
  {
    "aRecords": [
      {
        "ipv4Address": "10.224.0.7"
      }
    ],
    "etag": "ecc303c5-4577-4ca2-b545-d34e160d1c2d",
    "fqdn": "store-front.private.contoso.com.",
    "id": "/subscriptions/aaaa0a0a-bb1b-cc2c-dd3d-eeeeee4e4e4e/resourceGroups/test-rg/providers/Microsoft.Network/privateDnsZones/private.contoso.com/A/store-front",
    "isAutoRegistered": false,
    "name": "store-front",
    "resourceGroup": "test-rg",
    "ttl": 300,
    "type": "Microsoft.Network/privateDnsZones/A"
  }
]
```

## Next steps

For other configuration information related to SSL encryption other advanced NGINX ingress controller and ingress resource configuration, review [DNS and SSL configuration][dns-ssl-configuration] and [application routing add-on configuration][custom-ingress-configurations].

<!-- LINKS - external -->
[kubectl-apply]: https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#apply
[kubectl-get]: https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#get
[kubectl-create-namespace]: https://kubernetes.io/docs/reference/kubectl/generated/kubectl_create/kubectl_create_namespace/
[k8s-crds]: https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/
[app-routing-crds]: https://aka.ms/aks/approuting/nginxingresscontrollercrd

<!-- LINKS - internal -->
[summary-msi]: use-managed-identity.md#summary-of-managed-identities-used-by-aks
[rbac-owner]: /azure/role-based-access-control/built-in-roles#owner
[rbac-classic]: /azure/role-based-access-control/rbac-and-directory-admin-roles#classic-subscription-administrator-roles
[app-routing-add-on-basic-configuration]: app-routing.md
[dns-ssl-configuration]: app-routing-dns-ssl.md
[custom-ingress-configurations]: app-routing-nginx-configuration.md
[az-aks-approuting-zone]: /cli/azure/aks/approuting/zone
[az-network-dns-zone-show]: /cli/azure/network/dns/zone#az-network-dns-zone-show
[az-aks-install-cli]: /cli/azure/aks#az-aks-install-cli
[az-aks-get-credentials]: /cli/azure/aks#az-aks-get-credentials
[virtual-network-links]: /azure/dns/private-dns-virtual-network-links
[azure-dns-zone-role]: /azure/dns/dns-protect-private-zones-recordsets
[az-network-private-dns-zone-create]: /cli/azure/network/private-dns/zone?#az-network-private-dns-zone-create
[az-network-private-dns-link-vnet-create]: /cli/azure/network/private-dns/link/vnet#az-network-private-dns-link-vnet-create
[az-network-private-dns-record-set-a-list]: /cli/azure/network/private-dns/record-set/a#az-network-private-dns-record-set-a-list
