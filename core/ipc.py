import asyncio
import inspect
import json
import logging
import threading
import time
from typing import Any, Callable, Dict, Optional, Set

from websockets.asyncio.server import ServerConnection, serve

logger = logging.getLogger("geraldo.ipc")


class GeraldoIPCServer:
    """
    Servidor WebSocket local assíncrono para o barramento IPC do Geraldo.
    Executa em uma thread separada em segundo plano para não bloquear áudio ou NLU.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        token: Optional[str] = None,
        require_auth: bool = False,
    ):
        self.host = host
        self.port = port
        self.token = token
        self.require_auth = require_auth

        self._clients: Set[ServerConnection] = set()
        self._authenticated_clients: Set[ServerConnection] = set()
        self._handlers: Dict[str, Callable] = {}
        self._prompt_handler: Optional[Callable[[str], str]] = None
        self._cancel_handler: Optional[Callable[[], None]] = None

        self._assistant_state: str = "idle"
        self._is_muted: bool = False

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._server = None
        self._running: bool = False
        self._ready_event = threading.Event()

        # Registra comandos padrão
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        self.register_handler("ping", self._handle_ping)
        self.register_handler("get_state", self._handle_get_state)
        self.register_handler("toggle_mute", self._handle_toggle_mute)
        self.register_handler("set_mute", self._handle_set_mute)
        self.register_handler("send_prompt", self._handle_send_prompt)
        self.register_handler("cancel", self._handle_cancel)
        self.register_handler("diagnostics", self._handle_diagnostics)
        self.register_handler("get_config", self._handle_get_config)
        self.register_handler("set_config", self._handle_set_config)
        self.register_handler("check_ollama", self._handle_check_ollama)
        self.register_handler("check_llm", self._handle_check_llm)
        self.register_handler("detect_container", self._handle_detect_container)
        self.register_handler("check_calendar", self._handle_check_calendar)
        self.register_handler("open_calendar", self._handle_open_calendar)
        self.register_handler("auth_calendar", self._handle_auth_calendar)
        self.register_handler("disconnect_calendar", self._handle_disconnect_calendar)
        self.register_handler("save_google_creds", self._handle_save_google_creds)
        self.register_handler("get_audio_devices", self._handle_get_audio_devices)
        self.register_handler("get_audio_config", self._handle_get_audio_config)
        self.register_handler("set_audio_config", self._handle_set_audio_config)
        self.register_handler("test_audio_beep", self._handle_test_audio_beep)
        self.register_handler("get_tui_path_status", self._handle_get_tui_path_status)
        self.register_handler("export_tui_path", self._handle_export_tui_path)
        self.register_handler("pomodoro", self._handle_pomodoro)
        self.register_handler("timer_add", self._handle_timer_add)
        self.register_handler("timer_cancel", self._handle_timer_cancel)
        self.register_handler("alarm_add", self._handle_alarm_add)
        self.register_handler("alarm_cancel", self._handle_alarm_cancel)

    def register_handler(self, action: str, handler: Callable) -> None:
        """Registra um manipulador para uma ação RPC."""
        self._handlers[action] = handler

    def set_prompt_handler(self, handler: Callable[[str], str]) -> None:
        """Registra o processador de prompt textual (BrainLLM)."""
        self._prompt_handler = handler

    def set_cancel_handler(self, handler: Callable[[], None]) -> None:
        """Registra a função de cancelamento global (áudio, timers)."""
        self._cancel_handler = handler

    def start(self) -> None:
        """Inicia o servidor WebSocket em uma thread dedicada."""
        if self._running:
            return

        self._running = True
        self._ready_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop, name="GeraldoIPCThread", daemon=True
        )
        self._thread.start()
        # Aguarda o servidor estar pronto para escutar conexões
        self._ready_event.wait(timeout=5.0)

    def stop(self) -> None:
        """Encerra o servidor e a thread de background."""
        if not self._running:
            return

        self._running = False
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._async_stop(), self._loop)

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

        self._thread = None
        self._loop = None
        self._clients.clear()
        self._authenticated_clients.clear()

    def is_running(self) -> bool:
        return self._running

    @property
    def is_muted(self) -> bool:
        return self._is_muted

    @is_muted.setter
    def is_muted(self, value: bool) -> None:
        self._is_muted = bool(value)
        self.broadcast_event("mute_changed", {"muted": self._is_muted})

    @property
    def assistant_state(self) -> str:
        return self._assistant_state

    def set_assistant_state(self, state: str, details: Optional[dict] = None) -> None:
        """Atualiza e transmite a mudança de estado para todos os clientes."""
        self._assistant_state = state
        self.broadcast_event(
            "state_changed",
            {"state": state, "details": details or {}},
        )

    def broadcast_event(self, event_name: str, data: Optional[dict] = None) -> None:
        """
        Transmite um evento JSON para todos os clientes conectados.
        Thread-safe: pode ser chamado de qualquer thread do sistema.
        """
        if not self._running or not self._loop or not self._loop.is_running():
            return

        payload = {
            "type": "event",
            "event": event_name,
            "timestamp": time.time(),
            "data": data or {},
        }

        try:
            asyncio.run_coroutine_threadsafe(
                self._async_broadcast(json.dumps(payload, ensure_ascii=False)),
                self._loop,
            )
        except RuntimeError:
            pass

    async def _async_broadcast(self, message: str) -> None:
        """Envia mensagem para todos os clientes válidos."""
        targets = (
            self._authenticated_clients if self.require_auth else self._clients
        )
        if not targets:
            return

        # Envia em lote para todos os clientes ativos
        coros = [client.send(message) for client in list(targets)]
        results = await asyncio.gather(*coros, return_exceptions=True)
        for client, res in zip(list(targets), results):
            if isinstance(res, Exception):
                self._clients.discard(client)
                self._authenticated_clients.discard(client)

    def _run_loop(self) -> None:
        """Loop de eventos executado na thread de background."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            self._loop.run_until_complete(self._async_serve())
        except Exception:
            pass
        finally:
            try:
                self._loop.close()
            except Exception:
                pass

    async def _async_serve(self) -> None:
        """Cria e mantém o servidor WebSocket escutando."""
        try:
            self._server = await serve(
                self._handle_client,
                self.host,
                self.port,
            )
            self._ready_event.set()
            # Mantém vivo até ser sinalizado para parar
            while self._running:
                await asyncio.sleep(0.2)
        except Exception as e:
            logger.error(f"[Geraldo:IPC] Erro no servidor WebSocket: {e}")
            self._ready_event.set()
        finally:
            if self._server:
                try:
                    self._server.close()
                    await self._server.wait_closed()
                except Exception:
                    pass

    async def _async_stop(self) -> None:
        """Fecha todas as conexões ativas."""
        for client in list(self._clients):
            try:
                await client.close(1000, "Server stopping")
            except Exception:
                pass
        if self._server:
            try:
                self._server.close()
            except Exception:
                pass

    async def _handle_client(self, websocket: ServerConnection) -> None:
        """Gerencia a sessão de um cliente conectado."""
        self._clients.add(websocket)

        if not self.require_auth:
            self._authenticated_clients.add(websocket)

        # Envia estado inicial imediato para o cliente recém-conectado
        try:
            import config
            initial_state = {
                "type": "event",
                "event": "connected",
                "timestamp": time.time(),
                "data": {
                    "assistant_state": self._assistant_state,
                    "is_muted": self._is_muted,
                    "auth_required": self.require_auth,
                    "config": config.get_llm_config() if hasattr(config, "get_llm_config") else {
                        "ollama_host": getattr(config, "OLLAMA_HOST", "http://localhost:11434"),
                        "llm_model": getattr(config, "LLM_MODEL", "qwen2.5:3b"),
                    },
                },
            }
            await websocket.send(json.dumps(initial_state, ensure_ascii=False))
        except Exception:
            pass

        try:
            async for raw_message in websocket:
                await self._process_message(websocket, raw_message)
        except Exception:
            pass
        finally:
            self._clients.discard(websocket)
            self._authenticated_clients.discard(websocket)

    async def _process_message(self, websocket: ServerConnection, raw_message: str) -> None:
        """Processa comando JSON recebido do cliente."""
        try:
            data = json.loads(raw_message)
        except Exception:
            await self._send_error(websocket, None, "JSON inválido.")
            return

        req_id = data.get("id")
        action = data.get("action")

        # Tratamento de autenticação
        if self.require_auth and websocket not in self._authenticated_clients:
            if action == "auth":
                provided_token = data.get("token") or data.get("params", {}).get("token")
                if self.token and provided_token == self.token:
                    self._authenticated_clients.add(websocket)
                    await self._send_response(websocket, req_id, {"authenticated": True})
                    return
                else:
                    await self._send_error(websocket, req_id, "Token de autenticação inválido.")
                    await websocket.close(1008, "Invalid token")
                    return
            else:
                await self._send_error(websocket, req_id, "Não autenticado. Envie 'auth'.")
                return

        if not action or action not in self._handlers:
            await self._send_error(websocket, req_id, f"Ação desconhecida: '{action}'")
            return

        handler = self._handlers[action]
        params = data.get("params", {})

        try:
            if inspect.iscoroutinefunction(handler):
                result = await handler(params)
            else:
                result = handler(params)

            await self._send_response(websocket, req_id, result)
        except Exception as exc:
            logger.error(f"[Geraldo:IPC] Falha ao processar '{action}': {exc}")
            await self._send_error(websocket, req_id, str(exc))

    async def _send_response(self, websocket: ServerConnection, req_id: Any, result: Any) -> None:
        payload = {
            "type": "response",
            "id": req_id,
            "status": "ok",
            "data": result if result is not None else {},
        }
        await websocket.send(json.dumps(payload, ensure_ascii=False))

    async def _send_error(self, websocket: ServerConnection, req_id: Any, error_msg: str) -> None:
        payload = {
            "type": "response",
            "id": req_id,
            "status": "error",
            "error": error_msg,
        }
        await websocket.send(json.dumps(payload, ensure_ascii=False))

    # ==========================================
    # HANDLERS PADRÃO
    # ==========================================
    def _handle_ping(self, params: dict) -> dict:
        return {"pong": True, "server_time": time.time()}

    def _handle_get_state(self, params: dict) -> dict:
        return {
            "assistant_state": self._assistant_state,
            "is_muted": self._is_muted,
            "active_clients": len(self._clients),
        }

    def _handle_toggle_mute(self, params: dict) -> dict:
        self.is_muted = not self._is_muted
        return {"muted": self._is_muted}

    def _handle_set_mute(self, params: dict) -> dict:
        val = bool(params.get("muted", False))
        self.is_muted = val
        return {"muted": self._is_muted}

    def _handle_send_prompt(self, params: dict) -> dict:
        text = str(params.get("text", "")).strip()
        if not text:
            raise ValueError("Parâmetro 'text' não pode ser vazio.")

        if self._prompt_handler:
            self.set_assistant_state("thinking")
            try:
                reply = self._prompt_handler(text)
                self.set_assistant_state("idle")
                self.broadcast_event(
                    "reply_generated",
                    {"prompt": text, "reply": reply},
                )
                return {"prompt": text, "reply": reply}
            except Exception as e:
                self.set_assistant_state("idle")
                raise e
        else:
            return {"prompt": text, "reply": "Nenhum processador de prompt registrado."}

    def _handle_cancel(self, params: dict) -> dict:
        if self._cancel_handler:
            self._cancel_handler()
        self.set_assistant_state("idle")
        self.broadcast_event("cancelled", {"timestamp": time.time()})
        return {"cancelled": True}

    def _handle_diagnostics(self, params: dict) -> dict:
        from core.onboarding import OnboardingManager
        return OnboardingManager.run_full_diagnostics()

    def _handle_get_config(self, params: dict) -> dict:
        import config
        cfg = config.get_llm_config()
        cfg["audio"] = config.get_audio_config()
        return cfg

    def _handle_set_config(self, params: dict) -> dict:
        import config
        provider = params.get("provider") or params.get("llm_provider")
        host = params.get("ollama_host") or params.get("host")
        model = params.get("llm_model") or params.get("model")
        api_key = params.get("api_key") or params.get("llm_api_key")
        api_base = params.get("api_base") or params.get("llm_api_base")
        persist = bool(params.get("persist", True))
        updated = config.update_llm_config(
            provider=provider,
            host=host,
            model=model,
            api_key=api_key,
            api_base=api_base,
            persist=persist,
        )

        # Atualiza configurações de áudio se fornecidas
        if any(k in params for k in ("input_device", "audio_input_device", "output_device", "audio_output_device")):
            unset_marker = getattr(config, "_AUDIO_UNSET", object())
            in_dev = params.get("input_device", params.get("audio_input_device", unset_marker))
            out_dev = params.get("output_device", params.get("audio_output_device", unset_marker))
            audio_up = config.update_audio_config(
                input_device=in_dev,
                output_device=out_dev,
                persist=persist,
            )
            updated["audio"] = audio_up

        self.broadcast_event("config_changed", updated)
        return updated

    def _handle_get_audio_devices(self, params: dict) -> dict:
        from audio.device_utils import list_audio_devices
        return list_audio_devices()

    def _handle_get_audio_config(self, params: dict) -> dict:
        import config
        return config.get_audio_config()

    def _handle_set_audio_config(self, params: dict) -> dict:
        import config
        unset_marker = getattr(config, "_AUDIO_UNSET", object())
        in_dev = params.get("input_device", params.get("audio_input_device", unset_marker))
        out_dev = params.get("output_device", params.get("audio_output_device", unset_marker))
        persist = bool(params.get("persist", True))
        updated = config.update_audio_config(
            input_device=in_dev,
            output_device=out_dev,
            persist=persist,
        )
        self.broadcast_event("audio_config_changed", updated)
        return updated

    def _handle_test_audio_beep(self, params: dict) -> dict:
        from audio.player import AudioPlayer
        device = params.get("device")
        volume = params.get("volume")
        try:
            AudioPlayer.play_beep(volume=float(volume) if volume else None, device=device)
            return {"status": "ok", "message": "Beep reproduzido com sucesso."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _handle_get_tui_path_status(self, params: dict) -> dict:
        from core.cli_path import get_tui_path_status
        return get_tui_path_status()

    def _handle_export_tui_path(self, params: dict) -> dict:
        from core.cli_path import export_tui_path
        return export_tui_path()

    def _handle_pomodoro(self, params: dict) -> dict:
        from tools.timer import TimerManager
        sub_act = params.get("sub_action") or params.get("action") or "toggle"
        work_m = params.get("work_minutes")
        break_m = params.get("break_minutes")
        long_break_m = params.get("long_break_minutes")
        long_interval = params.get("long_break_interval")
        cycle = params.get("cycle")
        kwargs = {}
        if work_m is not None:
            kwargs["work_minutes"] = work_m
        if break_m is not None:
            kwargs["break_minutes"] = break_m
        if long_break_m is not None:
            kwargs["long_break_minutes"] = long_break_m
        if long_interval is not None:
            kwargs["long_break_interval"] = long_interval
        if cycle is not None:
            kwargs["cycle"] = cycle
        msg = TimerManager.pomodoro_control(sub_act, **kwargs)
        return {"status": "ok", "message": msg}

    def _handle_timer_add(self, params: dict) -> dict:
        from tools.timer import TimerManager
        hours = int(params.get("hours", 0))
        minutes = int(params.get("minutes", 0))
        seconds = int(params.get("seconds", 0))
        if "duration_sec" in params and not (hours or minutes or seconds):
            seconds = int(params["duration_sec"])
        label = params.get("label", "Timer")
        msg = TimerManager.add_timer(hours=hours, minutes=minutes, seconds=seconds, label=label)
        return {"status": "ok", "message": msg}


    def _handle_timer_cancel(self, params: dict) -> dict:
        from tools.timer import TimerManager
        ident = params.get("id") or params.get("label") or ""
        msg = TimerManager.cancel_timer(ident)
        return {"status": "ok", "message": msg}

    def _handle_alarm_add(self, params: dict) -> dict:
        from tools.timer import TimerManager
        time_str = params.get("time", "")
        label = params.get("label", "Alarme")
        msg = TimerManager.add_alarm(time_str, label)
        return {"status": "ok", "message": msg}

    def _handle_alarm_cancel(self, params: dict) -> dict:
        from tools.timer import TimerManager
        ident = params.get("id") or params.get("label") or ""
        msg = TimerManager.cancel_alarm(ident)
        return {"status": "ok", "message": msg}

    def _handle_check_ollama(self, params: dict) -> dict:
        from core.onboarding import OnboardingManager
        import config
        host = params.get("host") or params.get("ollama_host") or getattr(config, "OLLAMA_HOST", "http://localhost:11434")
        return OnboardingManager.check_ollama(host=host)

    def _handle_check_llm(self, params: dict) -> dict:
        from core.onboarding import OnboardingManager
        import config
        provider = params.get("provider") or getattr(config, "LLM_PROVIDER", "ollama")
        host = params.get("host") or params.get("ollama_host") or getattr(config, "OLLAMA_HOST", "http://localhost:11434")
        api_key = params.get("api_key")
        if api_key is None:
            api_key = getattr(config, "LLM_API_KEY", "")
        api_base = params.get("api_base") or getattr(config, "LLM_API_BASE", "")
        model = params.get("model") or params.get("llm_model") or getattr(config, "LLM_MODEL", "qwen2.5:3b")

        return OnboardingManager.check_llm_provider(
            provider=provider,
            host=host,
            api_key=api_key,
            api_base=api_base,
            model=model,
        )

    def _handle_detect_container(self, params: dict) -> dict:
        from core.onboarding import OnboardingManager
        info = OnboardingManager.detect_docker_ollama()
        if info:
            return {"detected": True, "container": info}
        return {"detected": False, "message": "Nenhum container Docker do Ollama detectado em execução."}

    def _handle_check_calendar(self, params: dict) -> dict:
        from core.onboarding import OnboardingManager
        return OnboardingManager.check_calendar_integration()

    def _handle_open_calendar(self, params: dict) -> dict:
        import webbrowser
        url = params.get("url") or "https://calendar.google.com"
        try:
            opened = webbrowser.open(url)
            return {"opened": opened, "url": url}
        except Exception as e:
            return {"opened": False, "url": url, "error": str(e)}

    async def _handle_auth_calendar(self, params: dict) -> dict:
        import asyncio
        import config
        from core.onboarding import OnboardingManager
        from core.paths import get_credentials_path

        # Se o cliente enviar chaves na chamada, salva imediatamente
        client_id = params.get("client_id")
        client_secret = params.get("client_secret")
        if client_id is not None or client_secret is not None:
            config.update_google_oauth_config(client_id=client_id, client_secret=client_secret)

        status = OnboardingManager.check_calendar_integration()
        if not status["credentials_exists"]:
            return {
                "success": False,
                "status": "missing_credentials",
                "message": (
                    "Nenhum Client ID do Google configurado. "
                    "Informe o Client ID do Google para conectar com 1 clique."
                ),
                "credentials_file": str(get_credentials_path()),
                "cloud_console_url": "https://console.cloud.google.com/apis/credentials",
            }

        try:
            from tools.calendar import CalendarTools
            # Executa o fluxo OAuth (que abre o navegador) em thread separada para não travar o WebSocket
            creds = await asyncio.to_thread(CalendarTools.authenticate)
            if creds:
                self.broadcast_event("calendar_status", {"status": "configured", "token_exists": True})
                return {"success": True, "status": "authenticated", "message": "Conta do Google vinculada com sucesso!"}
            return {"success": False, "status": "failed", "message": "A autorização no navegador foi cancelada ou falhou."}
        except Exception as e:
            return {"success": False, "status": "error", "message": str(e)}

    def _handle_disconnect_calendar(self, params: dict) -> dict:
        from core.paths import get_token_path
        from tools.calendar import CalendarTools
        token_path = get_token_path()
        if token_path.exists():
            try:
                token_path.unlink()
            except Exception:
                pass
        CalendarTools._service = None
        self.broadcast_event("calendar_status", {"status": "partial", "token_exists": False})
        return {"success": True, "status": "disconnected", "message": "Conta do Google desvinculada com sucesso."}

    def _handle_save_google_creds(self, params: dict) -> dict:
        import config
        client_id = params.get("client_id", "")
        client_secret = params.get("client_secret", "")
        updated = config.update_google_oauth_config(client_id=client_id, client_secret=client_secret)
        from core.onboarding import OnboardingManager
        status = OnboardingManager.check_calendar_integration()
        self.broadcast_event("calendar_status", status)
        return {"success": True, "config": updated, "status": status}


class IPCManager:
    """
    Gerenciador singleton para acesso global ao servidor IPC do Geraldo.
    Facilita emissão de eventos a partir de qualquer módulo sem acoplamento direto.
    """

    _instance: Optional[GeraldoIPCServer] = None
    _lock = threading.Lock()

    @classmethod
    def start(
        cls,
        host: str = "127.0.0.1",
        port: int = 8765,
        token: Optional[str] = None,
        require_auth: bool = False,
    ) -> GeraldoIPCServer:
        with cls._lock:
            if cls._instance is None:
                cls._instance = GeraldoIPCServer(
                    host=host,
                    port=port,
                    token=token,
                    require_auth=require_auth,
                )
                cls._instance.start()
            return cls._instance

    @classmethod
    def stop(cls) -> None:
        with cls._lock:
            if cls._instance:
                cls._instance.stop()
                cls._instance = None

    @classmethod
    def get_server(cls) -> Optional[GeraldoIPCServer]:
        return cls._instance

    @classmethod
    def is_running(cls) -> bool:
        return cls._instance is not None and cls._instance.is_running()

    @classmethod
    def broadcast(cls, event_name: str, data: Optional[dict] = None) -> None:
        """Transmite evento se o servidor estiver ativo, ignorando silenciosamente caso contrário."""
        if cls._instance and cls._instance.is_running():
            cls._instance.broadcast_event(event_name, data)

    @classmethod
    def set_state(cls, state: str, details: Optional[dict] = None) -> None:
        """Atualiza e transmite estado do assistente."""
        if cls._instance and cls._instance.is_running():
            cls._instance.set_assistant_state(state, details)

    @classmethod
    def is_muted(cls) -> bool:
        if cls._instance:
            return cls._instance.is_muted
        return False

    @classmethod
    def register_handler(cls, action: str, handler: Callable) -> None:
        if cls._instance:
            cls._instance.register_handler(action, handler)

    @classmethod
    def set_prompt_handler(cls, handler: Callable[[str], str]) -> None:
        if cls._instance:
            cls._instance.set_prompt_handler(handler)

    @classmethod
    def set_cancel_handler(cls, handler: Callable[[], None]) -> None:
        if cls._instance:
            cls._instance.set_cancel_handler(handler)

    @classmethod
    def reset_for_tests(cls) -> None:
        """Reinicia estado do singleton para testes limpos."""
        cls.stop()
