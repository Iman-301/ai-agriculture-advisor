"""FR-15–FR-17 — Farmer profiles (mock JSON backend)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from ..models.farmer_profile import FarmerProfile, InteractionRecord, Location


class FarmerRepository:
    def __init__(self, json_path: Path | str) -> None:
        self._path = Path(json_path)
        self._by_phone: dict[str, FarmerProfile] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        with self._path.open(encoding="utf-8") as f:
            data = json.load(f)
        for raw in data.get("farmers", []):
            loc = raw.get("location") or {}
            profile = FarmerProfile(
                profile_id=raw["profile_id"],
                phone_e164=raw["phone_e164"],
                display_name=raw.get("display_name"),
                national_id=raw.get("national_id"),
                location=Location(
                    region=loc.get("region"),
                    zone=loc.get("zone"),
                    woreda=loc.get("woreda"),
                    kebele=loc.get("kebele"),
                ),
                preferred_crops=list(raw.get("preferred_crops") or []),
                language_pref=raw.get("language_pref", "am"),
            )
            self._by_phone[profile.phone_e164] = profile

    def get_by_phone(self, phone_e164: str) -> Optional[FarmerProfile]:
        return self._by_phone.get(phone_e164)

    def append_interaction(self, phone_e164: str, record: InteractionRecord) -> None:
        p = self._by_phone.get(phone_e164)
        if p:
            p.interaction_history.append(record)
