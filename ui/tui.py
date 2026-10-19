import asyncio
import json
import time
from typing import Any, Dict, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, RichLog, Static

CSS = """
Screen {
    background: #0b0f19;
    color: #e2e8f0;
}

#top-bar {
    height: 3;
    background: #111827;
    border-bottom: solid #1f2937;
    padding: 0 1;
    align-vertical: middle;
}

#title-label {
    width: 26;
    color: #38bdf8;
    text-style: bold;
    content-align: left middle;
}

#conn-badge {
    width: 32;
    color: #ef4444;
    content-align: left middle;
}

#conn-badge.connected {
    color: #10b981;
}

#state-badge {
    width: 18;
    color: #94a3b8;
    background: #1e293b;
    border: none;
    text-align: center;
    content-align: center middle;
    text-style: bold;
}

#state-badge.state-listening {
    color: #0b0f19;
    background: #fbbf24;
}

#state-badge.state-thinking {
    color: #ffffff;
    background: #8b5cf6;
}

#state-badge.state-speaking {
    color: #ffffff;
    background: #ec4899;
}

#mic-badge {
    width: 14;
    color: #10b981;
    background: #064e3b;
    text-align: center;
    content-align: center middle;
    text-style: bold;
    margin-left: 1;
}

#mic-badge.muted {
    color: #ffffff;
    background: #991b1b;
}

#main-container {
    height: 1fr;
}

#chat-pane {
    width: 65%;
    height: 100%;
    border-right: solid #1f2937;
    padding: 0 1;
}

#chat-title {
    height: 1;
    color: #64748b;
    text-style: bold;
    margin-bottom: 1;
}

#chat-log {
    height: 1fr;
    background: #0f172a;
    border: round #1e293b;
    padding: 1;
}

#side-pane {
    width: 35%;
    height: 100%;
    padding: 0 1;
}

.side-card {
    background: #111827;
    border: round #1f2937;
    padding: 1;
    margin-bottom: 1;
}

.card-title {
    color: #93c5fd;
    text-style: bold;
    margin-bottom: 1;
}

#pomo-time {
    color: #f59e0b;
    text-style: bold;
    text-align: center;
    height: 2;
    content-align: center middle;
}

#pomo-buttons {
    height: 3;
    align: center middle;
}

#pomo-buttons Button {
    margin: 0 1;
    min-width: 8;
}

#timers-box {
    min-height: 4;
}

#alarms-box {
    min-height: 3;
}

#input-bar {
    height: 3;
    background: #111827;
    border-top: solid #1f2937;
    padding: 0 1;
    align-vertical: middle;
}

#cmd-input {
    width: 1fr;
    background: #1e293b;
    border: none;
    color: #f8fafc;
}

#cmd-input:focus {
    border: tall #38bdf8;
}

#btn-send {
    margin-left: 1;
    min-width: 10;
}

OllamaConfigModal {
    align: center middle;
    background: rgba(0, 0, 0, 0.75);
}

#ollama-dialog {
    width: 68;
    height: auto;
    background: #111827;
    border: round #38bdf8;
    padding: 1 2;
}

#ollama-title {
    color: #38bdf8;
    text-style: bold;
    text-align: center;
    margin-bottom: 1;
}

.form-label {
    color: #94a3b8;
    text-style: bold;
    margin-top: 1;
}

.form-hint {
    color: #64748b;
    margin-bottom: 1;
}

#input-host, #input-model, #input-provider, #input-api-key {
    background: #1e293b;
    border: none;
    color: #f8fafc;
    margin-bottom: 1;
}

#input-host:focus, #input-model:focus, #input-provider:focus, #input-api-key:focus {
    border: tall #38bdf8;
}

#test-status {
    height: auto;
    margin: 1 0;
    padding: 0 1;
    color: #e2e8f0;
}

#modal-buttons {
    height: 3;
    align: right middle;
    margin-top: 1;
}

#modal-buttons Button {
    margin-left: 1;
    min-width: 12;
}
"""


class OllamaConfigModal(ModalScreen):
    """Modal para configuração e teste do container/host do Ollama ou LLM externa no Geraldo."""

    def __init__(
        self,
        current_host: str = "http://localhost:11434",
        current_model: str = "qwen2.5:3b",
        current_provider: str = "ollama",
        current_api_key: str = "",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.current_host = current_host
        self.current_model = current_model
        self.current_provider = current_provider
        self.current_api_key = current_api_key

    def compose(self) -> ComposeResult:
        with Vertical(id="ollama-dialog"):
            yield Label("⚙️ Configurações de IA (Ollama / LLM Externa)", id="ollama-title")

            yield Label("Provedor (ollama, groq, openai, openrouter, gemini, custom):", classes="form-label")
            yield Input(value=self.current_provider, placeholder="ollama", id="input-provider")

            yield Label("Host / URL do Endpoint:", classes="form-label")
            yield Input(value=self.current_host, placeholder="http://localhost:11434", id="input-host")
            yield Label("Ex: http://localhost:11434 ou https://api.groq.com/openai/v1", classes="form-hint")

            yield Label("API Key (necessário para Groq, OpenAI, etc.):", classes="form-label")
            yield Input(value=self.current_api_key, placeholder="sk-... ou gsk_...", id="input-api-key", password=True)

            yield Label("Modelo LLM:", classes="form-label")
            yield Input(value=self.current_model, placeholder="qwen2.5:3b", id="input-model")

            yield Label("Status: Pronto para testar conexão ou salvar.", id="test-status")

            with Horizontal(id="modal-buttons"):
                yield Button("🔍 Testar", id="btn-modal-test", variant="default")
                yield Button("💾 Salvar", id="btn-modal-save", variant="primary")
                yield Button("✕ Fechar", id="btn-modal-close", variant="error")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "btn-modal-close":
            self.dismiss(False)
        elif button_id == "btn-modal-save":
            provider = self.query_one("#input-provider", Input).value.strip().lower() or "ollama"
            host = self.query_one("#input-host", Input).value.strip() or "http://localhost:11434"
            model = self.query_one("#input-model", Input).value.strip() or "qwen2.5:3b"
            api_key = self.query_one("#input-api-key", Input).value.strip()
            if hasattr(self.app, "save_ollama_config"):
                self.app.save_ollama_config(host=host, model=model, provider=provider, api_key=api_key)
            self.dismiss(True)
        elif button_id == "btn-modal-test":
            provider = self.query_one("#input-provider", Input).value.strip().lower() or "ollama"
            host = self.query_one("#input-host", Input).value.strip() or "http://localhost:11434"
            model = self.query_one("#input-model", Input).value.strip() or "qwen2.5:3b"
            api_key = self.query_one("#input-api-key", Input).value.strip()
            status_lbl = self.query_one("#test-status", Label)
            status_lbl.update(f"[bold yellow]⏳ Verificando {provider.upper()}...[/]")
            self.run_worker(
                self._async_test_llm(provider, host, model, api_key),
                exclusive=True,
                name="test_llm",
            )

    async def _async_test_llm(self, provider: str, host: str, model: str, api_key: str) -> None:
        from core.onboarding import OnboardingManager
        import asyncio

        res = await asyncio.to_thread(
            OnboardingManager.check_llm_provider,
            provider=provider,
            host=host,
            model=model,
            api_key=api_key,
            timeout=4.0,
        )
        status_lbl = self.query_one("#test-status", Label)
        if res.get("status") == "ok":
            models = res.get("available_models", [])
            m_str = ", ".join(models[:3]) + (f" (+{len(models)-3})" if len(models) > 3 else "")
            status_lbl.update(f"[bold green]✅ Conectado![/] {res.get('message')} Modelos: [cyan]{m_str or model}[/]")
        else:
            status_lbl.update(f"[bold red]❌ Erro:[/] {res.get('message', 'Inacessível')}")

    async def _async_test_ollama(self, host: str) -> None:
        await self._async_test_llm("ollama", host, "qwen2.5:3b", "")


class GeraldoTUI(App):
    """
    Interface Rica de Terminal (TUI) para o assistente Geraldo.
    Conecta-se ao barramento WebSocket (127.0.0.1:8765) para visualização e controle remoto.
    """

    CSS = CSS
    TITLE = "Geraldo Voice Assistant"

    BINDINGS = [
        Binding("m", "toggle_mute", "Mutar/Desmutar", show=True),
        Binding("p", "toggle_pomodoro", "Pomodoro Iniciar/Pausar", show=True),
        Binding("c", "cancel_action", "Cancelar/Silenciar", show=True),
        Binding("o", "open_ollama_settings", "Configurar Ollama", show=True),
        Binding("t", "focus_input", "Digitar Comando", show=True),
        Binding("ctrl+l", "clear_log", "Limpar Histórico", show=True),
        Binding("q", "quit", "Sair", show=True),
    ]

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        token: Optional[str] = None,
        auto_connect: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.host = host
        self.port = port
        self.token = token
        self.auto_connect = auto_connect

        self._connected = False
        self._is_muted = False
        self._assistant_state = "idle"
        self._pomodoro_state = "idle"
        self._pomodoro_cycle = 1
        self._llm_provider = "ollama"
        self._ollama_host = "http://localhost:11434"
        self._ollama_model = "qwen2.5:3b"
        self._llm_api_key = ""
        self._llm_api_base = ""

        self._send_queue: asyncio.Queue = asyncio.Queue()
        self._ws_worker_task = None
        self._last_user_prompt = None

    def compose(self) -> ComposeResult:
        with Horizontal(id="top-bar"):
            yield Label("🎙️ GERALDO ASSISTANT", id="title-label")
            yield Label("🔴 Desconectado", id="conn-badge")
            yield Label("[IDLE]", id="state-badge", markup=False)
            yield Label("🎤 ATIVO", id="mic-badge")

        with Horizontal(id="main-container"):
            with Vertical(id="chat-pane"):
                yield Label("HISTÓRICO DE COMANDOS & RESPOSTAS", id="chat-title")
                yield RichLog(id="chat-log", highlight=True, markup=True, wrap=True)

            with VerticalScroll(id="side-pane"):
                with Vertical(classes="side-card"):
                    yield Label("🍅 POMODORO", classes="card-title")
                    yield Label("Inativo (Ciclo 1) — 25:00", id="pomo-time")
                    with Horizontal(id="pomo-buttons"):
                        yield Button("▶ Foco", id="btn-pomo-toggle", variant="success")
                        yield Button("⏭ Pular", id="btn-pomo-skip")
                        yield Button("🔄 Reset", id="btn-pomo-reset")

                with Vertical(classes="side-card"):
                    yield Label("⏱️ TIMERS ATIVOS", classes="card-title")
                    yield Label("Nenhum timer ativo", id="timers-box")

                with Vertical(classes="side-card"):
                    yield Label("⏰ ALARMES PROGRAMADOS", classes="card-title")
                    yield Label("Nenhum alarme programado", id="alarms-box")

        with Horizontal(id="input-bar"):
            yield Input(
                placeholder='Digite um comando e aperte [Enter] (ex: "timer de 5 minutos", "minha agenda")...',
                id="cmd-input",
            )
            yield Button("Enviar", id="btn-send", variant="primary")

        yield Footer()

    async def on_mount(self) -> None:
        chat = self.query_one("#chat-log", RichLog)
        chat.write("[bold cyan]═════════════════════════════════════════════════════════════════[/]")
        chat.write("[bold cyan]  Bem-vindo à TUI do Geraldo! Conectando ao barramento IPC...   [/]")
        chat.write("[bold cyan]═════════════════════════════════════════════════════════════════[/]\n")

        if self.auto_connect:
            self.run_worker(self._ws_loop, exclusive=True, name="ws_worker")

    async def _ws_loop(self) -> None:
        """Loop de conexão contínuo com reconexão automática."""
        from websockets.asyncio.client import connect

        uri = f"ws://{self.host}:{self.port}"
        while True:
            try:
                self.update_connection_status(False, "Conectando...")
                async with connect(uri) as ws:
                    self.update_connection_status(True, f"🟢 Conectado ({self.host}:{self.port})")
                    self.send_action("get_config")

                    # Autenticação se houver token
                    if self.token:
                        auth_cmd = {"action": "auth", "token": self.token}
                        await ws.send(json.dumps(auth_cmd))

                    # Worker de envio concorrente
                    sender_task = asyncio.create_task(self._send_loop(ws))

                    try:
                        async for raw in ws:
                            self._handle_incoming_raw(raw)
                    finally:
                        sender_task.cancel()

            except Exception as e:
                self.update_connection_status(False, f"🔴 Desconectado ({e.__class__.__name__})")
                await asyncio.sleep(2.0)

    async def _send_loop(self, ws) -> None:
        """Consome a fila de envio e despacha mensagens para o WebSocket."""
        while True:
            msg = await self._send_queue.get()
            try:
                await ws.send(msg)
            except Exception:
                break

    def send_action(self, action: str, params: Optional[dict] = None) -> None:
        """Enfileira um comando RPC para envio via WebSocket."""
        payload = {
            "id": f"tui-{int(time.time()*1000)}",
            "action": action,
            "params": params or {},
        }
        self._send_queue.put_nowait(json.dumps(payload, ensure_ascii=False))

    def _handle_incoming_raw(self, raw_message: str) -> None:
        try:
            msg = json.loads(raw_message)
        except Exception:
            return

        msg_type = msg.get("type")
        if msg_type == "event":
            self.handle_event(msg.get("event"), msg.get("data", {}))
        elif msg_type == "response":
            self.handle_response(msg.get("id"), msg.get("status"), msg.get("data", {}), msg.get("error"))

    def handle_event(self, event_name: str, data: dict) -> None:
        """Processa eventos broadcast do Geraldo."""
        chat = self.query_one("#chat-log", RichLog)

        if event_name == "connected":
            state = data.get("assistant_state", "idle")
            muted = data.get("is_muted", False)
            self.update_state_badge(state)
            self.update_mic_badge(muted)
            cfg = data.get("config", {})
            if cfg:
                self._ollama_host = cfg.get("ollama_host", self._ollama_host)
                self._ollama_model = cfg.get("llm_model", self._ollama_model)

        elif event_name == "config_changed":
            self._ollama_host = data.get("ollama_host", self._ollama_host)
            self._ollama_model = data.get("llm_model", self._ollama_model)
            chat.write(f"[bold cyan]⚙️ Configuração atualizada:[/] Ollama em {self._ollama_host} ({self._ollama_model})\n")

        elif event_name == "state_changed":
            state = data.get("state", "idle")
            self.update_state_badge(state)

        elif event_name == "mute_changed":
            muted = data.get("muted", False)
            self.update_mic_badge(muted)

        elif event_name == "transcription":
            text = data.get("text", "")
            if text:
                chat.write(f"[bold cyan]👤 [Voz] Você:[/] {text}")

        elif event_name in ("reply", "reply_generated"):
            reply = data.get("reply") or data.get("text")
            if reply:
                chat.write(f"[bold green]🎙️ Geraldo:[/] {reply}\n")

        elif event_name == "status_update":
            self.update_status_dashboard(data)

        elif event_name == "cancelled":
            chat.write("[bold yellow]⚡ Ação / som cancelado.[/]")

    def handle_response(self, req_id: str, status: str, data: dict, error: Optional[str]) -> None:
        """Processa respostas RPC enviadas pelo Geraldo."""
        chat = self.query_one("#chat-log", RichLog)
        if status == "ok":
            reply = data.get("reply")
            if reply and not reply.startswith("Nenhum processador"):
                # Se ainda não logou como evento
                pass
            if data.get("pong"):
                chat.write("[dim italic]📡 Ping respondido com sucesso (Pong).[/]")
            if data.get("ollama_host"):
                self._ollama_host = data.get("ollama_host", self._ollama_host)
                self._ollama_model = data.get("llm_model", self._ollama_model)
        else:
            chat.write(f"[bold red]❌ Erro no comando:[/] {error or 'Falha desconhecida'}")

    def update_connection_status(self, connected: bool, text: str) -> None:
        self._connected = connected
        badge = self.query_one("#conn-badge", Label)
        badge.update(text)
        if connected:
            badge.add_class("connected")
        else:
            badge.remove_class("connected")

    def update_state_badge(self, state: str) -> None:
        self._assistant_state = state
        badge = self.query_one("#state-badge", Label)

        badge.remove_class("state-listening")
        badge.remove_class("state-thinking")
        badge.remove_class("state-speaking")

        labels = {
            "idle": "[IDLE]",
            "listening": "[OUVINDO]",
            "transcribing": "[TRANSCR.]",
            "thinking": "[PENSANDO]",
            "speaking": "[FALANDO]",
            "starting": "[INICIANDO]",
        }
        badge.update(labels.get(state, f"[{state.upper()}]"))

        if state == "listening":
            badge.add_class("state-listening")
        elif state in ("thinking", "transcribing"):
            badge.add_class("state-thinking")
        elif state == "speaking":
            badge.add_class("state-speaking")

    def update_mic_badge(self, is_muted: bool) -> None:
        self._is_muted = is_muted
        badge = self.query_one("#mic-badge", Label)
        if is_muted:
            badge.update("🔇 MUDO")
            badge.add_class("muted")
        else:
            badge.update("🎤 ATIVO")
            badge.remove_class("muted")

    def update_status_dashboard(self, data: dict) -> None:
        """Atualiza os cards laterais de Pomodoro, Timers e Alarmes."""
        # 1. Pomodoro
        pomo = data.get("pomodoro", {})
        if pomo:
            p_state = pomo.get("state", "idle")
            p_cycle = pomo.get("cycle", 1)
            p_left = pomo.get("left", 1500)
            self._pomodoro_state = p_state
            self._pomodoro_cycle = p_cycle

            m, s = divmod(p_left, 60)
            state_pt = {
                "work": "Foco",
                "break": "Pausa",
                "idle": "Inativo",
                "paused": "Pausado",
                "work_finished": "Foco Concluído!",
                "break_finished": "Pausa Concluída!",
            }.get(p_state, p_state)

            self.query_one("#pomo-time", Label).update(
                f"{state_pt} (Ciclo {p_cycle}) — [bold]{m:02d}:{s:02d}[/bold]"
            )

            btn = self.query_one("#btn-pomo-toggle", Button)
            if p_state in ("work", "break"):
                btn.label = "⏸ Pausar"
                btn.variant = "warning"
            else:
                btn.label = "▶ Foco"
                btn.variant = "success"

        # 2. Timers
        timers = data.get("timers", [])
        timers_box = self.query_one("#timers-box", Label)
        if not timers:
            timers_box.update("[dim]Nenhum timer ativo[/dim]")
        else:
            lines = []
            for t in timers:
                left = t.get("left", 0)
                m, s = divmod(left, 60)
                status = "pausado" if t.get("paused") else f"{m:02d}:{s:02d}"
                lines.append(f"⏱ [bold cyan]{t.get('label', 'Timer')}:[/] {status}")
            timers_box.update("\n".join(lines))

        # 3. Alarmes
        alarms = data.get("alarms", [])
        alarms_box = self.query_one("#alarms-box", Label)
        if not alarms:
            alarms_box.update("[dim]Nenhum alarme programado[/dim]")
        else:
            lines = []
            for a in alarms:
                status = "ativo" if a.get("enabled", True) else "desativado"
                lines.append(f"⏰ [bold yellow]{a.get('label', 'Alarme')}:[/] {a.get('time', '--:--')} ({status})")
            alarms_box.update("\n".join(lines))

    # ==========================================
    # EVENTOS DE INTERAÇÃO DO USUÁRIO
    # ==========================================
    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return

        chat = self.query_one("#chat-log", RichLog)
        chat.write(f"[bold white]⌨️ [Texto] Você:[/] {text}")

        self.send_action("send_prompt", {"text": text})
        event.input.value = ""

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "btn-send":
            inp = self.query_one("#cmd-input", Input)
            self.on_input_submitted(Input.Submitted(inp, inp.value))

        elif button_id == "btn-pomo-toggle":
            self.action_toggle_pomodoro()

        elif button_id == "btn-pomo-skip":
            self.send_action("pomodoro", {"sub_action": "skip"})

        elif button_id == "btn-pomo-reset":
            self.send_action("pomodoro", {"sub_action": "reset"})

    # ==========================================
    # AÇÕES DOS ATALHOS DE TECLADO
    # ==========================================
    def action_toggle_mute(self) -> None:
        self.send_action("toggle_mute")

    def action_cancel_action(self) -> None:
        self.send_action("cancel")

    def action_toggle_pomodoro(self) -> None:
        if self._pomodoro_state in ("work", "break"):
            self.send_action("pomodoro", {"sub_action": "pause"})
        else:
            self.send_action("pomodoro", {"sub_action": "start"})

    def action_focus_input(self) -> None:
        self.query_one("#cmd-input", Input).focus()

    def action_clear_log(self) -> None:
        chat = self.query_one("#chat-log", RichLog)
        chat.clear()
        chat.write("[dim italic]Histórico limpo.[/]")

    def action_open_ollama_settings(self) -> None:
        """Abre o diálogo modal de configuração do Ollama / LLM Externa."""
        self.push_screen(
            OllamaConfigModal(
                current_host=self._ollama_host,
                current_model=self._ollama_model,
                current_provider=self._llm_provider,
                current_api_key=self._llm_api_key,
            )
        )

    def save_ollama_config(
        self,
        host: str,
        model: str,
        provider: str = "ollama",
        api_key: str = "",
        api_base: str = "",
    ) -> None:
        """Salva a configuração do Ollama / LLM Externa e transmite via IPC."""
        self._llm_provider = provider
        self._ollama_host = host
        self._ollama_model = model
        if api_key:
            self._llm_api_key = api_key
        if api_base:
            self._llm_api_base = api_base

        payload = {
            "provider": provider,
            "ollama_host": host,
            "llm_model": model,
            "persist": True,
        }
        if api_key:
            payload["api_key"] = api_key
        if api_base:
            payload["api_base"] = api_base

        self.send_action("set_config", payload)
        chat = self.query_one("#chat-log", RichLog)
        prov_label = provider.upper() if provider != "ollama" else "Ollama"
        chat.write(f"[bold green]⚙️ Configuração salva:[/] {prov_label} em {host} ({model})\n")


def run_tui(host: str = "127.0.0.1", port: int = 8765, token: Optional[str] = None) -> None:
    app = GeraldoTUI(host=host, port=port, token=token)
    app.run()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Geraldo Terminal UI (TUI)")
    parser.add_argument("--host", default="127.0.0.1", help="Host do WebSocket")
    parser.add_argument("--port", type=int, default=8765, help="Porta do WebSocket")
    parser.add_argument("--token", default=None, help="Token de autenticação")
    args = parser.parse_args()

    run_tui(host=args.host, port=args.port, token=args.token)
