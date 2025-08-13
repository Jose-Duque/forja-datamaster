%pip install cryptography

from pyspark.sql import SparkSession
from pyspark.sql.dataframe import DataFrame
from pyspark.sql.functions import udf, col
from pyspark.sql.types import StringType
from pyspark.sql.utils import AnalysisException
from pyspark.dbutils import DBUtils
from cryptography.fernet import Fernet
from typing import Optional
import datetime
from pytz import timezone
from typing import List

class Commons:
  def __init__(self, storage, container, table_name, schema):
    self.spark = SparkSession.builder.appName("SparkApp").getOrCreate()
    self.dbutils = DBUtils(self.spark)
    self.path = f"abfss://{container}@{storage}.dfs.core.windows.net/{table_name}/"
    # self.path = self.dbutils.fs.ls(f"/Volumes/workspace/{container}/{table_name}")[0].path
    self.schema = schema
    self.storage = storage
    self.table_name = table_name

  def logging(self, func, log_line):
    tz_sp = timezone("America/Sao_Paulo")
    now = datetime.datetime.strftime(datetime.datetime.now(tz_sp), "%Y-%m-%d %H:%M:%S")
    return(f"[ {now} ] {func.__name__} - INFO - {log_line}")

  def verify_path_storage(self) -> bool:
      try:
        self.dbutils.fs.ls(self.path)
        return True
      except Exception as e:
        raise ValueError(f"Path or storage not found / Check permission: {e}")

  def load_data(self, type: str) -> DataFrame:
    try:
      print(self.logging(self.load_data, "Loading data"))
      if type == "csv":
        df = self.spark.read.format(type).load(
                                              path=self.path, 
                                              schema=self.schema if self.schema else None, 
                                              header=self.validate_header(), 
                                              delimiter=self.indentify_delimiter()
                                            )
        return df
      else:
        df = self.spark.read.format(type).load(self.path)
        return df
    except Exception as e:
        raise ValueError(self.logging(self.load_data, f"Error loading data: {e}"))

  def file_type(self) -> str:
    try:
      print(self.logging(self.file_type, "Validating file type"))
      file_type = set(map(lambda x: x.name.split(".")[-1], self.dbutils.fs.ls(self.path)))
      return file_type
    except Exception as e:
      raise ValueError(self.logging(self.file_type, f"Error validating file type: {e}"))

  def indentify_delimiter(self):
    try:
      line = self.spark.read.format("text").load(self.path).take(1)[0][0]
      delimiter = list(set(filter(lambda x: x in ["\x01", "\t", ",", ";", "|"], line)))[0]
      return delimiter
    except:
      raise ValueError(self.logging(self.indentify_delimiter, "Error indentifying delimiter"))
  
  def validate_header(self) -> bool:
    try:
      print(self.logging(self.validate_header, "Validating header"))
      df_with_header = self.spark.read.option("header", "true").csv(self.path)
      df_no_header = self.spark.read.option("header", "false").csv(self.path)

      header_likely = df_with_header.columns != df_no_header.columns
      print(self.logging(self.validate_header, "Header is valid"))
      return header_likely
    except Exception as e:
      print(self.logging(self.validate_header, "Header is invalid"))
      return False
  
  def encrypt_multiple_columns(self, dataframe: DataFrame, columns: List[str]) -> DataFrame:
    try:
        print(self.logging(self.encrypt_multiple_columns, f"Encrypting columns: {columns}"))
        key = Fernet.generate_key()
        cipher_suite = Fernet(key)

        def encrypt_value(val):
            if val is None:
                return None
            return cipher_suite.encrypt(val.encode()).decode("utf-8")

        encrypt_udf = udf(encrypt_value, StringType())
        for col_name in columns:
            dataframe = dataframe.withColumn(
                f"{col_name}",
                encrypt_udf(col(col_name))
            )
        return dataframe
    except Exception as e:
      raise ValueError(self.logging(self.encrypt_multiple_columns, f"Error encrypting columns: {e}"))
        
  def save_to_table(
    self,
    dataframe: DataFrame,
    modo: str = "overwrite",
    coluna_particao: Optional[str] = "dt_ingest",
    external: bool = False
    ) -> None:
    
    tabela_fqn = f"datamasterbr.bronze.{self.table_name}"
    try:
        print(self.logging(self.save_to_table,(
                    f"Saving DataFrame to {tabela_fqn} "
                    f"(Modo: {modo}, External: {external}, "
                    f"Partititons: {coluna_particao is not None})."),))
        writer = (dataframe.write.format("delta").mode(modo).option("mergeSchema", "true"))

        if coluna_particao:
            writer = writer.partitionBy(coluna_particao)
            print(self.logging(self.save_to_table, f"Partitioning by column: {coluna_particao}"))

        if external:
            writer = writer.option("path", f"abfss://bronze@{self.storage}.dfs.core.windows.net/{self.table_name}/")
            print(
              self.logging(self.save_to_table, 
              f"Saving as EXTERNAL Delta table in: abfss://bronze@{self.storage}.dfs.core.windows.net/{self.table_name}/")
            )
        else:
            print(self.logging(self.save_to_table, "Saving as a MANAGED Delta Table"))

        writer.saveAsTable(tabela_fqn)
        print(self.logging(self.save_to_table, f"Table {tabela_fqn} saved successfully"))

    except Exception as e:
        raise ValueError(self.logging(self.save_to_table, f"Error saving table {tabela_fqn}: {e}"))