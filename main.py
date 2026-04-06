"""Phase 5 — FastAPI + Twilio webhooks (mock-friendly; wire real Twilio in production)."""

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
from src.services.telephony_service import MockTelephonyService

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
_telephony = MockTelephonyService()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/voice/incoming")
async def voice_incoming(request: Request) -> PlainTextResponse:
    base = str(request.base_url).rstrip("/")
    twiml = _telephony.build_incoming_twiml(base)
    return PlainTextResponse(twiml, media_type="application/xml")


@app.post("/voice/process")
async def voice_process(
    CallSid: str = Form(""),
    From: str = Form("+251900000000"),
    SpeechResult: str = Form(""),
) -> PlainTextResponse:
    session_id = CallSid or "twilio_session"
    bundle = _dialogue.process_text(session_id, From, SpeechResult or "")
    # Escape XML for Twilio <Say>
    safe = (
        bundle.text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say language="en-GB">{safe}</Say>
  <Gather input="speech" language="am-ET" action="voice/process" method="POST" />
  <Redirect method="POST">voice/incoming</Redirect>
</Response>"""
    return PlainTextResponse(twiml, media_type="application/xml")


@app.get("/")
def root() -> Response:
    return Response("Agri Voice Advisory API. POST /voice/incoming for Twilio.", media_type="text/plain")
