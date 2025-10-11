#!/bin/sh
set -e

if [ "$ENV" = "development" ]; then
  echo "Starting in development mode..."
  exec python3 -m flask run --host=0.0.0.0 --port=8000
else
  echo "Starting in production mode..."
  exec gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app
fi
