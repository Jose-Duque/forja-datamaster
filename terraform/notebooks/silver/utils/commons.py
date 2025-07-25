from pyspark.sql import SparkSession
from pyspark.sql.dataframe import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.utils import AnalysisException
import time
import datetime
from pytz import timezone
from typing import Optional

class SilverTableHandler:
    def __init__(self, table, storage=None, container_name=None):
        self.spark = SparkSession.builder.appName("SparkApp").getOrCreate()
        self.table = table
        self.storage = storage
        self.container_name = container_name
        self.df = self.load_table()
    
    def logging(self, func, log_line):
        tz_sp = timezone("America/Sao_Paulo")
        now = datetime.datetime.strftime(datetime.datetime.now(tz_sp), "%Y-%m-%d %H:%M:%S")
        return(f"[ {now} ] {func.__name__} - INFO - {log_line}")

    def load_table(self) -> DataFrame:
        try:
            print(self.logging(self.load_table, f"Loading table: {self.table}"))
            df = self.spark.table(f"bronze.{self.table}")
            return df
        except Exception as e:
            print(self.logging(self.load_table, f"Error loading table: {e}"))
            raise

    def filter_by_column(self, column_name: str, value: str) -> DataFrame:
        try:
            print(self.logging(self.filter_by_column, f"Filtering column"))
            return self.df.filter(F.col(column_name) == value)
        except Exception as e:
            print(self.logging(self.filter_by_column, f"Error filtering column: {e}"))
            raise

    def selection_columns(self, column_list: list) -> DataFrame:
        try:
            print(self.logging(self.selection_columns, f"Selecting columns"))
            return self.df.select(*column_list)
        except Exception as e:
            print(self.logging(self.selection_columns, f"Error selecting columns: {e}"))
            raise

    def renaming_column(self, old_name: str, new_name: str) -> DataFrame:
        try:
            print(self.logging(self.renaming_column, f"Renaming column {old_name} to {new_name}"))
            return self.df.withColumnRenamed(old_name, new_name)
        except Exception as e:
            print(self.logging(self.renaming_column, f"Error renaming column: {e}"))
            raise

    def adding_column(self, column_name: str, value: str) -> DataFrame:
        try:
            print(self.logging(self.adding_column, f"Adding column {column_name} with value {value}"))
            return self.df.withColumn(column_name, F.lit(value))
        except Exception as e:
            print(self.logging(self.adding_column, f"Error adding column: {e}"))  
            raise

    def executar_query(self, query: str) -> DataFrame:
        try:
            print(self.logging(self.executar_query, f"Executando query SQL"))
            return spark.sql(query)
        except Exception as e:
            print(self.logging(self.executar_query, f"Error executing query SQL: {e}"))
            raise

    def save_to_table(self,
                       dataframe: DataFrame,
                       catalog: str,
                       table_name: str,
                       external: bool, 
                       mode: str,
                       database: str = "silver",
                       partition_column: Optional[str] = None
                      ) -> None:
        table_fqn = f"{catalog}.{database}.{table_name}"

        try:
            print(self.logging(self.save_to_table, f"Attempting to save DataFrame to table {table_fqn} (Mode: {mode}, External: {external}, Partitioned: {partition_column is not None})."))

            write_options = {
                "format": "delta",
                "mode": mode,
            }

            if partition_column:
                write_options["partitionBy"] = [partition_column]
                print(self.logging(self.save_to_table, f"Partitioning by column: {partition_column}"))

            if external:
                if not self.storage:
                     raise ValueError("Storage account name (self.storage) is not configured.")

                table_path = f"abfss://{self.container_name}@{self.storage}.dfs.core.windows.net/{table_name}/"
                write_options["path"] = table_path
                print(self.logging(self.save_to_table, f"Saving as EXTERNAL Delta table to path: {table_path}"))
            else:
                print(self.logging(self.save_to_table, f"Saving as MANAGED Delta table."))

            dataframe.write.saveAsTable(
                name=table_fqn,
                **write_options
            )
            print(self.logging(self.save_to_table, f"Successfully submitted save operation for table {table_fqn}. Spark job will execute."))
        except Exception as e:
            print(self.logging(self.save_to_table, f"Error saving DataFrame to table {table_fqn}: {e}"))
            raise