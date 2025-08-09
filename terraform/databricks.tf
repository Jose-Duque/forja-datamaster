# Cria o workspace Databricks na Azure
resource "azurerm_databricks_workspace" "main" {
  name                = var.databricks_workspace
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "premium"
}

# Concede ao SPN a função de Contributor no workspace Databricks
resource "azurerm_role_assignment" "spn_databricks_contributor" {
  principal_id         = azuread_service_principal.main.object_id
  role_definition_name = "Contributor"
  scope                = azurerm_databricks_workspace.main.id
}

# Cria o Access Connector para autenticação gerenciada no Unity Catalog
resource "azurerm_databricks_access_connector" "main" {
  name                = "ac-${var.prefix}-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  identity {
    type = "SystemAssigned"
  }
}

# Concede ao Access Connector permissão de acesso ao Data Lake
resource "azurerm_role_assignment" "connector_blob_contrib" {
  scope                = azurerm_storage_account.data_lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_databricks_access_connector.main.identity[0].principal_id
}

# Cria o Service Principal dentro do Databricks
resource "databricks_service_principal" "main" {
  display_name             = azuread_application.main.display_name
  application_id           = azuread_application.main.client_id
  allow_cluster_create      = true
  databricks_sql_access     = true
  allow_instance_pool_create = true
  depends_on               = [azurerm_databricks_workspace.main]
}

# Cria um Secret Scope no Databricks
resource "databricks_secret_scope" "app" {
  name = "application-secret-scope"
}

# Cria um segredo no Databricks usando senha do SPN
resource "databricks_secret" "publishing_api" {
  key          = "publishing_api"
  string_value = azurerm_key_vault_secret.spn_password.value
  scope        = databricks_secret_scope.app.id
}

# Concede ao SPN permissão para ler o segredo
resource "databricks_secret_acl" "spn_read_secret" {
  scope      = databricks_secret_scope.app.name
  principal  = azuread_application.main.client_id
  permission = "READ"
}

# Cria grupo de usuários no Databricks
resource "databricks_group" "data_analysts_group" {
  display_name             = "data-analysts-group"
  allow_cluster_create     = true
  allow_instance_pool_create = true
  databricks_sql_access    = true
  workspace_access         = true
}

# Define política de cluster para uso com Unity Catalog
resource "databricks_cluster_policy" "uc_policy" {
  name = "unity-catalog-policy"
  definition = jsonencode({
    data_security_mode       = { type = "fixed", value = "USER_ISOLATION" }
    spark_version            = { type = "fixed", value = "13.3.x-scala2.12" }
    node_type_id              = { type = "allowlist", values = ["Standard_DS3_v2", "Standard_DS4_v2", "Standard_F4"] }
    num_workers               = { type = "range", minValue = 1, maxValue = 5 }
    autotermination_minutes   = { type = "range", minValue = 10, maxValue = 30 }
  })
  depends_on = [azurerm_databricks_workspace.main]
}

# Concede ao SPN permissão para usar a política de cluster
resource "databricks_permissions" "uc_policy_can_use" {
  cluster_policy_id = databricks_cluster_policy.uc_policy.id
  access_control {
    service_principal_name = azuread_application.main.client_id
    permission_level       = "CAN_USE"
  }
}

# Lista das camadas da arquitetura Medallion
locals {
  medallion_layers = ["raw", "bronze", "silver", "gold"]
}

# Cria credencial de armazenamento para Unity Catalog usando o Access Connector
resource "databricks_storage_credential" "uc_credential" {
  name = "uc-storage-credential-azure"
  azure_managed_identity {
    access_connector_id = azurerm_databricks_access_connector.main.id
  }
  comment = "Credencial para acesso ao Data Lake pelo Unity Catalog"
  owner   = var.databricks_user
  depends_on = [azurerm_role_assignment.connector_blob_contrib]
}

# Cria External Locations para cada camada do Data Lake
resource "databricks_external_location" "medallion_locations" {
  for_each         = toset(local.medallion_layers)
  name             = "${each.key}-external-location"
  url              = "abfss://${each.key}@${azurerm_storage_account.data_lake.name}.dfs.core.windows.net/"
  credential_name  = databricks_storage_credential.uc_credential.id
  comment          = "External location for the ${each.key} layer."
  owner            = var.databricks_user
}

# Cria Schemas no Unity Catalog para cada camada do Data Lake
resource "databricks_schema" "medallion_schemas" {
  for_each      = toset(local.medallion_layers)
  catalog_name  = var.databricks_workspace
  name          = each.key
  comment       = "Schema para a camada ${each.key}."
  owner         = var.databricks_user
}