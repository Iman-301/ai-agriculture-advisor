"""FR-14 — Voice Response Delivery (TTS Streaming + Barge-in)."""

from __future__ import annotations

from pathlib import Path

from ..application.ports import TTSPort


class MockTTSService(TTSPort):
    def synthesize_to_file(self, text: str, out_path: str) -> str:
        path = Path(out_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"[TTS mock] {text}\n", encoding="utf-8")
        return str(path.resolve())


class GTTSService(TTSPort):
    """FR-14: Google Translate TTS — free, no API key, supports Amharic.
    
    Implements FR-14 requirements:
    - Text-to-Speech conversion (Step 1)
    - Audio streaming to caller (Step 2)
    - Playback control (Step 4)
    
    Note: Barge-in (Step 3) is handled by telephony layer (Twilio).
    """

    def __init__(self, lang: str = "am", slow: bool = False) -> None:
        """Initialize Amharic TTS service.
        
        Args:
            lang: Language code (default: "am" for Amharic)
            slow: Speak slowly for better clarity (default: False)
        """
        self._lang = lang
        self._slow = slow

    def synthesize_to_file(self, text: str, out_path: str) -> str:
        """FR-14 Step 1: Request TTS synthesis.
        
        Converts text to speech and saves to file.
        
        Args:
            text: Amharic text to synthesize
            out_path: Output file path
            
        Returns:
            Absolute path to generated audio file
        """
        try:
            from gtts import gTTS
        except ImportError as e:
            raise RuntimeError("Run: pip install gtts") from e

        path = Path(out_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # FR-14: Synthesize Amharic speech
        tts = gTTS(text=text, lang=self._lang, slow=self._slow)
        tts.save(str(path))
        return str(path.resolve())

    def synthesize_and_play(self, text: str) -> None:
        """FR-14 Step 2: Stream audio to caller (local playback for testing).
        
        Synthesizes and plays audio immediately.
        In production, this would stream to Twilio.
        
        Args:
            text: Amharic text to speak
        """
        try:
            from gtts import gTTS
            import pygame
            import tempfile
        except ImportError as e:
            raise RuntimeError("Run: pip install gtts pygame") from e

        # FR-14 Step 1: Synthesize
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name

        tts = gTTS(text=text, lang=self._lang, slow=self._slow)
        tts.save(tmp_path)

        # FR-14 Step 2: Play audio (simulates streaming to caller)
        pygame.mixer.init()
        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()

        # FR-14 Step 4: Wait for playback completion
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

        pygame.mixer.quit()
        Path(tmp_path).unlink(missing_ok=True)

    def get_twiml_response(self, text: str, next_action_url: str = "/voice/process") -> str:
        """FR-14: Generate TwiML for Twilio telephony integration.
        
        Creates TwiML that:
        - Speaks the response in Amharic (Step 2)
        - Supports barge-in via Gather (Step 3)
        - Prompts for follow-up (Step 4)
        
        Args:
            text: Amharic response text
            next_action_url: URL for next user input
            
        Returns:
            TwiML XML string
        """
        from xml.sax.saxutils import escape
        
        # Escape XML special characters
        safe_text = escape(text)
        
        # FR-14: TwiML with Amharic TTS + barge-in support
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say language="am-ET">{safe_text}</Say>
  <Gather input="speech" language="am-ET" action="{escape(next_action_url)}" method="POST" timeout="5" />
  <Redirect method="POST">/voice/incoming</Redirect>
</Response>"""
        return twiml


class GoogleCloudTTSService(TTSPort):
    """FR-14: Google Cloud Text-to-Speech — best quality Amharic, requires credentials.
    
    Implements FR-14 with high-quality Wavenet voices.
    Requires Google Cloud account + credentials.
    """

    def __init__(self, credentials_path: str, voice_name: str = "am-ET-Wavenet-A") -> None:
        """Initialize Google Cloud TTS.
        
        Args:
            credentials_path: Path to Google Cloud credentials JSON
            voice_name: Amharic voice to use (default: am-ET-Wavenet-A)
        """
        self._credentials_path = credentials_path
        self._voice_name = voice_name

    def synthesize_to_file(self, text: str, out_path: str) -> str:
        """FR-14 Step 1: Request TTS synthesis with Google Cloud."""
        try:
            from google.cloud import texttospeech
            import os
        except ImportError as e:
            raise RuntimeError("Run: pip install google-cloud-texttospeech") from e

        # Set credentials
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self._credentials_path

        client = texttospeech.TextToSpeechClient()

        # Configure Amharic voice
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="am-ET",
            name=self._voice_name,
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )
        
        # Optimize for telephone quality (16kHz)
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            sample_rate_hertz=16000,
            speaking_rate=0.9  # Slightly slower for clarity
        )

        # Synthesize
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        # Save to file
        path = Path(out_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(response.audio_content)
        
        return str(path.resolve())

    def synthesize_and_play(self, text: str) -> None:
        """FR-14 Step 2: Stream audio to caller (local playback for testing)."""
        try:
            import pygame
            import tempfile
        except ImportError as e:
            raise RuntimeError("Run: pip install pygame") from e

        # Synthesize to temp file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name
        
        self.synthesize_to_file(text, tmp_path)

        # Play audio
        pygame.mixer.init()
        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

        pygame.mixer.quit()
        Path(tmp_path).unlink(missing_ok=True)
