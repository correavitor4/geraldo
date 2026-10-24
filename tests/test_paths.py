# tests/test_paths.py
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from core.paths import (
    is_frozen,
    get_base_dir,
    get_user_data_dir,
    get_temp_dir,
    get_temp_audio_path,
    get_models_search_paths,
    resolve_model_path,
    ensure_model_available,
    get_credentials_path,
    get_token_path,
    get_env_path,
)


class TestPathsManager:
    def test_is_frozen_in_test_env(self):
        assert is_frozen() is False

    def test_get_base_dir_dev(self):
        base = get_base_dir()
        assert base.exists()
        assert (base / "main.py").exists()

    def test_get_base_dir_frozen(self):
        with patch.object(sys, "frozen", True, create=True), \
             patch.object(sys, "_MEIPASS", "/tmp/mock_bundle", create=True), \
             patch("os.path.exists", return_value=True):
            base = get_base_dir()
            assert base == Path("/tmp/mock_bundle")

    def test_get_user_data_dir_custom_env(self, tmp_path):
        custom = tmp_path / "custom_geraldo"
        with patch.dict(os.environ, {"GERALDO_DATA_DIR": str(custom)}):
            data_dir = get_user_data_dir()
            assert data_dir == custom
            assert data_dir.exists()

    def test_get_user_data_dir_linux(self, tmp_path):
        with patch.dict(os.environ, {"GERALDO_DATA_DIR": ""}, clear=False), \
             patch("sys.platform", "linux"), \
             patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_path / ".config")}):
            data_dir = get_user_data_dir()
            assert "geraldo" in str(data_dir).lower()
            assert data_dir.exists()

    def test_get_user_data_dir_windows(self, tmp_path):
        appdata = tmp_path / "AppData" / "Roaming"
        with patch.dict(os.environ, {"GERALDO_DATA_DIR": ""}, clear=False), \
             patch("sys.platform", "win32"), \
             patch.dict(os.environ, {"APPDATA": str(appdata)}):
            data_dir = get_user_data_dir()
            assert "Geraldo" in str(data_dir)
            assert data_dir.exists()

    def test_get_user_data_dir_macos(self, tmp_path):
        with patch.dict(os.environ, {"GERALDO_DATA_DIR": ""}, clear=False), \
             patch("sys.platform", "darwin"), \
             patch("pathlib.Path.home", return_value=tmp_path):
            data_dir = get_user_data_dir()
            assert "Library" in str(data_dir) and "Application Support" in str(data_dir) and "Geraldo" in str(data_dir)
            assert data_dir.exists()

    def test_get_temp_dir(self):
        tmp = get_temp_dir()
        assert tmp.exists()
        assert "geraldo" in str(tmp).lower()

    def test_get_temp_audio_path(self):
        audio_path = get_temp_audio_path("test_prefix", ".wav")
        assert audio_path.endswith(".wav")
        assert "test_prefix" in audio_path
        assert Path(audio_path).parent.exists()

    def test_get_models_search_paths(self):
        paths = get_models_search_paths()
        assert len(paths) >= 2
        assert get_base_dir() in paths

    def test_resolve_model_path_existing(self):
        # O repositório contém voz.onnx e voz_faber.onnx
        model = resolve_model_path("voz.onnx")
        assert model is not None
        assert model.exists()

    def test_resolve_model_path_non_existent(self):
        assert resolve_model_path("modelo_inexistente_99999.onnx") is None

    def test_get_credentials_path(self, tmp_path):
        creds = tmp_path / "my_creds.json"
        creds.write_text("{}", encoding="utf-8")
        with patch.dict(os.environ, {"GOOGLE_CREDENTIALS_FILE": str(creds)}):
            assert get_credentials_path() == creds

    def test_get_token_path(self, tmp_path):
        token = tmp_path / "my_token.json"
        with patch.dict(os.environ, {"GOOGLE_TOKEN_FILE": str(token)}):
            assert get_token_path() == token

    def test_get_env_path_dev(self):
        env_file = get_env_path()
        # No repositório local o arquivo .env existe
        if (get_base_dir() / ".env").exists():
            assert env_file is not None
            assert env_file.name == ".env"

    def test_resolve_model_path_alternatives(self):
        # voz_faber.onnx e voz.onnx são equivalentes
        res = resolve_model_path("voz_faber.onnx")
        assert res is not None
        assert res.exists()

    def test_ensure_model_available_existing(self):
        path = ensure_model_available("voz_faber.onnx")
        assert path.exists()

    def test_ensure_model_available_invalid_name(self):
        import pytest
        with pytest.raises(FileNotFoundError):
            ensure_model_available("invalid_voice_xyz_12345.onnx")

