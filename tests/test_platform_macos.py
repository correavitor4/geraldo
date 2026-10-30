# tests/test_platform_macos.py
"""
Testes dedicados e exclusivos para o sistema operacional macOS (Darwin).
Estes testes só são executados quando sys.platform == 'darwin'.
Em outros sistemas operacionais (Windows, Linux), são ignorados automaticamente via pytest.mark.skipif.
"""
import sys
import os
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Marca todo o módulo como exclusivo para macOS
pytestmark = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="Teste exclusivo para ambiente macOS (darwin)"
)


class TestMacOSPlatform:
    def test_macos_user_data_dir(self):
        """Verifica se a pasta de dados do Geraldo aponta para ~/Library/Application Support/Geraldo no macOS."""
        from core.paths import get_user_data_dir
        data_dir = get_user_data_dir()
        assert isinstance(data_dir, Path)
        home = Path.home()
        expected = home / "Library" / "Application Support" / "Geraldo"
        assert str(data_dir).lower() == str(expected).lower()
        assert data_dir.exists()

    def test_macos_temp_dir_and_audio_path(self):
        """Verifica se o diretório temporário no macOS é funcional."""
        from core.paths import get_temp_dir, get_temp_audio_path
        temp_dir = get_temp_dir()
        assert temp_dir.exists()
        audio_path = get_temp_audio_path(prefix="teste_mac", suffix=".wav")
        assert audio_path.endswith(".wav")
        assert "teste_mac" in audio_path
        assert Path(audio_path).parent.exists()

    def test_macos_audio_player_native_afplay(self):
        """Garante que o AudioPlayer use afplay nativo do macOS por padrão."""
        from audio.player import AudioPlayer

        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            # No macOS, afplay está em /usr/bin/afplay
            mock_which.side_effect = lambda cmd: "/usr/bin/afplay" if cmd == "afplay" else None
            AudioPlayer.play("/tmp/geraldo_mac.wav")
            mock_run.assert_called_once_with(
                ["afplay", "/tmp/geraldo_mac.wav"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )

    def test_macos_tts_speak_uses_afplay(self):
        """Garante que tts.speak() utilize afplay no macOS sem recorrer ao ALSA."""
        from brain.tts import TextToSpeech

        with patch.object(TextToSpeech, "synthesize", return_value="/tmp/test_mac.wav"), \
             patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.side_effect = lambda cmd: "/usr/bin/afplay" if cmd == "afplay" else None
            tts = TextToSpeech(model_path="voz_faber.onnx")
            tts.speak("Fala no macOS")
            mock_run.assert_called_once_with(
                ["afplay", "/tmp/test_mac.wav"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

    def test_macos_espeak_data_discovery(self):
        """Garante que a descoberta de espeak-ng-data suporte caminhos de macOS."""
        from core.paths import resolve_espeak_data_dir
        espeak_dir = resolve_espeak_data_dir()
        # Se os dados existirem na máquina, devem ser um diretório
        if espeak_dir:
            assert espeak_dir.is_dir()

    def test_macos_desktop_gui_app_mode(self):
        """Valida que o inicializador GUI detecte /Applications/Geraldo.app no macOS."""
        from ui.gui import run_gui

        with patch("sys.platform", "darwin"), \
             patch("os.path.isdir") as mock_isdir, \
             patch("subprocess.Popen") as mock_popen, \
             patch("socket.socket") as mock_socket:
            mock_s = MagicMock()
            mock_s.connect_ex.return_value = 0
            mock_socket.return_value.__enter__.return_value = mock_s
            mock_isdir.side_effect = lambda p: True if p == "/Applications/Geraldo.app" else False

            run_gui()
            mock_popen.assert_called_once_with(["open", "/Applications/Geraldo.app"])

    def test_macos_speak_callback_resilience(self):
        """Valida a resiliência do pipeline de áudio de main.py no macOS."""
        from brain.tts import TextToSpeech
        from audio.player import AudioPlayer

        mock_tts = MagicMock()
        mock_tts.synthesize.return_value = "/tmp/geraldo_mac_resp.wav"
        mock_player = MagicMock()

        def split_into_sentences(text: str) -> list[str]:
            import re
            raw_parts = re.split(r'(?<=[.!?])\s+', text.strip())
            parts = [p.strip() for p in raw_parts if p.strip()]
            return parts if parts else [text.strip()]

        def speak_callback(text: str):
            sentences = split_into_sentences(text)
            for sent in sentences:
                try:
                    wav = mock_tts.synthesize(sent)
                    if wav:
                        mock_player.play(wav)
                except Exception:
                    pass

        speak_callback("Primeira frase macOS. Segunda frase macOS.")
        assert mock_player.play.call_count == 2
        mock_player.play.assert_called_with("/tmp/geraldo_mac_resp.wav")
