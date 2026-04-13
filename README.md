# AI Agriculture Advisor (Agri Voice System)

A voice-based advisory system designed to allow Ethiopian farmers to access agronomic advice and market prices using any basic mobile phone via a multi-turn Amharic spoken interface.

## Current Implementation Status

This repository contains the foundational backend logic for the advisory system, covering several core functional requirements from the SRS:

*   **Telephony & API Webhooks:** A FastAPI application prepared to accept incoming call webhooks (e.g., Twilio). Currently uses a mock telephony service for development.
*   **Dialogue & State Management:** Tracks multi-turn sessions, context (crop, location), and manages follow-up questions or missing slot clarifications.
*   **NLU & Decision Layer:** Identifies user intent and extracts entities. Chooses response strategies (RAG, Static, Fallback).
*   **Retrieval-Augmented Generation (RAG):** Retrieves relevant context from a validated knowledge base and market data repositories to construct grounded answers.
*   **Safety Guardrails:** Intercepts high-risk topics (e.g., chemical usage) to ensure the system provides safe, conservative advice or triggers confirmation prompts.
*   **Data Layer:** Ingests mock data for farmer profiles, market prices, and agronomy knowledge bases to simulate production databases.

## Project Structure

*   **`src/`**: Core application logic.
    *   **`core/`**: Dialogue manager, decision layer, safety guard, and response builder.
    *   **`services/`**: Implementations for NLU, RAG, and Telephony.
    *   **`data/`**: Repositories for farmers, knowledge base, market data, and session states.
    *   **`cli/`**: Command-line interfaces for testing without phone setups.
    *   **`models/`**: Pydantic data models.
*   **`data/`**: Storage for mock JSON data, audio, and documents.
*   **`tests/`**: Unit tests for RAG, Dialog Manager, and Data parsing.

## Installation

1. Make sure you have Python 3.9+ installed.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

### 0. Dedicated STT/TTS services (recommended first)

Run STT and TTS independently to validate Amharic speech flow before telephony.

1) Start STT service:
```bash
python -m uvicorn stt_service.main:app --host 0.0.0.0 --port 8001
```

2) Start TTS service:
```bash
python -m uvicorn tts_service.main:app --host 0.0.0.0 --port 8002
```

3) Test STT (Amharic WAV -> text):
```bash
curl -X POST "http://127.0.0.1:8001/transcribe" -F "audio=@sample_amharic.wav"
```

4) Test TTS (Amharic text -> MP3):
```bash
curl -X POST "http://127.0.0.1:8002/synthesize" \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"ሰላም፣ ይህ የሙከራ የድምፅ መልዕክት ነው።\",\"lang\":\"am\"}" \
  --output speech.mp3
```

Requirements for STT/TTS:
- `pip install -r requirements.txt`
- For STT: install [FFmpeg](https://ffmpeg.org/download.html) and add to PATH.
- First STT run downloads `openai/whisper-small` model from Hugging Face.
- TTS uses `gTTS`, so internet access is required.

### 1. Voice CLI (Speech-to-Speech)
Test the full voice pipeline with speech recognition and text-to-speech:
```bash
python -m src.cli.voice_cli
```

**Important Notes:**
- **ASR (Speech Recognition):** Set `GROQ_API_KEY` in `.env` for free Whisper ASR
  - ⚠️ **Amharic Limitation:** Whisper has limited Amharic support. Transcription accuracy may be poor for Amharic speech.
  - For testing, consider using mock ASR (remove `GROQ_API_KEY` from `.env`)
- **TTS (Text-to-Speech):** Uses gTTS (free, no API key needed)
  - Requires: `pip install gtts pygame`
  - Speaks responses in Amharic through your speakers

**Mock ASR Testing:**
```bash
# Remove GROQ_API_KEY from .env, then:
python -m src.cli.voice_cli
# Press Enter (no file path) to use mock Amharic questions
```

### 2. Web Service (FastAPI)
Run the API server which will act as the webhook endpoint for telephony providers (like Twilio):
```bash
uvicorn main:app --reload
```
*   **API Docs:** Once running, navigate to `http://localhost:8000/docs`.
*   **Health Check:** `http://localhost:8000/health`



### 3. Text CLI Mode
You can interact with the conversational logic locally via the terminal:
```bash
python src/cli/chatbot_cli.py
```



## Running Tests

Automated tests are built using `pytest`. They cover the dialogue manager rules, mock data loading, and RAG retrieval accuracy.

```bash
pytest tests/ -v
```
