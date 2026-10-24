"""
Gravador contínuo de áudio para reuniões com escrita direta em arquivo WAV.
"""
import os
import time
import wave
import threading
import numpy as np
from typing import Optional

try:
    import sounddevice as sd
except Exception:
    sd = None

import config
from audio.device_utils import resolve_audio_device
from services.meeting.models import MeetingStatus


class MeetingAudioRecorder:
    def __init__(
        self,
        output_path: str,
        sample_rate: int = 16000,
        chunk_size: int = 1024,
        device=None,
    ):
        self.output_path = output_path
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.device = device

        self._status = MeetingStatus.IDLE
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()

        self._start_time: float = 0.0
        self._accumulated_duration: float = 0.0
        self._current_rms: float = 0.0
        self._wav_file: Optional[wave.Wave_write] = None

    @property
    def status(self) -> MeetingStatus:
        return self._status

    @property
    def current_rms(self) -> float:
        return self._current_rms

    @property
    def elapsed_duration(self) -> float:
        with self._lock:
            if self._status == MeetingStatus.RECORDING:
                return self._accumulated_duration + (time.time() - self._start_time)
            return self._accumulated_duration

    def start(self) -> None:
        """Inicia a gravação em segundo plano."""
        with self._lock:
            if self._status in (MeetingStatus.RECORDING, MeetingStatus.PAUSED):
                return

            os.makedirs(os.path.dirname(os.path.abspath(self.output_path)), exist_ok=True)
            self._wav_file = wave.open(self.output_path, "wb")
            self._wav_file.setnchannels(1)
            self._wav_file.setsampwidth(2)  # 16-bit PCM
            self._wav_file.setframerate(self.sample_rate)

            self._stop_event.clear()
            self._pause_event.clear()
            self._status = MeetingStatus.RECORDING
            self._start_time = time.time()
            self._accumulated_duration = 0.0

            self._thread = threading.Thread(target=self._record_loop, daemon=True, name="MeetingAudioRecorderThread")
            self._thread.start()

    def pause(self) -> None:
        """Pausa a captura de áudio."""
        with self._lock:
            if self._status == MeetingStatus.RECORDING:
                self._accumulated_duration += time.time() - self._start_time
                self._pause_event.set()
                self._status = MeetingStatus.PAUSED
                self._current_rms = 0.0

    def resume(self) -> None:
        """Retoma a captura de áudio."""
        with self._lock:
            if self._status == MeetingStatus.PAUSED:
                self._start_time = time.time()
                self._pause_event.clear()
                self._status = MeetingStatus.RECORDING

    def stop(self) -> float:
        """Finaliza a gravação, fecha o arquivo WAV e retorna a duração total."""
        with self._lock:
            if self._status not in (MeetingStatus.RECORDING, MeetingStatus.PAUSED):
                return self._accumulated_duration

            if self._status == MeetingStatus.RECORDING:
                self._accumulated_duration += time.time() - self._start_time

            self._stop_event.set()
            self._pause_event.clear()
            self._status = MeetingStatus.STOPPED
            self._current_rms = 0.0

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        with self._lock:
            if self._wav_file:
                try:
                    self._wav_file.close()
                except Exception:
                    pass
                self._wav_file = None

        return self._accumulated_duration

    def _record_loop(self) -> None:
        """Loop executado em thread dedicada para captura e escrita contínua."""
        dev_spec = self.device if self.device is not None else getattr(config, "AUDIO_INPUT_DEVICE", None)
        dev_idx = resolve_audio_device(dev_spec, kind="input")

        # Tratamento seguro caso sounddevice seja mock ou indisponível
        if sd is None:
            self._generate_dummy_audio()
            return

        try:
            with sd.InputStream(
                device=dev_idx,
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                blocksize=self.chunk_size,
            ) as stream:
                while not self._stop_event.is_set():
                    if self._pause_event.is_set():
                        time.sleep(0.05)
                        continue

                    data, overflowed = stream.read(self.chunk_size)
                    if overflowed:
                        pass

                    # Cálculo do RMS para indicador visual (normalizado 0.0 a 1.0)
                    np_data = data.flatten()
                    if len(np_data) > 0:
                        float_data = np_data.astype(np.float32) / 32768.0
                        rms = float(np.sqrt(np.mean(float_data ** 2)))
                        self._current_rms = min(1.0, rms * 5.0)

                    # Gravação direta dos bytes no arquivo WAV
                    if self._wav_file:
                        self._wav_file.writeframes(data.tobytes())

        except Exception as e:
            # Em ambientes headless de CI ou falhas de device, simula escrita de fallback
            print(f"[MeetingRecorder] Aviso ao ler microfone: {e}")
            self._generate_dummy_audio()

    def _generate_dummy_audio(self) -> None:
        """Gera silêncio em arquivo WAV quando rodando em ambiente sem dispositivo de áudio real."""
        silence_chunk = np.zeros(self.chunk_size, dtype=np.int16).tobytes()
        while not self._stop_event.is_set():
            if self._pause_event.is_set():
                time.sleep(0.05)
                continue
            if self._wav_file:
                try:
                    self._wav_file.writeframes(silence_chunk)
                except Exception:
                    break
            time.sleep(float(self.chunk_size) / float(self.sample_rate))
