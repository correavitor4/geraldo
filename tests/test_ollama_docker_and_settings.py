"""
Bateria massiva de testes para validação da conectividade com Ollama (Docker/Local),
detecção automática de containers, resiliência do modal de configurações e links externos na interface desktop.
"""
import asyncio
import json
import os
import re
import urllib.error
from unittest.mock import MagicMock, patch
import pytest
from websockets.asyncio.client import connect

import config
from core.onboarding import OnboardingManager
from core.ipc import GeraldoIPCServer, IPCManager

TEST_PORT = 8792
TEST_HOST = "127.0.0.1"


# ============================================================================
# 1. TESTES DE NORMALIZAÇÃO DE HOST E URL DO OLLAMA
# ============================================================================

class TestOllamaHostNormalization:
    """Valida normalização de strings de host do Ollama passadas pelo usuário na UI."""

    def test_normalize_without_protocol(self):
        """Host sem 'http://' (ex: localhost:11434) deve ser automaticamente prefixado."""
        with patch.object(OnboardingManager, "_ping_tags", return_value=(True, ["qwen2.5:3b"], "")):
            result = OnboardingManager.check_ollama("localhost:11434")
            assert result["connected"] is True
            assert result["host"] == "http://localhost:11434"

    def test_normalize_ip_without_protocol(self):
        """IP sem 'http://' (ex: 127.0.0.1:11434) deve ser prefixado."""
        with patch.object(OnboardingManager, "_ping_tags", return_value=(True, ["qwen2.5:3b"], "")):
            result = OnboardingManager.check_ollama("127.0.0.1:11434")
            assert result["connected"] is True
            assert result["host"] == "http://127.0.0.1:11434"

    def test_normalize_trailing_slashes_and_whitespace(self):
        """Espaços e barras finais devem ser limpos."""
        with patch.object(OnboardingManager, "_ping_tags", return_value=(True, ["qwen2.5:3b"], "")):
            result = OnboardingManager.check_ollama("   http://localhost:11434///   ")
            assert result["connected"] is True
            assert result["host"] == "http://localhost:11434"

    def test_normalize_empty_host_uses_default(self):
        """Host vazio deve usar o valor padrão http://localhost:11434."""
        with patch.object(OnboardingManager, "_ping_tags", return_value=(True, ["qwen2.5:3b"], "")):
            result = OnboardingManager.check_ollama("")
            assert result["connected"] is True
            assert result["host"] == "http://localhost:11434"


# ============================================================================
# 2. TESTES DE DETECÇÃO DE CONTAINER DOCKER DO OLLAMA
# ============================================================================

class TestDockerContainerDetection:
    """Valida identificação do container do Ollama via SDK do Docker e CLI fallback."""

    def test_detect_docker_via_sdk_success(self):
        """Simula container 'ollama' rodando com porta 11434 mapeada para o host."""
        mock_container = MagicMock()
        mock_container.name = "ollama"
        mock_container.image.tags = ["ollama/ollama:latest"]
        mock_container.status = "running"
        mock_container.short_id = "abc12345"
        mock_container.ports = {
            "11434/tcp": [{"HostIp": "0.0.0.0", "HostPort": "11434"}]
        }

        mock_client = MagicMock()
        mock_client.containers.list.return_value = [mock_container]

        with patch("docker.from_env", return_value=mock_client):
            info = OnboardingManager.detect_docker_ollama()
            assert info is not None
            assert info["container_name"] == "ollama"
            assert info["mapped_port"] == 11434
            assert info["host_url"] == "http://localhost:11434"
            assert info["status"] == "running"

    def test_detect_docker_custom_mapped_port(self):
        """Simula container Ollama mapeado em porta customizada (ex: 21434)."""
        mock_container = MagicMock()
        mock_container.name = "ollama-gpu"
        mock_container.image.tags = ["ollama/ollama:latest"]
        mock_container.status = "running"
        mock_container.short_id = "def67890"
        mock_container.ports = {
            "11434/tcp": [{"HostIp": "0.0.0.0", "HostPort": "21434"}]
        }

        mock_client = MagicMock()
        mock_client.containers.list.return_value = [mock_container]

        with patch("docker.from_env", return_value=mock_client):
            info = OnboardingManager.detect_docker_ollama()
            assert info is not None
            assert info["mapped_port"] == 21434
            assert info["host_url"] == "http://localhost:21434"

    def test_detect_docker_cli_fallback(self):
        """Se o SDK do Docker falhar, deve usar subprocess chamando 'docker ps'."""
        cli_output = "9b145877d541|ollama|ollama/ollama:latest|0.0.0.0:11434->11434/tcp\n"

        with patch("docker.from_env", side_effect=Exception("Socket not available")):
            with patch("subprocess.check_output", return_value=cli_output):
                info = OnboardingManager.detect_docker_ollama()
                assert info is not None
                assert info["container_name"] == "ollama"
                assert info["mapped_port"] == 11434
                assert info["host_url"] == "http://localhost:11434"

    def test_detect_docker_none_when_no_containers(self):
        """Se nenhum container Ollama estiver rodando, retorna None sem crashar."""
        mock_client = MagicMock()
        mock_client.containers.list.return_value = []

        with patch("docker.from_env", return_value=mock_client):
            with patch("subprocess.check_output", side_effect=Exception("No docker command")):
                info = OnboardingManager.detect_docker_ollama()
                assert info is None


# ============================================================================
# 3. TESTES DE RECUPERAÇÃO AUTOMÁTICA DE HOST CONTAINER (http://ollama:11434)
# ============================================================================

class TestOllamaContainerFallback:
    """Valida recuperação automática caso o usuário informe http://ollama:11434."""

    def test_container_dns_fails_and_falls_back_to_localhost(self):
        """Quando http://ollama:11434 falha no DNS do host, faz fallback para o container em localhost."""
        def side_effect(url, timeout=2.0):
            if "ollama:11434" in url:
                return False, [], "getaddrinfo failed"
            if "localhost:11434" in url or "127.0.0.1:11434" in url:
                return True, ["qwen2.5:3b", "llama3.2:3b"], ""
            return False, [], "connection refused"

        fake_docker_info = {
            "container_id": "9b145877d541",
            "container_name": "ollama",
            "status": "running",
            "mapped_port": 11434,
            "host_url": "http://localhost:11434",
            "method": "docker-sdk",
        }

        with patch.object(OnboardingManager, "detect_docker_ollama", return_value=fake_docker_info):
            with patch.object(OnboardingManager, "_ping_tags", side_effect=side_effect):
                result = OnboardingManager.check_ollama("http://ollama:11434")
                assert result["connected"] is True
                assert result["status"] == "ok"
                assert result["host"] == "http://localhost:11434"
                assert result["suggested_host"] == "http://localhost:11434"
                assert result["container_detected"] is True
                assert "qwen2.5:3b" in result["available_models"]
                assert result["target_model_installed"] is True
                assert "detectado ativo" in result["message"]

    def test_all_fallbacks_fail_produces_detailed_diagnostics(self):
        """Se o container estiver rodando mas a porta não responder, avisa com precisão."""
        fake_docker_info = {
            "container_id": "9b145877d541",
            "container_name": "ollama",
            "status": "running",
            "mapped_port": 11434,
            "host_url": "http://localhost:11434",
            "method": "docker-sdk",
        }

        with patch.object(OnboardingManager, "detect_docker_ollama", return_value=fake_docker_info):
            with patch.object(OnboardingManager, "_ping_tags", return_value=(False, [], "connection refused")):
                result = OnboardingManager.check_ollama("http://localhost:11434")
                assert result["connected"] is False
                assert result["status"] == "unreachable"
                assert "Container Docker 'ollama' está em execução" in result["message"]


# ============================================================================
# 4. TESTES DE PROVEDORES EXTERNOS (CHECK_LLM_PROVIDER & CHECK_EXTERNAL_LLM)
# ============================================================================

class TestExternalLLMProviderCheck:
    """Valida compatibilidade de parâmetros api_base / base_url e respostas do verificador."""

    def test_check_llm_provider_accepts_api_base_kwarg(self):
        """Verifica se check_llm_provider aceita api_base sem lançar TypeError."""
        with patch.object(OnboardingManager, "check_external_llm") as mock_check:
            mock_check.return_value = {"status": "ok", "connected": True}
            result = OnboardingManager.check_llm_provider(
                provider="groq",
                api_key="gsk_valid_key_12345",
                api_base="https://api.groq.com/openai/v1",
                model="llama-3.3-70b-versatile",
            )
            assert result["connected"] is True
            mock_check.assert_called_once()
            args, kwargs = mock_check.call_args
            assert kwargs["base_url"] == "https://api.groq.com/openai/v1"
            assert kwargs["api_key"] == "gsk_valid_key_12345"
            assert kwargs["model"] == "llama-3.3-70b-versatile"

    def test_check_llm_provider_ollama_dispatch(self):
        """Quando provider='ollama', check_llm_provider despacha para check_ollama."""
        with patch.object(OnboardingManager, "check_ollama") as mock_ollama:
            mock_ollama.return_value = {"status": "ok", "connected": True}
            result = OnboardingManager.check_llm_provider(provider="ollama", host="http://localhost:11434")
            assert result["connected"] is True
            mock_ollama.assert_called_once_with(host="http://localhost:11434", timeout=5.0)

    def test_check_external_llm_empty_api_key_error(self):
        """Verifica rejeição imediata com mensagem clara para chave vazia."""
        res = OnboardingManager.check_external_llm(base_url="https://api.openai.com/v1", api_key="")
        assert res["connected"] is False
        assert res["status"] == "error"
        assert "API Key vazia" in res["error"]


# ============================================================================
# 5. TESTES DO BARRAMENTO IPC (WEBSOCKET RPC)
# ============================================================================

class TestIPCWebSocketSettingsContract:
    """Valida o ciclo completo de RPC para detecção de containers e salvamento de configurações."""

    @pytest.mark.anyio
    async def test_detect_container_action_via_ipc(self):
        """Valida ação 'detect_container' sobre o canal WebSocket."""
        server = GeraldoIPCServer(host=TEST_HOST, port=TEST_PORT)
        server.start()
        await asyncio.sleep(0.05)

        uri = f"ws://{TEST_HOST}:{TEST_PORT}"
        try:
            async with connect(uri) as ws:
                # Descarta mensagem inicial 'connected'
                await ws.recv()

                fake_container = {
                    "container_id": "test1234",
                    "container_name": "ollama",
                    "status": "running",
                    "mapped_port": 11434,
                    "host_url": "http://localhost:11434",
                }

                with patch.object(OnboardingManager, "detect_docker_ollama", return_value=fake_container):
                    req = {"id": "req-detect-1", "action": "detect_container", "params": {}}
                    await ws.send(json.dumps(req))

                    raw_resp = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    resp = json.loads(raw_resp)

                    assert resp["type"] == "response"
                    assert resp["id"] == "req-detect-1"
                    assert resp["status"] == "ok"
                    assert resp["data"]["detected"] is True
                    assert resp["data"]["container"]["container_name"] == "ollama"
        finally:
            server.stop()

    @pytest.mark.anyio
    async def test_check_ollama_action_via_ipc(self):
        """Valida ação 'check_ollama' via IPC."""
        server = GeraldoIPCServer(host=TEST_HOST, port=TEST_PORT + 1)
        server.start()
        await asyncio.sleep(0.05)

        uri = f"ws://{TEST_HOST}:{TEST_PORT + 1}"
        try:
            async with connect(uri) as ws:
                await ws.recv()

                with patch.object(OnboardingManager, "check_ollama", return_value={"status": "ok", "connected": True, "models": ["qwen2.5:3b"]}):
                    req = {"id": "check-ollama-99", "action": "check_ollama", "params": {"host": "http://localhost:11434"}}
                    await ws.send(json.dumps(req))

                    raw_resp = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    resp = json.loads(raw_resp)

                    assert resp["status"] == "ok"
                    assert resp["data"]["connected"] is True
        finally:
            server.stop()

    @pytest.mark.anyio
    async def test_set_and_get_config_action_via_ipc(self):
        """Valida salvamento e leitura de configuração completa via IPC."""
        server = GeraldoIPCServer(host=TEST_HOST, port=TEST_PORT + 2)
        server.start()
        await asyncio.sleep(0.05)

        uri = f"ws://{TEST_HOST}:{TEST_PORT + 2}"
        try:
            async with connect(uri) as ws:
                await ws.recv()

                # Salva nova configuração
                req_set = {
                    "id": "set_config-123",
                    "action": "set_config",
                    "params": {
                        "provider": "ollama",
                        "ollama_host": "http://localhost:11434",
                        "llm_model": "qwen2.5:3b",
                        "persist": False,
                    }
                }
                await ws.send(json.dumps(req_set))

                # Espera evento de broadcast e resposta da RPC
                msg1 = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
                msg2 = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
                msgs = [msg1, msg2]

                resp = next(m for m in msgs if m.get("type") == "response" and m.get("id") == "set_config-123")
                event = next(m for m in msgs if m.get("type") == "event" and m.get("event") == "config_changed")

                assert resp["status"] == "ok"
                assert resp["data"]["ollama_host"] == "http://localhost:11434"
                assert resp["data"]["llm_model"] == "qwen2.5:3b"
                assert event["data"]["provider"] == "ollama"
        finally:
            server.stop()


# ============================================================================
# 6. TESTES DA INTERFACE WEB/DESKTOP (HTML, CSS & JS)
# ============================================================================

class TestDesktopUIElementsAndScript:
    """Valida presença dos elementos de detecção de container, botões de ação e scripts."""

    @pytest.fixture(autouse=True)
    def setup_paths(self):
        base = os.path.dirname(__file__)
        self.html_path = os.path.abspath(os.path.join(base, "..", "desktop-ui", "index.html"))
        self.js_path = os.path.abspath(os.path.join(base, "..", "desktop-ui", "app.js"))
        self.css_path = os.path.abspath(os.path.join(base, "..", "desktop-ui", "styles.css"))

    def test_html_contains_detect_container_button(self):
        """Verifica se o botão de auto-detecção de container está presente no index.html."""
        with open(self.html_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert 'id="btn-detect-container"' in content
        assert "Detectar Container" in content

    def test_html_contains_save_and_test_buttons(self):
        """Verifica se os botões de ação do modal estão definidos com IDs corretos."""
        with open(self.html_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert 'id="btn-save-settings"' in content
        assert 'id="btn-test-ollama"' in content
        assert 'id="api-key-link"' in content

    def test_js_contains_local_config_caching_and_load(self):
        """Verifica se o app.js implementa loadLocalConfig para persistência imediata."""
        with open(self.js_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "loadLocalConfig()" in content
        assert "localStorage.getItem(\"geraldo_llm_config\")" in content
        assert "localStorage.setItem(\"geraldo_llm_config\"" in content

    def test_js_contains_open_external_url_handler(self):
        """Verifica se o app.js suporta invocação do comando Tauri para abrir links no browser."""
        with open(self.js_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "openExternalUrl" in content
        assert "open_external_url" in content
        assert "window.open" in content

    def test_js_contains_detect_container_handler(self):
        """Verifica se o app.js implementa detectOllamaContainer."""
        with open(self.js_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "detectOllamaContainer()" in content
        assert '"detect_container"' in content

    def test_js_handles_save_settings_feedback_when_disconnected(self):
        """Verifica se o app.js lida com salvar configurações de forma graciosa mesmo sem daemon."""
        with open(self.js_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "SALVO NO APP" in content
        assert "SALVO COM SUCESSO" in content


# ============================================================================
# 7. TESTES DE INTEGRAÇÃO TAURI (MAIN.RS)
# ============================================================================

class TestTauriMainRsIntegration:
    """Valida se o código Rust em src-tauri/src/main.rs expõe o comando de link externo."""

    def test_main_rs_has_open_external_url_command(self):
        main_rs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src-tauri", "src", "main.rs"))
        with open(main_rs_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "fn open_external_url" in content
        assert "open_external_url" in content
        assert "tauri::generate_handler![get_desktop_version, is_daemon_active, open_external_url]" in content

    def test_main_rs_has_windows_sidecar_candidates(self):
        main_rs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src-tauri", "src", "main.rs"))
        with open(main_rs_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "geraldo-core.exe" in content
        assert "geraldo-core-x86_64-pc-windows-msvc.exe" in content


# ============================================================================
# 8. TESTE AO VIVO COM O CONTAINER OLLAMA REAL (SE DISPONÍVEL NO SISTEMA)
# ============================================================================

class TestLiveOllamaDockerConnection:
    """Executa verificação real contra o daemon ou container Ollama rodando no SO do usuário."""

    def test_live_check_ollama_or_container(self):
        """Se o container estiver rodando (como detectado nesta máquina), valida conexão real."""
        result = OnboardingManager.check_ollama()
        # Se houver Ollama ativo, valida que conectou
        if result.get("connected"):
            assert result["status"] == "ok"
            assert isinstance(result["available_models"], list)
            assert len(result["available_models"]) >= 1
            assert "qwen2.5:3b" in result["available_models"]
            assert result["target_model_installed"] is True
            print(f"\n[Sucesso ao vivo]: Conectado ao container Ollama! Modelos: {result['available_models']}")
        else:
            # Se não estiver rodando no momento da execução isolada, valida que mensagem é instrutiva
            assert "Ollama inacessível" in result["message"] or "Container Docker" in result["message"]
