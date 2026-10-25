import pytest
import numpy as np
import os
import subprocess
from unittest.mock import patch, MagicMock

from brain.stt import SpeechToText
from brain.tts import TextToSpeech

class TestSpeechToText:
    @patch("brain.stt.WhisperModel")
    def test_stt_init(self, mock_whisper):
        stt = SpeechToText(wake_model_size="tiny", cmd_model_size="small", device="cpu", compute_type="int8")
        assert mock_whisper.call_count == 2
        assert "Geraldo" in stt.vocab_prompt

    @patch("brain.stt.WhisperModel")
    def test_transcribe_quick_with_keyword(self, mock_whisper):
        stt = SpeechToText()
        mock_seg = MagicMock()
        mock_seg.text = "Geraldo, você está aí?"
        stt.model_wake.transcribe.return_value = ([mock_seg], None)

        fake_audio = np.ones(16000, dtype=np.float32)
        res = stt.transcribe_quick(fake_audio)
        assert "geraldo" in res

    @patch("brain.stt.WhisperModel")
    def test_transcribe_quick_without_keyword(self, mock_whisper):
        stt = SpeechToText()
        mock_seg = MagicMock()
        mock_seg.text = "Outra palavra aleatória"
        stt.model_wake.transcribe.return_value = ([mock_seg], None)

        fake_audio = np.ones(16000, dtype=np.float32)
        res = stt.transcribe_quick(fake_audio)
        # Filtro estrito: deve retornar vazio se não contiver 'geraldo'
        assert res == ""

    @patch("brain.stt.WhisperModel")
    def test_transcribe_quick_empty_audio(self, mock_whisper):
        stt = SpeechToText()
        assert stt.transcribe_quick(None) == ""
        assert stt.transcribe_quick(np.array([])) == ""

    @patch("brain.stt.WhisperModel")
    def test_transcribe_full(self, mock_whisper):
        stt = SpeechToText()
        seg1 = MagicMock(text="Que horas")
        seg2 = MagicMock(text="são agora?")
        stt.model_cmd.transcribe.return_value = ([seg1, seg2], None)

        fake_audio = np.ones(16000, dtype=np.float32)
        res = stt.transcribe(fake_audio)
        assert res == "Que horas são agora?"

    @patch("brain.stt.WhisperModel")
    def test_transcribe_empty_audio(self, mock_whisper):
        stt = SpeechToText()
        assert stt.transcribe(None) == ""
        assert stt.transcribe(np.array([])) == ""

    @patch("brain.stt.WhisperModel")
    def test_transcribe_vad_failure_fallback(self, mock_whisper):
        stt = SpeechToText()
        stt._vad_available = True
        
        # Simula falha na chamada com vad_filter=True e sucesso na chamada com vad_filter=False
        seg = MagicMock(text="Comando executado com sucesso")
        def mock_transcribe(*args, **kwargs):
            if kwargs.get("vad_filter") is True:
                raise RuntimeError("Silero VAD model missing")
            return ([seg], None)
        
        stt.model_cmd.transcribe.side_effect = mock_transcribe
        fake_audio = np.ones(16000, dtype=np.float32)
        res = stt.transcribe(fake_audio)
        assert res == "Comando executado com sucesso"
        assert stt._vad_available is False

    @patch("brain.stt.WhisperModel")
    def test_transcribe_quick_vad_failure_fallback(self, mock_whisper):
        stt = SpeechToText()
        stt._vad_available = True
        
        seg = MagicMock(text="Geraldo bom dia")
        seg.no_speech_prob = 0.1
        seg.avg_logprob = -0.5
        def mock_transcribe(*args, **kwargs):
            if kwargs.get("vad_filter") is True:
                raise RuntimeError("Silero VAD model missing")
            return ([seg], None)
        
        stt.model_wake.transcribe.side_effect = mock_transcribe
        fake_audio = np.ones(16000, dtype=np.float32)
        res = stt.transcribe_quick(fake_audio)
        assert "geraldo" in res
        assert stt._vad_available is False

class TestTextToSpeech:
    def test_init_model_not_found(self):
        with pytest.raises(FileNotFoundError):
            TextToSpeech(model_path="modelo_que_nao_existe_12345.onnx")

    @patch("os.path.exists", return_value=True)
    def test_synthesize_empty_text(self, mock_exists):
        tts = TextToSpeech(model_path="voz_mock.onnx")
        assert tts.synthesize("") == ""
        assert tts.synthesize(None) == ""

    @patch("subprocess.run")
    @patch("os.path.exists", return_value=True)
    def test_synthesize_valid_text(self, mock_exists, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        tts = TextToSpeech(model_path="voz_mock.onnx")
        out_path = tts.synthesize("Olá Mundo")
        assert out_path.replace("\\", "/").startswith("/tmp/geraldo_response_")
        assert out_path.endswith(".wav")
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "-m" in cmd
        assert "piper" in cmd

    @patch("subprocess.run")
    @patch("shutil.which")
    @patch.object(TextToSpeech, "synthesize", return_value="/tmp/test.wav")
    @patch("os.path.exists", return_value=True)
    def test_speak_pw_play(self, mock_exists, mock_synth, mock_which, mock_run):
        mock_which.return_value = "/usr/bin/pw-play"
        tts = TextToSpeech(model_path="voz_mock.onnx")
        tts.speak("Fala teste")
        mock_synth.assert_called_once_with("Fala teste")
        mock_run.assert_called_once_with(
            ["pw-play", "/tmp/test.wav"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    @patch("subprocess.run")
    @patch("shutil.which", return_value=None)
    @patch.object(TextToSpeech, "synthesize", return_value="/tmp/test.wav")
    @patch("os.path.exists", return_value=True)
    def test_speak_aplay_fallback(self, mock_exists, mock_synth, mock_which, mock_run):
        tts = TextToSpeech(model_path="voz_mock.onnx")
        tts.speak("Fala teste")
        mock_run.assert_called_once_with(
            ["aplay", "/tmp/test.wav"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
