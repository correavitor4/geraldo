import os
import numpy as np
from faster_whisper import WhisperModel

class SpeechToText:
    def __init__(
        self,
        wake_model_size: str = "tiny",
        cmd_model_size: str = "small",
        device: str = "cpu",
        compute_type: str = "int8"
    ):
        cpu_total = os.cpu_count() or 4
        print(f"[Geraldo] Inicializando STT Dual-Engine...")
        print(f"  -> Wake Word: {wake_model_size.upper()} (int8, 2 threads)")
        print(f"  -> Comandos:  {cmd_model_size.upper()} (int8, {cpu_total} threads)")

        # Modelo leve para o loop de escuta contínua (wake word)
        self.model_wake = WhisperModel(
            wake_model_size,
            device=device,
            compute_type=compute_type,
            cpu_threads=2,
            num_workers=1
        )

        # Modelo robusto para transcrever o comando após acordar
        self.model_cmd = WhisperModel(
            cmd_model_size,
            device=device,
            compute_type=compute_type,
            cpu_threads=cpu_total,
            num_workers=1
        )

        self.vocab_prompt = (
            "Geraldo, assistente virtual. Que horas são, previsão do tempo, clima, "
            "agenda do Google, compromissos, timer, alarme, tocar música, YouTube Music, "
            "Anápolis Goiás."
        )

    def transcribe_quick(self, audio_data: np.ndarray) -> str:
        """Usado exclusivamente para detectar a wake word ('Geraldo') rapidamente."""
        if audio_data is None or len(audio_data) == 0:
            return ""

        segments, _ = self.model_wake.transcribe(
            audio_data,
            language="pt",
            beam_size=1,
            best_of=1,
            temperature=0.0,
            initial_prompt="Geraldo.",
            condition_on_previous_text=False,
            vad_filter=False
        )
        return " ".join([seg.text.strip() for seg in segments]).strip()

    def transcribe(self, audio_data: np.ndarray) -> str:
        """Usado para o comando de voz completo após o assistente acordar."""
        if audio_data is None or len(audio_data) == 0:
            return ""

        segments, _ = self.model_cmd.transcribe(
            audio_data,
            language="pt",
            beam_size=1,
            best_of=1,
            temperature=0.0,
            initial_prompt=self.vocab_prompt,
            condition_on_previous_text=False,
            vad_filter=False
        )
        return " ".join([seg.text.strip() for seg in segments]).strip()
