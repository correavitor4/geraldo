import sys
import time
from brain.stt import SpeechToText
from brain.llm import BrainLLM
from brain.tts import TextToSpeech
from audio.wakeword import WakeWordDetector
from audio.recorder import AudioRecorder
from audio.feedback import play_wake_beep
from ui.waybar import set_state

def main():
    print("[Geraldo] Inicializando assistente...")
    set_state("dormindo")
    
    stt = SpeechToText()
    llm = BrainLLM()
    tts = TextToSpeech()
    
    wakeword = WakeWordDetector(stt_engine=stt)
    recorder = AudioRecorder()

    while True:
        try:
            # 1. Dormindo
            set_state("dormindo")
            if wakeword.wait_for_wake_word():
                # Toca som estilo Alexa
                play_wake_beep()
                time.sleep(0.18)

                # 2. Escutando
                set_state("escutando")
                audio_data = recorder.record_until_silence()
                if audio_data is None or len(audio_data) == 0:
                    continue

                # 3. Pensando (Whisper + LLM + Tools)
                set_state("pensando")
                print("[Geraldo] Transcrevendo comando...")
                user_text = stt.transcribe(audio_data)
                if not user_text:
                    continue

                print(f"[Você]: {user_text}")

                print("[Geraldo] Pensando...")
                response_text = llm.ask(user_text)

                # 4. Falando
                if response_text:
                    set_state("falando")
                    print(f"[Geraldo]: {response_text}")
                    print("[Geraldo] Falando...")
                    tts.speak(response_text)

        except KeyboardInterrupt:
            set_state("dormindo")
            print("\n[Geraldo] Encerrando...")
            sys.exit(0)
        except Exception as e:
            print(f"[Geraldo:Erro]: {e}")
            set_state("dormindo")
            time.sleep(1)

if __name__ == "__main__":
    main()
