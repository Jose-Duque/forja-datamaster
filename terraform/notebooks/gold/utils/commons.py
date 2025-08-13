from pyspark.sql import SparkSession, functions as F
from typing import List, Dict, Optional
from collections import Counter

class GoldTableProcessor:
    def __init__(self, silver_table_name: str):
        self.spark = SparkSession.getActiveSession()
        if not self.spark:
            raise Exception("SparkSession is not active.")
        
        self.silver_table_name = silver_table_name
        self.df = self._load_silver_table()

    def _load_silver_table(self):
        try:
            return self.spark.table(f"datamasterbr.silver.{self.silver_table_name}")
        except Exception as e:
            raise Exception(f"Error loading Silver table '{self.silver_table_name}': {e}")

    def aggregate_multiple(self, group_columns: List[str], aggregations: Dict[str, str]):
        try:
            functions_map = {
                'sum': F.sum,
                'avg': F.avg,
                'count': F.count,
                'max': F.max,
                'min': F.min
            }

            agg_expressions = []
            for column, func in aggregations.items():
                if func not in functions_map:
                    raise ValueError(f"Aggregate function '{func}' not supported for column '{column}'.")
                agg_expressions.append(functions_map[func](column).alias(f"{func}_{column}"))

            aggregated_df = self.df.groupBy(*group_columns).agg(*agg_expressions)
            self.df = aggregated_df
            return self.df

        except Exception as e:
            raise Exception(f"Error performing multiple aggregations: {e}")

    def run_query(self, query: str):
        try:
            self.df = self.spark.sql(query)
            return self.df
        except Exception as e:
            raise Exception(f"Error executing query: {e}")

    def join_with_table(
        self,
        other_table: str,
        join_condition: List[str],
        join_type: str = "inner",
        alias_main: str = "a",
        alias_other: str = "b"
    ):
        try:
            df_other = self.spark.table(f"datamasterbr.silver.{other_table}")

            conflicting_cols = [col for col in df_other.columns if col in self.df.columns and col not in join_condition]
            for col in conflicting_cols:
                df_other = df_other.withColumnRenamed(col, f"{col}_{alias_other}")

            df_a = self.df.alias(alias_main)
            df_b = df_other.alias(alias_other)

            condition = [F.col(f"{alias_main}.{col}") == F.col(f"{alias_other}.{col}") for col in join_condition]

            joined_df = df_a.join(df_b, on=condition, how=join_type)

            selected_columns = [F.col(f"{alias_main}.{col}").alias(col) for col in self.df.columns]
            selected_columns += [F.col(f"{alias_other}.{col}") for col in df_other.columns if col not in join_condition]

            self.df = joined_df.select(*selected_columns)
            return self.df

        except Exception as e:
            raise Exception(f"Error performing join with table '{other_table}': {e}")

    def select_columns(self, columns_to_keep: List[str]):
        missing = [col for col in columns_to_keep if col not in self.df.columns]
        if missing:
            raise Exception(f"Columns not found in DataFrame: {missing}")
        self.df = self.df.select(*columns_to_keep)

    def drop_duplicate_columns(self):
        col_counts = Counter(self.df.columns)
        colunas_vistas = set()
        colunas_unicas = []
        for col in self.df.columns:
            if col not in colunas_vistas:
                colunas_unicas.append(col)
                colunas_vistas.add(col)
        self.df = self.df.select(*colunas_unicas)

    def save_as_delta(self, gold_table_name: str, partition_by: Optional[List[str]] = None):
        try:
            self.drop_duplicate_columns()
            writer = self.df.write.format("delta").mode("overwrite")
            if partition_by:
                writer = writer.partitionBy(*partition_by)
            writer.option("mergeSchema", "true").saveAsTable(f"datamasterbr.gold.{gold_table_name}")
            print(f"Delta Gold Table saved successfully: gold.{gold_table_name}")
        except Exception as e:
            raise Exception(f"Error saving Gold table: {e}")
