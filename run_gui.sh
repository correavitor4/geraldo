#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

# 1. Garante que o serviço do Geraldo esteja rodando se disponível
if command -v systemctl >/dev/null 2>&1; then
    if ! systemctl --user is-active --quiet geraldo.service; then
        echo "[Geraldo] Iniciando serviço em segundo plano (geraldo.service)..."
        systemctl --user start geraldo.service || true
        sleep 1
    fi
fi

# 2. Prioridade 1: Executável nativo compilado Tauri 2.0
if [ -f "$DIR/src-tauri/target/debug/geraldo-desktop" ] && [ -x "$DIR/src-tauri/target/debug/geraldo-desktop" ]; then
    exec "$DIR/src-tauri/target/debug/geraldo-desktop" "$@"
fi

if [ -f "$DIR/src-tauri/target/release/geraldo-desktop" ] && [ -x "$DIR/src-tauri/target/release/geraldo-desktop" ]; then
    exec "$DIR/src-tauri/target/release/geraldo-desktop" "$@"
fi

if command -v geraldo-desktop >/dev/null 2>&1; then
    exec geraldo-desktop "$@"
fi

# 3. Fallback: ui/gui.py via venv Python
VENV_PYTHON="$DIR/venv/bin/python"
if [ -f "$VENV_PYTHON" ]; then
    exec "$VENV_PYTHON" "$DIR/ui/gui.py" "$@"
fi

exec python3 "$DIR/ui/gui.py" "$@"
