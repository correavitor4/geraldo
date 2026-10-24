"""
Testes unitários da Fase 2 para escuta ativa e atas de reunião (Config, Tools, NLU, LLM e IPC).
"""
import os
import json
import time
import pytest
from unittest.mock import MagicMock, patch

import config
from tools.meeting import MeetingTools
from services.meeting.manager import MeetingManager
from services.meeting.models import MeetingStatus, MeetingSession, MeetingSummary, MeetingSegment
from brain.nlu import IntentEngine
from brain.llm import BrainLLM
from core.ipc import GeraldoIPCServer


@pytest.fixture
def isolated_meeting_manager(tmp_path):
    storage_dir = str(tmp_path / "meetings")
    mock_transcriber = MagicMock()
    mock_transcriber.transcribe.return_value = [MeetingSegment(start=0.0, end=3.0, text="Teste reunião")]

    mock_analyzer = MagicMock()
    mock_analyzer.analyze.return_value = MeetingSummary(
        title="Reunião Teste",
        date="24/10/2026",
        duration_seconds=3.0,
        executive_summary="Resumo de teste da reunião."
    )

    manager = MeetingManager(
        storage_dir=storage_dir,
        default_provider="local",
        transcriber=mock_transcriber,
        analyzer=mock_analyzer,
    )
    MeetingTools.reset_for_tests(manager)
    yield manager
    MeetingTools.reset_for_tests(None)


# ==============================================================================
# 1. Testes de Configuração (config.py)
# ==============================================================================

def test_meeting_config_get_and_update():
    cfg = config.get_meeting_config()
    assert "provider" in cfg
    assert "storage_dir" in cfg
    assert "supported_providers" in cfg
    assert "local" in cfg["supported_providers"]
    assert "cloud" in cfg["supported_providers"]

    updated = config.update_meeting_config(provider="cloud", persist=False)
    assert updated["provider"] == "cloud"

    updated2 = config.update_meeting_config(provider="local", persist=False)
    assert updated2["provider"] == "local"


# ==============================================================================
# 2. Testes de Ferramentas (tools/meeting.py)
# ==============================================================================

def test_meeting_tools_lifecycle(isolated_meeting_manager):
    # Início da reunião
    resp_start = MeetingTools.start_meeting(title="Alinhamento com Cliente")
    assert "Reunião iniciada" in resp_start
    assert "local" in resp_start

    state = MeetingTools.get_live_state()
    assert state["is_active"] is True
    assert state["status"] == "recording"
    assert state["title"] == "Alinhamento com Cliente"

    # Status
    status_msg = MeetingTools.get_meeting_status()
    assert "Há uma reunião em andamento" in status_msg

    # Pausa
    resp_pause = MeetingTools.pause_meeting()
    assert "pausada" in resp_pause

    status_paused = MeetingTools.get_meeting_status()
    assert "pausada" in status_paused

    # Retomada
    resp_resume = MeetingTools.resume_meeting()
    assert "retomada" in resp_resume

    # Encerramento e Notificação de Voz
    spoken_messages = []
    def mock_speaker(msg):
        spoken_messages.append(msg)

    resp_stop = MeetingTools.stop_meeting(speak_fn=mock_speaker)
    assert "Reunião encerrada" in resp_stop
    assert "processando a transcrição" in resp_stop

    # Espera a conclusão do job assíncrono em background
    t0 = time.time()
    while not spoken_messages and (time.time() - t0 < 5.0):
        time.sleep(0.05)

    assert len(spoken_messages) == 1
    assert "foi gerada com sucesso" in spoken_messages[0]

    # Listagem e Exclusão
    meetings = MeetingTools.list_meetings()
    assert len(meetings) == 1
    sid = meetings[0]["session_id"]

    fetched = MeetingTools.get_meeting(sid)
    assert fetched is not None
    assert fetched["session_id"] == sid

    assert MeetingTools.delete_meeting(sid) is True
    assert len(MeetingTools.list_meetings()) == 0


# ==============================================================================
# 3. Testes de NLU (brain/nlu.py)
# ==============================================================================

def test_nlu_meeting_intents(shared_nlu_engine):
    # Comandos de início
    intent, conf, slots = shared_nlu_engine.predict("iniciar reunião")
    assert intent == "meeting_control"
    assert slots["action"] == "start"

    intent, conf, slots = shared_nlu_engine.predict("iniciar reunião chamada Planejamento Estratégico")
    assert intent == "meeting_control"
    assert slots["action"] == "start"
    assert slots["title"] == "Planejamento Estratégico"

    intent, conf, slots = shared_nlu_engine.predict("começar ata de reunião")
    assert intent == "meeting_control"
    assert slots["action"] == "start"

    # Pausa e retomada
    intent, conf, slots = shared_nlu_engine.predict("pause a reunião")
    assert intent == "meeting_control"
    assert slots["action"] == "pause"

    intent, conf, slots = shared_nlu_engine.predict("retomar reunião")
    assert intent == "meeting_control"
    assert slots["action"] == "resume"

    # Encerramento
    intent, conf, slots = shared_nlu_engine.predict("encerrar reunião e gerar ata")
    assert intent == "meeting_control"
    assert slots["action"] == "stop"

    intent, conf, slots = shared_nlu_engine.predict("finalizar reunião")
    assert intent == "meeting_control"
    assert slots["action"] == "stop"

    # Status
    intent, conf, slots = shared_nlu_engine.predict("status da reunião")
    assert intent == "meeting_control"
    assert slots["action"] == "status"


# ==============================================================================
# 4. Testes de Roteamento no BrainLLM (brain/llm.py)
# ==============================================================================

def test_llm_dispatch_meeting_control(isolated_meeting_manager):
    speaker_mock = MagicMock()
    llm = BrainLLM(speak_fn=speaker_mock.speak)

    # Iniciar
    res_start = llm._dispatch_intent("meeting_control", {"action": "start", "title": "Review Semanal"}, "iniciar reunião")
    assert "Reunião iniciada" in res_start

    # Status
    res_status = llm._dispatch_intent("meeting_control", {"action": "status"}, "status da reunião")
    assert "em andamento" in res_status

    # Pausar
    res_pause = llm._dispatch_intent("meeting_control", {"action": "pause"}, "pausar reunião")
    assert "pausada" in res_pause

    # Retomar
    res_resume = llm._dispatch_intent("meeting_control", {"action": "resume"}, "retomar reunião")
    assert "retomada" in res_resume

    # Encerrar
    res_stop = llm._dispatch_intent("meeting_control", {"action": "stop"}, "encerrar reunião")
    assert "Reunião encerrada" in res_stop


# ==============================================================================
# 5. Testes de IPC Server (core/ipc.py)
# ==============================================================================

def test_ipc_meeting_handlers(isolated_meeting_manager):
    server = GeraldoIPCServer(host="127.0.0.1", port=0)

    # get_state com meeting incluído
    state = server._handle_get_state({})
    assert "meeting" in state
    assert state["meeting"]["is_active"] is False

    # meeting_start
    res_start = server._handle_meeting_start({"title": "Sync IPC"})
    assert "Reunião iniciada" in res_start["message"]
    assert res_start["state"]["is_active"] is True

    # meeting_status
    res_status = server._handle_meeting_status({})
    assert "speech" in res_status
    assert res_status["state"]["is_active"] is True

    # meeting_pause e resume
    res_pause = server._handle_meeting_pause({})
    assert "pausada" in res_pause["message"]

    res_resume = server._handle_meeting_resume({})
    assert "retomada" in res_resume["message"]

    # meeting_stop
    res_stop = server._handle_meeting_stop({})
    assert "Reunião encerrada" in res_stop["message"]

    # meeting_list
    res_list = server._handle_meeting_list({})
    assert len(res_list["meetings"]) == 1
    sid = res_list["meetings"][0]["session_id"]

    # meeting_get
    res_get = server._handle_meeting_get({"session_id": sid})
    assert res_get["meeting"]["session_id"] == sid

    # get e set config
    cfg = server._handle_get_meeting_config({})
    assert "provider" in cfg

    updated_cfg = server._handle_set_meeting_config({"provider": "cloud"})
    assert updated_cfg["provider"] == "cloud"

    # meeting_delete
    res_del = server._handle_meeting_delete({"session_id": sid})
    assert res_del["deleted"] is True
