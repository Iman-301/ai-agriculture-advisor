"""FR-06 — Twilio TwiML builder (mock-friendly)."""

from __future__ import annotations

from xml.sax.saxutils import escape

from ..application.ports import TelephonyPort


class MockTelephonyService(TelephonyPort):
    def build_incoming_twiml(self, base_url: str) -> str:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say language="am-ET">{escape("እንኳን ደህና መጡ። ከድምጹ በኋላ የእርሻ ጥያቄዎን ይጠይቁ። መልሱን ለመድገም 1 ይጫኑ።")}</Say>
  <Gather input="speech dtmf" numDigits="1" timeout="5" language="am-ET" actionOnEmptyResult="true" action="{escape(base_url.rstrip('/') + '/voice/process')}" method="POST" />
  <Redirect method="POST">{escape(base_url.rstrip('/') + '/voice/incoming')}</Redirect>
</Response>"""
