#!/bin/sh
set -e

if [ "$ENV" = "development" ]; then
  echo "🚀 Starting in development mode..."
  exec python3 -m flask run --host=127.0.0.1 --port=8000
else
  echo "🚀 Starting in production mode..."

  echo "📦 Rodando migrações de banco de dados..."
  flask db upgrade || echo "⚠️ Nenhuma migração pendente ou erro leve."

  echo "🌐 Iniciando Gunicorn..."
  exec gunicorn -w 4 -b 0.0.0.0:4000 wsgi:app
fi
