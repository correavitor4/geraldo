import sounddevice as sd


def list_audio_devices():
    """Retorna lista de dispositivos de entrada e saída com metadados amigáveis."""
    try:
        devices = sd.query_devices()
    except Exception:
        return {"inputs": [], "outputs": []}

    inputs = []
    outputs = []
    for idx, dev in enumerate(devices):
        name = dev.get("name", f"Dispositivo {idx}")
        max_in = dev.get("max_input_channels", 0)
        max_out = dev.get("max_output_channels", 0)
        if max_in > 0:
            inputs.append({
                "id": idx,
                "name": name,
                "channels": max_in,
                "default_samplerate": dev.get("default_samplerate", 16000),
            })
        if max_out > 0:
            outputs.append({
                "id": idx,
                "name": name,
                "channels": max_out,
                "default_samplerate": dev.get("default_samplerate", 44100),
            })
    return {"inputs": inputs, "outputs": outputs}


def resolve_audio_device(device_spec, kind: str = "input"):
    """
    Resolve uma especificação de dispositivo (None, int, ou str) para um índice válido do sounddevice.
    Retorna None se for padrão ou não encontrado.
    """
    if device_spec is None or device_spec == "" or str(device_spec).lower() in ("default", "padrão", "none"):
        return None
    try:
        idx = int(device_spec)
        devices = sd.query_devices()
        if 0 <= idx < len(devices):
            dev = devices[idx]
            if (kind == "input" and dev.get("max_input_channels", 0) > 0) or \
               (kind == "output" and dev.get("max_output_channels", 0) > 0):
                return idx
    except (ValueError, TypeError):
        pass

    target = str(device_spec).lower().strip()
    try:
        devices = sd.query_devices()
        for idx, dev in enumerate(devices):
            dname = dev.get("name", "").lower()
            if kind == "input" and dev.get("max_input_channels", 0) > 0 and target in dname:
                return idx
            if kind == "output" and dev.get("max_output_channels", 0) > 0 and target in dname:
                return idx
    except Exception:
        pass
    return None


def get_input_device_id(name_substring: str = "Fifine K420"):
    """Encontra o índice de entrada do microfone pela substring."""
    return resolve_audio_device(name_substring, kind="input")

