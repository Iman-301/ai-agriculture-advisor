"""FR-11 — Strategy selection (RAG / STATIC / FALLBACK)."""

from __future__ import annotations

from typing import Any

from ..models.call_session import ResponseBundle
from ..models.response_strategy import StrategyChain
from .strategies import FallbackResponseStrategy, RAGResponseStrategy, StaticResponseStrategy


class DecisionLayer:
    def __init__(self, rag_min_confidence: float, rag_service) -> None:
        static = StaticResponseStrategy()
        rag = RAGResponseStrategy(rag_service, min_confidence=rag_min_confidence)
        fallback = FallbackResponseStrategy()
        self._chain = StrategyChain([static, rag, fallback])

    def decide(self, context: dict[str, Any]) -> ResponseBundle:
        strategy = self._chain.select(context)
        return strategy.build_response(context)
