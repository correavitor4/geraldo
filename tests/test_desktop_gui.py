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
        "pomo-empty",
        "pomo-active-display",
        "pomo-countdown",
        "pomo-phase-badge",
        "pomo-cycle-text",
        "pomo-actions",
        "btn-pomo-toggle",
        "btn-pomo-skip",
        "btn-pomo-reset",
        "btn-toggle-plan-pomo",
        "pomo-plan-form",
        "pomo-input-work",
        "pomo-input-break",
        "pomo-input-long-break",
        "pomo-input-long-interval",
        "pomo-input-cycles",
        "btn-save-plan-pomo",
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


def test_html_pomodoro_empty_state_initial():
    """Valida se o estado inicial do Pomodoro no HTML reflete ausência de pomodoro ativo."""
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    assert '<div id="pomo-empty" class="empty-state">Nenhum pomodoro ativo</div>' in html
    assert '<div id="pomo-active-display" class="hidden">' in html
    assert 'class="badge-phase hidden"' in html
    assert 'class="pomo-actions idle"' in html
    assert 'id="btn-pomo-skip" class="btn-action hidden"' in html
    assert 'id="btn-pomo-reset" class="btn-action hidden"' in html


def test_html_pomodoro_planning_form():
    """Valida se o formulário de planejamento de Pomodoro está presente com inputs e presets."""
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    assert 'id="btn-toggle-plan-pomo"' in html
    assert 'id="pomo-plan-form" class="pomo-plan-form hidden"' in html
    assert 'data-work="25"' in html
    assert 'data-work="50"' in html
    assert 'id="pomo-input-work"' in html
    assert 'id="pomo-input-break"' in html
    assert 'id="pomo-input-long-break"' in html
    assert 'id="pomo-input-long-interval"' in html
    assert 'id="pomo-input-cycles"' in html
    assert 'id="btn-save-plan-pomo"' in html
    assert 'data-long-break="15"' in html
    assert 'data-long-interval="4"' in html


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


# ==========================================
# TESTES DE COBERTURA DE TODOS OS BOTÕES DA INTERFACE DESKTOP
# ==========================================

def test_html_all_buttons_elements_and_attributes():
    """Valida a declaração e presença de todos os botões da GUI desktop no HTML."""
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    expected_buttons = [
        # Navbar / Cabeçalho
        ("id=\"btn-header-calendar\"", "Botão de calendário no topo"),
        ("id=\"btn-open-settings\"", "Botão de configurações no topo"),
        ("id=\"btn-mic-toggle\"", "Botão de microfone/mudo no topo"),

        # Chat
        ("id=\"btn-clear-chat\"", "Botão limpar histórico de chat"),
        ("id=\"btn-send\"", "Botão enviar comando"),
        ("id=\"btn-cancel\"", "Botão cancelar áudio"),

        # Pomodoro
        ("id=\"btn-toggle-plan-pomo\"", "Botão abrir painel planejar pomodoro"),
        ("id=\"btn-save-plan-pomo\"", "Botão iniciar ciclo planejado"),
        ("id=\"btn-pomo-toggle\"", "Botão principal iniciar/pausar pomodoro"),
        ("id=\"btn-pomo-skip\"", "Botão pular fase do pomodoro"),
        ("id=\"btn-pomo-reset\"", "Botão resetar pomodoro"),

        # Timers
        ("id=\"btn-toggle-new-timer\"", "Botão abrir formulário de novo timer"),
        ("id=\"btn-add-timer-submit\"", "Botão criar timer"),

        # Calendário
        ("id=\"btn-open-calendar\"", "Botão abrir agenda no navegador"),
        ("id=\"btn-auth-calendar\"", "Botão vincular conta Google"),

        # Modal de Configurações
        ("id=\"btn-close-settings\"", "Botão fechar modal de configurações"),
        ("id=\"btn-cancel-settings\"", "Botão cancelar modal"),
        ("id=\"btn-save-settings\"", "Botão salvar configurações"),
        ("id=\"btn-test-ollama\"", "Botão testar conexão LLM"),
        ("id=\"btn-detect-container\"", "Botão detectar container docker"),
        ("id=\"btn-toggle-key-visibility\"", "Botão alternar visibilidade da API Key"),
        ("id=\"btn-refresh-audio\"", "Botão recarregar dispositivos de áudio"),
        ("id=\"btn-test-audio-beep\"", "Botão reproduzir bipe de teste"),
        ("id=\"btn-export-tui-path\"", "Botão exportar PATH do TUI"),
        ("id=\"btn-check-updates\"", "Botão verificar atualizações"),
    ]

    for pattern, desc in expected_buttons:
        assert pattern in html, f"{desc} ({pattern}) não encontrado no index.html"


def test_js_all_buttons_event_listeners_bound():
    """Valida se todos os botões da GUI possuem event listener registrado no app.js."""
    with open(JS_PATH, "r", encoding="utf-8") as f:
        js = f.read()

    expected_bindings = [
        ("this.dom.btnSend.addEventListener(\"click\"", "btnSend"),
        ("this.dom.btnMicToggle.addEventListener(\"click\"", "btnMicToggle"),
        ("this.dom.btnCancel.addEventListener(\"click\"", "btnCancel"),
        ("this.dom.btnClearChat.addEventListener(\"click\"", "btnClearChat"),
        ("this.dom.btnTogglePlanPomo.addEventListener(\"click\"", "btnTogglePlanPomo"),
        ("this.dom.btnSavePlanPomo.addEventListener(\"click\"", "btnSavePlanPomo"),
        ("this.dom.btnPomoToggle.addEventListener(\"click\"", "btnPomoToggle"),
        ("this.dom.btnPomoSkip.addEventListener(\"click\"", "btnPomoSkip"),
        ("this.dom.btnPomoReset.addEventListener(\"click\"", "btnPomoReset"),
        ("this.dom.btnToggleNewTimer.addEventListener(\"click\"", "btnToggleNewTimer"),
        ("this.dom.btnAddTimerSubmit.addEventListener(\"click\"", "btnAddTimerSubmit"),
        ("this.dom.btnOpenSettings.addEventListener(\"click\"", "btnOpenSettings"),
        ("this.dom.btnCloseSettings.addEventListener(\"click\"", "btnCloseSettings"),
        ("this.dom.btnCancelSettings.addEventListener(\"click\"", "btnCancelSettings"),
        ("this.dom.btnSaveSettings.addEventListener(\"click\"", "btnSaveSettings"),
        ("this.dom.btnTestOllama.addEventListener(\"click\"", "btnTestOllama"),
        ("this.dom.btnDetectContainer.addEventListener(\"click\"", "btnDetectContainer"),
        ("this.dom.btnToggleKeyVisibility.addEventListener(\"click\"", "btnToggleKeyVisibility"),
        ("this.dom.btnHeaderCalendar.addEventListener(\"click\"", "btnHeaderCalendar"),
        ("this.dom.btnOpenCalendar.addEventListener(\"click\"", "btnOpenCalendar"),
        ("this.dom.btnAuthCalendar.addEventListener(\"click\"", "btnAuthCalendar"),
        ("this.dom.btnCheckUpdates.addEventListener(\"click\"", "btnCheckUpdates"),
        ("this.dom.btnRefreshAudio.addEventListener(\"click\"", "btnRefreshAudio"),
        ("this.dom.btnTestAudioBeep.addEventListener(\"click\"", "btnTestAudioBeep"),
        ("this.dom.btnExportTuiPath.addEventListener(\"click\"", "btnExportTuiPath"),
    ]

    for binding, name in expected_bindings:
        assert binding in js, f"Listener para {name} ('{binding}') ausente no app.js"


def test_js_pomodoro_button_toggle_state_machine():
    """Valida se o app.js trata os 4 estados do botão de Pomodoro (start, pause, resume, advance)."""
    with open(JS_PATH, "r", encoding="utf-8") as f:
        js = f.read()

    assert "sub_action: \"start\"" in js or "'start'" in js
    assert "sub_action: \"pause\"" in js or "'pause'" in js
    assert "sub_action: \"resume\"" in js or "'resume'" in js
    assert "sub_action: \"advance\"" in js or "'advance'" in js
    assert "sub_action: \"skip\"" in js or "'skip'" in js
    assert "sub_action: \"reset\"" in js or "'reset'" in js


@pytest.mark.anyio
async def test_desktop_gui_ipc_all_button_rpc_actions(monkeypatch):
    """
    Simula e valida no servidor IPC todas as chamadas RPC disparadas por cada botão da Desktop GUI.
    """
    monkeypatch.setattr("tools.calendar.CalendarTools.authenticate", classmethod(lambda cls: True))
    monkeypatch.setattr("webbrowser.open", lambda *args, **kwargs: True)
    import sounddevice as sd
    monkeypatch.setattr(sd, "play", lambda *args, **kwargs: None)
    monkeypatch.setattr(sd, "wait", lambda *args, **kwargs: None)

    server = GeraldoIPCServer(host=TEST_GUI_IPC_HOST, port=8796)
    server.set_prompt_handler(lambda t: f"Eco: {t}")
    server.start()

    uri = f"ws://{TEST_GUI_IPC_HOST}:8796"
    try:
        async with connect(uri) as ws:
            # Consome o evento connected
            await asyncio.wait_for(ws.recv(), timeout=2.0)

            # 1. Botão Enviar (#btn-send) e Sugestões (.chip-suggestion)
            await ws.send(json.dumps({
                "id": "btn-send-1",
                "action": "send_prompt",
                "params": {"text": "qual a previsão do tempo"}
            }))

            # 2. Botão Microfone (#btn-mic-toggle)
            await ws.send(json.dumps({"id": "btn-mic-1", "action": "toggle_mute", "params": {}}))

            # 3. Botão Cancelar (#btn-cancel)
            await ws.send(json.dumps({"id": "btn-cancel-1", "action": "cancel", "params": {}}))

            # 4. Botão Pomodoro Iniciar Planejado (#btn-save-plan-pomo)
            await ws.send(json.dumps({
                "id": "btn-pomo-plan-1",
                "action": "pomodoro",
                "params": {
                    "sub_action": "start",
                    "work_minutes": 25,
                    "break_minutes": 5,
                    "long_break_minutes": 15,
                    "long_break_interval": 4,
                    "cycle": 1
                }
            }))

            # 4.1 Pomodoro Acionamento Direto de Pausa Longa
            await ws.send(json.dumps({
                "id": "btn-pomo-long-break-1",
                "action": "pomodoro",
                "params": {"sub_action": "long_break", "long_break_minutes": 20}
            }))

            # 5. Botão Pomodoro Pausar (#btn-pomo-toggle em work)
            await ws.send(json.dumps({
                "id": "btn-pomo-pause-1",
                "action": "pomodoro",
                "params": {"sub_action": "pause"}
            }))

            # 6. Botão Pomodoro Retomar (#btn-pomo-toggle em pause)
            await ws.send(json.dumps({
                "id": "btn-pomo-resume-1",
                "action": "pomodoro",
                "params": {"sub_action": "resume"}
            }))

            # 7. Botão Pomodoro Avançar (#btn-pomo-toggle em finished)
            await ws.send(json.dumps({
                "id": "btn-pomo-advance-1",
                "action": "pomodoro",
                "params": {"sub_action": "advance"}
            }))

            # 8. Botão Pomodoro Pular (#btn-pomo-skip)
            await ws.send(json.dumps({
                "id": "btn-pomo-skip-1",
                "action": "pomodoro",
                "params": {"sub_action": "skip"}
            }))

            # 9. Botão Pomodoro Reset (#btn-pomo-reset)
            await ws.send(json.dumps({
                "id": "btn-pomo-reset-1",
                "action": "pomodoro",
                "params": {"sub_action": "reset"}
            }))

            # 10. Botão Criar Timer (#btn-add-timer-submit)
            await ws.send(json.dumps({
                "id": "btn-timer-add-1",
                "action": "timer_add",
                "params": {"label": "Café", "duration_sec": 180}
            }))

            # 11. Botão Autenticar Calendário (#btn-auth-calendar)
            await ws.send(json.dumps({
                "id": "btn-auth-cal-1",
                "action": "auth_calendar",
                "params": {}
            }))

            # 12. Botão Abrir Calendário (#btn-open-calendar)
            await ws.send(json.dumps({
                "id": "btn-open-cal-1",
                "action": "open_calendar",
                "params": {"url": "https://calendar.google.com"}
            }))

            # 13. Botão Listar Dispositivos de Áudio (#btn-refresh-audio)
            await ws.send(json.dumps({
                "id": "btn-audio-list-1",
                "action": "get_audio_devices",
                "params": {}
            }))

            # 14. Botão Testar Beep de Saída (#btn-test-audio-beep)
            await ws.send(json.dumps({
                "id": "btn-audio-beep-1",
                "action": "test_audio_beep",
                "params": {"device": None}
            }))

            # 15. Botão Exportar Atalho TUI (#btn-export-tui-path)
            await ws.send(json.dumps({
                "id": "btn-export-tui-1",
                "action": "export_tui_path",
                "params": {}
            }))

            # 16. Botão Salvar Configurações (#btn-save-settings)
            await ws.send(json.dumps({
                "id": "btn-save-cfg-1",
                "action": "set_config",
                "params": {
                    "provider": "ollama",
                    "ollama_host": "http://localhost:11434",
                    "llm_model": "qwen2.5:3b",
                    "audio_input_device": None,
                    "audio_output_device": None,
                    "persist": False
                }
            }))

            # Coleta todas as respostas RPC
            expected_ids = {
                "btn-send-1",
                "btn-mic-1",
                "btn-cancel-1",
                "btn-pomo-plan-1",
                "btn-pomo-pause-1",
                "btn-pomo-resume-1",
                "btn-pomo-advance-1",
                "btn-pomo-skip-1",
                "btn-pomo-reset-1",
                "btn-timer-add-1",
                "btn-auth-cal-1",
                "btn-open-cal-1",
                "btn-audio-list-1",
                "btn-audio-beep-1",
                "btn-export-tui-1",
                "btn-save-cfg-1",
            }
            received_ids = set()

            for _ in range(40):
                if len(received_ids) == len(expected_ids):
                    break
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    msg = json.loads(raw)
                    if msg.get("type") == "response":
                        req_id = msg.get("id")
                        if req_id in expected_ids:
                            assert msg.get("status") == "ok", f"Erro na resposta de {req_id}: {msg.get('error')}"
                            received_ids.add(req_id)
                except asyncio.TimeoutError:
                    break

            missing = expected_ids - received_ids
            assert not missing, f"Chamadas RPC pendentes ou sem resposta: {missing}"
    finally:
        server.stop()


def test_html_audio_devices_selectors_and_specs_exist():
    """Valida se os seletores de microfone/saída e os indicadores visuais existem no HTML."""
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    assert 'id="cfg-audio-input"' in html, "Seletor de microfone de entrada ausente no index.html"
    assert 'id="cfg-audio-output"' in html, "Seletor de saída de som ausente no index.html"
    assert 'id="btn-refresh-audio"' in html, "Botão de recarregar áudio ausente no index.html"
    assert 'id="btn-test-audio-beep"' in html, "Botão de testar bipe de áudio ausente no index.html"
    assert 'id="specs-audio-in-text"' in html, "Indicador de microfone ativo ausente no card de motor local"
    assert 'id="specs-audio-out-text"' in html, "Indicador de saída ativa ausente no card de motor local"


@pytest.mark.anyio
async def test_desktop_gui_audio_device_selection_rpc(monkeypatch):
    """Valida fluxo completo RPC de obtenção, configuração e teste de dispositivos de áudio."""
    import sounddevice as sd
    monkeypatch.setattr(sd, "play", lambda *args, **kwargs: None)
    monkeypatch.setattr(sd, "wait", lambda *args, **kwargs: None)

    server = GeraldoIPCServer(host=TEST_GUI_IPC_HOST, port=8797)
    server.start()
    uri = f"ws://{TEST_GUI_IPC_HOST}:8797"

    async def recv_response(ws, req_id):
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            msg = json.loads(raw)
            if msg.get("type") == "response" and msg.get("id") == req_id:
                return msg

    try:
        async with connect(uri) as ws:
            # Consome handshake
            await asyncio.wait_for(ws.recv(), timeout=2.0)

            # 1. Consulta configuração e lista de dispositivos
            await ws.send(json.dumps({
                "id": "get-audio-test-1",
                "action": "get_audio_config",
                "params": {}
            }))
            resp = await recv_response(ws, "get-audio-test-1")
            assert resp.get("status") == "ok"
            data = resp.get("data", {})
            assert "input_device" in data
            assert "output_device" in data
            assert "available_inputs" in data
            assert "available_outputs" in data

            # 2. Define dispositivos específicos de entrada e saída
            await ws.send(json.dumps({
                "id": "set-audio-test-1",
                "action": "set_audio_config",
                "params": {
                    "input_device": "Microfone Teste",
                    "output_device": "Alto-falante Teste",
                    "persist": False
                }
            }))
            resp = await recv_response(ws, "set-audio-test-1")
            assert resp.get("status") == "ok"
            assert resp["data"]["input_device"] == "Microfone Teste"
            assert resp["data"]["output_device"] == "Alto-falante Teste"

            # 3. Dispara teste de som de saída no dispositivo configurado
            await ws.send(json.dumps({
                "id": "test-beep-1",
                "action": "test_audio_beep",
                "params": {"device": "Alto-falante Teste"}
            }))
            resp = await recv_response(ws, "test-beep-1")
            assert resp.get("status") == "ok"

            # 4. Reseta para o padrão do sistema (None)
            await ws.send(json.dumps({
                "id": "set-audio-reset-1",
                "action": "set_audio_config",
                "params": {
                    "input_device": None,
                    "output_device": None,
                    "persist": False
                }
            }))
            resp = await recv_response(ws, "set-audio-reset-1")
            assert resp.get("status") == "ok"
            assert resp["data"]["input_device"] is None
            assert resp["data"]["output_device"] is None
    finally:
        server.stop()


def test_desktop_gui_long_break_styling_and_state():
    """Valida presença de classes CSS e mapeamento JS para pausa longa."""
    with open(CSS_PATH, "r", encoding="utf-8") as f:
        css = f.read()
    with open(JS_PATH, "r", encoding="utf-8") as f:
        js = f.read()

    assert ".badge-phase.long_break" in css
    assert ".badge-phase.long_break_finished" in css
    assert "Pausa Longa" in js
    assert "pomoInputLongBreak" in js
    assert "pomoInputLongInterval" in js



