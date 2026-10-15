import sys
from audio.wakeword import WakeWordDetector
from audio.recorder import AudioRecorder
from audio.player import AudioPlayer
from brain.stt import SpeechToText
from brain.llm import BrainLLM
from brain.tts import TextToSpeech

def main():
    print("Iniciando Geraldo...")

    detector = WakeWordDetector(target_word="geraldo")
    recorder = AudioRecorder()
    stt = SpeechToText(model_size="base", device="cpu", compute_type="int8")
    llm = BrainLLM()
    player = AudioPlayer()
    tts = TextToSpeech(model_path="voz.onnx")

    print("\n[Geraldo] Sistema pronto e em modo de espera! (Ctrl+C para encerrar)\n")

    try:
        while True:
            # 1. Espera a wake word "Geraldo"
            if detector.wait_for_wake_word():
                player.play_beep()

            # 2. Grava comando do microfone
            audio_data = recorder.record_until_silence()

            # 3. Transcrição STT
            print("[Geraldo] Transcrevendo comando...")
            user_text = stt.transcribe(audio_data)

            if not user_text.strip():
                print("[Geraldo] Nada compreendido.")
                continue

            print(f"\n[Você]: {user_text}")

            # 4. Raciocínio e execução de tools
            print("[Geraldo] Pensando...")
            reply_text = llm.ask(user_text)

            print(f"[Geraldo]: {reply_text}")

            # 5. Fala a resposta por voz
            if reply_text:
                print("[Geraldo] Falando...")
                wav_path = tts.synthesize(reply_text)
                player.play(wav_path)

    except KeyboardInterrupt:
        print("\nGeraldo encerrado.")
        sys.exit(0)

if __name__ == "__main__":
    main()

