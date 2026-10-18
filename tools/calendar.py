import datetime
import os
import os.path
import re
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv(os.path.expanduser("~/projects/geraldo/.env"))

# Escopo com permissão de leitura e criação de eventos
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events"
]
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", os.path.expanduser("~/projects/geraldo/credentials.json"))
TOKEN_FILE = os.getenv("GOOGLE_TOKEN_FILE", os.path.expanduser("~/projects/geraldo/token.json"))
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

    @classmethod
    def get_service(cls):
        if cls._service:
            return cls._service

        creds = None
        if os.path.exists(TOKEN_FILE):
            try:
                creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            except Exception:
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None
            
            if not creds and os.path.exists(CREDENTIALS_FILE):
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                    creds = flow.run_local_server(port=0)
                    with open(TOKEN_FILE, "w") as token:
                        token.write(creds.to_json())
                except Exception as e:
                    print(f"[Geraldo:Calendar Auth Error]: {e}")
                    return None

        if creds:
            cls._service = build("calendar", "v3", credentials=creds)
            return cls._service
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
        service = cls.get_service()
        if not service:
            return "A agenda do Google ainda não está configurada ou autenticada."

        q_lower = (date_query or "hoje").lower().strip()
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
                    return "Você não tem próximos compromissos agendados."

                ev = events[0]
                summary = ev.get("summary", "Compromisso sem título")
                start = ev.get("start", {}).get("dateTime", ev.get("start", {}).get("date"))
                today = datetime.date.today()
                if "T" in start:
                    dt_part, tm_part = start.split("T")
                    ev_date = datetime.date.fromisoformat(dt_part)
                    dia_str = "hoje" if ev_date == today else ("amanhã" if ev_date == today + datetime.timedelta(days=1) else f"no dia {ev_date.strftime('%d/%m')}")
                    tempo_falado = format_speech_time(tm_part[:5])
                    return f"Seu próximo compromisso é {summary}, {dia_str} {tempo_falado}."
                else:
                    ev_date = datetime.date.fromisoformat(start)
                    dia_str = "hoje" if ev_date == today else ("amanhã" if ev_date == today + datetime.timedelta(days=1) else f"no dia {ev_date.strftime('%d/%m')}")
                    return f"Seu próximo compromisso é {summary}, {dia_str} o dia todo."

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
                    return f"Você não tem compromissos agendados {rotulo_dia}."

                agenda_items = []
                dias_nomes = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
                for ev in events:
                    summary = ev.get("summary", "Compromisso sem título")
                    start = ev.get("start", {}).get("dateTime", ev.get("start", {}).get("date"))
                    if "T" in start:
                        dt_part, tm_part = start.split("T")
                        ev_date = datetime.date.fromisoformat(dt_part)
                        dia_nome = dias_nomes[ev_date.weekday()]
                        tempo_falado = format_speech_time(tm_part[:5])
                        agenda_items.append(f"{dia_nome} {ev_date.day}/{ev_date.month:02d}, {tempo_falado}: {summary}")
                    else:
                        ev_date = datetime.date.fromisoformat(start)
                        dia_nome = dias_nomes[ev_date.weekday()]
                        agenda_items.append(f"{dia_nome} {ev_date.day}/{ev_date.month:02d}, o dia todo: {summary}")

                return f"Compromissos {rotulo_dia}: " + "; ".join(agenda_items) + "."

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
                    return f"Você não tem compromissos agendados {rotulo_dia}."

                agenda_items = []
                for ev in events:
                    summary = ev.get("summary", "Compromisso sem título")
                    start = ev.get("start", {}).get("dateTime", ev.get("start", {}).get("date"))
                    if "T" in start:
                        hh_mm = start.split("T")[1][:5]
                        tempo_falado = format_speech_time(hh_mm)
                        agenda_items.append(f"{tempo_falado}: {summary}")
                    else:
                        agenda_items.append(f"o dia todo: {summary}")

                return f"Compromissos {rotulo_dia}: " + "; ".join(agenda_items) + "."

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
            deleted_title = matched_event.get("summary", summary or "Compromisso")
            return f"Compromisso '{deleted_title}' {dia_str} cancelado com sucesso."

        except Exception as e:
            print(f"[Geraldo:Calendar Delete Error]: {e}")
            return "Ocorreu um erro ao tentar cancelar o compromisso na agenda."
