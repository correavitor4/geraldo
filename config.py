import os
import json
from pathlib import Path
from core.paths import get_user_data_dir, get_base_dir

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

# Configurações embutidas no build (injetadas via GitHub Secrets)
_bundled_file = get_base_dir() / "_bundled_defaults.json"
_bundled_defaults = {}
if _bundled_file.exists():
    try:
        with open(_bundled_file, "r", encoding="utf-8") as bf:
            _bundled_defaults = json.load(bf)
    except Exception:
        _bundled_defaults = {}

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
LLM_PROVIDER = os.getenv("LLM_PROVIDER", _user_settings.get("llm_provider", _bundled_defaults.get("llm_provider", "ollama"))).lower()
OLLAMA_HOST = os.getenv("OLLAMA_HOST", _user_settings.get("ollama_host", _bundled_defaults.get("ollama_host", "http://localhost:11434")))
LLM_MODEL = os.getenv("LLM_MODEL", _user_settings.get("llm_model", _bundled_defaults.get("llm_model", "qwen2.5:3b")))
LLM_API_KEY = os.getenv(
    "LLM_API_KEY",
    os.getenv(
        "GEMINI_API_KEY",
        os.getenv(
            "GOOGLE_API_KEY",
            os.getenv(
                "OPENAI_API_KEY",
                os.getenv(
                    "GROQ_API_KEY",
                    _user_settings.get("llm_api_key", _bundled_defaults.get("llm_api_key", ""))
                )
            )
        )
    )
)
LLM_API_BASE = os.getenv("LLM_API_BASE", _user_settings.get("llm_api_base", _bundled_defaults.get("llm_api_base", "")))

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

# Google Calendar OAuth 2.0 (Carregado de variáveis de ambiente, settings.json ou bundle de release)
GOOGLE_CLIENT_ID = (
    os.getenv("GOOGLE_CLIENT_ID", "").strip()
    or _user_settings.get("google_client_id", "").strip()
    or _bundled_defaults.get("google_client_id", "").strip()
)
GOOGLE_CLIENT_SECRET = (
    os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    or _user_settings.get("google_client_secret", "").strip()
    or _bundled_defaults.get("google_client_secret", "").strip()
)

def get_google_oauth_config() -> dict:
    return {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "has_client_id": bool(GOOGLE_CLIENT_ID),
        "has_client_secret": bool(GOOGLE_CLIENT_SECRET),
    }

def update_google_oauth_config(client_id: str = None, client_secret: str = None, persist: bool = True) -> dict:
    global GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
    if client_id is not None:
        GOOGLE_CLIENT_ID = client_id.strip()
    if client_secret is not None:
        GOOGLE_CLIENT_SECRET = client_secret.strip()

    if persist:
        save_settings({
            "google_client_id": GOOGLE_CLIENT_ID,
            "google_client_secret": GOOGLE_CLIENT_SECRET,
        })

    return get_google_oauth_config()

# Configuração de Escuta Ativa e Atas de Reuniões (Híbrido: Local vs Nuvem)
MEETING_PROVIDER = os.getenv(
    "MEETING_PROVIDER",
    _user_settings.get("meeting_provider", "local")
).lower()
MEETING_STORAGE_DIR = os.path.normpath(
    os.getenv(
        "MEETING_STORAGE_DIR",
        _user_settings.get("meeting_storage_dir", os.path.expanduser("~/Geraldo/reunioes"))
    )
)
MEETING_EXPORT_DIR = os.path.normpath(
    os.getenv(
        "MEETING_EXPORT_DIR",
        _user_settings.get("meeting_export_dir", os.path.join(MEETING_STORAGE_DIR, "exportadas"))
    )
)
MEETING_DETAIL_LEVEL = os.getenv(
    "MEETING_DETAIL_LEVEL",
    _user_settings.get("meeting_detail_level", "detailed")
).lower()
if MEETING_DETAIL_LEVEL not in ("detailed", "concise"):
    MEETING_DETAIL_LEVEL = "detailed"

def get_meeting_config() -> dict:
    return {
        "provider": MEETING_PROVIDER,
        "storage_dir": MEETING_STORAGE_DIR,
        "export_dir": MEETING_EXPORT_DIR,
        "detail_level": MEETING_DETAIL_LEVEL,
        "supported_providers": ["local", "cloud"],
        "supported_detail_levels": ["detailed", "concise"],
    }

def update_meeting_config(
    provider: str = None,
    storage_dir: str = None,
    export_dir: str = None,
    detail_level: str = None,
    persist: bool = True
) -> dict:
    global MEETING_PROVIDER, MEETING_STORAGE_DIR, MEETING_EXPORT_DIR, MEETING_DETAIL_LEVEL
    if provider:
        p_clean = provider.strip().lower()
        if p_clean in ("local", "cloud"):
            MEETING_PROVIDER = p_clean
    if storage_dir:
        MEETING_STORAGE_DIR = os.path.normpath(os.path.abspath(os.path.expanduser(storage_dir.strip())))
    if export_dir:
        MEETING_EXPORT_DIR = os.path.normpath(os.path.abspath(os.path.expanduser(export_dir.strip())))
    if detail_level:
        d_clean = detail_level.strip().lower()
        if d_clean in ("detailed", "longo", "long", "completo"):
            MEETING_DETAIL_LEVEL = "detailed"
        elif d_clean in ("concise", "curto", "short", "resumido"):
            MEETING_DETAIL_LEVEL = "concise"

    if persist:
        save_settings({
            "meeting_provider": MEETING_PROVIDER,
            "meeting_storage_dir": MEETING_STORAGE_DIR,
            "meeting_export_dir": MEETING_EXPORT_DIR,
            "meeting_detail_level": MEETING_DETAIL_LEVEL,
        })
    return get_meeting_config()

# Parâmetros de Áudio
SAMPLE_RATE = 16000
CHUNK_SIZE = 512
VAD_THRESHOLD = 0.5
SILENCE_LIMIT_SEC = 0.8
BEEP_VOLUME = float(os.getenv("BEEP_VOLUME", 0.50))

# Dispositivos de Áudio Selecionados (None = padrão do sistema)
AUDIO_INPUT_DEVICE = _user_settings.get("audio_input_device", None)
AUDIO_OUTPUT_DEVICE = _user_settings.get("audio_output_device", None)


_AUDIO_UNSET = object()

def get_audio_config() -> dict:
    from audio.device_utils import list_audio_devices, resolve_audio_device
    devices = list_audio_devices()
    return {
        "input_device": AUDIO_INPUT_DEVICE,
        "output_device": AUDIO_OUTPUT_DEVICE,
        "resolved_input_id": resolve_audio_device(AUDIO_INPUT_DEVICE, kind="input"),
        "resolved_output_id": resolve_audio_device(AUDIO_OUTPUT_DEVICE, kind="output"),
        "devices": devices,
        "available_inputs": devices.get("inputs", []),
        "available_outputs": devices.get("outputs", []),
    }


def update_audio_config(input_device=_AUDIO_UNSET, output_device=_AUDIO_UNSET, persist: bool = True) -> dict:
    global AUDIO_INPUT_DEVICE, AUDIO_OUTPUT_DEVICE
    if input_device is not _AUDIO_UNSET:
        if input_device is None:
            AUDIO_INPUT_DEVICE = None
        else:
            val_str = str(input_device).strip().lower()
            if val_str in ("default", "none", "", "padrão"):
                AUDIO_INPUT_DEVICE = None
            else:
                try:
                    AUDIO_INPUT_DEVICE = int(input_device)
                except (ValueError, TypeError):
                    AUDIO_INPUT_DEVICE = str(input_device).strip()

    if output_device is not _AUDIO_UNSET:
        if output_device is None:
            AUDIO_OUTPUT_DEVICE = None
        else:
            val_str = str(output_device).strip().lower()
            if val_str in ("default", "none", "", "padrão"):
                AUDIO_OUTPUT_DEVICE = None
            else:
                try:
                    AUDIO_OUTPUT_DEVICE = int(output_device)
                except (ValueError, TypeError):
                    AUDIO_OUTPUT_DEVICE = str(output_device).strip()

    try:
        from audio.device_utils import resolve_audio_device
        import sounddevice as sd
        in_id = resolve_audio_device(AUDIO_INPUT_DEVICE, kind="input")
        out_id = resolve_audio_device(AUDIO_OUTPUT_DEVICE, kind="output")
        sd.default.device = (in_id, out_id)
    except Exception:
        pass

    if persist:
        save_settings({
            "audio_input_device": AUDIO_INPUT_DEVICE,
            "audio_output_device": AUDIO_OUTPUT_DEVICE,
        })

    return get_audio_config()


# Inicializa o dispositivo padrão do sounddevice se configurado
try:
    if AUDIO_INPUT_DEVICE is not None or AUDIO_OUTPUT_DEVICE is not None:
        from audio.device_utils import resolve_audio_device
        import sounddevice as sd
        in_id = resolve_audio_device(AUDIO_INPUT_DEVICE, kind="input")
        out_id = resolve_audio_device(AUDIO_OUTPUT_DEVICE, kind="output")
        sd.default.device = (in_id, out_id)
except Exception:
    pass


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