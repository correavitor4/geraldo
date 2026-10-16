import collections
import json
import urllib.request
import urllib.error
import inspect
import re
import datetime
import random
import threading
from config import OLLAMA_HOST, LLM_MODEL, SYSTEM_PROMPT
from tools.system import SystemTools
from tools.ytmusic import YTMusicPlayer
from tools.news import NewsTools
from tools.search import WebSearchTools
from tools.timer import TimerManager
from tools.calendar import CalendarTools

TimerManager.start_background_loop()

LLM_OPTIONS = {
    "temperature": 0.1,
    "num_ctx": 2048,
    "num_predict": 128
}

def get_dynamic_system_prompt() -> str:
    agora = datetime.datetime.now()
    dias_semana = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
    dia_nome = dias_semana[agora.weekday()]
    data_contexto = f"{dia_nome}, {agora.day} de {agora.strftime('%B')} de {agora.year}, {agora.strftime('%H:%M')}."

    return SYSTEM_PROMPT + f"""
VOCÊ É O GERALDO, ASSISTENTE DE VOZ PESSOAL PARA LINUX ESTILO ALEXA.

CONTEXTO TEMPORAL:
- HOJE É {data_contexto}
- ANO ATUAL: {agora.year}.

DIRETRIZES DE RESPOSTA ESTILO ALEXA:
- SEJA EXTREMAMENTE DIRETO, NATURAL E OBJETIVO.
- Limite suas respostas a no máximo 1 ou 2 frases curtas.
- NUNCA use introduções nem saudações repetitivas.
- Para resultados de futebol, política, eleições, notícias e eventos esportivos, você OBRIGATORIAMENTE deve usar a ferramenta search_web ou get_news. NUNCA tente adivinhar fatos recentes.
- NUNCA sugira comandos de texto nem nomes de funções internas ao usuário.
"""

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "create_calendar_event",
            "description": "Cria e agenda um novo compromisso no Google Calendar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Título do compromisso."},
                    "date_query": {"type": "string", "description": "Data: 'hoje', 'amanhã', etc."},
                    "time_str": {"type": "string", "description": "Horário 'HH:MM'."},
                    "duration_minutes": {"type": "integer", "description": "Duração em minutos."}
                },
                "required": ["summary", "date_query", "time_str"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_calendar_events",
            "description": "Consulta compromissos no Google Calendar para uma data específica.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_query": {"type": "string", "description": "Data a consultar: 'hoje', 'amanhã', etc."}
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
            "description": "Busca acontecimentos jornalísticos recentes do dia.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Tema recente."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Pesquisa na internet dados atualizados sobre esportes, campeões, política, cotações, pessoas e dúvidas gerais.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Termo de busca objetivo no DuckDuckGo."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_timer",
            "description": "Define timer regressivo em minutos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "minutes": {"type": "integer", "description": "Quantidade de minutos."},
                    "seconds": {"type": "integer", "description": "Quantidade de segundos."},
                    "label": {"type": "string", "description": "Rótulo opcional do timer."}
                },
                "required": ["minutes"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_alarm",
            "description": "Define alarme em horário específico (hora de 0 a 23 e minuto de 0 a 59).",
            "parameters": {
                "type": "object",
                "properties": {
                    "hour": {"type": "integer", "description": "Hora no formato 24h (ex: 22 para 10 da noite)."},
                    "minute": {"type": "integer", "description": "Minuto (0 a 59)."},
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
            "description": "Controla cronômetro (start, pause, reset).",
            "parameters": {
                "type": "object",
                "properties": {"action": {"type": "string", "enum": ["start", "pause", "reset"]}},
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_timers",
            "description": "Cancela timers e alarmes.",
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
                    "query": {"type": "string", "description": "Nome da música ou artista."},
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
                "properties": {"change": {"type": "string", "enum": ["+", "-", "mute"]}},
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
    def __init__(self, speaker=None, max_history_turns: int = 4):
        self.speaker = speaker
        self.api_url = f"{OLLAMA_HOST}/api/chat"
        self.history = collections.deque(maxlen=max_history_turns)
        self.tools_map = {
            "create_calendar_event": CalendarTools.create_event,
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

    def _speak_filler_async(self, text: str):
        if self.speaker and hasattr(self.speaker, "speak"):
            threading.Thread(target=self.speaker.speak, args=(text,), daemon=True).start()

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
                elif param.default is not inspect.Parameter.empty:
                    filtered_args[param.name] = param.default
            elif param.kind == inspect.Parameter.VAR_KEYWORD:
                filtered_args = fn_args
                break
        
        if fn_name == "set_alarm":
            if "hour" not in filtered_args:
                filtered_args["hour"] = 8
            if "minute" not in filtered_args:
                filtered_args["minute"] = 0

        return func(**filtered_args)

    def _parse_text_tool_call(self, text: str):
        match = re.search(r'([A-Za-z_]+)\s*\{([^}]+)\}', text)
        if match:
            fn_candidate = match.group(1).strip().lower()
            args_raw = match.group(2).strip()

            target_fn = None
            for tool_name in self.tools_map.keys():
                if tool_name.lower() == fn_candidate or fn_candidate in tool_name.lower():
                    target_fn = tool_name
                    break

            if not target_fn:
                if "compromisso" in text.lower() or "criar" in text.lower():
                    target_fn = "create_calendar_event"
                elif "agenda" in text.lower() or "calendar" in text.lower():
                    target_fn = "get_calendar_events"
                elif "previsão" in text.lower() or "clima" in text.lower():
                    target_fn = "get_weather"
                elif "notícia" in text.lower():
                    target_fn = "get_news"
                elif "busca" in text.lower() or "search" in text.lower():
                    target_fn = "search_web"
                elif "timer" in text.lower():
                    target_fn = "set_timer"
                elif "alarm" in text.lower() or "alarme" in text.lower():
                    target_fn = "set_alarm"
                elif "ytmusic" in text.lower() or "music" in text.lower() or "tocar" in text.lower():
                    target_fn = "play_ytmusic"

            if target_fn:
                args = {}
                pairs = re.findall(r'(\w+)\s*:\s*([^,}]+)', args_raw)
                for k, v in pairs:
                    val = v.strip().strip("'\"")
                    if val.isdigit():
                        val = int(val)
                    args[k] = val
                return target_fn, args

        return None, None

    def ask(self, user_prompt: str) -> str:
        normalized = user_prompt
        normalized = re.sub(r'\b(para\s+o\s+manhã|para\s+a\s+manhã|pra\s+a\s+manhã|pra\s+o\s+manhã|o\s+manhã|a\s+manhã|amanya)\b', 'amanhã', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\b(tá\s+a\s+merda|támerda|taimer|táime|taime)\b', 'timer', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\b(definitão|defina\s+então|defino)\b', 'defina', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\ba\s+larme\b', 'alarme', normalized, flags=re.IGNORECASE)

        clean_prompt = re.sub(r'[^\w\s]', '', normalized).lower().strip()

        # 1. Bypass direto: Horas Certa
        if bool(re.search(r'\b(que\s+horas\s+são|hora\s+certa|qual\s+é\s+a\s+hora|horas\s+agora|que\s+horas\s+temos)\b', clean_prompt)):
            res_hora = SystemTools.get_current_time()
            return clean_for_speech(res_hora)

        # 2. Bypass direto: Alarme
        if "alarme" in clean_prompt and any(w in clean_prompt for w in ["defina", "coloque", "bote", "marque", "crie"]):
            m_hora = re.search(r'(\d{1,2})(?:\s*horas?|\s*h)?(?:\s*e\s*(\d{1,2}))?', clean_prompt)
            if m_hora:
                h = int(m_hora.group(1))
                m = int(m_hora.group(2)) if m_hora.group(2) else 0
                if any(p in clean_prompt for p in ["noite", "tarde"]) and h < 12:
                    h += 12
                res = TimerManager.add_alarm(hour=h, minute=m, label="Alarme")
                return clean_for_speech(str(res))

        # 3. Bypass direto: Timer
        if "timer" in clean_prompt and any(w in clean_prompt for w in ["defina", "coloque", "bote", "inicie", "comece"]):
            m_min = re.search(r'(\d+)\s*(?:minuto|minutos|min|m)', clean_prompt)
            if m_min:
                minutos = int(m_min.group(1))
                m_rotulo = re.search(r'para\s+(?:o|a)?\s*(.+)', clean_prompt)
                rotulo = m_rotulo.group(1).strip() if m_rotulo else "Timer"
                res = TimerManager.add_timer(minutes=minutos, label=rotulo)
                return clean_for_speech(str(res))

        # 4. Bom dia
        if re.search(r'\b(bom\s+dia|boa\s+dia)\b', clean_prompt):
            weather_info = SystemTools.get_weather("hoje")
            agenda_info = CalendarTools.get_events("hoje")
            return clean_for_speech(f"Bom dia! {weather_info}. {agenda_info}")

        # 5. Agradecimentos
        agradecimentos = ["obrigado", "muito obrigado", "valeu", "valeu geraldo", "agradecido", "obrigada"]
        if any(clean_prompt.startswith(a) for a in agradecimentos):
            self.history.clear()
            return "De nada! Qualquer coisa é só chamar."

        # 6. Bypass determinístico: Busca na Web / Resultados / Pesquisa Eleitoral
        termos_busca_forcada = ["pesquise", "pesquisa eleitoral", "último campeão", "ultimo campeao", "atual campeão", "atual campeao", "quem ganhou", "quem venceu", "cotação do"]
        if any(t in clean_prompt for t in termos_busca_forcada):
            query_busca = re.sub(r'^(pesquise sobre|pesquise|procure sobre|procure|busque por|busque)\s*', '', normalized, flags=re.IGNORECASE).strip()
            print(f"[Geraldo:BypassSearch] Forçando busca web para: {query_busca}")
            
            filler = random.choice([
                f"Procurando na internet sobre {query_busca}...",
                "Consultando a internet, um instante...",
                f"Deixa eu verificar na web sobre {query_busca}..."
            ])
            print(f"[Geraldo:Filler]: {filler}")
            self._speak_filler_async(clean_for_speech(filler))
            
            tool_result = WebSearchTools.search_web(query=query_busca)
            sys_instruction = (
                "Você é o Geraldo, assistente estilo Alexa. Com base nos fatos fornecidos, responda em 1 ou 2 frases curtas, "
                "diretas e precisas para áudio. NUNCA mencione fontes, links ou introduções."
            )
            follow_up = self._post_json({
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": sys_instruction},
                    {"role": "user", "content": f"Pergunta: {normalized}\nFatos encontrados: {tool_result}"}
                ],
                "stream": False,
                "keep_alive": -1,
                "options": LLM_OPTIONS
            })
            final_msg = follow_up.get("message", {})
            raw_reply = final_msg.get("content", "").strip() or str(tool_result)
            reply_text = clean_for_speech(raw_reply)
            self.history.append({"role": "user", "content": normalized})
            self.history.append({"role": "assistant", "content": reply_text})
            return reply_text

        # 7. Bypass determinístico: Agenda
        palavras_criacao = ["marque", "marca", "marcar", "agende", "agenda", "agendar", "crie", "criar", "adicione", "adicionar", "botar", "coloque", "colocar", "lembra", "lembre"]
        is_creation = any(w in clean_prompt.split() for w in palavras_criacao)

        if not is_creation and any(w in clean_prompt for w in ["agenda", "compromisso", "compromissos"]):
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

            res_agenda = CalendarTools.get_events(alvo)
            sys_instruction = f"Você é o Geraldo. Diga os compromissos para {alvo} em 1 frase curta para voz. Sem introduções."
            follow_up = self._post_json({
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": sys_instruction},
                    {"role": "user", "content": f"Pergunta: {normalized}\nAgenda: {res_agenda}"}
                ],
                "stream": False,
                "keep_alive": -1,
                "options": LLM_OPTIONS
            })
            reply_text = clean_for_speech(follow_up.get("message", {}).get("content", "") or res_agenda)
            self.history.clear()
            self.history.append({"role": "user", "content": normalized})
            self.history.append({"role": "assistant", "content": reply_text})
            return reply_text

        # 8. Bypass determinístico: Previsão do tempo / Clima
        if any(w in clean_prompt for w in ["clima", "tempo", "temperatura", "chover", "chuva"]):
            alvo_clima = "hoje"
            if "amanhã" in clean_prompt or "amanha" in clean_prompt:
                alvo_clima = "amanhã"
            elif "semana" in clean_prompt:
                alvo_clima = "semana"

            clima_info = SystemTools.get_weather(alvo_clima)
            sys_instruction = f"Você é o Geraldo. Resuma o clima para {alvo_clima} em 1 frase curta e natural para voz. Sem saudações nem introduções."
            follow_up = self._post_json({
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": sys_instruction},
                    {"role": "user", "content": f"Dados do tempo: {clima_info}"}
                ],
                "stream": False,
                "keep_alive": -1,
                "options": LLM_OPTIONS
            })
            reply_text = clean_for_speech(follow_up.get("message", {}).get("content", "") or clima_info)
            self.history.clear()
            self.history.append({"role": "user", "content": normalized})
            self.history.append({"role": "assistant", "content": reply_text})
            return reply_text

        system_content = get_dynamic_system_prompt()
        messages = [{"role": "system", "content": system_content}]
        messages.extend(list(self.history))
        messages.append({"role": "user", "content": normalized})

        payload = {
            "model": LLM_MODEL,
            "messages": messages,
            "tools": TOOLS_SCHEMA,
            "stream": False,
            "keep_alive": -1,
            "options": LLM_OPTIONS
        }

        try:
            data = self._post_json(payload)
            message = data.get("message", {})

            fn_name = None
            fn_args = {}

            if "tool_calls" in message and message["tool_calls"]:
                tool_call = message["tool_calls"][0]
                fn_name = tool_call.get("function", {}).get("name")
                fn_args = tool_call.get("function", {}).get("arguments", {})
            else:
                raw_content = message.get("content", "")
                parsed_fn, parsed_args = self._parse_text_tool_call(raw_content)
                if parsed_fn:
                    fn_name = parsed_fn
                    fn_args = parsed_args

            if fn_name and fn_name in self.tools_map:
                print(f"[Geraldo:Tool] Executando {fn_name}({fn_args})...")

                if fn_name in ["search_web", "get_news"]:
                    termo = fn_args.get("query", "")
                    if fn_name == "search_web":
                        opcoes = [
                            f"Procurando na internet sobre {termo}...",
                            f"Deixa eu pesquisar na web sobre {termo}...",
                            "Consultando a internet, um instante..."
                        ]
                    else:
                        opcoes = [
                            f"Buscando as últimas notícias sobre {termo}...",
                            "Verificando os principais jornais de hoje...",
                            "Buscando acontecimentos recentes..."
                        ]
                    filler = random.choice(opcoes)
                    print(f"[Geraldo:Filler]: {filler}")
                    self._speak_filler_async(clean_for_speech(filler))

                tool_result = self._execute_tool_safely(fn_name, fn_args)

                if fn_name in [
                    "create_calendar_event", "set_timer", "set_alarm", "control_stopwatch",
                    "cancel_timers", "play_ytmusic", "stop_ytmusic", "play_pause_media",
                    "set_volume", "get_current_time"
                ]:
                    reply_text = clean_for_speech(str(tool_result))
                    self.history.append({"role": "user", "content": normalized})
                    self.history.append({"role": "assistant", "content": reply_text})
                    return reply_text

                sys_instruction = (
                    "Você é o Geraldo. Responda em 1 frase curta e direta para áudio, estilo Alexa. "
                    "NUNCA cite códigos, links ou introduções."
                )

                follow_up = self._post_json({
                    "model": LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": sys_instruction},
                        {"role": "user", "content": f"Pergunta: {normalized}\nFatos encontrados: {tool_result}"}
                    ],
                    "stream": False,
                    "keep_alive": -1,
                    "options": LLM_OPTIONS
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
