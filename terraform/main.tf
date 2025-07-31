data "azurerm_client_config" "current" {}
data "azuread_client_config" "current" {}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
}

# Storage Account (Data Lake Gen2)
resource "azurerm_storage_account" "data_lake" {
  name                     = var.storage_account_name
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  is_hns_enabled           = true

  tags = {
    environment = var.environment
  }
}

# Storage Containers (ex: raw, bronze, silver, gold)
resource "azurerm_storage_container" "data_lake_containers" {
  for_each              = toset(var.container_names)
  name                  = each.value
  storage_account_name  = azurerm_storage_account.data_lake.name
  container_access_type = "private"

  depends_on = [azurerm_storage_account.data_lake]
}

# Service Principal (Application + SPN + Password)
resource "azuread_application" "main" {
  display_name = var.spn_display_name
  owners       = [data.azurerm_client_config.current.object_id]
}

resource "azuread_service_principal" "main" {
  client_id = azuread_application.main.client_id
  owners    = [data.azurerm_client_config.current.object_id]
}

resource "azuread_service_principal_password" "main" {
  service_principal_id = azuread_service_principal.main.id
}

resource "azurerm_role_assignment" "spn_blob_data_access" {
  scope                = azurerm_storage_account.data_lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azuread_service_principal.main.object_id
}

# Key Vault com permissões para SPN e usuário atual
resource "azurerm_key_vault" "main" {
  name                = var.key_vault_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  access_policy {
    tenant_id          = data.azuread_client_config.current.tenant_id
    object_id          = azuread_service_principal.main.object_id
    secret_permissions = ["Get", "List"]
  }

  access_policy {
    tenant_id          = data.azuread_client_config.current.tenant_id
    object_id          = data.azuread_client_config.current.object_id
    secret_permissions = ["Get", "List", "Set", "Delete", "Purge", "Recover"]
    key_permissions    = ["Create", "Get", "List"]
  }
}

# Armazenar a senha do SPN no Key Vault
resource "azurerm_key_vault_secret" "spn_password" {
  name         = var.spn_display_name
  value        = azuread_service_principal_password.main.value
  key_vault_id = azurerm_key_vault.main.id
}

# Role assignment para o managed identity do Databricks (se aplicável)
resource "azurerm_role_assignment" "blob_contrib_mi" {
  scope                = azurerm_storage_account.data_lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_databricks_access_connector.main.identity[0].principal_id
}