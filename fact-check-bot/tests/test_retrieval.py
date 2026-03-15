"""
PART 4 — Hybrid Retrieval Test.
Tests the full retrieval pipeline: web search, article ingestion, vector search, reranking.
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import numpy as np


class TestHybridRetrieval:

    def test_web_retrieval_returns_sources(self):
        """Test that Serper web search returns results."""
        from backend.retriever import retrieve_evidence
        sources = retrieve_evidence("Einstein failed math in school", num_results=5)
        if not sources:
            pytest.skip("Serper API returned no results (check API key)")
        assert len(sources) <= 5
        for s in sources:
            assert s.title
            assert s.url
            assert s.snippet

    def test_hybrid_retrieve_returns_sources(self):
        """Test full hybrid pipeline: web + vector + rerank."""
        from backend.retrieval import hybrid_retrieve
        sources = hybrid_retrieve("Einstein failed math in school", num_results=5)
        if not sources:
            pytest.skip("No sources returned (check API keys)")
        assert len(sources) <= 5
        for s in sources:
            assert s.title
            assert s.snippet

    def test_article_ingestion_grows_index(self, tmp_path):
        """Test that ingesting an article increases FAISS index size."""
        from backend.retrieval.vector_index import VectorIndex
        from backend.retrieval.document_store import DocumentStore
        from backend.retrieval.document_ingestor import ingest_article

        idx = VectorIndex(dim=384, index_path=str(tmp_path / "test.bin"))
        store = DocumentStore(store_path=str(tmp_path / "store.json"))

        assert idx.total_vectors == 0

        article = {
            "title": "Test Article",
            "text": "This is a long test article. " * 200,
            "url": "http://test-article.com/page1",
            "source": "test-article.com",
        }
        count = ingest_article(article, idx, store)
        assert count > 0, "Should ingest at least 1 chunk"
        assert idx.total_vectors == count
        assert store.size == count

    def test_url_dedup_prevents_reingest(self, tmp_path):
        """Test that ingesting the same URL twice only stores once."""
        from backend.retrieval.vector_index import VectorIndex
        from backend.retrieval.document_store import DocumentStore
        from backend.retrieval.document_ingestor import ingest_from_url, ingest_article

        idx = VectorIndex(dim=384, index_path=str(tmp_path / "test2.bin"))
        store = DocumentStore(store_path=str(tmp_path / "store2.json"))

        article = {
            "title": "Dedup Test",
            "text": "Content for dedup testing. " * 200,
            "url": "http://dedup.com/article",
            "source": "dedup.com",
        }
        count1 = ingest_article(article, idx, store)
        assert count1 > 0

        count2 = ingest_from_url("http://dedup.com/article", idx, store)
        assert count2 == 0, "Should skip — URL already ingested"

    def test_vector_search_after_ingest(self, tmp_path):
        """Test that vector search finds content from ingested articles."""
        from backend.retrieval.vector_index import VectorIndex
        from backend.retrieval.document_store import DocumentStore, StoredDocument
        from backend.retrieval.embedder import embed_texts, embed_query

        idx = VectorIndex(dim=384, index_path=str(tmp_path / "vs.bin"))
        store = DocumentStore(store_path=str(tmp_path / "vs_store.json"))

        texts = [
            "Einstein was a brilliant physicist who excelled in mathematics.",
            "The Great Wall of China is an ancient fortification in northern China.",
            "Water is composed of hydrogen and oxygen atoms.",
        ]
        embeddings = embed_texts(texts)
        docs = [
            StoredDocument(chunk_text=t, source="test", url=f"http://test.com/{i}", title=f"Doc {i}")
            for i, t in enumerate(texts)
        ]
        store.add_documents(docs)
        idx.add(embeddings)

        query_emb = embed_query("Did Einstein fail math?")
        results = idx.search(query_emb, top_k=1)
        assert results[0][0] == 0, "Einstein doc should be closest match"
