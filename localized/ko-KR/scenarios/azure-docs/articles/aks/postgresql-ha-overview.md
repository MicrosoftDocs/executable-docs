---
title: Azure CLI를 사용하여 AKS에 고가용성 PostgreSQL 데이터베이스 배포 개요
description: CloudNativePG 연산자를 사용하여 AKS에 고가용성 PostgreSQL 데이터베이스를 배포하는 방법을 알아봅니다.
ms.topic: overview
ms.date: 07/24/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---
# Azure CLI를 사용하여 AKS에 고가용성 PostgreSQL 데이터베이스 배포

이 가이드에서는 Azure CLI를 사용하여 AKS의 여러 Azure 가용성 영역에 걸쳐 있는 고가용성 PostgreSQL 클러스터를 배포합니다.

이 문서에서는 [AKS(Azure Kubernetes Service)][what-is-aks]에서 PostgreSQL 클러스터를 설정하기 위한 필수 구성 요소를 살펴보고 전체 배포 프로세스 및 아키텍처에 대한 개요를 제공합니다.

## 필수 조건

* 이 가이드에서는 [핵심 Kubernetes 개념][core-kubernetes-concepts] 및 [PostgreSQL][postgresql]에 대한 기본적인 이해를 가정합니다.
* Azure 계정의 구독에 **소유자** 또는 **사용자 액세스 관리자** 및 **기여자** [Azure 기본 제공 역할][azure-roles]이 필요합니다.

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

* 또한 다음 리소스가 설치되어 있어야 합니다.

  * [Azure CLI](/cli/azure/install-azure-cli), 버전 2.56 이상
  * [AKS(Azure Kubernetes Service) 미리 보기 확장][aks-preview].
  * [jq][jq], 버전 1.5 이상.
  * [kubectl][install-kubectl] 버전 1.21.0 이상.
  * [Helm][install-helm] 버전 3.0.0 이상.
  * [openssl][install-openssl] 버전 3.3.0 이상.
  * [Visual Studio Code][install-vscode] 또는 이와 동등한 것.
  * [Krew][install-krew] 버전 0.4.4 이상.
  * [kubectl CloudNativePG(CNPG) 플러그인][cnpg-plugin].

## 배포 프로세스

이 가이드에서는 다음 작업 방법을 배웁니다.

* Azure CLI를 사용하여 다중 영역 AKS 클러스터를 만듭니다.
* [CNPG 연산자][cnpg-plugin]를 사용하여 고가용성 PostgreSQL 클러스터 및 데이터베이스를 배포합니다.
* Prometheus 및 Grafana를 사용하여 PostgreSQL에 대한 모니터링을 설정합니다.
* PostgreSQL 데이터베이스에 샘플 데이터 세트를 배포합니다.
* PostgreSQL 및 AKS 클러스터 업그레이드를 수행합니다.
* 클러스터 중단 및 PostgreSQL 복제본 장애 조치(failover)를 시뮬레이션합니다.
* PostgreSQL 데이터베이스의 백업 및 복원을 수행합니다.

## 배포 아키텍처

이 다이어그램에서는 [CNPG(CloudNativePG)](https://cloudnative-pg.io/) 연산자가 관리하는 주 복제본 1개와 읽기 복제본 2개와 함께 PostgreSQL 클러스터 설정을 보여 줍니다. 아키텍처는 AKS 클러스터에서 실행되는 고가용성 PostgreSQL을 제공하여 복제본 간에 장애 조치(failover)를 통해 영역 중단을 견딜 수 있습니다.

백업은 [Azure Blob Storage](/azure/storage/blobs/)에 저장되며 주 복제본에서 스트리밍 복제와 관련된 문제가 발생할 경우 데이터베이스를 복원하는 또 다른 방법을 제공합니다.

:::image source="./media/postgresql-ha-overview/architecture-diagram.png" alt-text="CNPG 아키텍처 다이어그램" lightbox="./media/postgresql-ha-overview/architecture-diagram.png":::

> [!NOTE]
> CNPG 연산자는 *클러스터당 하나의 데이터베이스*만 지원합니다. 데이터베이스 수준에서 데이터를 분리해야 하는 애플리케이션에 대해 적절하게 계획합니다.

## 다음 단계

> [!div class="nextstepaction"]
> [CNPG 연산자를 사용하여 AKS에 고가용성 PostgreSQL 데이터베이스를 배포하는 인프라 만들기][create-infrastructure]

## 참가자

*이 문서는 Microsoft에서 유지 관리합니다. 원래 다음 기여자가 작성했습니다.*

* Ken Kilty | 수석 TPM
* Russell de Pina | 수석 TPM
* Adrian Joian | 선임 고객 엔지니어
* Jenny Hayes | 선임 콘텐츠 개발자
* Carol Smith | 선임 콘텐츠 개발자
* Erin Schaffer | 콘텐츠 개발자 2
* Adam Sharif | 고객 엔지니어 2

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
