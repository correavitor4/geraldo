import pytest
import os
import tempfile
import shutil
from brain.nlu import IntentEngine
from tools.timer import TimerManager

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
        command_dir="/tmp/geraldo_commands",
        status_file="/tmp/geraldo_status.json",
        state_file=os.path.expanduser("~/.config/geraldo_state.json")
    )
