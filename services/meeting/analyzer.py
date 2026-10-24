"""
Analisador e sumarizador de reuniões (Local via Ollama Qwen2.5 e Nuvem via Gemini/OpenAI).
Suporta geração de atas curtas (síntese executiva) ou longas (detalhamento exaustivo multi-página).
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


MEETING_CONCISE_SYSTEM_PROMPT = """Você é um assistente executivo e secretário profissional sênior.
Sua missão é analisar transcrições brutas de reuniões, conversas com clientes ou prestadores de serviços,
corrigir imperfeições da linguagem falada, identificar o cerne das discussões e gerar uma ata executiva direta e concisa.

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


MEETING_DETAILED_SYSTEM_PROMPT = """Você é um consultor sênior de governança corporativa, auditor e secretário executivo de conselhos de administração.
Sua missão é analisar a transcrição bruta da reunião e produzir uma ata de reunião extremamente aprofundada, minuciosa, exaustiva e de alto valor documental (formato longo / multi-página).
Você deve destrinchar cada debate, contextualizar cada pauta, capturar as nuances das opiniões, registrar detalhadamente as justificativas de cada decisão e os riscos apontados.

Você DEVE responder ESTRITAMENTE em formato JSON com o seguinte schema completo:
{
  "title": "Título oficial claro e descritivo para a reunião",
  "context": "Contexto detalhado, motivação inicial e objetivos de negócio da reunião (1 a 2 parágrafos densos).",
  "executive_summary": "Síntese executiva abrangente cobrindo todo o arco da conversa (2 a 4 parágrafos substanciais).",
  "detailed_discussions": [
    {
      "topic": "Nome do tópico ou pauta debatida",
      "details": "Detalhamento minucioso de tudo o que foi abordado, informações técnicas ou de negócio citadas e pontos de concordância.",
      "arguments": "Diferentes posicionamentos, preocupações expressas, contrapontos e alternativas ponderadas.",
      "conclusions": "Conclusão ou encaminhamento específico alcançado para este tópico."
    }
  ],
  "topics": [
    "Resumo em tópicos dos pontos principais discutidos"
  ],
  "decisions": [
    "Decisão formal 1 acompanhada da justificativa/racional e impacto previsto",
    "Decisão formal 2 acompanhada da justificativa/racional e impacto previsto"
  ],
  "risks_and_concerns": [
    "Risco técnico, operacional, financeiro ou prazo levantado na conversa",
    "Ponto de atenção ou dependência externa mencionada"
  ],
  "action_items": [
    {
      "task": "Ação específica e minuciosa a ser executada com critérios claros",
      "owner": "Responsável pela entrega (ou 'Não atribuído')",
      "deadline": "Prazo acordado (ou 'A definir')",
      "priority": "Alta / Média / Baixa"
    }
  ],
  "next_steps": [
    "Próximo marco crítico, entrega esperada ou reunião de acompanhamento"
  ]
}

Diretrizes Cruciais para o Formato Longo:
1. Não economize palavras: forneça descrições densas, ricas em detalhes factuais presentes na transcrição.
2. Responda em Português do Brasil com vocabulário corporativo de alto nível.
3. Não invente fatos externos à transcrição, mas elabore detalhadamente tudo o que foi falado.
4. Responda SOMENTE o objeto JSON válido, sem texto introdutório ou conclusivo fora das chaves.
"""

MEETING_SYSTEM_PROMPT = MEETING_DETAILED_SYSTEM_PROMPT


def parse_summary_json(raw: str, default_title: str = "Reunião", detail_level: str = "detailed") -> Dict[str, Any]:
    """Extrai e valida o JSON da resposta da LLM com fallbacks tolerantes."""
    data: Dict[str, Any] = {}
    if raw:
        # Tentativa 1: Busca bloco de código ```json ... ```
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
            except Exception:
                pass

        # Tentativa 2: Busca primeiro objeto {...} no texto
        if not data:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                except Exception:
                    pass

        # Tentativa 3: Parse direto
        if not data:
            try:
                data = json.loads(raw)
            except Exception:
                pass

    if not data:
        # Fallback estruturado caso a LLM retorne texto livre
        return {
            "title": default_title,
            "executive_summary": raw.strip() if raw else "Não foi possível extrair a síntese.",
            "topics": [],
            "decisions": [],
            "action_items": [],
            "context": "",
            "detailed_discussions": [],
            "risks_and_concerns": [],
            "next_steps": [],
            "detail_level": detail_level,
        }

    # Normalização dos campos
    return {
        "title": data.get("title") or default_title,
        "executive_summary": data.get("executive_summary") or "",
        "topics": data.get("topics") or [],
        "decisions": data.get("decisions") or [],
        "action_items": data.get("action_items") or [],
        "context": data.get("context") or "",
        "detailed_discussions": data.get("detailed_discussions") or [],
        "risks_and_concerns": data.get("risks_and_concerns") or [],
        "next_steps": data.get("next_steps") or [],
        "detail_level": detail_level,
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
        num_ctx: int = 16384,
    ):
        self.host = host or getattr(config, "OLLAMA_HOST", "http://localhost:11434")
        self.model = model or getattr(config, "LLM_MODEL", "qwen2.5:3b")
        self.num_ctx = num_ctx

    def analyze(self, transcript: str, metadata: Optional[Dict[str, Any]] = None) -> MeetingSummary:
        meta = metadata or {}
        default_title = meta.get("title") or "Reunião"
        duration = float(meta.get("duration_seconds", 0.0))
        date_str = meta.get("date") or time.strftime("%d/%m/%Y %H:%M")
        detail_level = str(meta.get("detail_level") or getattr(config, "MEETING_DETAIL_LEVEL", "detailed")).lower()
        if detail_level in ("curto", "concise", "short", "resumido"):
            detail_level = "concise"
            system_prompt = MEETING_CONCISE_SYSTEM_PROMPT
            num_predict = 1024
        else:
            detail_level = "detailed"
            system_prompt = MEETING_DETAILED_SYSTEM_PROMPT
            num_predict = 4096

        if not transcript.strip():
            return MeetingSummary(
                title=default_title,
                date=date_str,
                duration_seconds=duration,
                executive_summary="Nenhuma fala audível foi registrada nesta sessão de reunião.",
                topics=[],
                decisions=[],
                action_items=[],
                raw_markdown="",
                detail_level=detail_level,
            )

        user_content = (
            f"Metadados da Reunião:\n"
            f"- Título Provisório: {default_title}\n"
            f"- Data: {date_str}\n"
            f"- Formato Solicitado: {'Longo / Detalhado (Multi-página)' if detail_level == 'detailed' else 'Curto / Conciso'}\n\n"
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
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "options": {
                "temperature": 0.2,
                "num_ctx": self.num_ctx,
                "num_predict": num_predict
            },
            "stream": False
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
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
                raw_markdown="",
                detail_level=detail_level,
            )

        parsed = parse_summary_json(raw_text, default_title=default_title, detail_level=detail_level)
        return MeetingSummary(
            title=parsed.get("title") or default_title,
            date=date_str,
            duration_seconds=duration,
            executive_summary=parsed.get("executive_summary", ""),
            topics=parsed.get("topics", []),
            decisions=parsed.get("decisions", []),
            action_items=parsed.get("action_items", []),
            raw_markdown=raw_text,
            detail_level=detail_level,
            context=parsed.get("context", ""),
            detailed_discussions=parsed.get("detailed_discussions", []),
            risks_and_concerns=parsed.get("risks_and_concerns", []),
            next_steps=parsed.get("next_steps", []),
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
        detail_level = str(meta.get("detail_level") or getattr(config, "MEETING_DETAIL_LEVEL", "detailed")).lower()
        if detail_level in ("curto", "concise", "short", "resumido"):
            detail_level = "concise"
            system_prompt = MEETING_CONCISE_SYSTEM_PROMPT
        else:
            detail_level = "detailed"
            system_prompt = MEETING_DETAILED_SYSTEM_PROMPT

        if not transcript.strip():
            return MeetingSummary(
                title=default_title,
                date=date_str,
                duration_seconds=duration,
                executive_summary="Nenhuma fala audível foi registrada nesta sessão de reunião.",
                topics=[],
                decisions=[],
                action_items=[],
                raw_markdown="",
                detail_level=detail_level,
            )

        user_content = (
            f"Metadados da Reunião:\n"
            f"- Título Provisório: {default_title}\n"
            f"- Data: {date_str}\n"
            f"- Formato Solicitado: {'Longo / Detalhado (Multi-página)' if detail_level == 'detailed' else 'Curto / Conciso'}\n\n"
            f"Transcrição da conversa:\n\"\"\"\n{transcript.strip()}\n\"\"\"\n\n"
            f"Gere a ata estruturada em JSON conforme as regras."
        )

        url = f"{self.api_base}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
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
            with urllib.request.urlopen(req, timeout=180) as resp:
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
                raw_markdown="",
                detail_level=detail_level,
            )

        parsed = parse_summary_json(raw_text, default_title=default_title, detail_level=detail_level)
        return MeetingSummary(
            title=parsed.get("title") or default_title,
            date=date_str,
            duration_seconds=duration,
            executive_summary=parsed.get("executive_summary", ""),
            topics=parsed.get("topics", []),
            decisions=parsed.get("decisions", []),
            action_items=parsed.get("action_items", []),
            raw_markdown=raw_text,
            detail_level=detail_level,
            context=parsed.get("context", ""),
            detailed_discussions=parsed.get("detailed_discussions", []),
            risks_and_concerns=parsed.get("risks_and_concerns", []),
            next_steps=parsed.get("next_steps", []),
        )


def create_meeting_analyzer(provider: str = "local", **kwargs) -> MeetingAnalyzer:
    """Fábrica de instâncias de analisadores."""
    p = (provider or "local").lower()
    if p in ("cloud", "gemini", "openai", "groq"):
        return CloudMeetingAnalyzer(**kwargs)
    return LocalMeetingAnalyzer(**kwargs)
