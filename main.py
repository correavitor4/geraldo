import sys
from audio.wakeword import WakeWordDetector
from audio.recorder import AudioRecorder
from audio.player import AudioPlayer
from brain.stt import SpeechToText
from brain.llm import BrainLLM
from brain.tts import TextToSpeech

def main():
    print("[Geraldo] Inicializando assistente...")

    stt = SpeechToText(device="cpu", compute_type="int8")
    # Se o seu WakeWordDetector aceitar stt, usamos; caso contrário inicializa padrão
    try:
        detector = WakeWordDetector(target_word="geraldo", stt=stt)
    except TypeError:
        detector = WakeWordDetector(target_word="geraldo")

    recorder = AudioRecorder()
    player = AudioPlayer()
    tts = TextToSpeech(model_path="voz_faber.onnx")

    def speak_callback(text: str):
        wav = tts.synthesize(text)
        if wav:
            player.play(wav)

    llm = BrainLLM(speak_fn=speak_callback)

    print("[Geraldo] Dormindo... Diga Geraldo para acordar.")

    try:
        while True:
            if detector.wait_for_wake_word():
                player.play_beep()

            audio_data = recorder.record_until_silence()

            print("[Geraldo] Transcrevendo comando...")
            user_text = stt.transcribe(audio_data)

            if not user_text.strip():
                print("[Geraldo] Nada compreendido.")
                print("[Geraldo] Dormindo... Diga Geraldo para acordar.")
                continue

            print(f"[Você]: {user_text}")
            print("[Geraldo] Pensando...")
            
            reply_text = llm.ask(user_text)

            print(f"[Geraldo]: {reply_text}")

            if reply_text:
                print("[Geraldo] Falando...")
                speak_callback(reply_text)

            print("[Geraldo] Dormindo... Diga Geraldo para acordar.")

    except KeyboardInterrupt:
        print("\nGeraldo encerrado.")
        sys.exit(0)

if __name__ == "__main__":
    main()
