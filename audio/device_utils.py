import sounddevice as sd

def get_input_device_id(name_substring: str = "Fifine K420"):
    """Encontra o índice de entrada do microfone pela substring."""
    devices = sd.query_devices()
    for idx, dev in enumerate(devices):
        if dev['max_input_channels'] > 0 and name_substring.lower() in dev['name'].lower():
            return idx
    return None
