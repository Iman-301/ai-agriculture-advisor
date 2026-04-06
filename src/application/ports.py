"""Service interfaces (SDS — ASR, NLU, TTS, telephony adapters)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ASRPort(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str, language_hint: str | None = None) -> dict[str, Any]:
        """Return at least: text (str), confidence (float 0..1)."""


class NLUPort(ABC):
    @abstractmethod
    def parse(
        self,
        text: str,
        session_context: dict[str, Any] | None = None,
        asr_confidence: float | None = None,
    ) -> dict[str, Any]:
        """
        Return structured NLU:
        intent, entities, confidence, missing_slots, flags, original_text
        """


class TTSPort(ABC):
    @abstractmethod
    def synthesize_to_file(self, text: str, out_path: str) -> str:
        """Write audio to out_path; return path."""


class TelephonyPort(ABC):
    @abstractmethod
    def build_incoming_twiml(self, base_url: str) -> str:
        """Produce TwiML string for webhook response."""
