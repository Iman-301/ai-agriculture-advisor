"""FR-09 — Market prices with locality and as-of metadata."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class MarketDataRepository:
    def __init__(self, json_path: Path | str) -> None:
        with Path(json_path).open(encoding="utf-8") as f:
            self._payload = json.load(f)
        self.currency = self._payload.get("currency", "ETB")
        self.unit = self._payload.get("unit", "kg")
        self._records: list[dict[str, Any]] = self._payload.get("records", [])

    def query(
        self,
        commodity: str | None,
        region_or_market: str | None = None,
    ) -> list[dict[str, Any]]:
        c = (commodity or "").lower()
        loc = (region_or_market or "").lower()
        out: list[dict[str, Any]] = []
        for r in self._records:
            names = [r.get("commodity", ""), *r.get("commodity_aliases", [])]
            if c and not any(c in str(n).lower() for n in names):
                continue
            if loc:
                hay = f"{r.get('market','')} {r.get('region','')}".lower()
                if loc not in hay:
                    continue
            out.append(r)
        return out

    def format_summary(self, records: list[dict[str, Any]]) -> str:
        if not records:
            return ""
        lines = []
        for r in records[:3]:
            low, high = r.get("low_price"), r.get("high_price")
            m = r.get("market") or r.get("region") or "market"
            com = r.get("commodity", "")
            as_of = r.get("as_of", "")
            try:
                ts = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
                as_of_s = ts.strftime("%Y-%m-%d")
            except Exception:
                as_of_s = str(as_of)[:10]
            lines.append(
                f"{m} ገበያ - {com}: በአንፃር {low:.0f}–{high:.0f} {self.currency}/{self.unit} (እስከ {as_of_s})።"
            )
        return " ".join(lines)
