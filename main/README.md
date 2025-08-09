# 💠 Provisionamento Automático com Terraform, Azure e Astronomer

Este repositório automatiza o provisionamento de infraestrutura de dados usando **Terraform**, **Azure CLI**, **Docker** e **Astronomer (Airflow)**.

O processo é orquestrado via script `main/init.sh`, que configura o ambiente local de ponta a ponta.

---

## 🚀 O que o script faz

O arquivo [`main/init.sh`](main/init.sh):

1. Autentica via `az login`
2. Inicializa e aplica o Terraform na pasta `terraform/`
3. Exporta os outputs para `.env` e `terraform_outputs.json`
4. Aplica configurações no Airflow via script Python
5. Sobe os containers com Astronomer e Airflow
6. Garante que o Webserver do Airflow está acessível
7. Valida/cria o banco de dados `loccar` no PostgreSQL local (em container)

---

## 🧩 Pré-requisitos

### ✔️ Instalações Necessárias

- [Azure CLI (`az`)](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)
- [Terraform](https://developer.hashicorp.com/terraform/install)
- [Docker](https://www.docker.com/products/docker-desktop/)
- [Astronomer CLI (`astro`)](https://docs.astronomer.io/astro/cli/install-cli)
- [Python 3](https://www.python.org/downloads/)
- [Git](https://git-scm.com/)

---

## ▶️ Como executar localmente

### 1. Clone o repositório

```bash
git clone https://github.com/Jose-Duque/forja-datamaster.git
cd forja-datamaster
```

### 2. Execute o script principal

```bash
./main/init.sh
```

Esse script executa todos os passos automaticamente. Ao final, você verá a mensagem:

```
✅ Ambiente pronto!
🌐 Acesse o Airflow: http://localhost:8080
👤 Usuário: admin | 🔑 Senha: admin
⚠️ A configuração do Connections no Airflow é de forma automática.
```

---

## 🔐 Variáveis exportadas (.env)

O script gera um `.env` com variáveis para uso no ambiente local:

```dotenv
DB_NAME="loccar"
DB_USER="postgres"
DB_PASSWORD="postgres"
DB_HOST="host.docker.internal"
DB_PORT=5432
AZURE_CONNECTION_STRING="..."
AZURE_CONTAINER_NAME="raw"
DATALAKE_NAME="..."
SPN_CLIENT_ID="..."
TENANT_ID="..."
SECRET_SCOPE="..."
SECRET_KEY="..."
```

---

## 📂 Estrutura esperada do projeto

```
.
├── main/
│   └── init.sh                # Script principal de automação
├── dags/                      # DAGs do Airflow
├── airflow_settings.py        # Configura conexões no Airflow
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── ...
├── .env                       # Gerado automaticamente
├── terraform_outputs.json     # Gerado automaticamente
└── Dockerfile, requirements.txt, etc.
```

---

## 🐘 Banco de Dados PostgreSQL

O script detecta automaticamente um container PostgreSQL com nome contendo `postgres`.

- Se o banco `loccar` **já existir**, ele será reutilizado.
- Caso contrário, será criado automaticamente com `psql`.

---

## ✅ Resultado Esperado

Após a execução:

- Infraestrutura provisionada na Azure com Terraform
- Variáveis sensíveis exportadas em `.env` e `terraform_outputs.json`
- Ambiente local com Airflow/Astronomer pronto
- Banco `loccar` criado automaticamente
- Interface acessível em `http://localhost:8080`

---

## Autor

José Duque - Engenheiro de Dados ✨

---

## 📄 Licença

MIT – © 2025 | Provisionamento automatizado com Terraform, Azure e Astronomer