---
title: How to deploy and run an Azure OpenAI ChatGPT application on AKS via Terraform
description: This article shows how to deploy an AKS cluster and Azure OpenAI Service via Terraform and how to deploy a ChatGPT-like application in Python.
ms.topic: quickstart 
ms.date: 09/06/2024 
author: aamini7 
ms.author: ariaamini
ms.custom: innovation-engine, linux-related-content 
---

<!-- TODO: PARAMETERIZE REGION AND SUB IDS  -->

## Install AKS extension

Run commands below to set up AKS extensions for Azure.

```bash
./terraform/register-preview-features.sh
```

## Set up service principal

A Service Principal is an application within Azure Active Directory with the authentication tokens Terraform needs to perform actions on your behalf.

```bash
# TODO: fix
# az ad sp create-for-rbac --role="Contributor" --scopes="/subscriptions/$ARM_SUBSCRIPTION_ID"
```

## Setup Infra

```bash
export ARM_SUBSCRIPTION_ID="0c8875c7-e423-4caa-827a-1f0350bd8dd3"
# For debugging in powershell
# $env:ARM_SUBSCRIPTION_ID = "0c8875c7-e423-4caa-827a-1f0350bd8dd3"

terraform apply
```

## Set up environment

```bash
export ARM_CLIENT_ID=""
export ARM_CLIENT_SECRET=""
export ARM_SUBSCRIPTION_ID=""
export ARM_TENANT_ID=""
```
