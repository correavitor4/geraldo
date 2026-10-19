import asyncio
import json
import pytest
from websockets.asyncio.client import connect

from core.ipc import GeraldoIPCServer, IPCManager

TEST_PORT = 8789
TEST_HOST = "127.0.0.1"


@pytest.fixture
def ipc_server():
    """Fixture que inicia e encerra um servidor IPC para testes."""
    server = GeraldoIPCServer(host=TEST_HOST, port=TEST_PORT, require_auth=False)
    server.start()
    yield server
    server.stop()


@pytest.mark.anyio
async def test_ipc_server_lifecycle_and_connect(ipc_server):
    assert ipc_server.is_running()

    uri = f"ws://{TEST_HOST}:{TEST_PORT}"
    async with connect(uri) as ws:
        # Primeiro pacote recebido deve ser o evento de boas-vindas / connected
        msg_raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        msg = json.loads(msg_raw)

        assert msg["type"] == "event"
        assert msg["event"] == "connected"
        assert msg["data"]["assistant_state"] == "idle"
        assert msg["data"]["is_muted"] is False


@pytest.mark.anyio
async def test_ipc_ping_and_get_state(ipc_server):
    uri = f"ws://{TEST_HOST}:{TEST_PORT}"
    async with connect(uri) as ws:
        # Descarta evento de boas-vindas
        await ws.recv()

        # Envia comando ping
        await ws.send(json.dumps({"id": "req-1", "action": "ping"}))
        resp_raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        resp = json.loads(resp_raw)

        assert resp["type"] == "response"
        assert resp["id"] == "req-1"
        assert resp["status"] == "ok"
        assert resp["data"]["pong"] is True

        # Envia comando get_state
        await ws.send(json.dumps({"id": "req-2", "action": "get_state"}))
        resp2_raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        resp2 = json.loads(resp2_raw)

        assert resp2["id"] == "req-2"
        assert resp2["data"]["assistant_state"] == "idle"
        assert resp2["data"]["is_muted"] is False


@pytest.mark.anyio
async def test_ipc_toggle_mute_and_broadcast(ipc_server):
    uri = f"ws://{TEST_HOST}:{TEST_PORT}"
    async with connect(uri) as ws:
        await ws.recv()  # welcome

        # Alterna mudo via RPC
        await ws.send(json.dumps({"id": "req-mute", "action": "toggle_mute"}))

        # Deve receber tanto o evento broadcast de mute_changed quanto a resposta RPC
        messages = []
        for _ in range(2):
            raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            messages.append(json.loads(raw))

        event_msg = next(m for m in messages if m.get("type") == "event")
        resp_msg = next(m for m in messages if m.get("type") == "response")

        assert event_msg["event"] == "mute_changed"
        assert event_msg["data"]["muted"] is True
        assert resp_msg["data"]["muted"] is True
        assert ipc_server.is_muted is True

        # Testa set_mute(False)
        await ws.send(json.dumps({"id": "req-unmute", "action": "set_mute", "params": {"muted": False}}))
        raw_resp = await asyncio.wait_for(ws.recv(), timeout=2.0)
        # Pode vir evento ou resposta primeiro
        assert ipc_server.is_muted is False


@pytest.mark.anyio
async def test_ipc_send_prompt_with_handler(ipc_server):
    def mock_prompt_handler(text: str) -> str:
        return f"Echo: {text}"

    ipc_server.set_prompt_handler(mock_prompt_handler)

    uri = f"ws://{TEST_HOST}:{TEST_PORT}"
    async with connect(uri) as ws:
        await ws.recv()  # welcome

        # Envia prompt de texto
        cmd = {"id": "p-1", "action": "send_prompt", "params": {"text": "teste de comando"}}
        await ws.send(json.dumps(cmd))

        # Recebe mensagens geradas
        received = []
        while len(received) < 4:  # state(thinking), state(idle), event(reply_generated), response
            raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            msg = json.loads(raw)
            received.append(msg)
            if msg.get("type") == "response" and msg.get("id") == "p-1":
                break

        resp = next(m for m in received if m.get("type") == "response" and m.get("id") == "p-1")
        assert resp["status"] == "ok"
        assert resp["data"]["reply"] == "Echo: teste de comando"


@pytest.mark.anyio
async def test_ipc_send_prompt_empty_validation(ipc_server):
    uri = f"ws://{TEST_HOST}:{TEST_PORT}"
    async with connect(uri) as ws:
        await ws.recv()  # welcome

        cmd = {"id": "err-1", "action": "send_prompt", "params": {"text": "   "}}
        await ws.send(json.dumps(cmd))

        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        msg = json.loads(raw)

        assert msg["type"] == "response"
        assert msg["id"] == "err-1"
        assert msg["status"] == "error"
        assert "não pode ser vazio" in msg["error"]


@pytest.mark.anyio
async def test_ipc_cancel_handler(ipc_server):
    cancel_called = False

    def on_cancel():
        nonlocal cancel_called
        cancel_called = True

    ipc_server.set_cancel_handler(on_cancel)

    uri = f"ws://{TEST_HOST}:{TEST_PORT}"
    async with connect(uri) as ws:
        await ws.recv()  # welcome

        await ws.send(json.dumps({"id": "c-1", "action": "cancel"}))

        # Espera resposta
        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        # Pode ser evento de cancelamento ou resposta
        msgs = [json.loads(raw)]
        raw2 = await asyncio.wait_for(ws.recv(), timeout=2.0)
        msgs.append(json.loads(raw2))

        resp = next(m for m in msgs if m.get("type") == "response")
        assert resp["status"] == "ok"
        assert resp["data"]["cancelled"] is True
        assert cancel_called is True


@pytest.mark.anyio
async def test_ipc_custom_handler(ipc_server):
    def custom_sum(params: dict) -> dict:
        a = params.get("a", 0)
        b = params.get("b", 0)
        return {"sum": a + b}

    ipc_server.register_handler("math.add", custom_sum)

    uri = f"ws://{TEST_HOST}:{TEST_PORT}"
    async with connect(uri) as ws:
        await ws.recv()  # welcome

        cmd = {"id": "m-1", "action": "math.add", "params": {"a": 10, "b": 32}}
        await ws.send(json.dumps(cmd))

        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        resp = json.loads(raw)

        assert resp["status"] == "ok"
        assert resp["data"]["sum"] == 42


@pytest.mark.anyio
async def test_ipc_unknown_action_and_invalid_json(ipc_server):
    uri = f"ws://{TEST_HOST}:{TEST_PORT}"
    async with connect(uri) as ws:
        await ws.recv()  # welcome

        # JSON quebrado
        await ws.send("nao-e-json")
        raw_err = await asyncio.wait_for(ws.recv(), timeout=2.0)
        err_msg = json.loads(raw_err)
        assert err_msg["status"] == "error"
        assert "inválido" in err_msg["error"]

        # Ação desconhecida
        await ws.send(json.dumps({"id": "unknown-1", "action": "voar_para_a_lua"}))
        raw_unknown = await asyncio.wait_for(ws.recv(), timeout=2.0)
        unknown_msg = json.loads(raw_unknown)
        assert unknown_msg["status"] == "error"
        assert "Ação desconhecida" in unknown_msg["error"]


@pytest.mark.anyio
async def test_ipc_authentication_flow():
    auth_port = 8790
    secret_token = "segredo123"
    server = GeraldoIPCServer(
        host=TEST_HOST, port=auth_port, token=secret_token, require_auth=True
    )
    server.start()

    try:
        uri = f"ws://{TEST_HOST}:{auth_port}"

        # 1. Cliente tenta rodar comando sem autenticar
        async with connect(uri) as ws:
            await ws.recv()  # welcome informando auth_required=True
            await ws.send(json.dumps({"id": "no-auth", "action": "ping"}))
            raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            res = json.loads(raw)
            assert res["status"] == "error"
            assert "Não autenticado" in res["error"]

        # 2. Cliente tenta autenticar com token errado
        async with connect(uri) as ws:
            await ws.recv()
            await ws.send(json.dumps({"id": "auth-fail", "action": "auth", "token": "errado"}))
            raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            res = json.loads(raw)
            assert res["status"] == "error"
            assert "inválido" in res["error"]

        # 3. Cliente autentica com token correto e executa ping
        async with connect(uri) as ws:
            await ws.recv()
            await ws.send(json.dumps({"id": "auth-ok", "action": "auth", "token": secret_token}))
            raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            res = json.loads(raw)
            assert res["status"] == "ok"
            assert res["data"]["authenticated"] is True

            # Agora comando funciona
            await ws.send(json.dumps({"id": "ping-after", "action": "ping"}))
            raw_ping = await asyncio.wait_for(ws.recv(), timeout=2.0)
            res_ping = json.loads(raw_ping)
            assert res_ping["status"] == "ok"
            assert res_ping["data"]["pong"] is True

    finally:
        server.stop()


def test_ipc_manager_singleton_operations():
    IPCManager.reset_for_tests()
    assert not IPCManager.is_running()

    # Operações em manager desligado não devem explodir
    IPCManager.broadcast("test_event", {"foo": "bar"})
    IPCManager.set_state("thinking")
    assert IPCManager.is_muted() is False

    mgr_port = 8791
    srv = IPCManager.start(host=TEST_HOST, port=mgr_port)
    assert IPCManager.is_running()
    assert IPCManager.get_server() is srv

    IPCManager.set_state("listening")
    assert srv.assistant_state == "listening"

    IPCManager.stop()
    assert not IPCManager.is_running()


@pytest.mark.anyio
async def test_ipc_get_and_set_config(ipc_server):
    import config
    orig_host = config.OLLAMA_HOST
    orig_model = config.LLM_MODEL

    try:
        uri = f"ws://{TEST_HOST}:{TEST_PORT}"
        async with connect(uri) as ws:
            init_raw = await ws.recv()
            init_data = json.loads(init_raw)["data"]
            assert "config" in init_data

            # 1. Obter config atual
            await ws.send(json.dumps({"id": "cfg-1", "action": "get_config"}))
            resp1 = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            assert resp1["status"] == "ok"
            assert "ollama_host" in resp1["data"]
            assert "llm_model" in resp1["data"]

            # 2. Atualizar config
            await ws.send(json.dumps({
                "id": "cfg-2",
                "action": "set_config",
                "params": {
                    "ollama_host": "http://ollama-docker:11434",
                    "llm_model": "llama3.2:3b",
                    "persist": False,
                }
            }))

            # Recebe a resposta e o evento de broadcast
            msg_a = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            msg_b = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            messages = [msg_a, msg_b]

            event_msg = next((m for m in messages if m.get("type") == "event"), None)
            resp_msg = next((m for m in messages if m.get("type") == "response"), None)

            assert event_msg is not None
            assert event_msg["event"] == "config_changed"
            assert event_msg["data"]["ollama_host"] == "http://ollama-docker:11434"

            assert resp_msg is not None
            assert resp_msg["data"]["llm_model"] == "llama3.2:3b"
    finally:
        config.OLLAMA_HOST = orig_host
        config.LLM_MODEL = orig_model

