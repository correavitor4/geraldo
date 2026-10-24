"""
Testes unitários para o módulo de escuta ativa e atas de reuniões (services.meeting).
"""
import io
import json
import os
import wave
import pytest
from unittest.mock import MagicMock, patch

from services.meeting.models import (
    MeetingStatus,
    MeetingSegment,
    MeetingSummary,
    MeetingSession,
)
from services.meeting.recorder import MeetingAudioRecorder
from services.meeting.transcriber import (
    LocalMeetingTranscriber,
    CloudMeetingTranscriber,
    create_meeting_transcriber,
)
from services.meeting.analyzer import (
    LocalMeetingAnalyzer,
    CloudMeetingAnalyzer,
    create_meeting_analyzer,
    parse_summary_json,
)
from services.meeting.manager import MeetingManager, sanitize_filename


# ==============================================================================
# 1. Testes de Modelos (models.py)
# ==============================================================================

def test_meeting_segment_formatting_and_dict():
    seg = MeetingSegment(start=65.5, end=130.0, text="Olá mundo", speaker="Cliente")
    assert seg.formatted_start == "01:05"
    assert seg.formatted_end == "02:10"

    d = seg.to_dict()
    assert d["start"] == 65.5
    assert d["end"] == 130.0
    assert d["text"] == "Olá mundo"
    assert d["speaker"] == "Cliente"
    assert d["timestamp"] == "[01:05 - 02:10]"

    restored = MeetingSegment.from_dict(d)
    assert restored.start == seg.start
    assert restored.end == seg.end
    assert restored.text == seg.text
    assert restored.speaker == seg.speaker


def test_meeting_summary_markdown_generation():
    summary = MeetingSummary(
        title="Alinhamento Estratégico",
        date="24/10/2026 14:00",
        duration_seconds=125.0,
        executive_summary="Alinhamos os prazos do projeto e entregas da sprint.",
        topics=["Prazos", "Design System"],
        decisions=["Aprovar layout até sexta-feira"],
        action_items=[
            {"task": "Criar protótipo no Figma", "owner": "Vitor", "deadline": "Sexta 18h"}
        ]
    )

    segments = [
        MeetingSegment(start=0.0, end=10.0, text="Bom dia a todos.", speaker="Vitor"),
        MeetingSegment(start=10.5, end=25.0, text="Vamos revisar o design.", speaker="Cliente")
    ]

    md = summary.to_markdown(segments=segments)
    assert "# 📋 Ata de Reunião: Alinhamento Estratégico" in md
    assert "**Duração:** 2m 5s" in md
    assert "## 📌 Resumo Executivo" in md
    assert "Alinhamos os prazos do projeto" in md
    assert "- Prazos" in md
    assert "- Aprovar layout até sexta-feira" in md
    assert "| Criar protótipo no Figma | Vitor | Sexta 18h |" in md
    assert "## 📝 Transcrição Bruta Completa" in md
    assert "**Vitor**: Bom dia a todos." in md


def test_meeting_session_serialization():
    session = MeetingSession(
        session_id="meet_123",
        title="Teste Session",
        duration_seconds=60.0,
        status=MeetingStatus.COMPLETED,
        provider="local",
        transcript_segments=[MeetingSegment(start=0.0, end=5.0, text="Fala teste")]
    )
    assert session.full_transcript_text == "Fala teste"

    d = session.to_dict()
    assert d["session_id"] == "meet_123"
    assert d["status"] == "completed"

    restored = MeetingSession.from_dict(d)
    assert restored.session_id == "meet_123"
    assert restored.status == MeetingStatus.COMPLETED
    assert len(restored.transcript_segments) == 1
    assert restored.transcript_segments[0].text == "Fala teste"


# ==============================================================================
# 2. Testes do Gravador de Áudio (recorder.py)
# ==============================================================================

def test_meeting_recorder_lifecycle(tmp_path):
    wav_path = str(tmp_path / "test_recording.wav")
    recorder = MeetingAudioRecorder(output_path=wav_path, sample_rate=16000)

    assert recorder.status == MeetingStatus.IDLE
    assert recorder.elapsed_duration == 0.0

    recorder.start()
    assert recorder.status == MeetingStatus.RECORDING

    recorder.pause()
    assert recorder.status == MeetingStatus.PAUSED

    recorder.resume()
    assert recorder.status == MeetingStatus.RECORDING

    duration = recorder.stop()
    assert recorder.status == MeetingStatus.STOPPED
    assert duration >= 0.0
    assert os.path.exists(wav_path)

    # Verifica se gerou um cabeçalho de WAV válido
    with wave.open(wav_path, "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 16000


# ==============================================================================
# 3. Testes do Transcritor (transcriber.py)
# ==============================================================================

def test_create_meeting_transcriber():
    local_t = create_meeting_transcriber("local")
    assert isinstance(local_t, LocalMeetingTranscriber)

    cloud_t = create_meeting_transcriber("cloud")
    assert isinstance(cloud_t, CloudMeetingTranscriber)


def test_local_transcriber_with_mock_whisper(tmp_path):
    wav_path = str(tmp_path / "dummy.wav")
    with open(wav_path, "wb") as f:
        f.write(b"RIFFdummydata")

    transcriber = LocalMeetingTranscriber(model_size="tiny")

    mock_seg = MagicMock()
    mock_seg.start = 1.0
    mock_seg.end = 4.0
    mock_seg.text = " Transcrição de teste local "

    mock_model = MagicMock()
    mock_model.transcribe.return_value = ([mock_seg], MagicMock())
    transcriber._model = mock_model

    segments = transcriber.transcribe(wav_path)
    assert len(segments) == 1
    assert segments[0].start == 1.0
    assert segments[0].end == 4.0
    assert segments[0].text == "Transcrição de teste local"


@patch("urllib.request.urlopen")
def test_cloud_transcriber_mock_api(mock_urlopen, tmp_path):
    wav_path = str(tmp_path / "dummy_cloud.wav")
    with open(wav_path, "wb") as f:
        f.write(b"RIFFclouddata")

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({
        "segments": [
            {"start": 0.5, "end": 3.0, "text": "Fala recebida da nuvem"}
        ]
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    transcriber = CloudMeetingTranscriber(api_key="sk-test", api_base="https://api.test.com/v1")
    segments = transcriber.transcribe(wav_path)

    assert len(segments) == 1
    assert segments[0].text == "Fala recebida da nuvem"
    assert segments[0].start == 0.5


# ==============================================================================
# 4. Testes do Analisador (analyzer.py)
# ==============================================================================

def test_parse_summary_json_variants():
    # Caso 1: JSON perfeito
    raw1 = '{"title": "Título 1", "executive_summary": "Resumo 1", "topics": ["T1"], "decisions": ["D1"], "action_items": []}'
    res1 = parse_summary_json(raw1)
    assert res1["title"] == "Título 1"
    assert res1["topics"] == ["T1"]

    # Caso 2: Embutido em markdown ```json ... ```
    raw2 = 'Aqui está a ata:\n```json\n{"title": "Título MD", "executive_summary": "Resumo MD", "topics": [], "decisions": [], "action_items": []}\n```\nEspero ter ajudado!'
    res2 = parse_summary_json(raw2)
    assert res2["title"] == "Título MD"

    # Caso 3: Texto livre sem JSON (fallback tolerante)
    raw3 = "Apenas uma conversa informal onde nada foi decidido."
    res3 = parse_summary_json(raw3, default_title="Fallback")
    assert res3["title"] == "Fallback"
    assert "Apenas uma conversa" in res3["executive_summary"]


@patch("urllib.request.urlopen")
def test_local_analyzer_mock_ollama(mock_urlopen):
    analyzer = LocalMeetingAnalyzer(host="http://localhost:11434", model="qwen2.5:3b")

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({
        "message": {
            "content": json.dumps({
                "title": "Reunião de Planejamento",
                "executive_summary": "Definimos o cronograma do trimestre.",
                "topics": ["Cronograma", "Orçamento"],
                "decisions": ["Contratar novo servidor"],
                "action_items": [{"task": "Orçar VPS", "owner": "Carlos", "deadline": "Segunda"}]
            })
        }
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    summary = analyzer.analyze("Transcrição de teste", metadata={"title": "Provisório", "duration_seconds": 60.0})
    assert summary.title == "Reunião de Planejamento"
    assert summary.topics == ["Cronograma", "Orçamento"]
    assert len(summary.action_items) == 1
    assert summary.action_items[0]["owner"] == "Carlos"


@patch("urllib.request.urlopen")
def test_cloud_analyzer_mock_gemini(mock_urlopen):
    analyzer = CloudMeetingAnalyzer(api_key="test-key", model="gemini-2.0-flash")

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "title": "Ata Gemini Cloud",
                        "executive_summary": "Processamento em alta velocidade via nuvem.",
                        "topics": ["Performance"],
                        "decisions": ["Usar Cloud para reuniões longas"],
                        "action_items": []
                    })
                }
            }
        ]
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    summary = analyzer.analyze("Transcrição via nuvem", metadata={"title": "Provisório"})
    assert summary.title == "Ata Gemini Cloud"
    assert summary.decisions == ["Usar Cloud para reuniões longas"]


# ==============================================================================
# 5. Testes do Orquestrador (manager.py)
# ==============================================================================

def test_sanitize_filename():
    assert sanitize_filename("Ata de Reunião: Projeto X!") == "ata_de_reuniao_projeto_x"
    assert sanitize_filename("???") == "reuniao"


def test_meeting_manager_full_workflow(tmp_path):
    storage_dir = str(tmp_path / "meeting_storage")

    # Mocks para transcritor e analisador customizados
    mock_transcriber = MagicMock(spec=LocalMeetingTranscriber)
    mock_transcriber.transcribe.return_value = [
        MeetingSegment(start=0.0, end=5.0, text="Olá, vamos iniciar o projeto."),
        MeetingSegment(start=5.5, end=12.0, text="Perfeito, eu cuido do backend.")
    ]

    mock_analyzer = MagicMock(spec=LocalMeetingAnalyzer)
    mock_analyzer.analyze.return_value = MeetingSummary(
        title="Kickoff do Projeto",
        date="24/10/2026 14:00",
        duration_seconds=12.0,
        executive_summary="Reunião inicial de kickoff definindo papéis.",
        topics=["Início de projeto", "Arquitetura"],
        decisions=["Vitor lidera backend"],
        action_items=[{"task": "Configurar repositório", "owner": "Vitor", "deadline": "Hoje"}]
    )

    manager = MeetingManager(
        storage_dir=storage_dir,
        default_provider="local",
        transcriber=mock_transcriber,
        analyzer=mock_analyzer,
    )

    # 1. Iniciar Reunião
    session = manager.start_meeting(title="Kickoff do Projeto")
    assert session.status == MeetingStatus.RECORDING
    assert manager.active_session is not None
    assert session.session_id == manager.active_session.session_id

    # Tentar iniciar outra com uma em andamento deve falhar
    with pytest.raises(RuntimeError):
        manager.start_meeting(title="Outra Reunião")

    # 2. Pausar e Retomar
    assert manager.pause_meeting() is True
    assert session.status == MeetingStatus.PAUSED

    assert manager.resume_meeting() is True
    assert session.status == MeetingStatus.RECORDING

    # 3. Encerrar Gravação
    stopped_session = manager.stop_meeting()
    assert stopped_session.status == MeetingStatus.STOPPED
    assert manager.active_session is None

    # 4. Processamento Síncrono
    processed_session = manager.process_meeting_sync(stopped_session.session_id)
    assert processed_session.status == MeetingStatus.COMPLETED
    assert processed_session.summary is not None
    assert processed_session.summary.title == "Kickoff do Projeto"
    assert len(processed_session.transcript_segments) == 2
    assert processed_session.output_markdown_path is not None
    assert os.path.exists(processed_session.output_markdown_path)

    # Verifica o conteúdo do arquivo Markdown gerado
    with open(processed_session.output_markdown_path, "r", encoding="utf-8") as f:
        md_text = f.read()
    assert "# 📋 Ata de Reunião: Kickoff do Projeto" in md_text
    assert "Vitor lidera backend" in md_text
    assert "Configurar repositório" in md_text

    # 5. Persistência e reload do histórico
    manager2 = MeetingManager(storage_dir=storage_dir)
    loaded_sessions = manager2.list_sessions()
    assert len(loaded_sessions) == 1
    assert loaded_sessions[0].session_id == session.session_id
    assert loaded_sessions[0].status == MeetingStatus.COMPLETED

    # 6. Exclusão de Sessão
    deleted = manager.delete_session(session.session_id)
    assert deleted is True
    assert len(manager.list_sessions()) == 0
    assert not os.path.exists(processed_session.output_markdown_path)


def test_meeting_manager_process_async(tmp_path):
    storage_dir = str(tmp_path / "async_meeting_storage")

    mock_transcriber = MagicMock()
    mock_transcriber.transcribe.return_value = [MeetingSegment(start=0.0, end=2.0, text="Teste rápido")]

    mock_analyzer = MagicMock()
    mock_analyzer.analyze.return_value = MeetingSummary(
        title="Async Test",
        date="24/10/2026",
        duration_seconds=2.0,
        executive_summary="Resumo assíncrono."
    )

    manager = MeetingManager(
        storage_dir=storage_dir,
        transcriber=mock_transcriber,
        analyzer=mock_analyzer
    )

    session = manager.start_meeting(title="Async Test")
    manager.stop_meeting()

    complete_called = False
    def on_complete(s):
        nonlocal complete_called
        complete_called = True

    future = manager.process_meeting_async(session.session_id, on_complete=on_complete)
    future.result(timeout=5.0)

    assert complete_called is True
    updated_session = manager.get_session(session.session_id)
    assert updated_session.status == MeetingStatus.COMPLETED
