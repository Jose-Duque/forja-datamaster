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
            print(self._log(self.load_table, f"Carregando tabela: {self.table}"))
            return self.spark.table(f"datamasterbr.bronze.{self.table}")
        except Exception as e:
            raise ValueError(self._log(self.load_table, f"Erro ao carregar tabela: {e}"))

    def filter_by_column(self, column_name: str, value: str) -> DataFrame:
        try:
            print(self._log(self.filter_by_column, f"Filtrando coluna '{column_name}'"))
            return self.df.filter(F.col(column_name) == value)
        except Exception as e:
            raise ValueError(self._log(self.filter_by_column, f"Erro ao filtrar coluna: {e}"))

    def selection_columns(self, column_list: list) -> DataFrame:
        try:
            print(self._log(self.selection_columns, "Selecionando colunas"))
            return self.df.select(*column_list)
        except Exception as e:
            raise ValueError(self._log(self.selection_columns, f"Erro ao selecionar colunas: {e}"))

    def renaming_column(self, old_name: str, new_name: str) -> DataFrame:
        try:
            print(self._log(self.renaming_column, f"Renomeando coluna '{old_name}' para '{new_name}'"))
            return self.df.withColumnRenamed(old_name, new_name)
        except Exception as e:
            raise ValueError(self._log(self.renaming_column, f"Erro ao renomear coluna: {e}"))

    def adding_column(self, column_name: str, value: str) -> DataFrame:
        try:
            print(self._log(self.adding_column, f"Adicionando coluna '{column_name}' com valor '{value}'"))
            return self.df.withColumn(column_name, F.lit(value))
        except Exception as e:
            raise ValueError(self._log(self.adding_column, f"Erro ao adicionar coluna: {e}"))

    def executar_query(self, query: str) -> DataFrame:
        try:
            print(self._log(self.executar_query, "Executando consulta SQL"))
            return self.spark.sql(query)
        except Exception as e:
            raise ValueError(self._log(self.executar_query, f"Erro ao executar consulta SQL: {e}"))

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
                        f"Tentando salvar DataFrame na tabela {table_fqn} "
                        f"(Modo: {mode}, Externo: {external}, "
                        f"Particionado: {partition_column is not None})."
                    ),
                )
            )

            write_options = {
                "format": "delta",
                "mode": mode,
            }

            if partition_column:
                write_options["partitionBy"] = [partition_column]
                print(self._log(self.save_to_table, f"Particionando pela coluna: {partition_column}"))

            if external:
                if not self.storage:
                    raise ValueError("Nome da conta de armazenamento (self.storage) não está configurado.")

                table_path = f"abfss://{self.container_name}@{self.storage}.dfs.core.windows.net/{table_name}/"
                write_options["path"] = table_path
                print(self._log(self.save_to_table, f"Salvando como tabela Delta EXTERNA no caminho: {table_path}"))
            else:
                print(self._log(self.save_to_table, "Salvando como tabela Delta GERENCIADA."))

            dataframe.write.saveAsTable(name=table_fqn, **write_options)
            print(self._log(self.save_to_table, f"Operação de salvamento enviada com sucesso para {table_fqn}."))
        except Exception as e:
            raise ValueError(self._log(self.save_to_table, f"Erro ao salvar DataFrame na tabela {table_fqn}: {e}"))
