import numpy as np
import wave
import os

def create_alarm_sound(output_path="assets/alarm.wav"):
    sr = 44100
    # Gera 3 beeps rápidos repetidos (4 beeps curtos de 100ms)
    t_beep = np.linspace(0, 0.1, int(sr * 0.1), False)
    tone = np.sin(2 * np.pi * 1200 * t_beep) * 0.5
    fade = np.linspace(0, 1, int(sr * 0.01))
    tone[:len(fade)] *= fade
    tone[-len(fade):] *= fade[::-1]

    silence = np.zeros(int(sr * 0.08))
    block = np.concatenate([tone, silence, tone, silence, tone, np.zeros(int(sr * 0.4))])
    
    # 2 repetições para o arquivo
    audio = np.concatenate([block, block])
    audio_int16 = (audio * 32767).astype(np.int16)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with wave.open(output_path, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sr)
        wav.writeframes(audio_int16.tobytes())
    print(f"[Geraldo] Alarme gerado em: {output_path}")

if __name__ == "__main__":
    create_alarm_sound()
