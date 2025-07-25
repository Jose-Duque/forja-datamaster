import json
from pathlib import Path

class Ddl:
    def __init__(self, table):
        self.table = str(table)
        # self.column_type = dict(column_type)

    def create_table(self):
        diretorio_atual = Path(__file__).parent / "column_type.json"
        
        with open(diretorio_atual.resolve(), "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
            
        colunas = ",\n".join([f"{col} {tipo}" for col, tipo in dados["tabelas"][self.table].items()])
        query = f"""CREATE TABLE IF NOT EXISTS {self.table} ({colunas});"""
        
        return query