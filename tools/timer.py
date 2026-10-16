import time
import threading
import subprocess
import json
import os

class TimerManager:
    _timers = {}
    _alarms = {}
    _stopwatch = {"running": False, "start_time": 0.0, "elapsed": 0.0}
    _lock = threading.Lock()
    _running = False
    _status_file = "/tmp/geraldo_status.json"
    _state_file = os.path.expanduser("~/.config/geraldo_state.json")

    @classmethod
    def start_background_loop(cls):
        if cls._running:
            return
        cls._load_state()
        cls._running = True
        t = threading.Thread(target=cls._loop, daemon=True)
        t.start()

    @classmethod
    def _load_state(cls):
        if os.path.exists(cls._state_file):
            try:
                with open(cls._state_file, "r") as f:
                    data = json.load(f)
                    now = time.time()
                    # Restaura timers apenas se ainda não expiraram
                    for tid, t_data in data.get("timers", {}).items():
                        if t_data["target"] > now:
                            cls._timers[tid] = t_data
                    # Restaura alarmes
                    cls._alarms = data.get("alarms", {})
                print(f"[Geraldo:Timer] Estado persistido carregado: {len(cls._timers)} timers, {len(cls._alarms)} alarmes.")
            except Exception as e:
                print(f"[Geraldo:Timer Error] Falha ao carregar estado: {e}")

    @classmethod
    def _save_state(cls):
        try:
            os.makedirs(os.path.dirname(cls._state_file), exist_ok=True)
            data = {
                "timers": cls._timers,
                "alarms": cls._alarms
            }
            with open(cls._state_file, "w") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"[Geraldo:Timer Error] Falha ao salvar estado: {e}")

    @classmethod
    def _loop(cls):
        while cls._running:
            now = time.time()
            with cls._lock:
                expired_timers = []
                for tid, t_data in cls._timers.items():
                    if now >= t_data["target"]:
                        expired_timers.append(tid)
                
                if expired_timers:
                    for tid in expired_timers:
                        label = cls._timers[tid]["label"]
                        cls._notify(f"Timer encerrado: {label}")
                        del cls._timers[tid]
                    cls._save_state()

                current_time = time.strftime("%H:%M")
                expired_alarms = []
                for aid, a_data in cls._alarms.items():
                    if current_time == a_data["time_str"]:
                        expired_alarms.append(aid)
                
                if expired_alarms:
                    for aid in expired_alarms:
                        label = cls._alarms[aid]["label"]
                        cls._notify(f"Alarme disparado: {label}")
                        del cls._alarms[aid]
                    cls._save_state()

                cls._export_status_for_waybar()

            time.sleep(1)

    @classmethod
    def _export_status_for_waybar(cls):
        try:
            now = time.time()
            display_texts = []
            active_timers_list = []

            for tid, t in cls._timers.items():
                left = int(t["target"] - now)
                if left > 0:
                    mins = left // 60
                    secs = left % 60
                    display_texts.append(f"⏱️ {t['label']} ({mins}m{secs}s)")
                    active_timers_list.append({"id": tid, "label": t["label"], "left": left})

            active_alarms_list = []
            for aid, a in cls._alarms.items():
                display_texts.append(f"⏰ {a['label']} ({a['time_str']})")
                active_alarms_list.append({"id": aid, "label": a['label'], "time": a['time_str']})

            data = {
                "text": " | ".join(display_texts) if display_texts else "",
                "tooltip": f"Timers: {len(cls._timers)} | Alarmes: {len(cls._alarms)}",
                "class": "active" if display_texts else "none",
                "timers": active_timers_list,
                "alarms": active_alarms_list
            }
            with open(cls._status_file, "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    @classmethod
    def _notify(cls, message: str):
        print(f"\n[Geraldo:Alerta] {message}")
        try:
            subprocess.run(["notify-send", "Geraldo", message], check=False)
            subprocess.run(["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"], check=False)
        except Exception:
            pass

    @classmethod
    def get_active_summary(cls) -> str:
        with cls._lock:
            now = time.time()
            if not cls._timers and not cls._alarms:
                return "Você não tem nenhum timer ou alarme ativo neste momento."
            
            res = []
            for tid, t in cls._timers.items():
                left = int(t["target"] - now)
                if left > 0:
                    res.append(f"Timer de {left // 60} minutos e {left % 60} segundos para {t['label']}")
            for aid, a in cls._alarms.items():
                res.append(f"Alarme programado para as {a['time_str']} com o rótulo {a['label']}")
            
            return ". ".join(res)

    @classmethod
    def add_timer(cls, hours: int = 0, minutes: int = 0, seconds: int = 0, label: str = "Timer") -> str:
        total_seconds = (hours * 3600) + (minutes * 60) + seconds
        if total_seconds <= 0:
            return "Defina um tempo válido para o timer."
        
        target = time.time() + total_seconds
        with cls._lock:
            tid = f"timer_{int(time.time())}"
            cls._timers[tid] = {"target": target, "label": label}
            cls._save_state()
            cls._export_status_for_waybar()

        return f"Timer de {minutes} minutos iniciado para {label}."

    @classmethod
    def add_alarm(cls, hour: int, minute: int, label: str = "Alarme") -> str:
        time_str = f"{hour:02d}:{minute:02d}"
        with cls._lock:
            aid = f"alarm_{int(time.time())}"
            cls._alarms[aid] = {"time_str": time_str, "label": label}
            cls._save_state()
            cls._export_status_for_waybar()
        return f"Alarme definido para às {hour} horas e {minute} minutos."

    @classmethod
    def cancel_item(cls, query: str = "") -> str:
        with cls._lock:
            q = query.lower().strip()
            if not q or "tudo" in q or "todos" in q:
                count = len(cls._timers) + len(cls._alarms)
                cls._timers.clear()
                cls._alarms.clear()
                cls._save_state()
                cls._export_status_for_waybar()
                return "Todos os timers e alarmes foram cancelados."
            
            canceled = 0
            for tid in list(cls._timers.keys()):
                if q in cls._timers[tid]["label"].lower():
                    del cls._timers[tid]
                    canceled += 1
            for aid in list(cls._alarms.keys()):
                if q in cls._alarms[aid]["label"].lower():
                    del cls._alarms[aid]
                    canceled += 1
            
            cls._save_state()
            cls._export_status_for_waybar()
            if canceled > 0:
                return f"Cancelados {canceled} itens correspondentes a {query}."
            return f"Não encontrei nenhum timer ou alarme chamado {query}."

    @classmethod
    def cancel_all(cls) -> str:
        return cls.cancel_item("todos")

    @classmethod
    def stopwatch_control(cls, action: str) -> str:
        with cls._lock:
            if action == "start":
                if not cls._stopwatch["running"]:
                    cls._stopwatch["running"] = True
                    cls._stopwatch["start_time"] = time.time() - cls._stopwatch["elapsed"]
                    cls._export_status_for_waybar()
                    return "Cronômetro iniciado."
                return "O cronômetro já está rodando."
            elif action == "pause":
                if cls._stopwatch["running"]:
                    cls._stopwatch["elapsed"] = time.time() - cls._stopwatch["start_time"]
                    cls._stopwatch["running"] = False
                    cls._export_status_for_waybar()
                    return "Cronômetro pausado."
                return "O cronômetro não está ativo."
            elif action == "reset":
                cls._stopwatch["running"] = False
                cls._stopwatch["elapsed"] = 0.0
                cls._export_status_for_waybar()
                return "Cronômetro zerado."
        return "Ação inválida."
