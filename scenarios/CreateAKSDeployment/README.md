---
title: Deploy a Scalable & Secure Azure Kubernetes Service cluster using the Azure CLI
description: This tutorial where we will take you step by step in creating an Azure Kubernetes Web Application that is secured via https.
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Quickstart: Deploy a Scalable & Secure Azure Kubernetes Service cluster using the Azure CLI

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262758)

Welcome to this tutorial where we will take you step by step in creating an Azure Kubernetes Web Application that is secured via https. This tutorial assumes you are logged into Azure CLI already and have selected a subscription to use with the CLI. It also assumes that you have Helm installed ([Instructions can be found here](https://helm.sh/docs/intro/install/)).

## Define Environment Variables

The first step in this tutorial is to define environment variables.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export SSL_EMAIL_ADDRESS="$(az account show --query user.name --output tsv)"
export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
```

## Create a resource group

A resource group is a container for related resources. All resources must be placed in a resource group. We will create one for this tutorial. The following command creates a resource group with the previously defined $MY_RESOURCE_GROUP_NAME and $REGION parameters.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Results:

<!-- expected_similarity=0.3 -->

```JSON
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myAKSResourceGroupxxxxxx",
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

## Create AKS Cluster

Create an AKS cluster use the az aks create command. The following example creates a cluster named myAKSCluster with one node and enables a system-assigned managed identity. This will take a few minutes.

```bash
az aks create --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME  --enable-managed-identity --node-count 1 --generate-ssh-keys
```

## Connect to the cluster

To manage a Kubernetes cluster, use the Kubernetes command-line client, kubectl. kubectl is already installed if you use Azure Cloud Shell. To install kubectl locally, call the az aks install-cli command.

1. Install az aks CLI locally using the az aks install-cli command

   ```bash
   if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
   ```

2. Configure kubectl to connect to your Kubernetes cluster using the az aks get-credentials command. The following command:

   - Downloads credentials and configures the Kubernetes CLI to use them.
   - Uses ~/.kube/config, the default location for the Kubernetes configuration file. Specify a different location for your Kubernetes configuration file using --file argument.

   > [!WARNING]
   > This will overwrite any existing credentials with the same entry

   ```bash
   az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
   ```

3. Verify the connection to your cluster using the kubectl get command. This command returns a list of the cluster nodes.

   ```bash
   kubectl get nodes
   ```

## Deploy the Application

A Kubernetes manifest file defines a cluster's desired state, such as which container images to run.

In this quickstart, you will use a manifest to create all objects needed to run the Azure Vote application. This manifest includes two Kubernetes deployments:

- The sample Azure Vote Python applications.
- A Redis instance.

Two Kubernetes Services are also created:

- An internal service for the Redis instance.
- An external service to access the Azure Vote application from the internet.

Finally, an Ingress resource is created to route traffic to the Azure Vote application.

A test voting app YML file is already prepared. To deploy this app run the following command

```bash
kubectl apply -f aks-store-quickstart.yml
```

## Test The Application

Validate that the application is running by either visiting the public ip or the application url. The application url can be found by running the following command:

> [!Note]
> It often takes 2-3 minutes for the PODs to be created and the site to be reachable via HTTP

```bash
runtime="5 minute";
endtime=$(date -ud "$runtime" +%s);
while [[ $(date -u +%s) -le $endtime ]]; do
   STATUS=$(kubectl get pods -l app=store-front -o 'jsonpath={..status.conditions[?(@.type=="Ready")].status}'); echo $STATUS;
   if [ "$STATUS" == 'True' ]; then
      break;
   else
      sleep 10;
   fi;
done
```

```bash
curl "http://$FQDN"
```

Results:

<!-- expected_similarity=0.3 -->

```HTML
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <link rel="stylesheet" type="text/css" href="/static/default.css">
    <title>Azure Voting App</title>

    <script language="JavaScript">
        function send(form){
        }
    </script>

</head>
<body>
    <div id="container">
        <form id="form" name="form" action="/"" method="post"><center>
        <div id="logo">Azure Voting App</div>
        <div id="space"></div>
        <div id="form">
        <button name="vote" value="Cats" onclick="send()" class="button button1">Cats</button>
        <button name="vote" value="Dogs" onclick="send()" class="button button2">Dogs</button>
        <button name="vote" value="reset" onclick="send()" class="button button3">Reset</button>
        <div id="space"></div>
        <div id="space"></div>
        <div id="results"> Cats - 0 | Dogs - 0 </div>
        </form>
        </div>
    </div>
</body>
</html>
```

## Add HTTPS termination to custom domain

At this point in the tutorial you have an AKS web app with NGINX as the Ingress controller and a custom domain you can use to access your application. The next step is to add an SSL certificate to the domain so that users can reach your application securely via HTTPS.

## Set Up Cert Manager

In order to add HTTPS we are going to use Cert Manager. Cert Manager is an open source tool used to obtain and manage SSL certificate for Kubernetes deployments. Cert Manager will obtain certificates from a variety of Issuers, both popular public Issuers as well as private Issuers, and ensure the certificates are valid and up-to-date, and will attempt to renew certificates at a configured time before expiry.

1. In order to install cert-manager, we must first create a namespace to run it in. This tutorial will install cert-manager into the cert-manager namespace. It is possible to run cert-manager in a different namespace, although you will need to make modifications to the deployment manifests.

   ```bash
   kubectl create namespace cert-manager
   ```

2. We can now install cert-manager. All resources are included in a single YAML manifest file. This can be installed by running the following:

   ```bash
   kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
   ```

3. Add the certmanager.k8s.io/disable-validation: "true" label to the cert-manager namespace by running the following. This will allow the system resources that cert-manager requires to bootstrap TLS to be created in its own namespace.

   ```bash
   kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
   ```

## Obtain certificate via Helm Charts

Helm is a Kubernetes deployment tool for automating creation, packaging, configuration, and deployment of applications and services to Kubernetes clusters.

Cert-manager provides Helm charts as a first-class method of installation on Kubernetes.

1. Add the Jetstack Helm repository

   This repository is the only supported source of cert-manager charts. There are some other mirrors and copies across the internet, but those are entirely unofficial and could present a security risk.

   ```bash
   helm repo add jetstack https://charts.jetstack.io
   ```

2. Update local Helm Chart repository cache

   ```bash
   helm repo update
   ```

3. Install Cert-Manager addon via helm by running the following:

   ```bash
   helm install cert-manager jetstack/cert-manager --namespace cert-manager --version v1.7.0
   ```

4. Apply Certificate Issuer YAML File

   ClusterIssuers are Kubernetes resources that represent certificate authorities (CAs) that are able to generate signed certificates by honoring certificate signing requests. All cert-manager certificates require a referenced issuer that is in a ready condition to attempt to honor the request.
   The issuer we are using can be found in the `cluster-issuer-prod.yml file`

   ```bash
   cluster_issuer_variables=$(<cluster-issuer-prod.yml)
   echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
   ```

5. Upate Voting App Application to use Cert-Manager to obtain an SSL Certificate.

   The full YAML file can be found in `azure-vote-nginx-ssl.yml`

   ```bash
   azure_vote_nginx_ssl_variables=$(<azure-vote-nginx-ssl.yml)
   echo "${azure_vote_nginx_ssl_variables//\$FQDN/$FQDN}" | kubectl apply -f -
   ```

<!--## Validate application is working

Wait for the SSL certificate to issue. The following command will query the 
status of the SSL certificate for 3 minutes. In rare occasions it may take up to 
15 minutes for Lets Encrypt to issue a successful challenge and 
the ready state to be 'True'

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(kubectl get certificate --output jsonpath={..status.conditions[0].status}); echo $STATUS; if [ "$STATUS" = 'True' ]; then break; else sleep 10; fi; done
```

Validate SSL certificate is True by running the follow command:

```bash
kubectl get certificate --output jsonpath={..status.conditions[0].status}
```

Results:

<!-- expected_similarity=0.3 -->
<!--
```ASCII
True
```
-->

## Browse your AKS Deployment Secured via HTTPS

Run the following command to get the HTTPS endpoint for your application:

> [!Note]
> It often takes 2-3 minutes for the SSL certificate to propogate and the site to be reachable via HTTPS.

```bash
runtime="5 minute";
endtime=$(date -ud "$runtime" +%s);
while [[ $(date -u +%s) -le $endtime ]]; do
   STATUS=$(kubectl get svc --namespace=ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}');
   echo $STATUS;
   if [ "$STATUS" == "$MY_STATIC_IP" ]; then
      break;
   else
      sleep 10;
   fi;
done
```

```bash
echo "You can now visit your web server at https://$FQDN"
```

## Next Steps

- [Azure Kubernetes Service Documentation](https://learn.microsoft.com/azure/aks/)
- [Create an Azure Container Registry](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-prepare-acr?tabs=azure-cli)
- [Scale your Applciation in AKS](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-scale?tabs=azure-cli)
- [Update your application in AKS](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-app-update?tabs=azure-cli)
