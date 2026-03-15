import logging
from typing import List
from backend.models import Source
from backend.retriever import retrieve_evidence
from backend.retrieval.embedder import embed_query
from backend.retrieval.vector_index import VectorIndex
from backend.retrieval.document_store import DocumentStore
from backend.retrieval.reranker import rerank
from backend.retrieval.document_ingestor import ingest_from_url

logger = logging.getLogger(__name__)

_vector_index = None
_doc_store = None


def _get_vector_index() -> VectorIndex:
    global _vector_index
    if _vector_index is None:
        _vector_index = VectorIndex()
    return _vector_index


def _get_doc_store() -> DocumentStore:
    global _doc_store
    if _doc_store is None:
        _doc_store = DocumentStore()
    return _doc_store


def preload_index() -> None:
    """Called at startup to load FAISS index and document store."""
    _get_vector_index()
    _get_doc_store()


def _vector_search(claim: str, top_k: int = 5) -> List[Source]:
    """Search FAISS index and return results as Source objects."""
    index = _get_vector_index()
    store = _get_doc_store()

    if index.total_vectors == 0:
        return []

    query_emb = embed_query(claim)
    results = index.search(query_emb, top_k=top_k)

    doc_ids = [doc_id for doc_id, _ in results]
    docs = store.get_by_ids(doc_ids)

    sources = []
    for doc in docs:
        sources.append(Source(
            title=doc.title,
            url=doc.url,
            snippet=doc.chunk_text[:500],
        ))
    return sources


def hybrid_retrieve(claim: str, num_results: int = 5) -> List[Source]:
    """
    Hybrid retrieval: web search + vector DB, merged and reranked.
    Automatically ingests new articles from web results into the vector DB.
    Returns top num_results sources compatible with the RAG generator.
    """
    # Web search retrieval
    web_sources = retrieve_evidence(claim, num_results=num_results)
    logger.info(f"Hybrid retrieval: {len(web_sources)} web sources")

    # Ingest new articles from web results into vector DB
    index = _get_vector_index()
    store = _get_doc_store()
    for src in web_sources:
        if src.url and not store.has_url(src.url):
            try:
                ingest_from_url(src.url, index, store)
            except Exception as e:
                logger.warning(f"Article ingestion failed ({src.url}): {e}")

    # Vector DB retrieval (now includes freshly ingested content)
    vector_sources = _vector_search(claim, top_k=num_results)
    logger.info(f"Hybrid retrieval: {len(vector_sources)} vector sources")

    # Merge — deduplicate by URL
    seen_urls = set()
    merged = []
    for src in web_sources + vector_sources:
        if src.url and src.url in seen_urls:
            continue
        seen_urls.add(src.url)
        merged.append(src)

    if not merged:
        return []

    # Rerank all candidates
    reranked = rerank(claim, merged, top_k=num_results)
    logger.info(f"Hybrid retrieval: {len(reranked)} sources after reranking")

    return reranked
