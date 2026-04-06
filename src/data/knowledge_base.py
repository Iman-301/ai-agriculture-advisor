"""FR-08 — KB access with ranked retrieval (mock vector search)."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"[^\w\s\u1200-\u137F]", " ", text)
    return [t for t in text.split() if len(t) > 1]


class KnowledgeBaseRepository:
    def __init__(self, json_path: Path | str) -> None:
        path = Path(json_path)
        with path.open(encoding="utf-8") as f:
            payload = json.load(f)
        self._documents: list[dict[str, Any]] = payload.get("documents", [])
        self._df: dict[str, int] = {}
        self._build_idf()

    def _build_idf(self) -> None:
        n = max(len(self._documents), 1)
        for doc in self._documents:
            terms = set(_tokenize(self._doc_text(doc)))
            for t in terms:
                self._df[t] = self._df.get(t, 0) + 1
        self._idf = {t: math.log((n + 1) / (df + 1)) + 1.0 for t, df in self._df.items()}

    @staticmethod
    def _doc_text(doc: dict[str, Any]) -> str:
        parts = [
            doc.get("crop", "") or "",
            doc.get("topic", "") or "",
            " ".join(doc.get("keywords", []) or []),
            doc.get("content", "") or "",
        ]
        return " ".join(parts)

    def search(self, query: str, k: int = 4, crop_hint: str | None = None) -> list[dict[str, Any]]:
        q_terms = _tokenize(query)
        if not q_terms:
            return []

        crop_hint_l = (crop_hint or "").lower()
        results: list[tuple[float, dict[str, Any]]] = []
        for doc in self._documents:
            if doc.get("status") and doc["status"] != "approved":
                continue
            doc_t = self._doc_text(doc)
            d_terms = _tokenize(doc_t)
            if not d_terms:
                continue
            tf: dict[str, int] = {}
            for t in d_terms:
                tf[t] = tf.get(t, 0) + 1
            score = 0.0
            for qt in q_terms:
                idf = self._idf.get(qt, 1.0)
                if qt in tf:
                    score += (1.0 + math.log(tf[qt])) * idf
                # partial match on keywords list
                for kw in doc.get("keywords", []) or []:
                    if qt in kw.lower():
                        score += 0.35 * idf

            doc_crop = (doc.get("crop") or "").lower()
            if crop_hint_l and doc_crop == crop_hint_l:
                score += 1.25
            elif crop_hint_l and crop_hint_l in doc_t.lower():
                score += 0.5

            if score > 0:
                results.append(
                    (
                        score,
                        {
                            "id": doc["id"],
                            "content": doc["content"],
                            "source": doc.get("source", ""),
                            "crop": doc.get("crop"),
                            "topic": doc.get("topic"),
                            "score": min(1.0, score / 5.0),
                        },
                    )
                )

        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:k]]
