variable "project_name" {
  description = "Nome do projeto (usado como prefixo)."
  type        = string
}
variable "prefix" {
  description = "Prefixo para garantir unicidade e identificação dos recursos."
  type        = string
}
variable "resource_group_name" {
  description = "Nome do Resource Group."
  type        = string
}
variable "location" {
  description = "Região do Azure para provisionamento. Use regiões brasileiras como 'brazilsouth'."
  type        = string
}
variable "environment" {
  description = "Ambiente (dev, test, prod)."
  type        = string
}
variable "storage_account_name" {
  description = "Nome da Storage Account (único globalmente)."
  type        = string
}
variable "key_vault_name" {
  description = "Nome do Key Vault (único globalmente)."
  type        = string
}
variable "spn_display_name" {
  description = "Nome do Service Principal (Azure AD)."
  type        = string
}
variable "container_names" {
  description = "Lista de containers para criar no Data Lake."
  type        = list(string)
}
variable "databricks_workspace" {
  description = "Nome do workspace Databricks."
  type        = string
}
variable "databricks_user" {
  description = "E-mail do usuário Databricks."
  type        = string
}
variable "cluster_name" {
  description = "Nome do cluster Databricks."
  type        = string
}