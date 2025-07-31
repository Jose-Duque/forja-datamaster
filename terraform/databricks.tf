resource "azurerm_databricks_workspace" "main" {
  name                = var.databricks_workspace
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "premium"
}

resource "azurerm_role_assignment" "spn_databricks_contributor" {
  principal_id         = azuread_service_principal.main.object_id
  role_definition_name = "Contributor"
  scope                = azurerm_databricks_workspace.main.id
}

resource "azurerm_databricks_access_connector" "main" {
  name                = "access-connector"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  identity {
    type = "SystemAssigned"
  }
}

resource "databricks_service_principal" "main" {
  display_name = azuread_application.main.display_name
  application_id = azuread_application.main.client_id

  allow_cluster_create      = true
  databricks_sql_access     = true
  allow_instance_pool_create = true

  depends_on = [azurerm_databricks_workspace.main]
}

resource "databricks_secret_scope" "app" {
  name = "application-secret-scope"
}

resource "databricks_secret" "publishing_api" {
  key          = "publishing_api"
  string_value = azurerm_key_vault_secret.spn_password.value
  scope        = databricks_secret_scope.app.id
}

resource "databricks_cluster_policy" "uc_policy" {
  name = "unity-catalog-policy"

  definition = jsonencode({
    "data_security_mode": {
      "type": "fixed",
      "value": "USER_ISOLATION"
    },
    "spark_version": {
      "type": "fixed",
      "value": "13.3.x-scala2.12"
    },
    "node_type_id": {
      "type": "allow",
      "values": [
        "Standard_DS3_v2",
        "Standard_D4as_v5",
        "Standard_D2as_v5"
      ]
    },
    "num_workers": {
      "type": "fixed",
      "value": 1
    },
    "auto_termination_minutes": {
      "type": "fixed",
      "value": 10
    }
  })
}

# resource "databricks_cluster" "main" {
#   cluster_name            = var.cluster_name
#   spark_version           = "13.3.x-scala2.12"
#   node_type_id            = "Standard_DS3_v2"
#   autotermination_minutes = 10
#   num_workers             = 1

#   policy_id = databricks_cluster_policy.uc_policy.id
#   spark_conf = {
#     "fs.azure.account.auth.type.${azurerm_storage_account.data_lake.name}.dfs.core.windows.net" = "OAuth"
#     "fs.azure.account.oauth.provider.type.${azurerm_storage_account.data_lake.name}.dfs.core.windows.net" = "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider"
#     "fs.azure.account.oauth2.client.id.${azurerm_storage_account.data_lake.name}.dfs.core.windows.net" = azuread_application.main.client_id
#     "fs.azure.account.oauth2.client.secret.${azurerm_storage_account.data_lake.name}.dfs.core.windows.net" = "{{secrets/${databricks_secret_scope.app.name}/${databricks_secret.publishing_api.key}}}"
#     "fs.azure.account.oauth2.client.endpoint.${azurerm_storage_account.data_lake.name}.dfs.core.windows.net" = "https://login.microsoftonline.com/${data.azurerm_client_config.current.tenant_id}/oauth2/token"
#     }
#   custom_tags = {
#     Environment = var.environment
#   }

#   depends_on = [ databricks_cluster_policy.uc_policy ]
# }

resource "databricks_notebook" "bronze_utils" {
  path     = "/Workspace/Users/${var.databricks_user}/bronze/utils/commons.py"
  language = "PYTHON"
  source   = "${path.module}/notebooks/bronze/utils/commons.py"
}

resource "databricks_notebook" "bronze_main" {
  path     = "/Workspace/Users/${var.databricks_user}/bronze/main"
  language = "PYTHON"
  source   = "${path.module}/notebooks/bronze/main.py"
}

resource "databricks_notebook" "silver_main" {
  path     = "/Workspace/Users/${var.databricks_user}/silver/main"
  language = "PYTHON"
  source   = "${path.module}/notebooks/silver/main.py"
}

resource "databricks_notebook" "silver_utils" {
  path     = "/Workspace/Users/${var.databricks_user}/silver/utils/commons.py"
  language = "PYTHON"
  source   = "${path.module}/notebooks/silver/utils/commons.py"
}

resource "databricks_notebook" "gold_main" {
  path     = "/Workspace/Users/${var.databricks_user}/gold/main"
  language = "PYTHON"
  source   = "${path.module}/notebooks/gold/main.py"
}

resource "databricks_notebook" "gold_utils" {
  path     = "/Workspace/Users/${var.databricks_user}/gold/utils/commons.py"
  language = "PYTHON"
  source   = "${path.module}/notebooks/gold/utils/commons.py"
}

resource "databricks_group" "data_analysts_group" {
  display_name = "data-analysts-group"
  allow_cluster_create = true
  allow_instance_pool_create = true
  databricks_sql_access = true
  workspace_access = true
}

resource "databricks_token" "my_automation_token" {
  comment = "Token para automação"
  lifetime_seconds = 2592000
}

locals {
  medallion_layers = ["bronze", "silver", "gold"]
}

# Credencial para o Unity Catalog acessar o storage
resource "databricks_storage_credential" "uc_credential" {
  provider = databricks
  name     = "uc_storage_credential_azure"
  azure_managed_identity {
    access_connector_id = azurerm_databricks_access_connector.main.id
  }
  comment = "Credencial para acesso ao Data Lake pelo Unity Catalog"
}

resource "databricks_schema" "medallion_layers" {
  for_each     = toset(local.medallion_layers)
  name         = each.key
  catalog_name = "${var.databricks_workspace}_${azurerm_databricks_workspace.main.workspace_id}"
  comment      = "Camada ${each.key}"
}