import pytest
import subprocess
from unittest.mock import patch, MagicMock
from tools.hyprland import HyprlandTools

class TestHyprlandTools:
    @patch("subprocess.run")
    def test_run_hyprctl_success(self, mock_run):
        mock_run.return_value = MagicMock(stdout="ok\n", returncode=0)
        res = HyprlandTools.run_hyprctl(["dispatch", "workspace", "2"])
        assert res == "ok"
        mock_run.assert_called_once_with(
            ["hyprctl", "dispatch", "workspace", "2"],
            capture_output=True,
            text=True,
            check=True
        )

    @patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, ["hyprctl"]))
    def test_run_hyprctl_error(self, mock_run):
        res = HyprlandTools.run_hyprctl(["dispatch", "workspace", "2"])
        assert "Erro ao executar comando do Hyprland" in res

    @patch.object(HyprlandTools, "run_hyprctl", return_value="ok")
    def test_change_workspace(self, mock_run):
        res = HyprlandTools.change_workspace("3")
        assert "Mudando para a área de trabalho 3" in res
        mock_run.assert_called_once_with(["dispatch", "workspace", "3"])

    @patch.object(HyprlandTools, "run_hyprctl", return_value="ok")
    def test_move_window_to_workspace(self, mock_run):
        res = HyprlandTools.move_window_to_workspace("5")
        assert "Janela movida para a área de trabalho 5" in res
        mock_run.assert_called_once_with(["dispatch", "movetoworkspace", "5"])

    @patch.object(HyprlandTools, "run_hyprctl", return_value="ok")
    def test_toggle_floating(self, mock_run):
        res = HyprlandTools.toggle_floating()
        assert "Alternado estado flutuante" in res
        mock_run.assert_called_once_with(["dispatch", "togglefloating", "active"])

    @patch.object(HyprlandTools, "run_hyprctl", return_value="ok")
    def test_toggle_fullscreen(self, mock_run):
        res = HyprlandTools.toggle_fullscreen()
        assert "Alternado modo tela cheia" in res
        mock_run.assert_called_once_with(["dispatch", "fullscreen", "0"])

    @patch.object(HyprlandTools, "run_hyprctl", return_value="ok")
    def test_close_active_window(self, mock_run):
        res = HyprlandTools.close_active_window()
        assert "Fechando janela ativa" in res
        mock_run.assert_called_once_with(["dispatch", "killactive", ""])

    @patch("subprocess.run")
    def test_set_brightness_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        res = HyprlandTools.set_brightness("70%")
        assert "Brilho ajustado para 70%" in res
        mock_run.assert_called_once_with(["brightnessctl", "set", "70%"], check=True)

    @patch("subprocess.run", side_effect=Exception("No brightnessctl"))
    def test_set_brightness_error(self, mock_run):
        res = HyprlandTools.set_brightness("70%")
        assert "Não foi possível ajustar o brilho" in res

    @patch("subprocess.Popen")
    def test_open_launcher_rofi(self, mock_popen):
        res = HyprlandTools.open_launcher()
        assert "Abrindo menu de aplicativos" in res
        mock_popen.assert_called_once_with(["rofi", "-show", "drun"])

    @patch("subprocess.Popen")
    def test_open_launcher_wofi_fallback(self, mock_popen):
        # Rofi falha, wofi funciona
        mock_popen.side_effect = [Exception("No rofi"), MagicMock()]
        res = HyprlandTools.open_launcher()
        assert "Abrindo menu de aplicativos" in res
        assert mock_popen.call_count == 2
        mock_popen.assert_any_call(["wofi", "--show", "drun"])

    @patch("subprocess.Popen", side_effect=Exception("No launcher"))
    def test_open_launcher_none_found(self, mock_popen):
        res = HyprlandTools.open_launcher()
        assert "Nenhum launcher encontrado" in res
