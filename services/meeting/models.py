"""
Modelos de dados e contratos para o módulo de atas e escuta ativa de reuniões.
"""
from dataclasses import dataclass, field
from enum import Enum
import json
import time
from typing import List, Dict, Any, Optional


class MeetingStatus(str, Enum):
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    STOPPED = "stopped"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class MeetingSegment:
    start: float
    end: float
    text: str
    speaker: Optional[str] = None

    @property
    def formatted_start(self) -> str:
        mins = int(self.start // 60)
        secs = int(self.start % 60)
        return f"{mins:02d}:{secs:02d}"

    @property
    def formatted_end(self) -> str:
        mins = int(self.end // 60)
        secs = int(self.end % 60)
        return f"{mins:02d}:{secs:02d}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start": round(self.start, 2),
            "end": round(self.end, 2),
            "text": self.text,
            "speaker": self.speaker,
            "timestamp": f"[{self.formatted_start} - {self.formatted_end}]"
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MeetingSegment":
        return cls(
            start=float(data.get("start", 0.0)),
            end=float(data.get("end", 0.0)),
            text=str(data.get("text", "")),
            speaker=data.get("speaker")
        )


@dataclass
class MeetingSummary:
    title: str
    date: str
    duration_seconds: float
    executive_summary: str
    topics: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    action_items: List[Dict[str, str]] = field(default_factory=list)
    raw_markdown: str = ""
    detail_level: str = "detailed"
    context: str = ""
    detailed_discussions: List[Dict[str, Any]] = field(default_factory=list)
    risks_and_concerns: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)

    def to_markdown(self, segments: Optional[List[MeetingSegment]] = None) -> str:
        """Gera o documento da ata em formato Markdown, adaptado para modo Curto ou Detalhado (multi-página)."""
        dur_mins = int(self.duration_seconds // 60)
        dur_secs = int(self.duration_seconds % 60)
        dur_str = f"{dur_mins}m {dur_secs}s" if dur_mins > 0 else f"{dur_secs}s"
        is_detailed = self.detail_level == "detailed" or bool(self.detailed_discussions or self.context)

        if not is_detailed:
            # Modo Curto / Executivo
            lines = [
                f"# 📋 Ata de Reunião: {self.title}",
                "",
                f"- **Data:** {self.date}",
                f"- **Duração:** {dur_str}",
                f"- **Formato:** Síntese Executiva Concisa",
                "",
                "---",
                "",
                "## 📌 Resumo Executivo",
                "",
                self.executive_summary.strip() or "Nenhum resumo gerado.",
                "",
                "## 💬 Principais Tópicos Abordados",
                ""
            ]

            if self.topics:
                for top in self.topics:
                    lines.append(f"- {top}")
            else:
                lines.append("- Nenhum tópico específico identificado.")

            lines.extend([
                "",
                "## ✅ Decisões Tomadas",
                ""
            ])

            if self.decisions:
                for dec in self.decisions:
                    lines.append(f"- {dec}")
            else:
                lines.append("- Nenhuma decisão definitiva registrada.")

            lines.extend([
                "",
                "## 📋 Tarefas e Próximos Passos (Action Items)",
                ""
            ])

            if self.action_items:
                lines.append("| Tarefa | Responsável | Prazo |")
                lines.append("| :--- | :--- | :--- |")
                for item in self.action_items:
                    task = item.get("task", "-")
                    owner = item.get("owner", "Não definido")
                    deadline = item.get("deadline", "A definir")
                    lines.append(f"| {task} | {owner} | {deadline} |")
            else:
                lines.append("- Nenhuma ação pendente identificada.")

        else:
            # Modo Longo / Detalhado (Multi-página Completo e Exaustivo)
            lines = [
                f"# 📋 Ata de Reunião: {self.title}",
                "",
                f"- **Data:** {self.date}",
                f"- **Duração:** {dur_str}",
                f"- **Formato:** Detalhada e Completa (Multi-página)",
                "",
                "> **Documento Oficial de Registro de Deliberações e Acordos (Ata Detalhada / Multi-página)**",
                "",
                "| Atributo | Detalhe |",
                "| :--- | :--- |",
                f"| **Título Oficial** | {self.title} |",
                f"| **Data e Hora** | {self.date} |",
                f"| **Duração Registrada** | {dur_str} |",
                f"| **Extensão / Nível de Detalhe** | Completo / Exaustivo (Multi-página) |",
                "",
                "---",
                "",
                "## 🎯 1. Contexto, Motivação e Objetivos da Sessão",
                "",
                (self.context.strip() or self.executive_summary.strip() or "Sessão dedicada ao alinhamento estratégico, deliberação de pautas e acompanhamento de projetos."),
                "",
                "---",
                "",
                "## 📌 Resumo Executivo",
                "",
                self.executive_summary.strip() or "Nenhum resumo executivo gerado.",
                "",
                "---",
                "",
                "## 💬 3. Discussão Minuciosa por Tópicos",
                ""
            ]

            if self.detailed_discussions:
                for idx, disc in enumerate(self.detailed_discussions, start=1):
                    topic_title = disc.get("topic") or f"Tópico {idx}"
                    details = disc.get("details", "")
                    arguments = disc.get("arguments", "")
                    conclusions = disc.get("conclusions", "")

                    lines.append(f"### 3.{idx}. {topic_title}")
                    lines.append("")
                    if details:
                        lines.append(f"**Panorama e Debate:**\n{details}\n")
                    if arguments:
                        lines.append(f"**Pontos de Vista e Argumentos Apresentados:**\n{arguments}\n")
                    if conclusions:
                        lines.append(f"**Encaminhamento do Tópico:**\n{conclusions}\n")
                    lines.append("")
            elif self.topics:
                for top in self.topics:
                    lines.append(f"- {top}")
                lines.append("")
            else:
                lines.append("- Não foram identificadas seções temáticas isoladas.")
                lines.append("")

            lines.extend([
                "---",
                "",
                "## ✅ 4. Decisões Tomadas e Deliberações",
                ""
            ])

            if self.decisions:
                for dec in self.decisions:
                    lines.append(f"- {dec}")
            else:
                lines.append("- Nenhuma deliberação formal registrada durante o diálogo.")

            lines.extend([
                "",
                "---",
                "",
                "## ⚠️ 5. Riscos, Gargalos e Pontos de Atenção",
                ""
            ])

            if self.risks_and_concerns:
                for risk in self.risks_and_concerns:
                    lines.append(f"- ⚠️ **Alerta:** {risk}")
            else:
                lines.append("- Nenhum risco crítico ou impeditivo imediato foi apontado.")

            lines.extend([
                "",
                "---",
                "",
                "## 📋 6. Tarefas e Próximos Passos (Action Items)",
                ""
            ])

            if self.action_items:
                lines.append("| Tarefa | Responsável | Prazo |")
                lines.append("| :--- | :--- | :--- |")
                for item in self.action_items:
                    task = item.get("task", "-")
                    owner = item.get("owner", "Não definido")
                    deadline = item.get("deadline", "A definir")
                    lines.append(f"| {task} | {owner} | {deadline} |")
            else:
                lines.append("- Nenhuma tarefa ou ação operacional pendente identificada.")

            lines.extend([
                "",
                "---",
                "",
                "## 🚀 7. Próximos Passos e Encaminhamentos",
                ""
            ])

            if self.next_steps:
                for step in self.next_steps:
                    lines.append(f"- ➔ {step}")
            else:
                lines.append("- Manter acompanhamento ordinário das atividades conforme cronograma.")

        # Transcrição integral ao final (em ambos os modos)
        if segments:
            lines.extend([
                "",
                "---",
                "",
                "## 📝 Transcrição Bruta Completa",
                "",
                "> A transcrição bruta foi persistida e pode ser consultada na íntegra.",
                "",
                "<details>",
                "<summary>🔍 Clique para expandir todo o fluxo cronológico com minutagem</summary>",
                ""
            ])
            for seg in segments:
                prefix = f"**{seg.speaker}**: " if seg.speaker else ""
                lines.append(f"- `[{seg.formatted_start} - {seg.formatted_end}]` {prefix}{seg.text}")
            lines.extend([
                "",
                "</details>",
                ""
            ])

        lines.append("")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "date": self.date,
            "duration_seconds": round(self.duration_seconds, 2),
            "executive_summary": self.executive_summary,
            "topics": self.topics,
            "decisions": self.decisions,
            "action_items": self.action_items,
            "raw_markdown": self.raw_markdown,
            "detail_level": self.detail_level,
            "context": self.context,
            "detailed_discussions": self.detailed_discussions,
            "risks_and_concerns": self.risks_and_concerns,
            "next_steps": self.next_steps,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MeetingSummary":
        return cls(
            title=data.get("title", "Reunião"),
            date=data.get("date", ""),
            duration_seconds=float(data.get("duration_seconds", 0.0)),
            executive_summary=data.get("executive_summary", ""),
            topics=data.get("topics", []),
            decisions=data.get("decisions", []),
            action_items=data.get("action_items", []),
            raw_markdown=data.get("raw_markdown", ""),
            detail_level=data.get("detail_level", "detailed"),
            context=data.get("context", ""),
            detailed_discussions=data.get("detailed_discussions", []),
            risks_and_concerns=data.get("risks_and_concerns", []),
            next_steps=data.get("next_steps", []),
        )


@dataclass
class MeetingSession:
    session_id: str
    title: str = "Reunião sem título"
    created_at: float = field(default_factory=time.time)
    duration_seconds: float = 0.0
    status: MeetingStatus = MeetingStatus.IDLE
    provider: str = "local"  # "local" ou "cloud"
    detail_level: str = "detailed"  # "detailed" ou "concise"
    audio_path: Optional[str] = None
    transcript_path: Optional[str] = None
    transcript_segments: List[MeetingSegment] = field(default_factory=list)
    summary: Optional[MeetingSummary] = None
    error_message: Optional[str] = None
    output_markdown_path: Optional[str] = None

    @property
    def full_transcript_text(self) -> str:
        return " ".join([seg.text.strip() for seg in self.transcript_segments if seg.text.strip()])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "title": self.title,
            "created_at": self.created_at,
            "duration_seconds": round(self.duration_seconds, 2),
            "status": self.status.value,
            "provider": self.provider,
            "detail_level": self.detail_level,
            "audio_path": self.audio_path,
            "transcript_path": self.transcript_path,
            "transcript_segments": [s.to_dict() for s in self.transcript_segments],
            "summary": self.summary.to_dict() if self.summary else None,
            "error_message": self.error_message,
            "output_markdown_path": self.output_markdown_path,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MeetingSession":
        segments = [MeetingSegment.from_dict(s) for s in data.get("transcript_segments", [])]
        summary = MeetingSummary.from_dict(data["summary"]) if data.get("summary") else None
        status = MeetingStatus(data.get("status", MeetingStatus.IDLE.value))
        return cls(
            session_id=data["session_id"],
            title=data.get("title", "Reunião sem título"),
            created_at=float(data.get("created_at", time.time())),
            duration_seconds=float(data.get("duration_seconds", 0.0)),
            status=status,
            provider=data.get("provider", "local"),
            detail_level=data.get("detail_level", "detailed"),
            audio_path=data.get("audio_path"),
            transcript_path=data.get("transcript_path"),
            transcript_segments=segments,
            summary=summary,
            error_message=data.get("error_message"),
            output_markdown_path=data.get("output_markdown_path"),
        )
