"""
PART 3 — Component Tests.
Tests each module independently: claim detection, vector DB, embedder,
chunker, reranker, article fetcher, document store.
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import numpy as np


# ── Claim Detection ──

class TestClaimDetection:

    def test_opinion_not_a_claim(self):
        from backend.claim_detector import detect_claim
        result = detect_claim("I love pizza")
        assert result.is_claim is False, f"Expected NOT a claim, got is_claim={result.is_claim}"

    def test_factual_claim_detected(self):
        from backend.claim_detector import detect_claim
        result = detect_claim("COVID vaccines cause infertility")
        assert result.is_claim is True, f"Expected a claim, got is_claim={result.is_claim}"
        assert result.extracted_claim is not None, "Extracted claim should not be None"

    def test_question_not_a_claim(self):
        from backend.claim_detector import detect_claim
        result = detect_claim("What time does the library close on Sundays?")
        assert result.is_claim is False


# ── Embedding System ──

class TestEmbedder:

    def test_embed_query_shape(self):
        from backend.retrieval.embedder import embed_query
        vec = embed_query("Einstein failed math")
        assert isinstance(vec, np.ndarray)
        assert vec.shape == (384,), f"Expected (384,), got {vec.shape}"

    def test_embed_texts_batch(self):
        from backend.retrieval.embedder import embed_texts
        vecs = embed_texts(["hello world", "fact checking is important"])
        assert vecs.shape == (2, 384)

    def test_embed_dtype(self):
        from backend.retrieval.embedder import embed_query
        vec = embed_query("test")
        assert vec.dtype == np.float32


# ── Chunker ──

class TestChunker:

    def test_chunk_sizes(self):
        from backend.retrieval.chunker import chunk_text
        text = " ".join(["word"] * 1200)
        chunks = chunk_text(text, {"source": "test"}, chunk_size=500, overlap=50)
        assert len(chunks) == 3, f"Expected 3 chunks, got {len(chunks)}"
        for c in chunks:
            word_count = len(c.text.split())
            assert word_count <= 500, f"Chunk too large: {word_count} words"

    def test_chunk_overlap(self):
        from backend.retrieval.chunker import chunk_text
        words = [f"w{i}" for i in range(600)]
        text = " ".join(words)
        chunks = chunk_text(text, {}, chunk_size=500, overlap=50)
        assert len(chunks) == 2
        first_words = set(chunks[0].text.split())
        second_words = set(chunks[1].text.split())
        overlap_words = first_words & second_words
        assert len(overlap_words) == 50, f"Expected 50 overlap words, got {len(overlap_words)}"

    def test_chunk_metadata_inherited(self):
        from backend.retrieval.chunker import chunk_text
        meta = {"url": "http://test.com", "title": "Test"}
        chunks = chunk_text("word " * 100, meta)
        for c in chunks:
            assert c.metadata["url"] == "http://test.com"

    def test_empty_text(self):
        from backend.retrieval.chunker import chunk_text
        assert chunk_text("", {}) == []


# ── Vector Index ──

class TestVectorIndex:

    def test_add_and_search(self, tmp_path):
        from backend.retrieval.vector_index import VectorIndex
        idx = VectorIndex(dim=384, index_path=str(tmp_path / "test.bin"))
        vecs = np.random.rand(5, 384).astype(np.float32)
        idx.add(vecs)
        assert idx.total_vectors == 5
        results = idx.search(vecs[0], top_k=3)
        assert len(results) == 3
        assert results[0][0] == 0, "Nearest neighbor should be the vector itself"

    def test_empty_search(self, tmp_path):
        from backend.retrieval.vector_index import VectorIndex
        idx = VectorIndex(dim=384, index_path=str(tmp_path / "empty.bin"))
        results = idx.search(np.random.rand(384).astype(np.float32))
        assert results == []


# ── Document Store ──

class TestDocumentStore:

    def test_add_and_retrieve(self, tmp_path):
        from backend.retrieval.document_store import DocumentStore, StoredDocument
        store = DocumentStore(store_path=str(tmp_path / "store.json"))
        docs = [
            StoredDocument(chunk_text="chunk 1", source="wiki", url="http://a.com", title="A"),
            StoredDocument(chunk_text="chunk 2", source="wiki", url="http://b.com", title="B"),
        ]
        ids = store.add_documents(docs)
        assert ids == [0, 1]
        retrieved = store.get_by_ids([0, 1])
        assert len(retrieved) == 2
        assert retrieved[0].chunk_text == "chunk 1"

    def test_has_url(self, tmp_path):
        from backend.retrieval.document_store import DocumentStore, StoredDocument
        store = DocumentStore(store_path=str(tmp_path / "store2.json"))
        store.add_documents([
            StoredDocument(chunk_text="x", source="s", url="http://exists.com", title="T")
        ])
        assert store.has_url("http://exists.com") is True
        assert store.has_url("http://missing.com") is False

    def test_persistence(self, tmp_path):
        from backend.retrieval.document_store import DocumentStore, StoredDocument
        path = str(tmp_path / "persist.json")
        store1 = DocumentStore(store_path=path)
        store1.add_documents([
            StoredDocument(chunk_text="persisted", source="s", url="http://p.com", title="P")
        ])
        store2 = DocumentStore(store_path=path)
        assert store2.size == 1
        assert store2.get_by_ids([0])[0].chunk_text == "persisted"


# ── Reranker ──

class TestReranker:

    def test_rerank_ordering(self):
        from backend.retrieval.reranker import rerank
        from backend.models import Source
        sources = [
            Source(title="Irrelevant", url="http://a.com", snippet="The weather is nice today in Paris."),
            Source(title="Relevant", url="http://b.com", snippet="Einstein excelled in physics and mathematics as a student."),
            Source(title="Somewhat", url="http://c.com", snippet="Many myths exist about famous scientists and their school performance."),
        ]
        reranked = rerank("Did Einstein fail math?", sources, top_k=3)
        assert len(reranked) == 3
        assert reranked[0].url != sources[0].url, "Irrelevant doc should not be ranked first"

    def test_rerank_top_k(self):
        from backend.retrieval.reranker import rerank
        from backend.models import Source
        sources = [
            Source(title=f"Doc {i}", url=f"http://{i}.com", snippet=f"Content {i}")
            for i in range(8)
        ]
        reranked = rerank("test query", sources, top_k=3)
        assert len(reranked) == 3

    def test_rerank_empty(self):
        from backend.retrieval.reranker import rerank
        assert rerank("query", [], top_k=5) == []


# ── Article Fetcher ──

class TestArticleFetcher:

    def test_invalid_url(self):
        from backend.retrieval.article_fetcher import fetch_article
        assert fetch_article("") is None
        assert fetch_article("not-a-url") is None

    def test_fetch_wikipedia(self):
        from backend.retrieval.article_fetcher import fetch_article
        result = fetch_article("https://en.wikipedia.org/wiki/Eli_Whitney")
        if result is None:
            pytest.skip("Network unavailable or Wikipedia blocked")
        assert result["title"], "Title should not be empty"
        assert len(result["text"]) >= 300, "Article text too short"
        assert result["url"] == "https://en.wikipedia.org/wiki/Eli_Whitney"
        assert result["source"], "Source domain should not be empty"


# ── Dedup Tracker ──

class TestDedupTracker:

    def test_mark_and_check(self):
        from backend.social.dedup import DedupTracker
        d = DedupTracker(ttl_hours=1)
        d.mark_seen("reddit", "abc123")
        assert d.is_seen("reddit", "abc123") is True
        assert d.is_seen("reddit", "xyz") is False
        assert d.size == 1

    def test_ttl_eviction(self):
        import time
        from backend.social.dedup import DedupTracker
        d = DedupTracker(ttl_hours=0.0001)
        d.mark_seen("rss", "post1")
        assert d.is_seen("rss", "post1") is True
        time.sleep(0.5)
        assert d.is_seen("rss", "post1") is False


# ── Text Normalization ──

class TestIngestion:

    def test_normalize_text(self):
        from backend.ingestion import normalize_text
        raw = "OMG u won't BELIEVE this!!! https://t.co/abc @user #breaking"
        norm = normalize_text(raw)
        assert "https://" not in norm
        assert "@user" not in norm
        assert "you" in norm  # slang expansion
        assert norm.count("!") <= 1  # collapsed punctuation

    def test_ingest_single_post(self):
        from backend.ingestion import ingest_single_post
        post = ingest_single_post("Test post for fact checking", platform="test")
        assert post.id is not None
        assert post.platform == "test"
        assert post.normalized_text
        assert post.timestamp
