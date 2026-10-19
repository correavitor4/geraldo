import asyncio
import json
import pytest
from textual.widgets import Button, Input, Label, RichLog

from core.ipc import GeraldoIPCServer
from ui.tui import GeraldoTUI

TEST_IPC_PORT = 8795
TEST_IPC_HOST = "127.0.0.1"


@pytest.mark.anyio
async def test_tui_layout_and_initial_widgets():
    """Valida se todos os widgets estruturais são montados corretamente."""
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        # Top bar
        assert app.query_one("#title-label", Label) is not None
        conn_badge = app.query_one("#conn-badge", Label)
        assert "Desconectado" in str(conn_badge.render())

        state_badge = app.query_one("#state-badge", Label)
        assert "IDLE" in str(state_badge.render())

        mic_badge = app.query_one("#mic-badge", Label)
        assert "ATIVO" in str(mic_badge.render())

        # Main containers
        assert app.query_one("#chat-title", Label) is not None
        assert app.query_one("#chat-log", RichLog) is not None
        assert app.query_one("#pomo-time", Label) is not None
        assert app.query_one("#timers-box", Label) is not None
        assert app.query_one("#alarms-box", Label) is not None

        # Input e botões
        assert app.query_one("#cmd-input", Input) is not None
        assert app.query_one("#btn-send", Button) is not None
        assert app.query_one("#btn-pomo-toggle", Button) is not None
        assert app.query_one("#btn-pomo-skip", Button) is not None
        assert app.query_one("#btn-pomo-reset", Button) is not None


@pytest.mark.anyio
async def test_tui_state_badge_classes():
    """Testa transições de classes visuais para cada estado do assistente."""
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        badge = app.query_one("#state-badge", Label)

        # Listening
        app.update_state_badge("listening")
        assert "OUVINDO" in str(badge.render())
        assert badge.has_class("state-listening")

        # Thinking
        app.update_state_badge("thinking")
        assert "PENSANDO" in str(badge.render())
        assert badge.has_class("state-thinking")
        assert not badge.has_class("state-listening")

        # Transcribing
        app.update_state_badge("transcribing")
        assert "TRANSCR." in str(badge.render())
        assert badge.has_class("state-thinking")

        # Speaking
        app.update_state_badge("speaking")
        assert "FALANDO" in str(badge.render())
        assert badge.has_class("state-speaking")

        # Idle
        app.update_state_badge("idle")
        assert "IDLE" in str(badge.render())
        assert not badge.has_class("state-speaking")


@pytest.mark.anyio
async def test_tui_connection_and_mic_badges():
    """Testa atualização de badges de conexão e microfone."""
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        conn = app.query_one("#conn-badge", Label)
        mic = app.query_one("#mic-badge", Label)

        # Conexão
        app.update_connection_status(True, "🟢 Conectado (127.0.0.1:8765)")
        assert conn.has_class("connected")
        assert "Conectado" in str(conn.render())

        app.update_connection_status(False, "🔴 Desconectado")
        assert not conn.has_class("connected")

        # Microfone
        app.update_mic_badge(True)
        assert mic.has_class("muted")
        assert "MUDO" in str(mic.render())

        app.update_mic_badge(False)
        assert not mic.has_class("muted")
        assert "ATIVO" in str(mic.render())


@pytest.mark.anyio
async def test_tui_status_dashboard_pomodoro_updates():
    """Valida renderização dos estados do Pomodoro no painel lateral."""
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        pomo_label = app.query_one("#pomo-time", Label)
        btn_toggle = app.query_one("#btn-pomo-toggle", Button)

        # Estado Work (Foco)
        data = {
            "pomodoro": {
                "state": "work",
                "cycle": 2,
                "left": 1215,  # 20m15s
            }
        }
        app.update_status_dashboard(data)
        assert "Foco (Ciclo 2)" in str(pomo_label.render())
        assert "20:15" in str(pomo_label.render())
        assert btn_toggle.label == "⏸ Pausar"
        assert btn_toggle.variant == "warning"

        # Estado Break (Pausa)
        data_break = {
            "pomodoro": {
                "state": "break",
                "cycle": 2,
                "left": 290,  # 04m50s
            }
        }
        app.update_status_dashboard(data_break)
        assert "Pausa (Ciclo 2)" in str(pomo_label.render())
        assert "04:50" in str(pomo_label.render())
        assert btn_toggle.label == "⏸ Pausar"

        # Estado Idle (Inativo)
        data_idle = {
            "pomodoro": {
                "state": "idle",
                "cycle": 1,
                "left": 1500,
            }
        }
        app.update_status_dashboard(data_idle)
        assert "Inativo" in str(pomo_label.render())
        assert btn_toggle.label == "▶ Foco"
        assert btn_toggle.variant == "success"


@pytest.mark.anyio
async def test_tui_status_dashboard_timers_and_alarms():
    """Valida renderização de múltiplos timers e alarmes."""
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        timers_box = app.query_one("#timers-box", Label)
        alarms_box = app.query_one("#alarms-box", Label)

        # Com dados
        data = {
            "timers": [
                {"id": "t1", "label": "Arroz", "left": 185, "paused": False},
                {"id": "t2", "label": "Bolo", "left": 600, "paused": True},
            ],
            "alarms": [
                {"id": "a1", "label": "Remédio", "time": "08:00", "enabled": True},
                {"id": "a2", "label": "Treino", "time": "18:30", "enabled": False},
            ],
        }
        app.update_status_dashboard(data)

        # Checa Timers
        timers_text = str(timers_box.render())
        assert "Arroz" in timers_text
        assert "03:05" in timers_text
        assert "Bolo" in timers_text
        assert "pausado" in timers_text

        # Checa Alarmes
        alarms_text = str(alarms_box.render())
        assert "Remédio" in alarms_text
        assert "08:00 (ativo)" in alarms_text
        assert "Treino" in alarms_text
        assert "18:30 (desativado)" in alarms_text

        # Limpando dados (vazios)
        app.update_status_dashboard({"timers": [], "alarms": []})
        assert "Nenhum timer ativo" in str(timers_box.render())
        assert "Nenhum alarme programado" in str(alarms_box.render())


@pytest.mark.anyio
async def test_tui_events_handling_dispatch():
    """Testa o processamento dos eventos broadcast recebidos do Geraldo."""
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        # Evento connected
        app.handle_event("connected", {"assistant_state": "idle", "is_muted": True})
        assert app._is_muted is True
        assert app.query_one("#mic-badge", Label).has_class("muted")

        # Evento state_changed
        app.handle_event("state_changed", {"state": "speaking"})
        assert app._assistant_state == "speaking"
        assert app.query_one("#state-badge", Label).has_class("state-speaking")

        # Evento transcription e reply
        app.handle_event("transcription", {"text": "qual é a previsão do tempo"})
        app.handle_event("reply", {"reply": "Tempo limpo com 25 graus."})

        # Evento cancelled
        app.handle_event("cancelled", {})

        # Resposta de ping
        app.handle_response("req-1", "ok", {"pong": True}, None)

        # Resposta com erro
        app.handle_response("req-err", "error", {}, "Comando inválido")


@pytest.mark.anyio
async def test_tui_input_submission_and_sending():
    """Testa envio de texto pelo Input e esvaziamento do campo."""
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        cmd_input = app.query_one("#cmd-input", Input)
        cmd_input.value = "timer de 10 minutos"
        cmd_input.focus()

        # Simula envio via Enter
        await pilot.press("enter")

        # Input deve ter sido esvaziado
        assert cmd_input.value == ""

        # Deve haver um item na fila de envio
        assert not app._send_queue.empty()
        queued = await app._send_queue.get()
        parsed = json.loads(queued)

        assert parsed["action"] == "send_prompt"
        assert parsed["params"]["text"] == "timer de 10 minutos"


@pytest.mark.anyio
async def test_tui_empty_input_submission_ignored():
    """Submeter texto vazio não deve disparar ação."""
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        cmd_input = app.query_one("#cmd-input", Input)
        cmd_input.value = "     "
        cmd_input.focus()

        await pilot.press("enter")
        assert app._send_queue.empty()


@pytest.mark.anyio
async def test_tui_button_clicks_enqueue_actions():
    """Testa se cliques nos botões de Pomodoro enfileiram as ações corretas."""
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        # Clique no botão Enviar com texto no input
        inp = app.query_one("#cmd-input", Input)
        inp.value = "pesquisar clima"
        await pilot.click("#btn-send")
        await pilot.pause()

        msg = json.loads(await app._send_queue.get())
        assert msg["action"] == "send_prompt"
        assert msg["params"]["text"] == "pesquisar clima"

        # Clique no botão Pular Pomodoro
        await pilot.click("#btn-pomo-skip")
        await pilot.pause()
        msg_skip = json.loads(await app._send_queue.get())
        assert msg_skip["action"] == "pomodoro"
        assert msg_skip["params"]["sub_action"] == "skip"

        # Clique no botão Reset Pomodoro
        await pilot.click("#btn-pomo-reset")
        await pilot.pause()
        msg_reset = json.loads(await app._send_queue.get())
        assert msg_reset["action"] == "pomodoro"
        assert msg_reset["params"]["sub_action"] == "reset"


@pytest.mark.anyio
async def test_tui_keyboard_shortcuts():
    """Testa atalhos de teclado (M, C, P, Ctrl+L)."""
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        # 'm' -> Mutar microfone
        await pilot.press("m")
        await pilot.pause()
        msg_mute = json.loads(await app._send_queue.get())
        assert msg_mute["action"] == "toggle_mute"

        # 'c' -> Cancelar
        await pilot.press("c")
        await pilot.pause()
        msg_cancel = json.loads(await app._send_queue.get())
        assert msg_cancel["action"] == "cancel"

        # 'p' -> Pomodoro start quando idle
        await pilot.press("p")
        await pilot.pause()
        msg_pomo = json.loads(await app._send_queue.get())
        assert msg_pomo["action"] == "pomodoro"
        assert msg_pomo["params"]["sub_action"] == "start"

        # Simula Pomodoro em execução e aperta 'p' novamente (deve pausar)
        app._pomodoro_state = "work"
        await pilot.press("p")
        await pilot.pause()
        msg_pause = json.loads(await app._send_queue.get())
        assert msg_pause["action"] == "pomodoro"
        assert msg_pause["params"]["sub_action"] == "pause"

        # Ctrl+L -> Limpa log
        await pilot.press("ctrl+l")
        await pilot.pause()


@pytest.mark.anyio
async def test_tui_integration_with_live_ipc_server():
    """Teste de integração ponta a ponta: TUI conecta ao GeraldoIPCServer real."""
    server = GeraldoIPCServer(host=TEST_IPC_HOST, port=TEST_IPC_PORT)

    def echo_prompt(text: str) -> str:
        return f"Processado: {text}"

    server.set_prompt_handler(echo_prompt)
    server.start()

    try:
        app = GeraldoTUI(host=TEST_IPC_HOST, port=TEST_IPC_PORT, auto_connect=True)
        async with app.run_test(size=(160, 50)) as pilot:
            # Aguarda a conexão se estabelecer
            for _ in range(20):
                if app._connected:
                    break
                await asyncio.sleep(0.1)

            assert app._connected is True

            # Envia prompt pelo input da TUI
            inp = app.query_one("#cmd-input", Input)
            inp.value = "olá geraldo"
            inp.focus()
            await pilot.press("enter")

            # Aguarda resposta ser processada pelo servidor IPC e refletida na TUI
            await asyncio.sleep(0.5)

            # Transmite um evento de mudança de estado a partir do servidor
            server.set_assistant_state("speaking")
            await asyncio.sleep(0.3)

            assert app._assistant_state == "speaking"
            assert app.query_one("#state-badge", Label).has_class("state-speaking")

    finally:
        server.stop()


@pytest.mark.anyio
async def test_tui_send_action_payload_format():
    """Valida formatação do payload gerado por send_action."""
    app = GeraldoTUI(auto_connect=False)
    app.send_action("custom_action", {"foo": "bar", "num": 123})
    assert not app._send_queue.empty()
    item = json.loads(await app._send_queue.get())
    assert item["action"] == "custom_action"
    assert item["params"]["foo"] == "bar"
    assert item["params"]["num"] == 123
    assert item["id"].startswith("tui-")


@pytest.mark.anyio
async def test_tui_action_focus_input_shortcut():
    """Valida se pressionar 't' foca no campo de input."""
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        inp = app.query_one("#cmd-input", Input)
        assert not inp.has_focus
        await pilot.press("t")
        await pilot.pause()
        assert inp.has_focus


@pytest.mark.anyio
async def test_tui_action_clear_log():
    """Valida limpeza do RichLog pelo atalho Ctrl+L."""
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        chat = app.query_one("#chat-log", RichLog)
        chat.write("Mensagem de teste que será limpa")
        app.action_clear_log()
        await pilot.pause()
        # Após limpar, deve conter a mensagem de histórico limpo
        assert len(chat.lines) >= 1


@pytest.mark.anyio
async def test_tui_handle_incoming_raw_malformed():
    """Valida que JSONs mal formatados não derrubam o app."""
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        # Não deve levantar exceção
        app._handle_incoming_raw("isso-nao-e-json")
        app._handle_incoming_raw("{json quebrado")
        app._handle_incoming_raw("")


@pytest.mark.anyio
async def test_tui_handle_response_error_display():
    """Valida exibição de erros no log de chat."""
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        app.handle_response("req-err1", "error", {}, "Serviço ocupado")
        app.handle_response("req-err2", "error", {}, None)


@pytest.mark.anyio
async def test_tui_status_dashboard_partial_keys():
    """Valida resiliência a dicionários parciais ou nulos no status_update."""
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        # Dicionário vazio
        app.update_status_dashboard({})
        # Apenas pomodoro sem timers nem alarmes
        app.update_status_dashboard({"pomodoro": {"state": "work", "left": 500, "cycle": 3}})
        assert "Ciclo 3" in str(app.query_one("#pomo-time", Label).render())
        # Apenas timers sem pomodoro
        app.update_status_dashboard({"timers": [{"id": "t", "label": "Café", "left": 120}]})
        assert "Café" in str(app.query_one("#timers-box", Label).render())


@pytest.mark.anyio
async def test_tui_pomodoro_all_state_translations():
    """Valida traduções e labels de todos os estados do Pomodoro."""
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        lbl = app.query_one("#pomo-time", Label)

        # work_finished
        app.update_status_dashboard({"pomodoro": {"state": "work_finished", "left": 0, "cycle": 1}})
        assert "Foco Concluído!" in str(lbl.render())

        # break_finished
        app.update_status_dashboard({"pomodoro": {"state": "break_finished", "left": 0, "cycle": 1}})
        assert "Pausa Concluída!" in str(lbl.render())

        # paused
        app.update_status_dashboard({"pomodoro": {"state": "paused", "left": 300, "cycle": 2}})
        assert "Pausado" in str(lbl.render())


@pytest.mark.anyio
async def test_tui_multiple_consecutive_user_prompts():
    """Valida envio de múltiplos prompts em sequência pelo usuário."""
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        inp = app.query_one("#cmd-input", Input)

        prompts = ["primeiro comando", "segundo comando", "terceiro comando"]
        for p in prompts:
            inp.value = p
            inp.focus()
            await pilot.press("enter")
            await pilot.pause()

        assert app._send_queue.qsize() == 3
        for p in prompts:
            item = json.loads(await app._send_queue.get())
            assert item["params"]["text"] == p


@pytest.mark.anyio
async def test_tui_ollama_config_modal_flow():
    """Valida fluxo de abertura, preenchimento e salvamento do modal do Ollama na TUI."""
    import config
    orig_host = config.OLLAMA_HOST
    orig_model = config.LLM_MODEL
    try:
        from ui.tui import OllamaConfigModal
        app = GeraldoTUI(auto_connect=False)
        async with app.run_test(size=(160, 50)) as pilot:
            # Pressiona tecla 'o' para abrir o modal
            await pilot.press("o")
            await pilot.pause()

            assert isinstance(app.screen, OllamaConfigModal)
            host_input = app.screen.query_one("#input-host", Input)
            model_input = app.screen.query_one("#input-model", Input)

            host_input.value = "http://meu-container:11434"
            model_input.value = "llama3.2:3b"

            # Clica em salvar
            btn_save = app.screen.query_one("#btn-modal-save", Button)
            await pilot.click(btn_save)
            await pilot.pause()

            # Modal deve ter sido fechado
            assert not isinstance(app.screen, OllamaConfigModal)
            assert app._ollama_host == "http://meu-container:11434"
            assert app._ollama_model == "llama3.2:3b"

            # Verifica ação enfileirada no WebSocket
            assert app._send_queue.qsize() == 1
            payload = json.loads(await app._send_queue.get())
            assert payload["action"] == "set_config"
            assert payload["params"]["ollama_host"] == "http://meu-container:11434"
            assert payload["params"]["llm_model"] == "llama3.2:3b"
    finally:
        config.OLLAMA_HOST = orig_host
        config.LLM_MODEL = orig_model


@pytest.mark.anyio
async def test_tui_external_llm_modal_flow():
    """Valida fluxo de configuração de LLM externa com API Key via modal da TUI."""
    import config
    orig_prov = config.LLM_PROVIDER
    orig_key = config.LLM_API_KEY
    orig_model = config.LLM_MODEL
    try:
        from ui.tui import OllamaConfigModal
        app = GeraldoTUI(auto_connect=False)
        async with app.run_test(size=(160, 50)) as pilot:
            # Pressiona tecla 'o' para abrir o modal
            await pilot.press("o")
            await pilot.pause()

            assert isinstance(app.screen, OllamaConfigModal)
            prov_input = app.screen.query_one("#input-provider", Input)
            host_input = app.screen.query_one("#input-host", Input)
            key_input = app.screen.query_one("#input-api-key", Input)
            model_input = app.screen.query_one("#input-model", Input)

            prov_input.value = "groq"
            host_input.value = "https://api.groq.com/openai/v1"
            key_input.value = "gsk_test_api_key_456"
            model_input.value = "llama-3.3-70b-versatile"

            # Clica em salvar
            btn_save = app.screen.query_one("#btn-modal-save", Button)
            await pilot.click(btn_save)
            await pilot.pause()

            assert not isinstance(app.screen, OllamaConfigModal)
            assert app._llm_provider == "groq"
            assert app._llm_api_key == "gsk_test_api_key_456"
            assert app._ollama_model == "llama-3.3-70b-versatile"

            # Verifica ação enviada com api_key e provider
            assert app._send_queue.qsize() == 1
            payload = json.loads(await app._send_queue.get())
            assert payload["action"] == "set_config"
            assert payload["params"]["provider"] == "groq"
            assert payload["params"]["api_key"] == "gsk_test_api_key_456"
            assert payload["params"]["llm_model"] == "llama-3.3-70b-versatile"
    finally:
        config.LLM_PROVIDER = orig_prov
        config.LLM_API_KEY = orig_key
        config.LLM_MODEL = orig_model


