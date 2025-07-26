import json
from pathlib import Path

class Ddl:
    def __init__(self, table):
        self.table = str(table)

    def create_table(self):
        diretorio_atual = Path(__file__).parent / "metadata_table.json"
        
        with open(diretorio_atual.resolve(), "r", encoding="utf-8") as file:
            dados = json.load(file)
            
        colunas = ",\n".join([f"{col} {tipo}" for col, tipo in dados["tabelas"][self.table].items()])
        query = f"""CREATE TABLE IF NOT EXISTS {self.table} ({colunas});"""
        
        return query