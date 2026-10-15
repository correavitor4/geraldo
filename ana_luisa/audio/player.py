# audio/player.py
import subprocess

class AudioPlayer:
    @staticmethod
    def play(audio_file: str):
        """Reproduz o arquivo de áudio via PipeWire ou ALSA."""
        if not audio_file:
            return

        try:
            subprocess.run(["pw-play", audio_file], check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            subprocess.run(["aplay", audio_file], check=True)