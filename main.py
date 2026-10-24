import sys
import threading
import queue
import re
import time
import config

class _TeeWriter:
    def __init__(self, original_stream, log_file):
        self.original_stream = original_stream
        self.log_file = log_file

    def write(self, message):
        if self.original_stream:
            try:
                self.original_stream.write(message)
                self.original_stream.flush()
            except Exception:
                pass
        if self.log_file:
            try:
                self.log_file.write(message)
                self.log_file.flush()
            except Exception:
                pass

    def flush(self):
        if self.original_stream:
            try:
                self.original_stream.flush()
            except Exception:
                pass
        if self.log_file:
            try:
                self.log_file.flush()
            except Exception:
                pass


if __name__ == "__main__":
    if any(arg in ("--tui", "tui", "-t") for arg in sys.argv[1:]):
        from ui.tui import run_tui
        run_tui()
        sys.exit(0)

    if "-m" in sys.argv and "piper" in sys.argv:
        from piper import __main__ as piper_main
        idx = sys.argv.index("piper")
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
        piper_main.main()
        sys.exit(0)

from audio.wakeword import WakeWordDetector
from audio.recorder import AudioRecorder
from audio.player import AudioPlayer
from brain.stt import SpeechToText
from brain.llm import BrainLLM
from brain.tts import TextToSpeech
from tools.timer import TimerManager
from tools.system import SystemTools
from tools.calendar import CalendarTools
from core.ipc import IPCManager
from core.paths import get_user_data_dir

def main():
    try:
        data_dir = get_user_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        log_f = open(data_dir / "geraldo.log", "a", encoding="utf-8", errors="replace")
        sys.stdout = _TeeWriter(sys.stdout, log_f)
        sys.stderr = _TeeWriter(sys.stderr, log_f)
        print(f"\n=== [Geraldo Daemon Iniciado: {time.strftime('%Y-%m-%d %H:%M:%S')}] ===")
    except Exception:
        pass

    print("[Geraldo] Inicializando assistente...")
    TimerManager.start_background_loop()
    TimerManager.set_assistant_state("starting")
    # Inicia pré-cache periódico de clima em background (atualiza a cada 15 min)
    SystemTools.start_weather_poller()
    # Inicia pré-cache periódico da agenda Google em background (atualiza a cada 5 min)
    CalendarTools.start_calendar_poller()

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

    import queue
    import re

    def split_into_sentences(text: str) -> list[str]:
        raw_parts = re.split(r'(?<=[.!?])\s+', text.strip())
        parts = [p.strip() for p in raw_parts if p.strip()]
        return parts if parts else [text.strip()]

    def speak_callback(text: str, on_first_audio = None):
        sentences = split_into_sentences(text)
        if len(sentences) <= 1:
            t0 = time.perf_counter()
            wav = tts.synthesize(text)
            ms_tts = (time.perf_counter() - t0) * 1000
            if wav:
                if on_first_audio:
                    on_first_audio()
                print(f"[Geraldo:TTS] Síntese de áudio gerada em {ms_tts:.1f}ms")
                player.play(wav)
            return

        # Pipeline streaming: sintetiza a próxima frase enquanto a anterior toca no alto-falante
        audio_queue = queue.Queue(maxsize=3)
        synthesis_done = threading.Event()

        def producer():
            for i, sent in enumerate(sentences):
                t0 = time.perf_counter()
                try:
                    wav_file = tts.synthesize(sent)
                    ms_sent = (time.perf_counter() - t0) * 1000
                    audio_queue.put((i, wav_file, ms_sent))
                except Exception as e:
                    print(f"[Geraldo:TTS Pipeline Error]: {e}")
            synthesis_done.set()

        threading.Thread(target=producer, daemon=True).start()

        first_played = False
        while True:
            try:
                item = audio_queue.get(timeout=0.1)
                i, wav_file, ms_sent = item
                if not first_played:
                    if on_first_audio:
                        on_first_audio()
                    first_played = True
                print(f"[Geraldo:TTS] Frase {i+1}/{len(sentences)} sintetizada em {ms_sent:.1f}ms -> Tocando")
                if wav_file:
                    player.play(wav_file)
                audio_queue.task_done()
            except queue.Empty:
                if synthesis_done.is_set() and audio_queue.empty():
                    break

    llm = BrainLLM(speak_fn=speak_callback)
    llm.warmup_async()

    # Conecta o processador de comandos de texto via WebSocket (GUI / TUI)
    def handle_ipc_prompt(text: str) -> str:
        t0 = time.perf_counter()
        print(f"[Geraldo:IPC] Prompt recebido: \"{text}\"")
        reply = llm.ask(text)
        ms_ipc = (time.perf_counter() - t0) * 1000
        print(f"[Geraldo:IPC] Resposta formulada em {ms_ipc:.1f}ms")
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
            # Garante o modelo carregado em paralelo enquanto o usuário fala e o STT transcreve
            llm.warmup_async()
            t_rec0 = time.perf_counter()
            audio_data = recorder.record_until_silence()
            ms_rec = (time.perf_counter() - t_rec0) * 1000
            t_speech_end = time.perf_counter()

            TimerManager.set_assistant_state("transcribing")
            print(f"[Geraldo:Audio] Áudio capturado em {ms_rec:.1f}ms. Transcrevendo...")
            t_stt0 = time.perf_counter()
            user_text = stt.transcribe(audio_data)
            ms_stt = (time.perf_counter() - t_stt0) * 1000
            print(f"[Geraldo:STT] Transcrito em {ms_stt:.1f}ms: \"{user_text}\"")

            if not user_text.strip():
                print("[Geraldo] Nada compreendido.")
                TimerManager.set_assistant_state("idle")
                print("[Geraldo] Dormindo... Diga Geraldo para acordar.")
                continue

            print(f"[Você]: {user_text}")
            IPCManager.broadcast("transcription", {"text": user_text})

            TimerManager.set_assistant_state("thinking")
            t_brain0 = time.perf_counter()
            reply_text = llm.ask(user_text)
            ms_brain = (time.perf_counter() - t_brain0) * 1000
            print(f"[Geraldo:Brain] Cérebro processou em {ms_brain:.1f}ms")

            print(f"[Geraldo]: {reply_text}")
            IPCManager.broadcast("reply", {"text": reply_text})

            if reply_text:
                TimerManager.set_assistant_state("speaking")
                def on_start_speaking():
                    ms_ttfa = (time.perf_counter() - t_speech_end) * 1000
                    print(f"[Geraldo:Latência] ⚡ TTFA (Tempo até a 1ª resposta falada pós-voz): {ms_ttfa:.1f}ms")

                speak_callback(reply_text, on_first_audio=on_start_speaking)
                ms_e2e = (time.perf_counter() - t_speech_end) * 1000
                print(f"[Geraldo:Latência] 🏁 Interação completa concluída em {ms_e2e:.1f}ms")

            TimerManager.set_assistant_state("idle")
            print("[Geraldo] Dormindo... Diga Geraldo para acordar.")

    except KeyboardInterrupt:
        print("\nGeraldo encerrado.")
        IPCManager.stop()
        sys.exit(0)
    finally:
        IPCManager.stop()

if __name__ == "__main__":
    if any(arg in ("--tui", "tui", "-t") for arg in sys.argv[1:]):
        from ui.tui import run_tui
        run_tui()
    else:
        main()

