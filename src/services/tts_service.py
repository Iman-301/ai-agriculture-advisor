"""FR-14 — TTS adapter; mock writes placeholder; Google Cloud optional."""

from __future__ import annotations

from pathlib import Path

from ..application.ports import TTSPort


class MockTTSService(TTSPort):
    def synthesize_to_file(self, text: str, out_path: str) -> str:
        path = Path(out_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"[TTS mock] {text}\n", encoding="utf-8")
        return str(path.resolve())
