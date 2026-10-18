import pytest
from unittest.mock import MagicMock, patch
import collections
import urllib.error

from brain.llm import BrainLLM, phonetize_time_patterns, clean_for_speech

class TestPhonetizeTime:
    def test_midnight(self):
        assert phonetize_time_patterns("00:00") == "à meia-noite"
        assert phonetize_time_patterns("00:15") == "à meia-noite e 15"
        assert phonetize_time_patterns("00:30") == "à meia-noite e meia"

    def test_midday(self):
        assert phonetize_time_patterns("12:00") == "ao meio-dia"
        assert phonetize_time_patterns("12:15") == "ao meio-dia e 15"
        assert phonetize_time_patterns("12:30") == "ao meio-dia e meia"

    def test_morning_hours(self):
        assert phonetize_time_patterns("01:00") == "à uma"
        assert phonetize_time_patterns("07:00") == "às sete"
        assert phonetize_time_patterns("07:30") == "às sete e meia da manhã"
        assert phonetize_time_patterns("07:50") == "às sete e 50 da manhã"

    def test_afternoon_hours(self):
        assert phonetize_time_patterns("13:00") == "à uma da tarde"
        assert phonetize_time_patterns("14:00") == "às duas da tarde"
        assert phonetize_time_patterns("14:30") == "às duas e meia da tarde"
        assert phonetize_time_patterns("17:45") == "às cinco e 45 da tarde"

    def test_night_hours(self):
        assert phonetize_time_patterns("18:00") == "às seis da tarde"
        assert phonetize_time_patterns("19:00") == "às sete da noite"
        assert phonetize_time_patterns("20:30") == "às oito e meia da noite"
        assert phonetize_time_patterns("23:15") == "às onze e 15 da noite"

    def test_h_notation(self):
        assert phonetize_time_patterns("14h") == "às duas da tarde"
        assert phonetize_time_patterns("14h30") == "às duas e meia da tarde"
        assert phonetize_time_patterns("08h") == "às oito"

    def test_prefixed_as(self):
        assert phonetize_time_patterns("Reunião às 14:00") == "Reunião às duas da tarde"
        assert phonetize_time_patterns("Almoço ao 12:00") == "Almoço ao meio-dia"

class TestCleanForSpeech:
    def test_markdown_removal(self):
        text = "Aqui está um **texto em negrito** e outro *em itálico*."
        assert clean_for_speech(text) == "Aqui está um texto em negrito e outro em itálico."

    def test_headers_and_lists(self):
        text = "### Título\n- Item um\n* Item dois"
        cleaned = clean_for_speech(text)
        assert "#" not in cleaned
        assert "- " not in cleaned
        assert "* " not in cleaned
        assert "Título" in cleaned
        assert "Item um" in cleaned

    def test_markdown_links(self):
        text = "Veja no [Google](https://google.com) mais informações."
        assert clean_for_speech(text) == "Veja no Google mais informações."

    def test_empty_or_none(self):
        assert clean_for_speech("") == ""
        assert clean_for_speech(None) == ""

    def test_embedded_times(self):
        text = "O alarme tocará às 07:30."
        assert "às sete e meia da manhã" in clean_for_speech(text)

class TestBrainLLM:
    @pytest.fixture
    def llm(self, shared_nlu_engine):
        with patch("brain.llm.IntentEngine", return_value=shared_nlu_engine):
            instance = BrainLLM(max_history_turns=4)
            return instance

    def test_reset_memory(self, llm):
        llm.history.append({"role": "user", "content": "olá"})
        assert len(llm.history) == 1
        llm.reset_memory()
        assert len(llm.history) == 0

    def test_wipe_memory_command(self, llm):
        llm.history.append({"role": "user", "content": "oi"})
        resp = llm.ask("Geraldo, esquece o que conversamos")
        assert "Memória recente apagada" in resp
        assert len(llm.history) == 0

    @patch("tools.system.SystemTools.get_current_time", return_value="Agora são 15 horas.")
    def test_ask_get_time(self, mock_time, llm):
        resp = llm.ask("que horas são?")
        assert "15 horas" in resp
        mock_time.assert_called_once()

    def test_ask_thanks(self, llm):
        llm.history.append({"role": "user", "content": "obrigado"})
        resp = llm.ask("muito obrigado geraldo")
        assert "Por nada" in resp
        assert len(llm.history) == 0

    @patch("tools.calendar.CalendarTools.get_events", return_value="Sem eventos.")
    @patch("tools.system.SystemTools.get_weather", return_value="Céu limpo.")
    def test_ask_greeting_morning(self, mock_weather, mock_cal, llm):
        resp = llm.ask("bom dia geraldo")
        assert "Bom dia" in resp
        assert "Céu limpo" in resp

    @patch("tools.timer.TimerManager.get_active_summary", return_value="Nenhum timer ativo.")
    def test_ask_list_timers(self, mock_summary, llm):
        resp = llm.ask("quais timers estão ativos?")
        assert "Nenhum timer ativo" in resp

    @patch("tools.timer.TimerManager.cancel_item", return_value="Timer cancelado.")
    def test_ask_cancel_timers(self, mock_cancel, llm):
        resp = llm.ask("cancele o timer do bolo")
        assert "Timer cancelado" in resp
        mock_cancel.assert_called_once_with("bolo")

    @patch("tools.timer.TimerManager.pause_timer", return_value="Timer pausado.")
    def test_ask_pause_timer(self, mock_pause, llm):
        resp = llm.ask("pause o timer do bolo")
        assert "Timer pausado" in resp

    @patch("tools.timer.TimerManager.resume_timer", return_value="Timer retomado.")
    def test_ask_resume_timer(self, mock_resume, llm):
        resp = llm.ask("retome o timer do bolo")
        assert "Timer retomado" in resp

    @patch("tools.timer.TimerManager.add_alarm", return_value="Alarme definido para às 7 horas.")
    def test_ask_set_alarm(self, mock_alarm, llm):
        resp = llm.ask("coloque um alarme para as 7 da manhã")
        assert "Alarme definido" in resp
        mock_alarm.assert_called_once()

    @patch("tools.timer.TimerManager.add_timer", return_value="Timer de 5 minutos iniciado.")
    def test_ask_set_timer(self, mock_timer, llm):
        resp = llm.ask("coloque um timer de 5 minutos")
        assert "Timer de" in resp
        mock_timer.assert_called_once()

    @patch("tools.timer.TimerManager.stopwatch_control", return_value="Cronômetro iniciado.")
    def test_ask_stopwatch(self, mock_sw, llm):
        resp = llm.ask("inicie o cronômetro")
        assert "Cronômetro iniciado" in resp
        mock_sw.assert_called_once_with("start")

    @patch("tools.timer.TimerManager.pomodoro_control", return_value="Pomodoro iniciado.")
    def test_ask_pomodoro(self, mock_pomo, llm):
        resp = llm.ask("iniciar modo foco de 25 minutos")
        assert "Pomodoro iniciado" in resp
        mock_pomo.assert_called_once()

    @patch("tools.hyprland.HyprlandTools.change_workspace", return_value="Mudando para a área 2.")
    def test_ask_hyprland_workspace(self, mock_hl, llm):
        resp = llm.ask("mude para o workspace 2")
        assert "Mudando para a área 2" in resp
        mock_hl.assert_called_once_with("2")

    @patch("tools.hyprland.HyprlandTools.close_active_window", return_value="Fechando janela.")
    def test_ask_hyprland_close_window(self, mock_hl, llm):
        resp = llm.ask("fechar janela")
        assert "Fechando janela" in resp
        mock_hl.assert_called_once()

    @patch("tools.waybar.WaybarTools.restart_waybar", return_value="Waybar atualizada.")
    def test_ask_restart_waybar(self, mock_wb, llm):
        resp = llm.ask("reinicie a waybar")
        assert "Waybar atualizada" in resp
        mock_wb.assert_called_once()

    @patch("tools.ytmusic.YTMusicPlayer.play_song", return_value="Tocando Bohemian Rhapsody.")
    def test_ask_play_music(self, mock_yt, llm):
        resp = llm.ask("toque Bohemian Rhapsody")
        assert "Tocando Bohemian Rhapsody" in resp
        mock_yt.assert_called_once()

    @patch("tools.system.SystemTools.play_pause_media", return_value="Mídia alternada.")
    def test_ask_media_control(self, mock_media, llm):
        resp = llm.ask("pausar música")
        assert "Mídia alternada" in resp
        mock_media.assert_called_once()

    @patch("tools.system.SystemTools.set_volume", return_value="Volume aumentado.")
    def test_ask_volume_control(self, mock_vol, llm):
        resp = llm.ask("aumente o volume")
        assert "Volume aumentado" in resp
        mock_vol.assert_called_once_with("+")

    @patch("tools.system.SystemTools.get_weather", return_value="Tempo ensolarado em Anápolis.")
    def test_ask_weather(self, mock_weather, llm):
        resp = llm.ask("como está o tempo hoje?")
        assert "Tempo ensolarado" in resp
        mock_weather.assert_called_once()

    @patch("tools.calendar.CalendarTools.get_events", return_value="Compromissos hoje: Almoço às 12:00.")
    def test_ask_calendar_events(self, mock_cal, llm):
        resp = llm.ask("o que eu tenho agendado para hoje?")
        assert "Compromissos hoje" in resp
        mock_cal.assert_called_once()

    @patch("tools.calendar.CalendarTools.create_event", return_value="Agendado com sucesso.")
    def test_ask_create_calendar(self, mock_cal, llm):
        resp = llm.ask("agende uma reunião para hoje às 15 horas")
        assert "Agendado com sucesso" in resp
        mock_cal.assert_called_once()

    @patch("tools.calendar.CalendarTools.create_event", return_value="Agendado com sucesso: Estudar para a Prova amanhã o dia inteiro.")
    def test_ask_create_calendar_all_day_phrase(self, mock_cal, llm):
        resp = llm.ask("Marque um evento para amanhã, que vai durar o dia inteiro, chamar das 18 da manhã, as 18 da noite, chamado Estudar para a Prova.")
        assert "Agendado com sucesso" in resp
        mock_cal.assert_called_once()
        call_kwargs = mock_cal.call_args.kwargs
        assert call_kwargs["all_day"] is True
        assert call_kwargs["date_query"] == "amanhã"
        assert "Estudar" in call_kwargs["summary"]

    @patch.object(BrainLLM, "_summarize_with_llm", return_value="As notícias tratam de avanços na IA.")
    @patch("tools.news.NewsTools.get_news", return_value="Avanços em IA anunciados hoje.")
    def test_ask_news_search(self, mock_news, mock_sum, llm):
        with patch.object(BrainLLM, "_start_filler_thread") as mock_filler:
            mock_thread = MagicMock()
            mock_filler.return_value = mock_thread
            resp = llm.ask("notícias sobre IA")
            assert "notícias tratam de avanços" in resp
            mock_thread.join.assert_called_once()

    @patch.object(BrainLLM, "_summarize_with_llm", return_value="A distância é de aproximadamente 384 mil km.")
    @patch("tools.search.WebSearchTools.search_web", return_value="A Lua fica a 384.400 km.")
    def test_ask_web_search(self, mock_search, mock_sum, llm):
        with patch.object(BrainLLM, "_start_filler_thread") as mock_filler:
            mock_thread = MagicMock()
            mock_filler.return_value = mock_thread
            resp = llm.ask("pesquise na internet qual a distância até a Lua")
            assert "384 mil km" in resp
            mock_thread.join.assert_called_once()

    def test_ask_fallback_ollama_success(self, llm):
        mock_response = {
            "message": {
                "content": "O céu é azul devido ao espalhamento Rayleigh da luz solar na atmosfera."
            }
        }
        with patch.object(BrainLLM, "_post_json", return_value=mock_response):
            resp = llm.ask("Por que o céu é azul?")
            assert "espalhamento Rayleigh" in resp
            assert len(llm.history) == 2
            assert llm.history[0]["role"] == "user"
            assert llm.history[1]["role"] == "assistant"

    def test_ask_fallback_ollama_error(self, llm):
        with patch.object(BrainLLM, "_post_json", side_effect=urllib.error.URLError("Connection refused")):
            resp = llm.ask("Por que o céu é azul?")
            assert "Desculpe" in resp
            assert "indisponível" in resp

    def test_speak_callback_invoked(self):
        mock_speak = MagicMock()
        llm = BrainLLM(speak_fn=mock_speak)
        llm._do_speak_sync("Teste de fala")
        mock_speak.assert_called_once_with("Teste de fala")
