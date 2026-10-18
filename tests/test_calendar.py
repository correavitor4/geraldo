import pytest
import datetime
from unittest.mock import patch, MagicMock
from tools.calendar import format_speech_time, CalendarTools

class TestFormatSpeechTime:
    def test_midnight(self):
        assert format_speech_time("00:00") == "à meia-noite"
        assert format_speech_time("00:30") == "à meia-noite e meia"
        assert format_speech_time("00:15") == "à meia-noite e 15"

    def test_midday(self):
        assert format_speech_time("12:00") == "ao meio-dia"
        assert format_speech_time("12:30") == "ao meio-dia e meia"
        assert format_speech_time("12:45") == "ao meio-dia e 45"

    def test_single_hour(self):
        assert format_speech_time("01:00") == "à uma"
        assert format_speech_time("13:00") == "à uma da tarde"
        assert format_speech_time("01:30") == "à uma e meia da manhã"
        assert format_speech_time("13:30") == "à uma e meia da tarde"

    def test_general_hours(self):
        assert format_speech_time("08:00") == "às oito"
        assert format_speech_time("08:30") == "às oito e meia da manhã"
        assert format_speech_time("14:15") == "às duas e 15 da tarde"
        assert format_speech_time("20:00") == "às oito da noite"

    def test_invalid_fallback(self):
        assert format_speech_time("invalid") == "às invalid"

class TestCalendarDateParsing:
    def test_parse_hoje(self):
        today = datetime.date.today()
        assert CalendarTools._parse_target_date("hoje") == today
        assert CalendarTools._parse_target_date("") == today

    def test_parse_amanha(self):
        today = datetime.date.today()
        assert CalendarTools._parse_target_date("amanhã") == today + datetime.timedelta(days=1)
        assert CalendarTools._parse_target_date("pra manha") == today + datetime.timedelta(days=1)

    def test_parse_depois_de_amanha(self):
        today = datetime.date.today()
        # Garante que "depois de amanhã" retorna +2 dias e não cai no if de "amanhã"
        assert CalendarTools._parse_target_date("depois de amanhã") == today + datetime.timedelta(days=2)
        assert CalendarTools._parse_target_date("depois de amanha") == today + datetime.timedelta(days=2)

    def test_parse_weekdays(self):
        today = datetime.date.today()
        parsed = CalendarTools._parse_target_date("próxima quarta-feira")
        assert parsed.weekday() == 2
        assert parsed > today

    def test_parse_iso_date(self):
        assert CalendarTools._parse_target_date("2026-12-25") == datetime.date(2026, 12, 25)

    def test_parse_invalid_iso_date(self):
        today = datetime.date.today()
        # Data impossível (31 de fevereiro) deve retornar fallback sem quebrar com ValueError
        assert CalendarTools._parse_target_date("2026-02-31") == today

    def test_parse_dia_number(self):
        today = datetime.date.today()
        parsed = CalendarTools._parse_target_date("dia 28")
        assert parsed.day == 28

class TestCalendarEventsAndCreation:
    @patch.object(CalendarTools, "get_service", return_value=None)
    def test_get_events_no_service(self, mock_svc):
        res = CalendarTools.get_events("hoje")
        assert "não está configurada" in res

    def test_get_events_empty(self):
        mock_svc = MagicMock()
        mock_svc.events().list().execute.return_value = {"items": []}
        with patch.object(CalendarTools, "get_service", return_value=mock_svc):
            res = CalendarTools.get_events("hoje")
            assert "Você não tem compromissos agendados hoje" in res

    def test_get_events_with_items(self):
        mock_svc = MagicMock()
        mock_svc.events().list().execute.return_value = {
            "items": [
                {
                    "summary": "Reunião de Alinhamento",
                    "start": {"dateTime": "2026-10-18T14:30:00Z"}
                },
                {
                    "summary": "Feriado",
                    "start": {"date": "2026-10-18"}
                }
            ]
        }
        with patch.object(CalendarTools, "get_service", return_value=mock_svc):
            res = CalendarTools.get_events("hoje")
            assert "Reunião de Alinhamento" in res
            assert "o dia todo: Feriado" in res
            assert "às duas e meia da tarde" in res

    def test_get_events_error(self):
        mock_svc = MagicMock()
        mock_svc.events().list().execute.side_effect = Exception("API Error")
        with patch.object(CalendarTools, "get_service", return_value=mock_svc):
            res = CalendarTools.get_events("hoje")
            assert "Não foi possível carregar os compromissos" in res

    @patch.object(CalendarTools, "get_service", return_value=None)
    def test_create_event_no_service(self, mock_svc):
        res = CalendarTools.create_event(summary="Reunião")
        assert "não está autenticada" in res

    def test_create_event_success(self):
        mock_insert = MagicMock()
        mock_insert.execute.return_value = {"id": "12345"}
        mock_events = MagicMock()
        mock_events.insert.return_value = mock_insert
        mock_svc = MagicMock()
        mock_svc.events.return_value = mock_events

        with patch.object(CalendarTools, "get_service", return_value=mock_svc):
            res = CalendarTools.create_event(
                summary="Dentista",
                date_query="hoje",
                time_str="10:00",
                duration_minutes=45
            )
            assert "Agendado com sucesso: Dentista hoje às dez" in res
            mock_events.insert.assert_called_once()
            call_body = mock_events.insert.call_args[1]["body"]
            assert call_body["summary"] == "Dentista"
            assert "10:00:00" in call_body["start"]["dateTime"]
            assert "10:45:00" in call_body["end"]["dateTime"]

    def test_create_event_api_error(self):
        mock_insert = MagicMock()
        mock_insert.execute.side_effect = Exception("Insert Error")
        mock_events = MagicMock()
        mock_events.insert.return_value = mock_insert
        mock_svc = MagicMock()
        mock_svc.events.return_value = mock_events

        with patch.object(CalendarTools, "get_service", return_value=mock_svc):
            res = CalendarTools.create_event(summary="Dentista")
            assert "Ocorreu um erro ao tentar criar o evento" in res

    def test_create_event_all_day(self):
        mock_insert = MagicMock()
        mock_insert.execute.return_value = {"id": "all_day_123"}
        mock_events = MagicMock()
        mock_events.insert.return_value = mock_insert
        mock_svc = MagicMock()
        mock_svc.events.return_value = mock_events

        with patch.object(CalendarTools, "get_service", return_value=mock_svc):
            res = CalendarTools.create_event(
                summary="Estudar para a Prova",
                date_query="amanhã",
                all_day=True
            )
            assert "Agendado com sucesso: Estudar para a Prova amanhã o dia inteiro" in res
            mock_events.insert.assert_called_once()
            call_body = mock_events.insert.call_args[1]["body"]
            assert call_body["summary"] == "Estudar para a Prova"
            assert "date" in call_body["start"]
            assert "dateTime" not in call_body["start"]
