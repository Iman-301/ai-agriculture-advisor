"""Concrete ResponseStrategy implementations."""

from __future__ import annotations

from typing import Any

from ..models.call_session import ResponseBundle
from ..models.response_strategy import ResponseStrategy
from ..services.rag_service import RAGService


class StaticResponseStrategy(ResponseStrategy):
    def __init__(self) -> None:
        super().__init__("STATIC", min_confidence=0.0)
        self._templates = {
            "greeting": "ሰላም። የእርሻ ጥያቄዎን በቀጥታ ይጠይቁ። እንደ ማዳመጃ፣ በሽታ ወይም ዋጋ ማወቅ ይችላሉ።",
            "help": "ስለ ማዳመጃ፣ ስለ በሽታ/እንቁላል፣ ስለ ተክል መዝራት፣ ስለ መከር ወይም የገበያ ዋጋ ጠይቅ። 'ድገም' ብለው ቀዳሚ መልስ ይድገሙ።",
            "goodbye": "እናመሰግናለን። ጤና ይስጥልዎ!",
            "repeat": "__REPEAT__",
        }

    def is_applicable(self, context: dict[str, Any]) -> bool:
        intent = context.get("intent")
        if intent == "repeat":
            return True
        return intent in self._templates

    def build_response(self, context: dict[str, Any]) -> ResponseBundle:
        intent = context.get("intent")
        if intent == "repeat":
            last = context.get("last_response_text")
            text = last if last else "ከዚህ በፊት ምንም መልስ የለም።"
            return ResponseBundle(text=text, confidence=1.0, strategy_name=self.name)
        text = self._templates[intent]
        return ResponseBundle(text=text, confidence=0.95, strategy_name=self.name)


class RAGResponseStrategy(ResponseStrategy):
    def __init__(self, rag: RAGService, min_confidence: float) -> None:
        super().__init__("RAG", min_confidence=min_confidence)
        self._rag = rag

    def is_applicable(self, context: dict[str, Any]) -> bool:
        intent = context.get("intent")
        conf = float(context.get("nlu_confidence", 0))
        if intent in ("greeting", "goodbye", "help", "repeat"):
            return False
        if conf < self.min_confidence:
            return False
        return True

    def build_response(self, context: dict[str, Any]) -> ResponseBundle:
        nlu = context["nlu"]
        question = context.get("question", "")
        text, refs, conf = self._rag.retrieve_and_synthesize(question, nlu)
        return ResponseBundle(
            text=text,
            references=refs,
            confidence=conf,
            strategy_name=self.name,
        )


class FallbackResponseStrategy(ResponseStrategy):
    def __init__(self) -> None:
        super().__init__("FALLBACK", min_confidence=0.0)

    def is_applicable(self, context: dict[str, Any]) -> bool:
        return True

    def build_response(self, context: dict[str, Any]) -> ResponseBundle:
        text = (
            "ይህን ጥያቄ በትክክል ልለውጥ አልቻልኩም። እባክዎ ከአካባቢዎ የአካባቢ ተግባር ባለሙያ ይጠይቁ። "
            "ወይም ተክልዎን እና ጥያቄዎን በግልጽ ይድገሙ።"
        )
        return ResponseBundle(text=text, confidence=0.2, strategy_name=self.name)
