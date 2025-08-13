# Databricks notebook source
# COMMAND ----------
# MAGIC %run ./utils/commons.py

# COMMAND ----------
silver_table = dbutils.widgets.get("silver_table")
gold_table = dbutils.widgets.get("gold_table")
action = dbutils.widgets.get("action").lower()
group_by = [col.strip() for col in dbutils.widgets.get("group_by").split(",") if col.strip()]
aggregations_input = dbutils.widgets.get("aggregations_input")
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
    processor = GoldTableProcessor(silver_table)

    if action == "agregar":
        if not group_by or not aggregations:
            raise ValueError("For 'aggregate', provide 'group_by' and 'aggregations'.")
        processor.aggregate_multiple(group_by, aggregations)

    elif action == "query":
        if not query:
            raise ValueError("For 'query', provide the 'query' parameter.")
        processor.run_query(query)

    elif action == "join":
        if not join_table or not join_columns:
            raise ValueError("For 'join', provide 'join_table' and 'join_columns'.")
        processor.join_with_table(join_table, join_columns, join_type)

    else:
        raise ValueError(f"Action '{action}' unrecognized. Use 'aggregate', 'query', or 'join'.")

    if columns_to_keep:
        processor.select_columns(columns_to_keep)

    processor.drop_duplicate_columns()

    display(processor.df)
    processor.save_as_delta(gold_table, partition_by if partition_by else None)

except Exception as e:
    import traceback
    traceback.print_exc()
    raise ValueError(f"Error: {e}")