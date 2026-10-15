import shutil
import subprocess
import numpy as np
import sounddevice as sd

class AudioPlayer:
    @staticmethod
    def play(audio_file: str):
        if not audio_file:
            return

        players = [
            ["pw-play", audio_file],
            ["paplay", audio_file],
            ["aplay", audio_file],
            ["mpv", "--no-video", audio_file],
            ["ffplay", "-nodisp", "-autoexit", audio_file]
        ]

        for cmd in players:
            if shutil.which(cmd[0]):
                try:
                    subprocess.run(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=True
                    )
                    return
                except subprocess.CalledProcessError:
                    continue

        print("[Player] Falha ao reproduzir áudio via utilitários do sistema.")

    @staticmethod
    def play_beep():
        sample_rate = 16000

        def make_tone(freq, duration, volume=0.15):
            t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
            envelope = np.sin(np.pi * np.linspace(0, 1, len(t))) ** 2
            return volume * np.sin(2 * np.pi * freq * t) * envelope

        # Tom harmônico duplo ascendente (Mi 659 Hz -> Sol# 830 Hz)
        tone1 = make_tone(659.25, 0.08, volume=0.10)
        gap = np.zeros(int(sample_rate * 0.02))
        tone2 = make_tone(830.61, 0.12, volume=0.14)

        chime = np.concatenate([tone1, gap, tone2]).astype(np.float32)
        sd.play(chime, samplerate=sample_rate)
        sd.wait()

