# Data Master — Forja
![Arquitetura](docs/arquitetura.png)

<p align="center">
  Terraform • Azure • Databricks • Unity Catalog • Airflow • PostgreSQL • Docker
</p>

---

## Sumário

1. [Objetivo do Case](#objetivo-do-case)

   * [Início Rápido](#início-rápido)
2. [Arquitetura da Solução](#arquitetura-da-solução)

   * [Visão Geral](#visão-geral)
   * [Fluxo de Dados](#fluxo-de-dados)
   * [Tecnologias](#tecnologias)
3. [Arquitetura Técnica](#arquitetura-técnica)

   * [Infraestrutura Provisionada](#infraestrutura-provisionada)
   * [Criação e Inserção de Dados](#criação-e-inserção-de-dados)
   * [Processamento](#processamento)
4. [Provisionamento (Terraform)](#provisionamento-terraform)

   * [Pré-requisitos](#pré-requisitos)
   * [Ordem de Criação](#ordem-de-criação)
   * [Exemplos de Código](#exemplos-de-código)
5. [Orquestração e Monitoramento (Airflow)](#orquestração-e-monitoramento-airflow)
6. [Transformações (Databricks)](#transformações-databricks)
7. [Governança e Segurança (Unity Catalog)](#governança-e-segurança-unity-catalog)
8. [Execução do Projeto (Passo a Passo)](#execução-do-projeto-passo-a-passo)
9. [Estrutura de Repositório](#estrutura-de-repositório)
10. [Operação & Custos](#operação--custos)
11. [Troubleshooting](#troubleshooting)
12. [Critérios de Pronto (DoD)](#critérios-de-pronto-dod)
13. [Melhorias Futuras](#melhorias-futuras)

---

## Objetivo do Case

Assim como uma **forja** transforma metal bruto em artefatos valiosos, este projeto transforma **dados brutos** em **ativos analíticos** governados e confiáveis. A proposta é implementar uma arquitetura completa de **ingestão → transformação → entrega**, com rastreabilidade e segurança ponta a ponta.

### Início Rápido

Para executar tudo localmente (provisionamento + orquestração):

```bash
./main/init.sh
```

> **Obs.**: O script inicializa serviços e dependências automaticamente (Terraform, containers do Astronomer/Airflow etc.).

---

## Arquitetura da Solução

### Visão Geral

* **Armazenamento** em **Azure Data Lake** estruturado no padrão **Medallion** (Raw → Bronze → Silver → Gold).
* **Processamento** com **Azure Databricks** (Apache Spark + Delta Lake).
* **Governança** com **Unity Catalog** (metastore, lineage, permissões e external locations).
* **Orquestração e Monitoramento** com **Apache Airflow** (via **Astronomer**).
* **Provisionamento** e reprodutibilidade via **Terraform**.

### Fluxo de Dados

1. **Ingestão**

   * **Fonte**: PostgreSQL (exemplos com DDL/DML automáticos).
   * **Destino**: Camada **Raw** no Data Lake.
2. **Armazenamento em Camadas**

   * **Bronze**: dados brutos padronizados.
   * **Silver**: dados limpos, *dedup*, enriquecidos.
   * **Gold**: dados prontos para consumo analítico (ex.: *marts*, **Smart Tables** quando aplicável).
3. **Processamento**

   * Notebooks/Jobs do Databricks orquestrados pelo Airflow.
4. **Orquestração**

   * DAGs com agendamentos, *retries* e logs centralizados.
5. **Entrega**

   * Tabelas Delta publicadas no **Unity Catalog** para acesso por BI/SQL/Notebooks.
6. **Governança e Segurança**

   * RBAC com Azure AD, segredos no Key Vault, lineage e auditoria no UC.

### Tecnologias

* **Azure**: Resource Groups, Storage (ADLS Gen2), Key Vault, Azure AD (SPN).
* **Databricks**: Workspace, Jobs/Workflows, Cluster Policies, Unity Catalog.
* **Airflow** (Astronomer), **PostgreSQL**, **Terraform**, **Docker**.

---

## Arquitetura Técnica

### Infraestrutura Provisionada

* **Resource Group** e **Storage Account** (HNS) com containers: `raw`, `bronze`, `silver`, `gold`.
* **App Registration (SPN)** com **credenciais no Key Vault**.
* **Databricks Workspace** com **Cluster Policy** e (opcional) **Access Connector**.
* **Unity Catalog**: storage credential, external locations, catálogo/esquemas e **grants**.

### Criação e Inserção de Dados

* **Classe DDL**: cria tabelas no PostgreSQL automaticamente.
* **Classe DML**: insere dados a partir de arquivos **JSON**.
* **Airflow Operator**: orquestra as operações de DDL/DML e a ingestão para o Data Lake.

### Processamento

* **ExtractDbSaveToAzure**: extrai do PostgreSQL e persiste no **Raw**.
* **Pipeline Databricks**: **Raw → Bronze → Silver → Gold**, acionado por DAG no Airflow.

---

## Provisionamento (Terraform)

### Pré-requisitos

* **Azure CLI**, **Terraform ≥ 1.5**, **Docker**, **Astronomer CLI**, **Python 3**, **Git**.
* Assinatura Azure com permissão para RG/Storage/Key Vault/Databricks/RBAC.
* **State remoto** (Azure Storage) configurado.
* Providers: `azurerm`, `azuread`, `databricks`.
* **SPN** com role **Storage Blob Data Contributor** no escopo adequado.

### Ordem de Criação

1. **Resource Group**
2. **Storage Account** (HNS) + containers `raw/bronze/silver/gold`
3. **Key Vault**
4. **App Registration (SPN)** + senha no **Key Vault**
5. **Role Assignments** para o SPN (Storage/Key Vault)
6. **Databricks Workspace** (+ **Access Connector**, se aplicável)
7. **Unity Catalog**: storage credential → external locations → catalog → schemas → grants
8. **Cluster Policy / Notebooks / Jobs (Workflows)**

---

## Orquestração e Monitoramento (Airflow)

* **DAGs** principais:

  * `extract_from_source` (PythonOperator) → grava em `raw/`.
  * `ingest_control` (PythonOperator) → valida partições/headers e aciona Databricks.
  * `bronze`, `silver`, `gold` (DatabricksWorkflowsTaskGroup ou DatabricksSubmitRunOperator).
  * `cleanup` (PythonOperator) → remove temporários/antigos.
* **Boas práticas**: `retries`, `retry_delay`, `max_active_runs`, parametrização por `{{ ds }}`.
* **Conexões**: `DATABRICKS_HOST` + `POSTGRES_CONN` (Secret/Env). Com UC Volumes, preferir identidade gerenciada.
* **Observabilidade**: Airflow UI (logs, reexecução), métricas e alertas.
* **Gráficos recomendados**: execuções por status, duração das tarefas, taxa sucesso/erro, *SLA misses*.

---

## Transformações (Databricks)

* **Bronze**: leitura bruta, correção de tipos, persistência Delta (`overwriteSchema=true` apenas aqui).
* **Silver**: conformidade de chaves, *dedup*, regras de qualidade e *joins*.
* **Gold**: agregações e modelagem (dim/fact ou *wide tables*); `OPTIMIZE` + `VACUUM` agendados.
* **Naming**: `catalog.schema.tabela` (ex.: `main.bronze.clientes` → `main.gold.fato_vendas`).

---

## Governança e Segurança (Unity Catalog)

* **Storage Credential** com identidade gerenciada ou SPN.
* **External Locations** para `raw/bronze/silver/gold` (`abfss://`).
* **Catálogo/Esquemas**: isolar camadas e aplicar **grants** por grupo/perfil.
* **Lineage/Auditoria**: use o UC para rastreabilidade e logs de acesso.

---

### Validar e executar DAGs

* **DAG** `extract-load-transform`: PostgreSQL → Raw → Bronze → Silver → Gold.

---

---

## Operação & Custos

* **Job clusters** com **autotermination** (10–15 min).
* Allowlist de `node_type_id` e tamanhos econômicos.
* Alertas de **quota** (cores/VM) e **falhas**.

---

## Troubleshooting

* **INSUFFICIENT\_PERMISSIONS / SELECT on any file**

  * Verifique grants no **External Location** e roles do SPN no Storage.
  * Garanta leitura via **UC** (tabelas) ou configs OAuth corretas.
* **cannot read/create external location / MANAGE no Storage Credential**

  * O aplicador precisa de `MANAGE` no credential e permissões no catálogo.
* **Quota/VM não disponível**

  * Ajuste `node_type_id` via policy ou solicite aumento de cores/região.
* **Key Vault Secret já existe**

  * Use `terraform import` com **ID versionado** do segredo.

---

## Critérios de Pronto (DoD)

* Infra via Terraform aplicada sem *drift*.
* UC configurado (credential, locations, catalog/schemas, grants).
* DAG executa `extract → bronze → silver → gold → cleanup` com logs e *retries*.
* Tabelas Delta acessíveis com permissões corretas.
* Custos sob controle (autotermination e tamanhos aprovados).

---

## Melhorias Futuras

* **Airflow em Kubernetes** (Helm Chart oficial, KubernetesExecutor/CeleryK8s, autoscaling com KEDA, Secrets/Configs no cluster e observabilidade nativa). Indicado para produção multiambiente e maior resiliência.
* **Ingestão em tempo real** com Kafka/Event Hubs (streaming) complementando batch.
* **Testes & CI/CD** com GitHub Actions para IaC e código.
* **Alertas proativos** (e-mail/Slack) e políticas de *retry/backoff*.
* **Data Quality** (Great Expectations/Delta Live Tables) e **observabilidade** (OpenLineage/Marquez).
* **Catalogação avançada** no Unity Catalog (tags sensíveis, lineage).