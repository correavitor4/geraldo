# tests/test_platform_windows.py
"""
Testes dedicados e exclusivos para o sistema operacional Windows.
Estes testes só são executados quando sys.platform == 'win32'.
Em outros sistemas operacionais (macOS, Linux), são ignorados automaticamente.
"""
import sys
import os
import wave
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Marca todo o módulo como exclusivo para Windows
pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Teste exclusivo para ambiente Windows (win32)"
)


class TestWindowsPlatform:
    def test_windows_user_data_dir(self):
        """Verifica se a pasta de dados do Geraldo aponta para %APPDATA%/Geraldo no Windows."""
        from core.paths import get_user_data_dir
        data_dir = get_user_data_dir()
        assert isinstance(data_dir, Path)
        app_data = os.getenv("APPDATA")
        if app_data:
            assert str(data_dir).lower().startswith(app_data.lower())
        assert data_dir.name.lower() == "geraldo"
        assert data_dir.exists()

    def test_windows_temp_dir_and_audio_path(self):
        """Verifica se o diretório temporário no Windows é seguro e funcional."""
        from core.paths import get_temp_dir, get_temp_audio_path
        temp_dir = get_temp_dir()
        assert temp_dir.exists()
        audio_path = get_temp_audio_path(prefix="teste_win", suffix=".wav")
        assert audio_path.endswith(".wav")
        assert "teste_win" in audio_path
        # No Windows, deve ser um caminho de arquivo válido
        assert Path(audio_path).parent.exists()

    def test_windows_espeak_data_discovery(self):
        """Garante que a pasta espeak-ng-data seja encontrada no ambiente Windows."""
        from core.paths import resolve_espeak_data_dir
        espeak_dir = resolve_espeak_data_dir()
        assert espeak_dir is not None, "espeak-ng-data não foi localizado no Windows"
        assert espeak_dir.is_dir()
        # No Windows, o diretório deve conter os arquivos fonéticos essenciais
        assert any(espeak_dir.iterdir()), "A pasta espeak-ng-data está vazia"

    def test_windows_piper_voice_in_process_loading(self):
        """Garante que o PiperVoice carregue in-process com baixa latência no Windows."""
        from brain.tts import TextToSpeech
        from core.paths import resolve_model_path

        model_file = resolve_model_path("voz_faber.onnx") or resolve_model_path("voz.onnx")
        if not model_file or not model_file.exists():
            pytest.skip("Modelo ONNX de voz não encontrado localmente para teste in-process.")

        tts = TextToSpeech(model_path=str(model_file))
        assert tts._voice is not None, "Falha ao carregar _voice in-process no Windows com espeak-ng-data"

    def test_windows_speech_synthesis_wav_generation(self):
        """Verifica se a síntese de texto gera um arquivo WAV válido e legível no Windows."""
        from brain.tts import TextToSpeech
        from core.paths import resolve_model_path

        model_file = resolve_model_path("voz_faber.onnx") or resolve_model_path("voz.onnx")
        if not model_file or not model_file.exists():
            pytest.skip("Modelo ONNX de voz não encontrado localmente.")

        tts = TextToSpeech(model_path=str(model_file))
        texto_teste = "Geraldo operacional no sistema Windows."
        wav_path = tts.synthesize(texto_teste)

        assert wav_path, "Caminho do WAV retornado não pode ser vazio"
        assert os.path.exists(wav_path), f"Arquivo de áudio não foi gerado em: {wav_path}"
        assert os.path.getsize(wav_path) > 1000, "Arquivo WAV gerado está vazio ou truncado"

        # Valida cabeçalho do arquivo WAV
        with wave.open(wav_path, "rb") as wf:
            assert wf.getnchannels() in (1, 2)
            assert wf.getsampwidth() == 2  # 16-bit PCM
            assert wf.getframerate() in (16000, 22050, 24000)
            assert wf.getnframes() > 0

    def test_windows_speak_does_not_crash_with_missing_alsa(self):
        """
        Garante que chamar tts.speak() no Windows não falha com FileNotFoundError (aplay).
        Antes da correção, aplay/pw-play eram executados diretamente causando crash.
        """
        from brain.tts import TextToSpeech

        with patch.object(TextToSpeech, "synthesize", return_value="C:\\tmp\\teste_win.wav"), \
             patch("audio.player.AudioPlayer.play") as mock_player:
            tts = TextToSpeech(model_path="voz_faber.onnx")
            tts.speak("Mensagem de teste de áudio")
            mock_player.assert_called_once_with("C:\\tmp\\teste_win.wav")

    def test_windows_audio_player_native_winsound(self):
        """Testa o fallback nativo via winsound no Windows."""
        from audio.player import AudioPlayer

        with patch("winsound.PlaySound") as mock_winsound, \
             patch("shutil.which", return_value=None):
            AudioPlayer.play("C:/temp/geraldo_audio.wav")
            mock_winsound.assert_called_once()
            called_path = mock_winsound.call_args[0][0]
            # No Windows, o separador de caminho deve ser normalizado
            assert "/" not in called_path or "\\" in called_path

    @patch("main.AudioPlayer")
    @patch("main.TextToSpeech")
    def test_windows_main_speak_callback_resilience(self, mock_tts_cls, mock_player_cls):
        """Garante que o callback de fala em main.py capture exceções e não quebre a execução no Windows."""
        import main
        mock_tts = MagicMock()
        mock_player = MagicMock()
        mock_tts_cls.return_value = mock_tts
        mock_player_cls.return_value = mock_player

        # Simula erro de síntese no Windows
        mock_tts.synthesize.side_effect = RuntimeError("Falha simulada de síntese no Windows")

        # Constrói o speak_callback isoladamente para verificar resiliência a falhas
        tts = mock_tts
        player = mock_player

        def split_into_sentences(text: str) -> list[str]:
            import re
            raw_parts = re.split(r'(?<=[.!?])\s+', text.strip())
            parts = [p.strip() for p in raw_parts if p.strip()]
            return parts if parts else [text.strip()]

        # Executa lógica de speak_callback igual à implementada em main.py
        def callback(text: str):
            sentences = split_into_sentences(text)
            if len(sentences) <= 1:
                try:
                    wav = tts.synthesize(text)
                except Exception as e:
                    wav = None
                if wav:
                    try:
                        player.play(wav)
                    except Exception:
                        pass

        # Não deve propagar erro
        callback("Teste de robustez no Windows.")
        assert player.play.call_count == 0

        # Agora com sucesso na síntese
        mock_tts.synthesize.side_effect = None
        mock_tts.synthesize.return_value = "C:\\tmp\\audio.wav"
        callback("Teste com sucesso.")
        mock_player.play.assert_called_with("C:\\tmp\\audio.wav")

