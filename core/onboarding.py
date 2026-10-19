# core/onboarding.py
"""
Módulo de Onboarding e Diagnóstico de Sistema do Geraldo.
Verifica a integridade do ambiente, modelos de voz locais,
conectividade do Ollama e permissões de áudio para distribuição comercial.
"""
import sys
import shutil
import urllib.request
import json
from typing import Dict, Any
from core.paths import (
    resolve_model_path,
    get_user_data_dir,
    get_temp_dir,
    get_credentials_path,
    get_token_path,
    is_frozen,
)
import config


class OnboardingManager:
    """Gerencia a verificação de primeiro uso e diagnóstico do Geraldo."""

    DEFAULT_VOICE_MODELS = ["voz_faber.onnx", "voz.onnx"]

    @classmethod
    def check_voice_models(cls) -> Dict[str, Any]:
        """Verifica se pelo menos um modelo de voz ONNX e seu JSON associado estão presentes."""
        found_models = []
        for name in cls.DEFAULT_VOICE_MODELS:
            model_path = resolve_model_path(name)
            if model_path:
                json_path = resolve_model_path(f"{name}.json")
                found_models.append({
                    "model": name,
                    "model_path": str(model_path),
                    "json_config_found": json_path is not None,
                })

        return {
            "status": "ok" if len(found_models) > 0 else "missing",
            "found_models": found_models,
            "message": "Modelos de voz locais encontrados." if found_models else "Nenhum modelo de voz ONNX localizado.",
        }

    @classmethod
    def check_tts_engine(cls) -> Dict[str, Any]:
        """Verifica se o motor Piper TTS está acessível (como módulo Python ou binário)."""
        has_binary = shutil.which("piper") is not None
        has_module = False
        try:
            import piper
            has_module = True
        except ImportError:
            pass

        available = has_binary or has_module
        return {
            "status": "ok" if available else "warning",
            "has_binary": has_binary,
            "has_module": has_module,
            "message": "Motor Piper TTS operacional." if available else "Piper TTS não encontrado em PATH nem como módulo.",
        }

    @classmethod
    def check_ollama(cls, host: str = None, timeout: float = 2.0) -> Dict[str, Any]:
        """Verifica se o serviço Ollama local está ativo e respondendo."""
        ollama_url = host or getattr(config, "OLLAMA_HOST", "http://localhost:11434")
        api_tags_url = f"{ollama_url.rstrip('/')}/api/tags"

        try:
            req = urllib.request.Request(api_tags_url, headers={"User-Agent": "Geraldo-Onboarding/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("name") for m in data.get("models", [])]
                    target_model = getattr(config, "LLM_MODEL", "qwen2.5:3b")
                    has_target = any(target_model in m for m in models)
                    return {
                        "status": "ok",
                        "connected": True,
                        "available_models": models,
                        "target_model": target_model,
                        "target_model_installed": has_target,
                        "message": f"Ollama ativo com {len(models)} modelos.",
                    }
        except Exception as e:
            return {
                "status": "unreachable",
                "connected": False,
                "error": str(e),
                "message": f"Ollama inacessível em {ollama_url}. Verifique se 'ollama serve' está rodando.",
            }

    @classmethod
    def check_external_llm(
        cls,
        base_url: str,
        api_key: str,
        model: str = None,
        timeout: float = 6.0,
    ) -> Dict[str, Any]:
        """Testa conectividade e autenticação com um provedor LLM externo (OpenAI-compatível)."""
        if not api_key:
            return {
                "status": "error",
                "connected": False,
                "error": "API Key vazia.",
                "message": "Por favor, informe a API Key do provedor.",
            }

        clean_base = (base_url or "https://api.openai.com/v1").rstrip("/")
        url = f"{clean_base}/chat/completions"
        target_model = model or "gpt-4o-mini"

        payload = {
            "model": target_model,
            "messages": [{"role": "user", "content": "teste de conexao"}],
            "max_tokens": 5,
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {api_key.strip()}",
                    "Content-Type": "application/json",
                    "User-Agent": "Geraldo-Assistant/1.0",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return {
                        "status": "ok",
                        "connected": True,
                        "model": target_model,
                        "message": f"Conexão com provedor externo validada com sucesso! (modelo: {target_model})",
                    }
                else:
                    return {
                        "status": "error",
                        "connected": False,
                        "message": f"Serviço retornou código HTTP {resp.status}.",
                    }
        except urllib.error.HTTPError as he:
            err_msg = ""
            try:
                raw_body = he.read().decode("utf-8")
                err_json = json.loads(raw_body)
                err_msg = err_json.get("error", {}).get("message", raw_body)
            except Exception:
                err_msg = str(he)
            return {
                "status": "error",
                "connected": False,
                "error": f"HTTP {he.code}: {err_msg}",
                "message": f"Falha na API (HTTP {he.code}): {err_msg}",
            }
        except Exception as e:
            return {
                "status": "error",
                "connected": False,
                "error": str(e),
                "message": f"Falha ao conectar em {url}: {e}",
            }

    @classmethod
    def check_llm_provider(
        cls,
        provider: str = None,
        host: str = None,
        base_url: str = None,
        api_key: str = None,
        model: str = None,
        timeout: float = 5.0,
    ) -> Dict[str, Any]:
        """Testa o provedor configurado (Ollama ou provedor externo com API Key)."""
        prov = (provider or getattr(config, "LLM_PROVIDER", "ollama")).lower().strip()
        if prov == "ollama":
            return cls.check_ollama(host=host or getattr(config, "OLLAMA_HOST", "http://localhost:11434"), timeout=timeout)
        else:
            key = api_key if api_key is not None else getattr(config, "LLM_API_KEY", "")
            base = base_url or getattr(config, "LLM_API_BASE", "") or (config.PROVIDER_PRESETS.get(prov, {}).get("default_base", ""))
            target_model = model or getattr(config, "LLM_MODEL", "") or (config.PROVIDER_PRESETS.get(prov, {}).get("default_model", ""))
            return cls.check_external_llm(base_url=base, api_key=key, model=target_model, timeout=timeout)


    @classmethod
    def check_calendar_integration(cls) -> Dict[str, Any]:
        """Verifica se as credenciais do Google Calendar estão configuradas."""
        creds_path = get_credentials_path()
        token_path = get_token_path()

        has_creds = creds_path.exists()
        has_token = token_path.exists()

        return {
            "status": "configured" if (has_creds and has_token) else "partial" if has_creds else "not_configured",
            "credentials_file": str(creds_path),
            "credentials_exists": has_creds,
            "token_file": str(token_path),
            "token_exists": has_token,
        }

    @classmethod
    def run_full_diagnostics(cls) -> Dict[str, Any]:
        """Executa um diagnóstico completo e retorna o estado de prontidão para uso comercial."""
        voice = cls.check_voice_models()
        tts = cls.check_tts_engine()
        ollama = cls.check_ollama()
        calendar = cls.check_calendar_integration()

        is_ready = (voice["status"] == "ok") and (ollama["status"] == "ok")

        return {
            "ready": is_ready,
            "platform": sys.platform,
            "is_frozen": is_frozen(),
            "user_data_dir": str(get_user_data_dir()),
            "temp_dir": str(get_temp_dir()),
            "checks": {
                "voice_models": voice,
                "tts_engine": tts,
                "ollama": ollama,
                "calendar": calendar,
            },
        }
