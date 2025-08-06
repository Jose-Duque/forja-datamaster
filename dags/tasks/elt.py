from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from dags.models.ddl import Ddl
from dags.models.dml import Dml
from dags.utils.data_export_pipeline import DatabaseToAzureBlobPipeline
from dags.utils.terraform_outputs import TerraformOutputManager
from dags.config.env_config import get_env_config
from dags.config.databricks_cluster import build_job_cluster_spec

from airflow.decorators import dag, task_group
from airflow.models.baseoperator import chain
from airflow.operators.empty import EmptyOperator
from airflow.utils.task_group import TaskGroup
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.operators.python import PythonOperator
from airflow.providers.databricks.operators.databricks_sql import DatabricksSqlOperator
from astro_databricks import DatabricksNotebookOperator, DatabricksWorkflowTaskGroup

config = get_env_config()
POSTGRES_CONN_ID = config["POSTGRES_CONN_ID"]
DATABRICKS_CONN_ID = config["DATABRICKS_CONN_ID"]
TABLE_NAMES = config["TABLE_NAMES"]
datalake_name = config["DATALAKE_NAME"]
spn_client_id = config["SPN_CLIENT_ID"]
tenant_id = config["TENANT_ID"]
secret_scope = config["SECRET_SCOPE"]
secret_key = config["SECRET_KEY"]
db_config = config["DB_CONFIG"]
azure_config = config["AZURE_CONFIG"]
default_args = config["DEFAULT_ARGS"]

job_cluster_spec = build_job_cluster_spec(
    datalake_name=datalake_name,
    spn_client_id=spn_client_id,
    tenant_id=tenant_id,
    secret_scope=secret_scope,
    secret_key=secret_key
)

@dag(
    dag_id="extract-load-transform",
    start_date=datetime(2025, 7, 4),
    schedule_interval="0 2 * * *",
    default_args=default_args,
    catchup=False,
    max_active_runs=1,
    tags=["azure", "databricks", "development", "extract", "ingestion", "load", "transform"]
)
def extract_load_transform():
    init = EmptyOperator(task_id="init")

    # with TaskGroup("create_table") as create_table_postgres:
    #     for table_name in TABLE_NAMES:
    #         PostgresOperator(
    #             task_id=f"create_table_{table_name}",
    #             postgres_conn_id=POSTGRES_CONN_ID,
    #             sql=Ddl(table_name).create_table(),
    #             autocommit=False
    #         )
    
    # with TaskGroup("insert_table") as insert_table_postgres:
    #     for table_name in TABLE_NAMES:
    #         PostgresOperator(
    #             task_id=f"insert_tabela_{table_name}",
    #             postgres_conn_id=POSTGRES_CONN_ID,
    #             sql=Dml(table_name).insert_table(),
    #             autocommit=False
    #         )
    
    # with TaskGroup("ingestion_to_datalake") as ingestion_file_datalake:
    #     for table_name in TABLE_NAMES:
    #         PythonOperator(
    #             task_id=f"ingestion_{table_name}_to_datalake",
    #             python_callable=DatabaseToAzureBlobPipeline(db_config, azure_config).run_pipeline,
    #             op_args=[table_name]
    #         )

    with DatabricksWorkflowTaskGroup(
        group_id="databricks_workflow",
        databricks_conn_id=DATABRICKS_CONN_ID,
        job_clusters=job_cluster_spec,
        notebook_params={"start_time": "{{ ds }}"},
    ) as workflow:
        
        raw_to_bronze_clientes = DatabricksNotebookOperator(
            task_id="bronze_ingest_clientes",
            databricks_conn_id=DATABRICKS_CONN_ID,
            notebook_path=TerraformOutputManager().get_output("path_notebooks_bronze"),
            source="WORKSPACE",
            # job_cluster_key=TerraformOutputManager().get_output("cluster_key"),
            job_cluster_key="cluster-data-analytics",
            notebook_params={
                "storage": TerraformOutputManager().get_output("storage_account_name"),
                "container": "raw",
                "table_name": "clientes",
                "schema": "",
                "encrypt_columns": "cpf_cnpj",
            }
        )

        raw_to_bronze_vendedores = DatabricksNotebookOperator(
            task_id="bronze_ingest_vendedores",
            databricks_conn_id=DATABRICKS_CONN_ID,
            notebook_path=TerraformOutputManager().get_output("path_notebooks_bronze"),
            source="WORKSPACE",
            job_cluster_key="cluster-data-analytics",
            notebook_params={
                "storage": TerraformOutputManager().get_output("storage_account_name"),
                "container": "raw",
                "table_name": "vendedores",
                "schema": "",
                "encrypt_columns": "",
            }
        )

        raw_to_bronze_vendas = DatabricksNotebookOperator(
            task_id="bronze_ingest_vendas",
            databricks_conn_id=DATABRICKS_CONN_ID,
            notebook_path=TerraformOutputManager().get_output("path_notebooks_bronze"),
            source="WORKSPACE",
            job_cluster_key="cluster-data-analytics",
            notebook_params={
                "storage": TerraformOutputManager().get_output("storage_account_name"),
                "container": "raw",
                "table_name": "vendas",
                "schema": "",
                "encrypt_columns": "",
            }
        )

        @task_group(group_id="inner_task_group")
        def transform_group_silver():
            silver_clientes_transform = DatabricksNotebookOperator(
                task_id="silver_clientes_transform",
                databricks_conn_id=DATABRICKS_CONN_ID,
                notebook_path=TerraformOutputManager().get_output("path_notebooks_silver"),
                source="WORKSPACE",
                job_cluster_key="cluster-data-analytics",
                notebook_params={
                    "action":"rename",
                    "table":"clientes",
                    "storage":TerraformOutputManager().get_output("storage_account_name"),
                    "column":"cliente",
                    "value":"",
                    "new_name":"nome_cliente",
                    "columns":"",
                    "query":"",
                    "external":False,
                    "mode":"overwrite",
                    "partition_column":"dt_ingest"
                }
            )

            silver_vendedores_transform = DatabricksNotebookOperator(
                task_id="silver_vendedores_transform",
                databricks_conn_id=DATABRICKS_CONN_ID,
                notebook_path=TerraformOutputManager().get_output("path_notebooks_silver"),
                source="WORKSPACE",
                job_cluster_key="cluster-data-analytics",
                notebook_params={
                    "action":"query",
                    "table":"vendedores",
                    "storage":TerraformOutputManager().get_output("storage_account_name"),
                    "column":"",
                    "value":"",
                    "new_name":"",
                    "columns":"",
                    "query":"""SELECT
                                *,
                                id_vendedores IS NOT NULL AS ativo
                            FROM datamasterbr.bronze.vendedores""",
                    "external":False,
                    "mode":"overwrite",
                    "partition_column":"dt_ingest"
                }
            )
            [silver_clientes_transform,silver_vendedores_transform]

        gold_analytics = DatabricksNotebookOperator(
            task_id="gold_analytics",
            databricks_conn_id=DATABRICKS_CONN_ID,
            notebook_path=TerraformOutputManager().get_output("path_notebooks_gold"),
            source="WORKSPACE",
            job_cluster_key="cluster-data-analytics",
            notebook_params={
                "silver_table": "clientes",
                "catalog": f"""
                            {TerraformOutputManager().get_output('databricks_workspace_name')}_{TerraformOutputManager().get_output('databricks_workspace_id')}""",
                "gold_table": "analise_vendas_clientes",
                "action": "query",
                "group_by": "",
                "aggregations_input": "",
                "partition_by": "",
                "columns_to_keep": "",
                "join_table": "",
                "join_columns": "",
                "join_type": "",
                "query": """
                        SELECT
                            c.id_clientes,
                            c.nome_cliente,
                            c.cpf_cnpj,
                            c.endereco,
                            c.id_concessionarias,
                            COUNT(v.id_vendas) AS qtd_vendas,
                            SUM(v.valor_pago) AS valor_total_gasto,
                            AVG(v.valor_pago) AS ticket_medio,
                            MIN(v.data_venda) AS primeira_compra,
                            MAX(v.data_venda) AS ultima_compra,
                            COUNT(DISTINCT v.id_vendedores) AS qtd_vendedores_diferentes
                            FROM datamasterbr.silver.clientes AS c
                            LEFT JOIN datamasterbr.bronze.vendas AS v
                            ON c.id_clientes = v.id_clientes
                            LEFT JOIN datamasterbr.silver.vendedores AS vd
                            ON v.id_vendedores = vd.id_vendedores
                            GROUP BY
                            c.id_clientes,
                            c.nome_cliente,
                            c.cpf_cnpj,
                            c.endereco,
                            c.id_concessionarias;
                        """
            }
        )

        [raw_to_bronze_clientes,raw_to_bronze_vendedores,raw_to_bronze_vendas] >> transform_group_silver() >> gold_analytics

    # with TaskGroup("delete_file_container") as delete_file_from_container:
    #     for table_name in TABLE_NAMES:
    #         PythonOperator(
    #             task_id=f"delete_file_{table_name}_container",
    #             python_callable=DatabaseToAzureBlobPipeline(db_config, azure_config).delete_blobs_inside_folder,
    #             op_args=[f"{table_name}/"]
    #         )

    finish = EmptyOperator(task_id="finish")
    chain(
        init,
        # create_table_postgres,
        # insert_table_postgres,
        # ingestion_file_datalake,
        workflow,
        # delete_file_from_container,
        finish
    )
dag = extract_load_transform()