"""
PART 7 — Failure Tests.
Simulates failures to verify the system degrades gracefully.
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from unittest.mock import patch


class TestFailureHandling:

    def test_serper_failure_returns_empty(self):
        """If Serper API fails, retrieval should return empty list."""
        with patch("backend.retriever.requests.post", side_effect=Exception("API down")):
            from backend.retriever import retrieve_evidence
            sources = retrieve_evidence("test claim")
            assert sources == []

    def test_article_fetch_failure_returns_none(self):
        """If newspaper3k fails, fetch_article returns None."""
        with patch("newspaper.Article", side_effect=Exception("Download failed")):
            from backend.retrieval.article_fetcher import fetch_article
            result = fetch_article("https://example.com/broken")
            assert result is None

    def test_hybrid_retrieve_survives_article_failure(self):
        """hybrid_retrieve should not crash when article ingestion fails."""
        from backend.models import Source

        fake_sources = [
            Source(title="Test", url="https://broken.example.com", snippet="test snippet")
        ]

        with patch("backend.retrieval.hybrid_retriever.retrieve_evidence", return_value=fake_sources):
            with patch("backend.retrieval.hybrid_retriever.ingest_from_url", side_effect=Exception("boom")):
                from backend.retrieval.hybrid_retriever import hybrid_retrieve
                sources = hybrid_retrieve("test claim", num_results=5)
                assert isinstance(sources, list)

    def test_reranker_with_empty_sources(self):
        """Reranker should handle empty input gracefully."""
        from backend.retrieval.reranker import rerank
        result = rerank("test query", [], top_k=5)
        assert result == []

    def test_vector_search_empty_index(self, tmp_path):
        """Vector search on empty index returns empty list."""
        import numpy as np
        from backend.retrieval.vector_index import VectorIndex
        idx = VectorIndex(dim=384, index_path=str(tmp_path / "empty.bin"))
        results = idx.search(np.random.rand(384).astype(np.float32))
        assert results == []

    def test_document_store_corrupt_file(self, tmp_path):
        """DocumentStore should handle corrupted JSON gracefully."""
        path = tmp_path / "corrupt.json"
        path.write_text("{not valid json!!", encoding="utf-8")
        from backend.retrieval.document_store import DocumentStore
        store = DocumentStore(store_path=str(path))
        assert store.size == 0

    def test_normalize_empty_text(self):
        """Normalization of empty string should not crash."""
        from backend.ingestion import normalize_text
        result = normalize_text("")
        assert result == ""

    def test_invalid_url_fetch(self):
        """fetch_article should return None for invalid URLs."""
        from backend.retrieval.article_fetcher import fetch_article
        assert fetch_article("") is None
        assert fetch_article("ftp://nope") is None
        assert fetch_article(None) is None
