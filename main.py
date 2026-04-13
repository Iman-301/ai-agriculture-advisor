"""FR-01 + FR-14: FastAPI + Twilio webhooks for voice advisory system."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config import settings

from fastapi import FastAPI, Form, Request
from fastapi.responses import PlainTextResponse, Response

from src.core.decision_layer import DecisionLayer
from src.core.dialogue_manager import DialogueManager
from src.core.response_builder import ResponseBuilder
from src.core.safety_guard import SafetyGuard
from src.data.farmer_repository import FarmerRepository
from src.data.knowledge_base import KnowledgeBaseRepository
from src.data.market_data import MarketDataRepository
from src.data.session_store import SessionStore
from src.services.nlu_service import RuleBasedNLUService
from src.services.rag_service import RAGService
from src.services.tts_service import GTTSService

app = FastAPI(title="Agri Voice Advisory", version="0.1.0")

_kb = KnowledgeBaseRepository(settings.knowledge_base_path)
_market = MarketDataRepository(settings.market_prices_path)
_farmers = FarmerRepository(settings.farmer_profiles_path)
_rag = RAGService(_kb, _market, top_k=settings.rag_top_k)
_decision = DecisionLayer(
    rag_min_confidence=settings.nlu_confidence_rag_min,
    rag_service=_rag,
)
_dialogue = DialogueManager(
    nlu=RuleBasedNLUService(),
    decision=_decision,
    sessions=SessionStore(),
    farmers=_farmers,
    safety=SafetyGuard(),
    builder=ResponseBuilder(),
)
_tts = GTTSService(lang="am")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/voice/incoming")
async def voice_incoming(request: Request) -> PlainTextResponse:
    """FR-01: Caller Interface - Initial greeting and prompt.
    
    This endpoint is called when a farmer dials the Twilio number.
    Returns TwiML with Amharic greeting and triggers ASR.
    """
    base = str(request.base_url).rstrip("/")
    
    print("📞 Incoming call received!")
    print(f"   Base URL: {base}")
    
    # NOTE: Twilio's <Say> doesn't support Amharic (am-ET)
    # We use <Play> with pre-generated audio files instead
    # For now, using English as fallback until we set up audio hosting
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say language="en-US">Welcome to the agricultural advisory system. Please ask your farming question in Amharic.</Say>
  <Gather input="speech" timeout="10" language="am-ET" speechTimeout="auto" action="{base}/voice/process" method="POST">
    <Say language="en-US">Please speak now.</Say>
  </Gather>
  <Say language="en-US">No input detected. Trying again.</Say>
  <Redirect method="POST">{base}/voice/incoming</Redirect>
</Response>"""
    return PlainTextResponse(twiml, media_type="application/xml")


@app.post("/voice/process")
async def voice_process(
    request: Request,
    CallSid: str = Form(""),
    From: str = Form("+251900000000"),
    SpeechResult: str = Form(""),
    Digits: str = Form(""),
    Confidence: str = Form("0.0"),
) -> PlainTextResponse:
    """FR-01 + FR-14: Process farmer's question and deliver voice response.
    
    This endpoint:
    - Receives ASR transcription from Twilio (FR-03)
    - Processes through dialogue manager (FR-04, FR-05)
    - Generates response (FR-10, FR-11, FR-12, FR-13)
    - Delivers via TTS (FR-14)
    """
    session_id = CallSid or "twilio_session"
    base = str(request.base_url).rstrip("/")
    
    print(f"🎤 Processing input from {From}")
    print(f"   Speech: '{SpeechResult}'")
    print(f"   Digits: '{Digits}'")
    print(f"   Confidence: {Confidence}")
    
    # FR-01: Handle DTMF input (optional repeat/confirmation)
    if Digits == "1":
        user_text = "repeat"
    elif Digits:
        # Ignore other digits (like trial account confirmation "2")
        print(f"   ⚠️ Ignoring unexpected digit: {Digits}")
        user_text = ""
    else:
        user_text = (SpeechResult or "").strip()
        
        # FR-01: Handle silence/no input
        if not user_text:
            print("   ⚠️ No speech detected, prompting again")
            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say language="am-ET">እባክዎ ጥያቄዎን ይድገሙ።</Say>
  <Gather input="speech" timeout="10" language="am-ET" speechTimeout="auto" action="{base}/voice/process" method="POST">
    <Say language="am-ET">እባክዎ ጥያቄዎን ይጠይቁ።</Say>
  </Gather>
  <Redirect method="POST">{base}/voice/incoming</Redirect>
</Response>"""
            return PlainTextResponse(twiml, media_type="application/xml")
    
    # FR-03: Check ASR confidence
    asr_confidence = float(Confidence) if Confidence else 0.0
    if asr_confidence < settings.asr_confidence_threshold and user_text != "repeat":
        print(f"   ⚠️ Low confidence ({asr_confidence}), asking to repeat")
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say language="am-ET">ዝቅተኛ ትክክለኛነት። እባክዎ ጥያቄዎን ይድገሙ።</Say>
  <Gather input="speech" timeout="10" language="am-ET" speechTimeout="auto" action="{base}/voice/process" method="POST">
    <Say language="am-ET">እባክዎ ጥያቄዎን ይጠይቁ።</Say>
  </Gather>
  <Redirect method="POST">{base}/voice/incoming</Redirect>
</Response>"""
        return PlainTextResponse(twiml, media_type="application/xml")
    
    # FR-04, FR-05, FR-10, FR-11, FR-12, FR-13: Process through dialogue manager
    print(f"   ✓ Processing: '{user_text}'")
    bundle = _dialogue.process_text(session_id, From, user_text, asr_confidence=asr_confidence)
    print(f"   ✓ Response: '{bundle.text}'")
    
    # FR-14: Generate TwiML response with TTS
    twiml = _tts.get_twiml_response(bundle.text, next_action_url=f"{base}/voice/process")
    
    return PlainTextResponse(twiml, media_type="application/xml")


@app.get("/")
def root() -> Response:
    return Response("Agri Voice Advisory API. POST /voice/incoming for Twilio.", media_type="text/plain")
