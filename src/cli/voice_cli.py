"""Voice pipeline: ASR (Groq Whisper / mock) → advisory pipeline."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config import settings

from src.cli.chatbot_cli import build_system
from src.services.asr_service import GoogleCloudASRService, GroqASRService, MockASRService, WhisperASRService, ElevenLabsASRService
from src.services.tts_service import GTTSService, MockTTSService


def main() -> None:
    dm = build_system()

    # Initialize ASR with fallback priority: ElevenLabs > Google Cloud > Groq > OpenAI > Mock
    asr_service = None
    
    if settings.elevenlabs_api_key:
        try:
            asr_service = ElevenLabsASRService(settings.elevenlabs_api_key)
            print("Using ElevenLabs 'scribe_v1' Speech-to-Text (excellent Amharic support).")
        except Exception as e:
            print(f"ElevenLabs ASR failed to initialize: {e}")
            asr_service = None

    if asr_service is None and settings.google_application_credentials:
        try:
            asr_service = GoogleCloudASRService(settings.google_application_credentials)
            print("Using Google Cloud Speech-to-Text (best Amharic support).")
        except Exception as e:
            print(f"Google Cloud ASR failed to initialize: {e}")
            asr_service = None
    
    if asr_service is None and settings.groq_api_key:
        asr_service = GroqASRService(settings.groq_api_key)
        print("Using Groq Whisper ASR (limited Amharic support).")
    elif asr_service is None and settings.openai_api_key:
        asr_service = WhisperASRService(settings.openai_api_key)
        print("Using OpenAI Whisper ASR (limited Amharic support).")
    
    if asr_service is None:
        asr = MockASRService()
        print("Using mock ASR (set ELEVENLABS_API_KEY for real Amharic recognition).")
    else:
        asr = asr_service

    # Initialize TTS
    try:
        tts = GTTSService(lang="am")
        print("Using gTTS for text-to-speech (Amharic).")
    except RuntimeError:
        tts = MockTTSService()
        print("Using mock TTS (install gtts and pygame for real speech).")

    session_id = "voice_cli"
    phone = "+251900000000"
    
    # Track if we've fallen back to mock
    using_mock_fallback = False

    print("Voice CLI. Enter path to a .wav/.mp3/.m4a file, or type 'mock' for mock mode.")
    while True:
        path = input("\nAudio file path (or 'quit'): ").strip()
        if path.lower() in ("quit", "exit"):
            break
        
        # Handle mock mode
        if not path or path.lower() == "mock":
            # Switch to mock ASR temporarily
            print("Using mock ASR for this query...")
            mock_asr = MockASRService()
            mock_path = str(Path(tempfile.gettempdir()) / "agri_voice_dummy.wav")
            try:
                result = mock_asr.transcribe(mock_path)
                text = result["text"]
                conf = float(result.get("confidence", 0.0))
                print(f"Mock ASR ({conf:.2f}): {text}")
            except Exception as e:
                print(f"Mock ASR error: {e}")
                continue
        else:
            # Use real ASR with the provided file
            # Try transcription with fallback to mock on error
            try:
                result = asr.transcribe(path)
                text = result["text"]
                conf = float(result.get("confidence", 0.0))
                print(f"ASR ({conf:.2f}): {text}")
            except Exception as e:
                if not using_mock_fallback and not isinstance(asr, MockASRService):
                    print(f"\n⚠️  ASR Error: {e}")
                    print("Falling back to mock ASR for this session...")
                    asr = MockASRService()
                    using_mock_fallback = True
                    # Retry with mock
                    try:
                        result = asr.transcribe(path)
                        text = result["text"]
                        conf = float(result.get("confidence", 0.0))
                        print(f"ASR ({conf:.2f}): {text}")
                    except Exception as mock_err:
                        print(f"Mock ASR also failed: {mock_err}")
                        continue
                else:
                    print(f"ASR Error: {e}")
                    continue

        if conf < settings.asr_confidence_threshold:
            print("ዝቅተኛ ትክክለኛነት — እባክዎ ጥያቄዎን ይድገሙ።")
            continue

        bundle = dm.process_text(session_id, phone, text, asr_confidence=conf)
        print(f"Bot: {bundle.text}")
        
        # Synthesize and play the response
        if isinstance(tts, GTTSService):
            try:
                print("Playing audio response...")
                tts.synthesize_and_play(bundle.text)
            except Exception as e:
                print(f"TTS playback error: {e}")
        else:
            print("(Mock TTS - no audio playback)")


if __name__ == "__main__":
    main()
