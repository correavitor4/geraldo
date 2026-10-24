"""
Módulo de escuta ativa e geração de atas de reuniões para o assistente Geraldo.
"""
from services.meeting.models import (
    MeetingStatus,
    MeetingSegment,
    MeetingSummary,
    MeetingSession,
)
from services.meeting.recorder import MeetingAudioRecorder
from services.meeting.transcriber import (
    MeetingTranscriber,
    LocalMeetingTranscriber,
    CloudMeetingTranscriber,
    create_meeting_transcriber,
)
from services.meeting.analyzer import (
    MeetingAnalyzer,
    LocalMeetingAnalyzer,
    CloudMeetingAnalyzer,
    create_meeting_analyzer,
)
from services.meeting.manager import MeetingManager

__all__ = [
    "MeetingStatus",
    "MeetingSegment",
    "MeetingSummary",
    "MeetingSession",
    "MeetingAudioRecorder",
    "MeetingTranscriber",
    "LocalMeetingTranscriber",
    "CloudMeetingTranscriber",
    "create_meeting_transcriber",
    "MeetingAnalyzer",
    "LocalMeetingAnalyzer",
    "CloudMeetingAnalyzer",
    "create_meeting_analyzer",
    "MeetingManager",
]
