import json
from pathlib import Path

class Dml:
    def __init__(self, table):
        self.table = str(table)
    
    def insert_table(self):
        diretorio_atual = Path(__file__).parent / "values_tables.json"
        
        with open(diretorio_atual.resolve(), "r", encoding="utf-8") as file:
            dados = json.load(file)
            
        _values = ",\n".join([str(tuple(i)) for i in dados[self.table]])
        query = f""" INSERT INTO {self.table} VALUES {_values}; """
        return query