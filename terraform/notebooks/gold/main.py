# Databricks notebook source
# COMMAND ----------
# MAGIC %run ./utils/commons.py

# COMMAND ----------
silver_table = dbutils.widgets.get("silver_table")
gold_table = dbutils.widgets.get("gold_table")
action = dbutils.widgets.get("action").lower()
group_by = [col.strip() for col in dbutils.widgets.get("group_by").split(",") if col.strip()]
aggregations_input = dbutils.widgets.get("aggregations")
partition_by = [col.strip() for col in dbutils.widgets.get("partition_by").split(",") if col.strip()]
columns_to_keep = [col.strip() for col in dbutils.widgets.get("columns_to_keep").split(",") if col.strip()]
join_table = dbutils.widgets.get("join_table")
join_columns = [col.strip() for col in dbutils.widgets.get("join_columns").split(",") if col.strip()]
join_type = dbutils.widgets.get("join_type") or "inner"
query = dbutils.widgets.get("query")

# COMMAND ----------
aggregations = {}
if aggregations_input:
    for item in aggregations_input.split(","):
        if ":" in item:
            col, func = item.split(":")
            aggregations[col.strip()] = func.strip()

try:
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS gold")
    processor = GoldTableProcessor(silver_table)

    if action == "agregar":
        if not group_by or not aggregations:
            raise ValueError("Para 'agregar', forneça 'group_by' e 'aggregations'.")
        processor.aggregate_multiple(group_by, aggregations)

    elif action == "query":
        if not query:
            raise ValueError("Para 'query', forneça o parâmetro 'query'.")
        processor.run_query(query)

    elif action == "join":
        if not join_table or not join_columns:
            raise ValueError("Para 'join', forneça 'join_table' e 'join_columns'.")
        processor.join_with_table(join_table, join_columns, join_type)

    else:
        raise ValueError(f"Ação '{action}' não reconhecida. Use 'agregar', 'query' ou 'join'.")

    if columns_to_keep:
        processor.select_columns(columns_to_keep)

    processor.drop_duplicate_columns()

    display(processor.df)
    processor.save_as_delta(gold_table, partition_by if partition_by else None)

except Exception as e:
    import traceback
    traceback.print_exc()
    raise ValueError(f"Error: {e}")