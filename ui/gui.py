"""
Inicializador da Interface Gráfica Nativa Desktop do Geraldo.
Executa a janela de desktop usando o runtime WebView2 nativo do Windows (pywebview ou Edge App Mode).
"""
import os
import sys
import time
import shutil
from core.paths import get_base_dir
from core.ipc import IPCManager


def run_gui():
    """Inicia o daemon IPC se necessário e abre a janela nativa desktop."""
    base_dir = get_base_dir()
    html_file = os.path.join(base_dir, "desktop-ui", "index.html")

    # Verifica se o motor principal (main.py com voz e IA) já está escutando na porta 8765
    import socket
    import subprocess
    is_active = False
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            is_active = (s.connect_ex(("127.0.0.1", 8765)) == 0)
    except Exception:
        is_active = False

    if not is_active:
        if sys.platform.startswith("linux"):
            try:
                res = subprocess.run(["systemctl", "--user", "start", "geraldo.service"], capture_output=True)
                if res.returncode == 0:
                    time.sleep(1.0)
            except Exception:
                pass

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.3)
                is_active = (s.connect_ex(("127.0.0.1", 8765)) == 0)
        except Exception:
            is_active = False

        if not is_active:
            main_script = os.path.join(base_dir, "main.py")
            if os.path.exists(main_script):
                try:
                    subprocess.Popen([sys.executable, main_script])
                    print("[Geraldo:GUI] Motor Geraldo (main.py) iniciado em segundo plano.")
                    time.sleep(1.0)
                except Exception as e:
                    print(f"[Geraldo:GUI] Aviso ao iniciar motor principal: {e}")

    # 1. Executável nativo compilado Tauri 2.0 (Janela nativa com System Tray)
    if sys.platform == "darwin" and os.path.isdir("/Applications/Geraldo.app"):
        try:
            subprocess.Popen(["open", "/Applications/Geraldo.app"])
            return
        except Exception:
            pass

    tauri_candidates = [
        os.path.join(base_dir, "src-tauri", "target", "debug", "geraldo-desktop"),
        os.path.join(base_dir, "src-tauri", "target", "release", "geraldo-desktop"),
        os.path.join(base_dir, "src-tauri", "target", "debug", "geraldo-desktop.exe"),
        os.path.join(base_dir, "src-tauri", "target", "release", "geraldo-desktop.exe"),
        os.path.join(base_dir, "src-tauri", "target", "debug", "Geraldo.exe"),
        os.path.join(base_dir, "src-tauri", "target", "release", "Geraldo.exe"),
        "/Applications/Geraldo.app/Contents/MacOS/Geraldo",
        "/Applications/Geraldo.app/Contents/MacOS/geraldo-desktop",
        "/usr/bin/geraldo-desktop",
        "/usr/local/bin/geraldo-desktop",
    ]
    for cand in tauri_candidates:
        if os.path.isfile(cand) and (sys.platform == "win32" or os.access(cand, os.X_OK)):
            try:
                if sys.platform == "win32":
                    subprocess.Popen([cand] + sys.argv[1:])
                    return
                else:
                    os.execv(cand, [cand] + sys.argv[1:])
            except Exception as e:
                print(f"[Geraldo:GUI] Fallback de Tauri: {e}")
                break

    # 2. Tentativa nativa via pywebview
    try:
        import webview
        url = f"file:///{html_file.replace(os.sep, '/')}"
        window = webview.create_window(
            title="Geraldo - Assistente de Voz",
            url=url,
            width=1100,
            height=750,
            min_size=(800, 600),
            resizable=True,
        )
        webview.start()
        return
    except Exception as e:
        print(f"[Geraldo:GUI] pywebview indisponível ou em fallback: {e}")

    # 3. Tentativa via App Mode (Chromium / Chrome / Edge sem abas e barra de endereço)
    app_url = f"file:///{html_file.replace(os.sep, '/')}"
    browser_bins = [
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "brave",
        "brave-browser",
        "msedge",
        "chrome",
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ]
    for b in browser_bins:
        b_path = shutil.which(b) if not os.path.isabs(b) else (b if os.path.exists(b) else None)
        if b_path:
            try:
                subprocess.Popen([b_path, f"--app={app_url}", "--window-size=1100,750"])
                return
            except Exception:
                pass

    # 4. Fallback no navegador padrão
    import webbrowser
    webbrowser.open(app_url)


if __name__ == "__main__":
    run_gui()
