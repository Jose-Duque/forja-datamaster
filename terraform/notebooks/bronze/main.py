# Databricks notebook source
# COMMAND ----------
# MAGIC %run ./utils/commons.py

# COMMAND ----------
from pyspark.sql import functions as F
from pyspark.sql.types import StructType
import json

# COMMAND ----------
storage = dbutils.widgets.get('storage')
container = dbutils.widgets.get('container')
catalog = dbutils.widgets.get('catalog')
table_name = dbutils.widgets.get('table_name')
schema = dbutils.widgets.get('schema')
encrypt_columns = dbutils.widgets.get('encrypt_columns').split(",") if dbutils.widgets.get("encrypt_columns") else None

# COMMAND ----------
try:
    print("Initializing process")
    
    # schema = StructType.fromJson(json.loads(schema.replace("'", '"')))
    # spark.sql("USE CATALOG workspace")
    # spark.sql(f"CREATE SCHEMA IF NOT EXISTS bronze")
    # spark.sql("USE SCHEMA bronze")
    
    base = Commons(storage.strip(), container.strip(), table_name.strip(), schema)
    
    if base.verify_path_storage():
        _type = list(base.file_type())[0]
        df = base.load_data(_type).withColumn("dt_ingest", F.lit(F.current_date()))
        
        if encrypt_columns is not None:
            df = base.encrypt_multiple_columns(df, encrypt_columns)
        
        base.save_to_table(df, catalog)
    else:
        print("Path or storage not found")
except Exception as e:
    print(e)
