import collections
import json
import urllib.request
import urllib.error
import inspect
import re
import datetime
from config import OLLAMA_HOST, LLM_MODEL, SYSTEM_PROMPT
from tools.system import SystemTools
from tools.ytmusic import YTMusicPlayer
from tools.news import NewsTools
from tools.search import WebSearchTools
from tools.timer import TimerManager

# Inicia o loop de timers em segundo plano
TimerManager.start_background_loop()

def get_dynamic_system_prompt() -> str:
    agora = datetime.datetime.now()
    dias_semana = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
    dia_nome = dias_semana[agora.weekday()]
    data_contexto = f"{dia_nome}, {agora.day} de {agora.strftime('%B')} de {agora.year}, {agora.strftime('%H:%M')}."

    return SYSTEM_PROMPT + f"""
VOCÊ É O GERALDO, ASSISTENTE DE VOZ PARA LINUX.

CONTEXTO TEMPORAL:
- HOJE É {data_contexto}
- O ANO É {agora.year}. NUNCA mencione que seu conhecimento parou em 2023 ou 2024. Você tem acesso à internet em tempo real via ferramentas.

FERRAMENTAS:
- "set_timer": Para contagens regressivas de tempo.
- "set_alarm": Para alarmes em horários determinados do relógio.
- "control_stopwatch": Para cronômetro progressivo ("start", "pause", "reset").
- "cancel_timers": Para cancelar timers/alarmes.
- "search_web": Para dúvidas, pesquisas eleitorais e dados recentes.
- "play_ytmusic": APENAS com ordem explícita de tocar música ou álbum.

DIRETRIZES:
- NUNCA use markdown nem introduções de radialista. Responda em no máximo 2 a 3 frases.
"""

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "set_timer",
            "description": "Define um timer de contagem regressiva em minutos, segundos ou horas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "minutes": {"type": "integer", "description": "Minutos de duração."},
                    "seconds": {"type": "integer", "description": "Segundos de duração."},
                    "hours": {"type": "integer", "description": "Horas de duração."},
                    "label": {"type": "string", "description": "Rótulo opcional."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_alarm",
            "description": "Define um alarme para um horário específico.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hour": {"type": "integer", "description": "Hora (0-23)."},
                    "minute": {"type": "integer", "description": "Minuto (0-59)."},
                    "label": {"type": "string", "description": "Rótulo opcional."}
                },
                "required": ["hour", "minute"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "control_stopwatch",
            "description": "Controla o cronômetro progressivo (start, pause, reset).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["start", "pause", "reset"]}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_timers",
            "description": "Cancela todos os timers e alarmes.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "play_ytmusic",
            "description": "Reproduz música ou álbum no YouTube Music.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Nome da música, álbum ou artista."},
                    "item_type": {"type": "string", "enum": ["musica", "album", "auto"]}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Busca dados factuais na web via DuckDuckGo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Termo de busca objetivo."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_news",
            "description": "Busca notícias e manchetes jornalísticas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Tema específico ou 'geral'."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Consulta a previsão do tempo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query_type": {"type": "string", "enum": ["hoje", "amanhã", "semana"]}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Consulta data e hora atual do relógio.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_volume",
            "description": "Altera o volume (+, -, mute).",
            "parameters": {
                "type": "object",
                "properties": {
                    "change": {"type": "string", "enum": ["+", "-", "mute"]}
                },
                "required": ["change"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "play_pause_media",
            "description": "Alterna entre reproduzir e pausar a mídia.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }
]

def clean_for_speech(text: str) -> str:
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"#+\s*", "", text)
    text = re.sub(r"^[-\*]\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r'["\']', '', text)
    return text.strip()

class BrainLLM:
    def __init__(self, max_history_turns: int = 4):
        self.api_url = f"{OLLAMA_HOST}/api/chat"
        self.history = collections.deque(maxlen=max_history_turns)
        self.tools_map = {
            "set_timer": TimerManager.add_timer,
            "set_alarm": TimerManager.add_alarm,
            "control_stopwatch": TimerManager.stopwatch_control,
            "cancel_timers": TimerManager.cancel_all,
            "play_ytmusic": YTMusicPlayer.play_song,
            "stop_ytmusic": YTMusicPlayer.stop,
            "play_pause_media": SystemTools.play_pause_media,
            "set_volume": SystemTools.set_volume,
            "get_current_time": SystemTools.get_current_time,
            "get_weather": SystemTools.get_weather,
            "get_news": NewsTools.get_news,
            "search_web": WebSearchTools.search_web,
        }

    def reset_memory(self):
        self.history.clear()
        print("[Geraldo:Memoria] Histórico limpo.")

    def _post_json(self, payload: dict) -> dict:
        req = urllib.request.Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _execute_tool_safely(self, fn_name: str, fn_args: dict):
        func = self.tools_map[fn_name]
        sig = inspect.signature(func)
        filtered_args = {}
        for param in sig.parameters.values():
            if param.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY):
                if param.name in fn_args:
                    filtered_args[param.name] = fn_args[param.name]
            elif param.kind == inspect.Parameter.VAR_KEYWORD:
                filtered_args = fn_args
                break
        return func(**filtered_args)

    def _try_deterministic_timer_or_alarm(self, text: str) -> str:
        t_low = text.lower()

        # 1. Cancelamentos
        if any(w in t_low for w in ["cancelar", "cancela", "pare", "parar", "desative", "desativa"]):
            if any(w in t_low for w in ["timer", "temporizador", "alarme", "cronômetro", "cronometro"]):
                return TimerManager.cancel_all()

        # 2. Interceptador de Alarme
        if "alarme" in t_low:
            # Padrão: 10 e meia -> 10:30
            m_meia = re.search(r'(\d{1,2})\s*e\s*meia\b', t_low)
            if m_meia:
                h = int(m_meia.group(1))
                return TimerManager.add_alarm(hour=h, minute=30)

            # Padrão: 10 e 30 / 10:30
            m_hm = re.search(r'(\d{1,2})\s*(?:e|:|h|horas?)\s*(\d{1,2})\b', t_low)
            if m_hm:
                h = int(m_hm.group(1))
                m = int(m_hm.group(2))
                return TimerManager.add_alarm(hour=h, minute=m)

            # Padrão: alarme para as 7 / 7 horas
            m_h = re.search(r'(?:para|às|as)\s*(\d{1,2})\b', t_low)
            if m_h:
                h = int(m_h.group(1))
                return TimerManager.add_alarm(hour=h, minute=0)

        # 3. Interceptador de Timer
        if any(w in t_low for w in ["timer", "temporizador"]):
            m_sec = re.search(r'(\d+)\s*(?:segundos?|segs?|s)\b', t_low)
            m_min = re.search(r'(\d+)\s*(?:minutos?|mins?|m)\b', t_low)
            m_hor = re.search(r'(\d+)\s*(?:horas?|hrs?|h)\b', t_low)

            if m_sec or m_min or m_hor:
                s = int(m_sec.group(1)) if m_sec else 0
                m = int(m_min.group(1)) if m_min else 0
                h = int(m_hor.group(1)) if m_hor else 0

                m_label = re.search(r'para (?:o |a )?([a-zA-Z0-9çãõáéíóú]+)', t_low)
                label = m_label.group(1).capitalize() if m_label else "Timer"
                return TimerManager.add_timer(minutes=m, seconds=s, hours=h, label=label)

        return ""

    def ask(self, user_prompt: str) -> str:
        normalized = user_prompt
        # Normalizações fonéticas
        normalized = re.sub(r'\ba\s+larme\b', 'alarme', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\b(defino|defina|coloque|bote)\s+a\s+larme\b', 'defina alarme', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\b(táme|taimer|táime)\b', 'timer', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\b(ele sim|inici|inicie)\b', 'inicie', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\b(tokyo|talk to)\b', 'toque', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bdiana winehouse\b', 'Amy Winehouse', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bbpc\b', 'BBC', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\b(numa|em uma|numa|em)\s+12\b', 'em uma dúzia', normalized, flags=re.IGNORECASE)

        # Interceptador determinístico
        fast_reply = self._try_deterministic_timer_or_alarm(normalized)
        if fast_reply:
            self.history.append({"role": "user", "content": normalized})
            self.history.append({"role": "assistant", "content": fast_reply})
            return fast_reply

        lowered = normalized.lower()
        agradecimentos = ["obrigado", "muito obrigado", "valeu", "valeu geraldo", "agradecido", "obrigada"]
        if any(lowered.startswith(a) for a in agradecimentos):
            self.history.clear()
            return "De nada! Sempre que precisar é só chamar."

        system_content = get_dynamic_system_prompt()
        messages = [{"role": "system", "content": system_content}]
        messages.extend(list(self.history))
        messages.append({"role": "user", "content": normalized})

        payload = {
            "model": LLM_MODEL,
            "messages": messages,
            "tools": TOOLS_SCHEMA,
            "stream": False,
            "options": {"temperature": 0.1}
        }

        try:
            data = self._post_json(payload)
            message = data.get("message", {})

            if "tool_calls" in message and message["tool_calls"]:
                tool_call = message["tool_calls"][0]
                fn_name = tool_call.get("function", {}).get("name")
                fn_args = tool_call.get("function", {}).get("arguments", {})

                # Injeta o ano atual para buscas políticas ou fatos recentes
                if fn_name in ["search_web", "get_news"]:
                    q = fn_args.get("query", "")
                    termos_eleicao = ["eleição", "eleicoes", "eleições", "eleitoral", "presidente", "segundo turno", "disputa"]
                    if any(t in q.lower() for t in termos_eleicao) and "202" not in q:
                        ano_atual = datetime.datetime.now().year
                        fn_args["query"] = f"{q} {ano_atual}"

                if fn_name in self.tools_map:
                    print(f"[Geraldo:Tool] Executando {fn_name}({fn_args})...")
                    tool_result = self._execute_tool_safely(fn_name, fn_args)

                    if fn_name in ["set_timer", "set_alarm", "control_stopwatch", "cancel_timers", "play_ytmusic", "stop_ytmusic", "play_pause_media", "set_volume", "get_current_time", "get_weather"]:
                        reply_text = clean_for_speech(str(tool_result))
                        self.history.append({"role": "user", "content": normalized})
                        self.history.append({"role": "assistant", "content": reply_text})
                        return reply_text

                    ano_atual = datetime.datetime.now().year
                    sys_instruction = (
                        f"Você é o Geraldo. O ano atual é {ano_atual}. Resuma as informações abaixo em no máximo 2 a 3 frases "
                        "diretas e estritamente factuais. NUNCA diga quando foi seu corte de conhecimento e nunca use markdown. Vá direto aos fatos."
                    )

                    follow_up = self._post_json({
                        "model": LLM_MODEL,
                        "messages": [
                            {"role": "system", "content": sys_instruction},
                            {"role": "user", "content": f"Pergunta: {normalized}\nDados: {tool_result}"}
                        ],
                        "stream": False,
                        "options": {"temperature": 0.1}
                    })
                    final_msg = follow_up.get("message", {})
                    raw_reply = final_msg.get("content", "").strip() or str(tool_result)
                    reply_text = clean_for_speech(raw_reply)
                    self.history.append({"role": "user", "content": normalized})
                    self.history.append({"role": "assistant", "content": reply_text})
                    return reply_text

            reply_text = clean_for_speech(message.get("content", "").strip())
            if reply_text:
                self.history.append({"role": "user", "content": normalized})
                self.history.append({"role": "assistant", "content": reply_text})
                return reply_text

            return "Entendido."

        except Exception as e:
            print(f"[Geraldo:LLM Error]: {e}")
            return "Desculpe, tive uma falha ao processar a resposta."
