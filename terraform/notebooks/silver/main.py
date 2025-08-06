# Databricks notebook source
# COMMAND ----------
# MAGIC %run ./utils/commons.py

# COMMAND ----------
action = dbutils.widgets.get("action")
table = dbutils.widgets.get("table")
storage = dbutils.widgets.get("storage")
column = dbutils.widgets.get("column")
value = dbutils.widgets.get("value")
new_name = dbutils.widgets.get("new_name")
columns = dbutils.widgets.get("columns").split(",") if dbutils.widgets.get("columns") else None
query = dbutils.widgets.get("query")
external = dbutils.widgets.get("external").lower() == "true"
mode = dbutils.widgets.get("mode")
partition_column = dbutils.widgets.get("partition_column")

# COMMAND ----------
try:
    handler = SilverTableHandler(table, storage)

    print(f"Executando ação: {action}")

    if action == 'filter':
        if not column or not value:
            raise ValueError("For 'filter', specify --column e --value")
        df = handler.filter_by_column(column, value)
        display(df)

    elif action == 'select':
        if not columns:
            raise ValueError("For 'select', specify --columns")
        df = handler.selection_columns(columns)
        display(df)

    elif action == 'rename':
        if not column or not new_name:
            raise ValueError("For 'rename', specify --column e --new_name")
        df = handler.renaming_column(column, new_name)
        display(df)

    elif action == 'add_col':
        if not column or not value:
            raise ValueError("For 'add_col', specify --column e --value")
        df = handler.adding_column(column, value)
        display(df)

    elif action == 'query':
        if not query:
            raise ValueError("For 'query', specify --query")
        df = handler.executar_query(query)
        display(df)
    else:
        raise ValueError(f"Unknown action: {action}")

    if 'df' not in locals():
        raise ValueError("No DataFrame was generated to save.")

    handler.save_to_table(
        dataframe=df,
        table_name=table,
        external=external,
        mode=mode,
        partition_column=partition_column
    )
except Exception as e:
    import traceback
    traceback.print_exc()
    raise ValueError(f"Error during execution: {e}")