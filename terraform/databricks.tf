provider "databricks" {
  alias      = "account"

  host       = "https://accounts.azuredatabricks.net"
  account_id = "452cd844-0da8-498e-aeda-1da30fc5f8d8"

  client_id       = "41e73722-17ec-4833-be30-912288057b9a"
  client_secret   = "dose588abdc34fbad36ab21da248253ed873"
  azure_tenant_id = "ec81c8cb-abe5-47b8-b6e9-e8aa10347fa0"
}

resource "azurerm_databricks_workspace" "main" {
  name                = var.databricks_workspace
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "premium"
}

resource "azurerm_databricks_access_connector" "main" {
  name                = "ac-${var.prefix}-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  identity { type = "SystemAssigned" }
}

# Permitir que o Access Connector leia o Data Lake
resource "azurerm_role_assignment" "connector_blob_contrib" {
  scope                = azurerm_storage_account.data_lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_databricks_access_connector.main.identity[0].principal_id
}

# SPN como contributor no workspace
resource "azurerm_role_assignment" "spn_ws_contributor" {
  principal_id         = azuread_service_principal.main.object_id
  role_definition_name = "Contributor"
  scope                = azurerm_databricks_workspace.main.id
}

###############################################################################
# 6. USUÁRIO ADMIN NO WORKSPACE
###############################################################################
resource "databricks_user" "admin" {
  user_name    = var.databricks_user
  display_name = "Admin User"
}

###############################################################################
# 7. UNITY CATALOG (ACCOUNT + WORKSPACE)
###############################################################################
locals { medallion_layers = ["bronze","silver","gold"] }

# 7.1 Metastore
resource "databricks_metastore" "main" {
  provider      = databricks.account
  name          = "metastore-${var.prefix}-${var.environment}"
  region        = var.location
  storage_root  = "abfss://uc@${azurerm_storage_account.data_lake.name}.dfs.core.windows.net/"
  owner         = databricks_service_principal.main.application_id
  force_destroy = true
}

# 7.2 Data-access
resource "databricks_metastore_data_access" "default" {
  provider      = databricks.account
  metastore_id  = databricks_metastore.main.id
  name          = "default-access"
  is_default    = true
  azure_managed_identity {
    access_connector_id = azurerm_databricks_access_connector.main.id
  }
}

# 7.3 Binding ao workspace
resource "databricks_metastore_assignment" "main" {
  metastore_id         = databricks_metastore.main.id
  workspace_id         = azurerm_databricks_workspace.main.workspace_id
}

# 7.4 Storage credential
resource "databricks_storage_credential" "uc_credential" {
  name = "uc-storage-credential-azure"
  azure_managed_identity { access_connector_id = azurerm_databricks_access_connector.main.id }
  owner = databricks_service_principal.main.application_id
  depends_on = [azurerm_role_assignment.connector_blob_contrib,
                databricks_metastore_assignment.main]
}

# 7.5 Catálogo principal
resource "databricks_catalog" "main" {
  name      = "main_catalog"
  comment   = "Catálogo principal para dados do projeto"
  owner     = databricks_service_principal.main.application_id
  depends_on = [databricks_metastore_assignment.main]
}

# 7.6 Schemas bronze/silver/gold
resource "databricks_schema" "medallion" {
  for_each     = toset(local.medallion_layers)
  catalog_name = databricks_catalog.main.name
  name         = each.key
  comment      = "Schema da camada ${each.key}"
  owner        = databricks_service_principal.main.application_id
}

# 7.7 External Locations
resource "databricks_external_location" "medallion" {
  for_each        = toset(local.medallion_layers)
  name            = "${each.key}-ext-loc"
  url             = "abfss://${each.key}@${azurerm_storage_account.data_lake.name}.dfs.core.windows.net/"
  credential_name = databricks_storage_credential.uc_credential.name
  owner           = databricks_service_principal.main.application_id
}

# 7.8 GRANTS → diretamente para o SPN (sem grupo de analistas)
## Catálogo
resource "databricks_grants" "spn_catalog" {
  catalog = databricks_catalog.main.name
  grant {
    principal  = databricks_service_principal.main.application_id
    privileges = ["USE_CATALOG"]
  }
}

## Schemas
resource "databricks_grants" "spn_schema" {
  for_each = databricks_schema.medallion
  catalog  = databricks_catalog.main.name
  schema   = each.value.name
  grant {
    principal  = databricks_service_principal.main.application_id
    privileges = ["USE_SCHEMA","CREATE_TABLE"]
  }
}

###############################################################################
# 8. POLICIES, SECRETS, TOKEN (opcionais)
###############################################################################
resource "databricks_service_principal" "main" {
  provider       = databricks.account
  display_name              = azuread_application.main.display_name
  application_id            = azuread_application.main.client_id
  allow_cluster_create       = true
  allow_instance_pool_create = true
  databricks_sql_access      = true
}

resource "databricks_secret_scope" "app" {
  name       = "application-secret-scope"
  depends_on = [azurerm_databricks_workspace.main]
}

resource "databricks_secret" "publishing_api" {
  key          = "publishing_api"
  string_value = azuread_service_principal_password.main.value
  scope        = databricks_secret_scope.app.name
}

resource "databricks_token" "my_automation_token" {
  comment          = "Token para automação"
  lifetime_seconds = 2592000
  depends_on       = [azurerm_databricks_workspace.main]
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
          "Standard_DS4_v2"
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