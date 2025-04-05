---
title: "Quickstart: Create an Azure IoT Edge Device on Linux"
description: Learn to configure an Azure IoT Edge device on Linux. This guide walks you through creating an IoT Hub, registering a device, and deploying a simulated sensor module.
#customer intent: As a developer, I want to create an IoT Edge device on Linux so that I can deploy and test containerized modules.
author: PatAltimore
ms.author: patricka
ms.date: 03/27/2025
ms.topic: quickstart
ms.service: azure-iot-edge
services: iot-edge
ms.custom: mvc, devx-track-azurecli, mode-other, linux-related-content
---

## Environment Variables

In this section we declare environment variables that will be used throughout the Exec Doc. A random suffix is appended to resource names that must be unique for each deployment.

```bash
export RANDOM_SUFFIX=$(openssl rand -hex 3)
export REGION="eastus2"
export RESOURCE_GROUP="IoTEdgeResources$RANDOM_SUFFIX"
export IOTHUB_NAME="UniqueIoTHub$RANDOM_SUFFIX"
export VM_NAME="myvm$RANDOM_SUFFIX"
```

# Quickstart: Deploy your first IoT Edge module to a virtual Linux device

[!INCLUDE [iot-edge-version-all-supported](includes/iot-edge-version-all-supported.md)]

Try Azure IoT Edge in this quickstart by deploying containerized code to a virtual Linux IoT Edge device. IoT Edge lets you remotely manage code on your devices so you can send more of your workloads to the edge. For this quickstart, use an Azure virtual machine for your IoT Edge device. It lets you quickly create a test machine and delete it when you're done.

In this quickstart, you learn how to:

* Create an IoT Hub.
* Register an IoT Edge device to your IoT hub.
* Install and start the IoT Edge runtime on a virtual device.
* Deploy a module remotely to an IoT Edge device.

:::image type="content" source="./media/quickstart-linux/install-edge-full.png" alt-text="Diagram of Quickstart architecture for device and cloud.":::

This quickstart walks you through creating a Linux virtual machine that's configured to be an IoT Edge device. Then, you deploy a module from the Azure portal to your device. This quickstart uses a simulated sensor module that generates temperature, humidity, and pressure data. The other Azure IoT Edge tutorials build upon the work you do here by deploying additional modules that analyze the simulated data for business insights.

If you don't have an active Azure subscription, create a [free account](https://azure.microsoft.com/free) before you begin.

## Prerequisites

Set up your environment for the Azure CLI.

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

## Create a resource group

A resource group to manage all the resources you use in this quickstart. This quickstart and the following tutorials use the example resource group name **IoTEdgeResources** with a randomized suffix.

   ```azurecli-interactive
   az group create --name $RESOURCE_GROUP --location $REGION
   ```
Results: 

<!-- expected_similarity=0.3 -->
```JSON
{
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/IoTEdgeResourcesabcd12",
  "location": "westus2",
  "managedBy": null,
  "name": "IoTEdgeResourcesabcd12",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Create an IoT Hub

Start the quickstart by creating an IoT Hub with the Azure CLI.

:::image type="content" source="./media/quickstart-linux/create-iot-hub.png" alt-text="Diagram that shows how to create an IoT Hub in the cloud.":::

The free tier of IoT Hub works for this quickstart. If you've used IoT Hub in the past and already have a hub created, you can use that IoT hub.

The following code creates a **S1** hub in the resource group. Replace the placeholder with your preferred IoT Hub name if desired – here we use the environment variable $IOTHUB_NAME. Creating an IoT Hub might take a few minutes.

   ```azurecli-interactive
   az iot hub create --resource-group $RESOURCE_GROUP --name $IOTHUB_NAME --sku S1 --partition-count 2
   ```
Results:

<!-- expected_similarity=0.3 -->
```JSON
{
  "name": "UniqueIoTHubabcd12",
  "sku": "S1",
  "resourceGroup": "IoTEdgeResourcesabcd12",
  "location": "westus2",
  "state": "Active",
  "skuCapacity": 1
}
```

If you use F1 (the free tier), you can only create one IoT Hub per subscription. If you try to create a second hub, you'll receive an error message. In such a case, change the SKU to **S1**. Each subscription can only have one free IoT hub. If you get an error that the IoT Hub name isn't available, it means that someone else already has a hub with that name. Try a new name.

## Register an IoT Edge device

Register an IoT Edge device with the IoT hub you just created.

:::image type="content" source="./media/quickstart-linux/register-device.png" alt-text="Diagram of how to register a device with an IoT Hub identity.":::

Create a device identity for your IoT Edge device so that it can communicate with your IoT hub. The device identity lives in the cloud, and you use a unique device connection string to associate a physical device to a device identity.

Because IoT Edge devices behave and are managed differently from typical IoT devices, declare this identity as an IoT Edge device using the --edge-enabled flag.

1. Enter the following command in Azure Cloud Shell to create a device named **myEdgeDevice** in your hub.

   ```azurecli-interactive
   az config set extension.use_dynamic_install=yes_without_prompt
   az iot hub device-identity create --device-id myEdgeDevice --edge-enabled --hub-name $IOTHUB_NAME
   ```
Results:

<!-- expected_similarity=0.3 -->
```JSON
{
  "deviceId": "myEdgeDevice",
  "generationId": "xxxxxxxx",
  "status": "enabled",
  "connectionState": "Disconnected",
  "statusReason": null,
  "connectionStateUpdatedTime": null,
  "statusUpdatedTime": "2025-03-27T00:00:00.000Z",
  "lastActivityTime": null,
  "cloudToDeviceMessageCount": 0,
  "authentication": {
    "symmetricKey": {
      "primaryKey": "xxxxxxxxxxxxxxxx==",
      "secondaryKey": "xxxxxxxxxxxxxxxx=="
    },
    "type": "sas"
  },
  "capabilities": {
    "iotEdge": true
  },
  "etag": "xxxxxxxxxxxxxx"
}
```

2. Check the connection string for your device, which links the physical device to its identity in IoT Hub. It includes the name of your IoT Hub, the name of your device, and a shared key that authenticates connections between them. You use this connection string again in the next section to set up your IoT Edge device.

   ```azurecli-interactive
   az iot hub device-identity connection-string show --device-id myEdgeDevice --hub-name $IOTHUB_NAME
   ```
Results:

<!-- expected_similarity=0.3 -->
```JSON
{
  "connectionString": "HostName=UniqueIoTHubabcd12.azure-devices.net;DeviceId=myEdgeDevice;SharedAccessKey=xxxxxxxxxxxxxxxxxxxxxxx"
}
```

For example, the connection string should look similar to 
HostName=contoso-hub.azure-devices.net;DeviceId=myEdgeDevice;SharedAccessKey=<DEVICE-SHARED-ACCESS-KEY>.

## Configure your IoT Edge device

Create a virtual machine with the Azure IoT Edge runtime.

:::image type="content" source="./media/quickstart-linux/start-runtime.png" alt-text="Diagram of how to start the runtime on a device.":::

The IoT Edge runtime is deployed on all IoT Edge devices and has three components. The IoT Edge security daemon starts each time an IoT Edge device boots and bootstraps the device by starting the IoT Edge agent. The IoT Edge agent facilitates deployment and monitoring of modules on the IoT Edge device, including the IoT Edge hub. The IoT Edge hub manages communications between modules on the IoT Edge device, and between the device and IoT Hub.

During runtime configuration, provide a device connection string. This string is retrieved from the Azure CLI. This string associates your physical device with the IoT Edge device identity in Azure.

### Deploy the IoT Edge device

This section uses an Azure Resource Manager template to create a new virtual machine and install the IoT Edge runtime on it. If you want to use your own Linux device instead, you can follow the installation steps in [Manually provision a single Linux IoT Edge device](how-to-provision-single-device-linux-symmetric.md), then return to this quickstart.

Use the Deploy to Azure button or CLI commands to create an IoT Edge device based on the prebuilt [iotedge-vm-deploy](https://github.com/Azure/iotedge-vm-deploy) template.

* Deploy using the IoT Edge Azure Resource Manager template.

   [![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fazure%2Fiotedge-vm-deploy%2Fmain%2FedgeDeploy.json)

* For bash or Cloud Shell users, first create a file named **cloud-init.txt** in your current working directory. This file contains the configuration for the IoT Edge runtime:

   ```text
    #cloud-config
    package_update: true
    package_upgrade: true
    runcmd:
      - curl https://packages.microsoft.com/config/ubuntu/22.04/packages-microsoft-prod.deb > packages-microsoft-prod.deb
      - dpkg -i packages-microsoft-prod.deb
      - apt-get update
      - apt-get install aziot-edge -y
      - |
        CONNECTION_STRING="$(az iot hub device-identity connection-string show \
          --device-id myEdgeDevice \
          --hub-name $IOTHUB_NAME \
          -o tsv)"
        iotedge config mp --connection-string "$CONNECTION_STRING"
        iotedge config apply
   ```

* Then, copy the following command into a text editor, replace the placeholder text with your information, then copy into your bash or Cloud Shell window:

   ```azurecli-interactive
   az vm create \
    --resource-group $RESOURCE_GROUP \
    --name $VM_NAME \
    --image Ubuntu2204 \
    --admin-username azureuser \
    --generate-ssh-keys \
    --custom-data cloud-init.txt
   ```

* For PowerShell users, copy the following command into your PowerShell window, then replace the placeholder text with your own information:

   ```powershell
   az deployment group create `
   --resource-group $RESOURCE_GROUP `
   --template-uri "https://raw.githubusercontent.com/Azure/iotedge-vm-deploy/main/edgeDeploy.json" `
   --parameters dnsLabelPrefix="$VM_NAME" `
   --parameters adminUsername='azureUser' `
   --parameters deviceConnectionString=$(az iot hub device-identity connection-string show --device-id myEdgeDevice --hub-name $IOTHUB_NAME -o tsv) `
   --parameters authenticationType='password' `
   --parameters adminPasswordOrKey="<REPLACE_WITH_PASSWORD>"
   ```

This template takes the following parameters:

| Parameter              | Description                                                                                                                                                      |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **resource-group**     | The resource group in which the resources are created. Use the default **IoTEdgeResources** that we've been using throughout this article or provide the name of an existing resource group in your subscription. |
| **template-uri**       | A pointer to the Resource Manager template that we're using.                                                                                                     |
| **dnsLabelPrefix**     | A string that is used to create the virtual machine's hostname. Replace the placeholder text with a name for your virtual machine.                                |
| **adminUsername**      | A username for the admin account of the virtual machine. Use the example **azureUser** or provide a new username.                                                   |
| **deviceConnectionString** | The connection string from the device identity in IoT Hub, which is used to configure the IoT Edge runtime on the virtual machine. The CLI command within this parameter grabs the connection string for you. Replace the placeholder text with your IoT hub name. |
| **authenticationType** | The authentication method for the admin account. This quickstart uses **password** authentication, but you can also set this parameter to **sshPublicKey**.   |
| **adminPasswordOrKey** | The password or value of the SSH key for the admin account. Replace the placeholder text with a secure password. Your password must be at least 12 characters long and have three of four of the following: lowercase characters, uppercase characters, digits, and special characters. |

After deployment completes, JSON-formatted output in the CLI contains the SSH information to connect to the virtual machine. The output includes the public IP address of the virtual machine, which you can use to connect to it.

   ```bash
   export IP_ADDRESS=$(az vm show -d -g $RESOURCE_GROUP -n $VM_NAME --query publicIps -o tsv)
   
   ssh azureuser@$IP_ADDRESS -o StrictHostKeyChecking=no
   ```

### View the IoT Edge runtime status

The rest of the commands in this quickstart take place on your IoT Edge device itself, so that you can see what's happening on the device. If you're using a virtual machine, connect to that machine now using the admin username that you set up and the DNS name that was output by the deployment command. You can also find the DNS name on your virtual machine's overview page in the Azure portal. Use the following command to connect to your virtual machine. Replace <admin-username> and <DNS-name> with your own values.

   ```text
   ssh <admin-username>@<DNS-name>
   ```

Once connected to your virtual machine, verify that the runtime was successfully installed and configured on your IoT Edge device.

1. Check if IoT Edge is running. The following command returns a status of **Ok** if IoT Edge is running or provides any service errors.

   ```bash
   sudo iotedge system status
   ```
Results:

<!-- expected_similarity=0.3 -->
```text
Status:  Ok
```

   >[!TIP]
   >You need elevated privileges to run iotedge commands. Once you sign out of your machine and sign back in the first time after installing the IoT Edge runtime, your permissions are automatically updated. Until then, use sudo in front of the commands.

2. If you need to troubleshoot the service, retrieve the service logs.

   ```bash
   sudo iotedge system logs
   ```
Results:

<!-- expected_similarity=0.3 -->
```text
... (service log output redacted for brevity) ...
```

3. View all the modules running on your IoT Edge device. Since the service just started for the first time, you should only see the **edgeAgent** module running. The edgeAgent module runs by default and helps to install and start any additional modules that you deploy to your device.

   ```bash
   sudo iotedge list
   ```
Results:

<!-- expected_similarity=0.3 -->
```JSON
[
  {
    "Name": "$edgeAgent",
    "Status": "running"
  }
]
```

Your IoT Edge device is now configured. It's ready to run cloud-deployed modules.

## Deploy a module

Manage your Azure IoT Edge device from the cloud to deploy a module that sends device telemetry data to IoT Hub.

:::image type="content" source="./media/quickstart-linux/deploy-module.png" alt-text="Diagram of how to deploy a module from cloud to device.":::

A key capability of Azure IoT Edge is deploying code to your IoT Edge devices from the cloud. IoT Edge modules are executable packages implemented as containers. In this section, you deploy a pre-built module from the [IoT Edge Modules section of Microsoft Artifact Registry](https://mcr.microsoft.com/catalog?cat=IoT%20Edge%20Modules&alphaSort=asc&alphaSortKey=Name).

The module that you deploy in this section simulates a sensor and sends generated data. This module is a useful piece of code when you're getting started with IoT Edge because you can use the simulated data for development and testing. If you want to see exactly what this module does, you can view the [simulated temperature sensor source code](https://github.com/Azure/iotedge/blob/main/edge-modules/SimulatedTemperatureSensor/src/Program.cs).

Use these steps to deploy your first module.

1. Sign in to the [Azure portal](https://portal.azure.com) and go to your IoT Hub.

2. From the menu on the left, under **Device Management**, select **Devices**.

3. Select the device ID of the target IoT Edge device from the list.

   When you create a new IoT Edge device, it displays the status code 417 -- The device's deployment configuration is not set in the Azure portal. This status is normal, and means that the device is ready to receive a module deployment.

4. On the upper bar, select **Set Modules**.

   Select the modules you want to run on your device. You can choose from modules that you've built yourself or images in a container registry. In this quickstart, you deploy a module from the Microsoft container registry.

5. In the **IoT Edge modules** section, select **Add** then choose **IoT Edge Module**.

6. Update the following module settings:

    | Setting            | Value                                                                |
    |--------------------|----------------------------------------------------------------------|
    | IoT Module name    | SimulatedTemperatureSensor                                           |
    | Image URI          | mcr.microsoft.com/azureiotedge-simulated-temperature-sensor:latest    |
    | Restart policy     | always                                                               |
    | Desired status     | running                                                              |

7. Select **Next: Routes** to continue to configure routes.

8. Add a route that sends all messages from the simulated temperature module to IoT Hub.

    | Setting    | Value                                      |
    |------------|--------------------------------------------|
    | Name       | SimulatedTemperatureSensorToIoTHub         |
    | Value      | FROM /messages/modules/SimulatedTemperatureSensor/* INTO $upstream |

9. Select **Next: Review + create**.

10. Review the JSON file, and then select **Create**. The JSON file defines all the modules that you deploy to your IoT Edge device. 

   > [!NOTE]
   > When you submit a new deployment to an IoT Edge device, nothing is pushed to your device. Instead, the device queries IoT Hub regularly for any new instructions. If the device finds an updated deployment manifest, it uses the information about the new deployment to pull the module images from the cloud then starts running the modules locally. This process can take a few minutes.

After you create the module deployment details, the wizard returns you to the device details page. View the deployment status on the **Modules** tab.

You should see three modules: **$edgeAgent**, **$edgeHub**, and **SimulatedTemperatureSensor**. If one or more of the modules has **Yes** under **Specified in Deployment** but not under **Reported by Device**, your IoT Edge device is still starting them. Wait a few minutes and refresh the page.

:::image type="content" source="./media/quickstart-linux/view-deployed-modules.png" alt-text="Screenshot that shows the SimulatedTemperatureSensor in the list of deployed modules." lightbox="./media/quickstart-linux/view-deployed-modules.png":::

If you have issues deploying modules, learn more in [Troubleshoot IoT Edge devices from the Azure portal](troubleshoot-in-portal.md).

## View generated data

In this quickstart, you create a new IoT Edge device and install the IoT Edge runtime on it. Then, you use the Azure portal to deploy an IoT Edge module to run on the device without making changes to the device itself.

In this case, the module that you pushed generates sample environment data that you can use for testing later. The simulated sensor is monitoring both a machine and the environment around the machine. For example, this sensor can be in a server room, on a factory floor, or on a wind turbine. The message includes ambient temperature and humidity, machine temperature and pressure, and a timestamp. The IoT Edge tutorials use the data created by this module as test data for analytics.

Open the command prompt on your IoT Edge device, or use the SSH connection from Azure CLI. Confirm that the module you deployed from the cloud is running on your IoT Edge device:

```bash
sudo iotedge list
```
Results:

<!-- expected_similarity=0.3 -->
```JSON
[
  {
    "Name": "$edgeAgent",
    "Status": "running"
  },
  {
    "Name": "$edgeHub",
    "Status": "running"
  },
  {
    "Name": "SimulatedTemperatureSensor",
    "Status": "running"
  }
]
```

View the messages sent from the temperature sensor module:

```bash
sudo iotedge logs SimulatedTemperatureSensor -f
```
Results:

<!-- expected_similarity=0.3 -->
```text
... (sample sensor data output redacted for brevity) ...
```

>[!TIP]
>IoT Edge commands are case sensitive when referring to module names.

## Clean up resources

To continue with the IoT Edge tutorials, use the device you registered and set up in this quickstart. Otherwise, delete the Azure resources you created to avoid charges.

If you created your virtual machine and IoT hub in a new resource group, you can delete that group and all the associated resources. Double-check the contents of the resource group to ensure there's nothing you want to keep. If you don't want to delete the whole group, you can delete individual resources instead.

> [!IMPORTANT]
> Deleting a resource group is irreversible.

(The deletion commands have been removed from this Exec Doc to avoid accidental deletion during automated execution.)

## Next steps

In this quickstart, you created an IoT Edge device and used the Azure IoT Edge cloud interface to deploy code onto the device. Now, you use a test device that generates raw data about its environment.

In the next tutorial, you'll learn how to monitor the activity and health of your device from the Azure portal.

> [!div class="nextstepaction"]
> [Monitor IoT Edge devices](tutorial-monitor-with-workbooks.md)