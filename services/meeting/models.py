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

    def to_markdown(self, segments: Optional[List[MeetingSegment]] = None) -> str:
        """Gera o documento final da ata em formato Markdown elegante."""
        dur_mins = int(self.duration_seconds // 60)
        dur_secs = int(self.duration_seconds % 60)
        dur_str = f"{dur_mins}m {dur_secs}s" if dur_mins > 0 else f"{dur_secs}s"

        lines = [
            f"# 📋 Ata de Reunião: {self.title}",
            "",
            f"- **Data:** {self.date}",
            f"- **Duração:** {dur_str}",
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

        if segments:
            lines.extend([
                "",
                "---",
                "",
                "## 📝 Transcrição Bruta Completa",
                "",
                "<details>",
                "<summary>Clique para expandir o registro cronológico completo</summary>",
                ""
            ])
            for seg in segments:
                prefix = f"**{seg.speaker}**: " if seg.speaker else ""
                lines.append(f"- `{seg.formatted_start}` {prefix}{seg.text}")
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
        )


@dataclass
class MeetingSession:
    session_id: str
    title: str = "Reunião sem título"
    created_at: float = field(default_factory=time.time)
    duration_seconds: float = 0.0
    status: MeetingStatus = MeetingStatus.IDLE
    provider: str = "local"  # "local" ou "cloud"
    audio_path: Optional[str] = None
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
            "audio_path": self.audio_path,
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
            audio_path=data.get("audio_path"),
            transcript_segments=segments,
            summary=summary,
            error_message=data.get("error_message"),
            output_markdown_path=data.get("output_markdown_path"),
        )
