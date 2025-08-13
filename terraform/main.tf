# Obtém informações do cliente autenticado na Azure (ID, Tenant, etc.)
data "azurerm_client_config" "current" {}

# Obtém informações do cliente autenticado no Azure AD
data "azuread_client_config" "current" {}

# Cria o Resource Group principal
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
}

# Cria a Storage Account habilitada para Data Lake Gen2
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

# Cria os containers do Data Lake (Bronze, Silver, Gold, etc.)
resource "azurerm_storage_container" "data_lake_containers" {
  for_each              = toset(var.container_names)
  name                  = each.value
  storage_account_name  = azurerm_storage_account.data_lake.name
  container_access_type = "private"

  depends_on = [azurerm_storage_account.data_lake]
}

# Cria a aplicação (SPN) no Azure AD
resource "azuread_application" "main" {
  display_name = var.spn_display_name
  owners       = [data.azurerm_client_config.current.object_id]
}

# Cria o Service Principal vinculado à aplicação
resource "azuread_service_principal" "main" {
  client_id = azuread_application.main.client_id
  owners    = [data.azurerm_client_config.current.object_id]
}

# Cria a senha para o Service Principal
resource "azuread_service_principal_password" "main" {
  service_principal_id = azuread_service_principal.main.id
}

# Concede ao SPN acesso de contribuinte no nível da Storage Account
resource "azurerm_role_assignment" "spn_blob_data_access" {
  scope                = azurerm_storage_account.data_lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azuread_service_principal.main.object_id
}

# Concede ao SPN acesso de contribuinte em cada container do Data Lake
resource "azurerm_role_assignment" "spn_blob_contrib_containers" {
  for_each = toset(local.medallion_layers)

  principal_id         = azuread_service_principal.main.object_id
  role_definition_name = "Storage Blob Data Contributor"

  scope = "${azurerm_storage_account.data_lake.id}/blobServices/default/containers/${each.value}"
}

# Cria o Key Vault para armazenar segredos
resource "azurerm_key_vault" "main" {
  name                = var.key_vault_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  # Permite que o SPN acesse segredos
  access_policy {
    tenant_id          = data.azuread_client_config.current.tenant_id
    object_id          = azuread_service_principal.main.object_id
    secret_permissions = ["Get", "List"]
  }

  # Permite que o usuário atual gerencie segredos e chaves
  access_policy {
    tenant_id          = data.azuread_client_config.current.tenant_id
    object_id          = data.azuread_client_config.current.object_id
    secret_permissions = ["Get", "List", "Set", "Delete", "Purge", "Recover"]
    key_permissions    = ["Create", "Get", "List"]
  }
}

# Armazena a senha do SPN no Key Vault
resource "azurerm_key_vault_secret" "spn_password" {
  name         = var.spn_display_name
  value        = azuread_service_principal_password.main.value
  key_vault_id = azurerm_key_vault.main.id
}