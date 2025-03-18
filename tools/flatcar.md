---
title: Running Flatcar Container Linux on Microsoft Azure
linktitle: Running on Microsoft Azure
weight: 10
aliases:
    - ../../os/booting-on-azure
    - ../../cloud-providers/booting-on-azure
---

## Creating resource group via Microsoft Azure CLI

Follow the [installation and configuration guides][azure-cli] for the Microsoft Azure CLI to set up your local installation.

Instances on Microsoft Azure must be created within a resource group. Create a new resource group with the following command:

```bash
az group create --name group-1 --location <location>
```

Now that you have a resource group, you can choose a channel of Flatcar Container Linux you would like to install.

## Using the official image from the Marketplace

Official Flatcar Container Linux images for all channels are available in the Marketplace.
Flatcar is published by the `kinvolk` publisher on Marketplace.
Flatcar Container Linux is designed to be [updated automatically][update-docs] with different schedules per channel. Updating
can be [disabled][reboot-docs], although it is not recommended to do so. The [release notes][release-notes] contain
information about specific features and bug fixes.

The following command will create a single instance through the Azure CLI.
    
```bash
az vm image list --all -p kinvolk -f flatcar -s stable-gen2 --query '[-1]'  # Query the image name urn specifier
```

```json
{
  "architecture": "x64",
  "offer": "flatcar-container-linux-free",
  "publisher": "kinvolk",
  "sku": "stable-gen2",
  "urn": "kinvolk:flatcar-container-linux-free:stable-gen2:3815.2.0",
  "version": "3815.2.0"
}

Use the offer named `flatcar-container-linux-free`, there is also a legacy offer called `flatcar-container-linux` with the same contents.
The SKU, which is the third element of the image URN, relates to one of the release channels and also depends on whether to use Hyper-V Generation 1 or 2 VM.
Generation 2 instance types use UEFI boot and should be preferred, the SKU matches the pattern `<channel>-gen`: `alpha-gen2`, `beta-gen2` or `stable-gen2`.
For Generation 1 instance types drop the `-gen2` from the SKU: `alpha`, `beta` or `stable`.  
Note: _`az vm image list -s` flag matches parts of the SKU, which means that `-s stable` will return both the `stable` and `stable-gen2` SKUs._

Before being able to use the offers, you may need to accept the legal terms once, here done for `flatcar-container-linux-free` and `stable-gen2`:

```bash
az vm image terms show --publish kinvolk --offer flatcar-container-linux-free --plan stable-gen2
az vm image terms accept --publish kinvolk --offer flatcar-container-linux-free --plan stable-gen2
```

For quick tests the official Azure CLI also supports an alias for the latest Flatcar stable image:
```bash
az vm create --name node-1 --resource-group group-1 --admin-username core --user-data config.ign --image FlatcarLinuxFreeGen2
```

### CoreVM

Flatcar images are also published under an offer called `flatcar-container-linux-corevm-amd64`. This offer does not require accepting image terms and does not require specifying plan information when creating instances or building derived images. The content of the images matches the other offers.
```bash
az vm image list --all -p kinvolk -f flatcar-container-linux-corevm-amd64 -s stable-gen2 --query '[-1]'
```

```json
{
  "architecture": "x64",
  "offer": "flatcar-container-linux-corevm-amd64",
  "publisher": "kinvolk",
  "sku": "stable-gen2",
  "urn": "kinvolk:flatcar-container-linux-corevm-amd64:stable-gen2:3815.2.0",
  "version": "3815.2.0"
}
```

### ARM64
Arm64 images are published under the offer called `flatcar-container-linux-corevm`. These are Generation 2 images, the only supported option on Azure for Arm64 instances, so the SKU contains only the release channel name without the `-gen2` suffix: `alpha`, `beta`, `stable`. This offer has the same properties as the `CoreVM` offer described above.

```bash
az vm image list --all --architecture arm64 -p kinvolk -f flatcar -s stable --query '[-1]'
```

```json
{
  "architecture": "Arm64",
  "offer": "flatcar-container-linux-corevm",
  "publisher": "kinvolk",
  "sku": "stable",
  "urn": "kinvolk:flatcar-container-linux-corevm:stable:3815.2.0",
  "version": "3815.2.0"
}
```



### Flatcar Pro Images

Flatcar Pro images were paid marketplace images that came with commercial support and extra features. All the previous features of Flatcar Pro images, such as support for NVIDIA GPUs, are now available to all users in standard Flatcar marketplace images.

### Plan information for building your image from the Marketplace Image

When building an image based on the Marketplace image you sometimes need to specify the original plan. The plan name is the image SKU, e.g., `stable`, the plan product is the image offer, e.g., `flatcar-container-linux-free`, and the plan publisher is the same (`kinvolk`).

## Community Shared Image Gallery

While the Marketplace images are recommended, it sometimes might be easier or required to use Shared Image Galleries, e.g., when using Packer for Kubernetes CAPI images.

A public Shared Image Gallery hosts recent Flatcar Stable images for amd64. Here is how to show the image definitions (for now you will only find `flatcar-stable-amd64`) and the image versions they provide:

```bash
az sig image-definition list-community --public-gallery-name flatcar-23485951-527a-48d6-9d11-6931ff0afc2e --location westeurope
az sig image-version list-community --public-gallery-name flatcar-23485951-527a-48d6-9d11-6931ff0afc2e --gallery-image-definition flatcar-stable-amd64 --location westeurope
```

A second gallery `flatcar4capi-742ef0cb-dcaa-4ecb-9cb0-bfd2e43dccc0` exists for prebuilt Kubernetes CAPI images. It has image definitions for each CAPI version, e.g., `flatcar-stable-amd64-capi-v1.26.3` which provides recent Flatcar Stable versions.

[flatcar-user]: https://groups.google.com/forum/#!forum/flatcar-linux-user
[etcd-docs]: https://etcd.io/docs
[quickstart]: ../
[reboot-docs]: ../../setup/releases/update-strategies
[azure-cli]: https://docs.microsoft.com/en-us/cli/azure/overview
[butane-configs]: ../../provisioning/config-transpiler
[irc]: irc://irc.freenode.org:6667/#flatcar
[docs]: ../../
[resource-group]: https://docs.microsoft.com/en-us/azure/architecture/best-practices/naming-conventions#naming-rules-and-restrictions
[storage-account]: https://docs.microsoft.com/en-us/azure/storage/common/storage-account-overview#naming-storage-accounts
[azure-flatcar-image-upload]: https://github.com/flatcar/flatcar-cloud-image-uploader
[release-notes]: https://flatcar.org/releases
[update-docs]: ../../setup/releases/update-strategies