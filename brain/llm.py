import collections
import json
import urllib.request
import urllib.error
import re
import datetime
import random
import threading
import time
import config
from config import SYSTEM_PROMPT
from brain.nlu import IntentEngine
from tools.system import SystemTools
from tools.ytmusic import YTMusicPlayer
from tools.news import NewsTools
from tools.search import WebSearchTools
from tools.timer import TimerManager
from tools.calendar import CalendarTools
from tools.hyprland import HyprlandTools
from tools.waybar import WaybarTools
from tools.meeting import MeetingTools

# num_ctx fixo para todas as chamadas: o Ollama recarrega o modelo se o contexto mudar entre requisições.
# 2048 comporta o prompt do roteador (lista de comandos) + histórico curto.
LLM_OPTIONS = {
    "temperature": 0.2,
    "num_ctx": 2048,
    "num_predict": 90
}

# Tokens extras para o roteador: JSON + resposta curta de conversa
ROUTER_MAX_TOKENS = 160
WARMUP_COOLDOWN_S = 60.0

# Comandos que a LLM pode escolher quando o NLU não tem confiança.
# Para cada um: (descrição curta, campos de TEXTO aceitos da LLM -> valores permitidos ou None = livre).
# Números e horários (hour, minute, minutes, time_str, ...) NÃO vêm da LLM: são sempre extraídos via Regex.
LLM_ROUTES = {
    "get_time": ("perguntar as horas", {}),
    "greeting_morning": ("cumprimento de bom dia", {}),
    "thanks": ("agradecimento", {}),
    "get_weather": ("previsão do tempo ou clima", {"query": None, "query_type": {"hoje", "amanhã", "semana"}}),
    "get_calendar": ("consultar agenda ou compromissos", {"date_query": {"hoje", "amanhã", "depois de amanhã", "semana", "próximo"}}),
    "create_calendar": ("criar compromisso na agenda", {"summary": None, "date_query": None}),
    "delete_calendar": ("cancelar compromisso da agenda", {"summary": None, "date_query": None}),
    "set_alarm": ("criar alarme ou despertador para um horário", {"label": None}),
    "set_timer": ("timer regressivo ou aviso daqui a um tempo", {"label": None}),
    "list_timers": ("listar timers ou alarmes ativos", {}),
    "cancel_timers": ("cancelar ou silenciar timers ou alarmes", {"query": None}),
    "pause_timer": ("pausar um timer", {"query": None}),
    "resume_timer": ("retomar um timer pausado", {"query": None}),
    "control_stopwatch": ("cronômetro progressivo", {"action": {"start", "pause", "reset"}}),
    "pomodoro_control": ("pomodoro ou modo foco", {"action": {"start", "pause", "resume", "advance", "stop", "status", "long_break"}}),
    "play_music": ("tocar música, artista ou álbum", {"query": None, "item_type": {"auto", "album"}}),
    "media_control": ("pausar ou continuar a mídia atual", {}),
    "volume_control": ("ajustar o volume (+, -, mute ou 0-100)", {"change": None}),
    "get_news": ("notícias", {"query": None}),
    "search_web": ("pesquisar informação atual na internet", {"query": None}),
    "hyprland_control": ("janelas, workspaces ou brilho da tela", {
        "action": {"workspace", "close_window", "fullscreen", "floating", "brightness", "launcher"},
        "target": None,
    }),
    "restart_waybar": ("reiniciar a waybar", {}),
    "meeting_control": ("iniciar, pausar, retomar, encerrar gravação de reunião ou ver status da ata", {
        "action": {"start", "pause", "resume", "stop", "status"},
        "title": None,
    }),
}

# Validação extra de formato para campos livres sensíveis
SLOT_PATTERNS = {
    "change": r"(?:\+|-|mute|\d{1,3})",
    "target": r"[\w%.\-]{1,10}",
}


def build_router_prompt() -> str:
    lines = []
    for name, (desc, fields) in LLM_ROUTES.items():
        field_desc = ", ".join(
            f"{k} ({'|'.join(sorted(v))})" if isinstance(v, set) else k
            for k, v in fields.items()
        )
        lines.append(f"- {name}: {desc}" + (f". Campos: {field_desc}" if field_desc else ""))
    return (
        f"{SYSTEM_PROMPT}\n"
        "Você também é o roteador de comandos do assistente. Analise a última mensagem do usuário e "
        "responda SOMENTE com um objeto JSON, sem nenhum texto fora dele.\n"
        'Se ela pedir uma das ações abaixo, responda {"intent": "<nome>", "slots": {...}} usando apenas os campos listados.\n'
        'Caso contrário, responda {"intent": "conversa", "reply": "<resposta em português, no máximo 2 frases curtas>"}.\n'
        "Ações:\n" + "\n".join(lines)
    )


def parse_llm_route(raw: str) -> dict | None:
    """Extrai o primeiro objeto JSON da resposta da LLM. Retorna None se não houver JSON válido."""
    if not raw:
        return None
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except (json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None

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
    def __init__(
        self,
        speaker=None,
        speak_fn=None,
        max_history_turns: int = 4,
        host: str = None,
        model: str = None,
        provider: str = None,
        api_key: str = None,
        api_base: str = None,
    ):
        print("[Geraldo] Treinando classificador NLU (Scikit-Learn)...")
        self.nlu = IntentEngine(confidence_threshold=0.38)
        self.speaker = speaker
        self.speak_fn = speak_fn
        self._provider = provider
        self._host = host
        self._model = model
        self._api_key = api_key
        self._api_base = api_base
        self._api_url_override = None
        self.history = collections.deque(maxlen=max_history_turns)
        self._fallback_tts = None
        self._fallback_player = None
        self._router_prompt = build_router_prompt()
        self._warmup_lock = threading.Lock()
        self._last_warmup = float("-inf")

    @property
    def provider(self) -> str:
        return (self._provider or getattr(config, "LLM_PROVIDER", "ollama")).lower()

    @provider.setter
    def provider(self, val: str) -> None:
        self._provider = (val or "ollama").lower()

    @property
    def api_key(self) -> str:
        return self._api_key or getattr(config, "LLM_API_KEY", "")

    @api_key.setter
    def api_key(self, val: str) -> None:
        self._api_key = val

    @property
    def api_base(self) -> str:
        if self._api_base:
            return self._api_base
        active_provider = getattr(config, "LLM_PROVIDER", "ollama")
        if self.provider == active_provider:
            cfg_base = getattr(config, "LLM_API_BASE", "")
            if cfg_base:
                return cfg_base
        presets = getattr(config, "PROVIDER_PRESETS", {})
        return presets.get(self.provider, {}).get("default_base", "https://api.openai.com/v1")

    @api_base.setter
    def api_base(self, val: str) -> None:
        self._api_base = val

    @property
    def host(self) -> str:
        return self._host or getattr(config, "OLLAMA_HOST", "http://localhost:11434")

    @host.setter
    def host(self, val: str) -> None:
        self._host = val

    @property
    def model(self) -> str:
        return self._model or getattr(config, "LLM_MODEL", "qwen2.5:3b")

    @model.setter
    def model(self, val: str) -> None:
        self._model = val

    @property
    def api_url(self) -> str:
        if self._api_url_override:
            return self._api_url_override
        h = (self.host or "http://localhost:11434").strip().rstrip("/")
        if not (h.startswith("http://") or h.startswith("https://")):
            h = f"http://{h}"
        return f"{h}/api/chat"

    @api_url.setter
    def api_url(self, val: str) -> None:
        self._api_url_override = val

    def set_llm_config(
        self,
        provider: str = None,
        host: str = None,
        model: str = None,
        api_key: str = None,
        api_base: str = None,
    ) -> None:
        if provider:
            self.provider = provider
        if host:
            self.host = host
        if model:
            self.model = model
        if api_key is not None:
            self.api_key = api_key
        if api_base is not None:
            self.api_base = api_base

    def set_ollama_config(self, host: str = None, model: str = None) -> None:
        self.set_llm_config(provider="ollama" if host else None, host=host, model=model)

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
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError) as e:
            # Fallback inteligente se o host configurado for nome de container Docker (ex: ollama:11434) que não resolve no host
            if "localhost" not in self.api_url and "127.0.0.1" not in self.api_url:
                fallback_url = "http://localhost:11434/api/chat"
                try:
                    fallback_req = urllib.request.Request(
                        fallback_url,
                        data=json.dumps(payload).encode("utf-8"),
                        headers={"Content-Type": "application/json"}
                    )
                    with urllib.request.urlopen(fallback_req, timeout=30) as resp:
                        return json.loads(resp.read().decode("utf-8"))
                except Exception:
                    pass
            raise e

    def _post_json_openai(self, payload: dict) -> dict:
        base = (self.api_base or "https://api.openai.com/v1").rstrip("/")
        url = f"{base}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Geraldo-Assistant/1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key.strip()}"

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def warmup_async(self) -> None:
        """Pré-carrega o modelo no Ollama em segundo plano, sem bloquear (limitado a 1x por minuto)."""
        if (self.provider or "ollama").lower() != "ollama":
            return
        now = time.monotonic()
        with self._warmup_lock:
            if now - self._last_warmup < WARMUP_COOLDOWN_S:
                return
            self._last_warmup = now
        threading.Thread(target=self._warmup_sync, daemon=True).start()

    def _warmup_sync(self) -> None:
        try:
            # messages vazio: o Ollama apenas carrega o modelo na memória (mesmo num_ctx das chamadas reais)
            self._post_json({
                "model": self.model,
                "messages": [],
                "stream": False,
                "keep_alive": -1,
                "options": LLM_OPTIONS,
            })
        except Exception as e:
            print(f"[Geraldo:LLM Warmup] Falhou: {e}")

    def _call_llm(self, messages: list, json_mode: bool = False, max_tokens: int | None = None) -> str:
        """Invoca o provedor LLM ativo (Ollama local ou provedor externo com API Key)."""
        prov = (self.provider or "ollama").lower()
        t_llm0 = time.perf_counter()
        if prov == "ollama":
            options = dict(LLM_OPTIONS)
            if max_tokens:
                options["num_predict"] = max_tokens
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "keep_alive": -1,
                "options": options
            }
            if json_mode:
                payload["format"] = "json"
            res = self._post_json(payload)
            ms_llm = (time.perf_counter() - t_llm0) * 1000
            print(f"[Geraldo:LLM] Resposta {prov} ({self.model}) em {ms_llm:.1f}ms")
            if "message" in res and isinstance(res["message"], dict):
                return res["message"].get("content", "").strip()
            elif "choices" in res and len(res["choices"]) > 0:
                return res["choices"][0].get("message", {}).get("content", "").strip()
            return ""
        else:
            # response_format não é enviado: nem todo provedor compatível com OpenAI suporta.
            # O formato JSON é pedido no prompt e a resposta é analisada de forma tolerante.
            res = self._post_json_openai({
                "model": self.model,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": max_tokens or 150,
            })
            ms_llm = (time.perf_counter() - t_llm0) * 1000
            print(f"[Geraldo:LLM] Resposta {prov} ({self.model}) em {ms_llm:.1f}ms")
            if "choices" in res and len(res["choices"]) > 0:
                return res["choices"][0].get("message", {}).get("content", "").strip()
            elif "message" in res and isinstance(res["message"], dict):
                return res["message"].get("content", "").strip()
            return ""

    def _summarize_with_llm(self, instruction: str, content: str) -> str:
        try:
            t_sum0 = time.perf_counter()
            messages = [
                {"role": "system", "content": instruction},
                {"role": "user", "content": content}
            ]
            reply = self._call_llm(messages)
            ms_sum = (time.perf_counter() - t_sum0) * 1000
            print(f"[Geraldo:LLM] Resumo gerado em {ms_sum:.1f}ms")
            return clean_for_speech(reply) if reply else clean_for_speech(content)
        except Exception as e:
            print(f"[Geraldo:LLM Error]: {e}")
            return clean_for_speech(content)

    def ask(self, user_prompt: str) -> str:
        t_ask_start = time.perf_counter()
        lowered = user_prompt.lower()
        if any(cmd in lowered for cmd in ["esquece o que conversamos", "esquecer conversa", "limpar memória", "limpar memoria", "novo assunto"]):
            self.reset_memory()
            return "Memória recente apagada."

        # 1. NLU sem LLM: regras Regex + TF-IDF/Regressão Logística (em paralelo)
        intent, confidence, slots = self.nlu.predict(user_prompt)

        if intent in LLM_ROUTES:
            t_act0 = time.perf_counter()
            reply = self._dispatch_intent(intent, slots, user_prompt)
            ms_act = (time.perf_counter() - t_act0) * 1000
            if reply is not None:
                ms_total = (time.perf_counter() - t_ask_start) * 1000
                print(f"[Geraldo:Action] '{intent}' executado em {ms_act:.1f}ms | ⏱️ Total Cérebro: {ms_total:.1f}ms")
                return reply

        # 2. NLU sem confiança: a LLM classifica o comando ou responde como conversa
        t_fallback0 = time.perf_counter()
        reply = self._llm_fallback(user_prompt)
        ms_fallback = (time.perf_counter() - t_fallback0) * 1000
        ms_total = (time.perf_counter() - t_ask_start) * 1000
        print(f"[Geraldo:LLM-Fallback] Concluído em {ms_fallback:.1f}ms | ⏱️ Total Cérebro: {ms_total:.1f}ms")
        return reply

    def _merge_llm_slots(self, intent: str, user_prompt: str, llm_slots) -> dict:
        """Slots numéricos/horários vêm do Regex; campos de texto validados da LLM sobrescrevem."""
        slots = self.nlu.extract_slots_from_text(intent, user_prompt)
        if not isinstance(llm_slots, dict):
            return slots
        for key, allowed in LLM_ROUTES[intent][1].items():
            val = llm_slots.get(key)
            if val is None or isinstance(val, bool):
                continue
            if isinstance(val, (int, float)):
                val = str(int(val))
            if not isinstance(val, str):
                continue
            val = val.strip()
            if not val or len(val) > 120:
                continue
            if isinstance(allowed, set):
                val = val.lower()
                if val not in allowed:
                    continue
            pattern = SLOT_PATTERNS.get(key)
            if pattern and not re.fullmatch(pattern, val.lower()):
                continue
            slots[key] = val
        return slots

    def _llm_fallback(self, user_prompt: str) -> str:
        messages = [{"role": "system", "content": self._router_prompt}]
        messages.extend(list(self.history))
        messages.append({"role": "user", "content": user_prompt})

        try:
            raw = self._call_llm(messages, json_mode=True, max_tokens=ROUTER_MAX_TOKENS)
        except Exception as e:
            print(f"[Geraldo:LLM Error]: {e}")
            return "Desculpe, não entendi ou o serviço de conversação está indisponível."

        route = parse_llm_route(raw)
        intent = str(route.get("intent", "")).strip() if route else ""

        if intent in LLM_ROUTES:
            slots = self._merge_llm_slots(intent, user_prompt, route.get("slots"))
            print(f"[Geraldo:LLM-Router] Intenção: '{intent}' | Slots: {slots}")
            reply = self._dispatch_intent(intent, slots, user_prompt)
            if reply is not None:
                return reply

        # Conversa livre: usa o campo de resposta do JSON ou, se a LLM ignorou o formato, o texto bruto
        if route is not None:
            reply_text = next(
                (route[k] for k in ("reply", "resposta", "response", "text") if isinstance(route.get(k), str)),
                ""
            )
        else:
            reply_text = raw

        reply = clean_for_speech((reply_text or "").strip())
        if reply:
            self.history.append({"role": "user", "content": user_prompt})
            self.history.append({"role": "assistant", "content": reply})
            return reply
        return "Não consegui formular uma resposta."

    def _dispatch_intent(self, intent: str, slots: dict, user_prompt: str) -> str | None:
        """Executa a função Python associada à intenção. Retorna None se a intenção não tiver handler."""
        lowered = user_prompt.lower()

        # Respostas 100% Determinísticas (Zero LLM, Zero Latência)
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

        if intent == "meeting_control":
            action = slots.get("action", "start")
            title = slots.get("title")
            if action == "pause":
                return clean_for_speech(MeetingTools.pause_meeting())
            elif action == "resume":
                return clean_for_speech(MeetingTools.resume_meeting())
            elif action == "stop":
                return clean_for_speech(MeetingTools.stop_meeting(speak_fn=self._do_speak_sync))
            elif action == "status":
                return clean_for_speech(MeetingTools.get_meeting_status())
            else:
                return clean_for_speech(MeetingTools.start_meeting(title=title))


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

        if intent == "delete_calendar":
            res = CalendarTools.delete_event(
                summary=slots.get("summary", ""),
                date_query=slots.get("date_query", "hoje")
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

        return None


LLMHandler = BrainLLM
