import subprocess
import shutil
import urllib.request
import urllib.parse
import json
from datetime import datetime

class SystemTools:
    @staticmethod
    def play_pause_media() -> str:
        if not shutil.which("playerctl"):
            return "Comando playerctl não instalado no sistema."
        try:
            subprocess.run(["playerctl", "play-pause"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return "Reprodução alternada com sucesso."
        except subprocess.CalledProcessError:
            return "Nenhum player ativo encontrado."

    @staticmethod
    def next_media() -> str:
        if not shutil.which("playerctl"):
            return "playerctl não disponível."
        try:
            subprocess.run(["playerctl", "next"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return "Faixa avançada."
        except subprocess.CalledProcessError:
            return "Não foi possível avançar a faixa."

    @staticmethod
    def previous_media() -> str:
        if not shutil.which("playerctl"):
            return "playerctl não disponível."
        try:
            subprocess.run(["playerctl", "previous"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return "Faixa retrocedida."
        except subprocess.CalledProcessError:
            return "Não foi possível retroceder a faixa."

    @staticmethod
    def set_volume(change: str) -> str:
        if not shutil.which("wpctl"):
            return "wpctl não disponível."
        try:
            if change == "mute":
                subprocess.run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"], check=True)
                return "Mudo alternado."
            direction = "+" if "+" in change or "up" in change or "aumentar" in change else "-"
            subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"5%{direction}"], check=True)
            return "Volume ajustado em cinco por cento."
        except subprocess.CalledProcessError:
            return "Falha ao ajustar o volume."

    @staticmethod
    def get_current_time() -> str:
        now = datetime.now()
        return now.strftime("Agora são %H horas e %M minutos do dia %d de %B de %Y.")

    @staticmethod
    def get_weather(query_type: str = "hoje") -> str:
        """
        Consulta clima atual e previsão com máximas e mínimas para Anápolis.
        query_type: hoje ou semana
        """
        # Coordenadas de Anápolis - GO
        lat, lon = -16.3267, -48.9534
        url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code"
            f"&daily=weather_code,temperature_2m_max,temperature_2m_min"
            f"&timezone=America%2FSao_Paulo"
        )

        weather_codes = {
            0: "céu limpo",
            1: "predomínio de sol",
            2: "parcialmente nublado",
            3: "tempo nublado",
            45: "nevoeiro",
            51: "chuvisco leve",
            53: "chuvisco moderado",
            61: "chuva leve",
            63: "chuva moderada",
            65: "chuva forte",
            80: "pancadas de chuva rápida",
            95: "tempestade com trovoadas"
        }

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GeraldoVoiceAssistant/1.0"})
            with urllib.request.urlopen(req, timeout=8) as res:
                data = json.loads(res.read().decode("utf-8"))

            curr = data.get("current", {})
            daily = data.get("daily", {})

            temp = int(round(curr.get("temperature_2m", 20)))
            sensacao = int(round(curr.get("apparent_temperature", 20)))
            umidade = int(round(curr.get("relative_humidity_2m", 60)))
            cond = weather_codes.get(curr.get("weather_code", 0), "tempo estável")

            max_hoje = int(round(daily["temperature_2m_max"][0]))
            min_hoje = int(round(daily["temperature_2m_min"][0]))

            # Se for pedido de semana/máximas da semana
            if "semana" in query_type.lower():
                max_sem = int(round(max(daily["temperature_2m_max"])))
                min_sem = int(round(min(daily["temperature_2m_min"])))
                return (
                    f"Em Anápolis, para esta semana a temperatura mínima prevista é de {min_sem} graus Celsius "
                    f"e a máxima pode chegar a {max_sem} graus Celsius. Hoje o dia fica com {cond}, "
                    f"máxima de {max_hoje} e mínima de {min_hoje} graus Celsius."
                )

            # Previsão normal do dia
            return (
                f"Em Anápolis, o tempo está com {cond} e os termômetros marcam {temp} graus Celsius, "
                f"com sensação térmica de {sensacao} graus Celsius e umidade de {umidade} por cento. "
                f"Para hoje, a previsão indica mínima de {min_hoje} e máxima de {max_hoje} graus Celsius."
            )

        except Exception as e:
            return "Não foi possível obter os dados da previsão meteorológica no momento."

