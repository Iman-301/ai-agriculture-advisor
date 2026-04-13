"""Standalone TTS service for Amharic (gTTS)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

app = FastAPI(title="Agri TTS Service", version="1.0.0")

_OUTPUT_DIR = Path(tempfile.gettempdir()) / "agri_tts_out"
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    lang: str = Field(default="am")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/synthesize")
def synthesize(payload: TTSRequest) -> FileResponse:
    try:
        from gtts import gTTS
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="Missing dependency: pip install gTTS") from exc

    # Unique filename to avoid multi-request collisions.
    out_file = _OUTPUT_DIR / f"{uuid4().hex}.mp3"
    try:
        tts = gTTS(text=payload.text.strip(), lang=payload.lang, slow=False)
        tts.save(str(out_file))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"TTS generation failed: {exc}",
        ) from exc

    return FileResponse(
        path=str(out_file),
        media_type="audio/mpeg",
        filename="speech.mp3",
    )

