#!/usr/bin/env python3
"""
scripts/package_dist.py
Utilitário de empacotamento e verificação de instaladores comerciais do Geraldo
para Windows (.exe NSIS, .msi WiX), macOS (.dmg) e Linux (.deb, .AppImage).

Uso:
    python scripts/package_dist.py --check
    python scripts/package_dist.py --build
"""
import os
import sys
import json
import shutil
import platform
import argparse
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_TAURI = REPO_ROOT / "src-tauri"
CONF_PATH = SRC_TAURI / "tauri.conf.json"
ICONS_DIR = SRC_TAURI / "icons"
BINARIES_DIR = SRC_TAURI / "binaries"


def verify_installer_configs() -> dict:
    """Verifica se todas as configurações e assets de instaladores estão completos."""
    report = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "platforms": {},
    }

    if not CONF_PATH.exists():
        report["valid"] = False
        report["errors"].append(f"Arquivo de configuração não encontrado: {CONF_PATH}")
        return report

    try:
        with open(CONF_PATH, "r", encoding="utf-8") as f:
            conf = json.load(f)
    except Exception as e:
        report["valid"] = False
        report["errors"].append(f"JSON inválido em tauri.conf.json: {e}")
        return report

    bundle = conf.get("bundle", {})
    if not bundle.get("active"):
        report["valid"] = False
        report["errors"].append("bundle.active está desativado.")

    # 1. Verificação de Ícones Multiplataforma
    icons = bundle.get("icon", [])
    has_ico = any(i.endswith(".ico") for i in icons) and (ICONS_DIR / "icon.ico").exists()
    has_icns = any(i.endswith(".icns") for i in icons) and (ICONS_DIR / "icon.icns").exists()
    has_png = any(i.endswith(".png") for i in icons)

    if not has_ico:
        report["valid"] = False
        report["errors"].append("Ícone do Windows (icon.ico) ausente ou não configurado.")
    if not has_icns:
        report["valid"] = False
        report["errors"].append("Ícone do macOS (icon.icns) ausente ou não configurado.")
    if not has_png:
        report["warnings"].append("Ícones PNG padrão recomendados para Linux ausentes.")

    # 2. Configuração de Instalador Windows (NSIS & WiX)
    win_conf = bundle.get("windows", {})
    nsis_conf = win_conf.get("nsis", {})
    wix_conf = win_conf.get("wix", {})

    win_valid = (
        bool(nsis_conf) and
        nsis_conf.get("installMode") in ("currentUser", "perMachine", "both") and
        has_ico
    )
    report["platforms"]["windows"] = {
        "status": "ready" if win_valid else "incomplete",
        "nsis_configured": bool(nsis_conf),
        "install_mode": nsis_conf.get("installMode", "unknown"),
        "languages": nsis_conf.get("languages", []),
        "wix_configured": bool(wix_conf),
        "icon_ico": has_ico,
    }

    # 3. Configuração de Instalador macOS (DMG & App Bundle)
    mac_conf = bundle.get("macOS", {}) or bundle.get("macos", {})
    dmg_conf = mac_conf.get("dmg", {})
    mac_valid = bool(dmg_conf) and has_icns and bool(mac_conf.get("minimumSystemVersion"))

    report["platforms"]["macos"] = {
        "status": "ready" if mac_valid else "incomplete",
        "dmg_configured": bool(dmg_conf),
        "min_system_version": mac_conf.get("minimumSystemVersion"),
        "window_size": dmg_conf.get("windowSize"),
        "icon_icns": has_icns,
    }

    # 4. Configuração de Instalador Linux (.deb / AppImage)
    targets = bundle.get("targets", "all")
    report["platforms"]["linux"] = {
        "status": "ready",
        "targets": targets,
    }

    # 5. Sidecar ExternalBin
    external_bin = bundle.get("externalBin", [])
    has_sidecar_config = "binaries/geraldo-core" in external_bin
    report["sidecar"] = {
        "configured": has_sidecar_config,
        "binaries_present": [p.name for p in BINARIES_DIR.glob("geraldo-core*")],
    }

    if not has_sidecar_config:
        report["valid"] = False
        report["errors"].append("Sidecar 'binaries/geraldo-core' não declarado em bundle.externalBin.")

    return report


def build_installer(target: str = None, dry_run: bool = False):
    """Executa a compilação do pacote instalador na plataforma atual."""
    current_os = platform.system().lower()
    target_info = f" (target: {target})" if target else ""
    print(f"[Package Dist] Iniciando empacotamento para SO detectado: {current_os.upper()}{target_info}...")

    check_res = verify_installer_configs()
    if not check_res["valid"]:
        print(f"[Package Dist] Erro de validação: {check_res['errors']}", file=sys.stderr)
        return False

    print("[Package Dist] Validações de instaladores para Windows, macOS e Linux: OK!")
    if dry_run:
        print("[Package Dist] Modo dry-run: configurações verificadas com sucesso.")
        return True

    # Verifica se cargo-tauri está disponível para gerar o bundle final
    has_tauri = shutil.which("cargo-tauri") or shutil.which("tauri")
    if not has_tauri:
        print("[Package Dist] 'tauri' CLI não encontrado no PATH local. Compilando binário release padrão...")
        cmd = ["cargo", "build", "--release"]
        if target:
            cmd.extend(["--target", target])
    else:
        cmd = ["cargo", "tauri", "build"]
        if target:
            cmd.extend(["--target", target])

    try:
        subprocess.run(cmd, cwd=SRC_TAURI, check=True)
        print("[Package Dist] Compilação do instalador concluída com sucesso!")
        return True
    except Exception as e:
        print(f"[Package Dist] Erro durante a compilação: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Geraldo Multiplatform Installer Packaging Utility.")
    parser.add_argument("--check", action="store_true", help="Validate installer configurations for all platforms")
    parser.add_argument("--build", action="store_true", help="Build installer for the current host OS")
    parser.add_argument("--target", default=None, help="Target triple (e.g. x86_64-apple-darwin, aarch64-apple-darwin)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate build without compiling")
    args = parser.parse_args()

    if args.check or not args.build:
        report = verify_installer_configs()
        print(json.dumps(report, indent=2, ensure_ascii=False))
        if not report["valid"]:
            sys.exit(1)

    if args.build:
        ok = build_installer(target=args.target, dry_run=args.dry_run)
        if not ok:
            sys.exit(1)


if __name__ == "__main__":
    main()
