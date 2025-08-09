# Data Master — Infra Azure + Databricks (Terraform)

Provisionamento de um ambiente **Azure + Databricks** com **governança via Unity Catalog**, **segredos no Key Vault**, **SPN para automação**, **Access Connector** e **estruturas base do lago de dados (raw/bronze/silver/gold)** — tudo com Terraform.

<p align="center">
  Azure • Databricks • Unity Catalog • Key Vault • Azure AD • Terraform
</p>

---

## Sumário
  
1. [Recursos Provisionados](#recursos-provisionados)  
2. [Pré‑requisitos](#pré-requisitos)  
3. [Variáveis](#variáveis)  
4. [Como executar](#como-executar)  
5. [Estrutura de diretórios (sugerida)](#estrutura-de-diretórios-sugerida)  
6. [Uso no Databricks](#uso-no-databricks)  
7. [Dicas e Troubleshooting](#dicas-e-troubleshooting)  
8. [Limpeza](#limpeza)

---

### Componentes
- **Resource Group + Storage Account HNS** com contêineres `raw/bronze/silver/gold` (privados).
- **Azure AD Application + Service Principal (SPN)** com senha armazenada no **Key Vault**.
- **Databricks Workspace (Premium)** e **Access Connector** (identidade gerenciada) com permissão no Storage.
- **Unity Catalog (pronto para)** uso com:
  - **Storage Credential** (via Access Connector).
  - **External Locations** para cada camada.
  - **Schemas** `raw/bronze/silver/gold` no **catálogo = nome do workspace**.
  - **Grants** para SPN e grupo de usuários.
- **Secret Scope** no Databricks e secret com a senha da SPN.
- **Grupo** `data-analysts-group`, **Cluster Policy** “Unity Catalog”.
- **Notebooks** (bronze/silver/gold) publicados no workspace do usuário informado.

> Observação: este código assume que o **metastore do Unity Catalog já existe e está associado ao workspace** (mesma região). O Terraform aqui prepara credenciais/locais/schemas/grants.

---

## Recursos Provisionados

- `azurerm_resource_group.main`
- `azurerm_storage_account.data_lake` + `azurerm_storage_container.data_lake_containers` (para `raw/bronze/silver/gold`)
- `azuread_application.main`, `azuread_service_principal.main`, `azuread_service_principal_password.main`
- `azurerm_role_assignment.*` (SPN no Storage e no Workspace; Access Connector no Storage)
- `azurerm_key_vault.main` + `azurerm_key_vault_secret.spn_password`
- `azurerm_databricks_workspace.main`
- `azurerm_databricks_access_connector.main`
- `databricks_service_principal.main` (mapeia a aplicação AAD no workspace)
- `databricks_secret_scope.app` + `databricks_secret.publishing_api` + `databricks_secret_acl.spn_read_secret`
- `databricks_group.data_analysts_group`
- `databricks_cluster_policy.uc_policy` + `databricks_permissions.uc_policy_can_use`
- `databricks_notebook.*` (bronze/silver/gold e utils)
- `databricks_storage_credential.uc_credential`
- `databricks_external_location.medallion_locations` (raw/bronze/silver/gold)
- `databricks_schema.medallion_schemas` (no catálogo = nome do workspace)
- Grants:
  - `databricks_grants.analysts_usage`
  - `databricks_grants.spn_extloc_read`
  - `databricks_grants.spn_catalog_use`
  - `databricks_grants.spn_schema_use`

---

## Pré‑requisitos

- **Terraform >= 1.3.0**
- Permissões para:
  - Criar **Resource Group**, **Storage**, **Key Vault**, **Databricks Workspace** e **Access Connector** na assinatura Azure.
  - Criar **Application/Service Principal** no **Azure AD**.
  - Associar o **Workspace** a um **Metastore** do Unity Catalog (feito uma vez no nível da conta Databricks).
- Providers:
  - `azurerm >= 3.0.0`
  - `azuread >= 2.0.0`
  - `databricks >= 1.49.0`
  - `time ~> 0.9`

---

## Variáveis

| Variável                    | Tipo           | Exemplo/Descrição                                                                 |
|----------------------------|----------------|-----------------------------------------------------------------------------------|
| `resource_group_name`      | string         | Nome do Resource Group.                                                           |
| `location`                 | string         | Região Azure (ex.: `brazilsouth`).                                               |
| `storage_account_name`     | string         | Nome *global único* do Storage (HNS ativado).                                     |
| `environment`              | string         | Ex.: `dev`, `prd` (usado em tags e nomes).                                        |
| `container_names`          | list(string)   | Ex.: `["raw","bronze","silver","gold"]`.                                          |
| `spn_display_name`         | string         | Nome de exibição da aplicação/SPN.                                                |
| `key_vault_name`           | string         | Nome do Key Vault.                                                                |
| `databricks_workspace`     | string         | **Nome do workspace** (também usado como **catálogo UC**).                        |
| `prefix`                   | string         | Prefixo para o Access Connector (ex.: `dm`).                                      |
| `databricks_user`          | string         | Usuário do workspace (email) que será owner de recursos/notebooks.                |

> Dica: mantenha `locals.medallion_layers = ["raw","bronze","silver","gold"]` alinhado com `var.container_names`.

---

## Como executar

1. **Autentique-se** no Azure CLI (ou configure SPN para o Terraform):
   ```bash
   az login
   az account set --subscription "<SUBSCRIPTION_ID>"
   ```

2. **Configuração das variáveis** (ex.: `terraform.tfvars`):
   ```hcl
   resource_group_name   = "rg-br-datamaster"
   location              = "brazilsouth"
   storage_account_name  = "stgbrdatalake"
   environment           = "dev"
   container_names       = ["raw","bronze","silver","gold"]
   spn_display_name      = "spn-datamaster-access"
   key_vault_name        = "kvsecretsdb"
   databricks_workspace  = "datamasterbr"
   prefix                = "dm"
   databricks_user       = "seu.usuario@empresa.com"
   ```

3. **Inicialização & plano**:
   ```bash
   terraform init
   terraform fmt -check
   terraform validate
   terraform plan -out tfplan
   ```

4. **Aplicar**:
   ```bash
   terraform apply tfplan
   ```

> Após o `apply`, confirme no **Admin Console (Account)** do Databricks se o **workspace está associado ao Metastore** certo. Esse passo é fora do escopo deste Terraform.

---

## Estrutura de diretórios (sugerida)

```
.
├─ main.tf / providers.tf / databricks.tf / databricks_notebooks.tf / databricks_grants.tf / variables.tf / outputs.tf
├─ terraform.tfvars
└─ notebooks/
   ├─ bronze/
   │  ├─ main.py
   │  └─ utils/commons.py
   ├─ silver/
   │  ├─ main.py
   │  └─ utils/commons.py
   └─ gold/
      ├─ main.py
      └─ utils/commons.py
```

> Os caminhos publicados no workspace seguem:  
> `/Workspace/Users/<databricks_user>/<layer>/[main|utils/commons.py]`.

---

## Uso no Databricks

- **Catálogo**: igual ao valor de `var.databricks_workspace` (ex.: `datamasterbr`).
- **Schemas**: `raw`, `bronze`, `silver`, `gold`.
- **External Locations**: apontam para `abfss://<layer>@<storage>.dfs.core.windows.net/`.
- **Cluster Policy**: `unity-catalog-policy` (modo `USER_ISOLATION`, versões e tipos de nó permitidos, `autotermination` 10–30 min).
- **Grupo**: `data-analysts-group` com `USE_CATALOG`/`USE_SCHEMA` apropriados.
- **SPN**: possui `ALL PRIVILEGES` no catálogo/schemas e nos external locations; secret lida via `databricks_secret_scope.app`.

---

## Dicas e Troubleshooting

- **Metastore UC**: se o workspace não estiver associado, você verá erros como _“User does not have any non-BROWSE privileges on External Location …”_ ou falhas ao criar schemas. Associe o workspace ao metastore correto na **conta** do Databricks.
- **Permissões no Storage**:
  - O **Access Connector** recebe `Storage Blob Data Contributor` no **Storage Account**.
  - A **SPN** também recebe `Storage Blob Data Contributor` (escopo do account e containers).
- **Key Vault Secret existente**: se já existir a versão do secret, você pode precisar **importar para o state** antes do `apply`:
  ```bash
  terraform import azurerm_key_vault_secret.spn_password   "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.KeyVault/vaults/<kv>/secrets/<secretName>/<version>"
  ```
- **Nomes globais**: `storage_account_name` deve ser único globalmente. Conflitos causam erro de criação.
- **Quotas/VM Size**: erros de cota ou tamanho indisponível ao subir clusters são do **pool de máquinas** da região/assinatura; ajuste `node_type_id` permitido na **policy** ou solicite quota.
- **Grants e Identities**: os grants usam `azuread_application.main.client_id` (App ID) como principal no Databricks. Garanta que a **aplicação foi mapeada** via `databricks_service_principal.main`.

---

## Limpeza

Para destruir todos os recursos criados por este módulo (cuidado!):

```bash
terraform destroy
```

> Confirme antes de destruir em ambientes compartilhados.

## Autor

José Duque - Engenheiro de Dados ✨