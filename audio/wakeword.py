import sounddevice as sd
import numpy as np
import time

class WakeWordDetector:
    def __init__(self, target_word: str = "geraldo", sample_rate: int = 16000, chunk_size: int = 1024, stt_engine=None):
        self.target_word = target_word.lower()
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.stt = stt_engine
        print("[Geraldo:Audio] Wake word escutando no microfone padrão do sistema.")

    def wait_for_wake_word(self) -> bool:
        print(f"\n[Geraldo] Dormindo... Diga {self.target_word.capitalize()} para acordar.")
        
        buffer_duration = 1.8
        buffer_len = int(self.sample_rate * buffer_duration)
        audio_buffer = np.zeros(buffer_len, dtype=np.float32)

        ambient_noise = 0.008
        speech_triggered = False
        speech_start = 0.0

        # device=None utiliza o microfone padrão definido no sistema (PipeWire/PulseAudio)
        with sd.InputStream(device=None, samplerate=self.sample_rate, channels=1, dtype='float32', blocksize=self.chunk_size) as stream:
            for _ in range(5):
                stream.read(self.chunk_size)

            while True:
                data, _ = stream.read(self.chunk_size)
                chunk = data.flatten()

                audio_buffer = np.roll(audio_buffer, -len(chunk))
                audio_buffer[-len(chunk):] = chunk

                rms = float(np.sqrt(np.mean(chunk**2)))

                if rms < ambient_noise * 1.5:
                    ambient_noise = 0.95 * ambient_noise + 0.05 * rms

                voice_threshold = max(ambient_noise * 2.8, 0.016)

                if rms > voice_threshold:
                    if not speech_triggered:
                        speech_triggered = True
                        speech_start = time.time()
                else:
                    if speech_triggered and (time.time() - speech_start > 0.4):
                        speech_triggered = False
                        
                        if self.stt:
                            peak = np.max(np.abs(audio_buffer))
                            sample = audio_buffer * (0.85 / peak) if peak > 0.01 else audio_buffer
                            transcription = self.stt.transcribe_quick(sample).lower()
                            
                            matches = ["geraldo", "eraldo", "gerald", "geral", "ei geraldo", "olá geraldo"]
                            if any(m in transcription for m in matches):
                                print(f"[Geraldo] Acordou! Palavra confirmada: '{transcription}'")
                                return True
                        else:
                            print("[Geraldo] Acordou!")
                            return True
