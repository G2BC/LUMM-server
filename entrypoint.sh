#!/bin/sh
set -e

if [ "$ENV" = "development" ]; then
  echo "🚀 Starting in development mode..."
  exec uv run flask run --host=0.0.0.0 --port=4000
else
  echo "🚀 Starting in production mode..."
  exec uv run gunicorn -w 4 -b 0.0.0.0:4000 wsgi:app
fi
