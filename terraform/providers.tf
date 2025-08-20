terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.0.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = ">= 2.0.0"
    }
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.47.0"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.9"
    }
  }

  required_version = ">= 1.3.0"
}

provider "azurerm" {
  features {}
}

provider "azuread" {}

provider "databricks" {
  host                        = azurerm_databricks_workspace.main.workspace_url
  azure_workspace_resource_id = azurerm_databricks_workspace.main.id
}
