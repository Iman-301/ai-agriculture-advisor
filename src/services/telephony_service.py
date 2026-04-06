"""FR-06 — Twilio TwiML builder (mock-friendly)."""

from __future__ import annotations

from xml.sax.saxutils import escape

from ..application.ports import TelephonyPort


class MockTelephonyService(TelephonyPort):
    def build_incoming_twiml(self, base_url: str) -> str:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say language="am-ET">{escape("Welcome. Ask your farming question after the tone.")}</Say>
  <Gather input="speech" language="am-ET" action="{escape(base_url.rstrip('/') + '/voice/process')}" method="POST" />
  <Redirect method="POST">{escape(base_url.rstrip('/') + '/voice/incoming')}</Redirect>
</Response>"""
