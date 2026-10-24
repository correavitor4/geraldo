import numpy as np
from typing import Optional
from brain.stt import SpeechToText

class WakeWordDetector:
    def __init__(self, target_word: str = "geraldo", stt: SpeechToText = None):
        self.target_word = target_word.lower().strip()
        # Usa o STT existente para aproveitar o modelo tiny otimizado
        self.stt = stt if stt else SpeechToText(wake_model_size="tiny", cmd_model_size="small")

    def wait_for_wake_word(self, max_loops: Optional[int] = None) -> bool:
        """
        Escuta o microfone em pequenos blocos de áudio até detectar 
        exatamente a palavra-chave, ignorando ruídos aleatórios.
        """
        import sounddevice as sd
        import config
        from audio.device_utils import resolve_audio_device
        
        sample_rate = 16000
        block_duration = 1.5  # Analisa blocos de 1.5 segundos
        block_size = int(sample_rate * block_duration)

        dev_idx = resolve_audio_device(getattr(config, "AUDIO_INPUT_DEVICE", None), kind="input")

        print(f"[Geraldo] Aguardando wake word: '{self.target_word}' (dispositivo: {dev_idx if dev_idx is not None else 'padrão'})...")

        loops = 0
        with sd.InputStream(device=dev_idx, samplerate=sample_rate, channels=1, dtype='float32') as stream:
            while max_loops is None or loops < max_loops:
                loops += 1
                # Captura um bloco contínuo de áudio do microfone sem fechar o stream
                audio_chunk, _ = stream.read(block_size)
                audio_data = np.squeeze(audio_chunk)

                peak = np.max(np.abs(audio_data))
                # Filtro de energia calibrado: silêncio absoluto ou ruído eletrônico desprezível
                if peak < 0.0025:
                    continue

                # Normalização de pico para garantir transcrição precisa no Whisper mesmo em microfones com ganho baixo
                norm_audio = audio_data * (0.9 / peak) if peak > 0.001 else audio_data

                # Transcreve usando o modelo de wake word com prompt específico
                try:
                    segments, _ = self.stt.model_wake.transcribe(
                        norm_audio,
                        language="pt",
                        beam_size=1,
                        best_of=1,
                        temperature=0.0,
                        initial_prompt="Geraldo.",
                        condition_on_previous_text=False,
                        vad_filter=False,
                    )

                    for seg in segments:
                        no_speech = getattr(seg, "no_speech_prob", None)
                        if isinstance(no_speech, (int, float)) and no_speech > 0.75:
                            continue

                        avg_logprob = getattr(seg, "avg_logprob", None)
                        if isinstance(avg_logprob, (int, float)) and avg_logprob < -1.4:
                            continue

                        text = seg.text.strip().lower()
                        cleaned_text = "".join([c for c in text if c.isalnum() or c.isspace()])
                        words = cleaned_text.split()
                        no_spaces = cleaned_text.replace(" ", "")

                        # Verifica se a palavra-chave está presente (inclui variações fonéticas comuns como "geral do")
                        if (
                            self.target_word in words
                            or self.target_word in no_spaces
                            or "gerald" in no_spaces
                            or any(self.target_word in w for w in words)
                        ):
                            print(f"[Geraldo] Wake word confirmada! Texto capturado: '{text}'")
                            return True

                except Exception as e:
                    # Evita que erros esporádicos de I/O quebrem o loop de escuta
                    continue

        return False