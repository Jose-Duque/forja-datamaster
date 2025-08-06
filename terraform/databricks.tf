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

resource "databricks_secret_acl" "spn_read_secret" {
  scope      = databricks_secret_scope.app.name
  principal  = azuread_application.main.client_id
  permission = "READ"
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

resource "databricks_permissions" "uc_policy_can_use" {
  cluster_policy_id = databricks_cluster_policy.uc_policy.id

  access_control {
    service_principal_name = azuread_application.main.client_id
    permission_level       = "CAN_USE"
  }
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

resource "databricks_permissions" "bronze_main_run" {
  notebook_path = databricks_notebook.bronze_main.path
  access_control {
    service_principal_name = azuread_application.main.client_id
    permission_level       = "CAN_MANAGE"
  }
}

resource "databricks_permissions" "bronze_utils_run" {
  notebook_path = databricks_notebook.bronze_utils.path
  access_control {
    service_principal_name = azuread_application.main.client_id
    permission_level       = "CAN_MANAGE"
  }
}

resource "databricks_token" "my_automation_token" {
  comment = "Token para automação"
  lifetime_seconds = 2592000
}

locals {
  medallion_layers = ["bronze", "silver", "gold"]
}

resource "databricks_storage_credential" "uc_credential" {
  name = "uc-storage-credential-azure"
  azure_managed_identity {
    access_connector_id = azurerm_databricks_access_connector.main.id
  }
  comment = "Credencial para acesso ao Data Lake pelo Unity Catalog"
  owner   = var.databricks_user

  depends_on = [ azurerm_role_assignment.connector_blob_contrib ]
}

resource "databricks_external_location" "medallion_locations" {
  for_each         = toset(local.medallion_layers)
  name             = "${each.key}-external-location"
  url              = "abfss://${each.key}@${azurerm_storage_account.data_lake.name}.dfs.core.windows.net/"
  credential_name  = databricks_storage_credential.uc_credential.id
  comment          = "External location for the ${each.key} layer."
  owner            = var.databricks_user
}

resource "databricks_schema" "medallion_schemas" {
  for_each      = toset(local.medallion_layers)
  catalog_name  = var.databricks_workspace
  name          = each.key
  comment       = "Schema para a camada ${each.key}."
  owner         = var.databricks_user
}

resource "databricks_grants" "analysts_usage" {
  grant {
    principal  = var.databricks_user
    privileges = ["ALL PRIVILEGES"]
  }

  for_each = databricks_schema.medallion_schemas
  grant {
    principal  = azuread_application.main.client_id
    privileges = ["ALL PRIVILEGES"]
  }

  catalog = var.databricks_workspace
}

resource "databricks_grants" "spn_extloc_read" {
  for_each = databricks_external_location.medallion_locations

  external_location = each.value.name

  grant {
    principal  = azuread_application.main.client_id
    privileges = ["READ_FILES"]
  }
}

# === Grants no catálogo ===
resource "databricks_grants" "spn_catalog_use" {
  catalog = var.databricks_workspace
  grant {
    principal  = azuread_application.main.client_id
    privileges = ["ALL PRIVILEGES"]
  }
}

# === Grants nos schemas (USE_SCHEMA + SELECT) ===
resource "databricks_grants" "spn_schema_use" {
  for_each = databricks_schema.medallion_schemas

  schema = each.value.id
  grant {
    principal  = azuread_application.main.client_id
    privileges = ["ALL PRIVILEGES"]
  }
}