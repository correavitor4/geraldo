from faster_whisper import WhisperModel
import numpy as np

class SpeechToText:
    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
        print(f"[Geraldo] Carregando modelo Whisper ({model_size})...")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def transcribe_quick(self, audio_data: np.ndarray) -> str:
        if audio_data is None or len(audio_data) == 0:
            return ""
        segments, _ = self.model.transcribe(
            audio_data,
            language="pt",
            beam_size=1,
            best_of=1,
            temperature=0.0,
            initial_prompt="Geraldo.",
            vad_filter=False
        )
        return " ".join([seg.text.strip() for seg in segments]).strip()

    def transcribe(self, audio_data: np.ndarray) -> str:
        if audio_data is None or len(audio_data) == 0:
            return ""

        vocab_prompt = (
            "Geraldo, assistente virtual. Dúzia, dezena, meia dúzia, doze unidades. "
            "Eleições 2026, pesquisa eleitoral, presidente, segundo turno. "
            "Álbum BBC, Live at the BBC, Amy Winehouse, Lana Del Rey, Coldplay. "
            "Cabo OTG, Linux, Waybar, Anápolis Goiás."
        )

        segments, _ = self.model.transcribe(
            audio_data,
            language="pt",
            beam_size=5,
            initial_prompt=vocab_prompt,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=450)
        )

        text = " ".join([seg.text.strip() for seg in segments]).strip()
        return text
