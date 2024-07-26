---
title: Introducción a la implementación de una base de datos PostgreSQL de alta disponibilidad en AKS con la CLI de Azure
description: Aprenda a implementar una base de datos PostgreSQL de alta disponibilidad en AKS mediante el operador CloudNativePG!!
ms.topic: overview
ms.date: 07/24/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---
# Implementación de una base de datos PostgreSQL de alta disponibilidad en AKS con la CLI de Azure

En esta guía, implementará un clúster de PostgreSQL de alta disponibilidad que abarca varias zonas de disponibilidad de Azure en AKS con la CLI de Azure.

En este artículo se describen los requisitos previos para configurar un clúster de PostgreSQL en [Azure Kubernetes Service (AKS)][what-is-aks] y se proporciona información general sobre el proceso de implementación completo y la arquitectura.

## Requisitos previos

* En esta guía se presupone un conocimiento básico de los [conceptos fundamentales de Kubernetes][core-kubernetes-concepts] y [PostgreSQL][postgresql].
* Necesita los [roles integrados de Azure][azure-roles] **Propietario** o **Administrador de acceso de usuario** y el de **Colaborador** en una suscripción en la cuenta de Azure.

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

* También necesita los siguientes recursos instalados:

  * [CLI de Azure](/cli/azure/install-azure-cli), versión 2.56 o posterior.
  * [Extensión Azure Kubernetes Service (AKS) versión preliminar][aks-preview].
  * [jq][jq] versión 1.5 o posterior.
  * [kubectl][install-kubectl] versión 1.21.0 o posterior.
  * [Helm][install-helm] versión 3.0.0 o posterior.
  * [openssl][install-openssl] versión 3.3.0 o posterior.
  * [Visual Studio Code][install-vscode] o equivalente.
  * [Krew][install-krew] versión 0.4.4 o posterior.
  * [El plugin kubectl CloudNativePG (CNPG)][cnpg-plugin].

## Proceso de implementación

En esta guía, aprenderá a:

* Use la CLI de Azure para crear un clúster de AKS de varias zonas.
* Implemente un clúster y una base de datos de PostgreSQL de alta disponibilidad mediante el [operador CNPG][cnpg-plugin].
* Configure la supervisión de PostgreSQL mediante Prometheus y Grafana.
* Implemente un conjunto de datos de ejemplo en una base de datos PostgreSQL.
* Realice actualizaciones de clúster de PostgreSQL y AKS.
* Simulación de una interrupción del clúster y conmutación por error de réplica de PostgreSQL.
* Realice la copia de seguridad y restauración de una base de datos PostgreSQL.

## Arquitectura de implementación

En este diagrama se muestra una configuración de clúster de PostgreSQL con una réplica principal y dos réplicas de lectura administradas por el [operador CloudNativePG (CNPG)](https://cloudnative-pg.io/). La arquitectura proporciona una instancia de PostgreSQL de alta disponibilidad que se ejecuta en un clúster de AKS que puede resistir una interrupción de zona mediante la conmutación por error entre réplicas.

Las copias de seguridad se almacenan en [Azure Blob Storage](/azure/storage/blobs/), lo que proporciona otra manera de restaurar la base de datos en caso de un problema con la replicación de streaming desde la réplica principal.

:::image source="./media/postgresql-ha-overview/architecture-diagram.png" alt-text="Diagrama de la arquitectura CNPG." lightbox="./media/postgresql-ha-overview/architecture-diagram.png":::

> [!NOTE]
> El operador CNPG solo admite *una base de datos por clúster*. Planee en consecuencia para las aplicaciones que requieren separación de datos en el nivel de base de datos.

## Pasos siguientes

> [!div class="nextstepaction"]
> [Creación de la infraestructura para implementar una base de datos PostgreSQL de alta disponibilidad en AKS mediante el operador CNPG][create-infrastructure]

## Colaboradores

*Microsoft mantiene este artículo. Originalmente fue escrito por los siguientes colaboradores*:

* Ken Kilty | TPM de entidad de seguridad
* Russell de Pina | TPM de entidad de seguridad
* Adrian Joian | Ingeniero de clientes sénior
* Jenny Hayes | Desarrollador de contenido sénior
* Carol Smith | Desarrollador de contenido sénior
* Erin Schaffer | Desarrollador de contenido 2
* Adam Fabric | Ingeniero de clientes 2

<!-- LINKS -->
[what-is-aks]: ./what-is-aks.md
[postgresql]: https://www.postgresql.org/
[core-kubernetes-concepts]: ./concepts-clusters-workloads.md
[azure-roles]: ../role-based-access-control/built-in-roles.md
[aks-preview]: ./draft.md#install-the-aks-preview-azure-cli-extension
[jq]: https://jqlang.github.io/jq/
[install-kubectl]: https://kubernetes.io/docs/tasks/tools/install-kubectl/
[install-helm]: https://helm.sh/docs/intro/install/
[install-openssl]: https://www.openssl.org/
[install-vscode]: https://code.visualstudio.com/Download
[install-krew]: https://krew.sigs.k8s.io/
[cnpg-plugin]: https://cloudnative-pg.io/documentation/current/kubectl-plugin/#using-krew
[create-infrastructure]: ./create-postgresql-ha.md
