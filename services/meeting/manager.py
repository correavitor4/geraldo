"""
Gerenciador central e orquestrador do ciclo de vida das reuniões.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import os
import re
import threading
import time
from typing import Dict, List, Optional, Callable

from services.meeting.models import MeetingSession, MeetingStatus, MeetingSummary, MeetingSegment
from services.meeting.recorder import MeetingAudioRecorder
from services.meeting.transcriber import create_meeting_transcriber, MeetingTranscriber
from services.meeting.analyzer import create_meeting_analyzer, MeetingAnalyzer


import unicodedata

def sanitize_filename(name: str) -> str:
    """Limpa caracteres especiais e acentos para uso seguro em nomes de arquivo."""
    # Remove acentos (ex: Reunião -> Reuniao)
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_text = "".join([c for c in nfkd if not unicodedata.combining(c)])
    s = re.sub(r"[^\w\s-]", "", ascii_text).strip().lower()
    return re.sub(r"[-\s]+", "_", s)[:50] or "reuniao"


class MeetingManager:
    """Orquestrador do ciclo de vida de reuniões e atas com processamento assíncrono."""

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        default_provider: str = "local",
        transcriber: Optional[MeetingTranscriber] = None,
        analyzer: Optional[MeetingAnalyzer] = None,
    ):
        if storage_dir is None:
            storage_dir = os.path.expanduser("~/Geraldo/reunioes")
        self.storage_dir = os.path.abspath(storage_dir)
        self.recordings_dir = os.path.join(self.storage_dir, "gravacoes")
        self.atas_dir = os.path.join(self.storage_dir, "atas")
        self.sessions_file = os.path.join(self.storage_dir, "sessions.json")

        self.default_provider = default_provider
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
        device=None,
    ) -> MeetingSession:
        """Inicia uma nova sessão de reunião e a gravação contínua."""
        with self._lock:
            if self._active_session and self._active_session.status in (MeetingStatus.RECORDING, MeetingStatus.PAUSED):
                raise RuntimeError("Já existe uma reunião em andamento.")

            session_id = f"meet_{int(time.time())}_{os.urandom(3).hex()}"
            chosen_provider = (provider or self.default_provider).lower()
            audio_path = os.path.join(self.recordings_dir, f"{session_id}.wav")

            session = MeetingSession(
                session_id=session_id,
                title=title,
                created_at=time.time(),
                status=MeetingStatus.RECORDING,
                provider=chosen_provider,
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
        """Executa a transcrição e análise da ata de forma síncrona."""
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

            # 2. Análise e Sumarização
            self._update_status(session, MeetingStatus.ANALYZING)
            analyzer = self._custom_analyzer or create_meeting_analyzer(session.provider)
            date_str = time.strftime("%d/%m/%Y %H:%M", time.localtime(session.created_at))
            summary = analyzer.analyze(
                transcript=session.full_transcript_text,
                metadata={
                    "title": session.title,
                    "date": date_str,
                    "duration_seconds": session.duration_seconds,
                }
            )
            session.summary = summary

            # 3. Geração e Salvamento do Arquivo Markdown
            slug = sanitize_filename(summary.title or session.title)
            date_prefix = time.strftime("%Y-%m-%d_%H-%M", time.localtime(session.created_at))
            md_filename = f"{date_prefix}_{slug}.md"
            md_path = os.path.join(self.atas_dir, md_filename)

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

            if session.audio_path and os.path.exists(session.audio_path):
                try:
                    os.remove(session.audio_path)
                except Exception:
                    pass

            if session.output_markdown_path and os.path.exists(session.output_markdown_path):
                try:
                    os.remove(session.output_markdown_path)
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
