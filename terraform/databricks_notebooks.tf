# Notebook utilitário da camada Bronze (funções comuns)
resource "databricks_notebook" "bronze_utils" {
  path     = "/Workspace/Users/${var.databricks_user}/bronze/utils/commons.py"
  language = "PYTHON"
  source   = "${path.module}/notebooks/bronze/utils/commons.py"
}

# Notebook principal da camada Bronze (pipeline principal)
resource "databricks_notebook" "bronze_main" {
  path     = "/Workspace/Users/${var.databricks_user}/bronze/main"
  language = "PYTHON"
  source   = "${path.module}/notebooks/bronze/main.py"
}

# Notebook principal da camada Silver (pipeline principal)
resource "databricks_notebook" "silver_main" {
  path     = "/Workspace/Users/${var.databricks_user}/silver/main"
  language = "PYTHON"
  source   = "${path.module}/notebooks/silver/main.py"
}

# Notebook utilitário da camada Silver (funções comuns)
resource "databricks_notebook" "silver_utils" {
  path     = "/Workspace/Users/${var.databricks_user}/silver/utils/commons.py"
  language = "PYTHON"
  source   = "${path.module}/notebooks/silver/utils/commons.py"
}

# Notebook principal da camada Gold (pipeline principal)
resource "databricks_notebook" "gold_main" {
  path     = "/Workspace/Users/${var.databricks_user}/gold/main"
  language = "PYTHON"
  source   = "${path.module}/notebooks/gold/main.py"
}

# Notebook utilitário da camada Gold (funções comuns)
resource "databricks_notebook" "gold_utils" {
  path     = "/Workspace/Users/${var.databricks_user}/gold/utils/commons.py"
  language = "PYTHON"
  source   = "${path.module}/notebooks/gold/utils/commons.py"
}

# Permissão para o SPN gerenciar o notebook Bronze principal
resource "databricks_permissions" "bronze_main_run" {
  notebook_path = databricks_notebook.bronze_main.path
  access_control {
    service_principal_name = azuread_application.main.client_id
    permission_level       = "CAN_MANAGE"
  }
}

# Permissão para o SPN gerenciar o notebook Bronze utilitário
resource "databricks_permissions" "bronze_utils_run" {
  notebook_path = databricks_notebook.bronze_utils.path
  access_control {
    service_principal_name = azuread_application.main.client_id
    permission_level       = "CAN_MANAGE"
  }
}

# Permissão para o SPN gerenciar o notebook Silver principal
resource "databricks_permissions" "silver_main_run" {
  notebook_path = databricks_notebook.silver_main.path
  access_control {
    service_principal_name = azuread_application.main.client_id
    permission_level       = "CAN_MANAGE"
  }
}

# Permissão para o SPN gerenciar o notebook Silver utilitário
resource "databricks_permissions" "silver_utils_run" {
  notebook_path = databricks_notebook.silver_utils.path
  access_control {
    service_principal_name = azuread_application.main.client_id
    permission_level       = "CAN_MANAGE"
  }
}

# Permissão para o SPN gerenciar o notebook Gold principal
resource "databricks_permissions" "gold_main_run" {
  notebook_path = databricks_notebook.gold_main.path
  access_control {
    service_principal_name = azuread_application.main.client_id
    permission_level       = "CAN_MANAGE"
  }
}

# Permissão para o SPN gerenciar o notebook Gold utilitário
resource "databricks_permissions" "gold_utils_run" {
  notebook_path = databricks_notebook.gold_utils.path
  access_control {
    service_principal_name = azuread_application.main.client_id
    permission_level       = "CAN_MANAGE"
  }
}