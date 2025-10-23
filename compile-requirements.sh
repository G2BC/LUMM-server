#!/bin/bash
set -e

echo "📦 Compilando requirements.txt... (silencioso)"
pip-compile --no-annotate --resolver=backtracking requirements.in > /dev/null
echo "✅ Pronto."

