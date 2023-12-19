---
title: Tworzenie maszyny wirtualnej z systemem Linux i protokołu SSH na platformie Azure
description: 'W tym samouczku pokazano, jak utworzyć maszynę wirtualną z systemem Linux i protokół SSH na platformie Azure.'
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Tworzenie maszyny wirtualnej z systemem Linux i protokołu SSH na platformie Azure

[![Wdróż na platformie Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/?Microsoft_Azure_CloudNative_clientoptimizations=false&feature.canmodifyextensions=true#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateLinuxVMAndSSH)


## Definiowanie zmiennych środowiskowych

Pierwszym krokiem w tym samouczku jest zdefiniowanie zmiennych środowiskowych.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
```

# Logowanie do platformy Azure przy użyciu interfejsu wiersza polecenia

Aby uruchamiać polecenia na platformie Azure przy użyciu interfejsu wiersza polecenia, musisz się zalogować. Odbywa się to bardzo po prostu, choć `az login` polecenie:

# Tworzenie grupy zasobów

Grupa zasobów to kontener powiązanych zasobów. Wszystkie zasoby należy umieścić w grupie zasobów. Utworzymy go na potrzeby tego samouczka. Następujące polecenie tworzy grupę zasobów z wcześniej zdefiniowanymi parametrami $MY_RESOURCE_GROUP_NAME i $REGION.

```bash
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

Aby utworzyć maszynę wirtualną w tej grupie zasobów, musimy uruchomić proste polecenie, w tym miejscu udostępniliśmy `--generate-ssh-keys` flagę, co spowoduje, że interfejs wiersza polecenia będzie szukać wyczyszwalnego klucza SSH w `~/.ssh`pliku , jeśli zostanie znaleziony, w przeciwnym razie zostanie wygenerowany i zapisany w pliku `~/.ssh`. Udostępniamy również flagę `--public-ip-sku Standard` , aby upewnić się, że maszyna jest dostępna za pośrednictwem publicznego adresu IP. Na koniec wdrażamy najnowszy `Ubuntu 22.04` obraz. 

Wszystkie inne wartości są konfigurowane przy użyciu zmiennych środowiskowych.

```bash
az vm create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_VM_NAME \
    --image $MY_VM_IMAGE \
    --admin-username $MY_USERNAME \
    --assign-identity \
    --generate-ssh-keys \
    --public-ip-sku Standard
```

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

### Włączanie logowania usługi Azure AD dla maszyny wirtualnej z systemem Linux na platformie Azure

W poniższym przykładzie wdrożono maszynę wirtualną z systemem Linux, a następnie instaluje rozszerzenie w celu włączenia logowania do usługi Azure AD dla maszyny wirtualnej z systemem Linux. Rozszerzenia maszyn wirtualnych to małe aplikacje, które zapewniają konfigurację po wdrożeniu i zadania automatyzacji na maszynach wirtualnych platformy Azure.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

# Przechowywanie adresu IP maszyny wirtualnej w celu SSH
Uruchom następujące polecenie, aby uzyskać adres IP maszyny wirtualnej i zapisać go jako zmienną środowiskową

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

# Połączenie SSH z maszyną wirtualną

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Login to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

Teraz możesz połączyć się z maszyną wirtualną za pomocą protokołu SSH, uruchamiając dane wyjściowe następującego polecenia w wybranym kliencie SSH

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

# Następne kroki

* [Dokumentacja maszyny wirtualnej](https://learn.microsoft.com/azure/virtual-machines/)
* [Użyj pakietu Cloud-Init, aby zainicjować maszynę wirtualną z systemem Linux podczas pierwszego rozruchu](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-automate-vm-deployment)
* [Tworzenie niestandardowych obrazów maszyn wirtualnych](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-custom-images)
* [Równoważenie obciążenia maszyn wirtualnych](https://learn.microsoft.com/azure/load-balancer/quickstart-load-balancer-standard-public-cli)
