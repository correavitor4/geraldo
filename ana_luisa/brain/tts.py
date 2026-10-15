# brain/tts.py
import sys
import subprocess
import os

class TextToSpeech:
    def __init__(self, model_path: str = "voz.onnx"):
        print("[Geraldo] Inicializando módulo Piper TTS...")
        self.model_path = model_path
        self.output_file = "/tmp/geraldo_response.wav"
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Modelo não encontrado: {model_path}")

    def synthesize(self, text: str) -> str:
        """Sintetiza o texto para WAV usando o módulo oficial piper do venv."""
        if not text:
            return ""

        cmd = [
            sys.executable,
            "-m", "piper",
            "--model", self.model_path,
            "--output_file", self.output_file
        ]

        subprocess.run(
            cmd,
            input=text.encode("utf-8"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )

        return self.output_file