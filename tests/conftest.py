import pytest
import os
import tempfile
import shutil
from brain.nlu import IntentEngine
from tools.timer import TimerManager

@pytest.fixture(scope="session", autouse=True)
def preserve_real_user_timer_state():
    """Salva o estado real de timers, alarmes, pomodoro e status antes dos testes e restaura ao final."""
    state_file = os.path.expanduser("~/.config/geraldo_state.json")
    status_file = "/tmp/geraldo_status.json"

    saved_state = None
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                saved_state = f.read()
        except Exception:
            pass

    saved_status = None
    if os.path.exists(status_file):
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                saved_status = f.read()
        except Exception:
            pass

    yield

    if saved_state is not None:
        try:
            with open(state_file, "w", encoding="utf-8") as f:
                f.write(saved_state)
        except Exception:
            pass

    if saved_status is not None:
        try:
            with open(status_file, "w", encoding="utf-8") as f:
                f.write(saved_status)
        except Exception:
            pass

@pytest.fixture(scope="session")
def shared_nlu_engine():
    """Treina o IntentEngine uma única vez para toda a suíte de testes para máxima performance."""
    return IntentEngine(confidence_threshold=0.35)

@pytest.fixture
def isolated_timer_manager(tmp_path):
    """Isola o TimerManager para não interferir nos arquivos reais do usuário."""
    command_dir = str(tmp_path / "geraldo_commands")
    status_file = str(tmp_path / "geraldo_status.json")
    state_file = str(tmp_path / "geraldo_state.json")
    os.makedirs(command_dir, exist_ok=True)

    TimerManager.reset_for_tests(
        command_dir=command_dir,
        status_file=status_file,
        state_file=state_file
    )
    yield TimerManager
    TimerManager.stop_background_loop()
    TimerManager.reset_for_tests(
        command_dir=str(tmp_path / "dummy_commands"),
        status_file=str(tmp_path / "dummy_status.json"),
        state_file=str(tmp_path / "dummy_state.json")
    )
