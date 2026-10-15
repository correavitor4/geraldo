# brain/llm.py
import ollama
from config import OLLAMA_HOST, LLM_MODEL, SYSTEM_PROMPT

class BrainLLM:
    def __init__(self, host: str = OLLAMA_HOST, model: str = LLM_MODEL):
        self.client = ollama.Client(host=host)
        self.model = model
        self.system_prompt = SYSTEM_PROMPT

    def ask(self, user_text: str, tools: list = None) -> dict:
        """
        Envia a mensagem transcrita para o Ollama e retorna a resposta
        ou as ferramentas solicitadas pelo modelo.
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_text}
        ]

        kwargs = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        response = self.client.chat(**kwargs)
        return response["message"]