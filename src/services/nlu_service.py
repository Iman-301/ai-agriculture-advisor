"""FR-04 — Intent + entity extraction (rule-based; swap for LLM)."""

from __future__ import annotations

import re
from typing import Any

from ..application.ports import NLUPort
from ..utils.text_normalizer import TextNormalizer


_INTENT_PATTERNS: list[tuple[str, list[str]]] = [
    ("greeting", [r"^hello\b", r"^hi\b", r"ሰላም", r"እንደምን", r"good morning"]),
    ("goodbye", [r"\b(bye|goodbye|exit)\b", r"እንገናኝ", r"ደህና ሁን"]),
    ("help", [r"\bhelp\b", r"ምን ልጠይቅ", r"እርዳኝ", r"what can you"]),
    ("repeat", [r"\brepeat\b", r"እንደገና", r"ድገም", r"last answer"]),
    ("market_price", [r"price", r"market", r"ብር", r"cost", r"ገበያ", r"ዋጋ"]),
    ("pest_disease", [r"disease", r"pest", r"rust", r"በሽታ", r"እንቁላል", r"fungus"]),
    ("fertilizer", [r"fertilizer", r"dap", r"urea", r"እርሳስ", r"ማዳመጃ", r"npk"]),
    ("planting", [r"plant", r"seed", r"spacing", r"መዝራት", r"ሰር"]),
    ("harvest", [r"harvest", r"thresh", r"መከር", r"yield"]),
    ("irrigation", [r"water", r"irrigation", r"drought", r"ማጠጣት"]),
]

_CROP_ALIASES: dict[str, list[str]] = {
    "teff": ["teff", "ጤፍ", "tef"],
    "wheat": ["wheat", "ስንዴ"],
    "maize": ["maize", "corn", "በቆሎ", "ማዝ"],
    "barley": ["barley", "ገብስ"],
}

_LOCATION_HINTS: list[tuple[str, list[str]]] = [
    ("Addis Ababa", ["addis", "አዲስ አበባ"]),
    ("Oromia", ["oromia", "ኦሮሚያ", "bishoftu", "bishoftu"]),
    ("Amhara", ["amhara", "አማራ", "bahir dar", "ባህር ዳር"]),
    ("Sidama", ["sidama", "ሲዳማ", "hawassa", "ሀዋሳ"]),
]


class RuleBasedNLUService(NLUPort):
    """High-recall rules + light regex; confidence from match strength."""

    def __init__(self, normalizer: TextNormalizer | None = None) -> None:
        self._norm = normalizer or TextNormalizer()

    def parse(
        self,
        text: str,
        session_context: dict[str, Any] | None = None,
        asr_confidence: float | None = None,
    ) -> dict[str, Any]:
        raw = text.strip()
        t = self._norm.strip_for_nlu(raw)

        intent, intent_score = self._classify_intent(t)
        crop = self._extract_crop(t)
        location = self._extract_location(t)

        missing_slots: list[str] = []
        if intent in ("pest_disease", "fertilizer", "planting", "harvest") and not crop:
            missing_slots.append("crop")
        if intent == "market_price" and not crop and not location:
            missing_slots.append("commodity_or_location")

        base_conf = 0.35 + 0.45 * intent_score
        if crop:
            base_conf += 0.08
        if location:
            base_conf += 0.05
        if asr_confidence is not None:
            base_conf = base_conf * 0.65 + asr_confidence * 0.35
        base_conf = max(0.0, min(1.0, base_conf))

        flags: list[str] = []
        if self._maybe_mixed_language(t):
            flags.append("possible_mixed_language")

        return {
            "original_text": raw,
            "intent": intent,
            "entities": {
                "crop": crop,
                "location": location,
            },
            "confidence": round(base_conf, 3),
            "missing_slots": missing_slots,
            "flags": flags,
        }

    def _classify_intent(self, t: str) -> tuple[str, float]:
        best = ("general", 0.15)
        for name, pats in _INTENT_PATTERNS:
            score = 0.0
            for p in pats:
                if re.search(p, t, re.I):
                    score = max(score, 0.55 + 0.1 * len(p))
            if score > best[1]:
                best = (name, min(1.0, score))
        if best[0] == "general" and len(t.split()) <= 2 and t.isalpha():
            best = ("greeting", 0.4)
        return best

    def _extract_crop(self, t: str) -> str | None:
        for canon, aliases in _CROP_ALIASES.items():
            for a in aliases:
                if a.lower() in t:
                    return canon
        return None

    def _extract_location(self, t: str) -> str | None:
        for canon, hints in _LOCATION_HINTS:
            for h in hints:
                if h.lower() in t:
                    return canon
        return None

    @staticmethod
    def _maybe_mixed_language(t: str) -> bool:
        has_ethiopic = bool(re.search(r"[\u1200-\u137F]", t))
        has_latin = bool(re.search(r"[a-z]{3,}", t))
        return has_ethiopic and has_latin
