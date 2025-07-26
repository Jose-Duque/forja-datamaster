import os
from dotenv import load_dotenv

load_dotenv()

def get_env_config():
    return {
        "POSTGRES_CONN_ID": "postgres",
        "DATABRICKS_CONN_ID": "databricks_default",
        "TABLE_NAMES": ["clientes"],
        "DATALAKE_NAME": os.getenv("DATALAKE_NAME"),
        "SPN_CLIENT_ID": os.getenv("SPN_CLIENT_ID"),
        "TENANT_ID": os.getenv("TENANT_ID"),
        "SECRET_SCOPE": os.getenv("SECRET_SCOPE"),
        "SECRET_KEY": os.getenv("SECRET_KEY"),
        "DB_CONFIG": {
            "dbname": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT")
        },
        "AZURE_CONFIG": {
            "connection_string": os.getenv("AZURE_CONNECTION_STRING"),
            "container_name": os.getenv("AZURE_CONTAINER_NAME")
        },
        "DEFAULT_ARGS": {
            "owner": "duque",
            "retries": 1,
            "retry_delay": 300,
        }
    }