import json
import os

STATE_FILE = "/tmp/geraldo_state.json"

# Mapeia diretamente com as classes do seu ~/.config/waybar/style.css:
# idle, listening, thinking, speaking, off
STATES = {
    "dormindo": {
        "text": "󰍭 GERALDO",
        "alt": "idle",
        "tooltip": "Geraldo em espera (Diga 'Geraldo')",
        "class": "idle"
    },
    "escutando": {
        "text": "󰍬 OUVINDO...",
        "alt": "listening",
        "tooltip": "Geraldo ouvindo seu comando...",
        "class": "listening"
    },
    "pensando": {
        "text": "󰑮 PENSANDO...",
        "alt": "thinking",
        "tooltip": "Processando raciocínio...",
        "class": "thinking"
    },
    "falando": {
        "text": "󰕾 RESPONDENDO...",
        "alt": "speaking",
        "tooltip": "Geraldo sintetizando resposta...",
        "class": "speaking"
    },
    "off": {
        "text": "󰍭 OFF",
        "alt": "off",
        "tooltip": "Serviço Geraldo desativado",
        "class": "off"
    }
}

def set_state(state_name: str):
    data = STATES.get(state_name, STATES["dormindo"])
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass
