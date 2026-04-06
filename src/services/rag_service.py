"""FR-10 — Retrieval + grounded synthesis (template-based without external LLM)."""

from __future__ import annotations

from typing import Any

from ..data.knowledge_base import KnowledgeBaseRepository
from ..data.market_data import MarketDataRepository
from ..models.farmer_profile import Reference


class RAGService:
    """Uses KB + market repositories; composes concise advisory text."""

    def __init__(
        self,
        kb: KnowledgeBaseRepository,
        market: MarketDataRepository,
        top_k: int = 4,
    ) -> None:
        self._kb = kb
        self._market = market
        self._top_k = top_k

    def retrieve_and_synthesize(
        self,
        question: str,
        nlu: dict[str, Any],
    ) -> tuple[str, list[Reference], float]:
        intent = nlu.get("intent") or "general"
        entities = nlu.get("entities") or {}
        crop_hint = entities.get("crop")
        loc = entities.get("location")

        refs: list[Reference] = []
        if intent == "market_price":
            commodity = crop_hint
            mrec = self._market.query(commodity, loc)
            summary = self._market.format_summary(mrec)
            if not summary:
                return (
                    "I could not find a matching mock price record. Try naming the crop "
                    "(teff, wheat, maize) or a market/region.",
                    [],
                    0.25,
                )
            for r in mrec[:3]:
                refs.append(
                    Reference(
                        ref_id=r["id"],
                        label=r.get("source", "market"),
                        kind="market",
                        snippet=summary[:200],
                    )
                )
            text = (
                f"Market snapshot (mock data): {summary} "
                "Prices change often—verify with local extension or market notice."
            )
            return text, refs, 0.75

        hits = self._kb.search(question, k=self._top_k, crop_hint=crop_hint)
        if not hits:
            return (
                "I did not find approved mock guidance for that. Please name the crop "
                "or ask about fertilizer, disease, planting, or harvest.",
                [],
                0.2,
            )

        lines = []
        conf_acc = 0.0
        for h in hits:
            lines.append(h["content"])
            refs.append(
                Reference(
                    ref_id=h["id"],
                    label=h.get("source", "kb"),
                    kind="kb_doc",
                    snippet=h["content"][:160],
                )
            )
            conf_acc += float(h.get("score", 0.5))
        conf = min(0.95, 0.45 + conf_acc / max(len(hits), 1))

        merged = " ".join(lines[:3])
        answer = (
            f"Based on validated mock sources: {merged} "
            "If symptoms are severe or unclear, contact your local extension worker."
        )
        return answer, refs, conf
