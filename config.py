import os
import json
from pathlib import Path
from core.paths import get_user_data_dir

# Gerenciamento de Configurações Persistentes do Usuário
def get_settings_file() -> Path:
    return get_user_data_dir() / "settings.json"

def load_settings() -> dict:
    sf = get_settings_file()
    if sf.exists():
        try:
            with open(sf, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_settings(new_settings: dict) -> None:
    sf = get_settings_file()
    try:
        data = load_settings()
        data.update(new_settings)
        with open(sf, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Geraldo:Config] Erro ao salvar configurações: {e}")

_user_settings = load_settings()

ASSISTANT_NAME = "Geraldo"

# Dicionário de Provedores e Presets Recomendados
PROVIDER_PRESETS = {
    "ollama": {
        "name": "Ollama (Local / Container)",
        "default_base": "http://localhost:11434",
        "default_model": "qwen2.5:3b",
        "models": ["qwen2.5:3b", "llama3.2:3b", "mistral:7b", "deepseek-r1:1.5b"],
        "requires_key": False,
        "key_url": "",
        "hint": "Execução 100% local ou via container Docker sem custo de API.",
    },
    "groq": {
        "name": "Groq (Latência Ultra-baixa / Voz)",
        "default_base": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
        "requires_key": True,
        "key_url": "https://console.groq.com/keys",
        "hint": "Ideal para assistentes de voz devido à velocidade de inferência (<200ms).",
    },
    "openai": {
        "name": "OpenAI",
        "default_base": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
        "requires_key": True,
        "key_url": "https://platform.openai.com/api-keys",
        "hint": "Modelos oficiais da OpenAI com alta precisão e rapidez.",
    },
    "openrouter": {
        "name": "OpenRouter",
        "default_base": "https://openrouter.ai/api/v1",
        "default_model": "openai/gpt-4o-mini",
        "models": ["openai/gpt-4o-mini", "anthropic/claude-3.5-haiku", "meta-llama/llama-3.3-70b-instruct"],
        "requires_key": True,
        "key_url": "https://openrouter.ai/keys",
        "hint": "Acesso a centenas de modelos abertos e proprietários com uma única chave.",
    },
    "gemini": {
        "name": "Google Gemini",
        "default_base": "https://generativelanguage.googleapis.com/v1beta/openai",
        "default_model": "gemini-2.0-flash",
        "models": ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
        "requires_key": True,
        "key_url": "https://aistudio.google.com/app/apikey",
        "hint": "Modelos multimodais de alta velocidade e cota gratuita generosa.",
    },
    "custom": {
        "name": "Personalizado (OpenAI Compatível)",
        "default_base": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "requires_key": True,
        "key_url": "",
        "hint": "Qualquer serviço com API compatível com OpenAI (DeepSeek, LocalAI, vLLM, etc).",
    },
}

# Configuração Ativa de LLM
LLM_PROVIDER = os.getenv("LLM_PROVIDER", _user_settings.get("llm_provider", "ollama")).lower()
OLLAMA_HOST = os.getenv("OLLAMA_HOST", _user_settings.get("ollama_host", "http://localhost:11434"))
LLM_MODEL = os.getenv("LLM_MODEL", _user_settings.get("llm_model", "qwen2.5:3b"))
LLM_API_KEY = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", os.getenv("GROQ_API_KEY", _user_settings.get("llm_api_key", ""))))
LLM_API_BASE = os.getenv("LLM_API_BASE", _user_settings.get("llm_api_base", ""))

def mask_api_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}...{key[-4:]}"

def get_llm_config() -> dict:
    default_base = PROVIDER_PRESETS.get(LLM_PROVIDER, {}).get("default_base", "http://localhost:11434")
    return {
        "provider": LLM_PROVIDER,
        "llm_provider": LLM_PROVIDER,
        "ollama_host": OLLAMA_HOST,
        "host": OLLAMA_HOST,
        "llm_model": LLM_MODEL,
        "model": LLM_MODEL,
        "api_base": LLM_API_BASE or default_base,
        "llm_api_base": LLM_API_BASE or default_base,
        "has_api_key": bool(LLM_API_KEY),
        "api_key_masked": mask_api_key(LLM_API_KEY),
        "providers": PROVIDER_PRESETS,
    }

def update_llm_config(
    provider: str = None,
    host: str = None,
    model: str = None,
    api_key: str = None,
    api_base: str = None,
    persist: bool = True,
) -> dict:
    global LLM_PROVIDER, OLLAMA_HOST, LLM_MODEL, LLM_API_KEY, LLM_API_BASE

    if provider:
        p_clean = provider.strip().lower()
        if p_clean in PROVIDER_PRESETS or p_clean:
            LLM_PROVIDER = p_clean

    if host:
        clean_host = host.strip().rstrip("/")
        if clean_host and not (clean_host.startswith("http://") or clean_host.startswith("https://")):
            clean_host = f"http://{clean_host}"
        OLLAMA_HOST = clean_host

    if model:
        LLM_MODEL = model.strip()

    if api_key is not None:
        LLM_API_KEY = api_key.strip()

    if api_base is not None:
        clean_base = api_base.strip().rstrip("/")
        if clean_base and not (clean_base.startswith("http://") or clean_base.startswith("https://")):
            clean_base = f"https://{clean_base}"
        LLM_API_BASE = clean_base

    if persist:
        save_settings({
            "llm_provider": LLM_PROVIDER,
            "ollama_host": OLLAMA_HOST,
            "llm_model": LLM_MODEL,
            "llm_api_key": LLM_API_KEY,
            "llm_api_base": LLM_API_BASE,
        })

    return get_llm_config()

# Funções retrocompatíveis com chamadas diretas a Ollama
def get_ollama_config() -> dict:
    return get_llm_config()

def update_ollama_config(host: str = None, model: str = None, persist: bool = True) -> dict:
    return update_llm_config(provider="ollama" if host else None, host=host, model=model, persist=persist)

# Parâmetros de Áudio
SAMPLE_RATE = 16000
CHUNK_SIZE = 512
VAD_THRESHOLD = 0.5
SILENCE_LIMIT_SEC = 0.8

# Barramento IPC Local (WebSocket)
IPC_HOST = "127.0.0.1"
IPC_PORT = 8765
IPC_REQUIRE_AUTH = False
IPC_AUTH_TOKEN = None

# System Prompt Neutro/Padrão
SYSTEM_PROMPT = f"""Seu nome é {ASSISTANT_NAME}. Você é um assistente de voz desktop inteligente, rápido e direto.
Você roda localmente em Anápolis, Goiás, Brasil. Responda sempre em português.

DIRETRIZES CRÍTICAS:
1. Respostas extremamente curtas e objetivas: no máximo 1 a 2 frases curtas.
2. Pare de falar imediatamente após responder. Não elabore além do necessário nem faça perguntas de acompanhamento a menos que seja solicitado.
3. NUNCA use markdown, asteriscos (*), listas, marcadores (-), numerações ou emojis.
4. O texto é lido diretamente por TTS, portanto forneça apenas texto simples para fala natural.
"""