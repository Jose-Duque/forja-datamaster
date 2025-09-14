# Catálogo
resource "databricks_grants" "catalog" {
  catalog = var.databricks_workspace

  grant {
    principal  = azuread_application.main.client_id
    privileges = ["USE_CATALOG", "MODIFY"]
  }

  grant {
    principal  = var.databricks_user
    privileges = ["USE_CATALOG"]
  }
  
  depends_on = [
    databricks_service_principal.main,
    azuread_application.main
  ]
}

# Schemas
resource "databricks_grants" "schemas" {
  for_each = databricks_schema.medallion_schemas

  schema = each.value.id

  grant {
    principal  = azuread_application.main.client_id
    privileges = ["USE_SCHEMA", "SELECT", "MODIFY", "CREATE_TABLE"]
  }

  grant {
    principal  = var.databricks_user
    privileges = ["USE_SCHEMA", "SELECT"]
  }

  depends_on = [
    databricks_service_principal.main,
    azuread_application.main
  ]
}

# External Locations
resource "databricks_grants" "extlocs" {
  for_each = databricks_external_location.medallion_locations

  external_location = each.value.name

  grant {
    principal  = azuread_application.main.client_id
    privileges = ["READ_FILES", "WRITE_FILES", "CREATE_EXTERNAL_TABLE"]
  }

  depends_on = [
    databricks_service_principal.main,
    azuread_application.main
  ]
}
