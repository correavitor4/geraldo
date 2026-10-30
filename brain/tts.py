# brain/tts.py
import sys
import subprocess
import os
import threading
from core.paths import resolve_model_path, get_temp_dir, resolve_espeak_data_dir, is_frozen

class TextToSpeech:
    def __init__(self, model_path: str = "voz.onnx"):
        print("[Geraldo] Inicializando módulo Piper TTS...")
        resolved = resolve_model_path(model_path)
        if resolved:
            self.model_path = str(resolved)
        elif os.path.exists(model_path):
            self.model_path = model_path
        elif any(k in model_path.lower() for k in ("voz_faber", "voz.onnx", "pt_br-faber")):
            from core.paths import ensure_model_available
            self.model_path = str(ensure_model_available(model_path))
        else:
            raise FileNotFoundError(f"Modelo não encontrado: {model_path}")

        self.output_file = "/tmp/geraldo_response.wav"
        self._voice = None
        try:
            from piper.voice import PiperVoice
            if os.path.exists(self.model_path):
                espeak_dir = resolve_espeak_data_dir()
                if espeak_dir:
                    self._voice = PiperVoice.load(self.model_path, espeak_data_dir=str(espeak_dir))
                else:
                    self._voice = PiperVoice.load(self.model_path)
        except Exception as e:
            print(f"[Geraldo:TTS] Aviso ao carregar voz neural: {e}")
            self._voice = None

    def synthesize(self, text: str) -> str:
        """Sintetiza o texto para WAV usando o módulo oficial piper do venv ou in-process."""
        if not text:
            return ""

        temp_dir = os.environ.get("GERALDO_TEMP_DIR", "/tmp")
        try:
            os.makedirs(temp_dir, exist_ok=True)
        except Exception:
            temp_dir = str(get_temp_dir())
            os.makedirs(temp_dir, exist_ok=True)

        out_path = os.path.join(temp_dir, f"geraldo_response_{threading.get_ident()}.wav")

        # Prioriza síntese in-process de alta performance se a voz estiver carregada
        if self._voice is not None:
            try:
                import wave
                with wave.open(out_path, "wb") as wav_file:
                    self._voice.synthesize_wav(text, wav_file)
                return out_path
            except Exception as e:
                print(f"[Geraldo:TTS] Aviso: síntese in-process falhou ({e}), tentando subprocesso...")

        # Fallback via subprocesso (módulo piper CLI)
        python_bin = sys.executable
        flags = ["-X", "utf8"]

        if is_frozen():
            import shutil
            cand_py = shutil.which("python") or shutil.which("python3") or shutil.which("py")
            if cand_py:
                python_bin = cand_py
            else:
                flags = []

        cmd = [python_bin] + flags + [
            "-m", "piper",
            "--model", self.model_path,
            "--output_file", out_path
        ]

        espeak_dir = resolve_espeak_data_dir()
        if espeak_dir:
            cmd.extend(["--espeak-data", str(espeak_dir)])

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        if espeak_dir:
            env["ESPEAK_DATA_DIR"] = str(espeak_dir)
            env["PIPER_ESPEAK_DATA_DIR"] = str(espeak_dir)

        try:
            subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
                check=True
            )
            return out_path
        except Exception as e:
            print(f"[Geraldo:TTS Error] Falha na síntese de áudio por subprocesso: {e}")
            return ""

    def speak(self, text: str):
        """Sintetiza e reproduz o áudio imediatamente via PipeWire/ALSA ou áudio nativo do sistema."""
        wav_path = self.synthesize(text)
        if not wav_path:
            return

        import shutil
        player = "pw-play" if shutil.which("pw-play") else ("afplay" if shutil.which("afplay") else "aplay")
        try:
            subprocess.run(
                [player, wav_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except (FileNotFoundError, OSError, subprocess.SubprocessError):
            from audio.player import AudioPlayer
            AudioPlayer.play(wav_path)

