import time
import threading
import subprocess
import json
import os
import difflib

class TimerManager:
    _timers = {}
    _alarms = {}
    _stopwatch = {"running": False, "start_time": 0.0, "elapsed": 0.0}
    _lock = threading.Lock()
    _running = False
    _assistant_state = "idle"
    _command_dir = "/tmp/geraldo_commands"
    _status_file = "/tmp/geraldo_status.json"
    _state_file = os.path.expanduser("~/.config/geraldo_state.json")
    _alarm_sound_path = os.path.expanduser("~/projects/geraldo/assets/alarm.wav")
    _timer_sound_path = os.path.expanduser("~/projects/geraldo/assets/timer.wav")
    _ringing_alarm = None
    _ringing_timer = None
    _alarm_stop_event = None
    _timer_stop_event = None

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
                    saved_timestamp = data.get("timestamp", now)
                    elapsed_offline = max(0, now - saved_timestamp)

                    valid_timers = {}
                    for tid, t_data in data.get("timers", {}).items():
                        if t_data.get("paused", False):
                            valid_timers[tid] = t_data
                        else:
                            remaining = t_data.get("remaining", 0) - elapsed_offline
                            if remaining > 0:
                                t_data["remaining"] = int(remaining)
                                t_data["target"] = now + remaining
                                valid_timers[tid] = t_data

                    cls._timers = valid_timers
                    cls._alarms = data.get("alarms", {})
                
                # EXPORTA IMEDIATAMENTE PARA A WAYBAR ASSIM QUE CARREGA
                cls._export_status_for_waybar()
                
                print(f"[Geraldo:Timer] Estado persistido carregado: {len(cls._timers)} timers válidos, {len(cls._alarms)} alarmes.")
            except Exception as e:
                print(f"[Geraldo:Timer Error] Falha ao carregar estado: {e}")
                
    @classmethod
    def _save_state(cls):
        try:
            os.makedirs(os.path.dirname(cls._state_file), exist_ok=True)
            saved_timers = {}
            now = time.time()
            for tid, t_data in cls._timers.items():
                if not t_data.get("paused", False):
                    remaining = max(0, int(t_data["target"] - now))
                else:
                    remaining = t_data.get("remaining", 0)
                
                saved_timers[tid] = {
                    "target": t_data.get("target", now + remaining),
                    "label": t_data["label"],
                    "paused": t_data.get("paused", False),
                    "remaining": remaining
                }

            data = {
                "timestamp": now,
                "timers": saved_timers,
                "alarms": cls._alarms
            }
            with open(cls._state_file, "w") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"[Geraldo:Timer Error] Falha ao salvar estado: {e}")


    @classmethod
    def set_assistant_state(cls, state: str) -> None:
        allowed = {
            "starting", "idle", "listening", "transcribing",
            "thinking", "searching", "speaking"
        }
        if state not in allowed:
            state = "idle"
        with cls._lock:
            cls._assistant_state = state
            cls._export_status_for_waybar()

    @classmethod
    def _process_waybar_commands(cls):
        try:
            os.makedirs(cls._command_dir, mode=0o700, exist_ok=True)
            names = sorted(
                n for n in os.listdir(cls._command_dir)
                if n.endswith(".json")
            )
        except Exception as exc:
            print(f"[Geraldo:Waybar] Falha ao ler fila: {exc}")
            return

        for name in names:
            path = os.path.join(cls._command_dir, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    cmd = json.load(f)
                os.unlink(path)
            except Exception as exc:
                print(f"[Geraldo:Waybar] Comando inválido: {exc}")
                try:
                    os.unlink(path)
                except OSError:
                    pass
                continue

            action = cmd.get("action", "")
            message = ""
            try:
                if action in ("dismiss_ringing_timer", "timer_silence"):
                    cls._stop_ringing_timer()
                    message = "Timer silenciado."

                elif action in ("dismiss_ringing_alarm", "alarm_silence"):
                    cls._stop_ringing_alarm()
                    message = "Alarme silenciado."

                elif action in ("dismiss_all_ringing", "silence_all"):
                    cls.stop_all_ringing()
                    message = "Sons silenciados."

                elif action == "timer_add":
                    message = cls.add_timer(
                        hours=int(cmd.get("hours", 0)),
                        minutes=int(cmd.get("minutes", 0)),
                        seconds=int(cmd.get("seconds", 0)),
                        label=str(cmd.get("label", "Timer"))[:60]
                    )

                elif action == "timer_pause_all":
                    message = cls.pause_timer("todos")

                elif action == "timer_resume_all":
                    message = cls.resume_timer("todos")

                elif action == "timer_clear_all":
                    with cls._lock:
                        count = len(cls._timers)
                        cls._timers.clear()
                        cls._save_state()
                        cls._export_status_for_waybar()
                    message = f"{count} timer(s) removido(s)."

                elif action == "timer_toggle":
                    with cls._lock:
                        item = cls._timers.get(str(cmd.get("id", "")))
                        if item is None:
                            message = "Esse timer já não existe."
                        elif item.get("paused", False):
                            item["target"] = time.time() + max(
                                0, item.get("remaining", 0)
                            )
                            item["paused"] = False
                            message = f"Timer {item['label']} retomado."
                            cls._save_state()
                            cls._export_status_for_waybar()
                        else:
                            item["remaining"] = max(
                                0, int(item["target"] - time.time())
                            )
                            item["paused"] = True
                            message = f"Timer {item['label']} pausado."
                            cls._save_state()
                            cls._export_status_for_waybar()

                elif action == "timer_remove":
                    with cls._lock:
                        item = cls._timers.pop(str(cmd.get("id", "")), None)
                        if item:
                            message = f"Timer {item['label']} cancelado."
                            cls._save_state()
                            cls._export_status_for_waybar()
                        else:
                            message = "Esse timer já não existe."

                elif action == "alarm_add":
                    message = cls.add_alarm(
                        int(cmd.get("hour", 0)),
                        int(cmd.get("minute", 0)),
                        str(cmd.get("label", "Alarme"))[:60]
                    )

                elif action == "alarm_toggle":
                    with cls._lock:
                        item = cls._alarms.get(str(cmd.get("id", "")))
                        if item is None:
                            message = "Esse alarme já não existe."
                        else:
                            item["enabled"] = not item.get("enabled", True)
                            state = "ativado" if item["enabled"] else "desativado"
                            message = f"Alarme {item['label']} {state}."
                            cls._save_state()
                            cls._export_status_for_waybar()

                elif action == "alarm_remove":
                    with cls._lock:
                        item = cls._alarms.pop(str(cmd.get("id", "")), None)
                        if item:
                            message = f"Alarme {item['label']} excluído."
                            cls._save_state()
                            cls._export_status_for_waybar()
                        else:
                            message = "Esse alarme já não existe."

                elif action == "alarm_clear_all":
                    with cls._lock:
                        count = len(cls._alarms)
                        cls._alarms.clear()
                        cls._save_state()
                        cls._export_status_for_waybar()
                    message = f"{count} alarme(s) removido(s)."

                elif action == "cancel_all":
                    message = cls.cancel_all()

                elif action == "stopwatch":
                    message = cls.stopwatch_control(str(cmd.get("value", "")))

                else:
                    message = "Operação desconhecida."

            except Exception as exc:
                message = f"Falha ao executar comando: {exc}"
                print(f"[Geraldo:Waybar] {message}")

            if message:
                try:
                    subprocess.run(
                        ["notify-send", "Geraldo", message],
                        check=False, timeout=3
                    )
                except Exception:
                    pass

    @classmethod
    def _loop(cls):
        os.makedirs(cls._command_dir, mode=0o700, exist_ok=True)
        while cls._running:
            cls._process_waybar_commands()
            now = time.time()
            changed = False

            # Verifica tempo limite de reprodução de alarme (60s) e timer (20s)
            if cls._ringing_alarm and (now - cls._ringing_alarm["start_time"]) >= cls._ringing_alarm["max_duration"]:
                cls._stop_ringing_alarm()

            if cls._ringing_timer and (now - cls._ringing_timer["start_time"]) >= cls._ringing_timer["max_duration"]:
                cls._stop_ringing_timer()

            with cls._lock:
                expired_timers = [
                    tid for tid, item in cls._timers.items()
                    if not item.get("paused", False)
                    and now >= item["target"]
                ]

                if expired_timers:
                    for tid in expired_timers:
                        label = cls._timers[tid]["label"]
                        del cls._timers[tid]
                        cls._start_ringing_timer(tid, label)
                    changed = True

                current_time = time.strftime("%H:%M")
                expired_alarms = [
                    aid for aid, item in cls._alarms.items()
                    if item.get("enabled", True)
                    and current_time == item["time_str"]
                ]

                if expired_alarms:
                    for aid in expired_alarms:
                        label = cls._alarms[aid]["label"]
                        time_str = cls._alarms[aid]["time_str"]
                        del cls._alarms[aid]
                        cls._start_ringing_alarm(aid, label, time_str)
                    changed = True

                if changed:
                    cls._save_state()

                cls._export_status_for_waybar()

            time.sleep(1)


    @classmethod
    def _export_status_for_waybar(cls):
        try:
            now = time.time()
            timers = []
            alarms = []

            for tid, item in cls._timers.items():
                paused = item.get("paused", False)
                if paused:
                    left = max(0, int(item.get("remaining", 0)))
                else:
                    left = max(0, int(item.get("target", now) - now))

                if left > 0 or paused:
                    timers.append({
                        "id": tid,
                        "label": str(item.get("label", "Timer")),
                        "left": left,
                        "paused": paused
                    })

            timers.sort(key=lambda item: (
                item["paused"], item["left"]
            ))

            for aid, item in cls._alarms.items():
                alarms.append({
                    "id": aid,
                    "label": str(item.get("label", "Alarme")),
                    "time": item.get("time_str", "--:--"),
                    "enabled": item.get("enabled", True)
                })

            alarms.sort(key=lambda item: (
                not item["enabled"], item["time"]
            ))

            stopwatch = cls._stopwatch.copy()
            if stopwatch.get("running", False):
                stopwatch["elapsed"] = max(
                    0, now - stopwatch.get("start_time", now)
                )
            else:
                stopwatch["elapsed"] = max(
                    0, stopwatch.get("elapsed", 0)
                )

            state = getattr(cls, "_assistant_state", "idle")
            labels = {
                "starting": "INICIANDO",
                "idle": "PRONTO",
                "listening": "OUVINDO",
                "transcribing": "TRANSCR.",
                "thinking": "PENSANDO",
                "searching": "PESQUISANDO",
                "speaking": "FALANDO"
            }
            compact = [labels.get(state, "PRONTO")]

            if timers:
                compact.append(f"⏱{len(timers)}")

            enabled_alarm_count = sum(
                1 for item in alarms if item["enabled"]
            )
            if enabled_alarm_count:
                compact.append(f"⏰{enabled_alarm_count}")

            if stopwatch.get("running", False):
                elapsed = int(stopwatch["elapsed"])
                compact.append(f"⏲{elapsed // 60}:{elapsed % 60:02d}")

            details = [
                f"Estado: {labels.get(state, state)}",
                f"Timers: {len(timers)} | Alarmes ativos: "
                f"{enabled_alarm_count} | Alarmes desativados: "
                f"{len(alarms) - enabled_alarm_count}"
            ]

            for item in timers:
                left = item["left"]
                duration = f"{left // 60}m{left % 60:02d}s"
                status = "pausado" if item["paused"] else duration
                details.append(f"⏱ {item['label']}: {status}")

            for item in alarms:
                status = "" if item["enabled"] else " (desativado)"
                details.append(
                    f"⏰ {item['label']}: {item['time']}{status}"
                )

            elapsed = int(stopwatch["elapsed"])
            sw_state = "rodando" if stopwatch.get("running") else "parado/pausado"
            details.append(
                f"Cronômetro: {sw_state} "
                f"({elapsed // 60}:{elapsed % 60:02d})"
            )

            classes = [state]
            if timers or alarms or stopwatch.get("running", False):
                classes.append("has-tasks")

            ringing_timer_data = None
            if cls._ringing_timer:
                rem = max(0, int(cls._ringing_timer["max_duration"] - (now - cls._ringing_timer["start_time"])))
                if rem > 0:
                    ringing_timer_data = {
                        "id": cls._ringing_timer["id"],
                        "label": cls._ringing_timer["label"],
                        "left": rem
                    }
                    classes.append("ringing-timer")

            ringing_alarm_data = None
            if cls._ringing_alarm:
                rem = max(0, int(cls._ringing_alarm["max_duration"] - (now - cls._ringing_alarm["start_time"])))
                if rem > 0:
                    ringing_alarm_data = {
                        "id": cls._ringing_alarm["id"],
                        "label": cls._ringing_alarm["label"],
                        "time": cls._ringing_alarm.get("time_str", "--:--"),
                        "left": rem
                    }
                    classes.append("ringing-alarm")

            data = {
                "text": " · ".join(compact),
                "tooltip": "\n".join(details),
                "class": classes,
                "state": state,
                "timers": timers,
                "alarms": alarms,
                "stopwatch": stopwatch,
                "ringing_timer": ringing_timer_data,
                "ringing_alarm": ringing_alarm_data
            }

            temp_path = cls._status_file + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            os.replace(temp_path, cls._status_file)

        except Exception as exc:
            print(f"[Geraldo:Timer Error] Falha ao exportar status: {exc}")

    @classmethod
    def _play_sound_loop(cls, sound_file: str, stop_event: threading.Event, max_duration: float):
        start = time.time()
        while not stop_event.is_set() and (time.time() - start) < max_duration:
            if not os.path.exists(sound_file):
                time.sleep(1)
                continue
            proc = subprocess.Popen(["paplay", sound_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            while proc.poll() is None:
                if stop_event.is_set() or (time.time() - start) >= max_duration:
                    proc.terminate()
                    try:
                        proc.wait(timeout=0.2)
                    except Exception:
                        proc.kill()
                    return
                time.sleep(0.05)

    @classmethod
    def _start_ringing_alarm(cls, aid: str, label: str, time_str: str):
        cls._stop_ringing_alarm()
        now = time.time()
        cls._ringing_alarm = {
            "id": aid,
            "label": label,
            "start_time": now,
            "max_duration": 60.0,
            "time_str": time_str
        }
        cls._alarm_stop_event = threading.Event()
        t = threading.Thread(
            target=cls._play_sound_loop,
            args=(cls._alarm_sound_path, cls._alarm_stop_event, 60.0),
            daemon=True
        )
        t.start()
        cls._export_status_for_waybar()
        try:
            subprocess.Popen([
                "notify-send", "-u", "critical", "-a", "Geraldo",
                "⏰ ALARME DISPARADO!",
                f"{label} ({time_str})\nClique na Waybar para silenciar."
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    @classmethod
    def _start_ringing_timer(cls, tid: str, label: str):
        cls._stop_ringing_timer()
        now = time.time()
        cls._ringing_timer = {
            "id": tid,
            "label": label,
            "start_time": now,
            "max_duration": 20.0
        }
        cls._timer_stop_event = threading.Event()
        t = threading.Thread(
            target=cls._play_sound_loop,
            args=(cls._timer_sound_path, cls._timer_stop_event, 20.0),
            daemon=True
        )
        t.start()
        cls._export_status_for_waybar()
        try:
            subprocess.Popen([
                "notify-send", "-u", "critical", "-a", "Geraldo",
                "⏱ TIMER FINALIZADO!",
                f"O timer '{label}' terminou!\nClique na Waybar para silenciar."
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    @classmethod
    def _stop_ringing_alarm(cls):
        if cls._alarm_stop_event:
            cls._alarm_stop_event.set()
        cls._ringing_alarm = None
        cls._export_status_for_waybar()

    @classmethod
    def _stop_ringing_timer(cls):
        if cls._timer_stop_event:
            cls._timer_stop_event.set()
        cls._ringing_timer = None
        cls._export_status_for_waybar()

    @classmethod
    def stop_all_ringing(cls):
        cls._stop_ringing_alarm()
        cls._stop_ringing_timer()

    @classmethod
    def _notify(cls, message: str):
        print(f"\n[Geraldo:Alerta] {message}")
        try:
            subprocess.Popen(["notify-send", "Geraldo", message], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
                if t.get("paused", False):
                    res.append(f"Timer {t['label']} está pausado")
                else:
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
            tid = f"timer_{time.time_ns()}"
            cls._timers[tid] = {"target": target, "label": label, "paused": False, "remaining": total_seconds}
            cls._save_state()
            cls._export_status_for_waybar()

        partes = []
        if hours > 0:
            partes.append(f"{hours} hora" if hours == 1 else f"{hours} horas")
        if minutes > 0:
            partes.append(f"{minutes} minuto" if minutes == 1 else f"{minutes} minutos")
        if seconds > 0:
            partes.append(f"{seconds} segundo" if seconds == 1 else f"{seconds} segundos")
        duracao_str = " e ".join(partes) if partes else f"{total_seconds} segundos"

        return f"Timer de {duracao_str} iniciado para {label}."

    @classmethod
    def _find_best_match(cls, query: str, items_dict: dict) -> str | None:
        if not items_dict:
            return None
        labels = {item_id: data["label"].lower() for item_id, data in items_dict.items()}
        query = query.lower().strip()
        
        # Busca por substring direta primeiro
        for item_id, label in labels.items():
            if query in label or label in query:
                return item_id
                
        # Se não achar por substring, usa similaridade fuzzy (difflib)
        best_match_id = None
        highest_ratio = 0.0
        for item_id, label in labels.items():
            ratio = difflib.SequenceMatcher(None, query, label).ratio()
            if ratio > highest_ratio and ratio > 0.35:
                highest_ratio = ratio
                best_match_id = item_id
                
        return best_match_id

    @classmethod
    def pause_timer(cls, query: str = "") -> str:
        with cls._lock:
            if not query or "todos" in query:
                paused_count = 0
                now = time.time()
                for tid, t in cls._timers.items():
                    if not t.get("paused", False):
                        t["remaining"] = max(0, int(t["target"] - now))
                        t["paused"] = True
                        paused_count += 1
                if paused_count > 0:
                    cls._save_state()
                    cls._export_status_for_waybar()
                    return "Todos os timers foram pausados."
                return "Nenhum timer ativo para pausar."

            best_id = cls._find_best_match(query, cls._timers)
            if best_id:
                t = cls._timers[best_id]
                if not t.get("paused", False):
                    t["remaining"] = max(0, int(t["target"] - time.time()))
                    t["paused"] = True
                    cls._save_state()
                    cls._export_status_for_waybar()
                    return f"Timer {t['label']} pausado com sucesso."
                return f"O timer {t['label']} já está pausado."
            return f"Não encontrei nenhum timer semelhante a {query}."

    @classmethod
    def resume_timer(cls, query: str = "") -> str:
        with cls._lock:
            if not query or "todos" in query:
                resumed_count = 0
                now = time.time()
                for tid, t in cls._timers.items():
                    if t.get("paused", False):
                        t["target"] = now + t.get("remaining", 60)
                        t["paused"] = False
                        resumed_count += 1
                if resumed_count > 0:
                    cls._save_state()
                    cls._export_status_for_waybar()
                    return "Todos os timers foram retomados."
                return "Nenhum timer pausado para retomar."

            best_id = cls._find_best_match(query, cls._timers)
            if best_id:
                t = cls._timers[best_id]
                if t.get("paused", False):
                    t["target"] = time.time() + t.get("remaining", 60)
                    t["paused"] = False
                    cls._save_state()
                    cls._export_status_for_waybar()
                    return f"Timer {t['label']} retomado."
                return f"O timer {t['label']} já está rodando."
            return f"Não encontrei nenhum timer pausado semelhante a {query}."

    @classmethod
    def add_alarm(cls, hour: int, minute: int, label: str = "Alarme") -> str:
        time_str = f"{hour:02d}:{minute:02d}"
        with cls._lock:
            aid = f"alarm_{time.time_ns()}"
            cls._alarms[aid] = {"time_str": time_str, "label": label, "enabled": True}
            cls._save_state()
            cls._export_status_for_waybar()
        return f"Alarme definido para às {hour} horas e {minute} minutos."

    @classmethod
    def cancel_item(cls, query: str = "") -> str:
        with cls._lock:
            q = query.lower().strip()

            # Se algo está tocando no momento, silencia imediatamente
            if cls._ringing_alarm or cls._ringing_timer:
                cls.stop_all_ringing()
                if "timer" in q:
                    return "Timer silenciado."
                if "alarme" in q:
                    return "Alarme silenciado."
                return "Som silenciado."

            # Cancelar todos os alarmes especificamente
            if "alarme" in q and ("todo" in q or "tudo" in q):
                count = len(cls._alarms)
                cls._alarms.clear()
                cls._save_state()
                cls._export_status_for_waybar()
                return f"{count} alarme(s) cancelado(s)." if count > 0 else "Você não tem nenhum alarme ativo para cancelar."

            # Cancelar todos os timers especificamente
            if "timer" in q and ("todo" in q or "tudo" in q):
                count = len(cls._timers)
                cls._timers.clear()
                cls._save_state()
                cls._export_status_for_waybar()
                return f"{count} timer(s) cancelado(s)." if count > 0 else "Você não tem nenhum timer ativo para cancelar."

            if not q or "tudo" in q or "todos" in q:
                cls._timers.clear()
                cls._alarms.clear()
                cls._save_state()
                cls._export_status_for_waybar()
                return "Todos os timers e alarmes foram cancelados."

            # Se pediu genericamente "o alarme" ou "alarme" e só tem 1 alarme cadastrado
            if q in ["alarme", "o alarme", "despertador"] and len(cls._alarms) == 1:
                aid = next(iter(cls._alarms.keys()))
                label = cls._alarms[aid]["label"]
                del cls._alarms[aid]
                cls._save_state()
                cls._export_status_for_waybar()
                return f"Alarme {label} cancelado."

            # Se pediu genericamente "o timer" ou "timer" e só tem 1 timer rodando
            if q in ["timer", "o timer"] and len(cls._timers) == 1:
                tid = next(iter(cls._timers.keys()))
                label = cls._timers[tid]["label"]
                del cls._timers[tid]
                cls._save_state()
                cls._export_status_for_waybar()
                return f"Timer {label} cancelado."

            # Tenta achar por similaridade nos timers ou alarmes
            best_timer = cls._find_best_match(q, cls._timers)
            if best_timer:
                label = cls._timers[best_timer]["label"]
                del cls._timers[best_timer]
                cls._save_state()
                cls._export_status_for_waybar()
                return f"Timer {label} cancelado."

            best_alarm = cls._find_best_match(q, cls._alarms)
            if best_alarm:
                label = cls._alarms[best_alarm]["label"]
                del cls._alarms[best_alarm]
                cls._save_state()
                cls._export_status_for_waybar()
                return f"Alarme {label} cancelado."

            return f"Não encontrei nenhum timer ou alarme correspondente a {query}."

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
