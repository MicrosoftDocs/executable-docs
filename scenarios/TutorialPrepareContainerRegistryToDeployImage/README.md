---
title: Prepare container registry to deploy image
description: Prepare an Azure container registry and push an image
ms.topic: tutorial
ms.author: tomcassidy
author: tomvcassidy
ms.service: container-instances
ms.date: 06/17/2022
ms.custom: innovation-engine, mvc, devx-track-azurecli, linux-related-content
ms.permissions: Microsoft.Resources/resourceGroups/write, Microsoft.ContainerRegistry/registries/listkeys/action, Microsoft.ContainerRegistry/registries/listCredentials/action, Microsoft.ContainerRegistry/registries/read, Microsoft.ContainerRegistry/registries/write, Microsoft.ContainerRegistry/registries/delete, Microsoft.ContainerRegistry/registries/listPublishingCredentials/action, Microsoft.ContainerRegistry/registries/login/action, Microsoft.ContainerRegistry/registries/login/action, Microsoft.ContainerRegistry/registries/read, Microsoft.ContainerRegistry/registries/read, Microsoft.ContainerRegistry/registries/listCredentials/action, Microsoft.Storage/storageAccounts/listKeys/action, Microsoft.Web/hosts/keys/action, Microsoft.ContainerService/managedClusters/list, Microsoft.ContainerRegistry/registries/showQuotaLimitations, Microsoft.Storage/storageAccounts/read, Microsoft.ContainerRegistry/registries/listPermissionsResult, Microsoft.ContainerInstance/containerGroups/list, Microsoft.ContainerRegistry/registries/showPermissions, Microsoft.Storage/storageAccounts/regenerateKey/action, Microsoft.ContainerInstance/containerGroups/read, Microsoft.ContainerRegistry/registries/replications/read, Microsoft.ContainerRegistry/registries/images/read,  Microsoft.ContainerRegistry/registries/read, Microsoft.ContainerRegistry/registries/webhooks/triggerEventSubscriptions/read, Microsoft.ContainerRegistry/registries/sourceRegistrySyncs/read, Microsoft.ContainerRegistry/registries/read, Microsoft.ContainerRegistry/registries/webhooks/read, Microsoft.ContainerRegistry/registries/tasks/read, Microsoft.ContainerRegistry/registries/webhooks/eventGridEventSubscriptions/read, Microsoft.ContainerRegistry/registries/policies/read, Microsoft.ContainerRegistry/registries/docker/change, Microsoft.ContainerRegistry/registries/tasks/runs/list, Microsoft.ContainerRegistry/registries/repositories/list, Microsoft.ContainerRegistry/registries/tasks/webhooks/read, Microsoft.ContainerRegistry/registries/docker/delete, Microsoft.ContainerRegistry/registries/read, Microsoft.ContainerRegistry/registries/repository/read
---

# Tutorial: Create an Azure container registry and push a container image

This is part two of a three-part tutorial. [Part one](container-instances-tutorial-prepare-app.md) of the tutorial created a Docker container image for a Node.js web application. In this tutorial, you push the image to Azure Container Registry. If you haven't yet created the container image, return to [Tutorial 1 – Create container image](container-instances-tutorial-prepare-app.md).

Azure Container Registry is your private Docker registry in Azure. In this tutorial, part two of the series, you:

> [!div class="checklist"]
> * Create an Azure Container Registry instance with the Azure CLI
> * Tag a container image for your Azure container registry
> * Upload the image to your registry

In the next article, the last in the series, you deploy the container from your private registry to Azure Container Instances.

## Before you begin

You must satisfy the following requirements to complete this tutorial:

**Azure CLI**: You must have Azure CLI version 2.0.29 or later installed on your local computer. Run `az --version` to find the version. If you need to install or upgrade, see [Install the Azure CLI][azure-cli-install].

**Docker**: This tutorial assumes a basic understanding of core Docker concepts like containers, container images, and basic `docker` commands. For a primer on Docker and container basics, see the [Docker overview][docker-get-started].

**Docker**: To complete this tutorial, you need Docker installed locally. Docker provides packages that configure the Docker environment on [macOS][docker-mac], [Windows][docker-windows], and [Linux][docker-linux].

```bash
sudo apt-get update
sudo apt-get install docker.io
sudo usermod -aG docker $USER
sudo service docker start
sudo service docker restart
sudo chmod 666 /var/run/docker.sock
```

> [!IMPORTANT]
> Because the Azure Cloud shell does not include the Docker daemon, you *must* install both the Azure CLI and Docker Engine on your *local computer* to complete this tutorial. You cannot use the Azure Cloud Shell for this tutorial.

<!-- LINKS - External -->
[docker-get-started]: https://docs.docker.com/engine/docker-overview/
[docker-linux]: https://docs.docker.com/engine/installation/#supported-platforms
[docker-mac]: https://docs.docker.com/docker-for-mac/
[docker-windows]: https://docs.docker.com/docker-for-windows/

<!-- LINKS - Internal -->
[azure-cli-install]: /cli/azure/install-azure-cli

## Define Environment Variables

The First step in this tutorial is to define environment variables.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export RESOURCE_GROUP=myResourceGroup$RANDOM_ID
export LOCATION=eastus
export ACR_NAME=acrname$RANDOM_ID
export ACR_SKU=Basic
export ACR_QUERY=loginServer
export ACR_OUTPUT=table
export ACR_REPOSITORY=aci-tutorial-app
```

## Login to Azure using the CLI

In order to run commands against Azure using the CLI you need to login. This is done, very simply, though the `az login` command:

## Create a resource group

A resource group is a container for related resources. All resources must be placed in a resource group. We will create one for this tutorial. The following command creates a resource group with the previously defined $RESOURCE_GROUP and $LOCATION parameters.

```bash
az group create --name $RESOURCE_GROUP --location $LOCATION
```

## Get application code

The sample application in this tutorial is a simple web app built in [Node.js][nodejs]. The application serves a static HTML page, and looks similar to the following screenshot:

![Tutorial app shown in browser][aci-tutorial-app]

Use Git to clone the sample application's repository:

```bash
git clone https://github.com/Azure-Samples/aci-helloworld.git
```

You can also [download the ZIP archive][aci-helloworld-zip] from GitHub directly.

## Build the container image

The Dockerfile in the sample application shows how the container is built. It starts from an [official Node.js image][docker-hub-nodeimage] based on [Alpine Linux][alpine-linux], a small distribution that is well suited for use with containers. It then copies the application files into the container, installs dependencies using the Node Package Manager, and finally, starts the application.

```bash
cat << EOF > Dockerfile
FROM node:8.9.3-alpine
RUN mkdir -p /usr/src/app
COPY ./app/* /usr/src/app/
WORKDIR /usr/src/app
RUN npm install
CMD node /usr/src/app/index.js
EOF
```

Use the [docker build][docker-build] command to create the container image and tag it as *aci-tutorial-app*:

```bash
docker build ./aci-helloworld -t aci-tutorial-app
```

Output from the [docker build][docker-build] command is similar to the following (truncated for readability):

```bash
docker build ./aci-helloworld -t aci-tutorial-app
```
```output
Sending build context to Docker daemon  119.3kB
Step 1/6 : FROM node:8.9.3-alpine
8.9.3-alpine: Pulling from library/node
88286f41530e: Pull complete
84f3a4bf8410: Pull complete
d0d9b2214720: Pull complete
Digest: sha256:c73277ccc763752b42bb2400d1aaecb4e3d32e3a9dbedd0e49885c71bea07354
Status: Downloaded newer image for node:8.9.3-alpine
 ---> 90f5ee24bee2
...
Step 6/6 : CMD node /usr/src/app/index.js
 ---> Running in f4a1ea099eec
 ---> 6edad76d09e9
Removing intermediate container f4a1ea099eec
Successfully built 6edad76d09e9
Successfully tagged aci-tutorial-app:latest
```

Use the [docker images][docker-images] command to see the built image:

Your newly built image should appear in the list:

```bash
docker images
```

```output
REPOSITORY          TAG       IMAGE ID        CREATED           SIZE
aci-tutorial-app    latest    5c745774dfa9    39 seconds ago    68.1 MB
```

## Run the container locally

Before you deploy the container to Azure Container Instances, use [docker run][docker-run] to run it locally and confirm that it works. The `-d` switch lets the container run in the background, while `-p` allows you to map an arbitrary port on your computer to port 80 in the container.

Output from the `docker run` command displays the running container's ID if the command was successful:

```bash
docker run -d -p 8080:80 aci-tutorial-app
```

```output
a2e3e4435db58ab0c664ce521854c2e1a1bda88c9cf2fcff46aedf48df86cccf
```

Now, navigate to `http://localhost:8080` in your browser to confirm that the container is running. You should see a web page similar to the following:

![Running the app locally in the browser][aci-tutorial-app-local]


## Create Azure container registry

Before you create your container registry, you need a *resource group* to deploy it to. A resource group is a logical collection into which all Azure resources are deployed and managed.

Create a resource group with the [az group create][az-group-create] command. In the following example, a resource group named *myResourceGroup* is created in the *eastus* region:

```azurecli
az group create --name $RESOURCE_GROUP --location $LOCATION
```

Once you've created the resource group, create an Azure container registry with the [az acr create][az-acr-create] command. The container registry name must be unique within Azure, and contain 5-50 alphanumeric characters. Replace `<acrName>` with a unique name for your registry:

```azurecli
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku $ACR_SKU
```

Here's partial output for a new Azure container registry named *mycontainerregistry082*:

```output
{
  "creationDate": "2020-07-16T21:54:47.297875+00:00",
  "id": "/subscriptions/<Subscription ID>/resourceGroups/myResourceGroup/providers/Microsoft.ContainerRegistry/registries/mycontainerregistry082",
  "location": "eastus",
  "loginServer": "mycontainerregistry082.azurecr.io",
  "name": "mycontainerregistry082",
  "provisioningState": "Succeeded",
  "resourceGroup": "myResourceGroup",
  "sku": {
    "name": "Basic",
    "tier": "Basic"
  },
  "status": null,
  "storageAccount": null,
  "tags": {},
  "type": "Microsoft.ContainerRegistry/registries"
}
```

The rest of the tutorial refers to `<acrName>` as a placeholder for the container registry name that you chose in this step.

## Log in to container registry

You must log in to your Azure Container Registry instance before pushing images to it. Use the [az acr login][az-acr-login] command to complete the operation. You must provide the unique name you chose for the container registry when you created it.

```azurecli
az acr login --name $ACR_NAME 
```

The command returns `Login Succeeded` once completed:

```output
Login Succeeded
```

<!-- LINKS - Internal -->
[az-acr-create]: /cli/azure/acr#az_acr_create
[az-acr-login]: /cli/azure/acr#az_acr_login
[az-group-create]: /cli/azure/group#az_group_create

## Tag container image

To push a container image to a private registry like Azure Container Registry, you must first tag the image with the full name of the registry's login server.

First, get the full login server name for your Azure container registry. Run the following [az acr show][az-acr-show] command, and replace `<acrName>` with the name of registry you just created:

```azurecli-interactive
az acr show --name $ACR_NAME --query $ACR_QUERY --output $ACR_OUTPUT
```

```output
Result
------------------------
mycontainerregistry082.azurecr.io
```

Now, display the list of your local images with the [docker images][docker-images] command:

```bash
docker images
```

```output
REPOSITORY   TAG       IMAGE ID   CREATED   SIZE
```

Along with any other images you have on your machine, you should see the *aci-tutorial-app* image you built in the [previous tutorial](container-instances-tutorial-prepare-app.md):

```bash
docker images
```

```output
REPOSITORY          TAG       IMAGE ID        CREATED           SIZE
aci-tutorial-app    latest    5c745774dfa9    39 minutes ago    68.1 MB
```

Tag the *aci-tutorial-app* image with the login server of your container registry. Also, add the `:v1` tag to the end of the image name to indicate the image version number. Replace `<acrLoginServer>` with the result of the [az acr show][az-acr-show] command you executed earlier.

```bash
docker tag $ACR_REPOSITORY $ACR_NAME.azurecr.io/$ACR_REPOSITORY:v1
```

Run `docker images` again to verify the tagging operation:

```bash
docker images
```

```output
REPOSITORY                                            TAG       IMAGE ID        CREATED           SIZE
aci-tutorial-app                                      latest    5c745774dfa9    39 minutes ago    68.1 MB
mycontainerregistry082.azurecr.io/aci-tutorial-app    v1        5c745774dfa9    7 minutes ago     68.1 MB
```

## Push image to Azure Container Registry

Now that you've tagged the *aci-tutorial-app* image with the full login server name of your private registry, you can push the image to the registry with the [docker push][docker-push] command. Replace `<acrLoginServer>` with the full login server name you obtained in the earlier step.

The `push` operation should take a few seconds to a few minutes depending on your internet connection, and output is similar to the following:

```bash
docker push $ACR_NAME.azurecr.io/$ACR_REPOSITORY:v1
```
```output
The push refers to a repository [mycontainerregistry082.azurecr.io/aci-tutorial-app]
3db9cac20d49: Pushed
13f653351004: Pushed
4cd158165f4d: Pushed
d8fbd47558a8: Pushed
44ab46125c35: Pushed
5bef08742407: Pushed
v1: digest: sha256:ed67fff971da47175856505585dcd92d1270c3b37543e8afd46014d328f05715 size: 1576
```

## List images in Azure Container Registry

To verify that the image you just pushed is indeed in your Azure container registry, list the images in your registry with the [az acr repository list][az-acr-repository-list] command. Replace `<acrName>` with the name of your container registry.

```azurecli-interactive
az acr repository list --name $ACR_NAME --output $ACR_OUTPUT
```

```output
Result
----------------
aci-tutorial-app
```

To see the *tags* for a specific image, use the [az acr repository show-tags][az-acr-repository-show-tags] command.

```azurecli-interactive
az acr repository show-tags --name $ACR_NAME --repository $ACR_REPOSITORY --output $ACR_OUTPUT
```

You should see output similar to the following:

```output
--------
v1
```

## Next steps

In this tutorial, you prepared an Azure container registry for use with Azure Container Instances, and pushed a container image to the registry. The following steps were completed:

> [!div class="checklist"]
> * Created an Azure Container Registry instance with the Azure CLI
> * Tagged a container image for Azure Container Registry
> * Uploaded an image to Azure Container Registry

Advance to the next tutorial to learn how to deploy the container to Azure using Azure Container Instances:

> [!div class="nextstepaction"]
> [Deploy container to Azure Container Instances](container-instances-tutorial-deploy-app.md)

<!-- LINKS - External -->
[docker-build]: https://docs.docker.com/engine/reference/commandline/build/
[docker-get-started]: https://docs.docker.com/get-started/
[docker-hub-nodeimage]: https://store.docker.com/images/node
[docker-images]: https://docs.docker.com/engine/reference/commandline/images/
[docker-linux]: https://docs.docker.com/engine/installation/#supported-platforms
[docker-login]: https://docs.docker.com/engine/reference/commandline/login/
[docker-mac]: https://docs.docker.com/docker-for-mac/
[docker-push]: https://docs.docker.com/engine/reference/commandline/push/
[docker-tag]: https://docs.docker.com/engine/reference/commandline/tag/
[docker-windows]: https://docs.docker.com/docker-for-windows/
[nodejs]: https://nodejs.org

<!-- LINKS - Internal -->
[az-acr-create]: /cli/azure/acr#az_acr_create
[az-acr-login]: /cli/azure/acr#az_acr_login
[az-acr-repository-list]: /cli/azure/acr/repository
[az-acr-repository-show-tags]: /cli/azure/acr/repository#az_acr_repository_show_tags
[az-acr-show]: /cli/azure/acr#az_acr_show
[az-group-create]: /cli/azure/group#az_group_create
[azure-cli-install]: /cli/azure/install-azure-cli

<details>
<summary><h2>FAQs</h2></summary>

#### Q. What is the command-specific breakdown of permissions needed to implement this doc? 

A. _Format: Commands as they appears in the doc | list of unique permissions needed to run each of those commands_
  - ```azurecli az group create --name $RESOURCE_GROUP --location $LOCATION ```

      - Microsoft.Resources/resourceGroups/write
  - ```azurecli az acr create --resource-group $RESOURCE_GROUP --name <acrName> --sku $ACR_SKU ```

      - Microsoft.ContainerRegistry/registries/listkeys/action
      - Microsoft.ContainerRegistry/registries/listCredentials/action
      - Microsoft.ContainerRegistry/registries/read
      - Microsoft.ContainerRegistry/registries/write
      - Microsoft.ContainerRegistry/registries/delete
      - Microsoft.ContainerRegistry/registries/listPublishingCredentials/action
  - ```azurecli az acr login --name <acrName> ```

      - Microsoft.ContainerRegistry/registries/login/action
  - ```azurecli az acr login --name $ACR_NAME ```

      - Microsoft.ContainerRegistry/registries/login/action
  - ```azurecli-interactive az acr show --name <acrName> --query $ACR_QUERY --output $ACR_OUTPUT ```

      - Microsoft.ContainerRegistry/registries/read
  - ```azurecli-interactive az acr show --name $ACR_NAME --query $ACR_QUERY --output $ACR_OUTPUT ```

      - Microsoft.ContainerRegistry/registries/read
      - Microsoft.ContainerRegistry/registries/listCredentials/action
  - ```bash docker images ```

      - 'Microsoft.Storage/storageAccounts/listKeys/action'
      - 'Microsoft.Web/hosts/keys/action'
      - 'Microsoft.ContainerService/managedClusters/list'
      - 'Microsoft.ContainerRegistry/registries/showQuotaLimitations'
      - 'Microsoft.Storage/storageAccounts/read'
      - 'Microsoft.ContainerRegistry/registries/listPermissionsResult'
      - 'Microsoft.ContainerInstance/containerGroups/list'
      - 'Microsoft.ContainerRegistry/registries/showPermissions'
      - 'Microsoft.Storage/storageAccounts/regenerateKey/action'
      - 'Microsoft.ContainerInstance/containerGroups/read'
      - 'Microsoft.ContainerRegistry/registries/replications/read'
      - 'Microsoft.ContainerRegistry/registries/images/read' 
  - ```azurecli-interactive az acr repository list --name <acrName> --output $ACR_OUTPUT ```

      - Microsoft.ContainerRegistry/registries/read
  - ```azurecli-interactive az acr repository list --name $ACR_NAME --output $ACR_OUTPUT ```

      - Microsoft.ContainerRegistry/registries/webhooks/triggerEventSubscriptions/read
      - Microsoft.ContainerRegistry/registries/sourceRegistrySyncs/read
      - Microsoft.ContainerRegistry/registries/read
      - Microsoft.ContainerRegistry/registries/webhooks/read
      - Microsoft.ContainerRegistry/registries/tasks/read
      - Microsoft.ContainerRegistry/registries/webhooks/eventGridEventSubscriptions/read
      - Microsoft.ContainerRegistry/registries/policies/read
      - Microsoft.ContainerRegistry/registries/docker/change
      - Microsoft.ContainerRegistry/registries/tasks/runs/list
      - Microsoft.ContainerRegistry/registries/repositories/list
      - Microsoft.ContainerRegistry/registries/tasks/webhooks/read
      - Microsoft.ContainerRegistry/registries/docker/delete
  - ```azurecli-interactive az acr repository show-tags --name <acrName> --repository $ACR_REPOSITORY --output $ACR_OUTPUT ```

      - Microsoft.ContainerRegistry/registries/read
      - Microsoft.ContainerRegistry/registries/repository/read

#### Q. What are the requirements to complete this tutorial? 

A. To complete this tutorial, you must have Azure CLI version 2.0.29 or later installed on your local computer. You also need to have Docker installed locally. Make sure you have a basic understanding of core Docker concepts like containers, container images, and basic `docker` commands. Refer to the [Docker overview][docker-get-started] for a primer on Docker and container basics.


#### Q. How do I create an Azure container registry? 

A. To create an Azure container registry, you need to first create a resource group to deploy it to using the `az group create` command. Then, use the `az acr create` command to actually create the container registry. Make sure to provide a unique name for the registry. Detailed steps and examples can be found in the [Create Azure container registry](#create-azure-container-registry) section of the tutorial.


#### Q. How do I log in to my Azure container registry? 

A. To log in to your Azure container registry, use the `az acr login` command followed by the name of your registry. This command will authenticate you with the container registry so that you can push images to it. Detailed steps and examples can be found in the [Log in to container registry](#log-in-to-container-registry) section of the tutorial.


#### Q. How do I tag a container image for my Azure container registry? 

A. To tag a container image for your Azure container registry, you need to use the `docker tag` command. First, get the full login server name for your registry using the `az acr show` command. Then, run the `docker tag` command by specifying the image name, the full login server name, and the desired tag (e.g., `:v1`). This command will associate the tagged image with your container registry. Detailed steps and examples can be found in the [Tag container image](#tag-container-image) section of the tutorial.


#### Q. How do I push an image to my Azure container registry? 

A. To push an image to your Azure container registry, use the `docker push` command followed by the full login server name of your registry and the tagged image name. This command will upload the image to your registry. Make sure you are logged in to your registry before pushing the image. Detailed steps and examples can be found in the [Push image to Azure Container Registry](#push-image-to-azure-container-registry) section of the tutorial.


#### Q. How do I list the images in my Azure container registry? 

A. To list the images in your Azure container registry, use the `az acr repository list` command followed by the name of your container registry. This command will display the list of images present in the registry. If you want to see the tags for a specific image, you can use the `az acr repository show-tags` command along with the name of the repository. Detailed steps and examples can be found in the [List images in Azure Container Registry](#list-images-in-azure-container-registry) section of the tutorial.


#### Q. What is the next step after pushing the image to my Azure container registry? 

A. After pushing the image to your Azure container registry, the next step is to deploy the container to Azure Container Instances. You can learn how to do this by following the next tutorial in the series, [Deploy container to Azure Container Instances](container-instances-tutorial-deploy-app.md).

</details>