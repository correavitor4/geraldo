import pytest
import numpy as np
from unittest.mock import patch, MagicMock

import config
import main

class TestConfig:
    def test_assistant_name(self):
        assert config.ASSISTANT_NAME == "Geraldo"

    def test_ollama_settings(self):
        assert config.OLLAMA_HOST
        assert config.LLM_MODEL

    def test_audio_parameters(self):
        assert config.SAMPLE_RATE == 16000
        assert config.CHUNK_SIZE == 512
        assert config.VAD_THRESHOLD == 0.5
        assert config.SILENCE_LIMIT_SEC == 0.8

    def test_system_prompt(self):
        assert "Geraldo" in config.SYSTEM_PROMPT
        assert "português" in config.SYSTEM_PROMPT

class TestMainFlow:
    @patch("main.TimerManager")
    @patch("main.TextToSpeech")
    @patch("main.AudioPlayer")
    @patch("main.AudioRecorder")
    @patch("main.WakeWordDetector")
    @patch("main.SpeechToText")
    @patch("main.BrainLLM")
    def test_main_loop_single_iteration_then_interrupt(
        self,
        mock_brain_cls,
        mock_stt_cls,
        mock_wake_cls,
        mock_rec_cls,
        mock_player_cls,
        mock_tts_cls,
        mock_tm
    ):
        mock_detector = MagicMock()
        # Primeiro ciclo: wake word detectada; segundo ciclo: KeyboardInterrupt para sair do loop infinito
        mock_detector.wait_for_wake_word.side_effect = [True, KeyboardInterrupt]
        mock_wake_cls.return_value = mock_detector

        mock_recorder = MagicMock()
        mock_recorder.record_until_silence.return_value = np.zeros(16000, dtype=np.float32)
        mock_rec_cls.return_value = mock_recorder

        mock_stt = MagicMock()
        mock_stt.transcribe.return_value = "que horas são"
        mock_stt_cls.return_value = mock_stt

        mock_brain = MagicMock()
        mock_brain.ask.return_value = "Agora são dez horas."
        mock_brain_cls.return_value = mock_brain

        mock_player = MagicMock()
        mock_player_cls.return_value = mock_player

        mock_tts = MagicMock()
        mock_tts.synthesize.return_value = "/tmp/resp.wav"
        mock_tts_cls.return_value = mock_tts

        with pytest.raises(SystemExit) as exc_info:
            main.main()

        assert exc_info.value.code == 0

        # Verifica chamadas dos estados principais
        mock_tm.set_assistant_state.assert_any_call("starting")
        mock_tm.set_assistant_state.assert_any_call("listening")
        mock_tm.set_assistant_state.assert_any_call("transcribing")
        mock_tm.set_assistant_state.assert_any_call("thinking")
        mock_tm.set_assistant_state.assert_any_call("speaking")
        mock_tm.set_assistant_state.assert_any_call("idle")

        mock_player.play_beep.assert_called_once()
        mock_brain.ask.assert_called_once_with("que horas são")
        mock_tts.synthesize.assert_called_once_with("Agora são dez horas.")
        mock_player.play.assert_called_once_with("/tmp/resp.wav")

    @patch("main.TimerManager")
    @patch("main.TextToSpeech")
    @patch("main.AudioPlayer")
    @patch("main.AudioRecorder")
    @patch("main.WakeWordDetector")
    @patch("main.SpeechToText")
    @patch("main.BrainLLM")
    def test_main_loop_empty_transcription(
        self,
        mock_brain_cls,
        mock_stt_cls,
        mock_wake_cls,
        mock_rec_cls,
        mock_player_cls,
        mock_tts_cls,
        mock_tm
    ):
        mock_detector = MagicMock()
        mock_detector.wait_for_wake_word.side_effect = [True, KeyboardInterrupt]
        mock_wake_cls.return_value = mock_detector

        mock_recorder = MagicMock()
        mock_recorder.record_until_silence.return_value = np.zeros(16000, dtype=np.float32)
        mock_rec_cls.return_value = mock_recorder

        # Transcrição vazia (nada compreendido)
        mock_stt = MagicMock()
        mock_stt.transcribe.return_value = "   "
        mock_stt_cls.return_value = mock_stt

        mock_brain = MagicMock()
        mock_brain_cls.return_value = mock_brain

        with pytest.raises(SystemExit) as exc_info:
            main.main()

        assert exc_info.value.code == 0
        # BrainLLM não deve ser chamado quando nada for compreendido
        mock_brain.ask.assert_not_called()
