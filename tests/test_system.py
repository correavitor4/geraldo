import pytest
import subprocess
import json
from unittest.mock import patch, MagicMock
from tools.system import SystemTools

class TestSystemToolsTime:
    def test_get_current_time(self):
        result = SystemTools.get_current_time()
        assert "Agora são" in result
        assert "horas" in result
        assert "minutos" in result
        assert "dia" in result

class TestSystemToolsVolume:
    @patch("subprocess.run")
    def test_set_volume_wpctl_percentage(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        res = SystemTools.set_volume("50%")
        assert "Volume definido para 50 por cento" in res
        mock_run.assert_called_once_with(
            ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "0.50"],
            check=True
        )

    @patch("subprocess.run")
    def test_set_volume_wpctl_increase_decrease_mute(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        
        res_plus = SystemTools.set_volume("+")
        assert "Volume aumentado" in res_plus

        res_minus = SystemTools.set_volume("-")
        assert "Volume abaixado" in res_minus

        res_mute = SystemTools.set_volume("mute")
        assert "Áudio silenciado" in res_mute

    @patch("subprocess.run")
    def test_set_volume_pamixer_fallback(self, mock_run):
        # Primeiro subprocess.run (wpctl) falha, segundo (pamixer) sucede
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, ["wpctl"]),
            MagicMock(returncode=0)
        ]
        res = SystemTools.set_volume("40")
        assert "Volume definido para 40 por cento" in res

    @patch("subprocess.run")
    def test_set_volume_all_fail(self, mock_run):
        mock_run.side_effect = Exception("No audio system")
        res = SystemTools.set_volume("+")
        assert "Não foi possível ajustar o volume" in res

    def test_set_volume_invalid(self):
        res = SystemTools.set_volume("invalid_command")
        assert "Comando de volume não reconhecido" in res

class TestSystemToolsMedia:
    @patch("subprocess.run")
    def test_play_pause_media_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        res = SystemTools.play_pause_media()
        assert "Mídia alternada" in res

    @patch("subprocess.run", side_effect=Exception("No playerctl"))
    def test_play_pause_media_failure(self, mock_run):
        res = SystemTools.play_pause_media()
        assert "Nenhum player de mídia ativo encontrado" in res

class TestSystemToolsWeather:
    def test_wmo_to_description(self):
        assert SystemTools._wmo_to_description(0) == "céu limpo"
        assert SystemTools._wmo_to_description(2) == "parcialmente nublado"
        assert SystemTools._wmo_to_description(61) == "com chuva fraca"
        assert SystemTools._wmo_to_description(95) == "com tempestade e trovões"
        assert SystemTools._wmo_to_description(9999) == "tempo estável"

    @patch("urllib.request.urlopen")
    def test_fetch_open_meteo_today(self, mock_urlopen):
        fake_data = {
            "current": {
                "temperature_2m": 26.4,
                "apparent_temperature": 27.0,
                "relative_humidity_2m": 55,
                "weather_code": 0
            },
            "daily": {
                "temperature_2m_max": [29.0, 30.0],
                "temperature_2m_min": [18.0, 19.0],
                "weather_code": [0, 1]
            }
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(fake_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        res = SystemTools._fetch_open_meteo("Anápolis", "hoje")
        assert "céu limpo" in res
        assert "26 graus" in res
        assert "29" in res

    @patch("urllib.request.urlopen")
    def test_fetch_open_meteo_tomorrow(self, mock_urlopen):
        fake_data = {
            "current": {"temperature_2m": 25},
            "daily": {
                "temperature_2m_max": [28.0, 31.0],
                "temperature_2m_min": [19.0, 20.0],
                "weather_code": [0, 61]
            }
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(fake_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        res = SystemTools._fetch_open_meteo("Anápolis", "amanhã")
        assert "Para amanhã em Anápolis" in res
        assert "com chuva fraca" in res
        assert "31" in res

    @patch("urllib.request.urlopen")
    def test_fetch_open_meteo_week(self, mock_urlopen):
        fake_data = {
            "current": {"temperature_2m": 25},
            "daily": {
                "temperature_2m_max": [28.0, 30.0, 31.0, 29.0, 27.0],
                "temperature_2m_min": [18.0, 19.0, 17.0, 16.0, 18.0],
                "weather_code": [0, 0, 0, 0, 0]
            }
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(fake_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        res = SystemTools._fetch_open_meteo("Anápolis", "semana")
        assert "ao longo da semana" in res
        assert "16" in res
        assert "31" in res

    @patch("urllib.request.urlopen")
    def test_fetch_wttr(self, mock_urlopen):
        fake_wttr = {
            "current_condition": [{
                "temp_C": "24",
                "FeelsLikeC": "25",
                "lang_pt": [{"value": "Ensolarado"}]
            }],
            "weather": [
                {"mintempC": "18", "maxtempC": "29"},
                {"mintempC": "19", "maxtempC": "30"}
            ]
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(fake_wttr).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        res = SystemTools._fetch_wttr("Goiânia", "hoje")
        assert "ensolarado" in res
        assert "24 graus" in res

    @pytest.fixture(autouse=True)
    def reset_weather_cache(self):
        SystemTools.clear_weather_cache()
        yield
        SystemTools.clear_weather_cache()

    @patch.object(SystemTools, "_fetch_open_meteo", side_effect=Exception("OpenMeteo Down"))
    @patch.object(SystemTools, "_fetch_wttr", return_value="Previsão via wttr.in")
    def test_get_weather_fallback_to_wttr(self, mock_wttr, mock_om):
        res = SystemTools.get_weather("hoje", "Anápolis")
        assert "Previsão via wttr.in" in res

    @patch.object(SystemTools, "_fetch_open_meteo", side_effect=Exception("OpenMeteo Down"))
    @patch.object(SystemTools, "_fetch_wttr", side_effect=Exception("wttr Down"))
    def test_get_weather_all_fail(self, mock_wttr, mock_om):
        res = SystemTools.get_weather("hoje", "Anápolis")
        assert "Não foi possível obter a previsão do tempo no momento" in res

    @patch.object(SystemTools, "_fetch_open_meteo", return_value="Tempo ensolarado em Anápolis.")
    def test_get_weather_cache_hit(self, mock_om):
        res1 = SystemTools.get_weather("hoje", "Anápolis")
        assert res1 == "Tempo ensolarado em Anápolis."
        assert mock_om.call_count == 1

        # Segunda chamada deve retornar do cache sem chamar a rede
        res2 = SystemTools.get_weather("hoje", "Anápolis")
        assert res2 == "Tempo ensolarado em Anápolis."
        assert mock_om.call_count == 1
