"""
Analisador e sumarizador de reuniões (Local via Ollama Qwen2.5 e Nuvem via Gemini/OpenAI).
"""
from abc import ABC, abstractmethod
import json
import re
import time
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

from services.meeting.models import MeetingSummary
import config


MEETING_SYSTEM_PROMPT = """Você é um assistente executivo e secretário profissional sênior.
Sua missão é analisar transcrições brutas de reuniões, conversas com clientes ou prestadores de serviços,
corrigir imperfeições da linguagem falada, identificar o cerne das discussões e gerar uma ata executiva impecável.

Você DEVE responder ESTRITAMENTE em formato JSON com o seguinte schema:
{
  "title": "Título descritivo e conciso para a reunião",
  "executive_summary": "Parágrafo coeso resumindo o objetivo e o resultado principal da reunião.",
  "topics": [
    "Tópico 1 discutido",
    "Tópico 2 discutido"
  ],
  "decisions": [
    "Decisão ou acordo formal 1",
    "Decisão ou acordo formal 2"
  ],
  "action_items": [
    {
      "task": "Descrição clara da ação que precisa ser executada",
      "owner": "Nome do responsável (ou 'Não atribuído' se não especificado)",
      "deadline": "Prazo acordado (ou 'A definir' se não especificado)"
    }
  ]
}

Regras:
1. Responda em Português do Brasil com gramática e pontuação profissionais.
2. Seja objetivo e factual: não invente dados, nomes ou decisões que não constem na transcrição.
3. Responda SOMENTE o objeto JSON, sem nenhum texto introdutório ou conclusivo fora dele.
"""


def parse_summary_json(raw: str, default_title: str = "Reunião") -> Dict[str, Any]:
    """Extrai e valida o JSON da resposta da LLM com fallbacks tolerantes."""
    if not raw:
        return {}

    # Tentativa 1: Busca bloco de código ```json ... ```
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    # Tentativa 2: Busca primeiro objeto {...} no texto
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    # Tentativa 3: Parse direto
    try:
        return json.loads(raw)
    except Exception:
        pass

    # Fallback estruturado caso a LLM retorne texto livre
    return {
        "title": default_title,
        "executive_summary": raw.strip(),
        "topics": [],
        "decisions": [],
        "action_items": []
    }


class MeetingAnalyzer(ABC):
    @abstractmethod
    def analyze(self, transcript: str, metadata: Optional[Dict[str, Any]] = None) -> MeetingSummary:
        """Processa a transcrição e gera a ata estruturada."""
        pass


class LocalMeetingAnalyzer(MeetingAnalyzer):
    """Análise local e confidencial usando Ollama (ex: qwen2.5:3b)."""

    def __init__(
        self,
        host: Optional[str] = None,
        model: Optional[str] = None,
        num_ctx: int = 8192,
    ):
        self.host = host or getattr(config, "OLLAMA_HOST", "http://localhost:11434")
        self.model = model or getattr(config, "LLM_MODEL", "qwen2.5:3b")
        self.num_ctx = num_ctx

    def analyze(self, transcript: str, metadata: Optional[Dict[str, Any]] = None) -> MeetingSummary:
        meta = metadata or {}
        default_title = meta.get("title") or "Reunião"
        duration = float(meta.get("duration_seconds", 0.0))
        date_str = meta.get("date") or time.strftime("%d/%m/%Y %H:%M")

        if not transcript.strip():
            return MeetingSummary(
                title=default_title,
                date=date_str,
                duration_seconds=duration,
                executive_summary="Nenhuma fala audível foi registrada nesta sessão de reunião.",
                topics=[],
                decisions=[],
                action_items=[],
                raw_markdown=""
            )

        user_content = (
            f"Metadados da Reunião:\n"
            f"- Título Provisório: {default_title}\n"
            f"- Data: {date_str}\n\n"
            f"Transcrição da conversa:\n\"\"\"\n{transcript.strip()}\n\"\"\"\n\n"
            f"Gere a ata estruturada em JSON conforme as regras."
        )

        h = self.host.strip().rstrip("/")
        if not (h.startswith("http://") or h.startswith("https://")):
            h = f"http://{h}"
        url = f"{h}/api/chat"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": MEETING_SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            "options": {
                "temperature": 0.2,
                "num_ctx": self.num_ctx,
                "num_predict": 1024
            },
            "stream": False
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            raw_text = data.get("message", {}).get("content", "")
        except Exception as e:
            # Fallback tolerante em caso de erro de conexão com o Ollama
            return MeetingSummary(
                title=default_title,
                date=date_str,
                duration_seconds=duration,
                executive_summary=f"Não foi possível conectar ao Ollama local para gerar o resumo: {e}",
                topics=[],
                decisions=[],
                action_items=[],
                raw_markdown=""
            )

        parsed = parse_summary_json(raw_text, default_title=default_title)
        return MeetingSummary(
            title=parsed.get("title") or default_title,
            date=date_str,
            duration_seconds=duration,
            executive_summary=parsed.get("executive_summary", ""),
            topics=parsed.get("topics", []),
            decisions=parsed.get("decisions", []),
            action_items=parsed.get("action_items", []),
            raw_markdown=raw_text
        )


class CloudMeetingAnalyzer(MeetingAnalyzer):
    """Análise via nuvem (Google Gemini, OpenAI, Groq) com suporte a contextos longos."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or getattr(config, "LLM_API_KEY", "")
        presets = getattr(config, "PROVIDER_PRESETS", {})
        default_gemini_base = presets.get("gemini", {}).get("default_base", "https://generativelanguage.googleapis.com/v1beta/openai")
        self.api_base = (api_base or default_gemini_base).rstrip("/")
        self.model = model or "gemini-2.0-flash"

    def analyze(self, transcript: str, metadata: Optional[Dict[str, Any]] = None) -> MeetingSummary:
        meta = metadata or {}
        default_title = meta.get("title") or "Reunião"
        duration = float(meta.get("duration_seconds", 0.0))
        date_str = meta.get("date") or time.strftime("%d/%m/%Y %H:%M")

        if not transcript.strip():
            return MeetingSummary(
                title=default_title,
                date=date_str,
                duration_seconds=duration,
                executive_summary="Nenhuma fala audível foi registrada nesta sessão de reunião.",
                topics=[],
                decisions=[],
                action_items=[],
                raw_markdown=""
            )

        user_content = (
            f"Metadados da Reunião:\n"
            f"- Título Provisório: {default_title}\n"
            f"- Data: {date_str}\n\n"
            f"Transcrição da conversa:\n\"\"\"\n{transcript.strip()}\n\"\"\"\n\n"
            f"Gere a ata estruturada em JSON conforme as regras."
        )

        url = f"{self.api_base}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": MEETING_SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Geraldo-MeetingAssistant/1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key.strip()}"

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            raw_text = data["choices"][0]["message"]["content"]
        except Exception as e:
            return MeetingSummary(
                title=default_title,
                date=date_str,
                duration_seconds=duration,
                executive_summary=f"Erro ao consultar a API na nuvem: {e}",
                topics=[],
                decisions=[],
                action_items=[],
                raw_markdown=""
            )

        parsed = parse_summary_json(raw_text, default_title=default_title)
        return MeetingSummary(
            title=parsed.get("title") or default_title,
            date=date_str,
            duration_seconds=duration,
            executive_summary=parsed.get("executive_summary", ""),
            topics=parsed.get("topics", []),
            decisions=parsed.get("decisions", []),
            action_items=parsed.get("action_items", []),
            raw_markdown=raw_text
        )


def create_meeting_analyzer(provider: str = "local", **kwargs) -> MeetingAnalyzer:
    """Fábrica de instâncias de analisadores."""
    p = (provider or "local").lower()
    if p in ("cloud", "gemini", "openai", "groq"):
        return CloudMeetingAnalyzer(**kwargs)
    return LocalMeetingAnalyzer(**kwargs)
