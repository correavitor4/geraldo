import asyncio
import json
import time
from typing import Any, Dict, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, RichLog, Static, TabbedContent, TabPane

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
    height: auto;
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
    height: auto;
    margin: 1 0;
    content-align: center middle;
}

#pomo-buttons {
    height: auto;
    align: center middle;
}

#pomo-buttons Button {
    margin: 0 1;
    min-width: 8;
    height: 3;
}

#audio-quick-buttons {
    height: auto;
    margin-top: 1;
}

#audio-quick-buttons Button {
    margin-right: 1;
    min-width: 10;
    height: 3;
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

TimerConfigModal {
    align: center middle;
    background: rgba(0, 0, 0, 0.75);
}

#timer-config-dialog {
    width: 66;
    height: auto;
    background: #111827;
    border: round #38bdf8;
    padding: 1 2;
}

#timer-config-title {
    color: #38bdf8;
    text-style: bold;
    text-align: center;
    margin-bottom: 1;
}

#timer-presets-bar {
    height: 3;
    align: center middle;
    margin-bottom: 1;
}

#timer-presets-bar Button {
    margin: 0 1;
    min-width: 8;
}

#timer-duration-inputs {
    height: auto;
    margin-bottom: 1;
}

.input-group-col {
    width: 1fr;
    margin: 0 1;
}

#input-timer-label, #input-timer-hours, #input-timer-min, #input-timer-sec {
    background: #1e293b;
    border: none;
    color: #f8fafc;
    margin-bottom: 1;
}

#input-timer-label:focus, #input-timer-hours:focus, #input-timer-min:focus, #input-timer-sec:focus {
    border: tall #38bdf8;
}

#timer-buttons {
    height: auto;
    margin-top: 1;
}

#timer-buttons Button {
    margin-right: 1;
    min-width: 9;
    height: 3;
}

#time-tasks-tabs {
    height: auto;
    margin: 0;
    padding: 0;
}

#alarm-buttons {
    height: auto;
    margin-top: 1;
}

#alarm-buttons Button {
    margin-right: 1;
    min-width: 9;
    height: 3;
}

AlarmConfigModal {
    align: center middle;
    background: rgba(0, 0, 0, 0.75);
}

#alarm-config-dialog {
    width: 66;
    height: auto;
    background: #111827;
    border: round #facc15;
    padding: 1 2;
}

#alarm-config-title {
    color: #facc15;
    text-style: bold;
    text-align: center;
    margin-bottom: 1;
}

#alarm-presets-bar {
    height: 3;
    align: center middle;
    margin-bottom: 1;
}

#alarm-presets-bar Button {
    margin: 0 1;
    min-width: 8;
}

#input-alarm-label, #input-alarm-time {
    background: #1e293b;
    border: none;
    color: #f8fafc;
    margin-bottom: 1;
}

#input-alarm-label:focus, #input-alarm-time:focus {
    border: tall #facc15;
}

PomodoroPlanModal {
    align: center middle;
    background: rgba(0, 0, 0, 0.75);
}

#pomo-plan-dialog {
    width: 62;
    height: auto;
    background: #111827;
    border: round #f59e0b;
    padding: 1 2;
}

#pomo-plan-title {
    color: #f59e0b;
    text-style: bold;
    text-align: center;
    margin-bottom: 1;
}

#pomo-presets-bar {
    height: 3;
    align: center middle;
    margin-bottom: 1;
}

#pomo-presets-bar Button {
    margin: 0 1;
    min-width: 12;
}

#input-pomo-work, #input-pomo-break, #input-pomo-long-break, #input-pomo-long-interval, #input-pomo-cycle {
    background: #1e293b;
    border: none;
    color: #f8fafc;
    margin-bottom: 1;
}

#input-pomo-work:focus, #input-pomo-break:focus, #input-pomo-long-break:focus, #input-pomo-long-interval:focus, #input-pomo-cycle:focus {
    border: tall #f59e0b;
}

AudioConfigModal {
    align: center middle;
    background: rgba(0, 0, 0, 0.75);
}

#audio-dialog {
    width: 76;
    height: auto;
    max-height: 90%;
    background: #111827;
    border: round #38bdf8;
    padding: 1 2;
}

#audio-title {
    color: #38bdf8;
    text-style: bold;
    text-align: center;
    margin-bottom: 1;
}

#audio-devices-scroll {
    height: 8;
    background: #0f172a;
    border: solid #1e293b;
    padding: 0 1;
    margin-bottom: 1;
}

#input-audio-mic, #input-audio-out {
    background: #1e293b;
    border: none;
    color: #f8fafc;
    margin-bottom: 1;
}

#input-audio-mic:focus, #input-audio-out:focus {
    border: tall #38bdf8;
}
"""


class AudioConfigModal(ModalScreen):
    """Modal para configuração e teste dos dispositivos de áudio (microfone e saída) no Geraldo."""

    def __init__(
        self,
        current_input: Optional[Any] = None,
        current_output: Optional[Any] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.current_input = "" if current_input is None else str(current_input)
        self.current_output = "" if current_output is None else str(current_output)
        self.devices_info: Dict[str, Any] = {"inputs": [], "outputs": []}

    def compose(self) -> ComposeResult:
        with Vertical(id="audio-dialog"):
            yield Label("🎙️ Dispositivos de Áudio (Microfone e Saída)", id="audio-title")

            yield Label("Dispositivos detectados no sistema:", classes="form-label")
            with VerticalScroll(id="audio-devices-scroll"):
                yield Static("Carregando lista de dispositivos...", id="audio-device-list")

            yield Label("🎤 Microfone (ID, nome ou vazio para Padrão):", classes="form-label")
            yield Input(value=self.current_input, placeholder="Ex: 1 ou fifine (vazio = padrão)", id="input-audio-mic")

            yield Label("🔊 Alto-falante / Saída (ID, nome ou vazio para Padrão):", classes="form-label")
            yield Input(value=self.current_output, placeholder="Ex: 0 ou realtek (vazio = padrão)", id="input-audio-out")

            yield Label("Status: Escolha o dispositivo ou teste o som de saída.", id="audio-status")

            with Horizontal(id="modal-buttons"):
                yield Button("🔔 Testar Saída", id="btn-audio-test", variant="default")
                yield Button("🔄 Atualizar", id="btn-audio-refresh", variant="default")
                yield Button("💾 Salvar", id="btn-audio-save", variant="primary")
                yield Button("✕ Fechar", id="btn-audio-close", variant="error")

    def on_mount(self) -> None:
        self.refresh_devices()

    def refresh_devices(self) -> None:
        from audio.device_utils import list_audio_devices
        try:
            self.devices_info = list_audio_devices()
            lines = []
            lines.append("[bold cyan]🎤 MICROFONES (Entrada):[/]")
            lines.append("  [0] Padrão do Sistema")
            for d in self.devices_info.get("inputs", []):
                lines.append(f"  [{d['id']}] {d['name']}")

            lines.append("\n[bold cyan]🔊 SAÍDAS (Alto-falante / Fone):[/]")
            lines.append("  [0] Padrão do Sistema")
            for d in self.devices_info.get("outputs", []):
                lines.append(f"  [{d['id']}] {d['name']}")

            list_widget = self.query_one("#audio-device-list", Static)
            list_widget.update("\n".join(lines))
        except Exception as e:
            try:
                self.query_one("#audio-device-list", Static).update(f"[red]Erro ao listar dispositivos: {e}[/]")
            except Exception:
                pass

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "btn-audio-close":
            self.dismiss(False)
        elif button_id == "btn-audio-refresh":
            self.refresh_devices()
            self.query_one("#audio-status", Label).update("[yellow]Lista de dispositivos atualizada![/]")
        elif button_id == "btn-audio-save":
            in_val = self.query_one("#input-audio-mic", Input).value.strip() or None
            out_val = self.query_one("#input-audio-out", Input).value.strip() or None
            if hasattr(self.app, "save_audio_config"):
                self.app.save_audio_config(input_device=in_val, output_device=out_val)
            self.dismiss(True)
        elif button_id == "btn-audio-test":
            out_val = self.query_one("#input-audio-out", Input).value.strip() or None
            status_lbl = self.query_one("#audio-status", Label)
            status_lbl.update("[bold yellow]🔔 Tocando som de teste...[/]")
            self.run_worker(self._async_test_beep(out_val), exclusive=True)

    async def _async_test_beep(self, device: Optional[str]) -> None:
        from audio.player import AudioPlayer
        import asyncio
        try:
            await asyncio.to_thread(AudioPlayer.play_beep, device=device)
            self.query_one("#audio-status", Label).update("[bold green]✅ Som reproduzido com sucesso![/]")
        except Exception as e:
            self.query_one("#audio-status", Label).update(f"[bold red]❌ Falha na reprodução: {e}[/]")



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


class PomodoroPlanModal(ModalScreen):
    """Diálogo modal para planejar e configurar o ciclo Pomodoro."""

    def __init__(
        self,
        current_work: int = 25,
        current_break: int = 5,
        current_long_break: int = 15,
        current_long_interval: int = 4,
        current_cycle: int = 1,
    ) -> None:
        super().__init__()
        self.current_work = current_work
        self.current_break = current_break
        self.current_long_break = current_long_break
        self.current_long_interval = current_long_interval
        self.current_cycle = current_cycle

    def compose(self) -> ComposeResult:
        with Vertical(id="pomo-plan-dialog"):
            yield Label("🍅 PLANEJAR CICLO POMODORO", id="pomo-plan-title")
            yield Label("Defina a duração do foco, pausas e ciclo:", classes="form-hint")

            with Horizontal(id="pomo-presets-bar"):
                yield Button("25/5 min", id="btn-preset-25", variant="default")
                yield Button("50/10 min", id="btn-preset-50", variant="default")
                yield Button("15/3 min", id="btn-preset-15", variant="default")

            yield Label("Duração do Foco (minutos):", classes="form-label")
            yield Input(value=str(self.current_work), placeholder="Ex: 25", id="input-pomo-work")

            yield Label("Duração da Pausa Curta (minutos):", classes="form-label")
            yield Input(value=str(self.current_break), placeholder="Ex: 5", id="input-pomo-break")

            yield Label("Duração da Pausa Longa (minutos):", classes="form-label")
            yield Input(value=str(self.current_long_break), placeholder="Ex: 15", id="input-pomo-long-break")

            yield Label("Intervalo da Pausa Longa (a cada X ciclos):", classes="form-label")
            yield Input(value=str(self.current_long_interval), placeholder="Ex: 4", id="input-pomo-long-interval")

            yield Label("Ciclo Inicial:", classes="form-label")
            yield Input(value=str(self.current_cycle), placeholder="Ex: 1", id="input-pomo-cycle")

            with Horizontal(id="modal-buttons"):
                yield Button("▶ Iniciar Ciclo", id="btn-pomo-start-plan", variant="success")
                yield Button("✕ Fechar", id="btn-pomo-close-plan", variant="error")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "btn-pomo-close-plan":
            self.dismiss(False)
        elif button_id == "btn-preset-25":
            self.query_one("#input-pomo-work", Input).value = "25"
            self.query_one("#input-pomo-break", Input).value = "5"
            self.query_one("#input-pomo-long-break", Input).value = "15"
            self.query_one("#input-pomo-long-interval", Input).value = "4"
        elif button_id == "btn-preset-50":
            self.query_one("#input-pomo-work", Input).value = "50"
            self.query_one("#input-pomo-break", Input).value = "10"
            self.query_one("#input-pomo-long-break", Input).value = "30"
            self.query_one("#input-pomo-long-interval", Input).value = "4"
        elif button_id == "btn-preset-15":
            self.query_one("#input-pomo-work", Input).value = "15"
            self.query_one("#input-pomo-break", Input).value = "3"
            self.query_one("#input-pomo-long-break", Input).value = "10"
            self.query_one("#input-pomo-long-interval", Input).value = "3"
        elif button_id == "btn-pomo-start-plan":
            try:
                work_val = int(self.query_one("#input-pomo-work", Input).value.strip() or "25")
            except ValueError:
                work_val = 25
            try:
                break_val = int(self.query_one("#input-pomo-break", Input).value.strip() or "5")
            except ValueError:
                break_val = 5
            try:
                long_break_val = int(self.query_one("#input-pomo-long-break", Input).value.strip() or "15")
            except ValueError:
                long_break_val = 15
            try:
                long_interval_val = int(self.query_one("#input-pomo-long-interval", Input).value.strip() or "4")
            except ValueError:
                long_interval_val = 4
            try:
                cycle_val = int(self.query_one("#input-pomo-cycle", Input).value.strip() or "1")
            except ValueError:
                cycle_val = 1

            if hasattr(self.app, "start_planned_pomodoro"):
                self.app.start_planned_pomodoro(work_val, break_val, long_break_val, long_interval_val, cycle_val)
            self.dismiss(True)


class TimerConfigModal(ModalScreen):
    """Diálogo modal para configurar e gerenciar timers no TUI."""

    def __init__(self, timers: Optional[list] = None) -> None:
        super().__init__()
        self.timers = timers or []

    def compose(self) -> ComposeResult:
        with Vertical(id="timer-config-dialog"):
            yield Label("⏱️ CONFIGURAR TIMERS", id="timer-config-title")
            yield Label("Escolha um preset ou defina a duração personalizada:", classes="form-hint")

            with Horizontal(id="timer-presets-bar"):
                yield Button("1 min", id="btn-timer-pre-1", variant="default")
                yield Button("5 min", id="btn-timer-pre-5", variant="default")
                yield Button("10 min", id="btn-timer-pre-10", variant="default")
                yield Button("15 min", id="btn-timer-pre-15", variant="default")
                yield Button("25 min", id="btn-timer-pre-25", variant="default")
                yield Button("1h", id="btn-timer-pre-60", variant="default")

            yield Label("Rótulo / Nome do Timer:", classes="form-label")
            yield Input(value="Timer", placeholder="Ex: Café, Forno, Reunião", id="input-timer-label")

            with Horizontal(id="timer-duration-inputs"):
                with Vertical(classes="input-group-col"):
                    yield Label("Horas:", classes="form-label")
                    yield Input(value="0", placeholder="0", id="input-timer-hours")
                with Vertical(classes="input-group-col"):
                    yield Label("Minutos:", classes="form-label")
                    yield Input(value="5", placeholder="5", id="input-timer-min")
                with Vertical(classes="input-group-col"):
                    yield Label("Segundos:", classes="form-label")
                    yield Input(value="0", placeholder="0", id="input-timer-sec")

            with Horizontal(id="modal-buttons"):
                yield Button("▶ Criar Timer", id="btn-timer-create", variant="success")
                yield Button("⏸ Pausar/Play", id="btn-timer-toggle-active")
                yield Button("🗑 Limpar Todos", id="btn-timer-clear-all", variant="error")
                yield Button("✕ Fechar", id="btn-timer-close", variant="default")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "btn-timer-close":
            self.dismiss(False)
        elif button_id == "btn-timer-pre-1":
            self.query_one("#input-timer-hours", Input).value = "0"
            self.query_one("#input-timer-min", Input).value = "1"
            self.query_one("#input-timer-sec", Input).value = "0"
        elif button_id == "btn-timer-pre-5":
            self.query_one("#input-timer-hours", Input).value = "0"
            self.query_one("#input-timer-min", Input).value = "5"
            self.query_one("#input-timer-sec", Input).value = "0"
        elif button_id == "btn-timer-pre-10":
            self.query_one("#input-timer-hours", Input).value = "0"
            self.query_one("#input-timer-min", Input).value = "10"
            self.query_one("#input-timer-sec", Input).value = "0"
        elif button_id == "btn-timer-pre-15":
            self.query_one("#input-timer-hours", Input).value = "0"
            self.query_one("#input-timer-min", Input).value = "15"
            self.query_one("#input-timer-sec", Input).value = "0"
        elif button_id == "btn-timer-pre-25":
            self.query_one("#input-timer-hours", Input).value = "0"
            self.query_one("#input-timer-min", Input).value = "25"
            self.query_one("#input-timer-sec", Input).value = "0"
        elif button_id == "btn-timer-pre-60":
            self.query_one("#input-timer-hours", Input).value = "1"
            self.query_one("#input-timer-min", Input).value = "0"
            self.query_one("#input-timer-sec", Input).value = "0"
        elif button_id == "btn-timer-create":
            label = self.query_one("#input-timer-label", Input).value.strip() or "Timer"
            try:
                hours = int(self.query_one("#input-timer-hours", Input).value.strip() or "0")
            except ValueError:
                hours = 0
            try:
                mins = int(self.query_one("#input-timer-min", Input).value.strip() or "0")
            except ValueError:
                mins = 0
            try:
                secs = int(self.query_one("#input-timer-sec", Input).value.strip() or "0")
            except ValueError:
                secs = 0

            if hasattr(self.app, "add_timer"):
                self.app.add_timer(hours=hours, minutes=mins, seconds=secs, label=label)
            self.dismiss(True)
        elif button_id == "btn-timer-toggle-active":
            if hasattr(self.app, "toggle_active_timers"):
                self.app.toggle_active_timers()
            self.dismiss(True)
        elif button_id == "btn-timer-clear-all":
            if hasattr(self.app, "clear_all_timers"):
                self.app.clear_all_timers()
            self.dismiss(True)


class AlarmConfigModal(ModalScreen):
    """Diálogo modal para configurar e gerenciar alarmes no TUI."""

    def __init__(self, alarms: Optional[list] = None) -> None:
        super().__init__()
        self.alarms = alarms or []

    def compose(self) -> ComposeResult:
        with Vertical(id="alarm-config-dialog"):
            yield Label("⏰ CONFIGURAR ALARMES", id="alarm-config-title")
            yield Label("Escolha um horário sugerido ou defina um horário personalizado:", classes="form-hint")

            with Horizontal(id="alarm-presets-bar"):
                yield Button("07:00", id="btn-alarm-pre-7", variant="default")
                yield Button("08:00", id="btn-alarm-pre-8", variant="default")
                yield Button("12:00", id="btn-alarm-pre-12", variant="default")
                yield Button("18:00", id="btn-alarm-pre-18", variant="default")
                yield Button("22:00", id="btn-alarm-pre-22", variant="default")

            yield Label("Rótulo / Nome do Alarme:", classes="form-label")
            yield Input(value="Alarme", placeholder="Ex: Acordar, Remédio, Reunião", id="input-alarm-label")

            yield Label("Horário (HH:MM):", classes="form-label")
            yield Input(value="08:00", placeholder="Ex: 08:00", id="input-alarm-time")

            with Horizontal(id="modal-buttons"):
                yield Button("⏰ Criar Alarme", id="btn-alarm-create", variant="success")
                yield Button("🔔 Alternar Ativo", id="btn-alarm-toggle-active")
                yield Button("🗑 Limpar Todos", id="btn-alarm-clear-all", variant="error")
                yield Button("✕ Fechar", id="btn-alarm-close", variant="default")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "btn-alarm-close":
            self.dismiss(False)
        elif button_id == "btn-alarm-pre-7":
            self.query_one("#input-alarm-time", Input).value = "07:00"
        elif button_id == "btn-alarm-pre-8":
            self.query_one("#input-alarm-time", Input).value = "08:00"
        elif button_id == "btn-alarm-pre-12":
            self.query_one("#input-alarm-time", Input).value = "12:00"
        elif button_id == "btn-alarm-pre-18":
            self.query_one("#input-alarm-time", Input).value = "18:00"
        elif button_id == "btn-alarm-pre-22":
            self.query_one("#input-alarm-time", Input).value = "22:00"
        elif button_id == "btn-alarm-create":
            label = self.query_one("#input-alarm-label", Input).value.strip() or "Alarme"
            time_val = self.query_one("#input-alarm-time", Input).value.strip() or "08:00"
            if hasattr(self.app, "add_alarm"):
                self.app.add_alarm(time_str=time_val, label=label)
            self.dismiss(True)
        elif button_id == "btn-alarm-toggle-active":
            if hasattr(self.app, "toggle_alarm"):
                self.app.toggle_alarm()
            self.dismiss(True)
        elif button_id == "btn-alarm-clear-all":
            if hasattr(self.app, "clear_all_alarms"):
                self.app.clear_all_alarms()
            self.dismiss(True)


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
        Binding("P", "open_pomodoro_plan", "Planejar Pomodoro", show=True),
        Binding("T", "open_timer_modal", "Configurar Timers", show=True),
        Binding("A", "open_alarm_modal", "Configurar Alarmes", show=True),
        Binding("c", "cancel_action", "Cancelar/Silenciar", show=True),
        Binding("o", "open_ollama_settings", "Configurar Ollama", show=True),
        Binding("s", "open_audio_settings", "Dispositivos Áudio", show=True),
        Binding("a", "open_calendar", "Agenda Google", show=True),
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
        self._audio_input_device: Optional[Any] = None
        self._audio_output_device: Optional[Any] = None
        self._latest_status: dict = {}

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
                    yield Label("[dim]Nenhum pomodoro ativo[/dim]", id="pomo-time")
                    with Horizontal(id="pomo-buttons"):
                        yield Button("▶ Iniciar", id="btn-pomo-toggle", variant="success")
                        yield Button("⚙ Plan", id="btn-pomo-plan", variant="default")
                        yield Button("⏭ Pular", id="btn-pomo-skip")
                        yield Button("🔄 Reset", id="btn-pomo-reset")

                with Vertical(classes="side-card", id="card-time-tasks"):
                    with TabbedContent(id="time-tasks-tabs"):
                        with TabPane("⏱️ Timers", id="tab-pane-timers"):
                            yield Label("Nenhum timer ativo", id="timers-box")
                            with Horizontal(id="timer-buttons"):
                                yield Button("+ Novo", id="btn-timer-new", variant="primary")
                                yield Button("⏸ Pausa/Play", id="btn-timer-toggle")
                                yield Button("✕ Limpar", id="btn-timer-clear", variant="error")

                        with TabPane("⏰ Alarmes", id="tab-pane-alarms"):
                            yield Label("Nenhum alarme programado", id="alarms-box")
                            with Horizontal(id="alarm-buttons"):
                                yield Button("+ Novo", id="btn-alarm-new", variant="primary")
                                yield Button("🔔 Alternar", id="btn-alarm-toggle-btn")
                                yield Button("✕ Limpar", id="btn-alarm-clear", variant="error")

                with Vertical(classes="side-card"):
                    yield Label("📅 AGENDA DO GOOGLE", classes="card-title")
                    yield Label("Status: [dim]Não Vinculada[/dim]", id="cal-status-label")
                    with Horizontal(id="cal-buttons"):
                        yield Button("🌐 Abrir", id="btn-cal-open", variant="primary")
                        yield Button("🔑 Conectar", id="btn-cal-auth")

                with Vertical(classes="side-card", id="card-audio-devices"):
                    yield Label("🎙️ DISPOSITIVOS DE ÁUDIO", classes="card-title")
                    yield Label("Mic: [cyan]Padrão[/cyan]", id="audio-in-label")
                    yield Label("Saída: [cyan]Padrão[/cyan]", id="audio-out-label")
                    with Horizontal(id="audio-quick-buttons"):
                        yield Button("🎙️ Ajustar", id="btn-audio-open", variant="default")
                        yield Button("🔔 Testar", id="btn-audio-quick-test", variant="default")

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

        try:
            self.query_one("#btn-pomo-skip", Button).display = False
            self.query_one("#btn-pomo-reset", Button).display = False
        except Exception:
            pass

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
        if not self._connected and self.auto_connect:
            try:
                chat = self.query_one("#chat-log", RichLog)
                chat.write("[bold red]⚠️ Não conectado ao serviço Geraldo.[/bold red] [yellow]Inicie o serviço com: [bold]systemctl --user start geraldo.service[/bold] ou [bold]./run.sh[/bold][/yellow]\n")
            except Exception:
                pass

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
                if "audio" in cfg and isinstance(cfg["audio"], dict):
                    self._audio_input_device = cfg["audio"].get("input_device")
                    self._audio_output_device = cfg["audio"].get("output_device")

        elif event_name == "config_changed":
            self._ollama_host = data.get("ollama_host", self._ollama_host)
            self._ollama_model = data.get("llm_model", self._ollama_model)
            if "audio" in data and isinstance(data["audio"], dict):
                self._audio_input_device = data["audio"].get("input_device")
                self._audio_output_device = data["audio"].get("output_device")
                self.update_audio_dashboard()
            chat.write(f"[bold cyan]⚙️ Configuração atualizada:[/] Ollama em {self._ollama_host} ({self._ollama_model})\n")

        elif event_name == "audio_config_changed":
            self._audio_input_device = data.get("input_device")
            self._audio_output_device = data.get("output_device")
            self.update_audio_dashboard()
            in_lbl = self._audio_input_device if self._audio_input_device is not None else "Padrão"
            out_lbl = self._audio_output_device if self._audio_output_device is not None else "Padrão"
            chat.write(f"[bold cyan]🎙️ Dispositivos de Áudio alterados:[/] Mic: {in_lbl} | Saída: {out_lbl}\n")

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
            if "audio" in data and isinstance(data["audio"], dict):
                self._audio_input_device = data["audio"].get("input_device")
                self._audio_output_device = data["audio"].get("output_device")
                self.update_audio_dashboard()
            elif "input_device" in data or "output_device" in data:
                self._audio_input_device = data.get("input_device")
                self._audio_output_device = data.get("output_device")
                self.update_audio_dashboard()
            if req_id.startswith("check_calendar") and isinstance(data, dict):
                try:
                    lbl = self.query_one("#cal-status-label", Label)
                    if data.get("status") == "configured" or data.get("token_exists"):
                        lbl.update("Status: [bold green]Conectada (OK)[/]")
                    elif data.get("status") == "partial" or data.get("credentials_exists"):
                        lbl.update("Status: [bold yellow]Credenciais OK[/]")
                    else:
                        lbl.update("Status: [dim]Não Vinculada[/]")
                except Exception:
                    pass
            elif req_id.startswith("auth_calendar") and isinstance(data, dict):
                if data.get("success"):
                    chat.write("[bold green]✅ Agenda do Google vinculada com sucesso![/]")
                    try:
                        self.query_one("#cal-status-label", Label).update("Status: [bold green]Conectada (OK)[/]")
                    except Exception:
                        pass
                else:
                    msg = data.get("message", "Falha na autenticação.")
                    chat.write(f"[bold red]❌ {msg}[/]")
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
        if pomo is not None and pomo:
            p_state = pomo.get("state", "idle")
            is_active = pomo.get("active", p_state in ("work", "break", "long_break", "paused", "work_finished", "break_finished", "long_break_finished"))
            p_cycle = pomo.get("cycle", 1)
            p_left = pomo.get("left", 0)
            self._pomodoro_state = p_state
            self._pomodoro_cycle = p_cycle

            btn_toggle = self.query_one("#btn-pomo-toggle", Button)
            btn_plan = self.query_one("#btn-pomo-plan", Button)
            btn_skip = self.query_one("#btn-pomo-skip", Button)
            btn_reset = self.query_one("#btn-pomo-reset", Button)
            pomo_label = self.query_one("#pomo-time", Label)

            if not is_active or p_state == "idle":
                pomo_label.update("[dim]Nenhum pomodoro ativo[/dim]")
                btn_toggle.label = "▶ Iniciar"
                btn_toggle.variant = "success"
                btn_plan.display = True
                btn_skip.display = False
                btn_reset.display = False
            else:
                btn_plan.display = False
                btn_skip.display = True
                btn_reset.display = True
                m, s = divmod(p_left, 60)
                state_pt = {
                    "work": "Foco",
                    "break": "Pausa",
                    "long_break": "Pausa Longa",
                    "paused": "Pausado",
                    "work_finished": "Foco Concluído!",
                    "break_finished": "Pausa Concluída!",
                    "long_break_finished": "Pausa Longa Concluída!",
                }.get(p_state, p_state)

                if p_state in ("work_finished", "break_finished", "long_break_finished"):
                    pomo_label.update(
                        f"[bold yellow]🔔 {state_pt} (Ciclo {p_cycle})[/bold yellow]"
                    )
                else:
                    pomo_label.update(
                        f"{state_pt} (Ciclo {p_cycle}) — [bold]{m:02d}:{s:02d}[/bold]"
                    )

                if p_state in ("work", "break", "long_break"):
                    btn_toggle.label = "⏸ Pausar"
                    btn_toggle.variant = "warning"
                elif p_state == "paused":
                    btn_toggle.label = "▶ Retomar"
                    btn_toggle.variant = "success"
                elif p_state == "work_finished":
                    btn_toggle.label = "▶ Iniciar Pausa"
                    btn_toggle.variant = "success"
                elif p_state in ("break_finished", "long_break_finished"):
                    btn_toggle.label = "▶ Próximo Ciclo"
                    btn_toggle.variant = "success"
                else:
                    btn_toggle.label = "▶ Iniciar"
                    btn_toggle.variant = "success"

        # 2. Timers
        self._latest_status = data
        timers = data.get("timers", [])
        timers_box = self.query_one("#timers-box", Label)
        if not timers:
            timers_box.update("[dim]Nenhum timer ativo[/dim]")
        else:
            lines = []
            for t in timers:
                left = int(t.get("left", 0))
                h = left // 3600
                m = (left % 3600) // 60
                s = left % 60
                time_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
                status = f"[yellow bold]pausado ({time_str})[/]" if t.get("paused") else f"[cyan bold]{time_str}[/]"
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

        elif button_id == "btn-pomo-plan":
            self.action_open_pomodoro_plan()

        elif button_id == "btn-pomo-skip":
            self.send_action("pomodoro", {"sub_action": "skip"})

        elif button_id == "btn-pomo-reset":
            self.send_action("pomodoro", {"sub_action": "reset"})

        elif button_id == "btn-cal-open":
            self.action_open_calendar()

        elif button_id == "btn-cal-auth":
            self.send_action("auth_calendar", {})
            chat = self.query_one("#chat-log", RichLog)
            chat.write("[bold yellow]🔑 Solicitando autorização da conta Google Calendar...[/]")

        elif button_id == "btn-audio-open":
            self.action_open_audio_settings()

        elif button_id == "btn-audio-quick-test":
            self.run_worker(self._async_quick_beep_test(), exclusive=True)

        elif button_id == "btn-timer-new":
            self.action_open_timer_modal()

        elif button_id == "btn-timer-toggle":
            self.toggle_active_timers()

        elif button_id == "btn-timer-clear":
            self.clear_all_timers()

        elif button_id == "btn-alarm-new":
            self.action_open_alarm_modal()

        elif button_id == "btn-alarm-toggle-btn":
            self.toggle_alarm()

        elif button_id == "btn-alarm-clear":
            self.clear_all_alarms()

    # ==========================================
    # AÇÕES DOS ATALHOS DE TECLADO
    # ==========================================
    def action_open_calendar(self) -> None:
        """Abre o Google Calendar no navegador padrão e notifica o barramento."""
        import webbrowser
        try:
            webbrowser.open("https://calendar.google.com")
        except Exception:
            pass
        self.send_action("open_calendar", {"url": "https://calendar.google.com"})
        chat = self.query_one("#chat-log", RichLog)
        chat.write("[bold cyan]📅 Abrindo Google Calendar no navegador padrão...[/]")
    def action_toggle_mute(self) -> None:
        self.send_action("toggle_mute")

    def action_cancel_action(self) -> None:
        self.send_action("cancel")

    def action_toggle_pomodoro(self) -> None:
        if self._pomodoro_state in ("work", "break", "long_break"):
            self.send_action("pomodoro", {"sub_action": "pause"})
        elif self._pomodoro_state == "paused":
            self.send_action("pomodoro", {"sub_action": "resume"})
        elif self._pomodoro_state in ("work_finished", "break_finished", "long_break_finished"):
            self.send_action("pomodoro", {"sub_action": "advance"})
        else:
            w_m = getattr(self, "_pomo_planned_work", 25)
            b_m = getattr(self, "_pomo_planned_break", 5)
            lb_m = getattr(self, "_pomo_planned_long_break", 15)
            li = getattr(self, "_pomo_planned_long_interval", 4)
            c = getattr(self, "_pomo_planned_cycle", 1)
            self.send_action("pomodoro", {
                "sub_action": "start",
                "work_minutes": w_m,
                "break_minutes": b_m,
                "long_break_minutes": lb_m,
                "long_break_interval": li,
                "cycle": c,
            })

    def action_open_pomodoro_plan(self) -> None:
        """Abre o diálogo modal para planejar e customizar o Pomodoro."""
        w_m = getattr(self, "_pomo_planned_work", 25)
        b_m = getattr(self, "_pomo_planned_break", 5)
        lb_m = getattr(self, "_pomo_planned_long_break", 15)
        li = getattr(self, "_pomo_planned_long_interval", 4)
        c = getattr(self, "_pomo_planned_cycle", 1)
        self.push_screen(
            PomodoroPlanModal(
                current_work=w_m,
                current_break=b_m,
                current_long_break=lb_m,
                current_long_interval=li,
                current_cycle=c,
            )
        )

    def action_open_timer_modal(self) -> None:
        """Abre o diálogo modal de configuração de timers."""
        timers = self._latest_status.get("timers", []) if hasattr(self, "_latest_status") else []
        self.push_screen(TimerConfigModal(timers=timers))

    def add_timer(self, hours: int = 0, minutes: int = 0, seconds: int = 0, label: str = "Timer") -> None:
        """Envia comando de criação de timer via WebSocket."""
        self.send_action("timer_add", {
            "hours": hours,
            "minutes": minutes,
            "seconds": seconds,
            "label": label,
        })
        chat = self.query_one("#chat-log", RichLog)
        chat.write(f"[bold cyan]⏱ Solicitado timer '{label}' ({hours:02d}:{minutes:02d}:{seconds:02d})...[/]")

    def toggle_active_timers(self) -> None:
        """Pausa ou retoma timers ativos."""
        timers = self._latest_status.get("timers", []) if hasattr(self, "_latest_status") else []
        chat = self.query_one("#chat-log", RichLog)
        if not timers:
            chat.write("[dim italic]Nenhum timer ativo para pausar ou retomar.[/]")
            return
        any_running = any(not t.get("paused") for t in timers)
        if any_running:
            self.send_action("timer_pause", {})
            chat.write("[bold yellow]⏸ Solicitado pausar timer...[/]")
        else:
            self.send_action("timer_resume", {})
            chat.write("[bold green]▶ Solicitado retomar timer...[/]")

    def clear_all_timers(self) -> None:
        """Cancela todos os timers."""
        self.send_action("timer_cancel", {"query": "todos"})
        chat = self.query_one("#chat-log", RichLog)
        chat.write("[bold red]🗑 Solicitado cancelar todos os timers...[/]")

    def action_open_alarm_modal(self) -> None:
        """Abre o diálogo modal de configuração de alarmes."""
        alarms = self._latest_status.get("alarms", []) if hasattr(self, "_latest_status") else []
        self.push_screen(AlarmConfigModal(alarms=alarms))

    def add_alarm(self, time_str: str = "08:00", label: str = "Alarme") -> None:
        """Envia comando de criação de alarme via WebSocket."""
        self.send_action("alarm_add", {
            "time": time_str,
            "label": label,
        })
        chat = self.query_one("#chat-log", RichLog)
        chat.write(f"[bold yellow]⏰ Solicitado alarme '{label}' para às {time_str}...[/]")

    def toggle_alarm(self, ident: str = "") -> None:
        """Alterna o estado de ativação do alarme."""
        alarms = self._latest_status.get("alarms", []) if hasattr(self, "_latest_status") else []
        chat = self.query_one("#chat-log", RichLog)
        if not alarms:
            chat.write("[dim italic]Nenhum alarme para alternar.[/]")
            return
        target = ident or alarms[0].get("id") or alarms[0].get("label") or ""
        self.send_action("alarm_toggle", {"id": target})
        chat.write(f"[bold yellow]🔔 Solicitado alternar alarme...[/]")

    def clear_all_alarms(self) -> None:
        """Cancela todos os alarmes."""
        self.send_action("alarm_clear_all", {})
        chat = self.query_one("#chat-log", RichLog)
        chat.write("[bold red]🗑 Solicitado cancelar todos os alarmes...[/]")

    def start_planned_pomodoro(
        self,
        work_minutes: int,
        break_minutes: int,
        long_break_minutes: int = 15,
        long_break_interval: int = 4,
        cycle: int = 1,
    ) -> None:
        """Inicia um Pomodoro com os parâmetros planejados."""
        self._pomo_planned_work = work_minutes
        self._pomo_planned_break = break_minutes
        self._pomo_planned_long_break = long_break_minutes
        self._pomo_planned_long_interval = long_break_interval
        self._pomo_planned_cycle = cycle
        self.send_action("pomodoro", {
            "sub_action": "start",
            "work_minutes": work_minutes,
            "break_minutes": break_minutes,
            "long_break_minutes": long_break_minutes,
            "long_break_interval": long_break_interval,
            "cycle": cycle,
        })

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

    def action_open_audio_settings(self) -> None:
        """Abre o diálogo modal de configuração de microfone e saída de áudio."""
        self.push_screen(
            AudioConfigModal(
                current_input=self._audio_input_device,
                current_output=self._audio_output_device,
            )
        )

    def save_audio_config(
        self,
        input_device: Optional[Any] = None,
        output_device: Optional[Any] = None,
    ) -> None:
        """Salva a configuração dos dispositivos de áudio e transmite via IPC."""
        self._audio_input_device = input_device
        self._audio_output_device = output_device
        self.update_audio_dashboard()

        payload = {
            "input_device": input_device,
            "output_device": output_device,
            "persist": True,
        }
        self.send_action("set_audio_config", payload)
        chat = self.query_one("#chat-log", RichLog)
        in_lbl = input_device if input_device is not None else "Padrão"
        out_lbl = output_device if output_device is not None else "Padrão"
        chat.write(f"[bold green]🎙️ Dispositivos de áudio salvos:[/] Mic: [cyan]{in_lbl}[/] | Saída: [cyan]{out_lbl}[/]\n")

    def update_audio_dashboard(self) -> None:
        """Atualiza os rótulos de dispositivos de áudio ativos na barra lateral da TUI."""
        try:
            in_lbl = self._audio_input_device if self._audio_input_device is not None else "Padrão"
            out_lbl = self._audio_output_device if self._audio_output_device is not None else "Padrão"
            self.query_one("#audio-in-label", Label).update(f"Mic: [cyan]{in_lbl}[/cyan]")
            self.query_one("#audio-out-label", Label).update(f"Saída: [cyan]{out_lbl}[/cyan]")
        except Exception:
            pass

    async def _async_quick_beep_test(self) -> None:
        from audio.player import AudioPlayer
        import asyncio
        chat = self.query_one("#chat-log", RichLog)
        out_lbl = self._audio_output_device if self._audio_output_device is not None else "Padrão"
        chat.write(f"[bold yellow]🔔 Testando som de saída ({out_lbl})...[/]\n")
        try:
            await asyncio.to_thread(AudioPlayer.play_beep, device=self._audio_output_device)
            chat.write("[bold green]✅ Teste de áudio concluído com sucesso![/]\n")
        except Exception as e:
            chat.write(f"[bold red]❌ Falha ao reproduzir áudio: {e}[/]\n")


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
