import pytest
import time
import json
import os
from unittest.mock import patch, MagicMock

class TestTimerManagerBasic:
    def test_add_timer_valid(self, isolated_timer_manager):
        tm = isolated_timer_manager
        msg = tm.add_timer(hours=1, minutes=10, seconds=5, label="Bolo")
        assert "1 hora e 10 minutos e 5 segundos" in msg
        assert "Bolo" in msg
        assert len(tm._timers) == 1
        tid = next(iter(tm._timers))
        assert tm._timers[tid]["label"] == "Bolo"

    def test_add_timer_singular_plural(self, isolated_timer_manager):
        tm = isolated_timer_manager
        msg = tm.add_timer(hours=2, minutes=1, seconds=1, label="Teste")
        assert "2 horas e 1 minuto e 1 segundo" in msg

    def test_add_timer_zero_duration(self, isolated_timer_manager):
        tm = isolated_timer_manager
        msg = tm.add_timer(hours=0, minutes=0, seconds=0)
        assert "Defina um tempo válido" in msg
        assert len(tm._timers) == 0

    def test_add_alarm(self, isolated_timer_manager):
        tm = isolated_timer_manager
        msg1 = tm.add_alarm(hour=8, minute=0, label="Acordar")
        assert "às 8 horas" in msg1
        assert len(tm._alarms) == 1

        msg2 = tm.add_alarm(hour=8, minute=30, label="Remédio")
        assert "às 8 horas e 30 minutos" in msg2
        assert len(tm._alarms) == 2

    def test_get_active_summary_empty(self, isolated_timer_manager):
        tm = isolated_timer_manager
        assert "não tem nenhum timer ou alarme ativo" in tm.get_active_summary()

    def test_get_active_summary_populated(self, isolated_timer_manager):
        tm = isolated_timer_manager
        tm.add_timer(minutes=5, label="Café")
        tm.add_alarm(hour=7, minute=15, label="Trabalho")
        summary = tm.get_active_summary()
        assert "Café" in summary
        assert "Trabalho" in summary
        assert "07:15" in summary

class TestTimerManagerPauseResumeCancel:
    def test_pause_and_resume_specific_timer(self, isolated_timer_manager):
        tm = isolated_timer_manager
        tm.add_timer(minutes=10, label="Café")
        
        msg_pause = tm.pause_timer("café")
        assert "pausado com sucesso" in msg_pause
        tid = next(iter(tm._timers))
        assert tm._timers[tid]["paused"] is True

        # Tentar pausar novamente
        msg_again = tm.pause_timer("café")
        assert "já está pausado" in msg_again

        # Retomar
        msg_resume = tm.resume_timer("café")
        assert "retomado" in msg_resume
        assert tm._timers[tid]["paused"] is False

        # Tentar retomar novamente
        msg_res_again = tm.resume_timer("café")
        assert "já está rodando" in msg_res_again

    def test_pause_and_resume_all_timers(self, isolated_timer_manager):
        tm = isolated_timer_manager
        tm.add_timer(minutes=5, label="T1")
        tm.add_timer(minutes=10, label="T2")

        msg = tm.pause_timer("todos")
        assert "Todos os timers foram pausados" in msg
        for t in tm._timers.values():
            assert t["paused"] is True

        msg_res = tm.resume_timer("todos")
        assert "Todos os timers foram retomados" in msg_res
        for t in tm._timers.values():
            assert t["paused"] is False

    def test_pause_resume_not_found(self, isolated_timer_manager):
        tm = isolated_timer_manager
        assert "Não encontrei nenhum timer" in tm.pause_timer("inexistente")
        assert "Não encontrei nenhum timer" in tm.resume_timer("inexistente")

    def test_cancel_item_by_name(self, isolated_timer_manager):
        tm = isolated_timer_manager
        tm.add_timer(minutes=5, label="Batata")
        assert len(tm._timers) == 1
        msg = tm.cancel_item("batata")
        assert "Timer Batata cancelado" in msg
        assert len(tm._timers) == 0

    def test_cancel_all_timers(self, isolated_timer_manager):
        tm = isolated_timer_manager
        tm.add_timer(minutes=5, label="T1")
        tm.add_timer(minutes=10, label="T2")
        tm.add_alarm(hour=8, minute=0, label="A1")

        msg = tm.cancel_item("todos os timers")
        assert "2 timer(s) cancelado(s)" in msg
        assert len(tm._timers) == 0
        assert len(tm._alarms) == 1

    def test_cancel_all_alarms(self, isolated_timer_manager):
        tm = isolated_timer_manager
        tm.add_alarm(hour=8, minute=0, label="A1")
        tm.add_alarm(hour=9, minute=0, label="A2")
        tm.add_timer(minutes=5, label="T1")

        msg = tm.cancel_item("todos os alarmes")
        assert "2 alarme(s) cancelado(s)" in msg
        assert len(tm._alarms) == 0
        assert len(tm._timers) == 1

    def test_cancel_all_everything(self, isolated_timer_manager):
        tm = isolated_timer_manager
        tm.add_timer(minutes=5, label="T1")
        tm.add_alarm(hour=8, minute=0, label="A1")
        msg = tm.cancel_all()
        assert "Todos os timers e alarmes foram cancelados" in msg
        assert len(tm._timers) == 0
        assert len(tm._alarms) == 0

    def test_cancel_single_generic_alarm(self, isolated_timer_manager):
        tm = isolated_timer_manager
        tm.add_alarm(hour=7, minute=0, label="Despertar")
        msg = tm.cancel_item("o alarme")
        assert "Alarme Despertar cancelado" in msg
        assert len(tm._alarms) == 0

    def test_cancel_single_generic_timer(self, isolated_timer_manager):
        tm = isolated_timer_manager
        tm.add_timer(minutes=5, label="Cozimento")
        msg = tm.cancel_item("o timer")
        assert "Timer Cozimento cancelado" in msg
        assert len(tm._timers) == 0

class TestTimerManagerFuzzyMatch:
    def test_find_best_match_substring_and_fuzzy(self, isolated_timer_manager):
        tm = isolated_timer_manager
        items = {
            "id1": {"label": "Bolo de Cenoura"},
            "id2": {"label": "Café da Manhã"}
        }
        assert tm._find_best_match("cenoura", items) == "id1"
        assert tm._find_best_match("bolo", items) == "id1"
        assert tm._find_best_match("cafe", items) == "id2"
        assert tm._find_best_match("xyz", items) is None
        assert tm._find_best_match("xyz", {}) is None

class TestTimerManagerStopwatch:
    def test_stopwatch_lifecycle(self, isolated_timer_manager):
        tm = isolated_timer_manager
        assert tm._stopwatch["running"] is False

        # Start
        msg_start = tm.stopwatch_control("start")
        assert "iniciado" in msg_start
        assert tm._stopwatch["running"] is True

        # Start again when running
        msg_start_again = tm.stopwatch_control("start")
        assert "já está rodando" in msg_start_again

        # Pause
        time.sleep(0.05)
        msg_pause = tm.stopwatch_control("pause")
        assert "pausado" in msg_pause
        assert tm._stopwatch["running"] is False
        assert tm._stopwatch["elapsed"] > 0

        # Pause again when stopped
        msg_pause_again = tm.stopwatch_control("pause")
        assert "não está ativo" in msg_pause_again

        # Reset
        msg_reset = tm.stopwatch_control("reset")
        assert "zerado" in msg_reset
        assert tm._stopwatch["elapsed"] == 0.0

    def test_stopwatch_invalid_action(self, isolated_timer_manager):
        tm = isolated_timer_manager
        assert tm.stopwatch_control("invalid") == "Ação inválida."

class TestTimerManagerPomodoro:
    def test_pomodoro_start_and_status(self, isolated_timer_manager):
        tm = isolated_timer_manager
        msg = tm.pomodoro_control("start", work_minutes=30, break_minutes=5)
        assert "30 minutos de foco" in msg
        assert tm._pomodoro["state"] == "work"
        assert tm._pomodoro["work_duration"] == 1800

        msg_status = tm.pomodoro_control("status")
        assert "ciclo 1 de foco" in msg_status

    def test_pomodoro_pause_and_resume(self, isolated_timer_manager):
        tm = isolated_timer_manager
        tm.pomodoro_control("start")
        msg_pause = tm.pomodoro_control("pause")
        assert "Pomodoro pausado" in msg_pause
        assert tm._pomodoro["state"] == "paused"

        msg_resume = tm.pomodoro_control("resume")
        assert "retomado no modo foco" in msg_resume
        assert tm._pomodoro["state"] == "work"

    def test_pomodoro_toggle_no_deadlock(self, isolated_timer_manager):
        """Verifica que toggle() executa recursivamente sem travar a thread (RLock)."""
        tm = isolated_timer_manager
        # De idle -> toggle deve chamar start
        msg = tm.pomodoro_control("toggle")
        assert "Pomodoro iniciado" in msg
        assert tm._pomodoro["state"] == "work"

        # De work -> toggle deve chamar pause
        msg2 = tm.pomodoro_control("toggle")
        assert "Pomodoro pausado" in msg2
        assert tm._pomodoro["state"] == "paused"

        # De paused -> toggle deve chamar resume
        msg3 = tm.pomodoro_control("toggle")
        assert "retomado" in msg3
        assert tm._pomodoro["state"] == "work"

    def test_pomodoro_advance_cycle(self, isolated_timer_manager):
        tm = isolated_timer_manager
        tm.pomodoro_control("start")
        # Avança de foco para pausa curta
        msg_adv = tm.pomodoro_control("advance")
        assert "Iniciando pausa curta" in msg_adv
        assert tm._pomodoro["state"] == "break"

        # Avança de pausa para próximo ciclo de foco
        msg_adv2 = tm.pomodoro_control("advance")
        assert "Iniciando ciclo 2 de foco" in msg_adv2
        assert tm._pomodoro["state"] == "work"
        assert tm._pomodoro["cycle"] == 2

    def test_pomodoro_finished_states(self, isolated_timer_manager):
        tm = isolated_timer_manager
        tm._pomodoro["state"] = "work_finished"
        tm._pomodoro["cycle"] = 1
        msg = tm.pomodoro_control("status")
        assert "terminou" in msg

        # Iniciar a partir de work_finished deve avançar para pausa
        msg_start = tm.pomodoro_control("start")
        assert "Iniciando pausa curta" in msg_start
        assert tm._pomodoro["state"] == "break"

    def test_pomodoro_stop(self, isolated_timer_manager):
        tm = isolated_timer_manager
        tm.pomodoro_control("start")
        msg = tm.pomodoro_control("stop")
        assert "Pomodoro encerrado" in msg
        assert tm._pomodoro["state"] == "idle"
        assert tm._pomodoro["cycle"] == 1

    def test_pomodoro_start_with_custom_long_break(self, isolated_timer_manager):
        tm = isolated_timer_manager
        msg = tm.pomodoro_control(
            "start",
            work_minutes=25,
            break_minutes=5,
            long_break_minutes=20,
            long_break_interval=3,
            cycle=1
        )
        assert "25 minutos de foco" in msg
        assert tm._pomodoro["long_break_duration"] == 20 * 60
        assert tm._pomodoro["long_break_interval"] == 3
        assert tm._pomodoro["state"] == "work"

    def test_pomodoro_automatic_long_break_on_interval(self, isolated_timer_manager):
        tm = isolated_timer_manager
        # Intervalo de 3 ciclos
        tm.pomodoro_control("start", work_minutes=25, break_minutes=5, long_break_minutes=15, long_break_interval=3, cycle=1)
        
        # Ciclo 1: work -> pausa curta
        msg1 = tm.pomodoro_control("advance")
        assert "Iniciando pausa curta" in msg1
        assert tm._pomodoro["state"] == "break"
        
        # Pausa curta -> ciclo 2 work
        msg2 = tm.pomodoro_control("advance")
        assert "ciclo 2 de foco" in msg2
        assert tm._pomodoro["cycle"] == 2
        assert tm._pomodoro["state"] == "work"

        # Ciclo 2: work -> pausa curta
        msg3 = tm.pomodoro_control("advance")
        assert "Iniciando pausa curta" in msg3
        assert tm._pomodoro["state"] == "break"

        # Pausa curta -> ciclo 3 work
        msg4 = tm.pomodoro_control("advance")
        assert "ciclo 3 de foco" in msg4
        assert tm._pomodoro["cycle"] == 3
        assert tm._pomodoro["state"] == "work"

        # Ciclo 3 (múltiplo do intervalo 3): work -> PAUSA LONGA!
        msg5 = tm.pomodoro_control("advance")
        assert "pausa longa" in msg5.lower()
        assert tm._pomodoro["state"] == "long_break"
        assert tm._pomodoro["long_break_duration"] == 15 * 60
        assert tm._pomodoro["remaining"] == 15 * 60

        # Pausa longa concluída -> ciclo 4 work
        msg6 = tm.pomodoro_control("advance")
        assert "ciclo 4 de foco" in msg6
        assert tm._pomodoro["cycle"] == 4
        assert tm._pomodoro["state"] == "work"

    def test_pomodoro_direct_long_break_action(self, isolated_timer_manager):
        tm = isolated_timer_manager
        # Iniciar diretamente uma pausa longa
        msg = tm.pomodoro_control("long_break", long_break_minutes=20)
        assert "pausa longa de 20 minutos" in msg.lower()
        assert tm._pomodoro["state"] == "long_break"
        assert tm._pomodoro["long_break_duration"] == 20 * 60

        # Status deve indicar pausa longa
        msg_st = tm.pomodoro_control("status")
        assert "pausa longa" in msg_st.lower()

        # Também funciona com alias 'pausa_longa'
        msg2 = tm.pomodoro_control("pausa_longa", long_break_minutes=10)
        assert "pausa longa de 10 minutos" in msg2.lower()
        assert tm._pomodoro["long_break_duration"] == 10 * 60

    def test_pomodoro_long_break_pause_and_resume(self, isolated_timer_manager):
        tm = isolated_timer_manager
        tm.pomodoro_control("long_break", long_break_minutes=15)
        assert tm._pomodoro["state"] == "long_break"

        msg_pause = tm.pomodoro_control("pause")
        assert "pausado" in msg_pause.lower()
        assert tm._pomodoro["state"] == "paused"
        assert tm._pomodoro["paused_from"] == "long_break"

        msg_resume = tm.pomodoro_control("resume")
        assert "retomado" in msg_resume.lower()
        assert "pausa longa" in msg_resume.lower()
        assert tm._pomodoro["state"] == "long_break"

    def test_pomodoro_long_break_finished_and_skip(self, isolated_timer_manager):
        tm = isolated_timer_manager
        tm._pomodoro["state"] = "long_break_finished"
        tm._pomodoro["cycle"] = 4
        msg = tm.pomodoro_control("status")
        assert "pausa longa" in msg.lower()
        assert "terminou" in msg.lower()

        # Avançar de long_break_finished deve iniciar o ciclo seguinte de foco
        msg_adv = tm.pomodoro_control("advance")
        assert "ciclo 5 de foco" in msg_adv
        assert tm._pomodoro["state"] == "work"
        assert tm._pomodoro["cycle"] == 5

        # Pular durante pausa longa
        tm.pomodoro_control("long_break", long_break_minutes=15)
        msg_skip = tm.pomodoro_control("skip")
        assert "ciclo 6 de foco" in msg_skip.lower()
        assert tm._pomodoro["state"] == "work"
        assert tm._pomodoro["cycle"] == 6

    def test_pomodoro_persistence_with_long_break(self, isolated_timer_manager):
        tm = isolated_timer_manager
        tm.pomodoro_control("start", work_minutes=25, break_minutes=5, long_break_minutes=25, long_break_interval=5)
        tm._save_state()

        # Carrega em novo manager simulando reinício
        with open(tm._state_file, "r") as f:
            data = json.load(f)
        assert data["pomodoro"]["long_break_duration"] == 25 * 60
        assert data["pomodoro"]["long_break_interval"] == 5

class TestTimerManagerWaybarAndPersistence:
    def test_export_status_for_waybar_structure(self, isolated_timer_manager):
        tm = isolated_timer_manager
        tm.add_timer(minutes=5, label="Chá")
        tm.add_alarm(hour=10, minute=0, label="Reunião")
        tm.stopwatch_control("start")
        tm.set_assistant_state("listening")

        assert os.path.exists(tm._status_file)
        with open(tm._status_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "text" in data
        assert "tooltip" in data
        assert "timers" in data
        assert "alarms" in data
        assert "stopwatch" in data
        assert "pomodoro" in data
        assert data["state"] == "listening"
        assert len(data["timers"]) == 1
        assert len(data["alarms"]) == 1
        assert data["stopwatch"]["running"] is True

    def test_process_waybar_commands(self, isolated_timer_manager):
        tm = isolated_timer_manager
        # Escreve um comando na fila
        cmd_file = os.path.join(tm._command_dir, "01_add_timer.json")
        with open(cmd_file, "w") as f:
            json.dump({
                "action": "timer_add",
                "minutes": 10,
                "label": "Massa"
            }, f)

        with patch("subprocess.run"):
            tm._process_waybar_commands()

        assert not os.path.exists(cmd_file)
        assert len(tm._timers) == 1
        tid = next(iter(tm._timers))
        assert tm._timers[tid]["label"] == "Massa"

    def test_process_waybar_alarm_toggle_and_remove(self, isolated_timer_manager):
        tm = isolated_timer_manager
        tm.add_alarm(hour=7, minute=0, label="Acordar")
        aid = next(iter(tm._alarms))

        # Toggle alarm
        cmd1 = os.path.join(tm._command_dir, "01_toggle.json")
        with open(cmd1, "w") as f:
            json.dump({"action": "alarm_toggle", "id": aid}, f)

        with patch("subprocess.run"):
            tm._process_waybar_commands()
        assert tm._alarms[aid]["enabled"] is False

        # Remove alarm
        cmd2 = os.path.join(tm._command_dir, "02_remove.json")
        with open(cmd2, "w") as f:
            json.dump({"action": "alarm_remove", "id": aid}, f)

        with patch("subprocess.run"):
            tm._process_waybar_commands()
        assert aid not in tm._alarms

    def test_save_and_load_state(self, isolated_timer_manager):
        tm = isolated_timer_manager
        tm.add_timer(minutes=10, label="Persistência")
        tm.add_alarm(hour=14, minute=0, label="Almoço")
        tm.pomodoro_control("start", work_minutes=25)

        # Salva
        tm._save_state()
        assert os.path.exists(tm._state_file)

        # Limpa memória e recarrega
        tm._timers = {}
        tm._alarms = {}
        tm._pomodoro = {}
        tm._load_state()

        assert len(tm._timers) == 1
        assert len(tm._alarms) == 1
        assert tm._pomodoro.get("state") == "work"

    def test_load_state_expired_pomodoro(self, isolated_timer_manager):
        tm = isolated_timer_manager
        tm.pomodoro_control("start", work_minutes=25)
        tm._save_state()

        # Simula tempo passado offline superior à duração
        with open(tm._state_file, "r") as f:
            data = json.load(f)
        data["timestamp"] = time.time() - 3600  # 1 hora atrás
        with open(tm._state_file, "w") as f:
            json.dump(data, f)

        tm._pomodoro = {}
        tm._load_state()

        assert tm._pomodoro.get("state") == "work_finished"
        assert tm._pomodoro.get("remaining") == 0
        assert tm._pomodoro.get("cycle") == 1

        # Verifica export para status
        with open(tm._status_file, "r") as f:
            status_data = json.load(f)
        pomo = status_data["pomodoro"]
        assert pomo["active"] is True
        assert pomo["state"] == "work_finished"
        assert pomo["left"] == 0
        assert pomo["cycle"] == 1

    def test_load_state_finished_pomodoro_preserves_cycle(self, isolated_timer_manager):
        tm = isolated_timer_manager
        tm._pomodoro = {
            "state": "work_finished",
            "cycle": 3,
            "work_duration": 1800,
            "break_duration": 300,
            "target": 0.0,
            "remaining": 0,
            "label": "Foco"
        }
        tm._save_state()

        tm._pomodoro = {}
        tm._load_state()

        assert tm._pomodoro.get("state") == "work_finished"
        assert tm._pomodoro.get("cycle") == 3
        assert tm._pomodoro.get("remaining") == 0

        with open(tm._status_file, "r") as f:
            status_data = json.load(f)
        pomo = status_data["pomodoro"]
        assert pomo["active"] is True
        assert pomo["state"] == "work_finished"
        assert pomo["cycle"] == 3
        assert pomo["left"] == 0


class TestTimerManagerDirectControls:
    def test_direct_id_pause_resume_and_cancel_timer(self, isolated_timer_manager):
        tm = isolated_timer_manager
        tm.add_timer(minutes=5, label="Chá")
        timers = tm.list_timers()
        assert len(timers) == 1
        timer_id = timers[0]["id"]

        # Pause by direct ID
        msg_pause = tm.pause_timer(timer_id)
        assert "pausado com sucesso" in msg_pause
        assert tm._timers[timer_id]["paused"] is True

        # Resume by direct ID
        msg_resume = tm.resume_timer(timer_id)
        assert "retomado" in msg_resume
        assert tm._timers[timer_id]["paused"] is False

        # Cancel by direct ID
        msg_cancel = tm.cancel_timer(timer_id)
        assert "cancelado" in msg_cancel
        assert len(tm._timers) == 0

    def test_cancel_all_timers(self, isolated_timer_manager):
        tm = isolated_timer_manager
        tm.add_timer(minutes=5, label="Timer 1")
        tm.add_timer(minutes=10, label="Timer 2")
        assert len(tm._timers) == 2

        msg = tm.cancel_timer("todos")
        assert "cancelado" in msg
        assert len(tm._timers) == 0

    def test_direct_id_and_all_cancel_alarm(self, isolated_timer_manager):
        tm = isolated_timer_manager
        tm.add_alarm(hour=8, minute=0, label="Acordar")
        alarms = tm.list_alarms()
        assert len(alarms) == 1
        alarm_id = alarms[0]["id"]

        # Cancel by direct ID
        msg_cancel = tm.cancel_alarm(alarm_id)
        assert "cancelado" in msg_cancel
        assert len(tm._alarms) == 0

        # Cancel all alarms
        tm.add_alarm(hour=9, minute=0, label="A1")
        tm.add_alarm(hour=10, minute=0, label="A2")
        assert len(tm._alarms) == 2
        msg_all = tm.cancel_alarm("todos")
        assert "cancelado" in msg_all
        assert len(tm._alarms) == 0

