import collections
import json
import urllib.request
import urllib.error
import re
import datetime
import random
import threading
from config import OLLAMA_HOST, LLM_MODEL, SYSTEM_PROMPT
from brain.nlu import IntentEngine
from tools.system import SystemTools
from tools.ytmusic import YTMusicPlayer
from tools.news import NewsTools
from tools.search import WebSearchTools
from tools.timer import TimerManager
from tools.calendar import CalendarTools
from tools.hyprland import HyprlandTools
from tools.waybar import WaybarTools

TimerManager.start_background_loop()

LLM_OPTIONS = {
    "temperature": 0.2,
    "num_ctx": 1024,
    "num_predict": 90
}

def phonetize_time_patterns(text: str) -> str:
    horas_map = {
        0: "meia-noite", 1: "uma", 2: "duas", 3: "três", 4: "quatro",
        5: "cinco", 6: "seis", 7: "sete", 8: "oito", 9: "nove",
        10: "dez", 11: "onze", 12: "meio-dia",
        13: "uma da tarde", 14: "duas da tarde", 15: "três da tarde",
        16: "quatro da tarde", 17: "cinco da tarde", 18: "seis da tarde",
        19: "sete da noite", 20: "oito da noite", 21: "nove da noite",
        22: "dez da noite", 23: "onze da noite"
    }

    def _format_h_m(h: int, minute: int) -> str:
        if h == 0:
            return "à meia-noite" if minute == 0 else f"à meia-noite e {'meia' if minute == 30 else minute}"
        if h == 12:
            return "ao meio-dia" if minute == 0 else f"ao meio-dia e {'meia' if minute == 30 else minute}"

        nome_h = horas_map.get(h, str(h))
        if minute == 0:
            artigo = "à " if h in [1, 13] else "às "
            return f"{artigo}{nome_h}"
        h_base = h if h <= 12 else (h - 12)
        sufixo = " da tarde" if 12 < h < 18 else (" da noite" if h >= 18 else " da manhã")
        art = "à " if h_base in [1, 13] else "às "
        if minute == 30:
            return f"{art}{horas_map.get(h_base, str(h_base))} e meia{sufixo}"
        return f"{art}{horas_map.get(h_base, str(h_base))} e {minute}{sufixo}"

    def repl_time_colon(m):
        return _format_h_m(int(m.group(2)), int(m.group(3)))

    def repl_time_h(m):
        return _format_h_m(int(m.group(2)), int(m.group(3)) if m.group(3) else 0)

    text = re.sub(r'(?:\b(às|as|à|a|ao|aos)\s+)?\b(\d{1,2}):(\d{2})\b', repl_time_colon, text, flags=re.IGNORECASE)
    text = re.sub(r'(?:\b(às|as|à|a|ao|aos)\s+)?\b(\d{1,2})h(\d{2})?\b', repl_time_h, text, flags=re.IGNORECASE)
    return text

def clean_for_speech(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"#+\s*", "", text)
    text = re.sub(r"^[-\*]\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r'[#*`_~\[\]()"\']', '', text)
    text = phonetize_time_patterns(text)
    return text.strip()


class BrainLLM:
    def __init__(self, speaker=None, speak_fn=None, max_history_turns: int = 4):
        print("[Geraldo] Treinando classificador NLU (Scikit-Learn)...")
        self.nlu = IntentEngine(confidence_threshold=0.38)
        self.speaker = speaker
        self.speak_fn = speak_fn
        self.api_url = f"{OLLAMA_HOST}/api/chat"
        self.history = collections.deque(maxlen=max_history_turns)
        self._fallback_tts = None
        self._fallback_player = None

    def reset_memory(self):
        self.history.clear()
        print("[Geraldo:Memoria] Histórico limpo.")

    def _do_speak_sync(self, text: str):
        try:
            if self.speak_fn:
                self.speak_fn(text)
            elif self.speaker and hasattr(self.speaker, "speak"):
                self.speaker.speak(text)
            elif self.speaker and hasattr(self.speaker, "synthesize"):
                from audio.player import AudioPlayer
                if not self._fallback_player:
                    self._fallback_player = AudioPlayer()
                wav = self.speaker.synthesize(text)
                if wav:
                    self._fallback_player.play(wav)
            else:
                from brain.tts import TextToSpeech
                from audio.player import AudioPlayer
                if not self._fallback_tts:
                    self._fallback_tts = TextToSpeech(model_path="voz_faber.onnx")
                if not self._fallback_player:
                    self._fallback_player = AudioPlayer()
                wav = self._fallback_tts.synthesize(text)
                if wav:
                    self._fallback_player.play(wav)
        except Exception as e:
            print(f"[Geraldo:Filler Audio Error]: {e}")

    def _start_filler_thread(self, text: str) -> threading.Thread:
        t = threading.Thread(target=self._do_speak_sync, args=(text,), daemon=True)
        t.start()
        return t

    def _post_json(self, payload: dict) -> dict:
        req = urllib.request.Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _summarize_with_llm(self, instruction: str, content: str) -> str:
        try:
            res = self._post_json({
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": content}
                ],
                "stream": False,
                "keep_alive": -1,
                "options": LLM_OPTIONS
            })
            reply = res.get("message", {}).get("content", "").strip()
            return clean_for_speech(reply) if reply else clean_for_speech(content)
        except Exception as e:
            print(f"[Geraldo:LLM Error]: {e}")
            return clean_for_speech(content)

    def ask(self, user_prompt: str) -> str:
        lowered = user_prompt.lower()
        if any(cmd in lowered for cmd in ["esquece o que conversamos", "esquecer conversa", "limpar memória", "limpar memoria", "novo assunto"]):
            self.reset_memory()
            return "Memória recente apagada."

        intent, confidence, slots = self.nlu.predict(user_prompt)
        print(f"[Geraldo:NLU] Intenção: '{intent}' (confiança: {confidence:.2f}) | Slots: {slots}")

        # 1. Respostas 100% Determinísticas (Zero LLM, Zero Latência)
        if intent == "get_time":
            return clean_for_speech(SystemTools.get_current_time())

        if intent == "thanks":
            self.history.clear()
            return "Por nada! Sempre às ordens."

        if intent == "greeting_morning":
            w = SystemTools.get_weather("hoje")
            a = CalendarTools.get_events("hoje")
            return clean_for_speech(f"Bom dia! {w} {a}")

        if intent == "list_timers":
            return clean_for_speech(TimerManager.get_active_summary())

        if intent == "cancel_timers":
            query_item = slots.get("query", "")
            return clean_for_speech(str(TimerManager.cancel_item(query_item)))

        if intent == "pause_timer":
            query_item = slots.get("query", "")
            return clean_for_speech(str(TimerManager.pause_timer(query_item)))

        if intent == "resume_timer":
            query_item = slots.get("query", "")
            return clean_for_speech(str(TimerManager.resume_timer(query_item)))

        if intent == "set_alarm":
            res = TimerManager.add_alarm(
                hour=slots.get("hour", 8),
                minute=slots.get("minute", 0),
                label=slots.get("label", "Alarme")
            )
            return clean_for_speech(str(res))

        if intent == "set_timer":
            res = TimerManager.add_timer(
                hours=slots.get("hours", 0),
                minutes=slots.get("minutes", 5),
                seconds=slots.get("seconds", 0),
                label=slots.get("label", "Timer")
            )
            return clean_for_speech(str(res))

        if intent == "control_stopwatch":
            action = slots.get("action")
            if not action:
                if "pausar" in lowered:
                    action = "pause"
                elif "zerar" in lowered or "parar" in lowered:
                    action = "reset"
                else:
                    action = "start"
            return clean_for_speech(str(TimerManager.stopwatch_control(action)))

        if intent == "pomodoro_control":
            action = slots.pop("action", "start")
            res = TimerManager.pomodoro_control(action, **slots)
            return clean_for_speech(str(res))


        if intent == "hyprland_control":
            action = slots.get("action", "launcher")
            target = slots.get("target", "1")
            if action == "workspace":
                res = HyprlandTools.change_workspace(target)
            elif action == "close_window":
                res = HyprlandTools.close_active_window()
            elif action == "fullscreen":
                res = HyprlandTools.toggle_fullscreen()
            elif action == "floating":
                res = HyprlandTools.toggle_floating()
            elif action == "brightness":
                res = HyprlandTools.set_brightness(target)
            else:
                res = HyprlandTools.open_launcher()
            return clean_for_speech(str(res))

        if intent == "restart_waybar":
            return clean_for_speech(WaybarTools.restart_waybar())

        if intent == "play_music":
            return clean_for_speech(str(YTMusicPlayer.play_song(
                query=slots.get("query", "música"),
                item_type=slots.get("item_type", "auto")
            )))

        if intent == "media_control":
            return clean_for_speech(str(SystemTools.play_pause_media()))

        if intent == "volume_control":
            return clean_for_speech(str(SystemTools.set_volume(slots.get("change", "+"))))

        if intent == "get_weather":
            alvo = slots.get("query_type", "amanhã" if "amanhã" in lowered else "hoje")
            cidade = slots.get("query", "Anápolis")
            clima_raw = SystemTools.get_weather(alvo, cidade)
            return clean_for_speech(str(clima_raw))

        if intent == "get_calendar":
            alvo = slots.get("date_query", "hoje")
            agenda_raw = CalendarTools.get_events(alvo)
            return clean_for_speech(str(agenda_raw))

        if intent == "create_calendar":
            res = CalendarTools.create_event(
                summary=slots.get("summary", "Compromisso"),
                date_query=slots.get("date_query", "hoje"),
                time_str=slots.get("time_str", "09:00"),
                duration_minutes=slots.get("duration_minutes", 60),
                all_day=slots.get("all_day", False)
            )
            return clean_for_speech(str(res))

        # 2. Intenções de Busca Externa (Filler Simultâneo + Join antes da Resposta)
        if intent == "get_news":
            TimerManager.set_assistant_state("searching")
            termo = slots.get("query", "geral")
            filler = clean_for_speech(f"Verificando as notícias sobre {termo}.")
            print(f"[Geraldo:Filler]: {filler}")
            filler_thread = self._start_filler_thread(filler)

            news_data = NewsTools.get_news(termo)
            sys_inst = "Você é o Geraldo. Resuma as principais notícias abaixo em no máximo 2 frases curtas e diretas para voz."
            final_reply = self._summarize_with_llm(sys_inst, f"Notícias: {news_data}")

            filler_thread.join(timeout=8.0)
            return final_reply

        if intent == "search_web":
            TimerManager.set_assistant_state("searching")
            termo = slots.get("query", user_prompt)
            opcoes_curtas = [
                "Consultando a internet, só um instante.",
                f"Pesquisando na web sobre {termo}.",
                "Deixa eu dar uma olhada na internet."
            ]
            filler = clean_for_speech(random.choice(opcoes_curtas))
            print(f"[Geraldo:Filler]: {filler}")
            filler_thread = self._start_filler_thread(filler)

            ano = datetime.datetime.now().year
            query_enriquecida = f"{termo} {ano}" if str(ano) not in termo else termo
            web_data = WebSearchTools.search_web(query=query_enriquecida)

            sys_inst = (
                f"Você é o Geraldo. Estamos em {ano}. Com base nos dados abaixo, responda à pergunta do usuário "
                "em 1 frase direta e objetiva para áudio. Nunca diga que os dados não foram fornecidos; extraia a melhor resposta possível."
            )
            final_reply = self._summarize_with_llm(sys_inst, f"Pergunta: {user_prompt}\nResultados da Web: {web_data}")

            filler_thread.join(timeout=8.0)
            return final_reply

        # 3. Fallback: Conversação Geral Aberta via Ollama
        sys_chat = (
            f"{SYSTEM_PROMPT}\nVocê é o Geraldo, assistente de voz local. "
            "Responda de forma direta, natural e concisa em no máximo 2 frases curtas. "
            "Nunca use listas markdown, asteriscos ou códigos."
        )
        messages = [{"role": "system", "content": sys_chat}]
        messages.extend(list(self.history))
        messages.append({"role": "user", "content": user_prompt})

        try:
            data = self._post_json({
                "model": LLM_MODEL,
                "messages": messages,
                "stream": False,
                "keep_alive": -1,
                "options": LLM_OPTIONS
            })
            reply = clean_for_speech(data.get("message", {}).get("content", "").strip())
            if reply:
                self.history.append({"role": "user", "content": user_prompt})
                self.history.append({"role": "assistant", "content": reply})
                return reply
            return "Não consegui formular uma resposta."
        except Exception as e:
            print(f"[Geraldo:LLM Error]: {e}")
            return "Desculpe, não entendi ou o serviço de conversação está indisponível."


LLMHandler = BrainLLM
