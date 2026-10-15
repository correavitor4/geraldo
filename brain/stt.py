# brain/stt.py
import numpy as np
from faster_whisper import WhisperModel

class SpeechToText:
    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
        print(f"[Geraldo] Carregando modelo Whisper ({model_size}) na {device.upper()}...")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def transcribe(self, audio_data: np.ndarray) -> str:
        if len(audio_data) == 0:
            return ""

        segments, _ = self.model.transcribe(
            audio_data,
            beam_size=1,
            language="pt",
            task="transcribe",
            vad_filter=False
        )

        full_text = " ".join([segment.text.strip() for segment in segments]).strip()
        return full_text