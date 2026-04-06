"""FR-13 — Final bundle assembly + normalization."""

from __future__ import annotations

from ..models.call_session import ResponseBundle
from ..utils.text_normalizer import TextNormalizer


class ResponseBuilder:
    def __init__(self, normalizer: TextNormalizer | None = None) -> None:
        self._norm = normalizer or TextNormalizer()

    def finalize(self, bundle: ResponseBundle) -> ResponseBundle:
        text, _meta = self._norm.normalize(bundle.text)
        return ResponseBundle(
            text=text,
            references=bundle.references,
            confidence=bundle.confidence,
            strategy_name=bundle.strategy_name,
            safety_flags=list(bundle.safety_flags),
        )
