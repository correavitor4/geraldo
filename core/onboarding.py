# core/onboarding.py
"""
Módulo de Onboarding e Diagnóstico de Sistema do Geraldo.
Verifica a integridade do ambiente, modelos de voz locais,
conectividade do Ollama e permissões de áudio para distribuição comercial.
"""
import sys
import os
import shutil
import urllib.request
import json
import re
import subprocess
from typing import Dict, Any, Optional, List, Tuple
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
    def detect_docker_ollama(cls) -> Optional[Dict[str, Any]]:
        """Detecta se há um container Docker do Ollama ativo no sistema e descobre a porta mapeada."""
        # Tentativa 1: Biblioteca Python docker (se disponível e com socket funcional)
        try:
            import docker
            client = docker.from_env()
            for container in client.containers.list():
                name = container.name.lower()
                image_tags = [t.lower() for t in (container.image.tags or [])]
                is_ollama = "ollama" in name or any("ollama" in tag for tag in image_tags)
                if is_ollama and container.status == "running":
                    ports = container.ports or {}
                    mapped_port = 11434
                    for port_spec, bindings in ports.items():
                        if "11434" in str(port_spec) and bindings:
                            mapped_port = int(bindings[0].get("HostPort", 11434))
                            break
                    cid = getattr(container, "short_id", getattr(container, "id", "")[:12])
                    return {
                        "container_id": cid,
                        "container_name": container.name,
                        "status": container.status,
                        "mapped_port": mapped_port,
                        "host_url": f"http://localhost:{mapped_port}",
                        "method": "docker-sdk",
                    }
        except Exception:
            pass

        # Tentativa 2: CLI do Docker (fallback seguro via subprocess)
        try:
            cmd = ["docker", "ps", "--format", "{{.ID}}|{{.Names}}|{{.Image}}|{{.Ports}}"]
            out = subprocess.check_output(cmd, text=True, timeout=3.0, stderr=subprocess.DEVNULL).strip()
            if out:
                for line in out.splitlines():
                    parts = line.split("|")
                    cid = parts[0].strip()
                    cname = parts[1].strip() if len(parts) > 1 else "ollama"
                    cimage = parts[2].strip().lower() if len(parts) > 2 else ""
                    cports = parts[3].strip() if len(parts) > 3 else ""
                    if "ollama" in cname.lower() or "ollama" in cimage:
                        m = re.search(r':(\d+)->11434', cports)
                        port = int(m.group(1)) if m else 11434
                        return {
                            "container_id": cid,
                            "container_name": cname,
                            "status": "running",
                            "mapped_port": port,
                            "host_url": f"http://localhost:{port}",
                            "method": "docker-cli",
                        }
        except Exception:
            pass

        return None

    @classmethod
    def _ping_tags(cls, url: str, timeout: float = 2.0) -> Tuple[bool, List[str], str]:
        """Testa o endpoint /api/tags de um host Ollama e retorna (sucesso, lista_modelos, erro)."""
        normalized = url.strip().rstrip("/")
        if not (normalized.startswith("http://") or normalized.startswith("https://")):
            normalized = f"http://{normalized}"
        api_tags_url = f"{normalized}/api/tags"
        try:
            req = urllib.request.Request(api_tags_url, headers={"User-Agent": "Geraldo-Onboarding/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("name") for m in data.get("models", [])]
                    return True, models, ""
        except Exception as e:
            return False, [], str(e)
        return False, [], "Resposta HTTP não foi 200."

    @classmethod
    def check_ollama(cls, host: str = None, timeout: float = 2.0) -> Dict[str, Any]:
        """Verifica se o serviço Ollama está ativo e respondendo (local ou container Docker)."""
        raw_host = (host or getattr(config, "OLLAMA_HOST", "http://localhost:11434")).strip()
        if not raw_host:
            raw_host = "http://localhost:11434"
        if not (raw_host.startswith("http://") or raw_host.startswith("https://")):
            raw_host = f"http://{raw_host}"
        ollama_url = raw_host.rstrip("/")

        target_model = getattr(config, "LLM_MODEL", "qwen2.5:3b")
        if (
            getattr(config, "LLM_PROVIDER", "ollama") != "ollama"
            or any(cloud_kw in target_model.lower() for cloud_kw in ["gemini", "gpt", "claude", "deepseek-chat"])
        ):
            target_model = "qwen2.5:3b"

        # Verifica se o container Docker está rodando no sistema
        docker_info = cls.detect_docker_ollama()

        # 1. Tenta a URL configurada/solicitada
        ok, models, err = cls._ping_tags(ollama_url, timeout=timeout)
        if ok:
            has_target = any(target_model in m for m in models)
            msg = f"Ollama ativo com {len(models)} modelo(s)."
            if docker_info and (ollama_url.startswith("http://localhost") or ollama_url.startswith("http://127.0.0.1")):
                msg = f"Container Docker '{docker_info['container_name']}' ativo e conectado com sucesso em {ollama_url} ({len(models)} modelo(s))."

            return {
                "status": "ok",
                "connected": True,
                "host": ollama_url,
                "available_models": models,
                "target_model": target_model,
                "target_model_installed": has_target,
                "container_detected": docker_info is not None,
                "container_info": docker_info,
                "message": msg,
            }

        # 2. Se falhou e o host continha "ollama" ou era preset ou falhou localmente:
        # Tenta fallback inteligente para o container detectado ou para localhost
        candidates = []
        if docker_info and docker_info.get("host_url") and docker_info["host_url"] != ollama_url:
            candidates.append(docker_info["host_url"])
        if ollama_url != "http://localhost:11434":
            candidates.append("http://localhost:11434")
        if ollama_url != "http://127.0.0.1:11434":
            candidates.append("http://127.0.0.1:11434")

        for cand in candidates:
            c_ok, c_models, _ = cls._ping_tags(cand, timeout=timeout)
            if c_ok:
                has_target = any(target_model in m for m in c_models)
                c_name = docker_info["container_name"] if docker_info else "ollama"
                return {
                    "status": "ok",
                    "connected": True,
                    "host": cand,
                    "suggested_host": cand,
                    "available_models": c_models,
                    "target_model": target_model,
                    "target_model_installed": has_target,
                    "container_detected": True,
                    "container_info": docker_info,
                    "message": f"Container Docker '{c_name}' detectado ativo! Conectado automaticamente via {cand} ({len(c_models)} modelo(s)).",
                }

        # 3. Se nenhuma tentativa funcionou, fornece diagnóstico preciso
        if docker_info:
            msg = (
                f"Container Docker '{docker_info['container_name']}' está em execução, mas a porta "
                f"{docker_info.get('mapped_port', 11434)} não respondeu em {ollama_url}. "
                f"Aguarde o container inicializar ou verifique se o mapeamento de portas (-p 11434:11434) está correto."
            )
        else:
            msg = (
                f"Ollama inacessível em {ollama_url}. Verifique se o container Docker 'ollama' está rodando "
                f"('docker run -d -p 11434:11434 ollama/ollama') ou execute 'ollama serve'."
            )

        return {
            "status": "unreachable",
            "connected": False,
            "host": ollama_url,
            "error": err,
            "container_detected": docker_info is not None,
            "container_info": docker_info,
            "message": msg,
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
        api_base: str = None,
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
            base = base_url or api_base or getattr(config, "LLM_API_BASE", "") or (config.PROVIDER_PRESETS.get(prov, {}).get("default_base", ""))
            target_model = model or getattr(config, "LLM_MODEL", "") or (config.PROVIDER_PRESETS.get(prov, {}).get("default_model", ""))
            return cls.check_external_llm(base_url=base, api_key=key, model=target_model, timeout=timeout)


    @classmethod
    def check_calendar_integration(cls) -> Dict[str, Any]:
        """Verifica se as credenciais do Google Calendar estão configuradas."""
        import config
        creds_path = get_credentials_path()
        token_path = get_token_path()

        has_creds_file = creds_path.exists()
        client_id = getattr(config, "GOOGLE_CLIENT_ID", "").strip() or os.getenv("GOOGLE_CLIENT_ID", "").strip()
        has_client_id = bool(client_id)

        has_creds = has_creds_file or has_client_id
        has_token = token_path.exists()

        if has_token:
            status = "configured"
        elif has_creds:
            status = "partial"
        else:
            status = "not_configured"

        return {
            "status": status,
            "ready_to_auth": has_creds,
            "credentials_file": str(creds_path),
            "credentials_exists": has_creds,
            "has_credentials_file": has_creds_file,
            "has_client_id": has_client_id,
            "client_id": client_id,
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
