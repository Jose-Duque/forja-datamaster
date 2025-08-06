%pip install cryptography

from pyspark.sql import SparkSession
from pyspark.sql.dataframe import DataFrame
from pyspark.sql.functions import udf, col
from pyspark.sql.types import StringType
from pyspark.dbutils import DBUtils
from cryptography.fernet import Fernet
from pytz import timezone
from typing import List
import datetime

class Commons:
    def __init__(self, storage: str, container: str, table_name: str, schema=None):
        self.spark = SparkSession.builder.appName("SparkApp").getOrCreate()
        self.dbutils = DBUtils(self.spark)
        self.path = f"abfss://{container}@{storage}.dfs.core.windows.net/{table_name}/"
        # self.path = self.dbutils.fs.ls(f"/Volumes/workspace/{container}/{table_name}")[0].path
        self.schema = schema
        self.table_name = table_name

    def _log(self, func, mensagem: str) -> str:
        tz_sp = timezone("America/Sao_Paulo")
        agora = datetime.datetime.now(tz_sp).strftime("%Y-%m-%d %H:%M:%S")
        return f"[ {agora} ] {func.__name__} - INFO - {mensagem}"

    def verificar_path_storage(self) -> bool:
        try:
            self.dbutils.fs.ls(self.path)
            return True
        except Exception as e:
            raise ValueError(f"Caminho ou storage não encontrado / Verifique permissões: {e}")

    def tipo_arquivos(self) -> set:
        try:
            print(self._log(self.tipo_arquivos, "Validando tipo de arquivo"))
            tipos = set(
                map(lambda x: x.name.split(".")[-1], self.dbutils.fs.ls(self.path))
            )
            return tipos
        except Exception as e:
            raise ValueError(self._log(self.tipo_arquivos, f"Erro ao validar tipo de arquivo: {e}"))

    def identificar_delimitador(self) -> str:
        try:
            linha = self.spark.read.format("text").load(self.path).take(1)[0][0]
            delimitador = list(
                set(filter(lambda x: x in ["\x01", "\t", ",", ";", "|"], linha))
            )[0]
            return delimitador
        except Exception:
            raise ValueError(self._log(self.identificar_delimitador, "Erro ao identificar delimitador"))

    def validar_header(self) -> bool:
        try:
            print(self._log(self.validar_header, "Validando cabeçalho"))
            df_com_header = self.spark.read.option("header", "true").csv(self.path)
            df_sem_header = self.spark.read.option("header", "false").csv(self.path)
            header_valido = df_com_header.columns != df_sem_header.columns
            print(self._log(self.validar_header, "Cabeçalho validado"))
            return header_valido
        except Exception:
            print(self._log(self.validar_header, "Cabeçalho inválido"))
            return False

    def carregar_dados(self, formato: str) -> DataFrame:
        try:
            print(self._log(self.carregar_dados, "Carregando dados"))
            if formato == "csv":
                df = (
                    self.spark.read.format(formato)
                    .load(
                        path=self.path,
                        schema=self.schema if self.schema else None,
                        header=self.validar_header(),
                        delimiter=self.identificar_delimitador(),
                    )
                )
            else:
                df = self.spark.read.format(formato).load(self.path)
            return df
        except Exception as e:
            raise ValueError(self._log(self.carregar_dados, f"Erro ao carregar dados: {e}"))

    def criptografar_colunas(self, dataframe: DataFrame, colunas: List[str]) -> DataFrame:
        try:
            print(self._log(self.criptografar_colunas, f"Criptografando colunas: {colunas}"))
            chave = Fernet.generate_key()
            cipher_suite = Fernet(chave)

            def _criptografar(valor):
                if valor is None:
                    return None
                return cipher_suite.encrypt(valor.encode()).decode("utf-8")

            criptografar_udf = udf(_criptografar, StringType())

            for nome_coluna in colunas:
                dataframe = dataframe.withColumn(nome_coluna, criptografar_udf(col(nome_coluna)))

            return dataframe
        except Exception as e:
            raise ValueError(self._log(self.criptografar_colunas, f"Erro ao criptografar colunas: {e}"))

    def salvar_tabela(self, dataframe: DataFrame) -> None:
        try:
            print(self._log(self.salvar_tabela, "Salvando na tabela"))
            (
                dataframe.write.format("delta")
                .partitionBy("dt_ingest")
                .mode("overwrite")
                .option("mergeSchema", "true")
                .saveAsTable(f"datamasterbr.bronze.{self.table_name}")
            )
            print(self._log(self.salvar_tabela, "Tabela salva com sucesso"))
        except Exception as e:
            raise ValueError(self._log(self.salvar_tabela, f"Erro ao salvar na tabela: {e}"))
