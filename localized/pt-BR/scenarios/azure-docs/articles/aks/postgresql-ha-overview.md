---
title: Visão geral da implantação de um banco de dados PostgreSQL altamente disponível no AKS com a CLI do Azure
description: Saiba como implantar um banco de dados PostgreSQL altamente disponível no AKS usando o operador CloudNativePG!!
ms.topic: overview
ms.date: 07/24/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---
# Implantar um banco de dados PostgreSQL altamente disponível no AKS com a CLI do Azure

Neste guia, você implanta um cluster PostgreSQL altamente disponível que abrange várias zonas de disponibilidade do Azure no AKS com a CLI do Azure!

Este artigo percorre os pré-requisitos para configurar um cluster PostgreSQL no [AKS (Serviço de Kubernetes do Azure)][what-is-aks] e apresenta uma visão geral do processo de implantação completo e da arquitetura.

## Pré-requisitos

* Este guia pressupõe um entendimento básico dos [principais conceitos do Kubernetes][core-kubernetes-concepts] e do [PostgreSQL][postgresql].
* Você precisa do **Proprietário** ou do **Administrador de Acesso do Usuário** e do **Contribuidor** como [funções internas do Azure][azure-roles] em uma assinatura em sua conta do Azure.

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

* Você também precisa ter os seguintes recursos instalados:

  * [CLI do Azure](/cli/azure/install-azure-cli) versão 2.56 ou posterior.
  * [Extensão de pré-visualização do Serviço Azure Kubernetes (AKS)][aks-preview].
  * [jq][jq] versão 1.5 ou posterior.
  * [kubectl][install-kubectl] versão 1.21.0 ou posterior.
  * [Helm][install-helm] versão 3.0.0 ou posterior.
  * [openssl][install-openssl] versão 3.3.0 ou posterior.
  * [Visual Studio Code][install-vscode] ou equivalente.
  * [Krew][install-krew] versão 0.4.4 ou posterior.
  * [Plugin kubectl do CloudNativePG (CNPG)][cnpg-plugin]

## Processo de implantação

Neste guia, você aprenderá a:

* Use a CLI do Azure para criar um cluster AKS de várias zonas.
* Implante um cluster e um banco de dados postgreSQL altamente disponíveis usando o [operador CNPG][cnpg-plugin].
* Configure o monitoramento para PostgreSQL usando o Prometheus e o Grafana.
* Implante um conjunto de dados de exemplo em um banco de dados PostgreSQL.
* Execute atualizações de cluster do PostgreSQL e do AKS.
* Simule uma interrupção de cluster e failover de réplica do PostgreSQL.
* Execute o backup e restauração de um banco de dados PostgreSQL.

## Arquitetura de implantação

O diagrama ilustra uma configuração de cluster PostgreSQL com uma réplica primária e duas réplicas de leitura gerenciadas pelo operador do [CloudNativePG (CNPG)](https://cloudnative-pg.io/). A arquitetura fornece um PostgreSQL altamente disponível em execução em um cluster do AKS que consegue resistir a uma interrupção de zona por fazer failover entre réplicas.

Os backups são armazenados no [Armazenamento de Blobs do Azure](/azure/storage/blobs/), fornecendo outra maneira de restaurar o banco de dados no caso de um problema com a replicação de streaming da réplica primária.

:::image source="./media/postgresql-ha-overview/architecture-diagram.png" alt-text="Diagrama da arquitetura CNPG." lightbox="./media/postgresql-ha-overview/architecture-diagram.png":::

> [!NOTE]
> O operador do CNPG dá suporte a apenas *um banco de dados por cluster*. Faça o planejamento adequado para aplicativos que exigem separação de dados no nível do banco de dados.

## Próximas etapas

> [!div class="nextstepaction"]
> [Criar a infraestrutura para implantar um banco de dados PostgreSQL altamente disponível no AKS usando o operador do CNPG][create-infrastructure]

## Colaboradores

*Este artigo é mantido pela Microsoft. Foi originalmente escrito pelos seguintes colaboradores*:

* Ken Kilty | Principal TPM
* Russell de Pina | Principal TPM
* Adrian Joian | Engenheiro sênior de clientes
* Jenny Hayes | Desenvolvedora sênior de conteúdo
* Carol Smith | Desenvolvedora sênior de conteúdo
* Erin Schaffer | Desenvolvedora de Conteúdo 2
* Adam Sharif | Engenheiro de clientes 2

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
