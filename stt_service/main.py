"""Standalone STT service for Amharic.

Backends (see STT_BACKEND):
- google-cloud-speech: Speech-to-Text with language am-ET (best accuracy when credentials are set).
- faster-whisper: local Systran CTranslate2 models (offline).
- auto: try GCP if credentials exist, else Whisper (set explicitly; default is whisper).

Optional Whisper fallback: Hugging Face transformers pipeline when decoded text has no Ethiopic script.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import wave
import zlib
from pathlib import Path
from threading import Lock
from typing import Any
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile

@asynccontextmanager
async def _lifespan(_app: FastAPI):
    # Start background load as early as possible (FastAPI on_event can be flaky across versions).
    _model_status["state"] = "starting"

    def _load() -> None:
        try:
            _get_faster_whisper_model()
        except Exception as exc:
            _model_status["state"] = "error"
            _model_status["error"] = str(exc)

    threading.Thread(target=_load, daemon=True).start()
    yield


app = FastAPI(title="Agri STT Service", version="1.0.0", lifespan=_lifespan)

_model = None
_model_lock = Lock()
_ethiopic_re = re.compile(r"[\u1200-\u137F]")
_latin_letters_re = re.compile(r"[A-Za-z]+")


def _gcp_credentials_available() -> bool:
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip():
        return True
    try:
        from google.auth import default as google_auth_default
        from google.auth.exceptions import DefaultCredentialsError

        google_auth_default()
        return True
    except (DefaultCredentialsError, ImportError, Exception):
        return False


def _stt_backend_choice() -> str:
    raw = os.getenv("STT_BACKEND", "whisper").strip().lower()
    if raw in ("gcp", "google", "google-cloud", "google_cloud_speech"):
        return "gcp"
    if raw in ("whisper", "faster-whisper", "local"):
        return "whisper"
    return "auto"


def _gather_pcm_s16le_16k_mono(path: str) -> bytes:
    """Raw little-endian 16-bit mono PCM at 16 kHz (no WAV header) for Cloud Speech LINEAR16."""
    try:
        with wave.open(path, "rb") as wf:
            if wf.getsampwidth() != 2 or wf.getframerate() != 16000 or wf.getnchannels() != 1:
                raise ValueError("not 16-bit 16kHz mono wav")
            return wf.readframes(wf.getnframes())
    except Exception:
        pass
    fd, out_wav = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                path,
                "-ac",
                "1",
                "-ar",
                "16000",
                "-sample_fmt",
                "s16",
                out_wav,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        with wave.open(out_wav, "rb") as wf:
            if wf.getsampwidth() != 2 or wf.getframerate() != 16000 or wf.getnchannels() != 1:
                raise RuntimeError("ffmpeg did not produce 16-bit 16kHz mono wav")
            return wf.readframes(wf.getnframes())
    finally:
        Path(out_wav).unlink(missing_ok=True)


def _latin_letter_run_ratio(text: str) -> float:
    """Share of Latin letter runs vs Ethiopic + Latin letter runs (ignores spaces/punct)."""
    if not text.strip():
        return 0.0
    latin = sum(len(m.group(0)) for m in _latin_letters_re.finditer(text))
    ethiopic = sum(len(m.group(0)) for m in _ethiopic_re.finditer(text))
    denom = latin + ethiopic
    if denom == 0:
        return 0.0
    return latin / denom


def _mixed_script_quality_note(text: str) -> str | None:
    if not text or not _ethiopic_re.search(text):
        return None
    ratio = _latin_letter_run_ratio(text)
    if ratio < 0.08:
        return None
    return (
        "Transcript mixes Latin letters with Amharic; Whisper often does this under noise or accent mismatch. "
        "For consistent Ethiopic output, set STT_BACKEND=gcp and use Google Cloud Speech (am-ET)."
    )


def _maybe_normalize_audio_wav(src: str) -> str:
    """If ffmpeg is available, convert to 16 kHz mono PCM WAV (Whisper-friendly)."""
    if os.getenv("STT_NORMALIZE_AUDIO", "1").strip() in ("0", "false", "False"):
        return src
    if not shutil.which("ffmpeg"):
        return src
    fd, out = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                src,
                "-ac",
                "1",
                "-ar",
                "16000",
                "-sample_fmt",
                "s16",
                out,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return out
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            Path(out).unlink(missing_ok=True)
        except Exception:
            pass
        return src


def _looks_fragmented_gibberish(text: str) -> bool:
    """English note: many tiny tokens / hyphens often mean model is guessing, not transcribing."""
    if len(text) < 25:
        return False
    tokens = [t.strip(".,") for t in text.split() if t.strip()]
    if len(tokens) < 6:
        return False
    shorties = sum(1 for t in tokens if len(t) <= 2)
    if shorties / len(tokens) > 0.35:
        return True
    if text.count("-") >= 4 and len(text) < 250:
        return True
    return False


def _looks_like_repetition_hallucination(text: str) -> bool:
    """Heuristic: Whisper sometimes loops syllables in Ethiopic when audio is noisy/short."""
    if len(text) < 40:
        return False
    if re.search(r"(.)\1{14,}", text):
        return True
    raw = text.encode("utf-8")
    if len(raw) > 80:
        cr = len(raw) / max(1, len(zlib.compress(raw)))
        if cr > 3.5:
            return True
    return False


_model_status: dict[str, Any] = {
    "state": "not_loaded",
    "backend": "faster-whisper",
    "model_id": None,
    "device": None,
    "error": None,
}


def _proto_duration_seconds(d: Any) -> float:
    if d is None:
        return 0.0
    ts = getattr(d, "total_seconds", None)
    if callable(ts):
        return float(ts())
    return float(getattr(d, "seconds", 0)) + float(getattr(d, "nanos", 0)) * 1e-9


def _transcribe_google_cloud(decode_path: str, audio_normalized: bool) -> dict[str, Any]:
    """Google Cloud Speech-to-Text sync recognize, language am-ET (Ethiopic)."""
    try:
        from google.cloud import speech
    except ImportError as exc:
        raise RuntimeError("Install google-cloud-speech for STT_BACKEND=gcp") from exc

    client = speech.SpeechClient()
    pcm = _gather_pcm_s16le_16k_mono(decode_path)
    audio = speech.RecognitionAudio(content=pcm)

    response = None
    last_exc: Exception | None = None
    for enable_words in (True, False):
        try:
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code="am-ET",
                enable_automatic_punctuation=True,
                enable_word_time_offsets=enable_words,
            )
            response = client.recognize(config=config, audio=audio)
            break
        except Exception as exc:
            last_exc = exc
    if response is None:
        raise RuntimeError(
            f"GCP Speech recognize failed after retries: {last_exc!r}"
        ) from last_exc

    text_parts: list[str] = []
    chunks: list[dict[str, Any]] = []
    confidences: list[float] = []
    for res in response.results:
        if not res.alternatives:
            continue
        alt = res.alternatives[0]
        t = (alt.transcript or "").strip()
        if not t:
            continue
        text_parts.append(t)
        if alt.words:
            start = _proto_duration_seconds(alt.words[0].start_time)
            end = _proto_duration_seconds(alt.words[-1].end_time)
        else:
            start, end = 0.0, 0.0
        chunks.append({"timestamp": [start, end], "text": t})
        try:
            confidences.append(float(alt.confidence))
        except (TypeError, ValueError, AttributeError):
            pass

    text = " ".join(text_parts).strip()
    script_ok = bool(_ethiopic_re.search(text))
    conf = sum(confidences) / len(confidences) if confidences else None
    return {
        "text": text,
        "language": "am-ET",
        "active_model_id": "google-cloud-speech:am-ET",
        "requested_model_id": "google-cloud-speech:am-ET",
        "audio_normalized_16k_mono": audio_normalized,
        "confidence": conf,
        "chunks": chunks,
        "is_ethiopic_script": script_ok,
        "warning": None
        if script_ok
        else "No Ethiopic script in GCP transcript; check audio or language.",
        "quality_note_en": None,
        "detected_language": "am",
        "language_probability": None,
        "stt_backend": "google-cloud-speech",
    }


def _transcribe_faster_whisper(decode_path: str, audio_normalized: bool) -> dict[str, Any]:
    model = _get_faster_whisper_model()
    prompt = os.getenv("STT_INITIAL_PROMPT", "").strip() or None

    segments, info = model.transcribe(
        decode_path,
        language="am",
        task="transcribe",
        beam_size=5,
        best_of=5,
        repetition_penalty=1.2,
        no_repeat_ngram_size=4,
        temperature=(0.0, 0.2, 0.4, 0.6),
        compression_ratio_threshold=2.0,
        log_prob_threshold=-0.5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 350},
        condition_on_previous_text=False,
        initial_prompt=prompt,
    )
    seg_list = list(segments)
    text = " ".join(s.text.strip() for s in seg_list).strip()
    chunks = [
        {"timestamp": [float(s.start), float(s.end)], "text": s.text}
        for s in seg_list
    ]

    if text and not _ethiopic_re.search(text):
        fb_text, fb_chunks = _hf_fallback_transcribe(decode_path)
        if _ethiopic_re.search(fb_text):
            text, chunks = fb_text, fb_chunks

    script_ok = bool(_ethiopic_re.search(text))
    active = _model_status.get("model_id")
    rep_warn = _looks_like_repetition_hallucination(text)
    frag = _looks_fragmented_gibberish(text)
    gibberish_note = None
    if frag:
        gibberish_note = (
            "This looks like fragmented / unreliable Amharic (not a clean sentence). "
            "Common causes: noisy audio, wrong mic level, stereo/odd sample rate, or speech not matching file. "
            "Try: record 16kHz mono WAV in a quiet room, or use Google Cloud Speech-to-Text (am-ET) for production."
        )
    mixed_note = _mixed_script_quality_note(text)
    quality_note_en = gibberish_note or mixed_note
    warning = None
    if not script_ok:
        warning = "Transcription not Ethiopic script; improve audio quality or retry."
    elif rep_warn:
        warning = "Possible repetition hallucination; re-record clearer audio or normalize to 16kHz mono."
    elif frag:
        warning = gibberish_note
    elif mixed_note:
        warning = mixed_note

    return {
        "text": text,
        "language": "am-ET",
        "active_model_id": active,
        "requested_model_id": _model_status.get("requested_model_id"),
        "audio_normalized_16k_mono": audio_normalized,
        "confidence": None,
        "chunks": chunks,
        "is_ethiopic_script": script_ok,
        "warning": warning,
        "quality_note_en": quality_note_en,
        "detected_language": getattr(info, "language", None),
        "language_probability": getattr(info, "language_probability", None),
        "stt_backend": "faster-whisper",
    }


def _get_faster_whisper_model():
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        try:
            import torch
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "Missing dependencies. Install: pip install faster-whisper"
            ) from exc

        # Best practical default for Amharic: large-v3 CTranslate2 (Systran).
        # If cache is incomplete, delete .../models--Systran--faster-whisper-large-v3 and re-download.
        requested_model_id = os.getenv("STT_MODEL_ID", "Systran/faster-whisper-large-v3")
        model_id = requested_model_id
        if model_id.startswith("openai/"):
            # faster-whisper expects CTranslate2 model names, not HF repo names.
            model_id = "large-v3"
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        local_only = os.getenv("STT_LOCAL_FILES_ONLY", "0").strip() in ("1", "true", "True")
        _model_status["state"] = "loading"
        _model_status["model_id"] = model_id
        _model_status["requested_model_id"] = requested_model_id
        _model_status["device"] = device
        _model_status["error"] = None
        try:
            _model = WhisperModel(
                model_id,
                device=device,
                compute_type=compute_type,
                local_files_only=local_only,
            )
            _model_status["state"] = "ready"
            return _model
        except Exception as exc:
            # Common on Windows when an earlier download was interrupted and cache is incomplete.
            _model_status["state"] = "error"
            _model_status["error"] = str(exc)

            fallback_id = "Systran/faster-whisper-medium"
            if model_id != fallback_id:
                _model_status["state"] = "loading"
                _model_status["model_id"] = fallback_id
                _model_status["error"] = None
                _model = WhisperModel(
                    fallback_id,
                    device=device,
                    compute_type=compute_type,
                    local_files_only=local_only,
                )
                _model_status["state"] = "ready"
                return _model
            raise


def _hf_fallback_transcribe(path: str) -> tuple[str, list[dict[str, Any]]]:
    try:
        from transformers import pipeline
        import torch
    except ImportError as exc:
        raise RuntimeError("Fallback requires transformers + torch") from exc

    model_id = os.getenv("HF_STT_MODEL_ID", "openai/whisper-large-v3-turbo")
    has_cuda = torch.cuda.is_available()
    device = 0 if has_cuda else -1
    dtype = torch.float16 if has_cuda else torch.float32
    pipe = pipeline(
        "automatic-speech-recognition",
        model=model_id,
        device=device,
        dtype=dtype,
    )
    result = pipe(
        path,
        generate_kwargs={"language": "am", "task": "transcribe"},
        return_timestamps=True,
    )
    return (result.get("text") or "").strip(), result.get("chunks") or []


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/model-status")
def model_status() -> dict[str, Any]:
    out = dict(_model_status)
    out["stt_backend_env"] = os.getenv("STT_BACKEND", "whisper")
    out["gcp_credentials_available"] = _gcp_credentials_available()
    return out


def preload_model() -> None:
    """Deprecated: kept for compatibility. Lifespan handles preload."""
    return None


@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)) -> dict[str, Any]:
    suffix = Path(audio.filename or "input.wav").suffix or ".wav"
    tmp_path: str | None = None
    decode_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
            content = await audio.read()
            if not content:
                raise HTTPException(status_code=400, detail="Uploaded file is empty.")
            tmp.write(content)

        decode_path = _maybe_normalize_audio_wav(tmp_path)
        audio_normalized = decode_path != tmp_path

        choice = _stt_backend_choice()
        gcp_ok = _gcp_credentials_available()
        use_gcp = choice == "gcp" or (choice == "auto" and gcp_ok)

        if use_gcp:
            try:
                return _transcribe_google_cloud(decode_path, audio_normalized)
            except Exception as gcp_exc:
                if choice == "gcp":
                    raise HTTPException(
                        status_code=502,
                        detail=(
                            "Google Cloud Speech failed. Check GOOGLE_APPLICATION_CREDENTIALS, "
                            f"billing, and Speech-to-Text API: {gcp_exc}"
                        ),
                    ) from gcp_exc
                # auto: fall through to Whisper

        try:
            return _transcribe_faster_whisper(decode_path, audio_normalized)
        except Exception as whisper_exc:
            _model_status["state"] = "error"
            _model_status["error"] = str(whisper_exc)
            raise HTTPException(
                status_code=500, detail=f"Transcription failed: {whisper_exc}"
            ) from whisper_exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc
    finally:
        if decode_path and tmp_path and decode_path != tmp_path:
            try:
                Path(decode_path).unlink(missing_ok=True)
            except Exception:
                pass
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass

