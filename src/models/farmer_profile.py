"""SDS §5.2 — Farmer profile, location, interaction history, references."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class Location:
    region: Optional[str] = None
    zone: Optional[str] = None
    woreda: Optional[str] = None
    kebele: Optional[str] = None

    def as_short_string(self) -> str:
        parts = [self.region, self.zone, self.woreda]
        return ", ".join(p for p in parts if p)


@dataclass
class Reference:
    """Provenance for RAG / market answers."""

    ref_id: str
    label: str
    kind: str  # "kb_doc" | "market" | "template"
    snippet: Optional[str] = None


@dataclass
class InteractionRecord:
    intent: str
    crop: Optional[str]
    response_strategy: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    notes: Optional[str] = None


@dataclass
class FarmerProfile:
    profile_id: str
    phone_e164: str
    display_name: Optional[str] = None
    national_id: Optional[str] = None
    location: Location = field(default_factory=Location)
    preferred_crops: list[str] = field(default_factory=list)
    language_pref: str = "am"
    interaction_history: list[InteractionRecord] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
