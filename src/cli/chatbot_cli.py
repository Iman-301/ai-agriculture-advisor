"""Text-only CLI — Phase 1 pipeline (NLU → decision → RAG mock → safety → bundle)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config import settings

from src.core.decision_layer import DecisionLayer
from src.core.dialogue_manager import DialogueManager
from src.core.response_builder import ResponseBuilder
from src.core.safety_guard import SafetyGuard
from src.data.farmer_repository import FarmerRepository
from src.data.knowledge_base import KnowledgeBaseRepository
from src.data.market_data import MarketDataRepository
from src.data.session_store import SessionStore
from src.services.nlu_service import RuleBasedNLUService
from src.services.rag_service import RAGService


def build_system() -> DialogueManager:
    kb = KnowledgeBaseRepository(settings.knowledge_base_path)
    market = MarketDataRepository(settings.market_prices_path)
    farmers = FarmerRepository(settings.farmer_profiles_path)
    rag = RAGService(kb, market, top_k=settings.rag_top_k)
    decision = DecisionLayer(
        rag_min_confidence=settings.nlu_confidence_rag_min,
        rag_service=rag,
    )
    return DialogueManager(
        nlu=RuleBasedNLUService(),
        decision=decision,
        sessions=SessionStore(),
        farmers=farmers,
        safety=SafetyGuard(),
        builder=ResponseBuilder(),
    )


def main() -> None:
    dm = build_system()
    print("=== Agricultural Advisory (mock data) ===")
    print("Commands: quit | repeat | help")
    print("-" * 44)
    session_id = "cli_session"
    phone = "+251900000000"

    while True:
        try:
            user = input("\nFarmer: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break
        if not user:
            continue
        low = user.lower()
        if low in ("quit", "exit", "bye"):
            print("Bot: Thank you. Goodbye!")
            break

        bundle = dm.process_text(session_id, phone, user)
        print(f"Bot: {bundle.text}")
        if bundle.references:
            print(f"     (refs: {bundle.primary_reference_labels()})")


if __name__ == "__main__":
    main()
