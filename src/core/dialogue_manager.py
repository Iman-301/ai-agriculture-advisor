"""FR-05 — Multi-turn dialogue orchestration."""

from __future__ import annotations

from typing import Any

from ..data.farmer_repository import FarmerRepository
from ..data.session_store import SessionStore
from ..models.call_session import CallSession, ResponseBundle
from ..models.farmer_profile import InteractionRecord
from ..services.nlu_service import RuleBasedNLUService
from ..utils.logger import audit_event, get_logger
from .decision_layer import DecisionLayer
from .response_builder import ResponseBuilder
from .safety_guard import SafetyGuard


class DialogueManager:
    def __init__(
        self,
        nlu: RuleBasedNLUService,
        decision: DecisionLayer,
        sessions: SessionStore,
        farmers: FarmerRepository,
        safety: SafetyGuard,
        builder: ResponseBuilder,
    ) -> None:
        self._nlu = nlu
        self._decision = decision
        self._sessions = sessions
        self._farmers = farmers
        self._safety = safety
        self._builder = builder
        self._log = get_logger(__name__)

    def process_text(
        self,
        session_id: str,
        phone_number: str,
        user_text: str,
        asr_confidence: float | None = None,
    ) -> ResponseBundle:
        session = self._sessions.get_or_create(session_id, phone_number)
        session.state.turn_count += 1

        profile = self._farmers.get_by_phone(phone_number)
        if profile:
            session.farmer_profile_id = profile.profile_id

        session_ctx: dict[str, Any] = {
            "crop": session.state.current_crop,
            "location": session.state.current_location,
        }
        nlu = self._nlu.parse(user_text, session_context=session_ctx, asr_confidence=asr_confidence)

        if profile and not session.state.current_location and profile.location.region:
            session.state.current_location = profile.location.region

        crop = nlu["entities"].get("crop")
        loc = nlu["entities"].get("location")
        if crop:
            session.state.current_crop = crop
        if loc:
            session.state.current_location = loc
        session.state.current_intent = nlu["intent"]

        audit_event(
            self._log,
            "turn",
            {
                "session_id": session_id,
                "intent": nlu["intent"],
                "confidence": nlu["confidence"],
            },
        )

        if nlu["missing_slots"] and nlu["intent"] not in (
            "greeting",
            "goodbye",
            "help",
            "repeat",
            "general",
        ):
            slot = nlu["missing_slots"][0]
            if slot == "crop":
                msg = "የትኛውን ተክል እንደሚመለከት ይንገሩኝ (ለምሳሌ ጤፍ፣ ስንዴ፣ በቆሎ)።"
            elif slot == "commodity_or_location":
                msg = "የትኛውን ምርት ወይም የት ያለ ገበያ እንደሚፈልጉ ይንገሩኝ።"
            else:
                msg = "እባክዎ ጥያቄዎን በአጭር ይድገሙ።"
            bundle = ResponseBundle(text=msg, confidence=0.5, strategy_name="CLARIFY")
            session.last_response = self._builder.finalize(bundle)
            return session.last_response

        decision_ctx: dict[str, Any] = {
            "intent": nlu["intent"],
            "nlu": nlu,
            "nlu_confidence": nlu["confidence"],
            "question": user_text,
            "last_response_text": session.last_response.text if session.last_response else None,
        }

        draft = self._decision.decide(decision_ctx)
        safe = self._safety.apply(draft, nlu, session.state)
        final = self._builder.finalize(safe)
        session.last_response = final

        if profile:
            self._farmers.append_interaction(
                phone_number,
                InteractionRecord(
                    intent=nlu["intent"],
                    crop=session.state.current_crop,
                    response_strategy=final.strategy_name,
                ),
            )

        return final
