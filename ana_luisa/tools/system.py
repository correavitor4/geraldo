import subprocess
import shutil
from datetime import datetime

class SystemTools:
    @staticmethod
    def play_pause_media() -> str:
        """Pausa ou retoma a reprodução de mídia."""
        if not shutil.which("playerctl"):
            return "Comando playerctl não instalado no sistema."
        try:
            subprocess.run(["playerctl", "play-pause"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return "Reprodução alternada com sucesso."
        except subprocess.CalledProcessError:
            return "Nenhum player ativo encontrado."

    @staticmethod
    def next_media() -> str:
        """Avança para a próxima música/faixa."""
        if not shutil.which("playerctl"):
            return "playerctl não disponível."
        try:
            subprocess.run(["playerctl", "next"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return "Faixa avançada."
        except subprocess.CalledProcessError:
            return "Não foi possível avançar a faixa."

    @staticmethod
    def previous_media() -> str:
        """Volta para a música anterior."""
        if not shutil.which("playerctl"):
            return "playerctl não disponível."
        try:
            subprocess.run(["playerctl", "previous"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return "Faixa retrocedida."
        except subprocess.CalledProcessError:
            return "Não foi possível retroceder a faixa."

    @staticmethod
    def set_volume(change: str) -> str:
        """Ajusta o volume do sistema via wpctl (PipeWire). Ex: +5%, -5%, mute."""
        if not shutil.which("wpctl"):
            return "wpctl não disponível."
        try:
            if change == "mute":
                subprocess.run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"], check=True)
                return "Mudo alternado."
            
            # Formato esperado: ex: "5%+" ou "5%-"
            direction = "+" if "+" in change or "up" in change or "aumentar" in change else "-"
            subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"5%{direction}"], check=True)
            return f"Volume ajustado em 5%."
        except subprocess.CalledProcessError:
            return "Falha ao ajustar o volume."

    @staticmethod
    def get_current_time() -> str:
        """Retorna a hora e a data atual exata."""
        now = datetime.now()
        return now.strftime("Agora são %H horas e %M minutos do dia %d de %B de %Y.")

