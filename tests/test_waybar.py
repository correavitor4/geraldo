import pytest
import subprocess
import json
import os
from unittest.mock import patch, MagicMock
from tools.waybar import WaybarTools
import ui.waybar as ui_waybar

class TestWaybarTools:
    @patch("subprocess.run")
    def test_restart_waybar_unavailable(self, mock_run):
        # WAYLAND_DISPLAY não setado e pgrep retorna 1 (não ativo)
        with patch.dict(os.environ, {}, clear=True):
            mock_run.return_value = MagicMock(returncode=1)
            res = WaybarTools.restart_waybar()
            assert "Comando indisponível" in res

    @patch("subprocess.run")
    def test_restart_waybar_sigusr2_success(self, mock_run):
        # Hyprland ativo e waybar existe
        with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-1"}):
            mock_run.side_effect = [
                MagicMock(returncode=0),  # which waybar
                MagicMock(returncode=0),  # pkill -SIGUSR2 waybar
            ]
            res = WaybarTools.restart_waybar()
            assert "Waybar atualizada com sucesso" in res

    @patch("subprocess.Popen")
    @patch("subprocess.run")
    def test_restart_waybar_fallback_restart(self, mock_run, mock_popen):
        with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-1"}):
            mock_run.side_effect = [
                MagicMock(returncode=0),  # which waybar
                MagicMock(returncode=1),  # pkill -SIGUSR2 waybar (falhou)
                MagicMock(returncode=0),  # pkill waybar
            ]
            res = WaybarTools.restart_waybar()
            assert "Waybar atualizada com sucesso" in res
            mock_popen.assert_called_once_with(
                ["waybar"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

    @patch("subprocess.run", side_effect=Exception("Crash"))
    def test_restart_waybar_exception(self, mock_run):
        with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-1"}):
            res = WaybarTools.restart_waybar()
            assert "Erro ao atualizar a Waybar" in res

class TestUIWaybar:
    @pytest.mark.parametrize("state_name, expected_class", [
        ("dormindo", "idle"),
        ("escutando", "listening"),
        ("pensando", "thinking"),
        ("falando", "speaking"),
        ("off", "off")
    ])
    def test_set_state_valid(self, tmp_path, state_name, expected_class):
        state_file = str(tmp_path / "state.json")
        with patch("ui.waybar.STATE_FILE", state_file):
            ui_waybar.set_state(state_name)
            assert os.path.exists(state_file)
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data["class"] == expected_class
            assert "text" in data
            assert "tooltip" in data

    def test_set_state_unknown_fallback_to_dormindo(self, tmp_path):
        state_file = str(tmp_path / "state.json")
        with patch("ui.waybar.STATE_FILE", state_file):
            ui_waybar.set_state("estado_inexistente")
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data["class"] == "idle"
            assert "GERALDO" in data["text"]
