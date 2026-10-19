@echo off
setlocal
cd /d "%~dp0"

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
    echo [Erro] Interpretador Python nao encontrado no sistema nem em venv.
    echo Instale o Python ou crie um ambiente virtual em .\venv.
    pause
    exit /b 1
)

%PYTHON_CMD% -m ui.tui %*
