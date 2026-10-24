#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

VENV_PYTHON="$DIR/venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "[Erro] Interpretador do venv não encontrado em $VENV_PYTHON" >&2
    echo "Execute 'python3 -m venv venv && pip install -r requirements.txt' primeiro." >&2
    exit 1
fi

export PYTHONPATH="$DIR:${PYTHONPATH:-}"

exec "$VENV_PYTHON" ui/tui.py "$@"
