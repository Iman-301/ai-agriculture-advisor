"""FR-03 — ASR adapter; mock for tests, Groq Whisper for real use."""

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
            "የጤፍ ማዳበሪያ መጠን ምን ያህል ነው?",
            "የስንዴ ዋጋ በአዲስ አበባ ስንት ነው?",
        ]
        text = samples[rng.randint(0, len(samples) - 1)]
        return {"text": text, "confidence": 0.75 + rng.random() * 0.2, "language": language_hint or "am"}


class GoogleCloudASRService(ASRPort):
    """Google Cloud Speech-to-Text — best Amharic support, requires credentials."""

    def __init__(self, credentials_path: str) -> None:
        self._credentials_path = credentials_path

    def transcribe(self, audio_path: str, language_hint: str | None = "am") -> dict[str, Any]:
        try:
            from google.cloud import speech
            import os
        except ImportError as e:
            raise RuntimeError("Run: pip install google-cloud-speech") from e

        # Set credentials
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self._credentials_path

        client = speech.SpeechClient()

        # Read audio file
        with open(audio_path, "rb") as audio_file:
            content = audio_file.read()

        audio = speech.RecognitionAudio(content=content)
        
        # Configure recognition
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="am-ET" if language_hint == "am" else language_hint,
            enable_automatic_punctuation=True,
            model="default",
        )

        # Perform recognition
        response = client.recognize(config=config, audio=audio)

        if not response.results:
            return {"text": "", "confidence": 0.0, "language": language_hint or "am"}

        # Get best result
        result = response.results[0]
        alternative = result.alternatives[0]
        
        return {
            "text": alternative.transcript,
            "confidence": alternative.confidence,
            "language": language_hint or "am"
        }


class GroqASRService(ASRPort):
    """Groq-hosted Whisper — free tier, install `groq` and set GROQ_API_KEY."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def transcribe(self, audio_path: str, language_hint: str | None = "am") -> dict[str, Any]:
        try:
            from groq import Groq
        except ImportError as e:
            raise RuntimeError("Run: pip install groq") from e

        client = Groq(api_key=self._api_key)
        
        # Amharic agricultural context prompt to help Whisper
        # Note: Whisper has limited Amharic support - transcription quality may be poor
        prompt = "ጤፍ ስንዴ በቆሎ ማዳበሪያ ዩሪያ DAP NPS በሽታ ተባይ ዝገት መዝራት መከር ዋጋ"
        
        try:
            with open(audio_path, "rb") as f:
                tr = client.audio.transcriptions.create(
                    model="whisper-large-v3",
                    file=f,
                    language="am",  # Force Amharic
                    prompt=prompt,
                    response_format="verbose_json",
                    temperature=0.0,
                )
            text = getattr(tr, "text", str(tr))
            
            # If transcription looks like English/gibberish, warn user
            if text and not any(ord(c) >= 0x1200 and ord(c) <= 0x137F for c in text):
                print(f"⚠️  Warning: Transcription doesn't contain Amharic characters.")
                print(f"   Whisper may have poor Amharic recognition for this audio.")
                
            return {"text": text, "confidence": 0.88, "language": "am"}
        except Exception as e:
            raise RuntimeError(f"Groq transcription failed: {e}") from e

class ElevenLabsASRService(ASRPort):
    """ElevenLabs Scribe API (Speech-to-Text) for high-quality Amharic transcription."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def transcribe(self, audio_path: str, language_hint: str | None = "am") -> dict[str, Any]:
        try:
            import requests
        except ImportError as e:
            raise RuntimeError("Run: pip install requests") from e

        url = "https://api.elevenlabs.io/v1/speech-to-text"
        headers = {
            "xi-api-key": self._api_key
        }
        
        # ElevenLabs 'scribe_v1' is their official speech-to-text model. 
        data = {
            "model_id": "scribe_v1",
            "language_code": "am",    # force Amharic
            "diarize": "false"
        }
        
        try:
            with open(audio_path, "rb") as audio_file:
                files = {"file": audio_file}
                response = requests.post(url, headers=headers, data=data, files=files)
            
            response.raise_for_status()
            result = response.json()
            
            text = result.get("text", "")
            return {"text": text, "confidence": 0.95, "language": "am"}
            
        except Exception as e:
            raise RuntimeError(f"ElevenLabs transcription failed: {e}") from e


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
