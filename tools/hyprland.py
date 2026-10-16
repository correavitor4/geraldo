import subprocess
import json

class HyprlandTools:
    @staticmethod
    def run_hyprctl(command: list[str]) -> str:
        try:
            res = subprocess.run(["hyprctl"] + command, capture_output=True, text=True, check=True)
            return res.stdout.strip()
        except Exception as e:
            return f"Erro ao executar comando do Hyprland: {e}"

    @classmethod
    def change_workspace(cls, target: str) -> str:
        cls.run_hyprctl(["dispatch", "workspace", target])
        return f"Mudando para a área de trabalho {target}."

    @classmethod
    def move_window_to_workspace(cls, target: str) -> str:
        cls.run_hyprctl(["dispatch", "movetoworkspace", target])
        return f"Janela movida para a área de trabalho {target}."

    @classmethod
    def toggle_floating(cls) -> str:
        cls.run_hyprctl(["dispatch", "togglefloating", "active"])
        return "Alternado estado flutuante da janela ativa."

    @classmethod
    def toggle_fullscreen(cls) -> str:
        cls.run_hyprctl(["dispatch", "fullscreen", "0"])
        return "Alternado modo tela cheia."

    @classmethod
    def close_active_window(cls) -> str:
        cls.run_hyprctl(["dispatch", "killactive", ""])
        return "Fechando janela ativa."

    @classmethod
    def set_brightness(cls, level: str) -> str:
        try:
            subprocess.run(["brightnessctl", "set", level], check=True)
            return f"Brilho ajustado para {level}."
        except Exception:
            return "Não foi possível ajustar o brilho."

    @classmethod
    def open_launcher(cls) -> str:
        try:
            subprocess.Popen(["rofi", "-show", "drun"])
            return "Abrindo menu de aplicativos."
        except Exception:
            try:
                subprocess.Popen(["wofi", "--show", "drun"])
                return "Abrindo menu de aplicativos."
            except Exception:
                return "Nenhum launcher encontrado."
