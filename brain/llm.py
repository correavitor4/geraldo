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

def get_dynamic_system_prompt() -> str:
    agora = datetime.datetime.now()
    dias_semana = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
    dia_nome = dias_semana[agora.weekday()]
    data_contexto = f"{dia_nome}, {agora.day} de {agora.strftime('%B')} de {agora.year}, {agora.strftime('%H:%M')}."

    return SYSTEM_PROMPT + f"""
VOCÊ É O GERALDO, ASSISTENTE DE VOZ PARA LINUX.

CONTEXTO TEMPORAL:
- HOJE É {data_contexto}
- O ANO É {agora.year}. NUNCA responda eleições antigas de 2022 ou 2024.

MÚSICA NO YOUTUBE MUSIC ("play_ytmusic"):
- Quando o usuário disser "álbum", "disco" ou citar uma obra completa (ex: "Live at the BBC", "Back to Black álbum"):
  -> Chame "play_ytmusic" passando "item_type": "album".
- Para faixas avulsas:
  -> Chame "play_ytmusic" passando "item_type": "musica".

CONHECIMENTO GERAL:
- Dúvidas de matemática, definições e conceitos não usam ferramentas; responda direto em 1 a 2 frases.
- 1 dúzia = 12 unidades. Meia dúzia = 6 unidades.
- NUNCA use markdown nem saudações de radialista.
"""

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "play_ytmusic",
            "description": "Reproduz música ou álbum no YouTube Music.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Nome da música, álbum ou artista."
                    },
                    "item_type": {
                        "type": "string",
                        "enum": ["musica", "album", "auto"],
                        "description": "Defina 'album' se for um álbum completo ou 'musica' se for faixa avulsa."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Busca dados factuais e recentes na web via DuckDuckGo.",
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
            "description": "Busca manchetes e reportagens jornalísticas recentes.",
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
            "name": "stop_ytmusic",
            "description": "Pausa ou encerra a reprodução de áudio.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "play_pause_media",
            "description": "Alterna entre reproduzir e pausar.",
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
            "name": "get_current_time",
            "description": "Consulta data e hora atual.",
            "parameters": {"type": "object", "properties": {}, "required": []}
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

    def ask(self, user_prompt: str) -> str:
        # Normalizações fonéticas antes do LLM
        normalized = user_prompt
        normalized = re.sub(r'\b(tokyo|talk to)\b', 'toque', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bdiana winehouse\b', 'Amy Winehouse', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bbpc\b', 'BBC', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\b(numa|em uma|numa|em)\s+12\b', 'em uma dúzia', normalized, flags=re.IGNORECASE)

        lowered = normalized.lower()
        agradecimentos = ["obrigado", "muito obrigado", "valeu", "valeu geraldo", "agradecido", "obrigada"]
        if any(lowered.startswith(a) for a in agradecimentos):
            self.history.clear()
            return "De nada! Sempre que precisar é só chamar."

        perguntas_diretas = ["quantos", "quantas", "o que é", "o que e", "quem veio primeiro", "como se calcula", "quanto é", "quanto e", "dúzia", "duzia"]
        ordens_claras = ["tocar", "toque", "reproduza", "notícia", "noticia", "jornal", "clima", "tempo", "hora", "volume", "pesquise"]

        enviar_tools = True
        if any(p in lowered for p in perguntas_diretas) and not any(o in lowered for o in ordens_claras):
            enviar_tools = False

        system_content = get_dynamic_system_prompt()
        messages = [{"role": "system", "content": system_content}]
        messages.extend(list(self.history))
        messages.append({"role": "user", "content": normalized})

        payload = {
            "model": LLM_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.1}
        }
        if enviar_tools:
            payload["tools"] = TOOLS_SCHEMA

        try:
            data = self._post_json(payload)
            message = data.get("message", {})

            if "tool_calls" in message and message["tool_calls"]:
                tool_call = message["tool_calls"][0]
                fn_name = tool_call.get("function", {}).get("name")
                fn_args = tool_call.get("function", {}).get("arguments", {})

                # Injeta 2026 em buscas políticas sem ano
                if fn_name in ["search_web", "get_news"]:
                    q = fn_args.get("query", "")
                    termos_eleicao = ["eleição", "eleicoes", "eleições", "eleitoral", "presidente", "segundo turno", "disputa"]
                    if any(t in q.lower() for t in termos_eleicao) and "202" not in q:
                        ano_atual = datetime.datetime.now().year
                        fn_args["query"] = f"{q} {ano_atual}"

                if fn_name in self.tools_map:
                    print(f"[Geraldo:Tool] Executando {fn_name}({fn_args})...")
                    tool_result = self._execute_tool_safely(fn_name, fn_args)

                    if fn_name in ["play_ytmusic", "stop_ytmusic", "play_pause_media", "set_volume", "get_current_time", "get_weather"]:
                        reply_text = clean_for_speech(str(tool_result))
                        self.history.append({"role": "user", "content": normalized})
                        self.history.append({"role": "assistant", "content": reply_text})
                        return reply_text

                    ano_atual = datetime.datetime.now().year
                    sys_instruction = (
                        f"Você é o Geraldo. O ano atual é {ano_atual}. Resuma as informações abaixo em no máximo 2 a 3 frases "
                        "diretas e estritamente factuais. NUNCA use saudações nem markdown. Vá direto ao ponto."
                    )

                    follow_up = self._post_json({
                        "model": LLM_MODEL,
                        "messages": [
                            {"role": "system", "content": sys_instruction},
                            {"role": "user", "content": f"Pergunta: {normalized}\nDados levantados: {tool_result}"}
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
