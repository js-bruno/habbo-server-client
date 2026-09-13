#!/usr/bin/env bash
set -e

DB_NAME="habbo"
SCHEMA_FILE="$DEVENV_ROOT/arcturus/base_arcturus.sql"
HOST="127.0.0.1"
PORT="3306"
USER="root"

if [ ! -f "$SCHEMA_FILE" ]; then
  echo "[erro] Schema não encontrado em: $SCHEMA_FILE"
  exit 1
fi

echo "[load-schema] Verificando conexão com MySQL em $HOST:$PORT ..."
if ! mysql -h "$HOST" -P "$PORT" -u "$USER" -e "SELECT 1;" >/dev/null 2>&1; then
  echo "[erro] Não consegui conectar no MySQL. Confirme que 'devenv up' está rodando."
  exit 1
fi

echo "[load-schema] Criando banco '$DB_NAME' se não existir ..."
mysql -h "$HOST" -P "$PORT" -u "$USER" -e "CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

TABLE_COUNT=$(mysql -h "$HOST" -P "$PORT" -u "$USER" -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '$DB_NAME';")

if [ "$TABLE_COUNT" -gt 0 ]; then
  echo "[load-schema] Banco '$DB_NAME' já tem $TABLE_COUNT tabela(s)."
  read -p "Quer reimportar mesmo assim? (digite 'sim'): " confirm
  if [ "$confirm" != "sim" ]; then
    echo "[load-schema] Cancelado."
    exit 0
  fi
fi

echo "[load-schema] Importando $SCHEMA_FILE em '$DB_NAME' ..."
mysql -h "$HOST" -P "$PORT" -u "$USER" "$DB_NAME" < "$SCHEMA_FILE"

FINAL_COUNT=$(mysql -h "$HOST" -P "$PORT" -u "$USER" -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '$DB_NAME';")
echo "[load-schema] Concluído. Banco '$DB_NAME' agora tem $FINAL_COUNT tabela(s)."
