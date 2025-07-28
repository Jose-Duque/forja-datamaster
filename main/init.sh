#!/bin/bash

set -e  # Interrompe imediatamente se qualquer comando falhar

INFRA_DIR="infra"

# Passo 2: Autenticação no Azure
echo "🔐 Autenticando na Azure..."
az login

# Passo 3: Exportar variáveis para o Terraform (opcional)
echo "📦 Exportando variáveis de ambiente para Terraform..."

# Passo 4: Inicializar o Terraform
echo "🚀 Inicializando Terraform..."
cd "$INFRA_DIR" || exit 1

echo "🧪 Executando terraform init..."
terraform init || { echo "❌ Erro ao inicializar o Terraform."; exit 1; }

echo "🧠 Criando plano de execução do Terraform..."
terraform plan -out=tfplan || { echo "❌ Erro ao gerar o plano do Terraform."; exit 1; }

echo "⚙️ Aplicando infraestrutura com Terraform..."
terraform apply -auto-approve tfplan || { echo "❌ Erro ao aplicar o plano Terraform."; exit 1; }

echo "📤 Exportando outputs do Terraform..."
terraform output -json > ../terraform_outputs.json || {
  echo "❌ Erro ao salvar outputs do Terraform."; exit 1;
}

# Criar .env com outputs
echo "🔧 Gerando arquivo .env..."
cat <<EOF > ../.env
DB_NAME="loccar"
DB_USER="postgres"
DB_PASSWORD="postgres"
DB_HOST="host.docker.internal"
DB_PORT=5432
AZURE_CONNECTION_STRING="$(terraform output -raw azure_connection_string)"
AZURE_CONTAINER_NAME="raw"
DATALAKE_NAME="$(terraform output -raw storage_account_name)"
SPN_CLIENT_ID="$(terraform output -raw service_principal_client_id)"
TENANT_ID="$(terraform output -raw service_principal_tenant_id)"
SECRET_SCOPE="$(terraform output -raw databricks_secret_scope)"
SECRET_KEY="$(terraform output -raw databricks_secret)"
EOF

cd ..

# Conectar Airflow
echo "⚙️ Aplicando configurações no Airflow..."
python ./airflow_settings.py || {
  echo "❌ Erro ao aplicar configurações no Airflow."; exit 1;
}

# Astronomer
echo "🚀 Inicializando Astronomer..."
astro dev init || echo "ℹ️ Ambiente Astronomer já inicializado."

echo "🐳 Subindo containers com Astronomer..."
# Iniciar o ambiente local do Astronomer
echo "🔧 Iniciando ambiente local com 'astro dev start'..."
astro dev start --wait 30m

# Aguardar o Airflow Webserver responder na porta 8080
echo "⏳ Aguardando o Airflow Webserver responder em http://localhost:8080 ..."

# Tempo limite de espera (em segundos)
TIMEOUT=180
SLEEP_INTERVAL=5
ELAPSED=0

while ! curl -s http://localhost:8080 > /dev/null; do
  if [ $ELAPSED -ge $TIMEOUT ]; then
    echo "❌ Timeout: O Webserver do Airflow não respondeu após $TIMEOUT segundos."
    exit 1
  fi
  echo "⏱️ Ainda não disponível... aguardando ($ELAPSED s)"
  sleep $SLEEP_INTERVAL
  ELAPSED=$((ELAPSED + SLEEP_INTERVAL))
done

echo "✅ Ambiente pronto! Acesse: http://localhost:8080"

# Fim
echo "✅ Ambiente pronto!"
echo "🌐 Acesse o Airflow: http://localhost:8080"
echo "👤 Usuário: admin | 🔑 Senha: admin"
echo "⚠️ Configure as conexões em Admin > Connections."
echo "🛑 Para parar, use: astro dev stop"

PG_CONTAINER=$(docker ps --filter name=postgres --format "{{.Names}}" | head -n 1)

if [ -z "$PG_CONTAINER" ]; then
  echo "❌ Nenhum container com 'postgres' no nome encontrado."
  echo "ℹ️ Use 'docker ps' para identificar o nome real do container e atualize o script."
  exit 1
fi

echo "✅ Container PostgreSQL encontrado: $PG_CONTAINER"

# Verifica se o banco existe
DB_EXISTS=$(docker exec -e PGPASSWORD=postgres "$PG_CONTAINER" psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='loccar'")

if [ "$DB_EXISTS" = "1" ]; then
  echo "ℹ️ Banco 'loccar' já existe."
else
  echo "🚀 Criando banco 'loccar'..."
  docker exec -e PGPASSWORD=postgres "$PG_CONTAINER" psql -U postgres -c "CREATE DATABASE loccar;"
  echo "✅ Banco 'loccar' criado com sucesso!"
fi