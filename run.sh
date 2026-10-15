#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

VENV_PYTHON="$DIR/venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "[Erro] Interpretador do venv não encontrado em $VENV_PYTHON" >&2
    exit 1
fi

# Executa diretamente o Python do venv com stdout/stderr em tempo real
exec "$VENV_PYTHON" -u main.py

