# tests/test_sidecar_packaging.py
import json
import os
from pathlib import Path
from unittest.mock import patch

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

    def test_ipc_diagnostics_handler(self):
        server = GeraldoIPCServer(host="127.0.0.1", port=9999)
        res = server._handle_diagnostics({})
        assert isinstance(res, dict)
        assert "checks" in res
        assert "voice_models" in res["checks"]
        assert "ollama" in res["checks"]
