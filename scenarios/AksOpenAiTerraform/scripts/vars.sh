cd terraform

RESOURCE_GROUP=$($(terraform output resource_group_name))
LOCATION="westus3"
SUBSCRIPTION_ID=$(az account show --query id --output tsv)
TENANT_ID=$(az account show --query tenantId --output tsv)

# Sample Application
namespace="magic8ball"
serviceAccountName="magic8ball-sa"