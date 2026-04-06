from config import settings

from src.data.knowledge_base import KnowledgeBaseRepository
from src.data.market_data import MarketDataRepository
from src.services.nlu_service import RuleBasedNLUService
from src.services.rag_service import RAGService


def test_kb_ranking_prefers_crop_hint() -> None:
    kb = KnowledgeBaseRepository(settings.knowledge_base_path)
    hits = kb.search("fertilizer recommendation", k=3, crop_hint="teff")
    assert hits
    assert hits[0].get("crop") == "teff"


def test_market_query() -> None:
    m = MarketDataRepository(settings.market_prices_path)
    rec = m.query("teff", "Addis")
    assert rec
    assert m.format_summary(rec)


def test_rag_synthesize() -> None:
    kb = KnowledgeBaseRepository(settings.knowledge_base_path)
    market = MarketDataRepository(settings.market_prices_path)
    rag = RAGService(kb, market, top_k=3)
    nlu = RuleBasedNLUService().parse("wheat price in Addis")
    text, refs, conf = rag.retrieve_and_synthesize("wheat price in Addis", nlu)
    assert conf > 0.5
    assert text
