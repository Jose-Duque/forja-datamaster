import os
from io import StringIO
import psycopg2
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from azure.storage.blob import BlobServiceClient
import logging
from datetime import datetime

class ExtractDbSaveToAzure:
    def __init__(self, db_config, azure_config):
        self.db_config = db_config
        self.azure_config = azure_config
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        
        # Configuração do logger
        logging.basicConfig(
            filename="app.log",
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    def log_message(self, level, message):        
        formatted_message = f"{self.timestamp} - {message}"
        
        if level == "info":
            logging.info(formatted_message)
        elif level == "warning":
            logging.warning(formatted_message)
        elif level == "error":
            logging.error(formatted_message)
        elif level == "critical":
            logging.critical(formatted_message)
        
        print(formatted_message)

    def extract_data(self, table_name):
        """Extrai dados do PostgreSQL."""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {table_name}")
            data = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            cursor.close()
            conn.close()
            self.log_message("info", f"Dados extraídos da tabela {table_name} com sucesso!")
            return data, column_names
        except psycopg2.OperationalError as e:
            self.log_message("error", f"Erro de conexão com o banco: {e}")
        except psycopg2.Error as e:
            self.log_message("error", f"Erro ao executar a query: {e}")
        return None, None

    def save_to_azure(self, data, column_names, table_name):
        """Salva os dados no Azure Blob Storage em formato CSV com cabeçalho."""
        try:
            if data is None or column_names is None:
                self.log_message("warning", "Nenhum dado foi extraído. Salvamento abortado.")
                return

            # Cria conexão com o Blob Storage
            blob_service_client = BlobServiceClient.from_connection_string(self.azure_config["connection_string"])
            container_client = blob_service_client.get_container_client(self.azure_config["container_name"])
            blob_client = container_client.get_blob_client(f"{table_name}/{self.timestamp}.csv")

            # Cria DataFrame e converte para CSV (com header)
            df = pd.DataFrame(data=data, columns=column_names)
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False)

            # Faz upload para o Azure Blob Storage
            blob_client.upload_blob(csv_buffer.getvalue(), overwrite=True)
            self.log_message("info", f"Arquivo {table_name}/{self.timestamp}.csv enviado para o Azure com sucesso!")

        except Exception as e:
            raise Exception(self.log_message("error", f"Erro ao salvar os dados no Azure: {e}"))

    def run_pipeline(self, table_name):
        """Executa a extração e envio dos dados."""
        self.log_message("info", f"Iniciando pipeline para a tabela {table_name}...")
        data, column_names = self.extract_data(table_name)
        self.save_to_azure(data, column_names, table_name)
        self.log_message("info", f"Pipeline finalizado para a tabela {table_name}.")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    db_config = {
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT")
    }

    azure_config = {
        "connection_string": os.getenv("AZURE_CONNECTION_STRING"),
        "container_name": os.getenv("AZURE_CONTAINER_NAME")
    }
    
    # Criando e executando a pipeline
    pipeline = ExtractDbSaveToAzure(db_config, azure_config)
    pipeline.run_pipeline("cidades")


    # SECRET_KEY=mysecret
    # DATABASE_URL=mysql://user:password@localhost/db
    # connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")


    # import os

    # load_dotenv()  # Carrega as variáveis do arquivo .env

    # secret_key = os.getenv("SECRET_KEY")
    # db_url = os.getenv("DATABASE_URL")

    # print(secret_key)  # mysecret
    # print(db_url)  # mysql://user:password@localhost/db
    # import os

    # secret_key = os.getenv("SECRET_KEY")
    # print(secret_key)

    
