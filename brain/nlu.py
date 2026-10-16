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
        "cancele todos os timers", "cancelar alarme", "pare o timer", "cancele o alarme", "cancele todos"
    ],
    "control_stopwatch": [
        "inicie o cronômetro", "pausar cronômetro", "zerar cronômetro"
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
    ]
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
        text = re.sub(r'[^\w\s]', '', text)
        return text.strip()

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
        if "timer" in norm and any(w in norm for w in ["ativo", "rodando", "tem", "quais"]):
            return "list_timers"
        if "timer" in norm and any(w in norm for w in ["defina", "coloque", "bote", "inicie", "marque"]):
            return "set_timer"
        if "alarme" in norm or "despertador" in norm:
            if any(w in norm for w in ["defina", "coloque", "bote", "marque", "crie"]):
                return "set_alarm"
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

        if intent == "cancel_timers":
            q = re.sub(r'^(cancele|cancelar|pare|parar|desativar|apague)\s*(todos\s+os\s+timers|o\s+timer|o\s+alarme|timer|alarme)?\s*(do|da|das)?\s*', '', norm).strip()
            slots["query"] = q

        elif intent == "hyprland_control":
            if "workspace" in norm or "área de trabalho" in norm:
                m_ws = re.search(r'(\d+)', norm)
                slots["action"] = "workspace"
                slots["target"] = m_ws.group(1) if m_ws else "1"
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
            m_min = re.search(r'(\d+)\s*(?:minuto|minutos|min|m\b)', norm)
            m_sec = re.search(r'(\d+)\s*(?:segundo|segundos|seg|s\b)', norm)
            m_hr = re.search(r'(\d+)\s*(?:hora|horas|h\b)', norm)

            slots["hours"] = int(m_hr.group(1)) if m_hr else 0
            slots["minutes"] = int(m_min.group(1)) if m_min else (0 if m_sec or m_hr else 5)
            slots["seconds"] = int(m_sec.group(1)) if m_sec else 0

            m_rotulo = re.search(r'(?:chamado|para\s+o|para\s+a|para)\s+([a-zA-ZÀ-ÿ0-9\s]+)$', norm)
            if m_rotulo:
                rotulo_raw = m_rotulo.group(1).strip()
                rotulo_limpo = re.sub(r'\b(o|a|um|uma)\b', '', rotulo_raw).strip()
                slots["label"] = rotulo_limpo.title() if rotulo_limpo else "Timer"
            else:
                slots["label"] = "Timer"

        elif intent == "play_music":
            q = re.sub(r'^(toque\s+a\s+música|toque|tocar|reproduza|coloque|quero ouvir)\s*', '', raw_text, flags=re.IGNORECASE)
            q = re.sub(r'\s*(no\s+youtube\s+music|no\s+youtube)$', '', q, flags=re.IGNORECASE)
            slots["query"] = q.strip() or "música"
            slots["item_type"] = "auto"

        elif intent == "volume_control":
            slots["change"] = "mute" if "mudo" in norm else ("-" if "abaixe" in norm or "baixar" in norm else "+")

        elif intent in ["search_web", "get_news"]:
            slots["query"] = raw_text.strip(" ?.")

        return slots

    def _extract_time(self, norm: str) -> tuple[int, int]:
        m = re.search(r'\b(\d{1,2})(?:\s*(?:horas?|h|:)\s*(?:e\s*)?(\d{1,2}|meia)?)?', norm)
        if m:
            h = int(m.group(1))
            min_raw = m.group(2)
            minute = 30 if min_raw == "meia" else (int(min_raw) if min_raw and min_raw.isdigit() else 0)
            if any(p in norm for p in ["noite", "tarde"]) and h < 12:
                h += 12
            return h % 24, minute % 60
        return 8, 0
