import datetime
import os
import os.path
import re
import time
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from core.paths import get_env_path, get_credentials_path, get_token_path

_env_file = get_env_path()
if _env_file:
    load_dotenv(str(_env_file))

# Escopo com permissão de leitura e criação de eventos
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events"
]
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", str(get_credentials_path()))
TOKEN_FILE = os.getenv("GOOGLE_TOKEN_FILE", str(get_token_path()))
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")

try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo("America/Sao_Paulo")
except Exception:
    LOCAL_TZ = datetime.timezone(datetime.timedelta(hours=-3))

MONTH_NAMES = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3,
    "abril": 4, "maio": 5, "junho": 6, "julho": 7,
    "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12
}

def format_speech_time(hh_mm: str) -> str:
    try:
        parts = hh_mm.split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0

        horas_nome = {
            0: "meia-noite", 1: "uma", 2: "duas", 3: "três", 4: "quatro",
            5: "cinco", 6: "seis", 7: "sete", 8: "oito", 9: "nove",
            10: "dez", 11: "onze", 12: "meio-dia",
            13: "uma da tarde", 14: "duas da tarde", 15: "três da tarde",
            16: "quatro da tarde", 17: "cinco da tarde", 18: "seis da tarde",
            19: "sete da noite", 20: "oito da noite", 21: "nove da noite",
            22: "dez da noite", 23: "onze da noite"
        }

        if h == 0:
            return "à meia-noite" if m == 0 else f"à meia-noite e {'meia' if m == 30 else m}"
        if h == 12:
            return "ao meio-dia" if m == 0 else f"ao meio-dia e {'meia' if m == 30 else m}"

        if m == 0:
            artigo = "à " if h in [1, 13] else "às "
            return f"{artigo}{horas_nome[h]}"
        elif m == 30:
            h_base = h if h <= 12 else (h - 12)
            sufixo = " da tarde" if 12 < h < 18 else (" da noite" if h >= 18 else " da manhã")
            artigo = "à " if h_base in [1, 13] else "às "
            return f"{artigo}{horas_nome[h_base]} e meia{sufixo}"
        else:
            h_base = h if h <= 12 else (h - 12)
            sufixo = " da tarde" if 12 < h < 18 else (" da noite" if h >= 18 else " da manhã")
            artigo = "à " if h_base in [1, 13] else "às "
            return f"{artigo}{horas_nome[h_base]} e {m}{sufixo}"
    except Exception:
        return f"às {hh_mm}"

class CalendarTools:
    _service = None
    _calendar_cache = {}
    _CALENDAR_CACHE_TTL = 300  # 5 minutos
    _poller_started = False

    @classmethod
    def clear_calendar_cache(cls):
        cls._calendar_cache.clear()

    @classmethod
    def refresh_cache(cls, async_run: bool = True):
        def _do_refresh():
            service = cls.get_service()
            if not service:
                return
            for query in ["hoje", "amanhã", "próximo", "semana"]:
                try:
                    cls.get_events(query, use_cache=False)
                except Exception as e:
                    print(f"[Geraldo:Calendar Cache Refresh Error for '{query}']: {e}")
            print("[Geraldo:Calendar] Cache de agenda renovado em background.")

        if async_run:
            import threading
            threading.Thread(target=_do_refresh, daemon=True, name="cal_cache_refresh").start()
        else:
            _do_refresh()

    @classmethod
    def start_calendar_poller(cls, interval_seconds: int = 300):
        """
        Polling periódico a cada 5 minutos em background (12 req/h, ~288/dia).
        A cota do Google Calendar é de 1.000.000 req/dia, portanto consome menos de 0.03% da cota.
        """
        if cls._poller_started:
            return
        cls._poller_started = True

        import threading
        import time as _t

        def _poller():
            _t.sleep(2)
            cls.refresh_cache(async_run=False)

            while True:
                _t.sleep(interval_seconds)
                try:
                    cls.refresh_cache(async_run=False)
                except Exception as e:
                    print(f"[Geraldo:Calendar Poller Error]: {e}")

        threading.Thread(target=_poller, daemon=True, name="cal_cache_poller").start()

    @classmethod
    def get_service(cls):
        if cls._service:
            return cls._service

        creds = cls.get_credentials()
        if creds:
            try:
                cls._service = build("calendar", "v3", credentials=creds)
                return cls._service
            except Exception as e:
                print(f"[Geraldo:Calendar Build Error]: {e}")
                return None
        return None

    @classmethod
    def get_credentials(cls) -> Optional[Credentials]:
        """Obtém credenciais válidas do Google, renovando o token se expirado."""
        creds = None
        if os.path.exists(TOKEN_FILE):
            try:
                creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            except Exception:
                creds = None

        if creds and creds.valid:
            return creds

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(TOKEN_FILE, "w", encoding="utf-8") as token:
                    token.write(creds.to_json())
                return creds
            except Exception as e:
                print(f"[Geraldo:Calendar Refresh Error]: {e}")
                try:
                    if os.path.exists(TOKEN_FILE):
                        os.remove(TOKEN_FILE)
                except Exception:
                    pass
                creds = None

        return None

    @classmethod
    def authenticate(cls) -> Optional[Credentials]:
        """
        Executa o fluxo de autenticação OAuth 2.0 no navegador (1 clique).
        Suporta tanto o GOOGLE_CLIENT_ID embutido/configurado quanto o credentials.json tradicional.
        """
        import config

        flow = None

        # 1. Se existir o arquivo credentials.json físico, respeita-o
        if os.path.exists(CREDENTIALS_FILE):
            try:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            except Exception as e:
                print(f"[Geraldo:Calendar] Erro ao ler credentials.json: {e}")

        # 2. Se não houver arquivo, usa o Client ID configurado (fluxo de 1 clique sem arquivos)
        if not flow:
            client_id = getattr(config, "GOOGLE_CLIENT_ID", "").strip() or os.getenv("GOOGLE_CLIENT_ID", "").strip()
            client_secret = getattr(config, "GOOGLE_CLIENT_SECRET", "").strip() or os.getenv("GOOGLE_CLIENT_SECRET", "").strip()

            if client_id:
                client_config = {
                    "installed": {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                        "redirect_uris": ["http://localhost", "http://127.0.0.1"]
                    }
                }
                try:
                    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
                except Exception as e:
                    print(f"[Geraldo:Calendar] Erro ao instanciar flow OAuth: {e}")

        if not flow:
            return None

        try:
            creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
            if creds:
                os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
                with open(TOKEN_FILE, "w", encoding="utf-8") as token:
                    token.write(creds.to_json())
                cls._service = build("calendar", "v3", credentials=creds)
                return creds
        except Exception as e:
            print(f"[Geraldo:Calendar Auth Error]: {e}")
            return None

        return None

    @classmethod
    def _parse_target_date(cls, date_str: str) -> datetime.date:
        today = datetime.date.today()
        d_lower = (date_str or "hoje").lower().strip()

        if "depois de amanhã" in d_lower or "depois de amanha" in d_lower:
            return today + datetime.timedelta(days=2)

        if any(w in d_lower for w in ["amanhã", "amanha", "pra manhã", "para manhã", "pra manha", "para manha"]):
            return today + datetime.timedelta(days=1)

        if "hoje" in d_lower:
            return today

        # Mês por extenso (ex: "25 de dezembro", "dia 15 de novembro", "5 de maio de 2027")
        months_pat = "|".join(MONTH_NAMES.keys())
        m_extenso = re.search(r'\b(?:dia\s+)?(\d{1,2})\s+(?:de\s+)?(' + months_pat + r')(?:\s+(?:de\s+)?(\d{4}))?\b', d_lower)
        if m_extenso:
            dia_num = int(m_extenso.group(1))
            mes_num = MONTH_NAMES[m_extenso.group(2)]
            ano_num = int(m_extenso.group(3)) if m_extenso.group(3) else today.year
            try:
                cand = datetime.date(ano_num, mes_num, dia_num)
                if not m_extenso.group(3) and cand < today:
                    cand = datetime.date(today.year + 1, mes_num, dia_num)
                return cand
            except ValueError:
                pass

        # Dias da semana
        dias_semana = {
            "segunda": 0, "terça": 1, "terca": 1,
            "quarta": 2, "quinta": 3, "sexta": 4,
            "sábado": 5, "sabado": 5, "domingo": 6
        }
        for dia_nome, weekday_idx in dias_semana.items():
            if dia_nome in d_lower:
                dias_a_frente = (weekday_idx - today.weekday()) % 7
                if dias_a_frente == 0:
                    dias_a_frente = 7
                return today + datetime.timedelta(days=dias_a_frente)

        match_data = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', d_lower)
        if match_data:
            y, m, d = map(int, match_data.groups())
            try:
                return datetime.date(y, m, d)
            except ValueError:
                pass

        match_dia = re.search(r'dia\s+(\d{1,2})', d_lower)
        if match_dia:
            dia_num = int(match_dia.group(1))
            try:
                cand = datetime.date(today.year, today.month, dia_num)
                if cand < today:
                    next_year = today.year + (1 if today.month == 12 else 0)
                    next_month = 1 if today.month == 12 else today.month + 1
                    cand = datetime.date(next_year, next_month, dia_num)
                return cand
            except ValueError:
                pass

        return today

    @classmethod
    def get_events(cls, date_query: str = "hoje", *args, **kwargs) -> str:
        q_lower = (date_query or "hoje").lower().strip()
        use_cache = kwargs.get("use_cache", True)

        if use_cache and q_lower in cls._calendar_cache:
            cached_time, cached_result = cls._calendar_cache[q_lower]
            if time.time() - cached_time < cls._CALENDAR_CACHE_TTL:
                print(f"[Geraldo:Calendar] Cache atingido para '{q_lower}'.")
                return cached_result

        service = cls.get_service()
        if not service:
            return "A agenda do Google ainda não está configurada ou autenticada."

        is_next = any(w in q_lower for w in ["próximo", "proximo", "em breve"])
        is_week = "semana" in q_lower

        try:
            if is_next:
                now_local = datetime.datetime.now(tz=LOCAL_TZ)
                now_utc = now_local.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
                events_result = service.events().list(
                    calendarId=CALENDAR_ID,
                    timeMin=now_utc,
                    maxResults=1,
                    singleEvents=True,
                    orderBy="startTime"
                ).execute()

                events = events_result.get("items", [])
                if not events:
                    result = "Você não tem próximos compromissos agendados."
                else:
                    ev = events[0]
                    summary = ev.get("summary", "Compromisso sem título")
                    start = (ev.get("start") or {}).get("dateTime") or (ev.get("start") or {}).get("date") or ""
                    today = datetime.date.today()
                    if "T" in start:
                        dt_part, tm_part = start.split("T")
                        ev_date = datetime.date.fromisoformat(dt_part)
                        dia_str = "hoje" if ev_date == today else ("amanhã" if ev_date == today + datetime.timedelta(days=1) else f"no dia {ev_date.strftime('%d/%m')}")
                        tempo_falado = format_speech_time(tm_part[:5])
                        result = f"Seu próximo compromisso é {summary}, {dia_str} {tempo_falado}."
                    elif start:
                        ev_date = datetime.date.fromisoformat(start)
                        dia_str = "hoje" if ev_date == today else ("amanhã" if ev_date == today + datetime.timedelta(days=1) else f"no dia {ev_date.strftime('%d/%m')}")
                        result = f"Seu próximo compromisso é {summary}, {dia_str} o dia todo."
                    else:
                        result = f"Seu próximo compromisso é {summary}."

            elif is_week:
                today = datetime.date.today()
                start_dt = datetime.datetime.combine(today, datetime.time.min, tzinfo=LOCAL_TZ)
                end_dt = datetime.datetime.combine(today + datetime.timedelta(days=7), datetime.time.max, tzinfo=LOCAL_TZ)
                start_of_day = start_dt.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
                end_of_day = end_dt.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
                rotulo_dia = "nesta semana"

                events_result = service.events().list(
                    calendarId=CALENDAR_ID,
                    timeMin=start_of_day,
                    timeMax=end_of_day,
                    singleEvents=True,
                    orderBy="startTime"
                ).execute()

                events = events_result.get("items", [])
                if not events:
                    result = f"Você não tem compromissos agendados {rotulo_dia}."
                else:
                    agenda_items = []
                    dias_nomes = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
                    for ev in events:
                        summary = ev.get("summary", "Compromisso sem título")
                        start = (ev.get("start") or {}).get("dateTime") or (ev.get("start") or {}).get("date") or ""
                        if "T" in start:
                            dt_part, tm_part = start.split("T")
                            ev_date = datetime.date.fromisoformat(dt_part)
                            dia_nome = dias_nomes[ev_date.weekday()]
                            tempo_falado = format_speech_time(tm_part[:5])
                            agenda_items.append(f"{dia_nome} {ev_date.day}/{ev_date.month:02d}, {tempo_falado}: {summary}")
                        elif start:
                            ev_date = datetime.date.fromisoformat(start)
                            dia_nome = dias_nomes[ev_date.weekday()]
                            agenda_items.append(f"{dia_nome} {ev_date.day}/{ev_date.month:02d}, o dia todo: {summary}")
                        else:
                            agenda_items.append(f"{summary}")

                    result = f"Compromissos {rotulo_dia}: " + "; ".join(agenda_items) + "."

            else:
                target_date = cls._parse_target_date(date_query)
                start_dt = datetime.datetime.combine(target_date, datetime.time.min, tzinfo=LOCAL_TZ)
                end_dt = datetime.datetime.combine(target_date, datetime.time.max, tzinfo=LOCAL_TZ)
                start_of_day = start_dt.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
                end_of_day = end_dt.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

                if target_date == datetime.date.today():
                    rotulo_dia = "hoje"
                elif target_date == datetime.date.today() + datetime.timedelta(days=1):
                    rotulo_dia = "amanhã"
                elif target_date == datetime.date.today() + datetime.timedelta(days=2):
                    rotulo_dia = "depois de amanhã"
                else:
                    rotulo_dia = f"para o dia {target_date.strftime('%d/%m')}"

                events_result = service.events().list(
                    calendarId=CALENDAR_ID,
                    timeMin=start_of_day,
                    timeMax=end_of_day,
                    singleEvents=True,
                    orderBy="startTime"
                ).execute()

                events = events_result.get("items", [])
                if not events:
                    result = f"Você não tem compromissos agendados {rotulo_dia}."
                else:
                    agenda_items = []
                    for ev in events:
                        summary = ev.get("summary", "Compromisso sem título")
                        start = (ev.get("start") or {}).get("dateTime") or (ev.get("start") or {}).get("date") or ""
                        if "T" in start:
                            hh_mm = start.split("T")[1][:5]
                            tempo_falado = format_speech_time(hh_mm)
                            agenda_items.append(f"{tempo_falado}: {summary}")
                        elif start:
                            agenda_items.append(f"o dia todo: {summary}")
                        else:
                            agenda_items.append(f"{summary}")

                    result = f"Compromissos {rotulo_dia}: " + "; ".join(agenda_items) + "."

            cls._calendar_cache[q_lower] = (time.time(), result)
            return result

        except Exception as e:
            print(f"[Geraldo:Calendar Error]: {e}")
            return "Não foi possível carregar os compromissos da agenda no momento."

    @classmethod
    def create_event(cls, summary: str, date_query: str = "hoje", time_str: str = "09:00", duration_minutes: int = 60, all_day: bool = False, *args, **kwargs) -> str:
        """Cria um novo evento no Google Calendar."""
        service = cls.get_service()
        if not service:
            return "A agenda do Google não está autenticada para escrita."

        target_date = cls._parse_target_date(date_query)

        dia_str = "hoje" if target_date == datetime.date.today() else ("amanhã" if target_date == datetime.date.today() + datetime.timedelta(days=1) else f"dia {target_date.strftime('%d/%m')}")

        if all_day:
            event_body = {
                'summary': summary,
                'start': {
                    'date': target_date.isoformat(),
                },
                'end': {
                    'date': (target_date + datetime.timedelta(days=1)).isoformat(),
                },
            }
        else:
            match_time = re.search(r'(\d{1,2}):?(\d{2})?', time_str)
            if match_time:
                hour = int(match_time.group(1))
                minute = int(match_time.group(2)) if match_time.group(2) else 0
            else:
                hour, minute = 9, 0

            start_dt = datetime.datetime.combine(target_date, datetime.time(hour, minute), tzinfo=LOCAL_TZ)
            end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)

            event_body = {
                'summary': summary,
                'start': {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': 'America/Sao_Paulo',
                },
                'end': {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': 'America/Sao_Paulo',
                },
            }

        try:
            created = service.events().insert(calendarId=CALENDAR_ID, body=event_body).execute()
            cls.clear_calendar_cache()
            cls.refresh_cache(async_run=True)
            if all_day:
                return f"Agendado com sucesso: {summary} {dia_str} o dia inteiro."
            hora_extenso = format_speech_time(f"{hour:02d}:{minute:02d}")
            return f"Agendado com sucesso: {summary} {dia_str} {hora_extenso}."
        except Exception as e:
            print(f"[Geraldo:Calendar Create Error]: {e}")
            return "Ocorreu um erro ao tentar criar o evento na agenda."

    @classmethod
    def delete_event(cls, summary: str = "", date_query: str = "hoje", *args, **kwargs) -> str:
        """Exclui um evento da agenda pelo título aproximado e data."""
        service = cls.get_service()
        if not service:
            return "A agenda do Google não está autenticada para escrita."

        target_date = cls._parse_target_date(date_query)
        dia_str = "hoje" if target_date == datetime.date.today() else ("amanhã" if target_date == datetime.date.today() + datetime.timedelta(days=1) else f"dia {target_date.strftime('%d/%m')}")

        start_dt = datetime.datetime.combine(target_date, datetime.time.min, tzinfo=LOCAL_TZ)
        end_dt = datetime.datetime.combine(target_date, datetime.time.max, tzinfo=LOCAL_TZ)
        start_of_day = start_dt.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        end_of_day = end_dt.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

        try:
            events_result = service.events().list(
                calendarId=CALENDAR_ID,
                timeMin=start_of_day,
                timeMax=end_of_day,
                singleEvents=True
            ).execute()

            events = events_result.get("items", [])
            if not events:
                return f"Você não tem compromissos agendados {dia_str} para cancelar."

            target_summary = summary.lower().strip() if summary else ""
            matched_event = None

            if target_summary:
                for ev in events:
                    ev_title = ev.get("summary", "").lower().strip()
                    if target_summary in ev_title or ev_title in target_summary:
                        matched_event = ev
                        break
                if not matched_event:
                    return f"Não encontrei o compromisso '{summary}' {dia_str}."
            else:
                if len(events) == 1:
                    matched_event = events[0]
                else:
                    titles = [ev.get("summary", "Sem título") for ev in events]
                    return f"Você tem mais de um compromisso {dia_str}: {', '.join(titles)}. Qual você deseja cancelar?"

            service.events().delete(calendarId=CALENDAR_ID, eventId=matched_event["id"]).execute()
            cls.clear_calendar_cache()
            cls.refresh_cache(async_run=True)
            deleted_title = matched_event.get("summary", summary or "Compromisso")
            return f"Compromisso '{deleted_title}' {dia_str} cancelado com sucesso."

        except Exception as e:
            print(f"[Geraldo:Calendar Delete Error]: {e}")
            return "Ocorreu um erro ao tentar cancelar o compromisso na agenda."
