import collections
import json
import urllib.request
import urllib.error
from config import OLLAMA_HOST, LLM_MODEL, SYSTEM_PROMPT
from tools.system import SystemTools
from tools.ytmusic import YTMusicPlayer

SYSTEM_PROMPT_TOOLS = SYSTEM_PROMPT + """
REGRA DE MÚSICA E YOUTUBE MUSIC:
- Se o usuário pedir para tocar música, banda, artista ou gênero: chame a ferramenta "play_ytmusic".
- CORREÇÃO DE NOMES: Se a transcrição de voz parecer um erro fonético de nome de cantor ou música (ex: "bob mali" -> "Bob Marley", "zé ramalho", "the winner take it all" -> "ABBA The Winner Takes It All"), CORRIJA o texto do parâmetro "query" para o nome correto do artista/música antes de chamar a ferramenta.
- Se pedir para parar/pausar: use "stop_ytmusic" ou "play_pause_media".
- Para clima e previsão do tempo: chame "get_weather".
- Para horas ou data: chame "get_current_time".
"""

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "play_ytmusic",
            "description": "Corrige o nome e abre a musica ou artista no YouTube Music pelo navegador.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Nome corrigido da musica ou artista."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "stop_ytmusic",
            "description": "Pausa ou para a reproducao de midia.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "play_pause_media",
            "description": "Pausa ou retoma a reproducao atual.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_volume",
            "description": "Altera o volume de audio do sistema operacional.",
            "parameters": {
                "type": "object",
                "properties": {
                    "change": {
                        "type": "string",
                        "enum": ["+", "-", "mute"],
                        "description": "Sinal + para aumentar, - para diminuir, ou mute."
                    }
                },
                "required": ["change"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Consulta as horas e a data atual do relogio do sistema.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Consulta o clima e previsao de tempo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "enum": ["hoje", "semana"],
                        "description": "hoje ou semana"
                    }
                },
                "required": []
            }
        }
    }
]

class BrainLLM:
    def __init__(self, max_history_turns: int = 6):
        self.api_url = f"{OLLAMA_HOST}/api/chat"
        self.history = collections.deque(maxlen=max_history_turns)
        self.tools_map = {
            "play_ytmusic": YTMusicPlayer.play_song,
            "stop_ytmusic": YTMusicPlayer.stop,
            "play_pause_media": SystemTools.play_pause_media,
            "set_volume": SystemTools.set_volume,
            "get_current_time": SystemTools.get_current_time,
            "get_weather": SystemTools.get_weather,
        }

    def reset_memory(self):
        self.history.clear()
        print("[Geraldo:Memoria] Historico limpo.")

    def _post_json(self, payload: dict) -> dict:
        req = urllib.request.Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def ask(self, user_prompt: str) -> str:
        lowered = user_prompt.lower()
        if any(cmd in lowered for cmd in ["esquece o que conversamos", "esquecer conversa", "limpar memoria", "novo assunto"]):
            self.reset_memory()
            return "Memória recente apagada."

        messages = [{"role": "system", "content": SYSTEM_PROMPT_TOOLS}]
        messages.extend(list(self.history))
        messages.append({"role": "user", "content": user_prompt})

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
                    tool_result = self.tools_map[fn_name](**fn_args) if fn_args else self.tools_map[fn_name]()

                    reply_text = str(tool_result)
                    self.history.append({"role": "user", "content": user_prompt})
                    self.history.append({"role": "assistant", "content": reply_text})
                    return reply_text

            reply_text = message.get("content", "")
            if reply_text:
                self.history.append({"role": "user", "content": user_prompt})
                self.history.append({"role": "assistant", "content": reply_text})

            return reply_text

        except Exception as e:
            print(f"[Geraldo:LLM Error]: {e}")
            return "Desculpe, tive uma falha ao processar a resposta."

