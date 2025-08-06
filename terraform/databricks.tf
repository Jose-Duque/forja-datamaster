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
  name                = "ac-${var.prefix}-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  identity {
    type = "SystemAssigned"
  }
}

# Atribui permissão para o Access Connector acessar o Storage
resource "azurerm_role_assignment" "connector_blob_contrib" {
  scope                = azurerm_storage_account.data_lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_databricks_access_connector.main.identity[0].principal_id
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

  definition = jsonencode(
    {
      "data_security_mode": {
        "type": "fixed",
        "value": "USER_ISOLATION"
      },
      "spark_version": {
        "type": "fixed",
        "value": "13.3.x-scala2.12"
      },
      "node_type_id": {
        "type": "allowlist",
        "values": [
          "Standard_DS3_v2",
          "Standard_DS4_v2",
          "Standard_F4"
        ]
      },
      "num_workers": {
        "type": "range",
        "minValue": 1,
        "maxValue": 5
      },
      "autotermination_minutes": {
        "type": "range",
        "minValue": 10,
        "maxValue": 30
      }
    }
  )
  depends_on = [azurerm_databricks_workspace.main]
}

resource "databricks_cluster" "main" {
  cluster_name            = var.cluster_name
  spark_version           = "13.3.x-scala2.12"
  node_type_id            = "Standard_F4"
  autotermination_minutes = 10
  num_workers             = 1

  policy_id = databricks_cluster_policy.uc_policy.id
  spark_conf = {
    "fs.azure.account.auth.type.${azurerm_storage_account.data_lake.name}.dfs.core.windows.net" = "OAuth"
    "fs.azure.account.oauth.provider.type.${azurerm_storage_account.data_lake.name}.dfs.core.windows.net" = "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider"
    "fs.azure.account.oauth2.client.id.${azurerm_storage_account.data_lake.name}.dfs.core.windows.net" = azuread_application.main.client_id
    "fs.azure.account.oauth2.client.secret.${azurerm_storage_account.data_lake.name}.dfs.core.windows.net" = "{{secrets/${databricks_secret_scope.app.name}/${databricks_secret.publishing_api.key}}}"
    "fs.azure.account.oauth2.client.endpoint.${azurerm_storage_account.data_lake.name}.dfs.core.windows.net" = "https://login.microsoftonline.com/${data.azurerm_client_config.current.tenant_id}/oauth2/token"
    }
  custom_tags = {
    Environment = var.environment
  }

  depends_on = [ databricks_cluster_policy.uc_policy ]
}

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

resource "databricks_token" "my_automation_token" {
  comment = "Token para automação"
  lifetime_seconds = 2592000
}

locals {
  medallion_layers = ["bronze", "silver", "gold"]
}

# 3. Credencial de Armazenamento para acessar o Data Lake via Unity Catalog
resource "databricks_storage_credential" "uc_credential" {
  name = "uc-storage-credential-azure"
  azure_managed_identity {
    access_connector_id = azurerm_databricks_access_connector.main.id
  }
  comment = "Credencial para acesso ao Data Lake pelo Unity Catalog"
  owner   = var.databricks_user

  depends_on = [ azurerm_role_assignment.connector_blob_contrib ]
}

# 4. Localizações Externas para cada camada (bronze, silver, gold)
resource "databricks_external_location" "medallion_locations" {
  for_each         = toset(local.medallion_layers)
  name             = "${each.key}-external-location"
  url              = "abfss://${each.key}@${azurerm_storage_account.data_lake.name}.dfs.core.windows.net/"
  credential_name  = databricks_storage_credential.uc_credential.id
  comment          = "External location for the ${each.key} layer."
  owner            = var.databricks_user
}

# 6. Schemas (Databases) para as camadas bronze, silver e gold
resource "databricks_schema" "medallion_schemas" {
  for_each      = toset(local.medallion_layers)
  catalog_name  = var.databricks_workspace
  name          = each.key
  comment       = "Schema para a camada ${each.key}."
  owner         = var.databricks_user
}

# 7. Permissões (Grants) para o grupo de analistas
resource "databricks_grants" "analysts_usage" {
  # Permissão para usar o catálogo
  grant {
    principal  = var.databricks_user
    privileges = ["ALL PRIVILEGES"]
  }

  # Permissões para usar os schemas e criar tabelas neles
  for_each = databricks_schema.medallion_schemas
  grant {
    principal  = azuread_application.main.client_id
    privileges = ["ALL PRIVILEGES"]
  }

  catalog = var.databricks_workspace
}