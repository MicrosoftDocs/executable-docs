RESOURCE_GROUP=$($(terraform output resource_group_name))
LOCATION="westus3"
SUBSCRIPTION_ID=$(az account show --query id --output tsv)
TENANT_ID=$(az account show --query tenantId --output tsv)

email="paolos@microsoft.com"

# AKS Cluster
aksResourceGroupName="CoralRG"

# Sample Application
namespace="magic8ball"
serviceAccountName="magic8ball-sa"

deploymentTemplate="deployment.yml"
serviceTemplate="service.yml"
configMapTemplate="configMap.yml"
secretTemplate="secret.yml"