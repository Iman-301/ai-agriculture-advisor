"""FR-21 — simple structured audit logging."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


def get_logger(name: str) -> logging.Logger:
    log = logging.getLogger(name)
    if not log.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
        log.addHandler(h)
        log.setLevel(logging.INFO)
    return log


def audit_event(logger: logging.Logger, event: str, payload: dict[str, Any]) -> None:
    line = json.dumps(
        {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **payload},
        ensure_ascii=False,
    )
    logger.info(line)
