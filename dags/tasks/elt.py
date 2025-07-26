from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from dags.models.ddl import Ddl
from dags.models.dml import Dml
from dags.utils.data_export_pipeline import DatabaseToAzureBlobPipeline
from dags.utils.terraform_outputs import TerraformOutputManager

from airflow.decorators import dag
from airflow.models.baseoperator import chain
from airflow.operators.empty import EmptyOperator
from airflow.utils.task_group import TaskGroup
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.operators.python import PythonOperator
from airflow.providers.databricks.operators.databricks_sql import DatabricksSqlOperator
from astro_databricks import DatabricksNotebookOperator, DatabricksWorkflowTaskGroup

POSTGRES_CONN_ID = "postgres"
DATABRICKS_CONN_ID = "databricks_default"
load_dotenv()

db_config = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}

azure_config = {
    "connection_string": os.getenv("AZURE_CONNECTION_STRING"),
    "container_name": os.getenv("AZURE_CONTAINER_NAME")
}

TABLE_NAMES = ["clientes"]

default_args = {
    "owner": "duque",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

@dag(
    dag_id="extract-load-transform",
    start_date=datetime(2025, 7, 4),
    schedule_interval="0 2 * * *",
    default_args=default_args,
    catchup=False,
    max_active_runs=1,
    tags=["azure", "databricks", "development", "extract", "ingestion" "load", "transform"]
)
def extract_load_transform():
    init = EmptyOperator(task_id="init")

    with TaskGroup("create_table") as create_table_postgres:
        for table_name in TABLE_NAMES:
            PostgresOperator(
                task_id=f"create_table_{table_name}",
                postgres_conn_id=POSTGRES_CONN_ID,
                sql=Ddl(table_name).create_table(),
                autocommit=False
            )
    
    with TaskGroup("insert_table") as insert_table_postgres:
        for table_name in TABLE_NAMES:
            PostgresOperator(
                task_id=f"insert_tabela_{table_name}",
                postgres_conn_id=POSTGRES_CONN_ID,
                sql=Dml(table_name).insert_table(),
                autocommit=False
            )
    
    with TaskGroup("ingestion_to_datalake") as ingestion_file_datalake:
        for table_name in TABLE_NAMES:
            PythonOperator(
                task_id=f"ingestion_{table_name}_to_datalake",
                python_callable=DatabaseToAzureBlobPipeline(db_config, azure_config).run_pipeline,
                op_args=[table_name]
            )

    with TaskGroup("delete_file_container") as delete_file_from_container:
        for table_name in TABLE_NAMES:
            PythonOperator(
                task_id=f"delete_file_{table_name}_container",
                python_callable=DatabaseToAzureBlobPipeline(db_config, azure_config).delete_blobs_inside_folder,
                op_args=[f"{table_name}/"]
            )

    finish = EmptyOperator(task_id="finish")
    chain(
        init,
        create_table_postgres,
        insert_table_postgres,
        ingestion_file_datalake,
        delete_file_from_container,
        finish
    )
dag = extract_load_transform()