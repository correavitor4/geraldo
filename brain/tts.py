# brain/tts.py
import sys
import subprocess
import os
import threading
from core.paths import resolve_model_path, get_temp_dir

class TextToSpeech:
    def __init__(self, model_path: str = "voz.onnx"):
        print("[Geraldo] Inicializando módulo Piper TTS...")
        resolved = resolve_model_path(model_path)
        if resolved:
            self.model_path = str(resolved)
        elif os.path.exists(model_path):
            self.model_path = model_path
        else:
            raise FileNotFoundError(f"Modelo não encontrado: {model_path}")

        self.output_file = "/tmp/geraldo_response.wav"

    def synthesize(self, text: str) -> str:
        """Sintetiza o texto para WAV usando o módulo oficial piper do venv."""
        if not text:
            return ""

        temp_dir = os.environ.get("GERALDO_TEMP_DIR", "/tmp")
        out_path = os.path.join(temp_dir, f"geraldo_response_{threading.get_ident()}.wav")
        cmd = [
            sys.executable,
            "-m", "piper",
            "--model", self.model_path,
            "--output_file", out_path
        ]

        subprocess.run(
            cmd,
            input=text.encode("utf-8"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )

        return out_path
    def speak(self, text: str):
        """Sintetiza e reproduz o áudio imediatamente via PipeWire."""
        wav_path = self.synthesize(text)
        if wav_path:
            import shutil
            player = "pw-play" if shutil.which("pw-play") else "aplay"
            subprocess.run(
                [player, wav_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
