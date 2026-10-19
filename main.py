import sys
from audio.wakeword import WakeWordDetector
from audio.recorder import AudioRecorder
from audio.player import AudioPlayer
from brain.stt import SpeechToText
from brain.llm import BrainLLM
from brain.tts import TextToSpeech
from tools.timer import TimerManager
from core.ipc import IPCManager
import config
import time

def main():
    print("[Geraldo] Inicializando assistente...")
    TimerManager.start_background_loop()
    TimerManager.set_assistant_state("starting")

    # Inicia barramento IPC local (WebSocket)
    try:
        IPCManager.start(
            host=getattr(config, "IPC_HOST", "127.0.0.1"),
            port=getattr(config, "IPC_PORT", 8765),
            token=getattr(config, "IPC_AUTH_TOKEN", None),
            require_auth=getattr(config, "IPC_REQUIRE_AUTH", False),
        )
    except Exception as e:
        print(f"[Geraldo:IPC Error] Falha ao iniciar barramento: {e}")

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

    # Conecta o processador de comandos de texto via WebSocket (GUI / TUI)
    def handle_ipc_prompt(text: str) -> str:
        reply = llm.ask(text)
        if reply:
            speak_callback(reply)
        return reply

    IPCManager.set_prompt_handler(handle_ipc_prompt)
    IPCManager.set_cancel_handler(TimerManager.stop_all_ringing)

    print("[Geraldo] Dormindo... Diga Geraldo para acordar.")
    TimerManager.set_assistant_state("idle")

    try:
        while True:
            TimerManager.set_assistant_state("idle")

            # Se o microfone estiver mutado via Tray/GUI, não escuta wake word
            if IPCManager.is_muted():
                time.sleep(0.5)
                continue

            if detector.wait_for_wake_word():
                player.play_beep()

            TimerManager.set_assistant_state("listening")
            audio_data = recorder.record_until_silence()
            TimerManager.set_assistant_state("transcribing")
            print("[Geraldo] Transcrevendo comando...")
            user_text = stt.transcribe(audio_data)

            if not user_text.strip():
                print("[Geraldo] Nada compreendido.")
                TimerManager.set_assistant_state("idle")
                print("[Geraldo] Dormindo... Diga Geraldo para acordar.")
                continue

            print(f"[Você]: {user_text}")
            IPCManager.broadcast("transcription", {"text": user_text})

            TimerManager.set_assistant_state("thinking")
            print("[Geraldo] Pensando...")
            
            reply_text = llm.ask(user_text)

            print(f"[Geraldo]: {reply_text}")
            IPCManager.broadcast("reply", {"text": reply_text})

            if reply_text:
                TimerManager.set_assistant_state("speaking")
                print("[Geraldo] Falando...")
                speak_callback(reply_text)

            TimerManager.set_assistant_state("idle")
            print("[Geraldo] Dormindo... Diga Geraldo para acordar.")

    except KeyboardInterrupt:
        print("\nGeraldo encerrado.")
        IPCManager.stop()
        sys.exit(0)
    finally:
        IPCManager.stop()

if __name__ == "__main__":
    main()
