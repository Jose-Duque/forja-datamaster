import json
import os

class TerraformOutputManager:
    def __init__(self, output_file: str = "terraform_outputs.json"):
        self.output_file = output_file
        self.outputs = {}
        self._load_outputs()

    def _load_outputs(self):
        """
        Carrega os outputs do Terraform a partir de um arquivo JSON.
        Caso o arquivo não exista ou esteja inválido, exibe mensagens de erro e mantém os outputs vazios.
        """
        if not os.path.exists(self.output_file):
            print(f"Erro: O arquivo '{self.output_file}' não foi encontrado.")
            print("Certifique-se de ter executado 'terraform output -json > {self.output_file}' no diretório do seu projeto Terraform.")
            self.outputs = {}
            return

        try:
            with open(self.output_file, 'r') as f:
                self.outputs = json.load(f)
            print(f"Outputs do Terraform carregados com sucesso de '{self.output_file}'.")
            print(json.dumps(self.outputs, indent=2))
        except json.JSONDecodeError:
            print(f"Erro: Não foi possível decodificar o arquivo '{self.output_file}' como JSON.")
            print("Verifique se o conteúdo do arquivo está em um formato JSON válido.")
            self.outputs = {}
        except Exception as e:
            print(f"Ocorreu um erro inesperado ao carregar os outputs: {e}")
            self.outputs = {}

    def get_output(self, key: str, default=None):
        """Obtém um output específico do Terraform pelo nome da chave."""
        if key in self.outputs:
            return self.outputs[key].get("value", default)
        else:
            print(f"Aviso: Output '{key}' não encontrado no arquivo '{self.output_file}'.")
            return default

    def get_all_outputs(self) -> dict:
        """ Retorna todos os outputs simplificados (apenas chave e valor, sem metadados)."""
        simplified_outputs = {}
        for key, details in self.outputs.items():
            if "value" in details:
                simplified_outputs[key] = details["value"]
        return simplified_outputs

    def is_loaded(self) -> bool:
        return bool(self.outputs)