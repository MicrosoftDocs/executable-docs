#!/bin/bash
aksClusterName="CoralAks"

# Retrieve the resource id of the user-assigned managed identity
echo "Retrieving clientId for [$managedIdentityName] managed identity..."
managedIdentityClientId=$(az identity show \
  --name $managedIdentityName \
  --resource-group $aksResourceGroupName \
  --query clientId \
  --output tsv)

if [[ -n $managedIdentityClientId ]]; then
  echo "[$managedIdentityClientId] clientId  for the [$managedIdentityName] managed identity successfully retrieved"
else
  echo "Failed to retrieve clientId for the [$managedIdentityName] managed identity"
  exit
fi

# Get the OIDC Issuer URL
aksOidcIssuerUrl="$(az aks show \
  --only-show-errors \
  --name $aksClusterName \
  --resource-group $aksResourceGroupName \
  --query oidcIssuerProfile.issuerUrl \
  --output tsv)"

# Establish the federated identity credential between the managed identity, the service account issuer, and the subject.
az identity federated-credential create \
  --name $federatedIdentityName \
  --identity-name $managedIdentityName \
  --resource-group $aksResourceGroupName \
  --issuer $aksOidcIssuerUrl \
  --subject system:serviceaccount:$namespace:$serviceAccountName
if [[ $? == 0 ]]; then
  echo "[$federatedIdentityName] federated identity credential successfully created in the [$aksResourceGroupName] resource group"
else
  echo "Failed to create [$federatedIdentityName] federated identity credential in the [$aksResourceGroupName] resource group"
  exit
fi
