# Provisionamento de Infraestrutura com Terraform para Azure + Databricks + Unity Catalog

Este repositório define toda a infraestrutura necessária para provisionar um ambiente completo no Azure com integração ao Databricks e Unity Catalog, utilizando Terraform.

## Visão Geral dos Recursos

Este projeto provisiona:

- Grupo de Recursos no Azure
- Storage Account com containers (bronze, silver, gold)
- Azure AD Application + Service Principal com senha
- Key Vault para armazenar a senha do SPN
- Role Assignments para acesso à Storage
- Workspace do Databricks (SKU Premium)
- Access Connector para o Databricks
- SPN registrado no Databricks (`databricks_service_principal`)
- Secret Scope no Databricks apontando para a senha do Key Vault
- Cluster com política Unity Catalog
- Notebooks para bronze, silver e gold
- Schemas no Unity Catalog

## Pré-requisitos

- Conta Azure com permissões para criar recursos (Resource Group, Storage, AD, Databricks)
- [Terraform](https://developer.hashicorp.com/terraform/downloads) >= 1.3
- `az login` feito com usuário com permissões de Owner

## Estrutura

```bash
infra/
├── providers.tf
├── main.tf
├── databricks.tf
├── variables.tf
├── terraform.tfvars
├── outputs.tf
├── notebooks/
```

## Comandos

1. Inicialize o Terraform:

```bash
terraform init
```

2. Valide:

```bash
terraform validate
```

3. Veja o plano:

```bash
terraform plan -out=tfplan
```

4. Aplique:

```bash
terraform apply tfplan
```

> Após a execução, o ambiente estará provisionado com todas as dependências configuradas.

## Autenticação

O provedor do Databricks usa `azure_workspace_resource_id` e `host`, com autenticação via identidade do Terraform (sem token manual).

```hcl
provider "databricks" {
  host                        = azurerm_databricks_workspace.main.workspace_url
  azure_workspace_resource_id = azurerm_databricks_workspace.main.id
}
```

## Segurança

- O segredo da SPN é armazenado no Key Vault
- O Databricks acessa o segredo via `databricks_secret`
- O `spark_conf` usa:

```hcl
"{{secrets/<scope>/<key>}}"
```

## Observações

- A política de cluster ativa o Unity Catalog (`USER_ISOLATION`)
- O Unity Catalog exige que o SPN ou usuário seja registrado como `account admin` para algumas ações

## Próximos passos

- Habilitar pipeline CI/CD com GitHub Actions
- Automatizar deploy de dados fictícios
- Criar monitoramento com Azure Monitor e Unity Catalog Audit Logs

## Autor

Duque - Engenheiro de Dados ✨

---