@echo off
setlocal
set "DIR=%~dp0"

if exist "%DIR%geraldo-core.exe" (
    "%DIR%geraldo-core.exe" --tui %*
    exit /b %ERRORLEVEL%
)

if exist "%DIR%binaries\geraldo-core.exe" (
    "%DIR%binaries\geraldo-core.exe" --tui %*
    exit /b %ERRORLEVEL%
)

if exist "%DIR%..\venv\Scripts\python.exe" (
    "%DIR%..\venv\Scripts\python.exe" "%DIR%..\ui\tui.py" %*
    exit /b %ERRORLEVEL%
)

if exist "%DIR%venv\Scripts\python.exe" (
    "%DIR%venv\Scripts\python.exe" "%DIR%ui\tui.py" %*
    exit /b %ERRORLEVEL%
)

python -m ui.tui %*
exit /b %ERRORLEVEL%
