import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion

TRAINING_DATA = {
    "get_time": [
        "que horas são", "que horas são agora", "qual é a hora", "me diga as horas", "hora certa"
    ],
    "greeting_morning": [
        "bom dia", "bom dia geraldo", "muito bom dia"
    ],
    "thanks": [
        "obrigado", "muito obrigado", "valeu", "valeu geraldo", "obrigada"
    ],
    "get_weather": [
        "como está o clima", "qual a previsão do tempo", "vai chover hoje", "vai chover amanhã"
    ],
    "get_calendar": [
        "o que eu tenho agendado para hoje", "como está minha agenda hoje", "quais são meus compromissos de amanhã"
    ],
    "create_calendar": [
        "marque um evento na minha agenda", "agende uma reunião para amanhã", "crie um compromisso hoje às 15 horas"
    ],
    "set_alarm": [
        "defina um alarme para as 10 da noite", "coloque um despertador para as 7 da manhã", "me acorde às 6 e meia"
    ],
    "set_timer": [
        "defina um timer de 5 minutos", "coloque um cronômetro regressivo de 10 minutos", "timer de 15 segundos para a pausa"
    ],
    "list_timers": [
        "tem algum timer ativo agora", "quais timers estão rodando", "ver timers ativos", "tenho algum alarme ligado"
    ],
    "cancel_timers": [
        "cancele todos os timers", "cancelar alarme", "pare o timer", "cancele o timer chamado teste", "cancele o alarme", "cancele todos",
        "desative todos os alarmes", "desative o alarme", "desative todos", "desativar alarme", "desativem todos os alarmes",
        "desligue o alarme", "desligue todos os alarmes", "apague os alarmes", "cancele todos os alarmes", "parar alarme",
        "todos os alarmes", "remover todos os alarmes", "excluir alarme", "desativar todos os timers",
        "silenciar alarme", "silencie o alarme", "silencie o timer", "pare o alarme", "silêncio", "silencio", "pare de tocar"
    ],
    "pause_timer": [
        "pause o timer", "pausar o timer", "congele o timer", "pause o timer descanso"
    ],
    "resume_timer": [
        "retome o timer", "despause o timer", "continue o timer", "resumir o timer", "retomar timer"
    ],
    "control_stopwatch": [
        "inicie o cronômetro", "pausar cronômetro", "zerar cronômetro", "parar cronômetro"
    ],
    "play_music": [
        "toque uma música", "reproduza coldplay", "coloque bob marley", "toca reggae",
        "toque a música love is a losing game da amy winehouse", "ouvir musica", "tocar o álbum"
    ],
    "media_control": [
        "pausar música", "continue a música", "pare o som", "dar play", "retomar reprodução"
    ],
    "volume_control": [
        "aumente o volume", "abaixe o volume", "diminuir o som", "deixe no mudo"
    ],
    "get_news": [
        "quais são as últimas notícias", "notícias de hoje", "últimas manchetes"
    ],
    "search_web": [
        "pesquise na internet sobre", "pesquise o resultado", "quem é o atual campeão",
        "qual a cotação do dólar", "pesquise sobre", "busque na web", "procure na internet"
    ],
    "hyprland_control": [
        "mude para a área de trabalho 2", "vá para o workspace 3", "fechar janela",
        "tela cheia", "modo tela cheia", "deixar janela flutuante", "abrir launcher"
    ],
    "restart_waybar": [
        "reinicie a waybar", "reiniciar a barra", "reinicia waybar", "inicie a waybar", "atualizar waybar"
    ],
    "pomodoro_control": [
        "iniciar pomodoro", "inicie o pomodoro", "começar pomodoro", "comece o pomodoro", "inicie pomodoro de 25 minutos", "ativar pomodoro", "iniciar modo foco",
        "pausar pomodoro", "pause o pomodoro", "congele o pomodoro", "pausar foco", "pause o foco",
        "retomar pomodoro", "despause o pomodoro", "continue o pomodoro", "retomar foco",
        "próximo ciclo", "próxima pausa", "iniciar pausa", "ir para pausa", "pular fase", "avançar pomodoro", "próxima fase do pomodoro", "próximo pomodoro",
        "parar pomodoro", "cancele o pomodoro", "desative o pomodoro", "zerar pomodoro", "encerrar pomodoro", "parar o foco",
        "status do pomodoro", "quanto tempo falta no pomodoro", "como está o pomodoro"
    ]
}

NUMBER_WORDS = {
    "um": 1, "uma": 1, "dois": 2, "duas": 2, "três": 3, "tres": 3,
    "quatro": 4, "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9,
    "dez": 10, "onze": 11, "doze": 12, "quinze": 15, "vinte": 20,
    "trinta": 30, "quarenta": 40, "cinquenta": 50, "sessenta": 60
}

class IntentEngine:
    def __init__(self, confidence_threshold: float = 0.35):
        self.threshold = confidence_threshold
        self.phrases = []
        self.labels = []

        for intent, examples in TRAINING_DATA.items():
            for ex in examples:
                self.phrases.append(self._normalize(ex))
                self.labels.append(intent)

        self.vectorizer = FeatureUnion([
            ("word", TfidfVectorizer(ngram_range=(1, 3), sublinear_tf=True)),
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True))
        ])

        X = self.vectorizer.fit_transform(self.phrases)
        self.clf = LogisticRegression(C=10.0, max_iter=500, class_weight="balanced")
        self.clf.fit(X, self.labels)

    def _normalize(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r'\b(para\s+o\s+manhã|para\s+a\s+manhã|amanya)\b', 'amanhã', text)
        text = re.sub(r'\b(tá\s+a\s+merda|taimer|táime|taime)\b', 'timer', text)
        text = re.sub(r'[^\w\s%]', '', text)
        return text.strip()

    def _parse_number(self, token: str) -> int:
        token = token.strip().lower()
        return int(token) if token.isdigit() else NUMBER_WORDS.get(token, 0)

    def predict(self, text: str) -> tuple[str, float, dict]:
        norm = self._normalize(text)
        if not norm:
            return "unknown", 0.0, {}

        intent_override = self._hard_rules(norm)
        if intent_override:
            slots = self.extract_slots(intent_override, text, norm)
            return intent_override, 1.0, slots

        X_test = self.vectorizer.transform([norm])
        probs = self.clf.predict_proba(X_test)[0]
        max_idx = int(np.argmax(probs))
        best_intent = self.clf.classes_[max_idx]
        confidence = float(probs[max_idx])

        if norm.startswith(("como ", "por que ", "porque ", "explique ", "qual a diferença ", "o que é ")):
            if best_intent not in ["get_weather", "get_calendar", "search_web", "get_news"]:
                return "conversa_llm", confidence, {}

        if confidence < self.threshold:
            return "conversa_llm", confidence, {}

        slots = self.extract_slots(best_intent, text, norm)
        return best_intent, confidence, slots

    def _hard_rules(self, norm: str) -> str | None:
        if re.search(r'^(bom\s+dia|boa\s+dia)\b', norm):
            return "greeting_morning"
        if any(norm.startswith(w) for w in ["obrigado", "muito obrigado", "valeu", "obrigada"]):
            return "thanks"
        if re.search(r'\b(que\s+horas\s+são|hora\s+certa|qual\s+é\s+a\s+hora)\b', norm):
            return "get_time"
        if "waybar" in norm or ("barra" in norm and any(w in norm for w in ["reinic", "atualiz"])):
            return "restart_waybar"
        if "cronômetro" in norm or "cronometro" in norm:
            if "regressivo" not in norm:
                return "control_stopwatch"

        # Regras de pausa e retomada de timer sem colidir com mídia ou cronômetro
        non_timer_targets = ["música", "musica", "som", "reprodução", "reproducao", "cronômetro", "cronometro"]
        if not any(t in norm for t in non_timer_targets):
            if any(w in norm for w in ["despause", "despausar", "resumir"]) or (
                "timer" in norm and any(w in norm for w in ["retomar", "continuar", "retome", "continue"])
            ):
                return "resume_timer"
            if "timer" in norm and any(w in norm for w in ["pause", "pausar", "congele"]):
                return "pause_timer"

        if "timer" in norm and any(w in norm for w in ["ativo", "ativos", "rodando", "tem", "quais"]):
            return "list_timers"
        if "timer" in norm and any(w in norm for w in ["defina", "coloque", "bote", "inicie", "marque", "crie"]):
            return "set_timer"
        if "alarme" in norm or "despertador" in norm:
            if any(w in norm for w in ["defina", "coloque", "bote", "marque", "crie"]):
                return "set_alarm"
        if any(w in norm for w in ["alarme", "alarmes", "despertador", "despertadores", "timer", "timers"]):
            if any(w in norm for w in ["cancele", "cancelar", "desative", "desativar", "desativem", "desligue", "desligar", "apague", "apagar", "remova", "remover", "exclua", "excluir", "parar", "pare", "silencie", "silenciar", "silêncio", "silencio"]):
                return "cancel_timers"
        if "pomodoro" in norm or "modo foco" in norm:
            return "pomodoro_control"
        if norm in ["próximo ciclo", "proximo ciclo", "próxima pausa", "proxima pausa", "iniciar pausa", "ir para pausa", "próxima fase", "proxima fase"]:
            return "pomodoro_control"
        if norm in ["cancele todos", "cancelar todos", "desative todos", "desativar todos", "todos os alarmes", "todos os timers", "silêncio", "silencio", "pare de tocar", "parar de tocar"]:
            return "cancel_timers"
        if any(w in norm for w in ["toque", "tocar", "ouvir", "reproduza"]):
            if not any(w in norm for w in ["pausar", "parar", "continuar"]):
                return "play_music"
        if any(w in norm for w in ["pesquise", "procure", "busque", "cotação"]):
            return "search_web"
        if any(w in norm for w in ["workspace", "área de trabalho", "tela cheia", "flutuante", "launcher", "brilho"]):
            return "hyprland_control"
        return None

    def extract_slots(self, intent: str, raw_text: str, norm: str) -> dict:
        slots = {}
        num_pattern = r'(\d+|' + '|'.join(NUMBER_WORDS.keys()) + r')'

        if intent in ["cancel_timers", "pause_timer", "resume_timer"]:
            if "todos os alarmes" in norm or "todos alarmes" in norm:
                slots["query"] = "todos os alarmes"
            elif "todos os timers" in norm or "todos timers" in norm:
                slots["query"] = "todos os timers"
            elif norm in ["cancele todos", "cancelar todos", "desative todos", "desativar todos", "todos"]:
                slots["query"] = "todos"
            else:
                m_target = re.search(r'(?:chamado|timer|alarme|despertador)\s+([a-zA-ZÀ-ÿ0-9\s]+)$', norm)
                if m_target:
                    q = m_target.group(1).strip()
                    slots["query"] = re.sub(r'\b(o|a|os|as|timer|timers|alarme|alarmes|chamado|de)\b', '', q).strip()
                else:
                    q = re.sub(
                        r'^(cancele|cancelar|pare|parar|desative|desativar|desativem|desligue|desligar|apague|apagar|remova|remover|exclua|excluir|pause|pausar|congele|retome|retomar|resumir|despause|despausar|continue|continuar|reiniciar)\s*'
                        r'(todos\s+os\s+timers|todos\s+os\s+alarmes|todos\s+os\s+despertadores|todos|todas|o\s+timer|o\s+alarme|os\s+alarmes|os\s+timers|timer|alarme|alarmes)?\s*(do|da|das)?\s*',
                        '',
                        norm
                    ).strip()
                    slots["query"] = re.sub(r'\b(chamado|de)\b', '', q).strip()

        elif intent == "hyprland_control":
            if "workspace" in norm or "área de trabalho" in norm:
                m_ws = re.search(num_pattern, norm)
                slots["action"] = "workspace"
                slots["target"] = str(self._parse_number(m_ws.group(1))) if m_ws else "1"
            elif "fechar" in norm or "matar" in norm:
                slots["action"] = "close_window"
            elif "tela cheia" in norm or "fullscreen" in norm:
                slots["action"] = "fullscreen"
            elif "flutuante" in norm or "floating" in norm:
                slots["action"] = "floating"
            elif "launcher" in norm or "menu" in norm or "aplicativos" in norm:
                slots["action"] = "launcher"
            elif "brilho" in norm:
                m_bri = re.search(r'(\d+%)', norm)
                slots["action"] = "brightness"
                slots["target"] = m_bri.group(1) if m_bri else "50%"
            else:
                slots["action"] = "launcher"

        elif intent == "set_alarm":
            h, m = self._extract_time(norm)
            slots["hour"] = h
            slots["minute"] = m
            m_label = re.search(r'(?:para\s+o|para\s+a|chamado)\s+([a-zA-ZÀ-ÿ0-9\s]+)$', norm)
            slots["label"] = m_label.group(1).strip().title() if m_label else "Alarme"

        elif intent == "set_timer":
            m_min = re.search(num_pattern + r'\s*(?:minuto|minutos|min|m\b)', norm)
            m_sec = re.search(num_pattern + r'\s*(?:segundo|segundos|seg|s\b)', norm)
            m_hr = re.search(num_pattern + r'\s*(?:hora|horas|h\b)', norm)

            slots["hours"] = self._parse_number(m_hr.group(1)) if m_hr else 0
            slots["minutes"] = self._parse_number(m_min.group(1)) if m_min else (0 if (m_sec or m_hr) else 5)
            slots["seconds"] = self._parse_number(m_sec.group(1)) if m_sec else 0

            m_rotulo = re.search(r'(?:chamado|para\s+o|para\s+a|para)\s+([a-zA-ZÀ-ÿ0-9\s]+)$', norm)
            if m_rotulo:
                rotulo_raw = m_rotulo.group(1).strip()
                rotulo_limpo = re.sub(r'\b(o|a|um|uma)\b', '', rotulo_raw).strip()
                slots["label"] = rotulo_limpo.title() if rotulo_limpo else "Timer"
            else:
                slots["label"] = "Timer"

        elif intent == "control_stopwatch":
            if any(w in norm for w in ["pausar", "pause"]):
                slots["action"] = "pause"
            elif any(w in norm for w in ["zerar", "parar", "resetar", "reiniciar"]):
                slots["action"] = "reset"
            else:
                slots["action"] = "start"

        elif intent == "pomodoro_control":
            if any(w in norm for w in ["proxim", "próxim", "avanc", "avanç", "pul", "fase", "proxima pausa", "próxima pausa", "iniciar pausa", "ir para pausa", "proximo ciclo", "próximo ciclo"]):
                slots["action"] = "advance"
            elif any(w in norm for w in ["pausar", "pause", "congel"]):
                slots["action"] = "pause"
            elif any(w in norm for w in ["retom", "despaus", "continu"]):
                slots["action"] = "resume"
            elif any(w in norm for w in ["par", "cancel", "desativ", "zer", "encerr"]):
                slots["action"] = "stop"
            elif any(w in norm for w in ["quant", "tempo", "status", "como"]):
                slots["action"] = "status"
            elif "pausa" in norm and any(w in norm for w in ["hora", "comece", "inicie", "vai", "vamos"]):
                slots["action"] = "advance"
            else:
                slots["action"] = "start"

            m_min = re.search(r'(\d+)\s*(?:minuto|minutos|min\b)', norm)
            if m_min:
                slots["work_minutes"] = int(m_min.group(1))

        elif intent == "play_music":
            q = re.sub(r'^(toque\s+a\s+música|toque|tocar|reproduza|coloque|quero ouvir)\s*', '', raw_text, flags=re.IGNORECASE)
            q = re.sub(r'\s*(no\s+youtube\s+music|no\s+youtube)$', '', q, flags=re.IGNORECASE)
            slots["query"] = q.strip() or "música"
            slots["item_type"] = "album" if any(w in norm for w in ["álbum", "album"]) else "auto"

        elif intent == "volume_control":
            m_pct = re.search(r'(\d+)\s*(?:%|por\s*cento)', norm)
            if "mudo" in norm or "silenciar" in norm or "mute" in norm:
                slots["change"] = "mute"
            elif m_pct:
                slots["change"] = m_pct.group(1)
            elif any(w in norm for w in ["abaixe", "abaixar", "baixar", "diminuir", "diminua", "reduzir", "reduza", "menos"]):
                slots["change"] = "-"
            else:
                slots["change"] = "+"

        elif intent == "get_weather":
            if "amanhã" in norm or "amanha" in norm:
                slots["query_type"] = "amanhã"
            elif "semana" in norm:
                slots["query_type"] = "semana"
            else:
                slots["query_type"] = "hoje"
            m_city = re.search(r'\b(?:em|para|de)\s+([a-zA-ZÀ-ÿ\s]+?)(?:\s+(?:hoje|amanhã|amanha|semana))?$', norm)
            slots["query"] = m_city.group(1).strip() if m_city else "Anápolis"

        elif intent == "get_calendar":
            slots["date_query"] = norm

        elif intent == "create_calendar":
            h, m = self._extract_time(norm)
            slots["time_str"] = f"{h:02d}:{m:02d}"
            slots["date_query"] = norm
            m_sum = re.search(r'(?:chamado|sobre|para|reunião|compromisso|evento)\s+([a-zA-ZÀ-ÿ0-9\s]+?)(?:\s+(?:hoje|amanhã|amanha|às|as|para)\b|$)', norm)
            slots["summary"] = m_sum.group(1).strip().title() if m_sum else "Compromisso"
            slots["duration_minutes"] = 60

        elif intent == "get_news":
            m_topic = re.search(r'\b(?:notícias|noticias|manchetes)\s+(?:sobre|de|do|da)\s+([a-zA-ZÀ-ÿ0-9\s]+)$', norm)
            if m_topic and m_topic.group(1).strip() not in ["hoje", "dia", "agora", "últimas", "ultimas"]:
                slots["query"] = m_topic.group(1).strip()
            else:
                slots["query"] = "geral"

        elif intent == "search_web":
            q = re.sub(
                r'^(pesquise\s+na\s+internet\s+sobre|pesquise\s+na\s+web\s+sobre|pesquise\s+sobre|pesquise|busque\s+na\s+web|procure\s+na\s+internet)\s*',
                '',
                raw_text.strip(" ?."),
                flags=re.IGNORECASE
            ).strip()
            slots["query"] = q or raw_text.strip(" ?.")

        return slots

    def _extract_time(self, norm: str) -> tuple[int, int]:
        # Exclui artigos "um"/"uma" quando seguidos de substantivos como alarme/compromisso/reunião/evento
        cleaned = re.sub(r'\b(um|uma)\s+(alarme|despertador|compromisso|evento|reunião|reuniao|lembrete)\b', r'\2', norm)
        num_pattern = r'(\d{1,2}|' + '|'.join(NUMBER_WORDS.keys()) + r')'
        # Prioriza padrões com indicador de horário (às, para as, horas, h, :, e meia, da manhã/tarde/noite)
        m = re.search(
            r'(?:(?:às|as|para\s+as|para)\s+)?\b' + num_pattern +
            r'(?:\s*(?:horas?|h|:)\s*(?:e\s*)?(\d{1,2}|meia|' + '|'.join(NUMBER_WORDS.keys()) + r')?'
            r'|\s+e\s+(meia|\d{1,2}|' + '|'.join(NUMBER_WORDS.keys()) + r')'
            r'|\s+da\s+(?:manhã|manha|tarde|noite))',
            cleaned
        )
        if not m:
            m = re.search(r'\b(\d{1,2})\b', cleaned)
        if m:
            h = self._parse_number(m.group(1))
            min_raw = (m.group(2) if m.lastindex and m.lastindex >= 2 else None) or (m.group(3) if m.lastindex and m.lastindex >= 3 else None)
            if min_raw == "meia":
                minute = 30
            elif min_raw:
                minute = self._parse_number(min_raw)
            else:
                minute = 0
            if any(p in cleaned for p in ["noite", "tarde"]) and h < 12:
                h += 12
            return h % 24, minute % 60
        return 8, 0
