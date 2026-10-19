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

echo [2/3] Iniciando o motor Geraldo (Voz, IA e WebSocket 8765)...
start "Geraldo Core (Voz + IA)" %PYTHON_CMD% main.py

timeout /t 2 /nobreak >nul

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
