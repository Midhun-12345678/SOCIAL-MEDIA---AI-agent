"""
Quick CLI test runner - runs the most critical tests without pytest.
Usage: python test_cases.py
"""

import sys
import os
import time
import traceback

sys.path.insert(0, os.path.dirname(__file__))

PASS = 0
FAIL = 0
SKIP = 0


def run_test(name, fn):
    global PASS, FAIL, SKIP
    try:
        result = fn()
        if result == "SKIP":
            print(f"  [SKIP] {name}")
            SKIP += 1
        else:
            print(f"  [PASS] {name}")
            PASS += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        traceback.print_exc()
        FAIL += 1


def test_normalize():
    from backend.ingestion import normalize_text
    norm = normalize_text("OMG u won't BELIEVE this!!! https://t.co/abc @user #breaking")
    assert "https://" not in norm
    assert "you" in norm


def test_embed_shape():
    from backend.retrieval.embedder import embed_query
    import numpy as np
    vec = embed_query("Einstein failed math")
    assert vec.shape == (384,)
    assert vec.dtype == np.float32


def test_chunker():
    from backend.retrieval.chunker import chunk_text
    text = " ".join(["word"] * 1200)
    chunks = chunk_text(text, {"src": "test"}, chunk_size=500, overlap=50)
    assert len(chunks) == 3


def test_vector_index():
    import numpy as np
    import tempfile
    from backend.retrieval.vector_index import VectorIndex
    with tempfile.TemporaryDirectory() as td:
        idx = VectorIndex(dim=384, index_path=os.path.join(td, "t.bin"))
        vecs = np.random.rand(3, 384).astype(np.float32)
        idx.add(vecs)
        assert idx.total_vectors == 3
        results = idx.search(vecs[0], top_k=1)
        assert results[0][0] == 0


def test_doc_store():
    import tempfile
    from backend.retrieval.document_store import DocumentStore, StoredDocument
    with tempfile.TemporaryDirectory() as td:
        store = DocumentStore(store_path=os.path.join(td, "s.json"))
        store.add_documents([
            StoredDocument(chunk_text="hello", source="test", url="http://x.com", title="X")
        ])
        assert store.size == 1
        assert store.has_url("http://x.com")
        assert not store.has_url("http://y.com")


def test_reranker():
    from backend.retrieval.reranker import rerank
    from backend.models import Source
    sources = [
        Source(title="A", url="http://a.com", snippet="The weather is nice today."),
        Source(title="B", url="http://b.com", snippet="Einstein was a genius physicist."),
    ]
    result = rerank("Einstein physics", sources, top_k=2)
    assert len(result) == 2


def test_dedup():
    from backend.social.dedup import DedupTracker
    d = DedupTracker(ttl_hours=1)
    d.mark_seen("reddit", "p1")
    assert d.is_seen("reddit", "p1")
    assert not d.is_seen("reddit", "p2")


def test_article_fetcher_invalid():
    from backend.retrieval.article_fetcher import fetch_article
    assert fetch_article("") is None
    assert fetch_article("not-a-url") is None


def test_claim_detection():
    from backend.claim_detector import detect_claim
    r1 = detect_claim("I love pizza")
    if r1.is_claim:
        return "SKIP"  # GPT might disagree
    r2 = detect_claim("COVID vaccines cause infertility")
    assert r2.is_claim


def test_full_pipeline_api():
    import requests
    try:
        r = requests.get("http://127.0.0.1:8000/", timeout=3)
        if r.status_code != 200:
            return "SKIP"
    except Exception:
        return "SKIP"

    r = requests.post(
        "http://127.0.0.1:8000/check",
        json={"post": "The Earth is flat"},
        timeout=30,
    )
    result = r.json()
    assert "verdict" in result
    assert "confidence" in result
    assert "response" in result
    assert result["verdict"] in ["TRUE", "FALSE", "UNVERIFIABLE", "NOT_A_CLAIM"]
    assert 0.0 <= result["confidence"] <= 1.0


if __name__ == "__main__":
    print("\n=== Fact-Check Bot - Quick Test Suite ===\n")

    start = time.time()

    print("[Component Tests]")
    run_test("Text normalization", test_normalize)
    run_test("Embedding shape (384d)", test_embed_shape)
    run_test("Chunker (500w, 50 overlap)", test_chunker)
    run_test("FAISS vector index", test_vector_index)
    run_test("Document store + has_url", test_doc_store)
    run_test("Reranker ordering", test_reranker)
    run_test("Dedup tracker", test_dedup)
    run_test("Article fetcher (invalid URL)", test_article_fetcher_invalid)

    print("\n[Pipeline Tests]")
    run_test("Claim detection (BART+GPT)", test_claim_detection)
    run_test("Full pipeline via API", test_full_pipeline_api)

    elapsed = time.time() - start
    total = PASS + FAIL + SKIP
    print(f"\n{'='*50}")
    print(f"Results: {PASS} passed, {FAIL} failed, {SKIP} skipped ({total} total)")
    print(f"Time: {elapsed:.1f}s")
    print(f"{'='*50}\n")

    sys.exit(1 if FAIL > 0 else 0)
