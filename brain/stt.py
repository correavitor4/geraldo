import os
import shutil
from pathlib import Path
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
            "reunião, ata, ata executiva, gravar reunião, iniciar reunião, pausar reunião, "
            "retomar reunião, encerrar reunião, gerar ata, pauta da reunião, conferência, "
            "Anápolis Goiás."
        )

        self._vad_available = self._check_and_restore_vad()

    def _check_and_restore_vad(self) -> bool:
        """
        Verifica se o modelo ONNX de VAD (silero_vad_v6.onnx) está disponível para o faster_whisper.
        Caso esteja ausente no diretório de assets do faster_whisper (comum em binários PyInstaller),
        tenta restaurá-lo a partir dos diretórios de recursos da aplicação.
        """
        try:
            import faster_whisper.vad as fw_vad
            assets_dir = fw_vad.get_assets_path()
            target_vad = os.path.join(assets_dir, "silero_vad_v6.onnx")
            if os.path.isfile(target_vad) and os.path.getsize(target_vad) > 1000:
                return True

            from core.paths import resolve_asset_path, resolve_model_path, get_user_data_dir, get_base_dir
            candidates = [
                resolve_asset_path("silero_vad_v6.onnx"),
                resolve_model_path("silero_vad_v6.onnx"),
                get_base_dir() / "assets" / "silero_vad_v6.onnx",
                get_user_data_dir() / "models" / "silero_vad_v6.onnx",
                get_user_data_dir() / "assets" / "silero_vad_v6.onnx",
            ]
            for cand in candidates:
                if cand and os.path.isfile(str(cand)) and os.path.getsize(str(cand)) > 1000:
                    os.makedirs(assets_dir, exist_ok=True)
                    shutil.copy2(str(cand), target_vad)
                    print(f"[Geraldo:STT] Modelo Silero VAD localizado e carregado em assets: {cand}")
                    return True
        except Exception as e:
            print(f"[Geraldo:STT] Aviso na checagem do modelo VAD: {e}")
        return False

    def transcribe_quick(self, audio_data: np.ndarray) -> str:
        """Validação estrita para a wake word com fallback seguro."""
        if audio_data is None or len(audio_data) == 0:
            return ""

        def _evaluate(segments):
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

        if self._vad_available:
            try:
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
                return _evaluate(segments)
            except Exception as e:
                print(f"[Geraldo:STT] VAD wake indisponível ({e}). Alternando para transcrição direta...")
                self._vad_available = False

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
        return _evaluate(segments)

    def transcribe(self, audio_data: np.ndarray) -> str:
        """Transcreve comando do usuário com tolerância a falhas no VAD."""
        if audio_data is None or len(audio_data) == 0:
            return ""

        if self._vad_available:
            try:
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
            except Exception as e:
                print(f"[Geraldo:STT] VAD indisponível ({e}). Transcrevendo diretamente sem VAD filter...")
                self._vad_available = False

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
