import yaml
import os
from dags.utils.terraform_outputs import TerraformOutputManager

manager_output = TerraformOutputManager()
config = {
    "airflow": {
        "connections": [
            {
                "conn_id": "postgres",
                "conn_type": "postgres",
                "conn_host": os.getenv("DB_HOST", "host.docker.internal"),
                "conn_schema": os.getenv("DB_SCHEMA", "loccar"),
                "conn_login": os.getenv("DB_LOGIN", "postgres"),
                "conn_password": os.getenv("DB_PASSWORD", "postgres"),
                "conn_port": int(os.getenv("DB_PORT", 5432)),
            },
            {
                "conn_id": "databricks_default",
                "conn_type": "databricks",
                "conn_host": manager_output.get_output(key="databricks_workspace_url"),
                "conn_schema": "",
                "conn_login": "",
                "conn_password": manager_output.get_output(key="databricks_token_value"),
                "conn_port": "",
                "conn_extra":
                            {
                            "appId": manager_output.get_output(key="service_principal_client_id"),
                            "password": manager_output.get_output(key="service_principal_password"),
                            "tenant": manager_output.get_output(key="service_principal_tenant_id"),
                            "displayName": manager_output.get_output(key="service_principal_name")
                            }
            },
        ],
        "pools": [
            {
                "pool_name": "",
                "pool_slot": "",
                "pool_description": "",
            }
        ],
        "variables": [
            {
                "variable_name": "example_var",
                "variable_value": os.getenv("EXAMPLE_VAR_VALUE", "hello_world"),
            }
        ]
    }
}

with open("airflow_settings.yaml", "w") as f:
    yaml.dump(config, f, default_flow_style=False)

print("Arquivo airflow_settings.yaml gerado com sucesso.")