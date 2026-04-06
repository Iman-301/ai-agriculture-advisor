"""Recording / VAD hooks — stub for Phase 3 (use sounddevice/pyaudio when wired)."""

from __future__ import annotations


def describe_audio_pipeline() -> str:
    return (
        "Audio pipeline placeholder: connect telephony 8 kHz stream → VAD → ASR. "
        "See services/asr_service.py for transcription entry point."
    )
