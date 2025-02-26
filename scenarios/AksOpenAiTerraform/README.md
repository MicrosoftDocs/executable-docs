---
title: Deploy and run an Azure OpenAI ChatGPT application on AKS via Terraform
description: This article shows how to deploy an AKS cluster and Azure OpenAI Service via Terraform and how to deploy a ChatGPT-like application in Python.
ms.topic: quickstart 
ms.date: 09/06/2024 
author: aamini7
ms.author: ariaamini
ms.custom: innovation-engine, linux-related-content 
---

## Install AKS extension

Run commands below to set up AKS extensions for Azure.

```bash
az extension add --name aks-preview
az aks install-cli
```

## Run Terraform

```bash
export ARM_SUBSCRIPTION_ID=$SUBSCRIPTION_ID
terraform init
terraform apply
```
