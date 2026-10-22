import datetime
import subprocess
import json
import urllib.request
import urllib.parse

class SystemTools:
    @staticmethod
    def get_current_time(*args, **kwargs) -> str:
        agora = datetime.datetime.now()
        dias_semana = [
            "segunda-feira", "terça-feira", "quarta-feira",
            "quinta-feira", "sexta-feira", "sábado", "domingo"
        ]
        meses = [
            "", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
            "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
        ]
        dia_nome = dias_semana[agora.weekday()]
        mes_nome = meses[agora.month]
        return f"Agora são {agora.hour} horas e {agora.minute} minutos de {dia_nome}, dia {agora.day} de {mes_nome}."

    @staticmethod
    def set_volume(change: str = "+", *args, **kwargs) -> str:
        change_str = str(change).strip().replace('%', '')
        try:
            # Tenta usar wpctl (Padrão PipeWire/WirePlumber no Hyprland)
            if change_str.isdigit():
                val = max(0, min(100, int(change_str)))
                fraction = val / 100.0
                subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{fraction:.2f}"], check=True)
                return f"Volume definido para {val} por cento."

            if change == "mute":
                subprocess.run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"], check=True)
                return "Áudio silenciado ou ativado."
            elif change == "+":
                subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%+"], check=True)
                return "Volume aumentado."
            elif change == "-":
                subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%-"], check=True)
                return "Volume abaixado."

            return "Comando de volume não reconhecido."
        except Exception:
            # Fallback para pamixer caso o wpctl falhe
            try:
                if change_str.isdigit():
                    val = max(0, min(100, int(change_str)))
                    subprocess.run(["pamixer", "--set-volume", str(val)], check=True)
                    return f"Volume definido para {val} por cento."
                elif change == "mute":
                    subprocess.run(["pamixer", "--toggle-mute"], check=True)
                    return "Áudio silenciado ou ativado."
                elif change == "+":
                    subprocess.run(["pamixer", "-i", "5"], check=True)
                    return "Volume aumentado."
                elif change == "-":
                    subprocess.run(["pamixer", "-d", "5"], check=True)
                    return "Volume abaixado."
            except Exception as inner_e:
                return f"Não foi possível ajustar o volume: {inner_e}"
            return "Comando de volume não reconhecido."

    @staticmethod
    def play_pause_media(*args, **kwargs) -> str:
        try:
            subprocess.run(["playerctl", "play-pause"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return "Mídia alternada entre reproduzir e pausar."
        except Exception:
            return "Nenhum player de mídia ativo encontrado."

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
        max_temps = daily.get("temperature_2m_max") or [temp, temp]
        min_temps = daily.get("temperature_2m_min") or [temp, temp]
        daily_codes = daily.get("weather_code") or [0, 0]

        cidade_nome = city.capitalize() if city else "Anápolis"
        q_norm = query_type.lower().strip()

        if any(w in q_norm for w in ["amanhã", "amanha", "amãhã"]):
            max_t = round(max_temps[1]) if len(max_temps) > 1 else round(max_temps[0])
            min_t = round(min_temps[1]) if len(min_temps) > 1 else round(min_temps[0])
            cond_amanha = cls._wmo_to_description(daily_codes[1] if len(daily_codes) > 1 else 0)
            return f"Para amanhã em {cidade_nome}, a previsão indica tempo {cond_amanha}, com mínima de {min_t} e máxima de {max_t} graus."

        if "semana" in q_norm:
            min_geral = round(min(min_temps[:5]))
            max_geral = round(max(max_temps[:5]))
            return f"Em {cidade_nome}, ao longo da semana as temperaturas devem variar entre mínimas de {min_geral} e máximas de {max_geral} graus."

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

    _weather_cache = {}
    _WEATHER_CACHE_TTL = 900  # 15 minutos

    @classmethod
    def clear_weather_cache(cls):
        cls._weather_cache.clear()

    _weather_poller_started = False

    @classmethod
    def start_weather_poller(cls, interval_seconds: int = 900):
        """Dispara poller em background thread que mantém o clima de Anápolis sempre em cache."""
        if cls._weather_poller_started:
            return
        cls._weather_poller_started = True

        import threading
        import time as _t

        def _poller():
            # Executa aquecimento imediato
            try:
                cls.get_weather("hoje", "Anápolis", use_cache=False)
                cls.get_weather("amanhã", "Anápolis", use_cache=False)
                print("[Geraldo:Weather] Pré-cache de clima carregado em background.")
            except Exception as e:
                print(f"[Geraldo:Weather] Falha no pré-cache inicial: {e}")

            while True:
                _t.sleep(interval_seconds)
                try:
                    cls.get_weather("hoje", "Anápolis", use_cache=False)
                    cls.get_weather("amanhã", "Anápolis", use_cache=False)
                    print("[Geraldo:Weather] Cache periódico de clima renovado em background.")
                except Exception as e:
                    print(f"[Geraldo:Weather] Falha ao renovar cache de clima: {e}")

        threading.Thread(target=_poller, daemon=True, name="weather_cache_poller").start()

    _INVALID_CITY_WORDS = {
        "hoje", "amanhã", "amanha", "amãhã", "semana", "agora", "aqui",
        "o maior", "maior", "tempo", "clima", "mim", "manhã", "manha", "tarde", "noite"
    }

    @classmethod
    def get_weather(cls, query_type: str = "hoje", query: str = "Anápolis", use_cache: bool = True, *args, **kwargs) -> str:
        city_raw = (query or "").strip()
        if not city_raw or city_raw.lower() in cls._INVALID_CITY_WORDS:
            city = "Anápolis"
        else:
            city = city_raw

        cache_key = (city.lower().strip(), query_type.lower().strip())
        import time as _t
        now = _t.time()

        if use_cache and cache_key in cls._weather_cache:
            cached_time, cached_val = cls._weather_cache[cache_key]
            if now - cached_time < cls._WEATHER_CACHE_TTL:
                remaining = int(cls._WEATHER_CACHE_TTL - (now - cached_time))
                print(f"[Geraldo:Weather] Cache atingido (restam {remaining}s de validade)")
                return cached_val

        result = None
        try:
            result = cls._fetch_open_meteo(city, query_type)
        except Exception as e:
            print(f"[Geraldo:Weather] Open-Meteo falhou ({e}). Recorrendo ao wttr.in...")

        if not result:
            try:
                result = cls._fetch_wttr(city, query_type)
            except Exception as e_fb:
                print(f"[Geraldo:Weather] Fallback wttr.in falhou: {e_fb}")
                return "Não foi possível obter a previsão do tempo no momento."

        if result:
            cls._weather_cache[cache_key] = (now, result)
        return result
