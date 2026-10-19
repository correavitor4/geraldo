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

    if has_pyinstaller:
        print("[Build Sidecar] PyInstaller detectado. Congelando daemon Python...")
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
            str(REPO_ROOT / "main.py")
        ]
        
        try:
            subprocess.run(cmd, check=True)
            src_binary = dist_dir / ("geraldo-core.exe" if is_windows else "geraldo-core")
            if src_binary.exists():
                shutil.copy2(src_binary, dest_path)
                print(f"[Build Sidecar] Sucesso! Binário congelado copiado para: {dest_path}")
                return dest_path
        except Exception as e:
            print(f"[Build Sidecar] Aviso: compilação com PyInstaller falhou ({e}). Gerando runner nativo...")

    # Fallback / Modo Desenvolvimento: Gera um launcher executável padrão
    print("[Build Sidecar] Gerando launcher executável para sidecar...")
    if is_windows:
        # Script batch/cmd executável no Windows
        launcher_content = f"""@echo off
set REPO_DIR=%~dp0..\\..
call "%REPO_DIR%\\venv\\Scripts\\python.exe" "%REPO_DIR%\\main.py" %*
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
PYTHON_EXEC="$DIR/venv/bin/python"
if [ ! -f "$PYTHON_EXEC" ]; then
    PYTHON_EXEC="python3"
fi
exec "$PYTHON_EXEC" -u "$DIR/main.py" "$@"
"""
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(launcher_content)
        dest_path.chmod(0o755)

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
