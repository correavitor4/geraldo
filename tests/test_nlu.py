import pytest
from brain.nlu import IntentEngine, NUMBER_WORDS

class TestNLUNormalization:
    def test_normalize_basic(self, shared_nlu_engine):
        engine = shared_nlu_engine
        assert engine._normalize("  Olá Mundo!  ") == "olá mundo"
        assert engine._normalize("TÁ A MERDA") == "timer"
        assert engine._normalize("taimer") == "timer"
        assert engine._normalize("para o manhã") == "amanhã"
        assert engine._normalize("para a manhã") == "amanhã"

    def test_normalize_time_colons(self, shared_nlu_engine):
        engine = shared_nlu_engine
        assert "7:50" in engine._normalize("alarme para 7h50")
        assert "7:50" in engine._normalize("alarme para 7h 50")
        assert "7:50" in engine._normalize("alarme para 7 : 50")
        assert "07:59" in engine._normalize("alarme para 07:59")

class TestNLUNumberParsing:
    @pytest.mark.parametrize("token, expected", [
        ("0", 0), ("1", 1), ("15", 15), ("50", 50),
        ("zero", 0), ("um", 1), ("uma", 1), ("dois", 2), ("duas", 2),
        ("três", 3), ("tres", 3), ("dez", 10), ("quinze", 15),
        ("vinte", 20), ("trinta", 30), ("quarenta", 40), ("cinquenta", 50),
        ("sessenta", 60),
        ("vinte e um", 21), ("vinte e duas", 22), ("trinta e cinco", 35),
        ("quarenta e sete", 47), ("cinquenta e nove", 59),
        ("invalid", 0), ("", 0)
    ])
    def test_parse_number(self, shared_nlu_engine, token, expected):
        assert shared_nlu_engine._parse_number(token) == expected

class TestNLUTimeExtraction:
    def test_extract_time_mins_before_hour(self, shared_nlu_engine):
        engine = shared_nlu_engine
        assert engine._extract_time("dez para as oito") == (7, 50)
        assert engine._extract_time("15 pras 8") == (7, 45)
        assert engine._extract_time("vinte para as sete da noite") == (18, 40)
        assert engine._extract_time("cinco para as duas da tarde") == (13, 55)

    def test_extract_time_colon_format(self, shared_nlu_engine):
        engine = shared_nlu_engine
        assert engine._extract_time("alarme para 7:50") == (7, 50)
        assert engine._extract_time("alarme para 07:59") == (7, 59)
        assert engine._extract_time("alarme para 19:30") == (19, 30)
        assert engine._extract_time("alarme para 8:00 da noite") == (20, 0)

    def test_extract_time_hours_format(self, shared_nlu_engine):
        engine = shared_nlu_engine
        assert engine._extract_time("às 7 horas") == (7, 0)
        assert engine._extract_time("às 7h") == (7, 0)
        assert engine._extract_time("às 7 horas e 30 minutos") == (7, 30)
        assert engine._extract_time("às 7 horas e meia") == (7, 30)
        assert engine._extract_time("às 8h e meia da noite") == (20, 30)

    def test_extract_time_e_format(self, shared_nlu_engine):
        engine = shared_nlu_engine
        assert engine._extract_time("às 7 e 50") == (7, 50)
        assert engine._extract_time("para as sete e meia") == (7, 30)
        assert engine._extract_time("às 7 e cinquenta e nove") == (7, 59)
        assert engine._extract_time("às 8 e 20 da noite") == (20, 20)

    def test_extract_time_digits_group(self, shared_nlu_engine):
        engine = shared_nlu_engine
        assert engine._extract_time("alarme 750") == (7, 50)
        assert engine._extract_time("alarme 0759") == (7, 59)
        assert engine._extract_time("alarme 1950") == (19, 50)

    def test_extract_time_single_hour(self, shared_nlu_engine):
        engine = shared_nlu_engine
        assert engine._extract_time("para as 7") == (7, 0)
        assert engine._extract_time("às 8 da noite") == (20, 0)
        assert engine._extract_time("para as 3 da tarde") == (15, 0)

    def test_extract_time_fallback(self, shared_nlu_engine):
        engine = shared_nlu_engine
        assert engine._extract_time("sem horário algum") == (8, 0)

    def test_extract_time_midday_midnight(self, shared_nlu_engine):
        engine = shared_nlu_engine
        assert engine._extract_time(engine._normalize("ao meio-dia")) == (12, 0)
        assert engine._extract_time(engine._normalize("ao meio dia e meia")) == (12, 30)
        assert engine._extract_time(engine._normalize("à meia-noite")) == (0, 0)
        assert engine._extract_time(engine._normalize("à meia-noite e meia")) == (0, 30)

    def test_extract_time_colloquial(self, shared_nlu_engine):
        engine = shared_nlu_engine
        # "quinze pro meio-dia" -> 11:45
        assert engine._extract_time(engine._normalize("quinze pro meio-dia")) == (11, 45)
        # "dez pra meia-noite" -> 23:50
        assert engine._extract_time(engine._normalize("dez pra meia-noite")) == (23, 50)
        # "meia-noite e quinze" -> 00:15
        assert engine._extract_time(engine._normalize("meia-noite e quinze")) == (0, 15)
        # "meio-dia e vinte" -> 12:20
        assert engine._extract_time(engine._normalize("meio-dia e vinte")) == (12, 20)

    def test_extract_relative_minutes(self, shared_nlu_engine):
        engine = shared_nlu_engine
        assert engine._extract_relative_minutes(engine._normalize("daqui a meia hora")) == 30
        assert engine._extract_relative_minutes(engine._normalize("daqui a uma hora e meia")) == 90
        assert engine._extract_relative_minutes(engine._normalize("em 20 minutos")) == 20
        assert engine._extract_relative_minutes(engine._normalize("dentro de quinze minutos")) == 15
        assert engine._extract_relative_minutes(engine._normalize("sem tempo relativo")) is None

    def test_extract_duration_range(self, shared_nlu_engine):
        engine = shared_nlu_engine
        assert engine._extract_duration(engine._normalize("evento das 14 às 16 horas")) == (120, False)
        assert engine._extract_duration(engine._normalize("das 9:00 até 11:30")) == (150, False)
        assert engine._extract_duration(engine._normalize("das 8 da manhã às 18 da noite")) == (600, False)

class TestNLUHardRules:
    @pytest.mark.parametrize("phrase, expected_intent", [
        ("bom dia geraldo", "greeting_morning"),
        ("boa dia", "greeting_morning"),
        ("muito obrigado", "thanks"),
        ("valeu geraldo", "thanks"),
        ("que horas são agora", "get_time"),
        ("hora certa", "get_time"),
        ("reinicie a waybar", "restart_waybar"),
        ("reiniciar a barra", "restart_waybar"),
        ("inicie o cronômetro", "control_stopwatch"),
        ("pause o cronometro", "control_stopwatch"),
        ("pause o timer", "pause_timer"),
        ("retome o timer", "resume_timer"),
        ("cancele todos os timers", "cancel_timers"),
        ("desative todos os alarmes", "cancel_timers"),
        ("silêncio", "cancel_timers"),
        ("pare de tocar", "cancel_timers"),
        ("quais timers estão ativos", "list_timers"),
        ("coloque um alarme para as 7", "set_alarm"),
        ("defina um timer de 10 minutos", "set_timer"),
        ("iniciar pomodoro", "pomodoro_control"),
        ("iniciar pausa longa", "pomodoro_control"),
        ("pausa longa de 15 minutos", "pomodoro_control"),
        ("descanso longo", "pomodoro_control"),
        ("próximo ciclo", "pomodoro_control"),
        ("toque uma música", "play_music"),
        ("pesquise na internet sobre cotação", "search_web"),
        ("mude para o workspace 2", "hyprland_control"),
        ("marque um evento para amanhã chamado estudar para a prova", "create_calendar"),
        ("agende uma reunião para amanhã às 10 horas", "create_calendar"),
        ("coloque na minha agenda médico amanhã às 14 horas", "create_calendar"),
        ("como está a agenda para amanhã", "get_calendar"),
        ("o que eu tenho agendado para hoje", "get_calendar"),
        ("quais são meus compromissos de amanhã", "get_calendar"),
        ("qual o meu próximo compromisso", "get_calendar"),
        ("agenda da semana", "get_calendar"),
        ("cancele o evento da agenda chamado dentista", "delete_calendar"),
        ("desmarque a reunião de amanhã", "delete_calendar"),
        ("apague o compromisso de hoje", "delete_calendar"),
    ])
    def test_hard_rules_detection(self, shared_nlu_engine, phrase, expected_intent):
        norm = shared_nlu_engine._normalize(phrase)
        assert shared_nlu_engine._hard_rules(norm) == expected_intent

class TestNLUIntentsAndSlots:
    def test_get_time(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("que horas são?")
        assert intent == "get_time"
        assert conf >= 0.35

    def test_thanks(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("Muito obrigado, Geraldo!")
        assert intent == "thanks"

    def test_greeting_morning(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("Bom dia Geraldo")
        assert intent == "greeting_morning"

    def test_set_alarm_slots(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("coloque um alarme para as 7:50 chamado Reunião")
        assert intent == "set_alarm"
        assert slots["hour"] == 7
        assert slots["minute"] == 50
        assert slots["label"] == "Reunião"

    def test_set_alarm_night(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("defina um alarme para as 10 da noite")
        assert intent == "set_alarm"
        assert slots["hour"] == 22
        assert slots["minute"] == 0
        assert slots["label"] == "Alarme"

    def test_set_timer_slots_minutes(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("defina um timer de 15 minutos para o bolo")
        assert intent == "set_timer"
        assert slots["hours"] == 0
        assert slots["minutes"] == 15
        assert slots["seconds"] == 0
        assert slots["label"] == "Bolo"

    def test_set_timer_duration_only_label_not_overwritten(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("coloque um timer para 10 minutos")
        assert intent == "set_timer"
        assert slots["minutes"] == 10
        # "10 minutos" não deve virar label
        assert slots["label"] == "Timer"

    def test_set_timer_hours_minutes_seconds(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("timer de 1 hora e 30 minutos e 45 segundos")
        assert intent == "set_timer"
        assert slots["hours"] == 1
        assert slots["minutes"] == 30
        assert slots["seconds"] == 45

    def test_cancel_timers_slots(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("cancele todos os alarmes")
        assert intent == "cancel_timers"
        assert slots["query"] == "todos os alarmes"

        intent, conf, slots = shared_nlu_engine.predict("cancele todos os timers")
        assert intent == "cancel_timers"
        assert slots["query"] == "todos os timers"

        intent, conf, slots = shared_nlu_engine.predict("cancele o timer do macarrão")
        assert intent == "cancel_timers"
        assert "macarrão" in slots["query"]

    def test_pause_resume_timer_slots(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("pause o timer do café")
        assert intent == "pause_timer"
        assert "café" in slots["query"]

        intent, conf, slots = shared_nlu_engine.predict("retome o timer do café")
        assert intent == "resume_timer"
        assert "café" in slots["query"]

    def test_stopwatch_slots(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("inicie o cronômetro")
        assert intent == "control_stopwatch"
        assert slots["action"] == "start"

        intent, conf, slots = shared_nlu_engine.predict("pausar o cronômetro")
        assert intent == "control_stopwatch"
        assert slots["action"] == "pause"

        intent, conf, slots = shared_nlu_engine.predict("zerar o cronômetro")
        assert intent == "control_stopwatch"
        assert slots["action"] == "reset"

    def test_pomodoro_control_slots(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("iniciar pomodoro de 25 minutos")
        assert intent == "pomodoro_control"
        assert slots["action"] == "start"
        assert slots["work_minutes"] == 25

        intent, conf, slots = shared_nlu_engine.predict("iniciar pomodoro de vinte minutos")
        assert intent == "pomodoro_control"
        assert slots["action"] == "start"
        assert slots["work_minutes"] == 20

        intent, conf, slots = shared_nlu_engine.predict("pausar o modo foco")
        assert intent == "pomodoro_control"
        assert slots["action"] == "pause"

        intent, conf, slots = shared_nlu_engine.predict("próximo ciclo do pomodoro")
        assert intent == "pomodoro_control"
        assert slots["action"] == "advance"

        intent, conf, slots = shared_nlu_engine.predict("parar o pomodoro")
        assert intent == "pomodoro_control"
        assert slots["action"] == "stop"

        intent, conf, slots = shared_nlu_engine.predict("iniciar pomodoro com 25 minutos de foco e 10 minutos de descanso")
        assert intent == "pomodoro_control"
        assert slots["action"] == "start"
        assert slots["work_minutes"] == 25
        assert slots["break_minutes"] == 10

        intent, conf, slots = shared_nlu_engine.predict("status do pomodoro")
        assert intent == "pomodoro_control"
        assert slots["action"] == "status"

        intent, conf, slots = shared_nlu_engine.predict("iniciar pausa longa")
        assert intent == "pomodoro_control"
        assert slots["action"] == "long_break"

        intent, conf, slots = shared_nlu_engine.predict("pausa longa de 20 minutos")
        assert intent == "pomodoro_control"
        assert slots["action"] == "long_break"
        assert slots["long_break_minutes"] == 20

        intent, conf, slots = shared_nlu_engine.predict("descanso longo de quinze minutos")
        assert intent == "pomodoro_control"
        assert slots["action"] == "long_break"
        assert slots["long_break_minutes"] == 15

        intent, conf, slots = shared_nlu_engine.predict("iniciar pomodoro com 25 minutos de foco, pausa de 5 e pausa longa de 15 minutos a cada 4 ciclos")
        assert intent == "pomodoro_control"
        assert slots["action"] == "start"
        assert slots["work_minutes"] == 25
        assert slots["break_minutes"] == 5
        assert slots["long_break_minutes"] == 15
        assert slots["long_break_interval"] == 4

        # Frase real dos logs do usuário
        intent, conf, slots = shared_nlu_engine.predict(
            "Iniciem o Pomodoro com 30 minutos de foco, 5 minutos de pausas curtas, 15 minutos de pausas longas, e 3 ciclos antes das pausas longas."
        )
        assert intent == "pomodoro_control"
        assert slots["action"] == "start"
        assert slots["work_minutes"] == 30
        assert slots["break_minutes"] == 5
        assert slots["long_break_minutes"] == 15
        assert slots["long_break_interval"] == 3

    def test_hyprland_control_slots(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("mude para o workspace 4")
        assert intent == "hyprland_control"
        assert slots["action"] == "workspace"
        assert slots["target"] == "4"

        intent, conf, slots = shared_nlu_engine.predict("fechar janela ativa")
        assert intent == "hyprland_control"
        assert slots["action"] == "close_window"

        intent, conf, slots = shared_nlu_engine.predict("colocar em tela cheia")
        assert intent == "hyprland_control"
        assert slots["action"] == "fullscreen"

        intent, conf, slots = shared_nlu_engine.predict("tornar janela flutuante")
        assert intent == "hyprland_control"
        assert slots["action"] == "floating"

        intent, conf, slots = shared_nlu_engine.predict("abrir o launcher de aplicativos")
        assert intent == "hyprland_control"
        assert slots["action"] == "launcher"

        intent, conf, slots = shared_nlu_engine.predict("ajuste o brilho para 75%")
        assert intent == "hyprland_control"
        assert slots["action"] == "brightness"
        assert slots["target"] == "75%"

    def test_play_music_slots(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("toque a música Bohemian Rhapsody no YouTube")
        assert intent == "play_music"
        assert "bohemian rhapsody" in slots["query"].lower()
        assert slots["item_type"] == "auto"

        intent, conf, slots = shared_nlu_engine.predict("toque o álbum Dark Side of the Moon")
        assert intent == "play_music"
        assert "dark side of the moon" in slots["query"].lower()
        assert slots["item_type"] == "album"

    def test_volume_control_slots(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("aumente o volume")
        assert intent == "volume_control"
        assert slots["change"] == "+"

        intent, conf, slots = shared_nlu_engine.predict("abaixe o volume")
        assert intent == "volume_control"
        assert slots["change"] == "-"

        intent, conf, slots = shared_nlu_engine.predict("coloque o som no mudo")
        assert intent == "volume_control"
        assert slots["change"] == "mute"

        intent, conf, slots = shared_nlu_engine.predict("defina o volume para 60%")
        assert intent == "volume_control"
        assert slots["change"] == "60"

    def test_weather_slots(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("qual a previsão do tempo para Goiânia hoje")
        assert intent == "get_weather"
        assert slots["query_type"] == "hoje"
        assert "Goiânia" in slots["query"] or "goiânia" in slots["query"].lower()

        intent, conf, slots = shared_nlu_engine.predict("vai chover amanhã")
        assert intent == "get_weather"
        assert slots["query_type"] == "amanhã"

    def test_news_slots(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("notícias sobre inteligência artificial")
        assert intent == "get_news"
        assert "inteligência artificial" in slots["query"]

        intent, conf, slots = shared_nlu_engine.predict("quais são as últimas manchetes de hoje")
        assert intent == "get_news"
        assert slots["query"] == "geral"

    def test_search_web_slots(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("pesquise na internet sobre a distância da Terra até a Lua")
        assert intent == "search_web"
        assert "distância da terra" in slots["query"].lower()

    def test_create_calendar_user_phrase_all_day(self, shared_nlu_engine):
        phrase = "Marque um evento para amanhã, que vai durar o dia inteiro, chamar das 18 da manhã, as 18 da noite, chamado Estudar para a Prova."
        intent, conf, slots = shared_nlu_engine.predict(phrase)
        assert intent == "create_calendar"
        assert conf >= 0.35
        assert slots["all_day"] is True
        assert slots["date_query"] == "amanhã"
        assert "Estudar" in slots["summary"]
        assert slots["duration_minutes"] == 1440

    def test_create_calendar_slots_with_time_and_duration(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("agende uma reunião com a equipe amanhã às 14 horas que vai durar 2 horas")
        assert intent == "create_calendar"
        assert slots["all_day"] is False
        assert slots["time_str"] == "14:00"
        assert slots["duration_minutes"] == 120
        assert slots["date_query"] == "amanhã"

    def test_create_calendar_explicit_chamado(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("marque um evento chamado Dentista amanhã às 15 horas")
        assert intent == "create_calendar"
        assert slots["summary"] == "Dentista"
        assert slots["time_str"] == "15:00"
        assert slots["date_query"] == "amanhã"

    def test_get_calendar_slots(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("como está a agenda para amanhã?")
        assert intent == "get_calendar"
        assert slots["date_query"] == "amanhã"

    def test_get_calendar_slots_next(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("qual é o meu próximo compromisso?")
        assert intent == "get_calendar"
        assert slots["date_query"] == "próximo"

    def test_get_calendar_slots_week(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("como está a agenda desta semana?")
        assert intent == "get_calendar"
        assert slots["date_query"] == "semana"

    def test_create_calendar_slots_midday(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("marque um almoço amanhã ao meio-dia e meia")
        assert intent == "create_calendar"
        assert slots["time_str"] == "12:30"
        assert slots["date_query"] == "amanhã"

    def test_delete_calendar_slots_explicit(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("cancele o evento da agenda chamado Dentista de amanhã")
        assert intent == "delete_calendar"
        assert "Dentista" in slots["summary"]
        assert slots["date_query"] == "amanhã"

    def test_delete_calendar_slots_heuristic(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("desmarque a reunião de amanhã")
        assert intent == "delete_calendar"
        assert slots["date_query"] == "amanhã"

    def test_question_fallback_to_conversa_llm(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("Por que o céu é azul?")
        assert intent == "conversa_llm"

        intent, conf, slots = shared_nlu_engine.predict("Explique como funciona a relatividade")
        assert intent == "conversa_llm"

        intent, conf, slots = shared_nlu_engine.predict("O que é computação quântica?")
        assert intent == "conversa_llm"

    def test_empty_string(self, shared_nlu_engine):
        intent, conf, slots = shared_nlu_engine.predict("")
        assert intent == "unknown"
        assert conf == 0.0
        assert slots == {}
