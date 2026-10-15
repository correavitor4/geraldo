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
from tools.calendar import CalendarTools

TimerManager.start_background_loop()

def get_dynamic_system_prompt() -> str:
    agora = datetime.datetime.now()
    dias_semana = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
    dia_nome = dias_semana[agora.weekday()]
    data_contexto = f"{dia_nome}, {agora.day} de {agora.strftime('%B')} de {agora.year}, {agora.strftime('%H:%M')}."

    return SYSTEM_PROMPT + f"""
VOCÊ É O GERALDO, ASSISTENTE DE VOZ PESSOAL PARA LINUX.

CONTEXTO TEMPORAL:
- HOJE É {data_contexto}
- O ANO É {agora.year}.

DIRETRIZES DE COMUNICAÇÃO:
- Os compromissos da agenda são do USUÁRIO (diga "você tem..." ou "você não tem compromissos"). NUNCA fale que os compromissos são seus.
- NUNCA use markdown nem jargões de radialista.
"""

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_calendar_events",
            "description": "Consulta compromissos no Google Calendar para uma data específica.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_query": {
                        "type": "string",
                        "description": "Data a consultar: 'hoje', 'amanhã', 'segunda', 'dia 20', etc."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Consulta a previsão do tempo e clima.",
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
            "name": "get_news",
            "description": "Busca notícias e reportagens jornalísticas detalhadas.",
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
            "name": "set_timer",
            "description": "Define timer regressivo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "minutes": {"type": "integer"},
                    "seconds": {"type": "integer"},
                    "hours": {"type": "integer"},
                    "label": {"type": "string"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_alarm",
            "description": "Define alarme em horário específico.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hour": {"type": "integer"},
                    "minute": {"type": "integer"},
                    "label": {"type": "string"}
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
                    "query": {"type": "string"},
                    "item_type": {"type": "string", "enum": ["musica", "album", "auto"]}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Consulta data e hora atual.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_volume",
            "description": "Altera volume (+, -, mute).",
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
            "description": "Alterna play/pause.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }
]

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

    def repl_time_colon(m):
        h = int(m.group(2))
        minute = int(m.group(3))
        nome_h = horas_map.get(h, str(h))
        artigo = "à " if h in [1, 13] else ("ao " if h in [0, 12] else "às ")
        
        if minute == 0:
            return f"{artigo}{nome_h}"
        elif minute == 30:
            h_base = h if h <= 12 else (h - 12)
            sufixo = " da tarde" if 12 < h < 18 else (" da noite" if h >= 18 else " da manhã")
            art = "à " if h_base in [1, 13] else "às "
            return f"{art}{horas_map.get(h_base, str(h_base))} e meia{sufixo}"
        else:
            h_base = h if h <= 12 else (h - 12)
            sufixo = " da tarde" if 12 < h < 18 else (" da noite" if h >= 18 else " da manhã")
            art = "à " if h_base in [1, 13] else "às "
            return f"{art}{horas_map.get(h_base, str(h_base))} e {minute}{sufixo}"

    text = re.sub(r'\b(às|as|à|a)?\s*(\d{1,2}):(\d{2})\b', repl_time_colon, text, flags=re.IGNORECASE)

    def repl_time_h(m):
        h = int(m.group(2))
        minute = int(m.group(3)) if m.group(3) else 0
        nome_h = horas_map.get(h, str(h))
        artigo = "à " if h in [1, 13] else ("ao " if h in [0, 12] else "às ")

        if minute == 0:
            return f"{artigo}{nome_h}"
        elif minute == 30:
            h_base = h if h <= 12 else (h - 12)
            sufixo = " da tarde" if 12 < h < 18 else (" da noite" if h >= 18 else " da manhã")
            art = "à " if h_base in [1, 13] else "às "
            return f"{art}{horas_map.get(h_base, str(h_base))} e meia{sufixo}"
        else:
            h_base = h if h <= 12 else (h - 12)
            sufixo = " da tarde" if 12 < h < 18 else (" da noite" if h >= 18 else " da manhã")
            art = "à " if h_base in [1, 13] else "às "
            return f"{art}{horas_map.get(h_base, str(h_base))} e {minute}{sufixo}"

    text = re.sub(r'\b(às|as|à|a)?\s*(\d{1,2})h(\d{2})?\b', repl_time_h, text, flags=re.IGNORECASE)
    return text

def clean_for_speech(text: str) -> str:
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"#+\s*", "", text)
    text = re.sub(r"^[-\*]\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r'["\']', '', text)
    text = phonetize_time_patterns(text)
    return text.strip()

class BrainLLM:
    def __init__(self, max_history_turns: int = 4):
        self.api_url = f"{OLLAMA_HOST}/api/chat"
        self.history = collections.deque(maxlen=max_history_turns)
        self.tools_map = {
            "get_calendar_events": CalendarTools.get_events,
            "get_weather": SystemTools.get_weather,
            "get_news": NewsTools.get_news,
            "search_web": WebSearchTools.search_web,
            "set_timer": TimerManager.add_timer,
            "set_alarm": TimerManager.add_alarm,
            "control_stopwatch": TimerManager.stopwatch_control,
            "cancel_timers": TimerManager.cancel_all,
            "play_ytmusic": YTMusicPlayer.play_song,
            "stop_ytmusic": YTMusicPlayer.stop,
            "play_pause_media": SystemTools.play_pause_media,
            "set_volume": SystemTools.set_volume,
            "get_current_time": SystemTools.get_current_time,
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
        with urllib.request.urlopen(req, timeout=35) as resp:
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

    def _handle_morning_routine(self) -> str:
        # Limpa o histórico de comandos passados para evitar contaminação
        self.history.clear()

        weather_info = SystemTools.get_weather("hoje")
        agenda_info = CalendarTools.get_events("hoje")

        sys_prompt = (
            "Você é o Geraldo, assistente de voz pessoal. O usuário acabou de te saudar com bom dia. "
            "Responda estritamente nesta ordem:\n"
            "1. Um 'Bom dia!' cordial;\n"
            "2. Resumo da previsão do tempo de hoje;\n"
            "3. O estado da agenda dele para HOJE (use 'você tem...' ou 'você não tem compromissos hoje').\n"
            "NUNCA fale de amanhã e NUNCA diga que os compromissos são seus. Seja direto e sem markdown."
        )
        user_content = f"Previsão de Hoje: {weather_info}\nAgenda de Hoje: {agenda_info}"

        try:
            res = self._post_json({
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_content}
                ],
                "stream": False,
                "options": {"temperature": 0.1}
            })
            return clean_for_speech(res.get("message", {}).get("content", ""))
        except Exception:
            return clean_for_speech(f"Bom dia! {weather_info}. {agenda_info}")

    def ask(self, user_prompt: str) -> str:
        normalized = user_prompt

        # Normalizações fonéticas de expressões temporais
        normalized = re.sub(r'\b(para\s+o\s+manhã|para\s+a\s+manhã|pra\s+a\s+manhã|pra\s+o\s+manhã)\b', 'para amanhã', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\b(para\s+o\s+manha|para\s+a\s+manha|pra\s+a\s+manha|pra\s+o\s+manha)\b', 'para amanhã', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\b(pra\s+manhã|para\s+manhã|pra\s+manha|para\s+manha)\b', 'para amanhã', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\ba\s+larme\b', 'alarme', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\b(defino|defina|coloque|bote)\s+a\s+larme\b', 'defina alarme', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\b(táme|taimer|táime)\b', 'timer', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\b(tokyo|talk to)\b', 'toque', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\b(numa|em uma|numa|em)\s+12\b', 'em uma dúzia', normalized, flags=re.IGNORECASE)

        clean_prompt = re.sub(r'[^\w\s]', '', normalized).lower().strip()

        # 1. ROTINA DE BOM DIA (Captura ampla: "bom dia", "boa dia", "bom dia bom dia", etc.)
        if re.search(r'\b(bom\s+dia|boa\s+dia)\b', clean_prompt):
            print("[Geraldo] Executando rotina matinal: Clima + Google Calendar (Hoje)...")
            reply = self._handle_morning_routine()
            self.history.append({"role": "user", "content": normalized})
            self.history.append({"role": "assistant", "content": reply})
            return reply

        # 2. Interceptador de Agenda Determinístico (sem contaminar com o dia de ontem/amanhã)
        if any(w in clean_prompt for w in ["agenda", "compromisso", "compromissos"]):
            alvo = "hoje"
            if "amanhã" in clean_prompt or "amanha" in clean_prompt:
                alvo = "amanhã"
            elif "depois de amanhã" in clean_prompt or "depois de amanha" in clean_prompt:
                alvo = "depois de amanhã"
            else:
                for dia in ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]:
                    if dia in clean_prompt:
                        alvo = dia
                        break

            print(f"[Geraldo:Calendar] Consulta direta da agenda para: '{alvo}'")
            res_agenda = CalendarTools.get_events(alvo)

            sys_instruction = (
                f"Você é o Geraldo. Transmita os compromissos da agenda do usuário para {alvo} de forma falada e natural em no máximo 2 frases. "
                "Lembre-se: os compromissos são do USUÁRIO (diga 'você tem...'). NUNCA use markdown."
            )
            follow_up = self._post_json({
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": sys_instruction},
                    {"role": "user", "content": f"Pergunta: {normalized}\nDados da agenda para {alvo}: {res_agenda}"}
                ],
                "stream": False,
                "options": {"temperature": 0.1}
            })
            reply_text = clean_for_speech(follow_up.get("message", {}).get("content", "") or res_agenda)
            
            # Limpa o histórico de agenda para não herdar a data em comandos futuros
            self.history.clear()
            self.history.append({"role": "user", "content": normalized})
            self.history.append({"role": "assistant", "content": reply_text})
            return reply_text

        # 3. Agradecimentos
        agradecimentos = ["obrigado", "muito obrigado", "valeu", "valeu geraldo", "agradecido", "obrigada"]
        if any(clean_prompt.startswith(a) for a in agradecimentos):
            self.history.clear()
            return "De nada! Sempre que precisar é só chamar."

        if any(w in clean_prompt for w in ["notícia", "noticia", "notícias", "noticias", "manchetes", "resumo das"]):
            if "goiás" in clean_prompt or "goias" in clean_prompt:
                user_prompt_tool = "get_news sobre Goiás"
            else:
                user_prompt_tool = normalized
        else:
            user_prompt_tool = normalized

        system_content = get_dynamic_system_prompt()
        messages = [{"role": "system", "content": system_content}]
        messages.extend(list(self.history))
        messages.append({"role": "user", "content": user_prompt_tool})

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

                if fn_name in self.tools_map:
                    print(f"[Geraldo:Tool] Executando {fn_name}({fn_args})...")
                    tool_result = self._execute_tool_safely(fn_name, fn_args)

                    if fn_name in ["set_timer", "set_alarm", "control_stopwatch", "cancel_timers", "play_ytmusic", "stop_ytmusic", "play_pause_media", "set_volume", "get_current_time"]:
                        reply_text = clean_for_speech(str(tool_result))
                        self.history.append({"role": "user", "content": normalized})
                        self.history.append({"role": "assistant", "content": reply_text})
                        return reply_text

                    ano_atual = datetime.datetime.now().year

                    if fn_name == "get_news":
                        sys_instruction = (
                            f"Você é o Geraldo. Apresente um resumo detalhado e abrangente das notícias a seguir "
                            f"para áudio, explicando os fatos com clareza em vários parágrafos fluídos. "
                            f"NUNCA use markdown e nunca mencione corte de conhecimento."
                        )
                    else:
                        sys_instruction = (
                            f"Você é o Geraldo. O ano atual é {ano_atual}. Resuma as informações abaixo em no máximo 2 a 3 frases "
                            "diretas e estritamente factuais. NUNCA use markdown nem fale sobre corte de conhecimento."
                        )

                    follow_up = self._post_json({
                        "model": LLM_MODEL,
                        "messages": [
                            {"role": "system", "content": sys_instruction},
                            {"role": "user", "content": f"Pergunta: {normalized}\nDados levantados: {tool_result}"}
                        ],
                        "stream": False,
                        "options": {"temperature": 0.2}
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
