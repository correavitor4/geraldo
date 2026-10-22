import os
import numpy as np
from faster_whisper import WhisperModel
import config

class SpeechToText:
    def __init__(
        self,
        wake_model_size: str = None,
        cmd_model_size: str = None,
        device: str = "cpu",
        compute_type: str = "int8"
    ):
        if wake_model_size is None:
            wake_model_size = getattr(config, "STT_WAKE_MODEL", "base")
        if cmd_model_size is None:
            cmd_model_size = getattr(config, "STT_CMD_MODEL", "base")
        cpu_total = os.cpu_count() or 4
        print(f"[Geraldo] Inicializando STT Dual-Engine...")
        print(f"  -> Wake Word: {wake_model_size.upper()} (int8, estrito)")
        print(f"  -> Comandos:  {cmd_model_size.upper()} (int8, {cpu_total} threads)")

        self.model_wake = WhisperModel(
            wake_model_size,
            device=device,
            compute_type=compute_type,
            cpu_threads=2,
            num_workers=1
        )

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
        """Validação estrita para a wake word."""
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
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=250, threshold=0.5)
        )
        for seg in segments:
            no_speech = getattr(seg, "no_speech_prob", None)
            if isinstance(no_speech, (int, float)) and no_speech > 0.65:
                continue

            avg_logprob = getattr(seg, "avg_logprob", None)
            if isinstance(avg_logprob, (int, float)) and avg_logprob < -1.3:
                continue
            text = seg.text.strip().lower()
            if "geraldo" in text:
                return text
        return ""

    def transcribe(self, audio_data: np.ndarray) -> str:
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
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        return " ".join([seg.text.strip() for seg in segments]).strip()
