# tests/test_onboarding.py
import json
from unittest.mock import patch, MagicMock
from core.onboarding import OnboardingManager


class TestOnboardingManager:
    def test_check_voice_models_found(self):
        result = OnboardingManager.check_voice_models()
        assert "status" in result
        assert "found_models" in result
        # voz.onnx e voz_faber.onnx existem no repo local
        assert result["status"] == "ok"
        assert len(result["found_models"]) >= 1

    @patch("core.onboarding.resolve_model_path", return_value=None)
    def test_check_voice_models_missing(self, mock_resolve):
        result = OnboardingManager.check_voice_models()
        assert result["status"] == "missing"
        assert len(result["found_models"]) == 0

    def test_check_tts_engine(self):
        result = OnboardingManager.check_tts_engine()
        assert "status" in result
        assert result["status"] in ("ok", "warning")

    @patch("urllib.request.urlopen")
    def test_check_ollama_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps({
            "models": [{"name": "qwen2.5:3b:latest"}, {"name": "llama3:latest"}]
        }).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        mock_urlopen.return_value = mock_resp

        result = OnboardingManager.check_ollama("http://localhost:11434")
        assert result["status"] == "ok"
        assert result["connected"] is True
        assert result["target_model_installed"] is True
        assert len(result["available_models"]) == 2

    @patch("urllib.request.urlopen", side_effect=Exception("Connection refused"))
    def test_check_ollama_failure(self, mock_urlopen):
        result = OnboardingManager.check_ollama("http://127.0.0.1:9999")
        assert result["status"] == "unreachable"
        assert result["connected"] is False

    def test_check_calendar_integration(self):
        result = OnboardingManager.check_calendar_integration()
        assert "status" in result
        assert result["status"] in ("configured", "partial", "not_configured")

    def test_run_full_diagnostics(self):
        diag = OnboardingManager.run_full_diagnostics()
        assert "ready" in diag
        assert "platform" in diag
        assert "checks" in diag
        assert "voice_models" in diag["checks"]
        assert "tts_engine" in diag["checks"]
        assert "ollama" in diag["checks"]
        assert "calendar" in diag["checks"]
