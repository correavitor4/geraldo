# core/paths.py
"""
Gerenciador Universal de Caminhos e Recursos para o Geraldo.
Garante compatibilidade multiplataforma (Linux, Windows, macOS)
e suporte a execução em desenvolvimento vs binário empacotado (Tauri Sidecar / PyInstaller).
"""
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

APP_NAME = "Geraldo"
APP_IDENTIFIER = "com.geraldo.assistant"


def is_frozen() -> bool:
    """Retorna True se o processo estiver executando a partir de um binário congelado (PyInstaller/Nuitka)."""
    return getattr(sys, "frozen", False)


def get_base_dir() -> Path:
    """
    Retorna o diretório base da aplicação.
    - Em ambiente congelado: sys._MEIPASS ou o diretório do executável.
    - Em desenvolvimento: diretório raiz do projeto (onde main.py está localizado).
    """
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass and os.path.exists(meipass):
            return Path(meipass)
        return Path(sys.executable).parent.resolve()
    
    # Em desenvolvimento, localiza a raiz do repositório a partir deste arquivo (core/paths.py)
    return Path(__file__).resolve().parent.parent


def get_user_data_dir() -> Path:
    """
    Retorna o diretório de dados/configuração do usuário específico do SO:
    - Windows: %APPDATA%/Geraldo
    - macOS: ~/Library/Application Support/Geraldo
    - Linux: $XDG_CONFIG_HOME/geraldo ou ~/.config/geraldo
    """
    custom_dir = os.getenv("GERALDO_DATA_DIR")
    if custom_dir:
        path = Path(custom_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    home = Path.home()
    if sys.platform == "win32":
        app_data = os.getenv("APPDATA")
        base = Path(app_data) if app_data else home / "AppData" / "Roaming"
        data_dir = base / APP_NAME
    elif sys.platform == "darwin":
        data_dir = home / "Library" / "Application Support" / APP_NAME
    else:
        xdg_config = os.getenv("XDG_CONFIG_HOME")
        base = Path(xdg_config) if xdg_config else home / ".config"
        data_dir = base / "geraldo"

    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_temp_dir() -> Path:
    """Retorna um diretório temporário seguro e compatível com todos os sistemas operacionais."""
    geraldo_temp = Path(tempfile.gettempdir()) / "geraldo"
    geraldo_temp.mkdir(parents=True, exist_ok=True)
    return geraldo_temp


def get_temp_audio_path(prefix: str = "geraldo_response", suffix: str = ".wav") -> str:
    """Gera um caminho absoluto seguro para arquivos temporários de áudio."""
    temp_dir = get_temp_dir()
    import threading
    tid = threading.get_ident()
    filename = f"{prefix}_{tid}{suffix}"
    return str(temp_dir / filename)


def get_models_search_paths() -> list[Path]:
    """Lista diretórios candidatos para busca de modelos ONNX e vozes neurais."""
    candidates = []

    # 1. Variável de ambiente explícita
    env_dir = os.getenv("GERALDO_MODELS_DIR")
    if env_dir:
        candidates.append(Path(env_dir))

    # 2. Diretório onde o executável está localizado (instalação / sidecar)
    if is_frozen():
        exe_dir = Path(sys.executable).parent.resolve()
        candidates.append(exe_dir)
        candidates.append(exe_dir / "resources")
        candidates.append(exe_dir / "_up_")
        candidates.append(exe_dir / "models")
        candidates.append(exe_dir / "assets")

    # 3. Diretório base da aplicação (raiz do projeto ou bundle PyInstaller sys._MEIPASS)
    base = get_base_dir()
    candidates.append(base)
    candidates.append(base / "models")
    candidates.append(base / "assets")

    # 4. Diretório de dados do usuário
    user_models = get_user_data_dir() / "models"
    candidates.append(user_models)
    candidates.append(get_user_data_dir())

    # 5. Diretório de trabalho atual (cwd)
    candidates.append(Path.cwd())
    candidates.append(Path.cwd() / "models")

    # 6. Diretórios conhecidos no home do usuário (repositórios de desenvolvimento)
    home = Path.home()
    for sub in ("source/repos/geraldo", "projects/geraldo", "geraldo", ".local/share/geraldo"):
        candidates.append(home / sub)

    # Retorna caminhos únicos preservando a ordem
    unique_paths = []
    for c in candidates:
        if c not in unique_paths:
            unique_paths.append(c)
    return unique_paths


def resolve_model_path(model_filename: str) -> Optional[Path]:
    """
    Encontra o caminho absoluto de um modelo ONNX ou arquivo de configuração.
    Retorna o primeiro arquivo existente encontrado ou None.
    """
    # Se já for caminho absoluto existente
    direct = Path(model_filename)
    if direct.is_absolute() and direct.exists():
        return direct

    # Nomes alternativos equivalentes
    alternatives = [model_filename]
    if model_filename == "voz_faber.onnx":
        alternatives.append("voz.onnx")
    elif model_filename == "voz.onnx":
        alternatives.append("voz_faber.onnx")
    elif model_filename == "voz_faber.onnx.json":
        alternatives.append("voz.onnx.json")
    elif model_filename == "voz.onnx.json":
        alternatives.append("voz_faber.onnx.json")

    for search_dir in get_models_search_paths():
        for alt in alternatives:
            candidate = search_dir / alt
            if candidate.exists() and candidate.is_file():
                return candidate

    return None


def ensure_model_available(model_filename: str = "voz_faber.onnx") -> Path:
    """
    Garante que o modelo neural ONNX esteja acessível.
    Se não for encontrado em nenhum diretório padrão, baixa automaticamente
    o modelo oficial pt_BR (Piper Faber) para a pasta de dados do usuário.
    """
    resolved = resolve_model_path(model_filename)
    if resolved:
        return resolved

    # Auto-download apenas para as vozes oficiais do Geraldo (voz_faber.onnx ou voz.onnx)
    is_official_model = any(k in model_filename.lower() for k in ("voz_faber", "voz.onnx", "pt_br-faber"))
    if not is_official_model:
        raise FileNotFoundError(f"Modelo não encontrado: {model_filename}")

    user_models_dir = get_user_data_dir() / "models"
    user_models_dir.mkdir(parents=True, exist_ok=True)
    target_onnx = user_models_dir / "voz_faber.onnx"
    target_json = user_models_dir / "voz_faber.onnx.json"

    print(f"[Geraldo:TTS] Modelo neural '{model_filename}' não encontrado localmente.")
    print(f"[Geraldo:TTS] Baixando modelo oficial Piper pt_BR (Faber) para {user_models_dir}...")

    import urllib.request
    onnx_url = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx"
    json_url = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx.json"

    try:
        urllib.request.urlretrieve(onnx_url, str(target_onnx))
        urllib.request.urlretrieve(json_url, str(target_json))
        print("[Geraldo:TTS] Modelo neural baixado com sucesso!")
        return target_onnx
    except Exception as e:
        print(f"[Geraldo:TTS] Erro ao baixar modelo neural: {e}")
        raise FileNotFoundError(
            f"Modelo não encontrado: {model_filename}. "
            f"Não foi possível localizá-lo nos diretórios de busca nem baixá-lo automaticamente ({e}). "
            f"Coloque o arquivo 'voz_faber.onnx' (ou 'voz.onnx') em {user_models_dir}."
        )



def get_credentials_path() -> Path:
    """Localiza o arquivo credentials.json do Google Calendar de forma agnóstica."""
    env_path = os.getenv("GOOGLE_CREDENTIALS_FILE")
    if env_path and os.path.exists(env_path):
        return Path(env_path)

    # Verifica na pasta de dados do usuário
    user_creds = get_user_data_dir() / "credentials.json"
    if user_creds.exists():
        return user_creds

    # Verifica no diretório base do projeto
    base_creds = get_base_dir() / "credentials.json"
    if base_creds.exists():
        return base_creds

    # Fallback padrão
    return user_creds


def get_token_path() -> Path:
    """Localiza ou define o arquivo token.json de forma agnóstica ao SO."""
    env_path = os.getenv("GOOGLE_TOKEN_FILE")
    if env_path:
        return Path(env_path)

    # Prioriza o diretório de dados do usuário
    user_token = get_user_data_dir() / "token.json"
    if user_token.exists():
        return user_token

    # Verifica no base_dir
    base_token = get_base_dir() / "token.json"
    if base_token.exists():
        return base_token

    return user_token


def get_env_path() -> Optional[Path]:
    """Localiza o arquivo .env no diretório base ou na pasta de configuração do usuário."""
    base_env = get_base_dir() / ".env"
    if base_env.exists():
        return base_env

    user_env = get_user_data_dir() / ".env"
    if user_env.exists():
        return user_env

    return None
