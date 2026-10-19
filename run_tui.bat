@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo   Geraldo - Interface de Terminal (TUI)
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

echo [1/2] Verificando motor Geraldo (porta 8765)...
%PYTHON_CMD% -c "import socket; s = socket.socket(); s.settimeout(0.5); res = s.connect_ex(('127.0.0.1', 8765)); s.close(); exit(0 if res == 0 else 1)"
if %ERRORLEVEL% NEQ 0 (
    echo   [Geraldo] Iniciando motor em segundo plano...
    start "Geraldo Core (Voz + IA)" %PYTHON_CMD% main.py
    timeout /t 2 /nobreak >nul
) else (
    echo   [OK] Barramento WebSocket ativo em ws://127.0.0.1:8765
)

echo [2/2] Abrindo interface de terminal TUI (Textual)...
%PYTHON_CMD% -m ui.tui %*
