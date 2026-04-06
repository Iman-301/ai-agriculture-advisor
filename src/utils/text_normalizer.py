"""FR-07 — numbers, units, currency for TTS-friendly text."""

from __future__ import annotations

import re
from typing import Optional


class TextNormalizer:
    _multi_space = re.compile(r"\s+")
    _currency = re.compile(r"\b(birr|etb)\b", re.I)

    def normalize(self, text: str, locale: str = "am-ET") -> tuple[str, dict[str, str]]:
        """Return (normalized_text, metadata_map)."""
        t = text.strip()
        t = self._multi_space.sub(" ", t)
        t = self._currency.sub("Birr", t)
        meta: dict[str, str] = {}
        if locale:
            meta["locale"] = locale
        return t, meta

    def strip_for_nlu(self, text: str) -> str:
        t = text.strip().lower()
        t = self._multi_space.sub(" ", t)
        return t
