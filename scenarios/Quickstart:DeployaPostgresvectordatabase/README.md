---
title: Quickstart: Deploy a Postgres vector database
description: Setup a Postgres vector database and openai resources to run a RAG-LLM model.
ms.topic: quickstart
ms.date: 01-16-2025
ms.author: pjsingh@microsoft.com
ms.custom: ion-engine, linux-related-content
---

## Introduction

In this doc, we go over how to host the infrastructure required to run a basic LLM model with RAG capabilities on Azure.
We first set up a Postgres database capable of storing vector embeddings for documents/knowledge files that we want to use to
augment our queries. We then create an Azure OpenAI deployment capable of generating embeddings and answering questions using the latest 'gpt-4-turbo' model.
We then use a python script to fill our postgres database with embeddings from a sample knowledge.txt file containing information about an imaginary
resource called 'Zytonium'. Once the database is filled with those embeddings, we use the same python script to answer any
questions we have about 'Zytonium'. The script will search the database for relevant information for our query using an embeddings search and
then augment our query with that relevant information before being sent our LLM to answer.

```bash

```

## Set up resource group

Set up a resource group with a random ID.

```bash
export RANDOM_ID=a66569
export RG_NAME=myPostgresResourceGroup
export REGION=centralus

az group create     --name      --location  
```


