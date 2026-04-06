"""Voice pipeline: ASR (mock) → same pipeline as chat CLI. Optional: Whisper + pyaudio."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config import settings

from src.cli.chatbot_cli import build_system
from src.services.asr_service import MockASRService, WhisperASRService


def main() -> None:
    dm = build_system()
    if settings.openai_api_key:
        asr: MockASRService | WhisperASRService = WhisperASRService(settings.openai_api_key)
        print("Using OpenAI Whisper ASR.")
    else:
        asr = MockASRService()
        print("Using mock ASR (set OPENAI_API_KEY for Whisper).")

    session_id = "voice_cli"
    phone = "+251900000000"

    print("Voice CLI (mock). Enter path to a .wav file, or press Enter for a fake path.")
    while True:
        path = input("\nAudio file path (or 'quit'): ").strip()
        if path.lower() in ("quit", "exit"):
            break
        if not path:
            path = str(Path(tempfile.gettempdir()) / "agri_voice_dummy.wav")

        result = asr.transcribe(path)
        text = result["text"]
        conf = float(result.get("confidence", 0.0))
        print(f"ASR ({conf:.2f}): {text}")

        if conf < settings.asr_confidence_threshold:
            print("Low confidence — in production, ask caller to repeat.")
            continue

        bundle = dm.process_text(session_id, phone, text, asr_confidence=conf)
        print(f"Bot: {bundle.text}")


if __name__ == "__main__":
    main()
