ingressName="magic8ball-ingress"
publicIpAddress=$(kubectl get ingress $ingressName -n $namespace -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
if [ -n $publicIpAddress ]; then
  echo "[$publicIpAddress] external IP address of the application gateway ingress controller successfully retrieved from the [$ingressName] ingress"
else
  echo "Failed to retrieve the external IP address of the application gateway ingress controller from the [$ingressName] ingress"
  exit
fi

az network dns record-set a add-record \
  --zone-name "contoso.com" \
  --resource-group $RESOURCE_GROUP \
  --record-set-name magic8ball \
  --ipv4-address $publicIpAddress