# main.py
import sys
from audio.recorder import AudioRecorder
from audio.player import AudioPlayer
from brain.stt import SpeechToText
from brain.llm import BrainLLM
from brain.tts import TextToSpeech

def main():
    print("Iniciando Geraldo...")
    recorder = AudioRecorder()
    stt = SpeechToText(model_size="base", device="cpu", compute_type="int8")
    llm = BrainLLM()
    player = AudioPlayer()
    tts = TextToSpeech(model_path="voz.onnx")

    print("\n[Geraldo] Pronto e operando! (Ctrl+C para encerrar)\n")

    try:
        while True:
            # 1. Ouvir
            audio_data = recorder.record_until_silence()

            # 2. STT
            print("[Geraldo] Transcrevendo...")
            user_text = stt.transcribe(audio_data)

            if not user_text.strip():
                continue

            print(f"\n[Você]: {user_text}")

            # 3. LLM
            print("[Geraldo] Pensando...")
            response = llm.ask(user_text)
            reply_text = response.get("content", "")

            print(f"[Geraldo]: {reply_text}")

            # 4. TTS e Playback
            if reply_text:
                print("[Geraldo] Falando...")
                wav_path = tts.synthesize(reply_text)
                player.play(wav_path)

    except KeyboardInterrupt:
        print("\nGeraldo encerrado.")
        sys.exit(0)

if __name__ == "__main__":
    main()