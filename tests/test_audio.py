import pytest
import numpy as np
import os
import wave
import subprocess
from unittest.mock import patch, MagicMock

from audio.player import AudioPlayer
from audio.recorder import AudioRecorder
from audio.wakeword import WakeWordDetector
from audio.device_utils import get_input_device_id
import audio.feedback as audio_feedback
from audio.generate_beep import create_alexa_beep
from audio.generate_alarm import create_alarm_sound
from audio.generate_timer import create_timer_sound

class TestAudioPlayer:
    def test_play_empty(self):
        with patch("shutil.which") as mock_which:
            AudioPlayer.play("")
            mock_which.assert_not_called()

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_play_selects_first_available_player(self, mock_which, mock_run):
        mock_which.side_effect = lambda cmd: cmd == "paplay"
        AudioPlayer.play("test.wav")
        mock_run.assert_called_once_with(
            ["paplay", "test.wav"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )

    @patch("subprocess.run")
    @patch("shutil.which", return_value=True)
    def test_play_fails_all_tries_next(self, mock_which, mock_run):
        # Primeiro player falha com CalledProcessError, segundo dá certo
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, ["pw-play"]),
            MagicMock(returncode=0)
        ]
        AudioPlayer.play("test.wav")
        assert mock_run.call_count == 2

    @patch("sounddevice.wait")
    @patch("sounddevice.play")
    def test_play_beep(self, mock_play, mock_wait):
        AudioPlayer.play_beep()
        mock_play.assert_called_once()
        chime_arg = mock_play.call_args[0][0]
        assert isinstance(chime_arg, np.ndarray)
        assert chime_arg.dtype == np.float32
        assert mock_play.call_args[1]["samplerate"] == 16000
        mock_wait.assert_called_once()

class TestAudioRecorder:
    def test_init_params(self):
        rec = AudioRecorder(sample_rate=16000, chunk_size=1024)
        assert rec.sample_rate == 16000
        assert rec.chunk_size == 1024
        assert rec.energy_threshold == 0.016
        assert rec.silence_limit == 1.5

    def test_record_until_silence_voice_then_silence(self):
        rec = AudioRecorder(sample_rate=16000, chunk_size=1024)
        rec.silence_limit = 1.0

        voice_chunk = (np.ones((1024, 1), dtype=np.float32) * 0.1, None)
        silence_chunk = (np.zeros((1024, 1), dtype=np.float32), None)

        def chunk_gen():
            yield voice_chunk
            yield voice_chunk
            while True:
                yield silence_chunk

        mock_stream = MagicMock()
        mock_stream.read.side_effect = chunk_gen()

        t_val = [100.0]
        def advance_time():
            t_val[0] += 0.6
            return t_val[0]

        with patch("time.time", side_effect=advance_time):
            with patch("sounddevice.InputStream") as mock_input_stream:
                mock_input_stream.return_value.__enter__.return_value = mock_stream
                audio = rec.record_until_silence()
                assert isinstance(audio, np.ndarray)
                assert len(audio) > 0

    def test_record_timeout_no_voice(self):
        rec = AudioRecorder(sample_rate=16000, chunk_size=1024)
        silence_chunk = (np.zeros((1024, 1), dtype=np.float32), None)

        mock_stream = MagicMock()
        mock_stream.read.return_value = silence_chunk

        # Simula time.time avançando mais de 6 segundos
        with patch("time.time", side_effect=[0, 0, 7.0, 7.0]):
            with patch("sounddevice.InputStream") as mock_input_stream:
                mock_input_stream.return_value.__enter__.return_value = mock_stream
                audio = rec.record_until_silence()
                assert isinstance(audio, np.ndarray)

class TestWakeWordDetector:
    def test_wait_for_wake_word_detected(self):
        mock_stt = MagicMock()
        mock_seg = MagicMock()
        mock_seg.text = "Geraldo"
        mock_stt.model_wake.transcribe.return_value = ([mock_seg], None)

        detector = WakeWordDetector(target_word="geraldo", stt=mock_stt)

        audio_chunk = np.ones((24000, 1), dtype=np.float32) * 0.1
        mock_stream = MagicMock()
        mock_stream.read.return_value = (audio_chunk, None)

        with patch("sounddevice.InputStream") as mock_input_stream:
            mock_input_stream.return_value.__enter__.return_value = mock_stream
            result = detector.wait_for_wake_word(max_loops=3)
            assert result is True

    def test_wait_for_wake_word_skips_silence(self):
        mock_stt = MagicMock()
        detector = WakeWordDetector(target_word="geraldo", stt=mock_stt)

        silent_chunk = np.zeros((24000, 1), dtype=np.float32)
        loud_chunk = np.ones((24000, 1), dtype=np.float32) * 0.1

        mock_seg = MagicMock()
        mock_seg.text = "oi geraldo"
        mock_stt.model_wake.transcribe.return_value = ([mock_seg], None)

        mock_stream = MagicMock()
        # Primeiro chunk silêncio absoluto, segundo com a palavra
        mock_stream.read.side_effect = [
            (silent_chunk, None),
            (loud_chunk, None)
        ]

        with patch("sounddevice.InputStream") as mock_input_stream:
            mock_input_stream.return_value.__enter__.return_value = mock_stream
            assert detector.wait_for_wake_word(max_loops=3) is True
            # Transcribe deve ser chamado apenas 1 vez (o silêncio foi pulado)
            assert mock_stt.model_wake.transcribe.call_count == 1

    def test_wait_for_wake_word_rejects_low_confidence(self):
        mock_stt = MagicMock()
        mock_seg = MagicMock()
        mock_seg.text = "geraldo"
        mock_seg.no_speech_prob = 0.8  # Alta probabilidade de ser ruído/silêncio
        mock_seg.avg_logprob = -1.5
        mock_stt.model_wake.transcribe.return_value = ([mock_seg], None)

        detector = WakeWordDetector(target_word="geraldo", stt=mock_stt)
        audio_chunk = np.ones((24000, 1), dtype=np.float32) * 0.1
        mock_stream = MagicMock()
        mock_stream.read.return_value = (audio_chunk, None)

        with patch("sounddevice.InputStream") as mock_input_stream:
            mock_input_stream.return_value.__enter__.return_value = mock_stream
            result = detector.wait_for_wake_word(max_loops=2)
            assert result is False

class TestAudioFeedback:
    @patch("subprocess.Popen")
    @patch("os.path.exists", return_value=True)
    def test_play_wake_beep_exists(self, mock_exists, mock_popen):
        audio_feedback.play_wake_beep()
        mock_popen.assert_called_once()
        assert "pw-play" in mock_popen.call_args[0][0]

    @patch("subprocess.Popen")
    @patch("os.path.exists", return_value=False)
    def test_play_wake_beep_not_exists(self, mock_exists, mock_popen):
        audio_feedback.play_wake_beep()
        mock_popen.assert_not_called()

class TestDeviceUtils:
    def test_get_input_device_id_found(self):
        mock_devices = [
            {"name": "Speakers", "max_input_channels": 0},
            {"name": "Fifine K420 Microphone", "max_input_channels": 2},
            {"name": "Webcam", "max_input_channels": 1}
        ]
        with patch("sounddevice.query_devices", return_value=mock_devices):
            idx = get_input_device_id("Fifine K420")
            assert idx == 1

    def test_get_input_device_id_not_found(self):
        mock_devices = [
            {"name": "Speakers", "max_input_channels": 0}
        ]
        with patch("sounddevice.query_devices", return_value=mock_devices):
            assert get_input_device_id("Fifine K420") is None

class TestSoundGenerators:
    def test_create_alexa_beep(self, tmp_path):
        out_file = str(tmp_path / "wake_alexa.wav")
        create_alexa_beep(output_path=out_file)
        assert os.path.exists(out_file)
        with wave.open(out_file, "rb") as wav:
            assert wav.getnchannels() == 1
            assert wav.getsampwidth() == 2
            assert wav.getframerate() == 44100
            assert wav.getnframes() > 0

    def test_create_alarm_sound(self, tmp_path):
        out_file = str(tmp_path / "alarm.wav")
        create_alarm_sound(output_path=out_file)
        assert os.path.exists(out_file)
        with wave.open(out_file, "rb") as wav:
            assert wav.getnchannels() == 1
            assert wav.getsampwidth() == 2
            assert wav.getframerate() == 44100
            assert wav.getnframes() > 0

    def test_create_timer_sound(self, tmp_path):
        out_file = str(tmp_path / "timer.wav")
        create_timer_sound(output_path=out_file)
        assert os.path.exists(out_file)
        with wave.open(out_file, "rb") as wav:
            assert wav.getnchannels() == 1
            assert wav.getsampwidth() == 2
            assert wav.getframerate() == 44100
            assert wav.getnframes() > 0


class TestAudioConfig:
    def test_get_audio_config_structure(self):
        import config
        cfg = config.get_audio_config()
        assert isinstance(cfg, dict)
        assert "input_device" in cfg
        assert "output_device" in cfg
        assert "devices" in cfg
        assert "available_inputs" in cfg
        assert "available_outputs" in cfg

    def test_update_audio_config_set_and_reset(self, monkeypatch):
        import config
        saved = {}
        monkeypatch.setattr(config, "save_settings", lambda d: saved.update(d))
        monkeypatch.setattr("sounddevice.default", MagicMock())

        # 1. Configura dispositivos específicos
        res = config.update_audio_config(input_device="Fifine K420", output_device="Realtek Speakers", persist=True)
        assert config.AUDIO_INPUT_DEVICE == "Fifine K420"
        assert config.AUDIO_OUTPUT_DEVICE == "Realtek Speakers"
        assert saved["audio_input_device"] == "Fifine K420"
        assert saved["audio_output_device"] == "Realtek Speakers"

        # 2. Configura por ID numérico
        res = config.update_audio_config(input_device="3", output_device=1, persist=False)
        assert config.AUDIO_INPUT_DEVICE == 3
        assert config.AUDIO_OUTPUT_DEVICE == 1

        # 3. Reseta explicitamente para None (padrão)
        res = config.update_audio_config(input_device=None, output_device=None, persist=True)
        assert config.AUDIO_INPUT_DEVICE is None
        assert config.AUDIO_OUTPUT_DEVICE is None
        assert saved["audio_input_device"] is None
        assert saved["audio_output_device"] is None

        # 4. Reseta passando "padrão" ou "default"
        config.update_audio_config(input_device="padrão", output_device="default", persist=False)
        assert config.AUDIO_INPUT_DEVICE is None
        assert config.AUDIO_OUTPUT_DEVICE is None

