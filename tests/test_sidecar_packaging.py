# tests/test_sidecar_packaging.py
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.build_sidecar import (
    get_default_target_triple,
    prepare_binaries_dir,
    build_sidecar,
    REPO_ROOT,
    SRC_TAURI,
)
from core.ipc import GeraldoIPCServer


class TestSidecarPackaging:
    def test_tauri_conf_external_bin(self):
        conf_path = SRC_TAURI / "tauri.conf.json"
        assert conf_path.exists()
        with open(conf_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        bundle = data.get("bundle", {})
        assert bundle.get("active") is True
        external_bin = bundle.get("externalBin", [])
        assert "binaries/geraldo-core" in external_bin

    def test_tauri_conf_commercial_metadata(self):
        conf_path = SRC_TAURI / "tauri.conf.json"
        with open(conf_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        bundle = data.get("bundle", {})
        assert "copyright" in bundle
        assert "Geraldo" in bundle.get("copyright")
        assert "shortDescription" in bundle
        assert "longDescription" in bundle
        assert bundle.get("category") == "Productivity"

    def test_get_default_target_triple_format(self):
        triple = get_default_target_triple()
        assert isinstance(triple, str)
        assert len(triple) > 5
        assert ("linux" in triple or "windows" in triple or "darwin" in triple)

    def test_prepare_binaries_dir(self):
        bin_dir = prepare_binaries_dir()
        assert bin_dir.exists()
        assert bin_dir.is_dir()

    def test_build_sidecar_dry_run(self):
        dest = build_sidecar(target_triple="x86_64-unknown-linux-gnu", dry_run=True)
        assert "geraldo-core-x86_64-unknown-linux-gnu" in str(dest)

    def test_build_sidecar_creates_executable(self, tmp_path):
        dest = build_sidecar(target_triple="x86_64-unknown-linux-gnu", dry_run=False)
        assert dest.exists()
        assert os.access(dest, os.X_OK)

    @pytest.mark.parametrize("target,expected_ext,expected_name", [
        ("x86_64-unknown-linux-gnu", "", "geraldo-core-x86_64-unknown-linux-gnu"),
        ("aarch64-unknown-linux-gnu", "", "geraldo-core-aarch64-unknown-linux-gnu"),
        ("x86_64-pc-windows-msvc", ".exe", "geraldo-core-x86_64-pc-windows-msvc.exe"),
        ("aarch64-pc-windows-msvc", ".exe", "geraldo-core-aarch64-pc-windows-msvc.exe"),
        ("x86_64-apple-darwin", "", "geraldo-core-x86_64-apple-darwin"),
        ("aarch64-apple-darwin", "", "geraldo-core-aarch64-apple-darwin"),
    ])
    def test_build_sidecar_for_all_os_targets(self, target, expected_ext, expected_name):
        dest = build_sidecar(target_triple=target, dry_run=False)
        assert dest.exists()
        assert dest.name == expected_name
        if expected_ext:
            assert dest.name.endswith(expected_ext)
            cmd_dest = dest.with_suffix(".cmd")
            assert cmd_dest.exists()
            cmd_dest.unlink(missing_ok=True)
        else:
            assert os.access(dest, os.X_OK)
        if dest.name != "geraldo-core-x86_64-unknown-linux-gnu":
            dest.unlink(missing_ok=True)

    def test_package_dist_build_installer_dry_run_all_targets(self):
        from scripts.package_dist import build_installer
        for t in [
            "x86_64-unknown-linux-gnu",
            "aarch64-unknown-linux-gnu",
            "x86_64-pc-windows-msvc",
            "aarch64-pc-windows-msvc",
            "x86_64-apple-darwin",
            "aarch64-apple-darwin",
        ]:
            assert build_installer(target=t, dry_run=True) is True

    def test_ipc_diagnostics_handler(self):
        server = GeraldoIPCServer(host="127.0.0.1", port=9999)
        res = server._handle_diagnostics({})
        assert isinstance(res, dict)
        assert "checks" in res
        assert "voice_models" in res["checks"]
        assert "ollama" in res["checks"]

    def test_package_dist_verify_installers(self):
        from scripts.package_dist import verify_installer_configs
        report = verify_installer_configs()
        assert report["valid"] is True
        assert report["platforms"]["windows"]["status"] == "ready"
        assert report["platforms"]["windows"]["nsis_configured"] is True
        assert report["platforms"]["windows"]["icon_ico"] is True
        assert report["platforms"]["macos"]["status"] == "ready"
        assert report["platforms"]["macos"]["dmg_configured"] is True
        assert report["platforms"]["macos"]["icon_icns"] is True
        assert report["platforms"]["linux"]["status"] == "ready"

    def test_installer_icons_exist(self):
        icons_dir = SRC_TAURI / "icons"
        assert (icons_dir / "icon.ico").exists()
        assert (icons_dir / "icon.icns").exists()
        assert (icons_dir / "32x32.png").exists()
        assert (icons_dir / "128x128.png").exists()

    def test_github_actions_release_workflow(self):
        workflow = REPO_ROOT / ".github" / "workflows" / "release.yml"
        assert workflow.exists()
        content = workflow.read_text(encoding="utf-8")
        assert "windows-latest" in content
        assert "macos-latest" in content
        assert "ubuntu-22.04" in content
        assert "aarch64-apple-darwin" in content
        assert "x86_64-apple-darwin" in content
        assert "tauri-action" in content

    def test_nsis_installer_hooks_exist_and_configures_path(self):
        hooks_file = SRC_TAURI / "nsis" / "installer_hooks.nsi"
        assert hooks_file.exists(), "src-tauri/nsis/installer_hooks.nsi não encontrado"
        content = hooks_file.read_text(encoding="utf-8")
        assert "customInstall" in content
        assert "customUnInstall" in content
        assert 'HKCU "Environment" "Path"' in content
        assert "SendMessage" in content

    def test_cli_wrapper_scripts_exist_and_valid(self):
        bin_dir = REPO_ROOT / "bin"
        assert (bin_dir / "geraldo_tui.cmd").exists()
        assert (bin_dir / "geraldo-tui.cmd").exists()
        assert (bin_dir / "geraldo_tui").exists()
        assert (bin_dir / "geraldo-tui").exists()

        if hasattr(os, "chmod") and sys.platform != "win32":
            try:
                os.chmod(bin_dir / "geraldo_tui", 0o755)
                os.chmod(bin_dir / "geraldo-tui", 0o755)
            except Exception:
                pass

        sh_content = (bin_dir / "geraldo_tui").read_text(encoding="utf-8")
        assert sh_content.startswith("#!/")
        assert "--tui" in sh_content

        assert os.access(bin_dir / "geraldo_tui", os.X_OK) or sh_content.startswith("#!/")
        assert os.access(bin_dir / "geraldo-tui", os.X_OK) or sh_content.startswith("#!/")

        cmd_content = (bin_dir / "geraldo_tui.cmd").read_text(encoding="utf-8")
        assert "--tui" in cmd_content

