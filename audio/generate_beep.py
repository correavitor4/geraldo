import numpy as np
import wave
import os

def create_alexa_beep(output_path="assets/wake_alexa.wav"):
    sr = 44100
    
    # Parâmetros dos tons (B5 -> E6)
    f1, d1 = 987.77, 0.08   # 80ms
    f2, d2 = 1318.51, 0.12  # 120ms
    
    # Onda 1
    t1 = np.linspace(0, d1, int(sr * d1), False)
    tone1 = np.sin(2 * np.pi * f1 * t1)
    # Fade in/out suave
    fade_len = int(sr * 0.01)
    fade = np.linspace(0, 1, fade_len)
    tone1[:fade_len] *= fade
    tone1[-fade_len:] *= fade[::-1]

    # Onda 2
    t2 = np.linspace(0, d2, int(sr * d2), False)
    tone2 = np.sin(2 * np.pi * f2 * t2)
    tone2[:fade_len] *= fade
    tone2[-fade_len:] *= fade[::-1]

    # Combina as duas notas com breve sobreposição harmônica
    audio = np.concatenate([tone1, tone2])
    
    # Volume confortável
    audio = audio * 0.45
    audio_int16 = (audio * 32767).astype(np.int16)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with wave.open(output_path, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sr)
        wav.writeframes(audio_int16.tobytes())

    print(f"[Geraldo] Beep gerado em: {output_path}")

if __name__ == "__main__":
    create_alexa_beep()
