#!/usr/bin/env bash
# ==============================================================================
# scripts/export_tui_path.sh
# Utilitário para exportar o alias e caminho executável do 'geraldo_tui'
# no PATH do usuário (Linux e macOS).
# ==============================================================================
set -e

ACTION="${1:---install}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." >/dev/null 2>&1 && pwd)"
BIN_DIR="${HOME}/.local/bin"

install_cli() {
    echo "======================================================"
    echo " Configurando atalho 'geraldo_tui' no PATH do terminal"
    echo "======================================================"

    mkdir -p "${BIN_DIR}"

    for cmd_name in "geraldo_tui" "geraldo-tui"; do
        target_file="${BIN_DIR}/${cmd_name}"
        cat << EOF > "${target_file}"
#!/usr/bin/env bash
# Wrapper executável do Geraldo TUI
if [ -f "/Applications/Geraldo.app/Contents/MacOS/geraldo-core" ]; then
    exec "/Applications/Geraldo.app/Contents/MacOS/geraldo-core" --tui "\$@"
elif [ -f "/usr/bin/geraldo-desktop" ]; then
    exec "/usr/bin/geraldo-desktop" --tui "\$@"
elif [ -f "/usr/bin/geraldo" ]; then
    exec "/usr/bin/geraldo" --tui "\$@"
elif [ -f "\$(dirname "\$0")/geraldo-core" ]; then
    exec "\$(dirname "\$0")/geraldo-core" --tui "\$@"
fi

# Ambientes de desenvolvimento / repositório local
CANDIDATES=("${REPO_DIR}" "\$HOME/projects/geraldo" "\$HOME/geraldo" "\$HOME/.local/share/geraldo")
for DIR in "\${CANDIDATES[@]}"; do
    if [ -f "\$DIR/venv/bin/python" ] && [ -f "\$DIR/main.py" ]; then
        exec "\$DIR/venv/bin/python" "\$DIR/main.py" --tui "\$@"
    fi
    if [ -f "\$DIR/venv/bin/python" ] && [ -f "\$DIR/ui/tui.py" ]; then
        PYTHONPATH="\$DIR:\${PYTHONPATH}" exec "\$DIR/venv/bin/python" -m ui.tui "\$@"
    fi
done

if [ -f "./ui/tui.py" ]; then
    if [ -f "./venv/bin/python" ]; then
        exec "./venv/bin/python" -m ui.tui "\$@"
    elif command -v python3 >/dev/null 2>&1; then
        exec python3 -m ui.tui "\$@"
    fi
fi

echo "[Erro] Não foi possível localizar a instalação ou ambiente virtual do Geraldo." >&2
echo "Certifique-se de que o repositório existe em '${REPO_DIR}' com o 'venv' configurado." >&2
exit 1
EOF
        chmod 0755 "${target_file}"
        echo "[OK] Atalho executável criado em: ${target_file}"
    done

    # Atualiza perfis de shell se ~/.local/bin não estiver no PATH
    for rc_file in "${HOME}/.bashrc" "${HOME}/.zshrc" "${HOME}/.profile"; do
        if [ -f "${rc_file}" ]; then
            if ! grep -q '\.local/bin' "${rc_file}"; then
                echo -e "\n# Geraldo TUI CLI PATH\nexport PATH=\"\$HOME/.local/bin:\$PATH\"" >> "${rc_file}"
                echo "[OK] Export adicionado a: ${rc_file}"
            fi
        fi
    done

    echo ""
    echo "✅ Sucesso! O comando 'geraldo_tui' está configurado."
    echo "Para testar no terminal atual execute:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo "  geraldo_tui"
}

uninstall_cli() {
    echo "Removendo atalhos 'geraldo_tui' de ${BIN_DIR}..."
    rm -f "${BIN_DIR}/geraldo_tui" "${BIN_DIR}/geraldo-tui"
    echo "[OK] Removido."
}

status_cli() {
    if command -v geraldo_tui >/dev/null 2>&1 || [ -f "${BIN_DIR}/geraldo_tui" ]; then
        echo "STATUS: INSTALLED"
        which geraldo_tui 2>/dev/null || echo "${BIN_DIR}/geraldo_tui"
    else
        echo "STATUS: NOT_INSTALLED"
    fi
}

case "${ACTION}" in
    --install|-i)
        install_cli
        ;;
    --uninstall|-u)
        uninstall_cli
        ;;
    --status|-s)
        status_cli
        ;;
    *)
        echo "Uso: $0 [--install | --uninstall | --status]"
        exit 1
        ;;
esac
