import numpy as np
from brain.stt import SpeechToText

class WakeWordDetector:
    def __init__(self, target_word: str = "geraldo", stt: SpeechToText = None):
        self.target_word = target_word.lower().strip()
        # Usa o STT existente para aproveitar o modelo tiny otimizado
        self.stt = stt if stt else SpeechToText(wake_model_size="tiny", cmd_model_size="small")

    def wait_for_wake_word(self) -> bool:
        """
        Escuta o microfone em pequenos blocos de áudio até detectar 
        exatamente a palavra-chave, ignorando ruídos aleatórios.
        """
        import sounddevice as sd
        
        sample_rate = 16000
        block_duration = 1.5  # Analisa blocos de 1.5 segundos
        block_size = int(sample_rate * block_duration)

        print(f"[Geraldo] Aguardando wake word: '{self.target_word}'...")

        with sd.InputStream(device=None, samplerate=sample_rate, channels=1, dtype='float32') as stream:
            while True:
                # Captura um bloco contínuo de áudio do microfone sem fechar o stream
                audio_chunk, _ = stream.read(block_size)
                audio_data = np.squeeze(audio_chunk)

                # Filtro básico de energia: se o áudio for silêncio quase absoluto, pula o processamento
                if np.max(np.abs(audio_data)) < 0.02:
                    continue

                # Transcreve usando o modelo leve (tiny) com parâmetros estritos
                try:
                    segments, _ = self.stt.model_wake.transcribe(
                        audio_data,
                        language="pt",
                        beam_size=1,
                        best_of=1,
                        temperature=0.0,
                        initial_prompt="Geraldo.",
                        condition_on_previous_text=False,
                        vad_filter=True,
                        vad_parameters=dict(min_silence_duration_ms=300, threshold=0.6)
                    )
                    
                    text = " ".join([seg.text.strip() for seg in segments]).strip().lower()
                    
                    # Remove pontuações para análise limpa
                    cleaned_text = "".join([c for c in text if c.isalnum() or c.isspace()])
                    words = cleaned_text.split()

                    # Verifica se a palavra-chave está presente de forma clara
                    if self.target_word in words or any(self.target_word in w for w in words):
                        print(f"[Geraldo] Wake word confirmada! Texto capturado: '{text}'")
                        return True

                except Exception:
                    # Evita que erros de áudio quebrem o loop de escuta
                    continue