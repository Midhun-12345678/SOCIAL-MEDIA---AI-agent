"""
Hybrid Retrieval Package.

Combines web search (Serper) + vector database (FAISS) retrieval
with cross-encoder semantic reranking.
"""

from backend.retrieval.hybrid_retriever import hybrid_retrieve
from backend.retrieval.embedder import embed_query, embed_texts
from backend.retrieval.vector_index import VectorIndex
from backend.retrieval.reranker import rerank

__all__ = ["hybrid_retrieve", "embed_query", "embed_texts", "VectorIndex", "rerank"]
