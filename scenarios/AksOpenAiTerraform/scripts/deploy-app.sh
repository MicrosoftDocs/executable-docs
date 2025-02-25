#!/bin/bash

openAiBase="https://coralopenai.openai.azure.com/"
openAiType="azure_ad"
openAiModel="gpt-35-turbo"
openAiDeployment="gpt-35-turbo"

# Parameters
title="Magic 8 Ball"
label="Pose your question and cross your fingers!"
temperature="0.9"
imageWidth="80"

# Create config map
cat configMap.yml |
    yq "(.data.TITLE)|="\""$title"\" |
    yq "(.data.LABEL)|="\""$label"\" |
    yq "(.data.TEMPERATURE)|="\""$temperature"\" |
    yq "(.data.IMAGE_WIDTH)|="\""$imageWidth"\" |
    yq "(.data.AZURE_OPENAI_TYPE)|="\""$openAiType"\" |
    yq "(.data.AZURE_OPENAI_BASE)|="\""$openAiBase"\" |
    yq "(.data.AZURE_OPENAI_MODEL)|="\""$openAiModel"\" |
    yq "(.data.AZURE_OPENAI_DEPLOYMENT)|="\""$openAiDeployment"\" |
    kubectl apply -n $namespace -f -

# Create deployment
cat deployment.yml |
    yq "(.spec.template.spec.containers[0].image)|="\""$image"\" |
    yq "(.spec.template.spec.containers[0].imagePullPolicy)|="\""$imagePullPolicy"\" |
    yq "(.spec.template.spec.serviceAccountName)|="\""$serviceAccountName"\" |
    kubectl apply -n $namespace -f -

# Create deployment
kubectl apply -f $serviceTemplate -n $namespace