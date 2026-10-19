import asyncio
import json
import os
import re
import pytest
from websockets.asyncio.client import connect

from core.ipc import GeraldoIPCServer

GUI_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "desktop-ui"))
HTML_PATH = os.path.join(GUI_DIR, "index.html")
CSS_PATH = os.path.join(GUI_DIR, "styles.css")
JS_PATH = os.path.join(GUI_DIR, "app.js")

TEST_GUI_IPC_PORT = 8798
TEST_GUI_IPC_HOST = "127.0.0.1"


# ==========================================
# TESTES DE HTML (ESTRUTURA & SEMÂNTICA)
# ==========================================

def test_html_file_exists_and_doctype():
    """Valida se o index.html existe e possui DOCTYPE HTML5 válido."""
    assert os.path.exists(HTML_PATH)
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    assert content.strip().startswith("<!DOCTYPE html>")
    assert '<html lang="pt-BR">' in content
    assert '<meta charset="UTF-8">' in content
    assert '<meta name="viewport"' in content


def test_html_assets_and_font_links():
    """Valida links de estilos e fontes no HTML."""
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    assert '<link rel="stylesheet" href="styles.css">' in content
    assert '<script src="app.js"></script>' in content
    assert "fonts.googleapis.com" in content
    assert "Outfit" in content


def test_html_all_critical_dom_elements():
    """Valida presença de todos os IDs consumidos pelo app.js."""
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    required_ids = [
        "top-navbar",
        "audio-wave",
        "state-badge",
        "btn-mic-toggle",
        "mic-icon",
        "mic-text",
        "conn-pill",
        "conn-text",
        "main-content",
        "chat-section",
        "chat-stream",
        "btn-clear-chat",
        "input-bar",
        "prompt-input",
        "btn-send",
        "btn-cancel",
        "sidebar-section",
        "pomo-countdown",
        "pomo-phase-badge",
        "pomo-cycle-text",
        "btn-pomo-toggle",
        "btn-pomo-skip",
        "btn-pomo-reset",
        "timers-list",
        "alarms-list",
        "btn-toggle-new-timer",
        "new-timer-form",
        "btn-add-timer-submit",
        "new-timer-label",
        "new-timer-min",
        "new-timer-sec",
        "btn-open-settings",
        "settings-modal",
        "btn-close-settings",
        "btn-cancel-settings",
        "btn-save-settings",
        "btn-test-ollama",
        "cfg-ollama-host",
        "cfg-llm-model",
        "test-result-box",
        "specs-llm-text",
    ]

    for elem_id in required_ids:
        pattern = f'id="{elem_id}"'
        assert pattern in html, f"Elemento com id '{elem_id}' não encontrado no index.html"


def test_html_chips_suggestions():
    """Valida os botões de atalho rápido com prompts prontos."""
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    chips = re.findall(r'class="chip-suggestion"\s+data-prompt="([^"]+)"', html)
    assert len(chips) >= 3, "Poucas sugestões de prompt configuradas"
    assert any("agenda" in p.lower() for p in chips)
    assert any("timer" in p.lower() for p in chips)


# ==========================================
# TESTES DE CSS (DESIGN SYSTEM & RESPONSIVIDADE)
# ==========================================

def test_css_variables_and_dark_palette():
    """Valida definição do design system com tokens CSS."""
    assert os.path.exists(CSS_PATH)
    with open(CSS_PATH, "r", encoding="utf-8") as f:
        css = f.read()

    required_vars = [
        "--bg-dark",
        "--bg-surface",
        "--bg-card",
        "--accent-blue",
        "--accent-green",
        "--accent-yellow",
        "--accent-red",
        "--font-sans",
        "--font-mono",
    ]
    for var in required_vars:
        assert var in css, f"Variável CSS '{var}' ausente no styles.css"


def test_css_animations_and_audio_wave():
    """Valida animações CSS da onda de áudio e transições suaves."""
    with open(CSS_PATH, "r", encoding="utf-8") as f:
        css = f.read()

    assert "@keyframes waveAnim" in css
    assert "@keyframes fadeIn" in css
    assert ".audio-wave.listening" in css
    assert ".audio-wave.speaking" in css
    assert ".state-badge.state-listening" in css
    assert ".state-badge.state-speaking" in css


def test_css_grid_and_layout():
    """Valida layout de duas colunas (chat + sidebar)."""
    with open(CSS_PATH, "r", encoding="utf-8") as f:
        css = f.read()

    assert "grid-template-columns: 1fr 360px;" in css or "grid-template-columns" in css
    assert ".chat-stream" in css
    assert ".message-bubble.user" in css
    assert ".message-bubble.assistant" in css


def test_html_and_css_ollama_settings_modal():
    """Valida a estrutura do modal de configurações do Ollama e seus estilos CSS."""
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()
    with open(CSS_PATH, "r", encoding="utf-8") as f:
        css = f.read()

    # Presets de container Docker / Localhost
    assert "data-host=\"http://localhost:11434\"" in html
    assert "data-host=\"http://host.docker.internal:11434\"" in html
    assert "data-host=\"http://ollama:11434\"" in html

    # CSS do modal
    assert ".modal-overlay" in css
    assert ".modal-dialog" in css
    assert ".preset-chip" in css
    assert "backdrop-filter: blur" in css


# ==========================================
# TESTES DE JS (PROTOCOLO & CLIENTE WEBSOCKET)
# ==========================================

def test_js_file_structure_and_syntax():
    """Valida se o app.js define a classe GeraldoDesktopClient."""
    assert os.path.exists(JS_PATH)
    with open(JS_PATH, "r", encoding="utf-8") as f:
        js = f.read()

    assert "class GeraldoDesktopClient" in js
    assert "openSettingsModal" in js
    assert "closeSettingsModal" in js
    assert "testOllamaConnection" in js
    assert "saveOllamaSettings" in js
    assert "updateConfigDisplay" in js
    assert "connect()" in js
    assert "handleMessage(" in js
    assert "handleEvent(" in js
    assert "sendAction(" in js
    assert "updateDashboardStatus(" in js
    assert "submitPrompt(" in js


def test_js_event_handlers_coverage():
    """Valida se o app.js trata todos os eventos gerados pelo GeraldoIPCServer."""
    with open(JS_PATH, "r", encoding="utf-8") as f:
        js = f.read()

    expected_events = [
        "connected",
        "state_changed",
        "mute_changed",
        "transcription",
        "reply",
        "status_update",
        "cancelled",
    ]
    for ev in expected_events:
        assert f'case "{ev}":' in js or f"'{ev}'" in js, f"Evento '{ev}' não tratado no app.js"


def test_js_rpc_actions_supported():
    """Valida se o app.js envia os comandos RPC suportados pelo Geraldo."""
    with open(JS_PATH, "r", encoding="utf-8") as f:
        js = f.read()

    expected_actions = [
        "send_prompt",
        "toggle_mute",
        "cancel",
        "pomodoro",
        "timer_add",
    ]
    for act in expected_actions:
        assert f'"{act}"' in js or f"'{act}'" in js, f"Ação RPC '{act}' não encontrada no app.js"


# ==========================================
# TESTE DE CONTRATO PAIXÃO-IPC (DESKTOP GUI <-> CORE DAEMON)
# ==========================================

@pytest.mark.anyio
async def test_desktop_client_ipc_contract_full_exchange():
    """
    Testa a compatibilidade exata de formato JSON entre o cliente desktop
    e o servidor IPC do Geraldo.
    """
    server = GeraldoIPCServer(host=TEST_GUI_IPC_HOST, port=TEST_GUI_IPC_PORT)
    server.set_prompt_handler(lambda t: f"Resposta para: {t}")
    server.start()

    try:
        uri = f"ws://{TEST_GUI_IPC_HOST}:{TEST_GUI_IPC_PORT}"
        async with connect(uri) as ws:
            # 1. Recepção do evento 'connected'
            raw_welcome = await asyncio.wait_for(ws.recv(), timeout=2.0)
            welcome = json.loads(raw_welcome)
            assert welcome["type"] == "event"
            assert welcome["event"] == "connected"
            assert "assistant_state" in welcome["data"]
            assert "is_muted" in welcome["data"]

            # 2. Envio de prompt exatamente no formato gerado pelo app.js (sendAction)
            gui_prompt_payload = {
                "id": "gui-1729300000000",
                "action": "send_prompt",
                "params": {"text": "que dia é hoje"}
            }
            await ws.send(json.dumps(gui_prompt_payload))

            # 3. Servidor responde RPC e dispara eventos
            msgs = []
            for _ in range(2):
                raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                msgs.append(json.loads(raw))

            response_msg = next(m for m in msgs if m.get("type") == "response")
            assert response_msg["id"] == "gui-1729300000000"
            assert response_msg["status"] == "ok"

            # 4. Envio de toggle_mute (clique no microfone do desktop)
            gui_mute_payload = {
                "id": "gui-mute-1",
                "action": "toggle_mute",
                "params": {}
            }
            await ws.send(json.dumps(gui_mute_payload))

            raw_mute = await asyncio.wait_for(ws.recv(), timeout=2.0)
            mute_event_or_resp = json.loads(raw_mute)
            assert mute_event_or_resp is not None

            # 5. Broadcast de status_update (exatamente lido por updateDashboardStatus)
            dashboard_data = {
                "pomodoro": {
                    "state": "work",
                    "cycle": 1,
                    "left": 1400,
                    "work_duration": 1500
                },
                "timers": [
                    {"id": "t1", "label": "Forno", "left": 600, "paused": False}
                ],
                "alarms": [
                    {"id": "a1", "label": "Acordar", "time": "07:00", "enabled": True}
                ]
            }
            server.broadcast_event("status_update", dashboard_data)

            found_status = False
            for _ in range(10):
                raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                msg = json.loads(raw)
                if msg.get("type") == "event" and msg.get("event") == "status_update":
                    found_status = True
                    assert msg["data"]["pomodoro"]["state"] == "work"
                    assert len(msg["data"]["timers"]) == 1
                    assert len(msg["data"]["alarms"]) == 1
                    break

            assert found_status is True, "Evento 'status_update' não recebido pelo cliente"

    finally:
        server.stop()


def test_html_and_css_external_llm_elements():
    """Valida presença dos novos elementos de provedores externos e API Key no index.html e styles.css."""
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()
    with open(CSS_PATH, "r", encoding="utf-8") as f:
        css = f.read()

    # Elementos HTML
    assert 'id="provider-tabs"' in html
    assert 'id="cfg-api-key"' in html
    assert 'id="btn-toggle-key-visibility"' in html
    assert 'id="cfg-api-base"' in html
    assert 'id="model-presets-container"' in html
    assert 'data-provider="groq"' in html
    assert 'data-provider="openai"' in html
    assert 'data-provider="gemini"' in html

    # Estilos CSS
    assert ".provider-selector-tabs" in css
    assert ".provider-tab" in css
    assert ".btn-eye-toggle" in css
    assert ".model-preset-chip" in css


@pytest.mark.anyio
async def test_gui_websocket_external_llm_set_and_get_config():
    """Valida ciclo completo de configuração de LLM externa (Groq / API Key) via IPC WebSocket."""
    import config
    orig_prov = config.LLM_PROVIDER
    orig_key = config.LLM_API_KEY
    orig_model = config.LLM_MODEL
    orig_base = config.LLM_API_BASE

    server = GeraldoIPCServer(host=TEST_GUI_IPC_HOST, port=8799)
    server.start()

    uri = f"ws://{TEST_GUI_IPC_HOST}:8799"
    try:
        async with connect(uri) as ws:
            # Consome o evento connected inicial
            raw_init = await asyncio.wait_for(ws.recv(), timeout=2.0)
            init_data = json.loads(raw_init)
            assert init_data["event"] == "connected"

            # Envia set_config com Groq e API Key
            payload = {
                "id": "set_config-1",
                "action": "set_config",
                "params": {
                    "provider": "groq",
                    "api_key": "gsk_test123456789",
                    "model": "llama-3.3-70b-versatile",
                    "persist": False,
                }
            }
            await ws.send(json.dumps(payload))

            # Aguarda resposta (descartando eventos intercalados se houver)
            resp = None
            for _ in range(5):
                raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                msg = json.loads(raw)
                if msg.get("type") == "response" and msg.get("id") == "set_config-1":
                    resp = msg
                    break

            assert resp is not None
            assert resp["status"] == "ok"
            assert resp["data"]["provider"] == "groq"
            assert resp["data"]["llm_model"] == "llama-3.3-70b-versatile"
            assert "api_key_masked" in resp["data"]
            assert "6789" in resp["data"]["api_key_masked"]

            # Envia get_config para validar retorno seguro
            await ws.send(json.dumps({"id": "get_config-1", "action": "get_config", "params": {}}))
            get_resp = None
            for _ in range(5):
                raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                msg = json.loads(raw)
                if msg.get("type") == "response" and msg.get("id") == "get_config-1":
                    get_resp = msg
                    break

            assert get_resp is not None
            assert get_resp["status"] == "ok"
            assert get_resp["data"]["provider"] == "groq"
            assert get_resp["data"]["has_api_key"] is True
            # A chave crua não deve ser vazada no get_config
            assert "gsk_test123456789" not in json.dumps(get_resp["data"])
    finally:
        server.stop()
        config.LLM_PROVIDER = orig_prov
        config.LLM_API_KEY = orig_key
        config.LLM_MODEL = orig_model
        config.LLM_API_BASE = orig_base

