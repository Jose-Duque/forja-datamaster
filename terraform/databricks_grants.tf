# Concede todos os privilégios no catálogo e schemas para o usuário e SPN
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

# Concede todos os privilégios de acesso nas External Locations para o SPN
resource "databricks_grants" "spn_extloc_read" {
  for_each = databricks_external_location.medallion_locations

  external_location = each.value.name

  grant {
    principal  = azuread_application.main.client_id
    privileges = ["ALL PRIVILEGES"]
  }
}

# Concede todos os privilégios no catálogo para o SPN e acesso de USER para o grupo de analistas
resource "databricks_grants" "spn_catalog_use" {
  catalog = var.databricks_workspace
  grant {
    principal  = azuread_application.main.client_id
    privileges = ["ALL PRIVILEGES"]
  }
}

# Concede todos os privilégios nos schemas para o SPN e permissão de USER/SELECT para o grupo de analistas
resource "databricks_grants" "spn_schema_use" {
  for_each = databricks_schema.medallion_schemas

  schema = each.value.id
  grant {
    principal  = azuread_application.main.client_id
    privileges = ["ALL PRIVILEGES"]
  }
}