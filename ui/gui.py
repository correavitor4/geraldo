"""
Inicializador da Interface Gráfica Nativa Desktop do Geraldo.
Executa a janela de desktop usando o runtime WebView2 nativo do Windows (pywebview ou Edge App Mode).
"""
import os
import sys
import time
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
        main_script = os.path.join(base_dir, "main.py")
        if os.path.exists(main_script):
            try:
                subprocess.Popen([sys.executable, main_script])
                print("[Geraldo:GUI] Motor Geraldo (main.py) iniciado em segundo plano.")
                time.sleep(1.0)
            except Exception as e:
                print(f"[Geraldo:GUI] Aviso ao iniciar motor principal: {e}")

    # 1. Tentativa nativa via pywebview (usa WebView2 diretamente)
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

    # 2. Tentativa nativa via MS Edge App Mode (janela independente sem abas/URL)
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for edge in edge_paths:
        if os.path.exists(edge):
            import subprocess
            subprocess.Popen([
                edge,
                f"--app=file:///{html_file.replace(os.sep, '/')}",
                "--window-size=1100,750"
            ])
            return

    # 3. Fallback no navegador padrão
    import webbrowser
    webbrowser.open(f"file:///{html_file.replace(os.sep, '/')}")


if __name__ == "__main__":
    run_gui()
