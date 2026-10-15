import time
import threading
import json
import os
import subprocess
import datetime
import uuid

TIMER_FILE = "/tmp/geraldo_timer.json"
STOPWATCH_FILE = "/tmp/geraldo_stopwatch.json"
ALARM_FILE = "/tmp/geraldo_alarm.json"
ALARM_SOUND = os.path.expanduser("~/projects/geraldo/assets/alarm.wav")

class TimerManager:
    _lock = threading.Lock()
    _timers = []       # [{"id": str, "label": str, "target_ts": float, "total_s": int}]
    _alarms = []       # [{"id": str, "label": str, "target_dt": datetime}]
    _stopwatch = {"running": False, "start_ts": None, "accumulated": 0.0}
    _ringing = False
    _started = False

    @classmethod
    def start_background_loop(cls):
        if not cls._started:
            cls._started = True
            t = threading.Thread(target=cls._loop, daemon=True)
            t.start()

    @classmethod
    def _loop(cls):
        while True:
            now = time.time()
            now_dt = datetime.datetime.now()
            trigger_labels = []

            with cls._lock:
                expired_timers = [t for t in cls._timers if t["target_ts"] <= now]
                for exp in expired_timers:
                    trigger_labels.append(f"Timer: {exp['label']}")
                cls._timers = [t for t in cls._timers if t["target_ts"] > now]

                expired_alarms = [a for a in cls._alarms if a["target_dt"] <= now_dt]
                for exp in expired_alarms:
                    trigger_labels.append(f"Alarme: {exp['label']}")
                cls._alarms = [a for a in cls._alarms if a["target_dt"] > now_dt]

            if trigger_labels:
                cls._trigger_alarm(trigger_labels)

            cls._dump_all_states()
            time.sleep(1)

    @classmethod
    def _trigger_alarm(cls, labels: list):
        cls._ringing = True
        msg = ", ".join(labels)
        subprocess.Popen(["notify-send", "-u", "critical", "-t", "10000", "⏰ GERALDO", f"Tempo esgotado!\n{msg}"])

        def ring_sound():
            for _ in range(7):
                if not cls._ringing:
                    break
                subprocess.run(["pw-play", ALARM_SOUND], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(0.4)
            cls._ringing = False

        threading.Thread(target=ring_sound, daemon=True).start()

    @classmethod
    def stop_ringing(cls):
        cls._ringing = False

    @classmethod
    def add_timer(cls, minutes=0, seconds=0, hours=0, label="Geral", *args, **kwargs) -> str:
        try:
            h = int(hours or 0)
            m = int(minutes or 0)
            s = int(seconds or 0)
        except (ValueError, TypeError):
            h, m, s = 0, 0, 0

        clean_label = str(label) if label and str(label).lower() != "none" else "Timer"
        total_s = int(h * 3600 + m * 60 + s)
        if total_s <= 0:
            return "Duração inválida para o timer."

        target_ts = time.time() + total_s
        tid = str(uuid.uuid4())[:8]
        with cls._lock:
            cls._timers.append({
                "id": tid,
                "label": clean_label,
                "target_ts": target_ts,
                "total_s": total_s
            })
        cls._dump_all_states()

        partes = []
        if h > 0: partes.append(f"{h} hora{'s' if h > 1 else ''}")
        if m > 0: partes.append(f"{m} minuto{'s' if m > 1 else ''}")
        if s > 0: partes.append(f"{s} segundo{'s' if s > 1 else ''}")
        duracao_str = " e ".join(partes) or f"{total_s} segundos"
        return f"Timer de {duracao_str} iniciado para {clean_label}."

    @classmethod
    def cancel_timer(cls):
        with cls._lock:
            cls._timers.clear()
            cls._ringing = False
        cls._dump_all_states()
        return "Timers cancelados."

    @classmethod
    def add_alarm(cls, hour, minute, label="Alarme", *args, **kwargs) -> str:
        try:
            h = int(hour)
            m = int(minute)
        except (ValueError, TypeError):
            return "Horário de alarme inválido."

        now = datetime.datetime.now()
        target = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if target <= now:
            target += datetime.timedelta(days=1)

        clean_label = str(label) if label and str(label).lower() != "none" else "Alarme"
        aid = str(uuid.uuid4())[:8]
        with cls._lock:
            cls._alarms.append({
                "id": aid,
                "label": clean_label,
                "target_dt": target
            })
        cls._dump_all_states()
        return f"Alarme definido para às {h:02d}:{m:02d}."

    @classmethod
    def cancel_alarm(cls):
        with cls._lock:
            cls._alarms.clear()
            cls._ringing = False
        cls._dump_all_states()
        return "Alarmes cancelados."

    @classmethod
    def stopwatch_control(cls, action="start", *args, **kwargs) -> str:
        act = str(action).lower().strip()
        with cls._lock:
            now = time.time()
            if act in ["start", "iniciar"]:
                if not cls._stopwatch["running"]:
                    cls._stopwatch["running"] = True
                    cls._stopwatch["start_ts"] = now
                    cls._dump_all_states()
                    return "Cronômetro iniciado."
                return "O cronômetro já está em andamento."

            elif act in ["pause", "pausar", "parar"]:
                if cls._stopwatch["running"] and cls._stopwatch["start_ts"]:
                    cls._stopwatch["accumulated"] += now - cls._stopwatch["start_ts"]
                    cls._stopwatch["running"] = False
                    cls._stopwatch["start_ts"] = None
                    cls._dump_all_states()
                    s = int(cls._stopwatch["accumulated"])
                    return f"Cronômetro pausado em {s // 60} minutos e {s % 60} segundos."
                return "O cronômetro não está rodando."

            elif act in ["reset", "zerar", "reiniciar"]:
                cls._stopwatch = {"running": False, "start_ts": None, "accumulated": 0.0}
                cls._dump_all_states()
                return "Cronômetro zerado."
        return "Ação de cronômetro não reconhecida."

    @classmethod
    def toggle_stopwatch(cls):
        with cls._lock:
            if cls._stopwatch["running"]:
                cls.stopwatch_control("pause")
            else:
                cls.stopwatch_control("start")

    @classmethod
    def cancel_all(cls, *args, **kwargs) -> str:
        with cls._lock:
            cls._timers.clear()
            cls._alarms.clear()
            cls._stopwatch = {"running": False, "start_ts": None, "accumulated": 0.0}
            cls._ringing = False
        cls._dump_all_states()
        return "Todos os timers, alarmes e cronômetros foram cancelados."

    @classmethod
    def _dump_all_states(cls):
        now = time.time()

        # 1. DUMP TIMER
        active_timers = sorted([t for t in cls._timers if t["target_ts"] > now], key=lambda x: x["target_ts"])
        if cls._ringing:
            timer_data = {"text": "󰂞 ALARME!", "class": "ringing", "tooltip": "Tempo esgotado! Clique para silenciar."}
        elif active_timers:
            menor = active_timers[0]
            r = max(0, int(menor["target_ts"] - now))
            m, s = divmod(r, 60)
            h, m = divmod(m, 60)
            fmt = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
            tooltips = [f"• {t['label']}: {int(t['target_ts'] - now)//60:02d}:{int(t['target_ts'] - now)%60:02d}" for t in active_timers]
            timer_data = {
                "text": f"󱎫 {fmt}",
                "class": "active",
                "tooltip": "Timers ativos:\n" + "\n".join(tooltips) + "\n\nClique: Cancelar timer"
            }
        else:
            timer_data = {"text": "", "class": "hidden", "tooltip": ""}

        # 2. DUMP STOPWATCH
        sw_sec = cls._stopwatch["accumulated"]
        if cls._stopwatch["running"] and cls._stopwatch["start_ts"]:
            sw_sec += (now - cls._stopwatch["start_ts"])
            sm, ss = divmod(int(sw_sec), 60)
            sh, sm = divmod(sm, 60)
            fmt = f"{sh:02d}:{sm:02d}:{ss:02d}" if sh > 0 else f"{sm:02d}:{ss:02d}"
            sw_data = {
                "text": f" {fmt}",
                "class": "running",
                "tooltip": f"Cronômetro em andamento: {fmt}\n\nClique esquerdo: Pausar\nClique direito: Zerar"
            }
        elif cls._stopwatch["accumulated"] > 0:
            sm, ss = divmod(int(sw_sec), 60)
            sh, sm = divmod(sm, 60)
            fmt = f"{sh:02d}:{sm:02d}:{ss:02d}" if sh > 0 else f"{sm:02d}:{ss:02d}"
            sw_data = {
                "text": f" {fmt}",
                "class": "paused",
                "tooltip": f"Cronômetro pausado: {fmt}\n\nClique esquerdo: Retomar\nClique direito: Zerar"
            }
        else:
            sw_data = {"text": "", "class": "hidden", "tooltip": ""}

        # 3. DUMP ALARM
        if cls._alarms:
            first_alarm = cls._alarms[0]
            fmt_a = first_alarm["target_dt"].strftime("%H:%M")
            tooltips = [f"• {a['label']}: às {a['target_dt'].strftime('%H:%M')}" for a in cls._alarms]
            alarm_data = {
                "text": f"󰀠 {fmt_a}",
                "class": "scheduled",
                "tooltip": "Alarmes agendados:\n" + "\n".join(tooltips) + "\n\nClique: Cancelar alarme"
            }
        else:
            alarm_data = {"text": "", "class": "hidden", "tooltip": ""}

        # Grava os 3 arquivos
        for path, payload in [(TIMER_FILE, timer_data), (STOPWATCH_FILE, sw_data), (ALARM_FILE, alarm_data)]:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False)
            except Exception:
                pass
