import collections
import json
import urllib.request
import urllib.error
from config import OLLAMA_HOST, LLM_MODEL, SYSTEM_PROMPT
from tools.system import SystemTools

SYSTEM_PROMPT_TOOLS = SYSTEM_PROMPT + """
REGRA OBRIGATÓRIA DE FERRAMENTAS:
- Ao receber o resultado da ferramenta "get_weather", transmita a resposta com naturalidade em voz alta.
- Mantenha sempre todos os acentos ortográficos (Anápolis, máxima, mínima, graus Celsius).
- NUNCA abrevie graus Celsius nem use simbolos como o grau ou porcentagem.
- Nunca diga que nao pode responder ou que nao tem acesso a dados em tempo real.
"""

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "play_pause_media",
            "description": "Pausa ou retoma a musica ou video tocando no computador.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "next_media",
            "description": "Pula para a proxima faixa de musica.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "previous_media",
            "description": "Volta para a faixa de musica anterior.",
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
                        "description": "Sinal + para aumentar volume, - para diminuir, ou mute."
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
            "description": "Consulta o clima, temperatura atual, sensação térmica, umidade e previsão com mínimas e máximas de hoje ou da semana.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "enum": ["hoje", "semana"],
                        "description": "Use semana se o usuario perguntou sobre a semana ou previsao estendida. Caso contrario use hoje."
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
            "play_pause_media": SystemTools.play_pause_media,
            "next_media": SystemTools.next_media,
            "previous_media": SystemTools.previous_media,
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

                    # Para clima ou relógio, o retorno da tool já é perfeito e 100% acentuado
                    if fn_name in ["get_weather", "get_current_time"]:
                        reply_text = str(tool_result)
                        self.history.append({"role": "user", "content": user_prompt})
                        self.history.append({"role": "assistant", "content": reply_text})
                        return reply_text

                    tool_messages = list(messages)
                    tool_messages.append(message)
                    tool_messages.append({
                        "role": "tool",
                        "content": str(tool_result)
                    })

                    follow_up = self._post_json({
                        "model": LLM_MODEL,
                        "messages": tool_messages,
                        "stream": False,
                        "options": {"temperature": 0.1}
                    })
                    final_msg = follow_up.get("message", {})
                    reply_text = final_msg.get("content", "").strip() or str(tool_result)

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

