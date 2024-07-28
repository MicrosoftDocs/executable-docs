---
title: Visão geral da implantação de um banco de dados PostgreSQL altamente disponível no AKS com a CLI do Azure
description: Saiba como implantar um banco de dados PostgreSQL altamente disponível no AKS usando o operador CloudNativePG com a CLI do Azure.
ms.topic: overview
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---
# Implantar um banco de dados PostgreSQL altamente disponível no AKS com a CLI do Azure

Neste guia, você implanta um cluster PostgreSQL altamente disponível que abrange várias zonas de disponibilidade do Azure no AKS com a CLI do Azure.

Este artigo descreve os pré-requisitos para configurar um cluster PostgreSQL no [Serviço Kubernetes do Azure (AKS)][what-is-aks] e fornece uma visão geral do processo de implantação completo e da arquitetura.

## Pré-requisitos

* Este guia pressupõe uma compreensão básica dos principais conceitos[ do Kubernetes e [do ][core-kubernetes-concepts]PostgreSQL.][postgresql]
* Você precisa do **Proprietário** ou **Administrador de Acesso de Usuário** e das funções[ internas do **Azure de Colaborador** ][azure-roles]em uma assinatura em sua conta do Azure.

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

* Você também precisa dos seguintes recursos instalados:

  * [Azure CLI](/cli/azure/install-azure-cli) versão 2.56 ou posterior.
  * [Extensão][aks-preview] de visualização do Serviço Kubernetes do Azure (AKS).
  * [JQ][jq], versão 1.5 ou posterior.
  * [Kubectl][install-kubectl] versão 1.21.0 ou posterior.
  * [Helm][install-helm] versão 3.0.0 ou posterior.
  * [OpenSSL][install-openssl] versão 3.3.0 ou posterior.
  * [Visual Studio Code][install-vscode] ou equivalente.
  * [Krew][install-krew] versão 0.4.4 ou posterior.
  * [kubectl CloudNativePG (CNPG) Plugin][cnpg-plugin].

## Processo de implementação

Neste guia, ficará a saber como:

* Use a CLI do Azure para criar um cluster AKS de várias zonas.
* Implante um cluster e banco de dados PostgreSQL altamente disponíveis usando o [operador][cnpg-plugin] CNPG.
* Configure o monitoramento para PostgreSQL usando Prometheus e Grafana.
* Implante um conjunto de dados de exemplo em um banco de dados PostgreSQL.
* Execute atualizações de cluster PostgreSQL e AKS.
* Simule uma interrupção de cluster e failover de réplica do PostgreSQL.
* Execute backup e restauração de um banco de dados PostgreSQL.

## Arquitetura de implantação

Este diagrama ilustra uma configuração de cluster PostgreSQL com uma réplica primária e duas réplicas de leitura gerenciadas [pelo operador CloudNativePG (CNPG).](https://cloudnative-pg.io/) A arquitetura fornece um PostgreSQL altamente disponível em execução em um cluster AKS que pode resistir a uma interrupção de zona fazendo failover em réplicas.

Os backups são armazenados no [Armazenamento](/azure/storage/blobs/) de Blobs do Azure, fornecendo outra maneira de restaurar o banco de dados no caso de um problema com a replicação de streaming da réplica primária.

:::image source="./media/postgresql-ha-overview/architecture-diagram.png" alt-text="Diagrama da arquitetura CNPG." lightbox="./media/postgresql-ha-overview/architecture-diagram.png":::

> [!NOTE]
> O operador CNPG suporta apenas *um banco de dados por cluster*. Planeje de acordo com os aplicativos que exigem separação de dados no nível do banco de dados.

## Próximos passos

> [!div class="nextstepaction"]
> [Criar a infraestrutura para implantar um banco de dados PostgreSQL altamente disponível no AKS usando o operador CNPG][create-infrastructure]

## Contribuidores

*Este artigo é mantido pela Microsoft. Foi originalmente escrito pelos seguintes contribuidores*:

* Ken Kilty - Brasil | Principal TPM
* Russell de Pina - Brasil | Principal TPM
* Adrian Joian - Brasil | Engenheiro de Clientes Sênior
* Jenny Hayes - Brasil | Desenvolvedor de Conteúdo Sênior
* Carol Smith - Brasil | Desenvolvedor de Conteúdo Sênior
* Erin Schaffer - Brasil | Desenvolvedor de Conteúdo 2
* Adam Sharif - Brasil | Engenheiro de Clientes 2

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
