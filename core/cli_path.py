"""
core/cli_path.py
Gerenciamento cross-platform do atalho de terminal e exportação de PATH do Geraldo TUI
Compatível com Linux, macOS e Windows.
"""

import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Dict, Any


def get_platform_name() -> str:
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    if system == "windows":
        return "windows"
    return "linux"


def get_tui_path_status() -> Dict[str, Any]:
    """
    Verifica se o comando geraldo_tui está instalado e acessível no PATH do sistema.
    """
    plat = get_platform_name()
    which_cmd = shutil.which("geraldo_tui") or shutil.which("geraldo-tui")
    
    if plat == "windows":
        local_app_data = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        windows_apps = Path(local_app_data) / "Microsoft" / "WindowsApps" / "geraldo_tui.cmd"
        geraldo_bin = Path(local_app_data) / "Geraldo" / "bin" / "geraldo_tui.cmd"
        
        installed = windows_apps.exists() or geraldo_bin.exists() or (which_cmd is not None)
        cli_path = str(which_cmd) if which_cmd else (str(windows_apps) if windows_apps.exists() else str(geraldo_bin))
        in_path = which_cmd is not None
        
        return {
            "status": "ok",
            "os": plat,
            "installed": installed,
            "in_path": in_path,
            "cli_path": cli_path,
            "message": "Atalho geraldo_tui configurado no PATH" if in_path else ("Arquivo criado mas terminal precisa reiniciar" if installed else "Atalho não configurado")
        }
    else:
        home = Path.home()
        local_bin = home / ".local" / "bin"
        target_script = local_bin / "geraldo_tui"
        
        installed = target_script.exists()
        in_path = which_cmd is not None
        
        return {
            "status": "ok",
            "os": plat,
            "installed": installed,
            "in_path": in_path,
            "cli_path": str(target_script) if installed else (str(which_cmd) if which_cmd else ""),
            "message": "Atalho geraldo_tui configurado no PATH" if in_path else ("Instalado em ~/.local/bin (recarregue o terminal)" if installed else "Atalho não configurado")
        }


def export_tui_path() -> Dict[str, Any]:
    """
    Instala e configura o wrapper executável 'geraldo_tui' e atualiza o PATH do usuário.
    Funciona no Windows, Linux e macOS.
    """
    plat = get_platform_name()
    home = Path.home()
    
    if plat == "windows":
        local_app_data = os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local"))
        geraldo_dir = Path(local_app_data) / "Geraldo" / "bin"
        geraldo_dir.mkdir(parents=True, exist_ok=True)
        
        repo_dir = str(Path(__file__).resolve().parent.parent)
        batch_content = (
            "@echo off\r\n"
            "REM Wrapper executável do Geraldo TUI para Windows\r\n"
            "if exist \"%LOCALAPPDATA%\\Programs\\Geraldo\\Geraldo.exe\" (\r\n"
            "    start \"\" \"%LOCALAPPDATA%\\Programs\\Geraldo\\Geraldo.exe\" --tui %*\r\n"
            "    goto :eof\r\n"
            ")\r\n"
            "if exist \"%ProgramFiles%\\Geraldo\\Geraldo.exe\" (\r\n"
            "    start \"\" \"%ProgramFiles%\\Geraldo\\Geraldo.exe\" --tui %*\r\n"
            "    goto :eof\r\n"
            ")\r\n"
            f"if exist \"{repo_dir}\\venv\\Scripts\\python.exe\" (\r\n"
            f"    \"{repo_dir}\\venv\\Scripts\\python.exe\" \"{repo_dir}\\main.py\" --tui %*\r\n"
            "    goto :eof\r\n"
            ")\r\n"
            "if exist \"%USERPROFILE%\\projects\\geraldo\\venv\\Scripts\\python.exe\" (\r\n"
            "    \"%USERPROFILE%\\projects\\geraldo\\venv\\Scripts\\python.exe\" \"%USERPROFILE%\\projects\\geraldo\\main.py\" --tui %*\r\n"
            "    goto :eof\r\n"
            ")\r\n"
            "python -m ui.tui %*\r\n"
        )
        
        created_paths = []
        # 1. Cria em %LOCALAPPDATA%\Geraldo\bin
        cmd_file = geraldo_dir / "geraldo_tui.cmd"
        cmd_file.write_text(batch_content, encoding="utf-8")
        created_paths.append(str(cmd_file))
        
        # 2. Copia para %LOCALAPPDATA%\Microsoft\WindowsApps (já presente no PATH padrão do Windows 10/11)
        win_apps = Path(local_app_data) / "Microsoft" / "WindowsApps"
        if win_apps.exists():
            win_apps_cmd = win_apps / "geraldo_tui.cmd"
            try:
                win_apps_cmd.write_text(batch_content, encoding="utf-8")
                created_paths.append(str(win_apps_cmd))
            except Exception:
                pass
                
        # 3. Adiciona ao registro HKCU\Environment se possível
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE)
            try:
                curr_path, _ = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                curr_path = ""
            if str(geraldo_dir) not in curr_path:
                new_path = f"{curr_path};{geraldo_dir}" if curr_path else str(geraldo_dir)
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
            winreg.CloseKey(key)
        except Exception:
            pass
            
        return {
            "status": "ok",
            "os": "windows",
            "installed": True,
            "created_paths": created_paths,
            "message": f"Atalho 'geraldo_tui.cmd' configurado com sucesso em: {', '.join(created_paths)}"
        }

    else:
        # Linux e macOS
        local_bin = home / ".local" / "bin"
        local_bin.mkdir(parents=True, exist_ok=True)
        repo_dir = str(Path(__file__).resolve().parent.parent)
        
        script_content = (
            "#!/usr/bin/env bash\n"
            "# Wrapper executável do Geraldo TUI\n"
            'if [ -f "/Applications/Geraldo.app/Contents/MacOS/geraldo-core" ]; then\n'
            '    exec "/Applications/Geraldo.app/Contents/MacOS/geraldo-core" --tui "$@"\n'
            'elif [ -f "/usr/bin/geraldo-desktop" ]; then\n'
            '    exec "/usr/bin/geraldo-desktop" --tui "$@"\n'
            'elif [ -f "/usr/bin/geraldo" ]; then\n'
            '    exec "/usr/bin/geraldo" --tui "$@"\n'
            'elif [ -f "$(dirname "$0")/geraldo-core" ]; then\n'
            '    exec "$(dirname "$0")/geraldo-core" --tui "$@"\n'
            "fi\n\n"
            "# Ambientes de desenvolvimento / repositório local\n"
            f'CANDIDATES=("{repo_dir}" "$HOME/projects/geraldo" "$HOME/geraldo" "$HOME/.local/share/geraldo")\n'
            'for DIR in "${CANDIDATES[@]}"; do\n'
            '    if [ -f "$DIR/venv/bin/python" ] && [ -f "$DIR/main.py" ]; then\n'
            '        exec "$DIR/venv/bin/python" "$DIR/main.py" --tui "$@"\n'
            '    fi\n'
            '    if [ -f "$DIR/venv/bin/python" ] && [ -f "$DIR/ui/tui.py" ]; then\n'
            '        PYTHONPATH="$DIR:${PYTHONPATH}" exec "$DIR/venv/bin/python" -m ui.tui "$@"\n'
            '    fi\n'
            "done\n\n"
            "# Fallback se executado dentro da pasta do repositório\n"
            'if [ -f "./ui/tui.py" ]; then\n'
            '    if [ -f "./venv/bin/python" ]; then\n'
            '        exec "./venv/bin/python" -m ui.tui "$@"\n'
            '    elif command -v python3 >/dev/null 2>&1; then\n'
            '        exec python3 -m ui.tui "$@"\n'
            '    fi\n'
            "fi\n\n"
            'echo "[Erro] Não foi possível localizar a instalação ou ambiente virtual do Geraldo." >&2\n'
            f'echo "Certifique-se de que o repositório existe em \'{repo_dir}\' com o \'venv\' configurado." >&2\n'
            "exit 1\n"
        )
        
        created_paths = []
        for cmd_name in ("geraldo_tui", "geraldo-tui"):
            target = local_bin / cmd_name
            target.write_text(script_content, encoding="utf-8")
            os.chmod(target, 0o755)
            created_paths.append(str(target))
            
        # Atualiza perfis de shell se necessário
        rc_files = [home / ".bashrc", home / ".zshrc", home / ".profile"]
        updated_rcs = []
        for rc in rc_files:
            if rc.exists():
                try:
                    content = rc.read_text(encoding="utf-8", errors="ignore")
                    if ".local/bin" not in content and "geraldo_tui" not in content:
                        with rc.open("a", encoding="utf-8") as f:
                            f.write("\n# Geraldo TUI CLI PATH\nexport PATH=\"$HOME/.local/bin:$PATH\"\n")
                        updated_rcs.append(rc.name)
                except Exception:
                    pass
                    
        return {
            "status": "ok",
            "os": plat,
            "installed": True,
            "created_paths": created_paths,
            "updated_profiles": updated_rcs,
            "message": f"Atalho 'geraldo_tui' criado em {local_bin}. Profiles atualizados: {', '.join(updated_rcs) if updated_rcs else 'PATH já configurado'}."
        }
