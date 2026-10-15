import sounddevice as sd
import numpy as np
import time

class AudioRecorder:
    def __init__(self, sample_rate: int = 16000, chunk_size: int = 1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.energy_threshold = 0.016
        self.silence_limit = 1.5

    def record_until_silence(self) -> np.ndarray:
        print("[Geraldo] Escutando... Pode falar.")
        recorded_chunks = []
        silence_start = None
        has_spoken = False
        start_time = time.time()

        # device=None utiliza o microfone padrão do sistema
        with sd.InputStream(device=None, samplerate=self.sample_rate, channels=1, dtype='float32', blocksize=self.chunk_size) as stream:
            while True:
                data, _ = stream.read(self.chunk_size)
                chunk = data.flatten()
                recorded_chunks.append(chunk)

                rms = np.sqrt(np.mean(chunk**2))

                if rms > self.energy_threshold:
                    if not has_spoken:
                        print("[Geraldo] Voz detectada...")
                        has_spoken = True
                    silence_start = None
                else:
                    if has_spoken:
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start > self.silence_limit:
                            print("[Geraldo] Silêncio detectado. Fim da gravação.")
                            break

                if not has_spoken and (time.time() - start_time > 6.0):
                    break

        audio = np.concatenate(recorded_chunks, axis=0) if recorded_chunks else np.array([], dtype=np.float32)

        peak = np.max(np.abs(audio)) if len(audio) > 0 else 0
        if peak > 0.01:
            audio = audio * (0.9 / peak)

        return audio
