#!/usr/bin/env python3
"""
scripts/build_sidecar.py
Script de automação para congelar e empacotar o daemon do Geraldo
como binário Sidecar multiplataforma para o Tauri 2.0.

Uso:
    python scripts/build_sidecar.py [--dry-run] [--target TRIPLE]
"""
import os
import sys
import shutil
import platform
import subprocess
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_TAURI = REPO_ROOT / "src-tauri"
BINARIES_DIR = SRC_TAURI / "binaries"


def get_default_target_triple() -> str:
    """Detecta a tripla de alvo padrão para a máquina atual."""
    # Tenta consultar o rustc diretamente se disponível
    try:
        proc = subprocess.run(["rustc", "-vV"], capture_output=True, text=True, check=True)
        for line in proc.stdout.splitlines():
            if line.startswith("host:"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass

    # Mapeamento heurístico padrão
    arch = platform.machine().lower()
    if arch in ("x86_64", "amd64"):
        arch_norm = "x86_64"
    elif arch in ("aarch64", "arm64"):
        arch_norm = "aarch64"
    else:
        arch_norm = arch

    system = platform.system().lower()
    if system == "linux":
        return f"{arch_norm}-unknown-linux-gnu"
    elif system == "windows":
        return f"{arch_norm}-pc-windows-msvc"
    elif system == "darwin":
        return f"{arch_norm}-apple-darwin"
    return f"{arch_norm}-unknown-linux-gnu"


def prepare_binaries_dir() -> Path:
    """Garante que a pasta src-tauri/binaries exista."""
    BINARIES_DIR.mkdir(parents=True, exist_ok=True)
    return BINARIES_DIR


def build_sidecar(target_triple: str = None, dry_run: bool = False) -> Path:
    """
    Compila ou prepara o executável sidecar geraldo-core-<triple>.
    Se pyinstaller estiver instalado no ambiente, gera o binário compilado.
    Caso contrário, gera o runner executável de desenvolvimento.
    """
    triple = target_triple or get_default_target_triple()
    prepare_binaries_dir()

    is_windows = "windows" in triple
    ext = ".exe" if is_windows else ""
    dest_binary_name = f"geraldo-core-{triple}{ext}"
    dest_path = BINARIES_DIR / dest_binary_name

    print(f"[Build Sidecar] Alvo detectado: {triple}")
    print(f"[Build Sidecar] Arquivo de destino: {dest_path}")

    if dry_run:
        print("[Build Sidecar] Modo dry-run: nenhuma alteração gravada.")
        return dest_path

    # Verifica se pyinstaller está disponível
    has_pyinstaller = shutil.which("pyinstaller") is not None
    if not has_pyinstaller:
        venv_pyinstaller = REPO_ROOT / "venv" / "bin" / "pyinstaller"
        if venv_pyinstaller.exists():
            has_pyinstaller = True

    host_system = platform.system().lower()
    target_system = "windows" if "windows" in triple else ("darwin" if ("darwin" in triple or "apple" in triple) else "linux")
    
    host_arch = "x86_64" if platform.machine().lower() in ("x86_64", "amd64") else "aarch64"
    target_arch = "aarch64" if ("aarch64" in triple or "arm64" in triple) else "x86_64"

    can_use_pyinstaller = False
    if has_pyinstaller and host_system == target_system and not os.getenv("PYTEST_CURRENT_TEST"):
        if host_system == "darwin":
            can_use_pyinstaller = True
        elif host_arch == target_arch:
            can_use_pyinstaller = True

    # Injeta credenciais padrão se fornecidas via variável de ambiente no CI
    default_key = os.getenv("GEMINI_API_KEY") or os.getenv("DEFAULT_LLM_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("LLM_API_KEY")
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    bundled_file = REPO_ROOT / "_bundled_defaults.json"
    if (default_key or client_id or client_secret) and not bundled_file.exists():
        import json
        bundled_data = {}
        if default_key:
            bundled_data["llm_api_key"] = default_key.strip()
            if default_key.startswith("AIzaSy"):
                bundled_data["llm_provider"] = "gemini"
                bundled_data["llm_model"] = "gemini-2.5-flash"
                bundled_data["llm_api_base"] = "https://generativelanguage.googleapis.com/v1beta/openai"
        if client_id:
            bundled_data["google_client_id"] = client_id
        if client_secret:
            bundled_data["google_client_secret"] = client_secret
        try:
            with open(bundled_file, "w", encoding="utf-8") as f:
                json.dump(bundled_data, f, indent=2)
            print("[Build Sidecar] Configurações de API e OAuth padrão embutidas no build com sucesso.")
        except Exception as e:
            print(f"[Build Sidecar] Aviso ao gerar _bundled_defaults.json: {e}")

    if can_use_pyinstaller:
        print(f"[Build Sidecar] PyInstaller detectado para {host_system} {host_arch}. Congelando daemon Python...")
        build_dir = REPO_ROOT / "build" / "sidecar"
        dist_dir = REPO_ROOT / "dist" / "sidecar"
        
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--name", "geraldo-core",
            "--distpath", str(dist_dir),
            "--workpath", str(build_dir),
        ]
        if bundled_file.exists():
            cmd.extend(["--add-data", f"{bundled_file}{os.pathsep}."])
        cmd.append(str(REPO_ROOT / "main.py"))

        if "apple-darwin" in triple and platform.system().lower() == "darwin":
            if "x86_64" in triple:
                cmd.extend(["--target-arch", "x86_64"])
            elif "aarch64" in triple or "arm64" in triple:
                cmd.extend(["--target-arch", "arm64"])
        
        try:
            subprocess.run(cmd, check=True)
            src_binary = dist_dir / ("geraldo-core.exe" if is_windows else "geraldo-core")
            if src_binary.exists():
                shutil.copy2(src_binary, dest_path)
                print(f"[Build Sidecar] Sucesso! Binário congelado copiado para: {dest_path}")
                return dest_path
        except Exception as e:
            if os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true":
                print(f"[Build Sidecar] ERRO CRÍTICO no CI: compilação com PyInstaller falhou ({e}). Abortando build para evitar gerar instalador incompleto.")
                raise e
            print(f"[Build Sidecar] Aviso: compilação com PyInstaller falhou ({e}). Gerando runner nativo...")
    else:
        if os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true":
            raise RuntimeError(f"[Build Sidecar] ERRO CRÍTICO no CI: PyInstaller indisponível ou arquitetura incompatível ('{triple}' a partir de '{host_system}-{host_arch}').")
        print(f"[Build Sidecar] Compilando para alvo '{triple}' a partir de host '{host_system}-{host_arch}'. Gerando runner nativo...")

    # Fallback / Modo Desenvolvimento: Gera um launcher executável padrão
    print("[Build Sidecar] Gerando launcher executável para sidecar...")
    if is_windows:
        # Script batch/cmd executável no Windows
        launcher_content = f"""@echo off
set REPO_DIR=%~dp0..\\..
if exist "%REPO_DIR%\\main.py" (
    set TARGET_DIR=%REPO_DIR%
) else if exist "%USERPROFILE%\\projects\\geraldo\\main.py" (
    set TARGET_DIR=%USERPROFILE%\\projects\\geraldo
) else if exist "%USERPROFILE%\\geraldo\\main.py" (
    set TARGET_DIR=%USERPROFILE%\\geraldo
) else (
    set TARGET_DIR=%REPO_DIR%
)
if exist "%TARGET_DIR%\\venv\\Scripts\\python.exe" (
    call "%TARGET_DIR%\\venv\\Scripts\\python.exe" "%TARGET_DIR%\\main.py" %*
) else (
    python "%TARGET_DIR%\\main.py" %*
)
"""
        cmd_path = dest_path.with_suffix(".cmd")
        with open(cmd_path, "w", encoding="utf-8") as f:
            f.write(launcher_content)
        # Cria cópia .exe ou mantém o launcher
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(launcher_content)
    else:
        # Script Shell executável padrão POSIX (Linux/macOS)
        launcher_content = f"""#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." >/dev/null 2>&1 && pwd)"
CANDIDATES=("$DIR" "$HOME/projects/geraldo" "$HOME/geraldo" "$HOME/.local/share/geraldo")
TARGET_DIR=""
for c in "${{CANDIDATES[@]}}"; do
    if [ -f "$c/main.py" ]; then
        TARGET_DIR="$c"
        break
    fi
done

if [ -n "$TARGET_DIR" ]; then
    PYTHON_EXEC="$TARGET_DIR/venv/bin/python"
    if [ ! -f "$PYTHON_EXEC" ]; then
        PYTHON_EXEC="python3"
    fi
    exec "$PYTHON_EXEC" -u "$TARGET_DIR/main.py" "$@"
fi

if [ -f "$DIR/venv/bin/python" ]; then
    PYTHON_EXEC="$DIR/venv/bin/python"
else
    PYTHON_EXEC="python3"
fi
exec "$PYTHON_EXEC" -u "$DIR/main.py" "$@"
"""
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(launcher_content)
        dest_path.chmod(0o755)

    # Copia wrappers CLI do geraldo_tui para a pasta de binarios do Tauri
    bin_dir = REPO_ROOT / "bin"
    for name in ("geraldo_tui.cmd", "geraldo-tui.cmd", "geraldo_tui", "geraldo-tui"):
        src = bin_dir / name
        if src.exists():
            shutil.copy2(src, BINARIES_DIR / name)

    print(f"[Build Sidecar] Sidecar executável pronto em: {dest_path}")
    return dest_path


def main():
    parser = argparse.ArgumentParser(description="Build and package Geraldo daemon as a Tauri sidecar.")
    parser.add_argument("--target", default=None, help="Target triple (e.g. x86_64-unknown-linux-gnu)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without building")
    args = parser.parse_args()

    dest = build_sidecar(target_triple=args.target, dry_run=args.dry_run)
    print(f"OK: {dest}")


if __name__ == "__main__":
    main()
