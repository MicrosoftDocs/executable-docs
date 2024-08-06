---
title: 'Szybki start: tworzenie maszyny wirtualnej z systemem Linux przy użyciu interfejsu wiersza polecenia platformy Azure'
description: 'Z tego przewodnika Szybki start dowiesz się, jak utworzyć maszynę wirtualną z systemem Linux za pomocą interfejsu wiersza polecenia platformy Azure'
author: ju-shim
ms.service: virtual-machines
ms.collection: linux
ms.topic: quickstart
ms.date: 03/11/2024
ms.author: jushiman
ms.custom: 'mvc, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Szybki start: tworzenie maszyny wirtualnej z systemem Linux przy użyciu interfejsu wiersza polecenia platformy Azure na platformie Azure

**Dotyczy:** :heavy_check_mark: Maszyny wirtualne z systemem Linux

[![Wdróż na platformie Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262692)

Z tego przewodnika Szybki start dowiesz się, jak za pomocą interfejsu wiersza polecenia platformy Azure wdrożyć maszynę wirtualną platformy Azure. Interfejs wiersza polecenia platformy Azure służy do tworzenia zasobów platformy Azure i zarządzania nimi za pośrednictwem wiersza polecenia lub skryptów.

Jeśli nie masz subskrypcji platformy Azure, przed rozpoczęciem utwórz [bezpłatne konto](https://azure.microsoft.com/free/?WT.mc_id=A261C142F).

## Uruchamianie usługi Azure Cloud Shell

Usługa Azure Cloud Shell to bezpłatna interaktywna powłoka, której możesz używać do wykonywania kroków opisanych w tym artykule. Udostępnia ona wstępnie zainstalowane i najczęściej używane narzędzia platformy Azure, które są skonfigurowane do użycia na koncie. 

Aby otworzyć usługę Cloud Shell, wybierz pozycję **Wypróbuj** w prawym górnym rogu bloku kodu. Możesz również otworzyć usługę Cloud Shell na osobnej karcie przeglądarki, przechodząc do .[https://shell.azure.com/bash](https://shell.azure.com/bash) Wybierz pozycję **Kopiuj** , aby skopiować bloki kodu, wklej go w usłudze Cloud Shell, a następnie wybierz **Enter** , aby go uruchomić.

Jeśli wolisz zainstalować interfejs wiersza polecenia i korzystać z niego lokalnie, ten przewodnik Szybki start wymaga interfejsu wiersza polecenia platformy Azure w wersji 2.0.30 lub nowszej. Uruchom polecenie `az --version`, aby dowiedzieć się, jaka wersja jest używana. Jeśli konieczna będzie instalacja lub uaktualnienie, zobacz [Instalowanie interfejsu wiersza polecenia platformy Azure]( /cli/azure/install-azure-cli).

## Logowanie się do platformy Azure przy użyciu interfejsu wiersza polecenia

Aby uruchamiać polecenia na platformie Azure przy użyciu interfejsu wiersza polecenia, musisz najpierw się zalogować. Zaloguj się przy użyciu `az login` polecenia .

## Tworzenie grupy zasobów

Grupa zasobów to kontener powiązanych zasobów. Wszystkie zasoby należy umieścić w grupie zasobów. Polecenie [az group create](/cli/azure/group) tworzy grupę zasobów z wcześniej zdefiniowanymi parametrami $MY_RESOURCE_GROUP_NAME i $REGION.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Wyniki:

<!-- expected_similarity=0.3 -->
```json
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMResourceGroup",
  "location": "eastus",
  "managedBy": null,
  "name": "myVMResourceGroup",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Tworzenie maszyny wirtualnej

Aby utworzyć maszynę wirtualną w tej grupie zasobów, użyj `vm create` polecenia . 

Poniższy przykład tworzy maszynę wirtualną i dodaje konto użytkownika. Parametr `--generate-ssh-keys` powoduje, że interfejs wiersza polecenia szuka dostępnego klucza SSH w pliku `~/.ssh`. Jeśli zostanie znaleziony, zostanie użyty ten klucz. Jeśli tak nie jest, jest generowany i przechowywany w pliku `~/.ssh`. Parametr `--public-ip-sku Standard` zapewnia, że maszyna jest dostępna za pośrednictwem publicznego adresu IP. Na koniec wdrożymy najnowszy `Ubuntu 22.04` obraz.

Wszystkie inne wartości są konfigurowane przy użyciu zmiennych środowiskowych.

```bash
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
az vm create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_VM_NAME \
    --image $MY_VM_IMAGE \
    --admin-username $MY_USERNAME \
    --assign-identity \
    --generate-ssh-keys \
    --public-ip-sku Standard
```

Utworzenie maszyny wirtualnej i zasobów pomocniczych potrwa kilka minut. Następujące przykładowe dane wyjściowe pokazują, że operacja utworzenia maszyny wirtualnej zakończyła się pomyślnie.

Wyniki:
<!-- expected_similarity=0.3 -->
```json
{
  "fqdns": "",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMResourceGroup/providers/Microsoft.Compute/virtualMachines/myVM",
  "location": "eastus",
  "macAddress": "00-0D-3A-10-4F-70",
  "powerState": "VM running",
  "privateIpAddress": "10.0.0.4",
  "publicIpAddress": "52.147.208.85",
  "resourceGroup": "myVMResourceGroup",
  "zones": ""
}
```

## Włączanie logowania usługi Azure AD dla maszyny wirtualnej z systemem Linux na platformie Azure

Poniższy przykład kodu wdraża maszynę wirtualną z systemem Linux, a następnie instaluje rozszerzenie w celu włączenia logowania usługi Azure AD dla maszyny wirtualnej z systemem Linux. Rozszerzenia maszyn wirtualnych to małe aplikacje, które zapewniają konfigurację po wdrożeniu i zadania automatyzacji na maszynach wirtualnych platformy Azure.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

## Przechowywanie adresu IP maszyny wirtualnej w celu SSH

Uruchom następujące polecenie, aby zapisać adres IP maszyny wirtualnej jako zmienną środowiskową:

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

## Połączenie SSH z maszyną wirtualną

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Log in to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

Teraz możesz połączyć się z maszyną wirtualną za pomocą protokołu SSH, uruchamiając dane wyjściowe następującego polecenia w wybranym kliencie SSH:

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

## Następne kroki

* [Dowiedz się więcej o maszynach wirtualnych](../index.yml)
* [Użyj pakietu Cloud-Init, aby zainicjować maszynę wirtualną z systemem Linux podczas pierwszego rozruchu](tutorial-automate-vm-deployment.md)
* [Tworzenie niestandardowych obrazów maszyn wirtualnych](tutorial-custom-images.md)
* [Równoważenie obciążenia maszyn wirtualnych](../../load-balancer/quickstart-load-balancer-standard-public-cli.md)