"""
Módulos de transcrição de reuniões (Local via Whisper e Nuvem).
"""
from abc import ABC, abstractmethod
import json
import os
import urllib.request
import urllib.error
import uuid
from typing import List, Optional

from services.meeting.models import MeetingSegment
import config


class MeetingTranscriber(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str) -> List[MeetingSegment]:
        """Transcreve um arquivo de áudio e retorna os segmentos com timestamps."""
        pass


class LocalMeetingTranscriber(MeetingTranscriber):
    """Transcrição 100% local e confidencial usando faster-whisper."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "pt",
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self._model = None

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            cpu_threads = max(1, (os.cpu_count() or 4) - 1)
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=cpu_threads,
                num_workers=1,
            )
        return self._model

    def transcribe(self, audio_path: str) -> List[MeetingSegment]:
        if not os.path.exists(audio_path):
            return []

        model = self._get_model()

        # Lê WAV de forma nativa para evitar bugs de PyAV (av.open metadata_errors) no Python 3.14
        audio_input = audio_path
        try:
            import wave
            import numpy as np
            with wave.open(audio_path, "rb") as wf:
                sampwidth = wf.getsampwidth()
                nchannels = wf.getnchannels()
                frames = wf.readframes(wf.getnframes())
                if sampwidth == 2 and nchannels == 1:
                    audio_input = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        except Exception:
            audio_input = audio_path

        segments_gen, _ = model.transcribe(
            audio_input,
            language=self.language,
            beam_size=2,
            temperature=0.0,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        segments = []
        for s in segments_gen:
            text = s.text.strip()
            if text:
                segments.append(
                    MeetingSegment(
                        start=float(s.start),
                        end=float(s.end),
                        text=text,
                    )
                )
        return segments


class CloudMeetingTranscriber(MeetingTranscriber):
    """Transcrição via API na nuvem (Groq Whisper, OpenAI ou Gemini)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: str = "whisper-1",
        language: str = "pt",
    ):
        self.api_key = api_key or getattr(config, "LLM_API_KEY", "")
        self.api_base = (api_base or "https://api.openai.com/v1").rstrip("/")
        self.model = model
        self.language = language

    def transcribe(self, audio_path: str) -> List[MeetingSegment]:
        if not os.path.exists(audio_path):
            return []

        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        if len(audio_bytes) == 0:
            return []

        boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
        body = bytearray()

        def add_field(name: str, value: str):
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
            body.extend(f"{value}\r\n".encode("utf-8"))

        def add_file(name: str, filename: str, content: bytes, content_type: str = "audio/wav"):
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode("utf-8"))
            body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
            body.extend(content)
            body.extend(b"\r\n")

        add_file("file", os.path.basename(audio_path), audio_bytes)
        add_field("model", self.model)
        add_field("language", self.language)
        add_field("response_format", "verbose_json")
        body.extend(f"--{boundary}--\r\n".encode("utf-8"))

        url = f"{self.api_base}/audio/transcriptions"
        headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "Geraldo-MeetingAssistant/1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key.strip()}"

        req = urllib.request.Request(url, data=bytes(body), headers=headers)
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        segments = []
        raw_segments = data.get("segments", [])
        if raw_segments:
            for seg in raw_segments:
                text = seg.get("text", "").strip()
                if text:
                    segments.append(
                        MeetingSegment(
                            start=float(seg.get("start", 0.0)),
                            end=float(seg.get("end", 0.0)),
                            text=text,
                        )
                    )
        elif data.get("text"):
            # Fallback se a API retornar apenas o texto completo
            segments.append(
                MeetingSegment(
                    start=0.0,
                    end=0.0,
                    text=data["text"].strip(),
                )
            )

        return segments


def create_meeting_transcriber(provider: str = "local", **kwargs) -> MeetingTranscriber:
    """Fábrica de instâncias de transcritores."""
    p = (provider or "local").lower()
    if p in ("cloud", "openai", "groq", "gemini"):
        return CloudMeetingTranscriber(**kwargs)
    return LocalMeetingTranscriber(**kwargs)
