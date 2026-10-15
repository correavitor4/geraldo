# audio/recorder.py
import queue
import time
import numpy as np
import sounddevice as sd
import torch
from config import SAMPLE_RATE, CHUNK_SIZE, VAD_THRESHOLD, SILENCE_LIMIT_SEC

class AudioRecorder:
    def __init__(self):
        print("Carregando Silero VAD...")
        self.model, _ = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            trust_repo=True
        )
        self.audio_queue = queue.Queue()

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"Status do microfone: {status}", flush=True)
        self.audio_queue.put(indata.copy())

    def record_until_silence(self) -> np.ndarray:
        self.audio_queue.queue.clear()
        self.model.reset_states()

        audio_frames = []
        is_speaking = False
        silence_start = None

        print("\n[Geraldo] Escutando... Pode falar.")

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=CHUNK_SIZE,
            callback=self._audio_callback
        ):
            while True:
                chunk = self.audio_queue.get()
                audio_frames.append(chunk)

                tensor_chunk = torch.from_numpy(chunk.squeeze())
                speech_prob = self.model(tensor_chunk, SAMPLE_RATE).item()

                if speech_prob > VAD_THRESHOLD:
                    if not is_speaking:
                        print("[Geraldo] Voz detectada...")
                        is_speaking = True
                    silence_start = None
                else:
                    if is_speaking:
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start >= SILENCE_LIMIT_SEC:
                            print("[Geraldo] Silêncio detectado. Fim da gravação.")
                            break

        return np.concatenate(audio_frames, axis=0).flatten()