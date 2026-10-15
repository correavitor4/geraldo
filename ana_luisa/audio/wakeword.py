import collections
import time
import numpy as np
import sounddevice as sd
import torch
from faster_whisper import WhisperModel
from config import SAMPLE_RATE

class WakeWordDetector:
    def __init__(self, target_word: str = "geraldo"):
        self.target_word = target_word.lower()
        print(f"[Geraldo] Carregando detector de wake word ({self.target_word})...")

        # Modelo tiny leve rodando em INT8
        self.tiny_model = WhisperModel("tiny", device="cpu", compute_type="int8")

        # Silero VAD para detecção de presença de voz
        self.vad_model, _ = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            trust_repo=True
        )

    def wait_for_wake_word(self) -> bool:
        print(f"\n[Geraldo] Dormindo... Diga Geraldo para acordar.")

        # Janela deslizante de 1.5s
        buffer_len = int(SAMPLE_RATE * 1.5)
        audio_ring = collections.deque(maxlen=buffer_len)
        block_size = 512

        speech_frames = 0
        cooldown_until = 0

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", blocksize=block_size) as stream:
            while True:
                data, _ = stream.read(block_size)
                samples = data.flatten()
                audio_ring.extend(samples)

                tensor_chunk = torch.from_numpy(samples)
                prob = self.vad_model(tensor_chunk, SAMPLE_RATE).item()

                if prob > 0.6:
                    speech_frames += 1
                else:
                    speech_frames = max(0, speech_frames - 1)

                # Se detectou voz consistente por pelo menos ~0.35s
                if speech_frames >= 11 and time.time() > cooldown_until:
                    audio_segment = np.array(audio_ring, dtype=np.float32)

                    segments, _ = self.tiny_model.transcribe(
                        audio_segment,
                        beam_size=1,
                        language="pt",
                        vad_filter=False
                    )

                    raw_text = " ".join([seg.text.strip().lower() for seg in segments])
                    cleaned = raw_text.replace(",", "").replace(".", "").replace("!", "").replace("?", "").strip()

                    # Verifica se o nome Geraldo foi falado
                    if "geraldo" in cleaned or "gerald" in cleaned:
                        print(f"[Geraldo] Acordou! Detectado: {raw_text}")
                        return True

                    cooldown_until = time.time() + 1.0
                    speech_frames = 0

