import datetime
import subprocess
import json
import urllib.request
import urllib.parse

class SystemTools:
    @staticmethod
    def get_current_time(*args, **kwargs) -> str:
        now = datetime.datetime.now()
        dias_semana = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
        dia = dias_semana[now.weekday()]
        return f"Agora são {now.strftime('%H horas e %M minutos')} de {dia}, dia {now.day} de {now.strftime('%B')}."

    @staticmethod
    def set_volume(change: str = "+", *args, **kwargs) -> str:
        cmd = ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@"]
        if change == "+":
            cmd.extend(["5%+"])
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return "Volume aumentado."
        elif change == "-":
            cmd.extend(["5%-"])
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return "Volume reduzido."
        elif change == "mute":
            subprocess.run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return "Áudio alternado mudo."
        return "Comando de volume não reconhecido."

    @staticmethod
    def play_pause_media(*args, **kwargs) -> str:
        subprocess.run(["playerctl", "play-pause"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return "Mídia alternada entre reproduzir e pausar."

    @staticmethod
    def _wmo_to_description(code: int) -> str:
        mapping = {
            0: "céu limpo",
            1: "predominantemente limpo",
            2: "parcialmente nublado",
            3: "nublado",
            45: "com neblina",
            48: "com nevoeiro",
            51: "com chuvisco leve",
            53: "com chuvisco moderado",
            55: "com chuvisco denso",
            61: "com chuva fraca",
            63: "com chuva moderada",
            65: "com chuva forte",
            80: "com pancadas de chuva leves",
            81: "com pancadas de chuva moderadas",
            82: "com pancadas de chuva violentas",
            95: "com tempestade e trovões",
            96: "com tempestade e granizo",
            99: "com tempestade severa"
        }
        return mapping.get(code, "tempo estável")

    @classmethod
    def _fetch_open_meteo(cls, city: str, query_type: str) -> str:
        lat, lon = -16.3267, -48.9534

        if city and "anápolis" not in city.lower() and "anapolis" not in city.lower():
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1&language=pt&format=json"
            req_geo = urllib.request.Request(geo_url, headers={"User-Agent": "GeraldoVoice/1.0"})
            with urllib.request.urlopen(req_geo, timeout=3) as resp_geo:
                geo_data = json.loads(resp_geo.read().decode("utf-8"))
                if geo_data.get("results"):
                    first = geo_data["results"][0]
                    lat = first["latitude"]
                    lon = first["longitude"]
                    city = first.get("name", city)

        url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code"
            f"&daily=temperature_2m_max,temperature_2m_min,weather_code&timezone=America%2FSao_Paulo"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "GeraldoVoice/1.0"})
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        curr = data.get("current", {})
        temp = round(curr.get("temperature_2m", 25))
        sensacao = round(curr.get("apparent_temperature", temp))
        umidade = curr.get("relative_humidity_2m", 60)
        condicao_hoje = cls._wmo_to_description(curr.get("weather_code", 0))

        daily = data.get("daily", {})
        max_temps = daily.get("temperature_2m_max", [temp, temp])
        min_temps = daily.get("temperature_2m_min", [temp, temp])
        daily_codes = daily.get("weather_code", [0, 0])

        cidade_nome = city.capitalize() if city else "Anápolis"
        q_norm = query_type.lower().strip()

        # Previsão específica para amanhã (índice 1)
        if any(w in q_norm for w in ["amanhã", "amanha", "amãhã"]):
            max_t = round(max_temps[1]) if len(max_temps) > 1 else round(max_temps[0])
            min_t = round(min_temps[1]) if len(min_temps) > 1 else round(min_temps[0])
            cond_amanha = cls._wmo_to_description(daily_codes[1] if len(daily_codes) > 1 else 0)
            return f"Para amanhã em {cidade_nome}, a previsão indica tempo {cond_amanha}, com mínima de {min_t} e máxima de {max_t} graus."

        # Previsão da semana
        if "semana" in q_norm:
            min_geral = round(min(min_temps[:5]))
            max_geral = round(max(max_temps[:5]))
            return f"Em {cidade_nome}, ao longo da semana as temperaturas devem variar entre mínimas de {min_geral} e máximas de {max_geral} graus."

        # Padrão: Hoje
        max_t = round(max_temps[0])
        min_t = round(min_temps[0])
        return f"Em {cidade_nome}, o tempo está {condicao_hoje}, marcando {temp} graus, com sensação de {sensacao} graus e umidade de {umidade} por cento. Hoje a mínima é de {min_t} e a máxima de {max_t} graus."

    @classmethod
    def _fetch_wttr(cls, city: str, query_type: str) -> str:
        target_city = city if city else "Anapolis"
        safe_city = urllib.parse.quote(target_city)
        url = f"https://wttr.in/{safe_city}?format=j1&lang=pt"
        
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.88.1"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        cc = data["current_condition"][0]
        temp = cc.get("temp_C", "25")
        sensacao = cc.get("FeelsLikeC", temp)
        umidade = cc.get("humidity", "60")
        
        desc = "tempo estável"
        if "lang_pt" in cc and cc["lang_pt"]:
            desc = cc["lang_pt"][0].get("value", desc).lower()

        weather_list = data.get("weather", [{}])
        cidade_nome = target_city.capitalize()
        q_norm = query_type.lower().strip()

        if any(w in q_norm for w in ["amanhã", "amanha", "amãhã"]) and len(weather_list) > 1:
            amanha = weather_list[1]
            return f"Para amanhã em {cidade_nome}, a mínima prevista é de {amanha.get('mintempC')} e a máxima de {amanha.get('maxtempC')} graus."

        hoje = weather_list[0]
        return f"Em {cidade_nome}, o tempo está {desc}, marcando {temp} graus com sensação de {sensacao} graus. Para hoje, mínima de {hoje.get('mintempC', temp)} e máxima de {hoje.get('maxtempC', temp)} graus."

    @classmethod
    def get_weather(cls, query_type: str = "hoje", query: str = "Anápolis", *args, **kwargs) -> str:
        city = query if query and query.lower() not in ["hoje", "amanhã", "amanha", "amãhã", "semana"] else "Anápolis"

        try:
            return cls._fetch_open_meteo(city, query_type)
        except Exception as e:
            print(f"[Geraldo:Weather] Open-Meteo falhou ({e}). Recorrendo ao wttr.in...")

        try:
            return cls._fetch_wttr(city, query_type)
        except Exception as e_fb:
            print(f"[Geraldo:Weather] Fallback wttr.in falhou: {e_fb}")
            return "Não foi possível obter a previsão do tempo no momento."
