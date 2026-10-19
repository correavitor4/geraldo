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

    # 2. Diretório base da aplicação (raiz do projeto ou bundle PyInstaller)
    base = get_base_dir()
    candidates.append(base)
    candidates.append(base / "models")
    candidates.append(base / "assets")

    # 3. Diretório de dados do usuário
    user_models = get_user_data_dir() / "models"
    candidates.append(user_models)

    # 4. Diretório de trabalho atual (cwd)
    candidates.append(Path.cwd())

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

    for search_dir in get_models_search_paths():
        candidate = search_dir / model_filename
        if candidate.exists():
            return candidate

    return None


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
