output "resource_group_name" {
  description = "Name of the resource group."
  value       = azurerm_resource_group.main.name
}

output "storage_account_name" {
  description = "Name of the Data Lake Storage Account."
  value       = azurerm_storage_account.data_lake.name
}

output "azure_connection_string" {
  description = "Azure Connection String"
  value = "DefaultEndpointsProtocol=https;AccountName=${azurerm_storage_account.data_lake.name};AccountKey=${azurerm_storage_account.data_lake.primary_access_key};EndpointSuffix=core.windows.net"
  sensitive = true
}

output "key_vault_uri" {
  description = "URI of the Key Vault."
  value       = azurerm_key_vault.main.vault_uri
}

output "service_principal_client_id" {
  description = "Azure AD Service Principal Client ID (Application ID)."
  value       = azuread_application.main.client_id
}

output "service_principal_tenant_id" {
  description = "Azure AD Service Principal Tenant Id."
  value       = data.azurerm_client_config.current.tenant_id
}

output "service_principal_name" {
  description = "Azure AD Service Principal Name"
  value = azuread_application.main.display_name
}

output "service_principal_password" {
  description = "Azure AD Service Principal passaword. <terraform output -json service_principal_password>"
  value       = azuread_service_principal_password.main.value
  sensitive = true
}

output "service_principal_object_id" {
  description = "Object ID do Service Principal criado."
  value       = azuread_service_principal.main.object_id
}

output "databricks_workspace_url" {
  description = "URL do Databricks Workspace."
  value       = azurerm_databricks_workspace.main.workspace_url
}

output "databricks_workspace_name" {
  description = "URL do Databricks Workspace."
  value       = azurerm_databricks_workspace.main.name
}

output "databricks_workspace_id" {
  description = "ID do Databricks Workspace."
  value       = azurerm_databricks_workspace.main.workspace_id
}

output "databricks_secret_scope" {
  description = "Nome da Secret Scope"
  value = databricks_secret_scope.app.name
}

output "databricks_secret" {
  description = "Nome da Secret Databricks"
  value = databricks_secret.publishing_api.key
}

output "cluster_policy" {
  description = "Id do Cluster Policy"
  value = databricks_cluster_policy.uc_policy.id
}

# output "cluster_id" {
#   description = "Id do cluster"
#   value = databricks_cluster.main.id
# }

# output "cluster_key" {
#   value = databricks_cluster.main.cluster_name
# }

# output "databricks_group_name" {
#   description = "Nome do Grupo Databricks"
#   value = databricks_group.data_analysts_group.display_name
# }

output "databricks_token_value" {
  description = "Token para automação"
  value     = databricks_token.my_automation_token.token_value
  sensitive = true
}

output "path_notebooks_bronze" {
  description = "Notebook Path Bronze"
  value = databricks_notebook.bronze_main.path  
}

output "path_notebooks_silver" {
  description = "Notebook Path Silver"
  value = databricks_notebook.silver_main.path  
}

output "path_notebooks_gold" {
  description = "Notebook Path Gold"
  value = databricks_notebook.gold_main.path  
}