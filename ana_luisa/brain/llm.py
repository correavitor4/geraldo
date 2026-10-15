import json
import urllib.request
import urllib.error
from config import OLLAMA_HOST, LLM_MODEL, SYSTEM_PROMPT
from tools.system import SystemTools

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "play_pause_media",
            "description": "Alterna entre pausar e tocar musicas ou videos no computador via playerctl.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "next_media",
            "description": "Pula para a proxima musica ou video.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "previous_media",
            "description": "Volta para a musica ou video anterior.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_volume",
            "description": "Aumenta, diminui ou muta o volume do audio do sistema.",
            "parameters": {
                "type": "object",
                "properties": {
                    "change": {
                        "type": "string",
                        "enum": ["+", "-", "mute"],
                        "description": "Use + para aumentar, - para diminuir, ou mute para alternar mudo."
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
            "description": "Informa as horas exatas e a data de hoje.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }
]

class BrainLLM:
    def __init__(self):
        self.api_url = f"{OLLAMA_HOST}/api/chat"
        self.tools_map = {
            "play_pause_media": SystemTools.play_pause_media,
            "next_media": SystemTools.next_media,
            "previous_media": SystemTools.previous_media,
            "set_volume": SystemTools.set_volume,
            "get_current_time": SystemTools.get_current_time,
        }

    def _post_json(self, payload: dict) -> dict:
        req = urllib.request.Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def ask(self, user_prompt: str) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        payload = {
            "model": LLM_MODEL,
            "messages": messages,
            "tools": TOOLS_SCHEMA,
            "stream": False
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
                    if fn_args:
                        tool_result = self.tools_map[fn_name](**fn_args)
                    else:
                        tool_result = self.tools_map[fn_name]()

                    messages.append(message)
                    messages.append({
                        "role": "tool",
                        "content": str(tool_result)
                    })

                    follow_up = self._post_json({"model": LLM_MODEL, "messages": messages, "stream": False})
                    final_msg = follow_up.get("message", {})
                    return final_msg.get("content", tool_result)

            return message.get("content", "")

        except Exception as e:
            print(f"[Geraldo:LLM Error]: {e}")
            return "Desculpe, tive uma falha ao processar a resposta."

