from pyspark.sql import SparkSession
from pyspark.sql.dataframe import DataFrame
from pyspark.sql import functions as F
from pytz import timezone
from typing import Optional
import datetime

class SilverTableHandler:
    def __init__(self, table, storage=None, container_name="silver"):
        self.spark = SparkSession.builder.appName("SparkApp").getOrCreate()
        self.table = table
        self.storage = storage
        self.container_name = container_name
        self.df = self.load_table()

    def _log(self, func, msg: str) -> str:
        tz_sp = timezone("America/Sao_Paulo")
        now = datetime.datetime.now(tz_sp).strftime("%Y-%m-%d %H:%M:%S")
        return f"[ {now} ] {func.__name__} - INFO - {msg}"

    def load_table(self) -> DataFrame:
        try:
            print(self._log(self.load_table, f"Loading table: {self.table}"))
            return self.spark.table(f"datamasterbr.bronze.{self.table}")
        except Exception as e:
            raise ValueError(self._log(self.load_table, f"Error loading table: {e}"))

    def filter_by_column(self, column_name: str, value: str) -> DataFrame:
        try:
            print(self._log(self.filter_by_column, f"Filtering column '{column_name}'"))
            return self.df.filter(F.col(column_name) == value)
        except Exception as e:
            raise ValueError(self._log(self.filter_by_column, f"Error when filtering column: {e}"))

    def selection_columns(self, column_list: list) -> DataFrame:
        try:
            print(self._log(self.selection_columns, "Selecting columns"))
            return self.df.select(*column_list)
        except Exception as e:
            raise ValueError(self._log(self.selection_columns, f"Error selecting columns: {e}"))

    def renaming_column(self, old_name: str, new_name: str) -> DataFrame:
        try:
            print(self._log(self.renaming_column, f"Renaming column '{old_name}' to '{new_name}'"))
            return self.df.withColumnRenamed(old_name, new_name)
        except Exception as e:
            raise ValueError(self._log(self.renaming_column, f"Error renaming column: {e}"))

    def adding_column(self, column_name: str, value: str) -> DataFrame:
        try:
            print(self._log(self.adding_column, f"Adding column '{column_name}' with value '{value}'"))
            return self.df.withColumn(column_name, F.lit(value))
        except Exception as e:
            raise ValueError(self._log(self.adding_column, f"Error adding column: {e}"))

    def executar_query(self, query: str) -> DataFrame:
        try:
            print(self._log(self.executar_query, "Executing SQL query"))
            return self.spark.sql(query)
        except Exception as e:
            raise ValueError(self._log(self.executar_query, f"Error executing SQL query: {e}"))

    def save_to_table(
        self,
        dataframe: DataFrame,
        table_name: str,
        external: bool,
        mode: str,
        database: str = "silver",
        partition_column: Optional[str] = None,
    ) -> None:

        table_fqn = f"datamasterbr.{database}.{table_name}"
        try:
            print(
                self._log(
                    self.save_to_table,
                    (
                        f"Trying to save DataFrame to table {table_fqn} "
                        f"(Modo: {mode}, Externo: {external}, "
                        f"Partition: {partition_column is not None})."
                    ),
                )
            )

            write_options = {
                "format": "delta",
                "mode": mode,
            }

            if partition_column:
                write_options["partitionBy"] = [partition_column]
                print(self._log(self.save_to_table, f"Partitioning by column: {partition_column}"))

            if external:
                if not self.storage:
                    raise ValueError(f"Storage account name {self.storage} is not configured.")

                table_path = f"abfss://{self.container_name}@{self.storage}.dfs.core.windows.net/{table_name}/"
                write_options["path"] = table_path
                print(self._log(self.save_to_table, f"Saving as EXTERNAL Delta table in path: {table_path}"))
            else:
                print(self._log(self.save_to_table, "Saving as a MANAGED Delta Table."))

            dataframe.write.saveAsTable(name=table_fqn, **write_options)
            print(self._log(self.save_to_table, f"Rescue operation successfully sent to {table_fqn}."))
        except Exception as e:
            raise ValueError(self._log(self.save_to_table, f"Error saving DataFrame to table {table_fqn}: {e}"))
