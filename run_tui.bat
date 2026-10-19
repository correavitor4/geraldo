@echo off
setlocal
cd /d "%~dp0"

set "VENV_PYTHON=%~dp0venv\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
    echo [Erro] Interpretador do venv nao encontrado em %VENV_PYTHON%
    echo Execute "python -m venv venv && .\venv\Scripts\pip install -r requirements.txt" primeiro.
    pause
    exit /b 1
)

"%VENV_PYTHON%" ui\tui.py %*
