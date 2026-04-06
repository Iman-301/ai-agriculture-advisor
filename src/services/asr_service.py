"""FR-03 — ASR adapter; mock for tests, real provider optional."""

from __future__ import annotations

import random
from typing import Any

from ..application.ports import ASRPort


class MockASRService(ASRPort):
    """Returns deterministic transcript from filename or random phrase for tests."""

    def transcribe(self, audio_path: str, language_hint: str | None = "am") -> dict[str, Any]:
        seed = abs(hash(audio_path)) % 10_000
        rng = random.Random(seed)
        samples = [
            "ጤፍ ለምን ያህል ዩሪያ ልጠቀም",
            "What fertilizer rate for teff in Oromia?",
            "የስንዴ ዋጋ በአዲስ አበባ ስንት ነው?",
        ]
        text = samples[rng.randint(0, len(samples) - 1)]
        return {"text": text, "confidence": 0.75 + rng.random() * 0.2, "language": language_hint or "am"}


class WhisperASRService(ASRPort):
    """Optional OpenAI Whisper — install `openai` and set OPENAI_API_KEY."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def transcribe(self, audio_path: str, language_hint: str | None = "am") -> dict[str, Any]:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError("Install openai package for WhisperASRService") from e

        client = OpenAI(api_key=self._api_key)
        with open(audio_path, "rb") as f:
            tr = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language=language_hint or "am",
            )
        text = getattr(tr, "text", str(tr))
        return {"text": text, "confidence": 0.85, "language": language_hint or "am"}
