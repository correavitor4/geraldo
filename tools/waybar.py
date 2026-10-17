import subprocess
import os

class WaybarTools:
    @staticmethod
    def restart_waybar() -> str:
        hyprland_active = os.environ.get("WAYLAND_DISPLAY") is not None or subprocess.run(["pgrep", "-x", "Hyprland"], capture_output=True).returncode == 0
        waybar_exists = subprocess.run(["which", "waybar"], capture_output=True).returncode == 0

        if hyprland_active and waybar_exists:
            try:
                # Tenta dar reload suave primeiro, se falhar reinicia o processo
                res = subprocess.run(["pkill", "-SIGUSR2", "waybar"], capture_output=True)
                if res.returncode != 0:
                    subprocess.run(["pkill", "waybar"], check=False)
                    subprocess.Popen(["waybar"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                return "Waybar atualizada com sucesso."
            except Exception as e:
                return f"Erro ao atualizar a Waybar: {e}"
        else:
            return "Comando indisponível: o ambiente atual não está rodando Waybar com Hyprland."
