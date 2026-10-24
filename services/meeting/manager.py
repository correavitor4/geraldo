"""
Gerenciador central e orquestrador do ciclo de vida das reuniões.
Compatível com Linux e Windows, com persistência completa da transcrição em texto
e suporte a níveis de detalhe configuráveis (curto vs longo) e exportação personalizada.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import os
import re
import shutil
import threading
import time
import unicodedata
from typing import Dict, List, Optional, Callable

from services.meeting.models import MeetingSession, MeetingStatus, MeetingSummary, MeetingSegment
from services.meeting.recorder import MeetingAudioRecorder
from services.meeting.transcriber import create_meeting_transcriber, MeetingTranscriber
from services.meeting.analyzer import create_meeting_analyzer, MeetingAnalyzer
import config


WINDOWS_RESERVED_NAMES = {
    "con", "prn", "aux", "nul",
    "com1", "com2", "com3", "com4", "com5", "com6", "com7", "com8", "com9",
    "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9"
}


def sanitize_filename(name: str) -> str:
    """
    Limpa caracteres especiais, acentos e caracteres proibidos no Windows e Linux.
    Garante nomes de arquivo seguros em qualquer sistema operacional.
    """
    if not name:
        return "reuniao"

    # Remove acentos e normaliza para ASCII
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_text = "".join([c for c in nfkd if not unicodedata.combining(c)])

    # Remove caracteres estritamente proibidos no Windows: < > : " / \ | ? * e controles ASCII 0-31
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", ascii_text)
    # Mantém apenas letras, números, hífens e underscores
    cleaned = re.sub(r"[^\w\s-]", "", cleaned).strip().lower()
    # Substitui espaços e hífens múltiplos por underscore
    slug = re.sub(r"[-\s]+", "_", cleaned).strip("._")[:50]

    # Protege contra nomes de dispositivos reservados do Windows (ex: CON, PRN, AUX, NUL)
    if not slug or slug.lower() in WINDOWS_RESERVED_NAMES:
        slug = f"reuniao_{slug}" if slug else "reuniao"

    return slug


class MeetingManager:
    """Orquestrador do ciclo de vida de reuniões e atas com processamento assíncrono."""

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        default_provider: str = "local",
        default_detail_level: str = "detailed",
        transcriber: Optional[MeetingTranscriber] = None,
        analyzer: Optional[MeetingAnalyzer] = None,
    ):
        if storage_dir is None:
            storage_dir = getattr(config, "MEETING_STORAGE_DIR", os.path.expanduser("~/Geraldo/reunioes"))
        self.storage_dir = os.path.normpath(os.path.abspath(os.path.expanduser(storage_dir)))
        self.recordings_dir = os.path.normpath(os.path.join(self.storage_dir, "gravacoes"))
        self.atas_dir = os.path.normpath(os.path.join(self.storage_dir, "atas"))
        self.transcricoes_dir = os.path.normpath(os.path.join(self.storage_dir, "transcricoes"))
        self.export_dir = os.path.normpath(
            os.path.abspath(os.path.expanduser(getattr(config, "MEETING_EXPORT_DIR", os.path.join(self.storage_dir, "exportadas"))))
        )
        self.sessions_file = os.path.normpath(os.path.join(self.storage_dir, "sessions.json"))

        self.default_provider = default_provider
        self.default_detail_level = default_detail_level
        self._custom_transcriber = transcriber
        self._custom_analyzer = analyzer

        self._active_session: Optional[MeetingSession] = None
        self._current_recorder: Optional[MeetingAudioRecorder] = None
        self._sessions: Dict[str, MeetingSession] = {}
        self._status_callbacks: List[Callable[[MeetingSession], None]] = []
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="MeetingWorker")

        os.makedirs(self.recordings_dir, exist_ok=True)
        os.makedirs(self.atas_dir, exist_ok=True)
        os.makedirs(self.transcricoes_dir, exist_ok=True)
        os.makedirs(self.export_dir, exist_ok=True)
        self._load_sessions()

    def register_status_callback(self, callback: Callable[[MeetingSession], None]) -> None:
        with self._lock:
            if callback not in self._status_callbacks:
                self._status_callbacks.append(callback)

    def _notify_status_change(self, session: MeetingSession) -> None:
        with self._lock:
            callbacks = list(self._status_callbacks)
        for cb in callbacks:
            try:
                cb(session)
            except Exception as e:
                print(f"[MeetingManager:Callback Error]: {e}")

    @property
    def active_session(self) -> Optional[MeetingSession]:
        with self._lock:
            return self._active_session

    @property
    def current_rms(self) -> float:
        with self._lock:
            if self._current_recorder:
                return self._current_recorder.current_rms
            return 0.0

    def start_meeting(
        self,
        title: str = "Reunião de Alinhamento",
        provider: Optional[str] = None,
        detail_level: Optional[str] = None,
        device=None,
    ) -> MeetingSession:
        """Inicia uma nova sessão de reunião e a gravação contínua."""
        with self._lock:
            if self._active_session and self._active_session.status in (MeetingStatus.RECORDING, MeetingStatus.PAUSED):
                raise RuntimeError("Já existe uma reunião em andamento.")

            session_id = f"meet_{int(time.time())}_{os.urandom(3).hex()}"
            chosen_provider = (provider or self.default_provider).lower()
            chosen_detail = (detail_level or getattr(config, "MEETING_DETAIL_LEVEL", self.default_detail_level)).lower()
            if chosen_detail in ("curto", "concise", "short", "resumido"):
                chosen_detail = "concise"
            else:
                chosen_detail = "detailed"

            audio_path = os.path.normpath(os.path.join(self.recordings_dir, f"{session_id}.wav"))

            session = MeetingSession(
                session_id=session_id,
                title=title,
                created_at=time.time(),
                status=MeetingStatus.RECORDING,
                provider=chosen_provider,
                detail_level=chosen_detail,
                audio_path=audio_path,
            )

            self._current_recorder = MeetingAudioRecorder(output_path=audio_path, device=device)
            self._current_recorder.start()

            self._active_session = session
            self._sessions[session_id] = session
            self._save_sessions()
        self._notify_status_change(session)
        return session

    def pause_meeting(self) -> bool:
        """Pausa a gravação da reunião ativa."""
        with self._lock:
            if self._active_session and self._current_recorder and self._active_session.status == MeetingStatus.RECORDING:
                self._current_recorder.pause()
                self._active_session.status = MeetingStatus.PAUSED
                self._active_session.duration_seconds = self._current_recorder.elapsed_duration
                self._save_sessions()
                session = self._active_session
            else:
                session = None
        if session:
            self._notify_status_change(session)
            return True
        return False

    def resume_meeting(self) -> bool:
        """Retoma a gravação da reunião pausada."""
        with self._lock:
            if self._active_session and self._current_recorder and self._active_session.status == MeetingStatus.PAUSED:
                self._current_recorder.resume()
                self._active_session.status = MeetingStatus.RECORDING
                self._save_sessions()
                session = self._active_session
            else:
                session = None
        if session:
            self._notify_status_change(session)
            return True
        return False

    def stop_meeting(self) -> MeetingSession:
        """Finaliza a gravação da reunião ativa e a deixa pronta para processamento."""
        with self._lock:
            if not self._active_session or not self._current_recorder:
                raise RuntimeError("Nenhuma reunião ativa para encerrar.")

            duration = self._current_recorder.stop()
            self._active_session.duration_seconds = duration
            self._active_session.status = MeetingStatus.STOPPED
            session = self._active_session

            self._active_session = None
            self._current_recorder = None
            self._save_sessions()
        self._notify_status_change(session)
        return session

    def process_meeting_sync(self, session_id: str) -> MeetingSession:
        """Executa a transcrição, persistência em texto bruto e análise da ata de forma síncrona."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise KeyError(f"Sessão {session_id} não encontrada.")
            if session.status in (MeetingStatus.TRANSCRIBING, MeetingStatus.ANALYZING):
                raise RuntimeError("A sessão já está em processamento.")

        try:
            # 1. Transcrição
            self._update_status(session, MeetingStatus.TRANSCRIBING)
            transcriber = self._custom_transcriber or create_meeting_transcriber(session.provider)
            if session.audio_path and os.path.exists(session.audio_path):
                segments = transcriber.transcribe(session.audio_path)
            else:
                segments = []
            session.transcript_segments = segments

            date_str = time.strftime("%d/%m/%Y %H:%M", time.localtime(session.created_at))
            date_prefix = time.strftime("%Y-%m-%d_%H-%M", time.localtime(session.created_at))
            slug = sanitize_filename(session.title)

            # 2. Persistência Integral da Transcrição Bruta em Arquivo (.txt)
            txt_filename = f"{date_prefix}_{slug}_transcricao.txt"
            txt_path = os.path.normpath(os.path.join(self.transcricoes_dir, txt_filename))

            dur_mins = int(session.duration_seconds // 60)
            dur_secs = int(session.duration_seconds % 60)
            dur_formatted = f"{dur_mins}m {dur_secs}s" if dur_mins > 0 else f"{dur_secs}s"

            txt_lines = [
                "=" * 80,
                "GERALDO - TRANSCRIÇÃO INTEGRAL DE REUNIÃO",
                f"Título: {session.title}",
                f"Data: {date_str}",
                f"Duração Total: {dur_formatted} ({session.duration_seconds:.2f}s)",
                f"Modo de Processamento: {session.provider.upper()}",
                f"Formato da Ata: {session.detail_level.upper()}",
                "=" * 80,
                "",
                "REGISTRO CRONOLÓGICO DE FALAS:",
                ""
            ]

            if session.transcript_segments:
                for seg in session.transcript_segments:
                    speaker_tag = f"[{seg.speaker}] " if seg.speaker else ""
                    txt_lines.append(f"[{seg.formatted_start} - {seg.formatted_end}] {speaker_tag}{seg.text}")
            else:
                txt_lines.append("(Nenhum segmento de fala capturado ou áudio inaudível)")

            txt_lines.append("")
            txt_lines.append("=" * 80)
            txt_lines.append("Fim da transcrição.")

            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(txt_lines))

            session.transcript_path = txt_path

            # 3. Análise e Sumarização da Ata
            self._update_status(session, MeetingStatus.ANALYZING)
            analyzer = self._custom_analyzer or create_meeting_analyzer(session.provider)
            summary = analyzer.analyze(
                transcript=session.full_transcript_text,
                metadata={
                    "title": session.title,
                    "date": date_str,
                    "duration_seconds": session.duration_seconds,
                    "detail_level": session.detail_level,
                }
            )
            session.summary = summary

            # 4. Geração e Salvamento do Arquivo Markdown (.md)
            final_slug = sanitize_filename(summary.title or session.title)
            md_filename = f"{date_prefix}_{final_slug}.md"
            md_path = os.path.normpath(os.path.join(self.atas_dir, md_filename))

            md_content = summary.to_markdown(segments=session.transcript_segments)
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_content)

            session.output_markdown_path = md_path
            self._update_status(session, MeetingStatus.COMPLETED)
            return session

        except Exception as e:
            session.error_message = str(e)
            self._update_status(session, MeetingStatus.FAILED)
            raise e

    def process_meeting_async(
        self,
        session_id: str,
        on_complete: Optional[Callable[[MeetingSession], None]] = None,
        on_error: Optional[Callable[[MeetingSession, Exception], None]] = None,
    ):
        """Dispara o pós-processamento da ata em background via thread pool (não bloqueante)."""
        def _worker():
            try:
                res = self.process_meeting_sync(session_id)
                if on_complete:
                    on_complete(res)
            except Exception as ex:
                session = self.get_session(session_id)
                if on_error and session:
                    on_error(session, ex)

        return self._executor.submit(_worker)

    def export_meeting(
        self,
        session_id: str,
        target_dir_or_file: Optional[str] = None,
        format_type: str = "both",
    ) -> Dict[str, str]:
        """
        Exporta a ata (.md) e/ou a transcrição (.txt) para um destino escolhido pelo usuário.
        Funciona transparentemente tanto no Linux quanto no Windows.
        """
        with self._lock:
            session = self.get_session(session_id)
            if not session:
                raise KeyError(f"Sessão {session_id} não encontrada.")

        result: Dict[str, str] = {}
        dest_raw = target_dir_or_file or self.export_dir
        dest = os.path.normpath(os.path.abspath(os.path.expanduser(dest_raw)))

        slug = sanitize_filename(session.title)
        date_prefix = time.strftime("%Y-%m-%d_%H-%M", time.localtime(session.created_at))

        # Determina se o destino é um arquivo específico ou um diretório
        is_file_target = dest.lower().endswith(".md") or dest.lower().endswith(".txt")
        if is_file_target:
            parent_dir = os.path.dirname(dest)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            if dest.lower().endswith(".md"):
                if session.output_markdown_path and os.path.exists(session.output_markdown_path):
                    shutil.copy2(session.output_markdown_path, dest)
                    result["markdown_path"] = dest
                elif session.summary:
                    with open(dest, "w", encoding="utf-8") as f:
                        f.write(session.summary.to_markdown(session.transcript_segments))
                    result["markdown_path"] = dest
            elif dest.lower().endswith(".txt"):
                if session.transcript_path and os.path.exists(session.transcript_path):
                    shutil.copy2(session.transcript_path, dest)
                    result["transcript_path"] = dest
            return result

        # Caso seja diretório:
        os.makedirs(dest, exist_ok=True)
        if format_type in ("md", "markdown", "both"):
            md_dest = os.path.normpath(os.path.join(dest, f"{date_prefix}_{slug}_ata.md"))
            if session.output_markdown_path and os.path.exists(session.output_markdown_path):
                shutil.copy2(session.output_markdown_path, md_dest)
            elif session.summary:
                with open(md_dest, "w", encoding="utf-8") as f:
                    f.write(session.summary.to_markdown(session.transcript_segments))
            result["markdown_path"] = md_dest

        if format_type in ("txt", "transcription", "both"):
            txt_dest = os.path.normpath(os.path.join(dest, f"{date_prefix}_{slug}_transcricao.txt"))
            if session.transcript_path and os.path.exists(session.transcript_path):
                shutil.copy2(session.transcript_path, txt_dest)
            result["transcript_path"] = txt_dest

        return result

    def list_sessions(self) -> List[MeetingSession]:
        """Retorna todas as reuniões registradas ordenadas pela mais recente."""
        with self._lock:
            return sorted(list(self._sessions.values()), key=lambda s: s.created_at, reverse=True)

    def get_session(self, session_id: str) -> Optional[MeetingSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """Remove a sessão do histórico e apaga os arquivos associados."""
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if not session:
                return False

            for path in (session.audio_path, session.output_markdown_path, session.transcript_path):
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass

            self._save_sessions()
            return True

    def _update_status(self, session: MeetingSession, status: MeetingStatus) -> None:
        with self._lock:
            session.status = status
            self._save_sessions()
        self._notify_status_change(session)

    def _save_sessions(self) -> None:
        with self._lock:
            try:
                data = {sid: s.to_dict() for sid, s in self._sessions.items()}
                with open(self.sessions_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[MeetingManager] Erro ao persistir sessões: {e}")

    def _load_sessions(self) -> None:
        with self._lock:
            if not os.path.exists(self.sessions_file):
                return
            try:
                with open(self.sessions_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._sessions = {sid: MeetingSession.from_dict(val) for sid, val in data.items()}
            except Exception as e:
                print(f"[MeetingManager] Erro ao carregar sessões anteriores: {e}")
