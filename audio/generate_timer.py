import numpy as np
import wave
import os

def create_timer_sound(output_path="assets/timer.wav"):
    sr = 44100
    
    # Função para gerar um beep puro de timer (com harmônicos sutis de buzzer piezoelétrico)
    def make_beep(duration=0.09, freq=2048.0):
        t = np.linspace(0, duration, int(sr * duration), False)
        # Fundamental + leve 2º harmônico
        tone = 0.7 * np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * (freq * 2) * t)
        # Envelope de fade para suavizar e evitar estalos
        fade_len = int(sr * 0.005)
        fade_in = np.linspace(0, 1, fade_len)
        fade_out = np.linspace(1, 0, fade_len)
        tone[:fade_len] *= fade_in
        tone[-fade_len:] *= fade_out
        return tone

    beep = make_beep(0.09, 2048.0)
    short_silence = np.zeros(int(sr * 0.07))
    rest_silence = np.zeros(int(sr * 0.68))

    # Padrão clássico de timer: Beep-Beep... silêncio... Beep-Beep... silêncio
    cycle = np.concatenate([beep, short_silence, beep, rest_silence])
    
    # 2 ciclos para formar um bloco de 2 segundos que faz loop perfeito
    audio = np.concatenate([cycle, cycle])
    audio_int16 = (audio * 32767).astype(np.int16)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with wave.open(output_path, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sr)
        wav.writeframes(audio_int16.tobytes())
    print(f"[Geraldo] Som de timer gerado em: {output_path}")

if __name__ == "__main__":
    create_timer_sound()
