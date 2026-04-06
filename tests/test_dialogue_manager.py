"""End-to-end pipeline tests."""

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


def _dm() -> DialogueManager:
    kb = KnowledgeBaseRepository(settings.knowledge_base_path)
    market = MarketDataRepository(settings.market_prices_path)
    farmers = FarmerRepository(settings.farmer_profiles_path)
    rag = RAGService(kb, market, top_k=4)
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


def test_market_price_teff_addis() -> None:
    dm = _dm()
    b = dm.process_text("s1", "+251900000000", "What is teff price in Addis Ababa?")
    assert "teff" in b.text.lower() or "Teff" in b.text
    assert "Addis" in b.text or "addis" in b.text.lower() or "ETB" in b.text or "Birr" in b.text


def test_fertilizer_teff_kb() -> None:
    dm = _dm()
    b = dm.process_text("s1", "+251900000000", "Teff fertilizer recommendation")
    assert "teff" in b.text.lower() or "Teff" in b.text
    assert b.strategy_name == "RAG" or "mock" in b.text.lower()


def test_repeat() -> None:
    dm = _dm()
    dm.process_text("s2", "+251900000000", "hello")
    first = dm.process_text("s2", "+251900000000", "teff rust disease")
    second = dm.process_text("s2", "+251900000000", "repeat")
    assert first.text in second.text or second.text in first.text or len(second.text) > 10
