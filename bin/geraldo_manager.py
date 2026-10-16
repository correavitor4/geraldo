#!/usr/bin/env python3
import json
import os
import subprocess

STATUS_FILE = "/tmp/geraldo_status.json"

def load_status():
    if not os.path.exists(STATUS_FILE):
        return {"timers": {}, "alarms": {}, "stopwatch": {}}
    try:
        with open(STATUS_FILE, "r") as f:
            return json.load(f)
    except:
        return {"timers": {}, "alarms": {}, "stopwatch": {}}

def main():
    # Como o TimerManager exporta um resumo simples, vamos estendê-lo para exportar um dicionário completo
    pass

if __name__ == "__main__":
    main()
