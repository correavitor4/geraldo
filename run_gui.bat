@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo   Geraldo - Assistente Inteligente Desktop
echo ========================================================

set "PYTHON_CMD="
if exist "%~dp0venv\Scripts\python.exe" (
    set "PYTHON_CMD=%~dp0venv\Scripts\python.exe"
) else (
    where py >nul 2>&1 && set "PYTHON_CMD=py"
    if not defined PYTHON_CMD (
        where python >nul 2>&1 && set "PYTHON_CMD=python"
    )
)

if not defined PYTHON_CMD (
    echo [Erro] Python nao encontrado no sistema.
    pause
    exit /b 1
)

echo [1/3] Verificando container Docker do Ollama...
%PYTHON_CMD% -c "from core.onboarding import OnboardingManager; info = OnboardingManager.detect_docker_ollama(); print(f'  [Ollama] Container detectado: {info[\"container_name\"]} na porta {info[\"mapped_port\"]}') if info else print('  [Ollama] Nenhum container ativo detectado. Usando http://localhost:11434.')"

echo [2/3] Verificando motor Geraldo (Voz, IA e WebSocket 8765)...
%PYTHON_CMD% -c "import socket; s = socket.socket(); s.settimeout(0.5); res = s.connect_ex(('127.0.0.1', 8765)); s.close(); exit(0 if res == 0 else 1)"
if %ERRORLEVEL% NEQ 0 (
    echo   [Geraldo] Iniciando motor em segundo plano...
    start "Geraldo Core (Voz + IA)" %PYTHON_CMD% main.py
    echo   [Geraldo] Aguardando barramento IPC conectar...
    %PYTHON_CMD% -c "import socket, time; [exit(0) for _ in range(30) if socket.socket().connect_ex(('127.0.0.1', 8765)) == 0 or time.sleep(0.3)]; exit(1)"
) else (
    echo   [OK] Motor Geraldo ja ativo na porta 8765.
)

echo [3/3] Abrindo interface Desktop nativa...
if exist "src-tauri\Cargo.toml" (
    where cargo >nul 2>&1 && (
        echo Iniciando aplicativo nativo Tauri...
        start "" cargo tauri dev
        goto :fim
    )
)

echo Iniciando janela desktop nativa (WebView2)...
start "" %PYTHON_CMD% -m ui.gui
goto :fim

:fim
echo Geraldo operacional!
