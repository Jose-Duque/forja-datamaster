import json
from pathlib import Path

class Dml:
    def __init__(self, table):
        self.table = str(table)
    
    def insert_table(self):
        diretorio_atual = Path(__file__).parent / "insert.json"
        
        with open(diretorio_atual.resolve(), "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
            
        _values = ",\n".join([str(tuple(i)) for i in dados[self.table]])
        query = f""" INSERT INTO {self.table} VALUES {_values}; """
        return query