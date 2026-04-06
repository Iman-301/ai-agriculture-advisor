"""SDS §5.2 — CallSession, SessionState, ResponseBundle."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from .farmer_profile import Reference


@dataclass
class SessionState:
    """Composition-owned dialogue state for one call."""

    current_intent: Optional[str] = None
    current_crop: Optional[str] = None
    current_location: Optional[str] = None
    pending_confirmation: Optional[str] = None
    missing_slots: list[str] = field(default_factory=list)
    turn_count: int = 0
    last_nlu_ambiguous: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResponseBundle:
    """Aggregated response for TTS, audit, and repeat-last-answer."""

    text: str
    references: list[Reference] = field(default_factory=list)
    confidence: float = 1.0
    strategy_name: str = "UNKNOWN"
    safety_flags: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def primary_reference_labels(self) -> list[str]:
        return [r.label for r in self.references]


@dataclass
class CallSession:
    """Central runtime object for one phone interaction."""

    session_id: str
    phone_number: str
    state: SessionState = field(default_factory=SessionState)
    last_response: Optional[ResponseBundle] = None
    farmer_profile_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
