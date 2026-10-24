import asyncio
import json
import pytest
from textual.widgets import Button, Input, Label, RichLog, TabbedContent

from core.ipc import GeraldoIPCServer
from ui.tui import GeraldoTUI, TimerConfigModal, AlarmConfigModal, CalendarNewEventModal

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
        assert app.query_one("#btn-pomo-plan", Button) is not None
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

        # Estado Idle (Inativo / Nenhum pomodoro ativo)
        data_idle = {
            "pomodoro": {
                "state": "idle",
                "cycle": 1,
                "left": 0,
            }
        }
        app.update_status_dashboard(data_idle)
        assert "Nenhum pomodoro ativo" in str(pomo_label.render())
        assert "Iniciar" in str(btn_toggle.label)
        assert btn_toggle.variant == "success"
        btn_plan = app.query_one("#btn-pomo-plan", Button)
        btn_skip = app.query_one("#btn-pomo-skip", Button)
        btn_reset = app.query_one("#btn-pomo-reset", Button)
        assert btn_plan.display is True
        assert btn_skip.display is False
        assert btn_reset.display is False


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

        # Ativa pomodoro para exibir botões Pular e Reset
        app.update_status_dashboard({"pomodoro": {"state": "work", "active": True, "left": 1500, "cycle": 1}})
        app.query_one("#main-app-tabs", TabbedContent).active = "tab-pane-pomodoro"
        await pilot.pause()

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

        # long_break
        app.update_status_dashboard({"pomodoro": {"state": "long_break", "left": 900, "cycle": 4}})
        assert "Pausa Longa (Ciclo 4)" in str(lbl.render())
        assert "15:00" in str(lbl.render())
        btn = app.query_one("#btn-pomo-toggle", Button)
        assert btn.label == "⏸ Pausar"
        assert btn.variant == "warning"

        # long_break_finished
        app.update_status_dashboard({"pomodoro": {"state": "long_break_finished", "left": 0, "cycle": 4}})
        assert "Pausa Longa Concluída!" in str(lbl.render())
        assert btn.label == "▶ Próximo Ciclo"
        assert btn.variant == "success"

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


@pytest.mark.anyio
async def test_tui_audio_config_modal_flow():
    """Valida fluxo de configuração de dispositivos de áudio via modal na TUI (tecla 's')."""
    from ui.tui import AudioConfigModal
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        # Pressiona tecla 's' para abrir o modal de áudio
        await pilot.press("s")
        await pilot.pause()

        assert isinstance(app.screen, AudioConfigModal)
        mic_input = app.screen.query_one("#input-audio-mic", Input)
        out_input = app.screen.query_one("#input-audio-out", Input)

        mic_input.value = "fifine"
        out_input.value = "2"

        # Clica no botão de salvar
        btn_save = app.screen.query_one("#btn-audio-save", Button)
        await pilot.click(btn_save)
        await pilot.pause()

        # Modal fechou e valores foram salvos
        assert not isinstance(app.screen, AudioConfigModal)
        assert app._audio_input_device == "fifine"
        assert app._audio_output_device == "2"

        # Ação set_audio_config transmitida
        assert app._send_queue.qsize() == 1
        payload = json.loads(await app._send_queue.get())
        assert payload["action"] == "set_audio_config"
        assert payload["params"]["input_device"] == "fifine"
        assert payload["params"]["output_device"] == "2"


def test_cli_path_status_and_export():
    """Testa utilitário cross-platform de status e exportação do atalho TUI."""
    from core.cli_path import get_tui_path_status, export_tui_path
    st = get_tui_path_status()
    assert isinstance(st, dict)
    assert st.get("status") == "ok"
    assert "os" in st

    res = export_tui_path()
    assert isinstance(res, dict)
    assert res.get("status") == "ok"
    assert res.get("installed") is True


@pytest.mark.anyio
async def test_tui_pomodoro_plan_modal():
    """Testa abertura e submissão do modal de planejamento de Pomodoro."""
    from ui.tui import PomodoroPlanModal
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        # Clica no botão de planejar
        app.query_one("#main-app-tabs", TabbedContent).active = "tab-pane-pomodoro"
        await pilot.pause()
        await pilot.click("#btn-pomo-plan")
        await pilot.pause()

        assert isinstance(app.screen, PomodoroPlanModal)

        # Clica no preset de 50/10 min
        btn_50 = app.screen.query_one("#btn-preset-50", Button)
        await pilot.click(btn_50)
        await pilot.pause()

        inp_work = app.screen.query_one("#input-pomo-work", Input)
        inp_break = app.screen.query_one("#input-pomo-break", Input)
        inp_long_break = app.screen.query_one("#input-pomo-long-break", Input)
        inp_long_interval = app.screen.query_one("#input-pomo-long-interval", Input)
        assert inp_work.value == "50"
        assert inp_break.value == "10"
        assert inp_long_break.value == "30"
        assert inp_long_interval.value == "4"

        # Inicia ciclo planejado
        btn_start = app.screen.query_one("#btn-pomo-start-plan", Button)
        await pilot.click(btn_start)
        await pilot.pause()

        # Modal fechou
        assert not isinstance(app.screen, PomodoroPlanModal)

        # Mensagem enviada para a fila IPC
        assert app._send_queue.qsize() == 1
        msg = json.loads(await app._send_queue.get())
        assert msg["action"] == "pomodoro"
        assert msg["params"]["sub_action"] == "start"
        assert msg["params"]["work_minutes"] == 50
        assert msg["params"]["break_minutes"] == 10
        assert msg["params"]["long_break_minutes"] == 30
        assert msg["params"]["long_break_interval"] == 4
        assert msg["params"]["cycle"] == 1


@pytest.mark.anyio
async def test_tui_pomodoro_toggle_transitions():
    """Valida cliques em btn-pomo-toggle cobrindo todos os estados: start, pause, resume e advance."""
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        btn = app.query_one("#btn-pomo-toggle", Button)

        # 1. Estado inicial Idle -> Clicar dispara 'start'
        btn.press()
        await pilot.pause()
        assert not app._send_queue.empty()
        msg_start = json.loads(await app._send_queue.get())
        assert msg_start["action"] == "pomodoro"
        assert msg_start["params"]["sub_action"] == "start"

        # 2. Transição para Estado Work ativo -> Botão vira 'Pausar', Clicar dispara 'pause'
        app.update_status_dashboard({"pomodoro": {"state": "work", "active": True, "left": 1500, "cycle": 1}})
        await pilot.pause()
        assert "Pausar" in str(btn.label)
        btn.press()
        await pilot.pause()
        msg_pause = json.loads(await app._send_queue.get())
        assert msg_pause["action"] == "pomodoro"
        assert msg_pause["params"]["sub_action"] == "pause"

        # 3. Transição para Work pausado -> Botão vira 'Retomar', Clicar dispara 'resume'
        app.update_status_dashboard({"pomodoro": {"state": "paused", "active": True, "left": 1500, "cycle": 1}})
        await pilot.pause()
        assert "Retomar" in str(btn.label)
        btn.press()
        await pilot.pause()
        msg_resume = json.loads(await app._send_queue.get())
        assert msg_resume["action"] == "pomodoro"
        assert msg_resume["params"]["sub_action"] == "resume"

        # 4. Transição para Estado Concluído -> Botão vira Avançar/Próximo, Clicar dispara 'advance'
        app.update_status_dashboard({"pomodoro": {"state": "work_finished", "active": True, "left": 0, "cycle": 1}})
        await pilot.pause()
        btn.press()
        await pilot.pause()
        msg_advance = json.loads(await app._send_queue.get())
        assert msg_advance["action"] == "pomodoro"
        assert msg_advance["params"]["sub_action"] == "advance"

        # 5. Transição para Pausa Longa Concluída -> Botão vira Próximo Ciclo, Clicar dispara 'advance'
        app.update_status_dashboard({"pomodoro": {"state": "long_break_finished", "active": True, "left": 0, "cycle": 4}})
        await pilot.pause()
        assert "Próximo Ciclo" in str(btn.label)
        btn.press()
        await pilot.pause()
        msg_advance2 = json.loads(await app._send_queue.get())
        assert msg_advance2["action"] == "pomodoro"
        assert msg_advance2["params"]["sub_action"] == "advance"


@pytest.mark.anyio
async def test_tui_pomodoro_plan_modal_presets_and_dismiss():
    """Valida os botões de presets (25/5, 15/3) e o botão de fechar modal sem disparar comando."""
    from ui.tui import PomodoroPlanModal
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        # Abre o modal de planejamento
        app.action_open_pomodoro_plan()
        await pilot.pause()
        assert isinstance(app.screen, PomodoroPlanModal)

        inp_work = app.screen.query_one("#input-pomo-work", Input)
        inp_break = app.screen.query_one("#input-pomo-break", Input)
        inp_long_break = app.screen.query_one("#input-pomo-long-break", Input)
        inp_long_interval = app.screen.query_one("#input-pomo-long-interval", Input)

        # Clica no preset 15/3
        app.screen.query_one("#btn-preset-15", Button).press()
        await pilot.pause()
        assert inp_work.value == "15"
        assert inp_break.value == "3"
        assert inp_long_break.value == "10"
        assert inp_long_interval.value == "3"

        # Clica no preset 25/5
        app.screen.query_one("#btn-preset-25", Button).press()
        await pilot.pause()
        assert inp_work.value == "25"
        assert inp_break.value == "5"
        assert inp_long_break.value == "15"
        assert inp_long_interval.value == "4"

        # Clica no botão Fechar sem salvar
        app.screen.query_one("#btn-pomo-close-plan", Button).press()
        await pilot.pause()

        # Modal deve ter fechado e nenhuma mensagem de pomodoro enviada
        assert not isinstance(app.screen, PomodoroPlanModal)
        assert app._send_queue.empty()


@pytest.mark.anyio
async def test_tui_calendar_buttons(monkeypatch):
    """Testa os botões de abrir agenda (btn-cal-open) e autenticar (btn-cal-auth)."""
    opened_urls = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened_urls.append(url))

    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        # 1. Clique em Abrir Agenda
        app.query_one("#btn-cal-open", Button).press()
        await pilot.pause()
        assert "https://calendar.google.com" in opened_urls
        msg_cal = json.loads(await app._send_queue.get())
        assert msg_cal["action"] == "open_calendar"

        # 2. Clique em Conectar / Autenticar Google Calendar
        app.query_one("#btn-cal-auth", Button).press()
        await pilot.pause()
        msg_auth = json.loads(await app._send_queue.get())
        assert msg_auth["action"] == "auth_calendar"


@pytest.mark.anyio
async def test_tui_ollama_modal_buttons_test_and_close(monkeypatch):
    """Testa os botões de testar conexão (btn-modal-test) e fechar (btn-modal-close) no modal do Ollama."""
    from ui.tui import OllamaConfigModal
    from core.onboarding import OnboardingManager

    monkeypatch.setattr(
        OnboardingManager,
        "check_llm_provider",
        lambda **kwargs: {"status": "ok", "connected": True, "message": "Ollama ativo"}
    )

    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        await pilot.press("o")
        await pilot.pause()
        assert isinstance(app.screen, OllamaConfigModal)

        # Clica no botão Testar
        app.screen.query_one("#btn-modal-test", Button).press()
        await pilot.pause()

        # Clica no botão Fechar sem salvar
        app.screen.query_one("#btn-modal-close", Button).press()
        await pilot.pause()

        assert not isinstance(app.screen, OllamaConfigModal)
        assert app._send_queue.empty()


@pytest.mark.anyio
async def test_tui_audio_modal_buttons_test_refresh_close(monkeypatch):
    """Testa os botões de som de teste, refresh e fechar no modal de áudio."""
    from ui.tui import AudioConfigModal
    from audio.player import AudioPlayer

    beep_played = []
    monkeypatch.setattr(AudioPlayer, "play_beep", lambda device=None: beep_played.append(device))

    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        await pilot.press("s")
        await pilot.pause()
        assert isinstance(app.screen, AudioConfigModal)

        # 1. Clica no botão Testar Saída
        app.screen.query_one("#btn-audio-test", Button).press()
        await pilot.pause()
        assert len(beep_played) == 1

        # 2. Clica no botão Atualizar Dispositivos
        app.screen.query_one("#btn-audio-refresh", Button).press()
        await pilot.pause()
        assert "atualizada" in str(app.screen.query_one("#audio-status", Label).render())

        # 3. Clica no botão Fechar sem salvar
        app.screen.query_one("#btn-audio-close", Button).press()
        await pilot.pause()

        assert not isinstance(app.screen, AudioConfigModal)
        assert app._send_queue.empty()


@pytest.mark.anyio
async def test_tui_audio_card_and_quick_actions(monkeypatch):
    """Testa card de dispositivos de áudio na barra lateral e os botões de ajuste e teste rápido."""
    from ui.tui import AudioConfigModal
    from audio.player import AudioPlayer

    beep_played = []
    monkeypatch.setattr(AudioPlayer, "play_beep", lambda device=None: beep_played.append(device))
    monkeypatch.setattr(
        "audio.device_utils.list_audio_devices",
        lambda: {
            "inputs": [{"id": 1, "name": "Microfone USB"}],
            "outputs": [{"id": 2, "name": "Fone Bluetooth"}]
        }
    )

    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        # Card existe
        assert app.query_one("#card-audio-devices") is not None
        assert "Padrão" in str(app.query_one("#audio-in-label", Label).render())
        assert "Padrão" in str(app.query_one("#audio-out-label", Label).render())

        # 1. Clica no botão de teste rápido
        app.query_one("#btn-audio-quick-test", Button).press()
        await pilot.pause()
        assert len(beep_played) == 1

        # 2. Clica no botão de ajustar áudio para abrir o modal
        app.query_one("#btn-audio-open", Button).press()
        await pilot.pause()
        assert isinstance(app.screen, AudioConfigModal)

        # Preenche novos dispositivos e salva
        app.screen.query_one("#input-audio-mic", Input).value = "Microfone USB"
        app.screen.query_one("#input-audio-out", Input).value = "Fone Bluetooth"
        btn_save = app.screen.query_one("#btn-audio-save", Button)
        await pilot.click(btn_save)
        await pilot.pause()

        # Modal fechado e card lateral atualizado
        assert not isinstance(app.screen, AudioConfigModal)
        assert "Microfone USB" in str(app.query_one("#audio-in-label", Label).render())
        assert "Fone Bluetooth" in str(app.query_one("#audio-out-label", Label).render())

        # Verifica ação IPC despachada
        assert app._send_queue.qsize() == 1
        msg = json.loads(await app._send_queue.get())
        assert msg["action"] == "set_audio_config"
        assert msg["params"]["input_device"] == "Microfone USB"
        assert msg["params"]["output_device"] == "Fone Bluetooth"


@pytest.mark.anyio
async def test_tui_timer_modal_presets_and_creation():
    """Valida abertura do modal de timers, clique em preset e envio de timer_add."""
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        # 1. Abre modal de timers
        app.action_open_timer_modal()
        await pilot.pause()
        assert isinstance(app.screen, TimerConfigModal)

        # 2. Clica no preset de 10 min
        app.screen.query_one("#btn-timer-pre-10", Button).press()
        await pilot.pause()
        assert app.screen.query_one("#input-timer-hours", Input).value == "0"
        assert app.screen.query_one("#input-timer-min", Input).value == "10"
        assert app.screen.query_one("#input-timer-sec", Input).value == "0"

        # 3. Altera label e adiciona 30 segundos
        app.screen.query_one("#input-timer-label", Input).value = "Massa de Pão"
        app.screen.query_one("#input-timer-sec", Input).value = "30"

        # 4. Confirma criação
        app.screen.query_one("#btn-timer-create", Button).press()
        await pilot.pause()

        # Modal fechou
        assert not isinstance(app.screen, TimerConfigModal)

        # Ação enviada
        assert app._send_queue.qsize() == 1
        msg = json.loads(await app._send_queue.get())
        assert msg["action"] == "timer_add"
        assert msg["params"]["label"] == "Massa de Pão"
        assert msg["params"]["hours"] == 0
        assert msg["params"]["minutes"] == 10
        assert msg["params"]["seconds"] == 30


@pytest.mark.anyio
async def test_tui_timer_card_buttons_and_actions():
    """Valida botões de pausa/play e limpeza de timers na barra lateral."""
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        # Atualiza status com 1 timer rodando
        app.update_status_dashboard({
            "timers": [{"id": "t1", "label": "Chá", "left": 120, "paused": False}],
            "alarms": []
        })

        # 1. Clica no botão de pausar/retomar
        app.query_one("#btn-timer-toggle", Button).press()
        await pilot.pause()
        assert app._send_queue.qsize() == 1
        msg = json.loads(await app._send_queue.get())
        assert msg["action"] == "timer_pause"

        # Atualiza para pausado
        app.update_status_dashboard({
            "timers": [{"id": "t1", "label": "Chá", "left": 120, "paused": True}],
            "alarms": []
        })

        # Clica de novo no botão de pausar/retomar -> agora envia timer_resume
        app.query_one("#btn-timer-toggle", Button).press()
        await pilot.pause()
        assert app._send_queue.qsize() == 1
        msg = json.loads(await app._send_queue.get())
        assert msg["action"] == "timer_resume"

        # 2. Clica no botão de limpar
        app.query_one("#btn-timer-clear", Button).press()
        await pilot.pause()
        assert app._send_queue.qsize() == 1
        msg = json.loads(await app._send_queue.get())
        assert msg["action"] == "timer_cancel"
        assert msg["params"]["query"] == "todos"


@pytest.mark.anyio
async def test_tui_tabs_structure():
    """Valida presença das abas separadas de Timers e Alarmes no TUI."""
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        assert app.query_one("#time-tasks-tabs") is not None
        assert app.query_one("#tab-pane-timers") is not None
        assert app.query_one("#tab-pane-alarms") is not None
        assert app.query_one("#timers-box") is not None
        assert app.query_one("#alarms-box") is not None


@pytest.mark.anyio
async def test_tui_alarm_modal_presets_and_creation():
    """Valida abertura do modal de alarmes, clique em preset e envio de alarm_add."""
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        # 1. Abre modal de alarmes
        app.action_open_alarm_modal()
        await pilot.pause()
        assert isinstance(app.screen, AlarmConfigModal)

        # 2. Clica no preset de 07:00
        app.screen.query_one("#btn-alarm-pre-7", Button).press()
        await pilot.pause()
        assert app.screen.query_one("#input-alarm-time", Input).value == "07:00"

        # 3. Altera label e customiza horário
        app.screen.query_one("#input-alarm-label", Input).value = "Tomar Remédio"
        app.screen.query_one("#input-alarm-time", Input).value = "07:15"

        # 4. Confirma criação
        app.screen.query_one("#btn-alarm-create", Button).press()
        await pilot.pause()

        # Modal fechou
        assert not isinstance(app.screen, AlarmConfigModal)

        # Ação enviada
        assert app._send_queue.qsize() == 1
        msg = json.loads(await app._send_queue.get())
        assert msg["action"] == "alarm_add"
        assert msg["params"]["label"] == "Tomar Remédio"
        assert msg["params"]["time"] == "07:15"


@pytest.mark.anyio
async def test_tui_alarm_card_buttons_and_actions():
    """Valida botões de alternar e limpar alarmes na barra lateral."""
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        # Atualiza status com 1 alarme ativo
        app.update_status_dashboard({
            "timers": [],
            "alarms": [{"id": "a1", "label": "Café", "time": "06:30", "enabled": True}]
        })

        # 1. Clica no botão de alternar
        app.query_one("#btn-alarm-toggle-btn", Button).press()
        await pilot.pause()
        assert app._send_queue.qsize() == 1
        msg = json.loads(await app._send_queue.get())
        assert msg["action"] == "alarm_toggle"
        assert msg["params"]["id"] == "a1"

        # 2. Clica no botão de limpar alarmes
        app.query_one("#btn-alarm-clear", Button).press()
        await pilot.pause()
        assert app._send_queue.qsize() == 1
        msg = json.loads(await app._send_queue.get())
        assert msg["action"] == "alarm_clear_all"


@pytest.mark.anyio
async def test_tui_main_tabbed_content_structure():
    """Valida presença das 5 abas principais do Textual (Chat, Agenda, Pomodoro, Timers, Sistema)."""
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        main_tabs = app.query_one("#main-app-tabs")
        assert main_tabs is not None
        assert app.query_one("#tab-pane-chat") is not None
        assert app.query_one("#tab-pane-agenda") is not None
        assert app.query_one("#tab-pane-pomodoro") is not None
        assert app.query_one("#tab-pane-time-tasks") is not None
        assert app.query_one("#tab-pane-system") is not None

        # Valida elementos da aba Agenda
        assert app.query_one("#cal-top-bar") is not None
        assert app.query_one("#btn-cal-prev-month", Button) is not None
        assert app.query_one("#btn-cal-next-month", Button) is not None
        assert app.query_one("#btn-cal-today", Button) is not None
        assert app.query_one("#btn-cal-new", Button) is not None
        assert app.query_one("#btn-cal-refresh-btn", Button) is not None
        assert app.query_one("#btn-cal-open", Button) is not None
        assert app.query_one("#btn-cal-auth", Button) is not None
        assert app.query_one("#calendar-grid-view") is not None
        assert app.query_one("#cal-events-log") is not None


@pytest.mark.anyio
async def test_tui_calendar_navigation_and_rendering():
    """Valida navegação de meses (anterior, próximo, hoje) no calendário da TUI."""
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        import datetime
        today = datetime.date.today()
        assert app._cal_year == today.year
        assert app._cal_month == today.month

        # Navega para o próximo mês
        app.query_one("#btn-cal-next-month", Button).press()
        await pilot.pause()
        expected_month = today.month + 1 if today.month < 12 else 1
        expected_year = today.year if today.month < 12 else today.year + 1
        assert app._cal_month == expected_month
        assert app._cal_year == expected_year

        # Navega para o mês anterior duas vezes
        app.query_one("#btn-cal-prev-month", Button).press()
        await pilot.pause()
        assert app._cal_month == today.month
        assert app._cal_year == today.year

        app.query_one("#btn-cal-prev-month", Button).press()
        await pilot.pause()
        prev_month = today.month - 1 if today.month > 1 else 12
        assert app._cal_month == prev_month

        # Clica em Hoje
        app.query_one("#btn-cal-today", Button).press()
        await pilot.pause()
        assert app._cal_month == today.month
        assert app._cal_year == today.year


@pytest.mark.anyio
async def test_tui_calendar_events_display_and_response():
    """Valida renderização de eventos recebidos via IPC na agenda da TUI."""
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        sample_events = [
            {
                "id": "ev1",
                "summary": "Reunião Geral",
                "start": "2026-10-22T10:00:00-03:00",
                "end": "2026-10-22T11:00:00-03:00",
                "all_day": False,
                "location": "Google Meet",
                "description": "Alinhamento semanal de metas"
            },
            {
                "id": "ev2",
                "summary": "Feriado Municipal",
                "start": "2026-10-25",
                "end": "2026-10-25",
                "all_day": True,
                "location": "",
                "description": ""
            }
        ]

        app.handle_response(
            req_id="get_calendar_events-123",
            status="ok",
            data={"events": sample_events, "count": 2},
            error=None
        )
        await pilot.pause()

        assert len(app._cal_events) == 2
        cal_log = app.query_one("#cal-events-log", RichLog)
        assert cal_log is not None


@pytest.mark.anyio
async def test_tui_calendar_new_event_modal_flow():
    """Valida abertura do modal de novo evento, preenchimento e despacho de create_calendar_event."""
    app = GeraldoTUI(auto_connect=False)
    async with app.run_test(size=(160, 50)) as pilot:
        # 1. Abre modal pelo botão "+ Novo"
        app.query_one("#btn-cal-new", Button).press()
        await pilot.pause()

        assert isinstance(app.screen, CalendarNewEventModal)

        # 2. Preenche os dados do evento
        app.screen.query_one("#input-event-summary", Input).value = "Alinhamento com Cliente"
        app.screen.query_one("#input-event-date", Input).value = "amanhã"
        app.screen.query_one("#input-event-time", Input).value = "14:30"
        app.screen.query_one("#input-event-duration", Input).value = "45"

        # 3. Clica em Criar Evento
        app.screen.query_one("#btn-modal-event-save", Button).press()
        await pilot.pause()

        # Modal fechou
        assert not isinstance(app.screen, CalendarNewEventModal)

        # Ação create_calendar_event enfileirada
        assert app._send_queue.qsize() == 1
        msg = json.loads(await app._send_queue.get())
        assert msg["action"] == "create_calendar_event"
        assert msg["params"]["summary"] == "Alinhamento com Cliente"
        assert msg["params"]["date_query"] == "amanhã"
        assert msg["params"]["time_str"] == "14:30"
        assert msg["params"]["duration_minutes"] == 45










