"""
Ferramenta de escuta ativa e controle de reuniões para o assistente Geraldo.
"""
import os
import time
from typing import Optional, Dict, Any, List, Callable

import config
from services.meeting.manager import MeetingManager
from services.meeting.models import MeetingStatus, MeetingSession


class MeetingTools:
    """Interface estática e singleton para orquestração de reuniões pelo assistente."""

    _manager: Optional[MeetingManager] = None

    @classmethod
    def get_manager(cls) -> MeetingManager:
        if cls._manager is None:
            storage_dir = getattr(config, "MEETING_STORAGE_DIR", os.path.expanduser("~/Geraldo/reunioes"))
            provider = getattr(config, "MEETING_PROVIDER", "local")
            cls._manager = MeetingManager(storage_dir=storage_dir, default_provider=provider)
        return cls._manager

    @classmethod
    def reset_for_tests(cls, manager: Optional[MeetingManager] = None) -> None:
        """Permite injetar um MeetingManager mockado ou reiniciar o estado em testes."""
        cls._manager = manager

    @classmethod
    def start_meeting(cls, title: Optional[str] = None, provider: Optional[str] = None) -> str:
        manager = cls.get_manager()
        active = manager.active_session
        if active and active.status in (MeetingStatus.RECORDING, MeetingStatus.PAUSED):
            return "Já existe uma reunião em andamento sendo gravada."

        meeting_title = (title or "Reunião de Alinhamento").strip()
        chosen_provider = (provider or getattr(config, "MEETING_PROVIDER", "local")).lower()

        try:
            manager.start_meeting(title=meeting_title, provider=chosen_provider)
            provider_desc = "em modo local com total privacidade" if chosen_provider == "local" else "em modo nuvem com alta velocidade"
            return f"Reunião iniciada. Estou gravando a conversa {provider_desc}."
        except Exception as e:
            return f"Não foi possível iniciar a gravação da reunião: {e}"

    @classmethod
    def pause_meeting(cls) -> str:
        manager = cls.get_manager()
        if manager.pause_meeting():
            return "Gravação da reunião pausada."
        return "Não há nenhuma reunião em gravação ativa para pausar."

    @classmethod
    def resume_meeting(cls) -> str:
        manager = cls.get_manager()
        if manager.resume_meeting():
            return "Gravação da reunião retomada."
        return "Não há nenhuma reunião pausada para retomar."

    @classmethod
    def stop_meeting(cls, speak_fn: Optional[Callable[[str], None]] = None) -> str:
        manager = cls.get_manager()
        active = manager.active_session
        if not active or not manager._current_recorder:
            return "Nenhuma reunião em andamento para encerrar."

        try:
            session = manager.stop_meeting()
            dur_mins = int(session.duration_seconds // 60)
            dur_secs = int(session.duration_seconds % 60)
            dur_str = f"{dur_mins} minutos e {dur_secs} segundos" if dur_mins > 0 else f"{dur_secs} segundos"

            def _on_complete(s: MeetingSession):
                if speak_fn:
                    try:
                        speak_fn(f"A ata da reunião '{s.title}' foi gerada com sucesso e salva na sua pasta de reuniões.")
                    except Exception as e:
                        print(f"[MeetingTools:VoiceNotify Error]: {e}")

            def _on_error(s: MeetingSession, ex: Exception):
                if speak_fn:
                    try:
                        speak_fn(f"Houve um problema ao processar a ata da reunião '{s.title}'.")
                    except Exception as e:
                        print(f"[MeetingTools:VoiceNotify Error]: {e}")

            # Dispara o pós-processamento assíncrono (não bloqueante)
            manager.process_meeting_async(
                session.session_id,
                on_complete=_on_complete,
                on_error=_on_error
            )

            return f"Reunião encerrada. A gravação durou {dur_str}. Estou processando a transcrição e gerando a ata em segundo plano."
        except Exception as e:
            return f"Erro ao encerrar a reunião: {e}"

    @classmethod
    def get_meeting_status(cls) -> str:
        manager = cls.get_manager()
        active = manager.active_session
        if not active:
            return "Nenhuma reunião em andamento no momento."

        if active.status == MeetingStatus.PAUSED:
            return "A reunião atual está pausada."

        if active.status == MeetingStatus.RECORDING:
            dur = int(manager._current_recorder.elapsed_duration if manager._current_recorder else 0)
            mins = dur // 60
            secs = dur % 60
            time_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
            mode = "local" if active.provider == "local" else "nuvem"
            return f"Há uma reunião em andamento gravando há {time_str} em modo {mode}."

        return f"A reunião está no estado: {active.status.value}."

    # Métodos utilitários para IPC, TUI e GUI
    @classmethod
    def list_meetings(cls) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in cls.get_manager().list_sessions()]

    @classmethod
    def get_meeting(cls, session_id: str) -> Optional[Dict[str, Any]]:
        s = cls.get_manager().get_session(session_id)
        return s.to_dict() if s else None

    @classmethod
    def delete_meeting(cls, session_id: str) -> bool:
        return cls.get_manager().delete_session(session_id)

    @classmethod
    def register_status_callback(cls, callback: Callable[[MeetingSession], None]) -> None:
        cls.get_manager().register_status_callback(callback)

    @classmethod
    def get_live_state(cls) -> Dict[str, Any]:
        manager = cls.get_manager()
        active = manager.active_session
        if active:
            return {
                "is_active": bool(active.status in (MeetingStatus.RECORDING, MeetingStatus.PAUSED)),
                "status": active.status.value,
                "title": active.title,
                "provider": active.provider,
                "duration": active.duration_seconds,
                "rms": manager.current_rms,
            }
        # Verifica se há alguma sessão recente em pós-processamento assíncrono
        recent = manager.list_sessions()
        if recent and recent[0].status in (MeetingStatus.TRANSCRIBING, MeetingStatus.ANALYZING):
            proc = recent[0]
            return {
                "is_active": False,
                "status": proc.status.value,
                "title": proc.title,
                "provider": proc.provider,
                "duration": proc.duration_seconds,
                "rms": 0.0,
            }
        return {
            "is_active": False,
            "status": "idle",
            "title": "",
            "provider": getattr(config, "MEETING_PROVIDER", "local"),
            "duration": 0.0,
            "rms": 0.0,
        }
