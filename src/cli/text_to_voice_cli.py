"""Text-to-Voice CLI: Type Amharic text, hear spoken response.

Bypasses ASR completely - perfect for testing TTS (FR-14) without ASR issues.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config import settings
from src.cli.chatbot_cli import build_system
from src.services.tts_service import GTTSService, MockTTSService


def main() -> None:
    dm = build_system()

    # Initialize TTS
    try:
        tts = GTTSService(lang="am")
        print("Using gTTS for text-to-speech (Amharic).")
    except RuntimeError:
        tts = MockTTSService()
       