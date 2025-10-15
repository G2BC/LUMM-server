#!/bin/sh
set -e

if [ "$ENV" = "development" ]; then
  echo "🚀 Starting in development mode..."
  exec python3 -m flask run --host=127.0.0.1 --port=8000
else
  echo "🚀 Starting in production mode..."

  echo "📦 Running database migrations..."
  MIGRATION_OUTPUT=$(flask db upgrade 2>&1)
  MIGRATION_EXIT_CODE=$?
  if [ $MIGRATION_EXIT_CODE -ne 0 ]; then
    echo "$MIGRATION_OUTPUT" | grep -q -i "No migrations to apply"
    if [ $? -eq 0 ]; then
      echo "⚠️ No pending migrations."
    else
      echo "❌ Critical error while running migrations:"
      echo "$MIGRATION_OUTPUT"
      exit $MIGRATION_EXIT_CODE
    fi
  fi

  echo "🌐 Starting Gunicorn..."
  exec gunicorn -w 4 -b 0.0.0.0:4000 wsgi:app
fi
