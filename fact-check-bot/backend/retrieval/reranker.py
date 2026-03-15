import logging
from typing import List
from backend.models import Source

logger = logging.getLogger(__name__)

_reranker = None


def _get_reranker():
    """Singleton loader for the cross-encoder reranker model."""
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        logger.info("Reranker model loaded: ms-marco-MiniLM-L-6-v2")
    return _reranker


def preload_reranker() -> None:
    """Called at startup to warm up the reranker."""
    _get_reranker()


def rerank(query: str, sources: List[Source], top_k: int = 5) -> List[Source]:
    """
    Re-rank sources by query-document relevance using a cross-encoder.
    Returns the top_k highest-scoring sources.
    """
    if not sources:
        return []

    model = _get_reranker()
    pairs = [(query, s.snippet) for s in sources]
    scores = model.predict(pairs)

    scored = sorted(zip(sources, scores), key=lambda x: x[1], reverse=True)
    return [s for s, _ in scored[:top_k]]
