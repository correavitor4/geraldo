@echo off
setlocal
set "DIR=%~dp0"

if exist "%DIR%Geraldo.exe" (
    start "" "%DIR%Geraldo.exe" %*
    exit /b 0
)

if exist "%DIR%geraldo-desktop.exe" (
    start "" "%DIR%geraldo-desktop.exe" %*
    exit /b 0
)

if exist "%DIR%..\src-tauri\target\release\geraldo-desktop.exe" (
    start "" "%DIR%..\src-tauri\target\release\geraldo-desktop.exe" %*
    exit /b 0
)

if exist "%DIR%..\src-tauri\target\debug\geraldo-desktop.exe" (
    start "" "%DIR%..\src-tauri\target\debug\geraldo-desktop.exe" %*
    exit /b 0
)

if exist "%DIR%..\venv\Scripts\python.exe" (
    "%DIR%..\venv\Scripts\python.exe" "%DIR%..\ui\gui.py" %*
    exit /b %ERRORLEVEL%
)

if exist "%DIR%venv\Scripts\python.exe" (
    "%DIR%venv\Scripts\python.exe" "%DIR%ui\gui.py" %*
    exit /b %ERRORLEVEL%
)

python -m ui.gui %*
exit /b %ERRORLEVEL%
