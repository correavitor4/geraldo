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

        # Fallback nativo para Windows ou sistemas sem utilitários de linha de comando
        import sys
        if sys.platform == "win32":
            try:
                import winsound
                winsound.PlaySound(audio_file, winsound.SND_FILENAME)
                return
            except Exception:
                pass

        try:
            import wave
            with wave.open(audio_file, 'rb') as wf:
                sr = wf.getframerate()
                frames = wf.readframes(wf.getnframes())
                dtype = np.int16 if wf.getsampwidth() == 2 else np.int32
                audio = np.frombuffer(frames, dtype=dtype)
                sd.play(audio, samplerate=sr)
                sd.wait()
                return
        except Exception:
            pass

        print("[Player] Falha ao reproduzir áudio via utilitários do sistema.")

    @staticmethod
    def play_beep(volume: float = None):
        if volume is None:
            try:
                import config
                volume = getattr(config, "BEEP_VOLUME", 0.50)
            except Exception:
                volume = 0.50

        sample_rate = 16000

        def make_tone(freq, duration, vol=0.50):
            t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
            envelope = np.sin(np.pi * np.linspace(0, 1, len(t))) ** 2
            return vol * np.sin(2 * np.pi * freq * t) * envelope

        # Tom harmônico duplo ascendente (Mi 659 Hz -> Sol# 830 Hz) com volume reforçado
        tone1 = make_tone(659.25, 0.08, vol=volume * 0.85)
        gap = np.zeros(int(sample_rate * 0.02))
        tone2 = make_tone(830.61, 0.12, vol=volume)

        chime = np.concatenate([tone1, gap, tone2]).astype(np.float32)
        chime = np.clip(chime, -0.95, 0.95)
        sd.play(chime, samplerate=sample_rate)
        sd.wait()

