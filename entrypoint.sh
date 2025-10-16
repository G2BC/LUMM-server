#!/bin/sh
set -e

if [ "$ENV" = "development" ]; then
  echo "🚀 Starting in development mode..."
  exec python3 -m flask run --host=127.0.0.1 --port=4000
else
  echo "🚀 Starting in production mode..."
  exec gunicorn -w 4 -b 0.0.0.0:4000 wsgi:app
fi
