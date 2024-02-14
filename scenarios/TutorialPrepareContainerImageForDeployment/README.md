---
title: Prepare container image for deployment
description: Prepare an app in a container image for deployment to Azure Container Instances
ms.topic: tutorial
ms.author: tomcassidy
author: tomvcassidy
ms.service: container-instances
ms.date: 06/17/2022
ms.custom: innovation-engine, mvc, linux-related-content
ms.permissions: Microsoft.Storage/storageAccounts/listKeys/action, Microsoft.Web/hosts/keys/action, Microsoft.ContainerService/managedClusters/list, Microsoft.ContainerRegistry/registries/showQuotaLimitations, Microsoft.Storage/storageAccounts/read, Microsoft.ContainerRegistry/registries/listPermissionsResult, Microsoft.ContainerInstance/containerGroups/list, Microsoft.ContainerRegistry/registries/showPermissions, Microsoft.Storage/storageAccounts/regenerateKey/action, Microsoft.ContainerInstance/containerGroups/read, Microsoft.ContainerRegistry/registries/replications/read, Microsoft.ContainerRegistry/registries/images/read, Microsoft.Network/loadBalancers/providers/microsoft.insights/diagnosticSettings/write, Microsoft.Network/virtualNetworks/providers/microsoft.insights/logProfiles/read, Microsoft.Web/sites/providers/microsoft.insights/read, Microsoft.Network/virtualNetworks/providers/microsoft.insights/diagnosticSettings/read, Microsoft.Web/sites/read, Microsoft.Network/virtualNetworks/providers/microsoft.insights/write, Microsoft.Network/loadBalancers/providers/microsoft.insights/write, Microsoft.Network/networkInterfaces/providers/microsoft.insights/logProfiles/read, Microsoft.Web/sites/providers/microsoft.insights/write, Microsoft.Network/networkInterfaces/providers/microsoft.insights/diagnosticSettings/read, Microsoft.Network/networkInterfaces/providers/microsoft.insights/write, Microsoft.Web/sites/providers/diagnosticSettings/read, Microsoft.Network/loadBalancers/providers/microsoft.insights/read, Microsoft.Network/networkInterfaces/providers/microsoft.insights/diagnosticSettings/write, Microsoft.Storage/storageAccounts/listKeys/action, Microsoft.Network/virtualNetworks/providers/microsoft.insights/diagnosticSettings/write, Microsoft.Storage/storageAccounts/read, Microsoft.Network/networkInterfaces/providers/microsoft.insights/read, Microsoft.Web/sites/metricDefinitions/list, Microsoft.Web/sites/metrics/list, Microsoft.Web/sites/providers/microsoft.insights/logProfiles/write, Microsoft.Network/networkInterfaces/providers/microsoft.insights/logProfiles/write, Microsoft.Web/sites/providers/microsoft.insights/alertrules/read, Microsoft.Web/sites/metrics/write, Microsoft.Network/loadBalancers/read, Microsoft.Web/sites/stop/action, Microsoft.Network/networkInterfaces/providers/diagnosticSettings/read, Microsoft.Network/virtualNetworks/providers/microsoft.insights/read, Microsoft.Web/sites/write, Microsoft.Web/sites/metrics/read, Microsoft.Network/loadBalancers/providers/diagnosticSettings/read, Microsoft.Network/loadBalancers/providers/microsoft.insights/logProfiles/write, Microsoft.Network/loadBalancers/providers/microsoft.insights/diagnosticSettings/read, Microsoft.ContainerInstance/containerGroups/delete, Microsoft.Network/virtualNetworks/providers/microsoft.insights/logProfiles/write, Microsoft.Storage/storageAccounts/listkeys/action, Microsoft.Network/publicIPAddresses/read, Microsoft.Network/loadBalancers/providers/microsoft.insights/logProfiles/read, Microsoft.Web/sites/providers/microsoft.insights/diagnosticSettings/write, Microsoft.Web/sites/metricDefinitions/write, Microsoft.Network/virtualNetworks/read, Microsoft.Network/networkInterfaces/read, Microsoft.Web/sites/metricDefinitions/read, Microsoft.ContainerInstance/containerGroups/write, Microsoft.Web/sites/providers/microsoft.insights/alertrules/write, Microsoft.Web/sites/providers/microsoft.insights/logProfiles/read, Microsoft.Web/sites/providers/microsoft.insights/diagnosticSettings/read, Microsoft.Web/sites/providers/microsoft.insights/alertrules/delete, Microsoft.Network/virtualNetworks/providers/diagnosticSettings/read, Microsoft.Network/virtualNetworks/subnets/read, Microsoft.Network/virtualNetworks/subnets/write, Microsoft.ContainerInstance/containerGroups/delete, Microsoft.Network/virtualNetworks/read, Microsoft.ContainerInstance/containerGroups/write, Microsoft.Network/virtualNetworks/subnets/join/action
---

# Tutorial: Create a container image for deployment to Azure Container Instances

Azure Container Instances enables deployment of Docker containers onto Azure infrastructure without provisioning any virtual machines or adopting a higher-level service. In this tutorial, you package a small Node.js web application into a container image that can be run using Azure Container Instances.

In this article, part one of the series, you:

> [!div class="checklist"]
> * Clone application source code from GitHub
> * Create a container image from application source
> * Test the image in a local Docker environment

In tutorial parts two and three, you upload your image to Azure Container Registry, and then deploy it to Azure Container Instances.

## Before you begin

You must satisfy the following requirements to complete this tutorial:

**Azure CLI**: You must have Azure CLI version 2.0.29 or later installed on your local computer. Run `az --version` to find the version. If you need to install or upgrade, see [Install the Azure CLI][azure-cli-install].

**Docker**: This tutorial assumes a basic understanding of core Docker concepts like containers, container images, and basic `docker` commands. For a primer on Docker and container basics, see the [Docker overview][docker-get-started].

**Docker**: To complete this tutorial, you need Docker installed locally. Docker provides packages that configure the Docker environment on [macOS][docker-mac], [Windows][docker-windows], and [Linux][docker-linux].

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
export LOCATION=EastUS
```
# Login to Azure using the CLI

In order to run commands against Azure using the CLI you need to login. This is done, very simply, though the `az login` command:

# Create a resource group

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

## Next steps

In this tutorial, you created a container image that can be deployed in Azure Container Instances, and verified that it runs locally. So far, you've done the following:

> [!div class="checklist"]
> * Cloned the application source from GitHub
> * Created a container image from the application source
> * Tested the container locally

Advance to the next tutorial in the series to learn about storing your container image in Azure Container Registry:

> [!div class="nextstepaction"]
> [Push image to Azure Container Registry](container-instances-tutorial-prepare-acr.md)

<!--- IMAGES --->
[aci-tutorial-app]:./media/container-instances-quickstart/aci-app-browser.png
[aci-tutorial-app-local]: ./media/container-instances-tutorial-prepare-app/aci-app-browser-local.png

<!-- LINKS - External -->
[aci-helloworld-zip]: https://github.com/Azure-Samples/aci-helloworld/archive/master.zip
[alpine-linux]: https://alpinelinux.org/
[docker-build]: https://docs.docker.com/engine/reference/commandline/build/
[docker-get-started]: https://docs.docker.com/get-started/
[docker-hub-nodeimage]: https://store.docker.com/images/node
[docker-images]: https://docs.docker.com/engine/reference/commandline/images/
[docker-linux]: https://docs.docker.com/engine/installation/#supported-platforms
[docker-login]: https://docs.docker.com/engine/reference/commandline/login/
[docker-mac]: https://docs.docker.com/docker-for-mac/
[docker-push]: https://docs.docker.com/engine/reference/commandline/push/
[docker-run]: https://docs.docker.com/engine/reference/commandline/run/
[docker-tag]: https://docs.docker.com/engine/reference/commandline/tag/
[docker-windows]: https://docs.docker.com/docker-for-windows/
[nodejs]: https://nodejs.org

<!-- LINKS - Internal -->
[azure-cli-install]: /cli/azure/install-azure-cli

<details>
<summary><h2>FAQs</h2></summary>

#### Q. What is the command-specific breakdown of permissions needed to implement this doc? 

A. _Format: Commands as they appears in the doc | list of unique permissions needed to run each of those commands_
  - '```bash\ndocker images\n```'
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
  - '```bash\ndocker run -d -p 8080:80 aci-tutorial-app\n```'
      - 'Microsoft.Network/loadBalancers/providers/microsoft.insights/diagnosticSettings/write'
      - 'Microsoft.Network/virtualNetworks/providers/microsoft.insights/logProfiles/read'
      - 'Microsoft.Web/sites/providers/microsoft.insights/read'
      - 'Microsoft.Network/virtualNetworks/providers/microsoft.insights/diagnosticSettings/read', 'Microsoft.Web/sites/read'
      - 'Microsoft.Network/virtualNetworks/providers/microsoft.insights/write'
      - 'Microsoft.Network/loadBalancers/providers/microsoft.insights/write'
      - 'Microsoft.Network/networkInterfaces/providers/microsoft.insights/logProfiles/read'
      - 'Microsoft.Web/sites/providers/microsoft.insights/write'
      - 'Microsoft.Network/networkInterfaces/providers/microsoft.insights/diagnosticSettings/read'
      - 'Microsoft.Network/networkInterfaces/providers/microsoft.insights/write'
      - 'Microsoft.Web/sites/providers/diagnosticSettings/read'
      - 'Microsoft.Network/loadBalancers/providers/microsoft.insights/read'
      - 'Microsoft.Network/networkInterfaces/providers/microsoft.insights/diagnosticSettings/write'
      - 'Microsoft.Storage/storageAccounts/listKeys/action'
      - 'Microsoft.Network/virtualNetworks/providers/microsoft.insights/diagnosticSettings/write'
      - 'Microsoft.Storage/storageAccounts/read'
      - 'Microsoft.Network/networkInterfaces/providers/microsoft.insights/read'
      - 'Microsoft.Web/sites/metricDefinitions/list'
      - 'Microsoft.Web/sites/metrics/list'
      - 'Microsoft.Web/sites/providers/microsoft.insights/logProfiles/write'
      - 'Microsoft.Network/networkInterfaces/providers/microsoft.insights/logProfiles/write'
      - 'Microsoft.Web/sites/providers/microsoft.insights/alertrules/read'
      - 'Microsoft.Web/sites/metrics/write'
      - 'Microsoft.Network/loadBalancers/read'
      - 'Microsoft.Web/sites/stop/action'
      - 'Microsoft.Network/networkInterfaces/providers/diagnosticSettings/read'
      - 'Microsoft.Network/virtualNetworks/providers/microsoft.insights/read'
      - 'Microsoft.Web/sites/write'
      - 'Microsoft.Web/sites/metrics/read'
      - 'Microsoft.Network/loadBalancers/providers/diagnosticSettings/read'
      - 'Microsoft.Network/loadBalancers/providers/microsoft.insights/logProfiles/write'
      - 'Microsoft.Network/loadBalancers/providers/microsoft.insights/diagnosticSettings/read'
      - 'Microsoft.ContainerInstance/containerGroups/delete'
      - 'Microsoft.Network/virtualNetworks/providers/microsoft.insights/logProfiles/write'
      - 'Microsoft.Storage/storageAccounts/listkeys/action'
      - 'Microsoft.Network/publicIPAddresses/read'
      - 'Microsoft.Network/loadBalancers/providers/microsoft.insights/logProfiles/read'
      - 'Microsoft.Web/sites/providers/microsoft.insights/diagnosticSettings/write'
      - 'Microsoft.Web/sites/metricDefinitions/write'
      - 'Microsoft.Network/virtualNetworks/read'
      - 'Microsoft.Network/networkInterfaces/read'
      - 'Microsoft.Web/sites/metricDefinitions/read'
      - 'Microsoft.ContainerInstance/containerGroups/write'
      - 'Microsoft.Web/sites/providers/microsoft.insights/alertrules/write'
      - 'Microsoft.Web/sites/providers/microsoft.insights/logProfiles/read'
      - 'Microsoft.Web/sites/providers/microsoft.insights/diagnosticSettings/read'
      - 'Microsoft.Web/sites/providers/microsoft.insights/alertrules/delete'
      - 'Microsoft.Network/virtualNetworks/providers/diagnosticSettings/read'
      - 'Microsoft.Network/virtualNetworks/subnets/read'
      - 'Microsoft.Network/virtualNetworks/subnets/write'
      - 'Microsoft.ContainerInstance/containerGroups/delete'
      - 'Microsoft.Network/virtualNetworks/read'
      - 'Microsoft.ContainerInstance/containerGroups/write'
      - 'Microsoft.Network/virtualNetworks/subnets/join/action'

#### Q. What requirements do I need to satisfy to complete this tutorial? 

A. You need to have Azure CLI version 2.0.29 or later installed on your local computer. Run 'az --version' to check the version. If you need to install or upgrade Azure CLI, you can refer to the guide on [Install the Azure CLI](/cli/azure/install-azure-cli). Additionally, you need Docker installed locally. Docker provides packages for configuring the Docker environment on [macOS](https://docs.docker.com/docker-for-mac/), [Windows](https://docs.docker.com/docker-for-windows/), and [Linux](https://docs.docker.com/engine/installation/#supported-platforms).


#### Q. How can I clone the sample application's repository? 

A. You can use Git to clone the sample application's repository by running the following command: `git clone https://github.com/Azure-Samples/aci-helloworld.git`. Alternatively, you can also download the ZIP archive directly from [GitHub](https://github.com/Azure-Samples/aci-helloworld/archive/master.zip).


#### Q. How can I build the container image? 

A. To build the container image, you can use the `docker build` command. Make sure you are in the root directory of the cloned sample application. The Dockerfile in the sample application specifies the steps for building the container image. Run the following command: `docker build ./aci-helloworld -t aci-tutorial-app`. This command builds the image using the Dockerfile in the `aci-helloworld` directory and tags it as `aci-tutorial-app`.


#### Q. How can I run the container locally? 

A. Before deploying the container to Azure Container Instances, you can run it locally using the `docker run` command. This command runs the container in the background and maps port 8080 on your computer to port 80 in the container. Run the following command: `docker run -d -p 8080:80 aci-tutorial-app`. After running the command, you can navigate to `http://localhost:8080` in your browser to confirm that the container is running. You should see a web page similar to the one shown in the tutorial.


#### Q. What are the next steps after completing this tutorial? 

A. After completing this tutorial, you have created a container image that can be deployed in Azure Container Instances and verified that it runs locally. The next step is to learn about storing your container image in Azure Container Registry. You can proceed to the next tutorial in the series, [Push image to Azure Container Registry](container-instances-tutorial-prepare-acr.md), to learn more.

</details>
