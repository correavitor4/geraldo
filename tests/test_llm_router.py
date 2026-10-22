"""Testes do fallback por LLM: classificação de comando em JSON quando o NLU não tem confiança."""
import json
import pytest
from unittest.mock import patch

from brain.llm import BrainLLM, LLM_ROUTES, parse_llm_route, build_router_prompt
from brain.nlu import TRAINING_DATA


def _ollama(content) -> dict:
    if not isinstance(content, str):
        content = json.dumps(content, ensure_ascii=False)
    return {"message": {"content": content}}


@pytest.fixture
def llm(shared_nlu_engine):
    with patch("brain.llm.IntentEngine", return_value=shared_nlu_engine):
        return BrainLLM(max_history_turns=4, provider="ollama")


class TestRouterHelpers:
    def test_routes_cover_all_nlu_intents(self):
        assert set(LLM_ROUTES) == set(TRAINING_DATA)

    def test_router_prompt_lists_every_intent(self):
        prompt = build_router_prompt()
        for name in LLM_ROUTES:
            assert f"- {name}:" in prompt

    @pytest.mark.parametrize("raw, expected", [
        ('{"intent": "get_time"}', {"intent": "get_time"}),
        ('Claro! {"intent": "conversa", "reply": "Oi"} fim', {"intent": "conversa", "reply": "Oi"}),
        ("texto puro sem json", None),
        ("{quebrado", None),
        ("", None),
        ("[1, 2]", None),
    ])
    def test_parse_llm_route(self, raw, expected):
        assert parse_llm_route(raw) == expected


class TestLLMFallback:
    def test_nlu_hit_never_calls_llm(self, llm):
        with patch("tools.system.SystemTools.get_current_time", return_value="São 10 horas."), \
             patch.object(BrainLLM, "_post_json") as mock_post:
            assert "10 horas" in llm.ask("que horas são")
            mock_post.assert_not_called()

    def test_llm_routes_to_command_and_uses_text_slots(self, llm):
        route = {"intent": "play_music", "slots": {"query": "Queen", "item_type": "auto"}}
        with patch.object(BrainLLM, "_post_json", return_value=_ollama(route)) as mock_post, \
             patch("tools.ytmusic.YTMusicPlayer.play_song", return_value="Tocando Queen.") as mock_play:
            resp = llm.ask("bota aquela banda do Freddie Mercury")
            assert "Tocando Queen" in resp
            mock_play.assert_called_once_with(query="Queen", item_type="auto")
            payload = mock_post.call_args[0][0]
            assert payload["format"] == "json"
            assert len(llm.history) == 0  # comandos não poluem o histórico de conversa

    def test_llm_cannot_override_numeric_slots(self, llm):
        route = {"intent": "set_timer", "slots": {"label": "Pizza", "minutes": 99}}
        with patch.object(BrainLLM, "_post_json", return_value=_ollama(route)), \
             patch.object(llm.nlu, "predict", return_value=("conversa_llm", 0.1, {})), \
             patch("tools.timer.TimerManager.add_timer", return_value="Timer criado.") as mock_timer:
            llm.ask("me cutuca em quinze minutos por causa da pizza")
            kwargs = mock_timer.call_args.kwargs
            assert kwargs["minutes"] == 15      # veio do Regex
            assert kwargs["label"] == "Pizza"   # veio da LLM

    def test_invalid_enum_slot_is_ignored(self, llm):
        route = {"intent": "volume_control", "slots": {"change": "rm -rf /"}}
        with patch.object(BrainLLM, "_post_json", return_value=_ollama(route)), \
             patch.object(llm.nlu, "predict", return_value=("conversa_llm", 0.1, {})), \
             patch("tools.system.SystemTools.set_volume", return_value="Volume ajustado.") as mock_vol:
            llm.ask("deixa o som mais alto aí")
            mock_vol.assert_called_once_with("+")

    def test_llm_conversation_json_reply(self, llm):
        route = {"intent": "conversa", "reply": "Pelo espalhamento Rayleigh."}
        with patch.object(BrainLLM, "_post_json", return_value=_ollama(route)):
            resp = llm.ask("Por que o céu é azul?")
            assert resp == "Pelo espalhamento Rayleigh."
            assert [m["role"] for m in llm.history] == ["user", "assistant"]
            assert llm.history[1]["content"] == resp  # histórico guarda o texto, não o JSON

    def test_unknown_intent_falls_back_to_reply(self, llm):
        route = {"intent": "desligar_computador", "reply": "Não posso fazer isso."}
        with patch.object(BrainLLM, "_post_json", return_value=_ollama(route)):
            assert llm.ask("Por que você não desliga o PC?") == "Não posso fazer isso."

    def test_empty_json_reply(self, llm):
        with patch.object(BrainLLM, "_post_json", return_value=_ollama({"intent": "conversa"})):
            assert "Não consegui" in llm.ask("Por que o céu é azul?")


class TestWarmup:
    def test_warmup_is_throttled(self, llm):
        with patch.object(BrainLLM, "_warmup_sync") as mock_sync:
            llm.warmup_async()
            llm.warmup_async()
            # a thread roda _warmup_sync; aguarda brevemente
            import time
            time.sleep(0.05)
            assert mock_sync.call_count == 1

    def test_warmup_skipped_for_external_provider(self):
        ext = BrainLLM(provider="groq", api_key="x")
        with patch.object(BrainLLM, "_warmup_sync") as mock_sync:
            ext.warmup_async()
            mock_sync.assert_not_called()

    def test_warmup_payload_loads_model_only(self, llm):
        with patch.object(BrainLLM, "_post_json", return_value={}) as mock_post:
            llm._warmup_sync()
            payload = mock_post.call_args[0][0]
            assert payload["messages"] == []
            assert payload["keep_alive"] == -1
