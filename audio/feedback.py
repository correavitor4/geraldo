import subprocess
import os

BEEP_PATH = os.path.expanduser("~/projects/geraldo/assets/wake_alexa.wav")

def play_wake_beep():
    """Toca o tom de ativação em segundo plano sem bloquear a gravação."""
    if os.path.exists(BEEP_PATH):
        subprocess.Popen(
            ["pw-play", BEEP_PATH],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
