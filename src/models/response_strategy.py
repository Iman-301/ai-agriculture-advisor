"""SDS §5.3.2 — Strategy selection (RAG / STATIC / FALLBACK)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .call_session import ResponseBundle


class ResponseStrategy(ABC):
    name: str
    min_confidence: float

    def __init__(self, name: str, min_confidence: float = 0.0) -> None:
        self.name = name
        self.min_confidence = min_confidence

    @abstractmethod
    def is_applicable(self, context: dict[str, Any]) -> bool:
        raise NotImplementedError

    @abstractmethod
    def build_response(self, context: dict[str, Any]) -> "ResponseBundle":
        raise NotImplementedError


class StrategyChain:
    """Ordered strategies; first match wins (caller appends fallback last)."""

    def __init__(self, strategies: list[ResponseStrategy]) -> None:
        self.strategies = strategies

    def select(self, context: dict[str, Any]) -> ResponseStrategy:
        for s in self.strategies:
            if s.is_applicable(context):
                return s
        raise RuntimeError("No strategy matched; append FallbackStrategy.")
