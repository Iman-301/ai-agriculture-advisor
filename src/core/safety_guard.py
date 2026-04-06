"""FR-12 — High-risk topics: conservative wording and disclaimers."""

from __future__ import annotations

import re
from typing import Any

from ..models.call_session import ResponseBundle, SessionState


class SafetyGuard:
    _risk_terms = re.compile(
        r"\b(pesticide|herbicide|fungicide|insecticide|kg/ha|dosage|poison|toxic)\b|"
        r"(መርጃ|መድሃኒት|መርዝ)",
        re.I,
    )

    def apply(
        self,
        draft: ResponseBundle,
        nlu: dict[str, Any],
        state: SessionState,
    ) -> ResponseBundle:
        _ = state
        intent = nlu.get("intent")
        is_risk = intent in ("pest_disease", "fertilizer") or bool(self._risk_terms.search(draft.text))
        if not is_risk:
            return draft

        safe_text = (
            f"{draft.text} "
            "Safety note: follow product labels and your local extension worker for chemicals "
            "and fertilizer rates."
        )
        return ResponseBundle(
            text=safe_text,
            references=draft.references,
            confidence=min(draft.confidence, 0.88),
            strategy_name=draft.strategy_name,
            safety_flags=draft.safety_flags + ["high_risk_disclaimer"],
        )
