import json
import os
import textwrap


def make_md_cell(text: str) -> dict:
    """Create a markdown cell from a multi-line string."""
    cleaned = textwrap.dedent(text).lstrip("\n")
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in cleaned.splitlines()],
    }


def make_code_cell(code: str) -> dict:
    """Create a code cell from a multi-line string."""
    cleaned = textwrap.dedent(code).lstrip("\n")
    return {
        "cell_type": "code",
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": [line + "\n" for line in cleaned.splitlines()],
    }


def build_notebook() -> dict:
    cells = []

    # SECTION 1 - Title and project overview (markdown-only)
    cells.append(
        make_md_cell(
            '''# SECTION 1 - Title and project overview

# FactCheckBot: End-to-End Fact-Checking Demo (Live API)

This Google Colab notebook demonstrates the full **FactCheckBot** pipeline using the **already-deployed** backend API, without running any servers locally. The system is designed for **social media fact-checking**: it ingests noisy posts, normalizes text, detects factual claims, retrieves evidence via hybrid search, and generates RAG-grounded verdicts.

**Key capabilities demonstrated in this notebook:**

- Robust ingestion and normalization of noisy social media text (slang, emojis, URLs) via [`normalize_text()`](fact-check-bot/backend/ingestion.py:37).
- Two-stage claim detection pipeline (NLI/BART + GPT) from [`claim_detector`](fact-check-bot/backend/claim_detector.py:61) and [`ZeroShotClassifier`](fact-check-bot/backend/zero_shot_classifier.py:20).
- Hybrid retrieval over live web search (Serper.dev) plus vector index and cross-encoder reranking, orchestrated by [`hybrid_retrieve()`](fact-check-bot/backend/retrieval/hybrid_retriever.py:61).
- RAG-style verdict generation (TRUE / FALSE / UNVERIFIABLE) grounded in retrieved evidence via [`rag_generator`](fact-check-bot/backend/rag_generator.py:52).
- Evaluation and latency metrics exposed via `/evaluate` and implemented in [`evaluator`](fact-check-bot/backend/evaluator.py:34).

**Live links:**

- Project README (source code overview): [`fact-check-bot README`](fact-check-bot/README.md:1)
- Frontend (Next.js chat UI): https://social-media-ai-agent-bice.vercel.app
- Backend API (Hugging Face Space): https://midhunpa-fact-check-bot.hf.space
- API docs (OpenAPI): https://midhunpa-fact-check-bot.hf.space/docs

**Tech stack summary:**

- **Backend**: FastAPI app in [`main.py`](fact-check-bot/backend/main.py:1) with hybrid retrieval combining Serper.dev web search ([`retrieve_evidence()`](fact-check-bot/backend/retriever.py:12)), FAISS vector index ([`VectorIndex`](fact-check-bot/backend/retrieval/vector_index.py:11)), sentence-transformer embeddings ([`embed_texts()`](fact-check-bot/backend/retrieval/embedder.py:25)), and cross-encoder reranker ([`rerank()`](fact-check-bot/backend/retrieval/reranker.py:25)). GPT-3.5 powers both claim extraction and RAG generation, and a zero-shot NLI classifier provides fast **NOT A CLAIM** filtering.
- **Frontend**: Next.js + Tailwind chat interface (see [`ChatInterface`](fact-check-bot/frontend/app/components/ChatInterface.tsx:1)) with WebSocket streaming of pipeline stages, plus UI components like [`ResultBubble`](fact-check-bot/frontend/app/components/ResultBubble.tsx:1) and [`ThinkingBubble`](fact-check-bot/frontend/app/components/ThinkingBubble.tsx:1).
- **Infra & tooling**: JSON logging ([`logger`](fact-check-bot/backend/logger.py:1)), evaluation suite ([`EVALUATION.md`](fact-check-bot/EVALUATION.md:1)), caching via `PostCache` in [`ingestion`](fact-check-bot/backend/ingestion.py:70), and deployment to Hugging Face Spaces (backend) + Vercel (frontend).

In the following sections, we connect to the **live backend** at `https://midhunpa-fact-check-bot.hf.space`, explore normalization and claim detection, inspect evidence retrieval and RAG verdicts, and finally run the canonical 15-case evaluation used in the project.'''
        )
    )

    # SECTION 2 - Install dependencies
    cells.append(
        make_md_cell(
            '''# SECTION 2 - Install dependencies

This section installs the only extra dependency needed for running this notebook in Google Colab: **`requests`**.

- The notebook talks directly to the **already-deployed** backend at `https://midhunpa-fact-check-bot.hf.space`.
- We do **not** run the FastAPI server, load models, or start any Docker containers locally.
- All heavy lifting (BART classifier, embeddings, FAISS, OpenAI calls, Serper.dev search, logging, evaluation) happens in the remote backend defined in [`main.py`](fact-check-bot/backend/main.py:1).

Installing `requests` explicitly ensures a consistent experience in Colab, even though it may already be available by default.'''
        )
    )

    cells.append(
        make_code_cell(
            '''# Install the only external dependency needed in this notebook: `requests`.
!pip install -q requests'''
        )
    )

    # SECTION 3 - Connect to live backend
    cells.append(
        make_md_cell(
            '''# SECTION 3 - Connect to live backend

In this section we:

- Import `requests`, `json`, and `time`.
- Define the base API URL for the deployed backend: `https://midhunpa-fact-check-bot.hf.space`.
- Implement small helper functions:
  - `get(url, **kwargs)`: wraps `requests.get` with a default timeout and basic error handling.
  - `post_json(url, payload, **kwargs)`: wraps `requests.post` for JSON payloads.
- Call `GET /health` to verify that the backend is reachable and healthy.

The same base URL powers both:

- The production frontend (Next.js UI) at https://social-media-ai-agent-bice.vercel.app.
- The backend API routes documented in [`fact-check-bot README`](fact-check-bot/README.md:171).

If the `/health` check fails (network issues, backend down, etc.), we print a clear message instead of crashing the notebook, so the rest of the notebook remains readable.'''
        )
    )

    cells.append(
        make_code_cell(
            '''import json
import time
from typing import Any, Dict, Optional

import requests


API_URL = "https://midhunpa-fact-check-bot.hf.space"


def resolve_url(path_or_url: str) -> str:
    """Resolve a relative path like "/health" against the global API_URL."""
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return path_or_url
    return API_URL.rstrip("/") + "/" + path_or_url.lstrip("/")


def get(url: str, timeout: float = 15.0, **kwargs) -> Optional[requests.Response]:
    """Thin wrapper around requests.get with timeout and basic error handling.

    Returns the Response object on success, or None if the request fails.
    """

    full_url = resolve_url(url)
    try:
        resp = requests.get(full_url, timeout=timeout, **kwargs)
        print(f"GET {full_url} -> {resp.status_code}")
        return resp
    except requests.exceptions.RequestException as e:
        print(f"[GET] Request to {full_url} failed: {e}")
        return None


def post_json(url: str, payload: Dict[str, Any], timeout: float = 30.0, **kwargs) -> Optional[requests.Response]:
    """Thin wrapper around requests.post for JSON payloads.

    Returns the Response object on success, or None if the request fails.
    """

    full_url = resolve_url(url)
    try:
        resp = requests.post(full_url, json=payload, timeout=timeout, **kwargs)
        print(f"POST {full_url} -> {resp.status_code}")
        return resp
    except requests.exceptions.RequestException as e:
        print(f"[POST] Request to {full_url} failed: {e}")
        return None


# Ping the live backend to confirm it is healthy.
health_resp = get("/health", timeout=10.0)

if health_resp is None:
    print("Health check failed: could not reach backend API.")
else:
    try:
        health_json = health_resp.json()
    except ValueError:
        print("Health check failed: /health did not return valid JSON.")
        health_json = None

    if health_json is not None:
        print("/health JSON:")
        print(json.dumps(health_json, indent=2))

        status = health_json.get("status")
        if status == "healthy":
            print("Backend status: healthy ✅")
        else:
            print(f"Backend status is not 'healthy' (status={status!r}). The API may still be starting up or degraded.")
'''
        )
    )

    # SECTION 4 - Demonstrate ingestion and text normalization
    cells.append(
        make_md_cell(
            '''# SECTION 4 - Demonstrate ingestion and text normalization

The ingestion layer cleans and normalizes noisy social media text before claim detection and retrieval. The core logic lives in [`normalize_text()`](fact-check-bot/backend/ingestion.py:37) and performs several key transformations:

- **URL stripping**: removes `http://`, `https://`, and `www.` links.
- **Mention and hashtag handling**: removes `@user` handles and converts `#hashtag` to plain text.
- **Emoji removal**: drops common emoji ranges to reduce noise.
- **Slang expansion**: maps chat slang (e.g., `omg`, `idk`, `tbh`, `lmao`) to clearer English using `SLANG_MAP` from [`ingestion`](fact-check-bot/backend/ingestion.py:21).
- **Case normalization**: softens SHOUTING words (e.g., `SO GOOD` → `So good`).
- **Punctuation & whitespace cleanup**: collapses repeated `!` / `?`, normalizes `...`, and trims spaces.

In this section we:

1. Implement a **local mirror** `normalize_text_local` in pure Python (`re` only) that approximates the backend behavior for demonstration.
2. Create a noisy example post containing emojis, repeated punctuation, slang, and a URL, and show original vs locally-normalized text.
3. Call the live `/simulate` endpoint to view server-side normalized examples.
4. Call `/check` on the same noisy post to show how the backend handles noisy input and returns fields like `original_post`, `is_claim`, `extracted_claim`, and `verdict`.

The local function is only for visualization; the actual production logic always runs in the backend.'''
        )
    )

    cells.append(
        make_code_cell(
            '''import re


def normalize_text_local(text: str) -> str:
    """Lightweight local mirror of backend normalize_text for illustration.

    This function intentionally mirrors the behavior of
    [`normalize_text()`](fact-check-bot/backend/ingestion.py:37) conceptually,
    but is implemented here in a simplified way without any external deps.
    """

    # Remove URLs
    text = re.sub(r"https?://\S+|www\.\S+", "", text)

    # Remove @mentions and strip # from hashtags
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"#(\w+)", r"\\1", text)

    # Remove common emoji ranges
    emoji_pattern = re.compile(
        "["  # start character class
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F9FF"  # transport & map symbols
        "\u2702-\u27B0"          # dingbats
        "]+",
        flags=re.UNICODE,
    )
    text = emoji_pattern.sub(" ", text)

    # Slang expansion (subset of SLANG_MAP from ingestion.py)
    slang_map = {
        r"\bomg\b": "oh my god",
        r"\bidk\b": "I do not know",
        r"\btbh\b": "to be honest",
        r"\blmao\b": "laughing",
        r"\brn\b": "right now",
        r"\bu\b": "you",
    }
    for pattern, replacement in slang_map.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Light case normalization for ALL CAPS words (excluding very short tokens)
    words = text.split()
    normalized_words = []
    for w in words:
        if len(w) > 4 and w.isupper():
            w = w.capitalize()
        normalized_words.append(w)
    text = " ".join(normalized_words)

    # Collapse repeated punctuation and extra spaces
    text = re.sub(r"[!?]{2,}", "!", text)
    text = re.sub(r"\.{2,}", "...", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


# Example noisy social media post
noisy_post = (
    "omg this PIZZA is SO GOOD rn!!! check this out: "
    "https://example.com/best-pizza 😍🔥 idk if i can ever eat anywhere else tbh lmao!!!"
)

print("ORIGINAL POST:")
print(noisy_post)
print("\nLOCALLY NORMALIZED POST:")
print(normalize_text_local(noisy_post))


# Call the live /simulate endpoint to show server-side normalization examples
print("\n--- Live /simulate examples (server-side normalization) ---")
simulate_resp = get("/simulate", timeout=20.0)

if simulate_resp is None:
    print("Failed to call /simulate on the live backend.")
else:
    try:
        simulate_data = simulate_resp.json()
    except ValueError:
        print("/simulate did not return valid JSON.")
        simulate_data = []

    # Expect a list of objects with text + normalized fields, but handle flexibly
    for i, item in enumerate(simulate_data[:5]):
        original = (
            item.get("text")
            or item.get("original_post")
            or item.get("post")
            or ""
        )
        normalized = (
            item.get("normalized")
            or item.get("normalized_text")
            or ""
        )
        print(f"[{i}] text=\"{original}\"")
        if normalized:
            print(f"    normalized=\"{normalized}\"")


# Call /check on the same noisy post to demonstrate end-to-end handling
print("\n--- Live /check on noisy input ---")
check_resp = post_json("/check", {"post": noisy_post}, timeout=60.0)

if check_resp is None:
    print("Failed to call /check on the live backend.")
else:
    try:
        check_data = check_resp.json()
    except ValueError:
        print("/check did not return valid JSON.")
        check_data = {}

    fields_of_interest = [
        "original_post",
        "is_claim",
        "extracted_claim",
        "verdict",
    ]

    for key in fields_of_interest:
        print(f"{key}: {check_data.get(key)}")
'''
        )
    )

    # SECTION 5 - Demonstrate claim detection
    cells.append(
        make_md_cell(
            '''# SECTION 5 - Demonstrate claim detection

FactCheckBot uses a **two-stage claim detection pipeline** to decide whether an input is a factual claim and to extract a clean claim span:

1. **Stage 1 — NLI / BART zero-shot classifier**: implemented by [`ZeroShotClassifier`](fact-check-bot/backend/zero_shot_classifier.py:20), which uses `cross-encoder/nli-MiniLM2-L6-H768` to classify text into labels like `"factual claim"`, `"personal opinion"`, `"question"`, and `"joke or sarcasm"`.
2. **Stage 2 — GPT-based claim extractor**: implemented in [`claim_detector`](fact-check-bot/backend/claim_detector.py:61), which refines borderline cases and extracts a focused, searchable claim string.

The backend combines signals from both stages to compute `is_claim`, `bart_label`, `bart_score`, and a final `detection_method` field (e.g., `"bart+gpt"`, `"gpt-only"`).

In this section we send a small set of curated examples through the live `/check` endpoint, covering:

- Pure opinions
- Pure questions
- Jokes / sarcasm
- Clear factual statements

We then print a compact table showing for each post:

- `text` (truncated for readability)
- `is_claim`
- `verdict`
- `bart_label`
- `bart_score`
- `detection_method`'''
        )
    )

    cells.append(
        make_code_cell(
            '''from typing import List, Dict


def truncate(text: str, max_len: int = 70) -> str:
    """Utility to truncate long strings for compact printing."""

    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


test_posts: List[Dict[str, str]] = [
    {
        "type": "opinion",
        "text": "omg this pizza is so good i cant even rn",
    },
    {
        "type": "question",
        "text": "what time does the library close on sundays?",
    },
    {
        "type": "joke",
        "text": "Monday should be illegal lmao",
    },
    {
        "type": "factual",
        "text": "Elon Musk bought Twitter for $44 billion in 2022",
    },
    {
        "type": "factual",
        "text": "Water boils at 100 degrees Celsius at sea level",
    },
]


results = []
for item in test_posts:
    text = item["text"]
    print("\n--- Checking post ---")
    print(text)
    resp = post_json("/check", {"post": text}, timeout=60.0)
    if resp is None:
        print("Request failed; skipping.")
        continue
    try:
        data = resp.json()
    except ValueError:
        print("Invalid JSON from /check; skipping.")
        continue

    row = {
        "type": item["type"],
        "text": text,
        "is_claim": data.get("is_claim"),
        "verdict": data.get("verdict"),
        "bart_label": data.get("bart_label"),
        "bart_score": data.get("bart_score"),
        "detection_method": data.get("detection_method"),
    }
    results.append(row)


print("\n=== Claim detection summary ===")
header = f"{'type':<10} {'text':<70} {'is_claim':<8} {'verdict':<12} {'bart_label':<18} {'bart_score':<10} {'method':<12}"
print(header)
print("-" * len(header))

for r in results:
    print(
        f"{r['type']:<10} "
        f"{truncate(r['text']):<70} "
        f"{str(r['is_claim']):<8} "
        f"{str(r['verdict']):<12} "
        f"{str(r['bart_label']):<18} "
        f"{str(round(r['bart_score'], 3) if isinstance(r['bart_score'], (int, float)) else r['bart_score']):<10} "
        f"{str(r['detection_method']):<12}"
    )
'''
        )
    )

    # SECTION 6 - Demonstrate evidence retrieval
    cells.append(
        make_md_cell(
            '''# SECTION 6 - Demonstrate evidence retrieval

For factual claims, the system retrieves supporting (or refuting) evidence using a **hybrid retrieval pipeline**:

- Live web search via Serper.dev is implemented in [`retrieve_evidence()`](fact-check-bot/backend/retriever.py:12), which builds an entity-aware query using spaCy-based NER from [`extract_entities`](fact-check-bot/backend/ingestion.py:204).
- Retrieved URLs are ingested and chunked into passages using:
  - [`VectorIndex`](fact-check-bot/backend/retrieval/vector_index.py:11)
  - [`DocumentStore`](fact-check-bot/backend/retrieval/document_store.py:22)
  - [`embed_texts()`](fact-check-bot/backend/retrieval/embedder.py:25)
  - [`chunk_text()`](fact-check-bot/backend/retrieval/chunker.py:14)
- These components are orchestrated by [`hybrid_retrieve()`](fact-check-bot/backend/retrieval/hybrid_retriever.py:61), which combines web search + vector search.
- A cross-encoder-based reranker ([`rerank()`](fact-check-bot/backend/retrieval/reranker.py:25)) scores chunks by relevance to the extracted claim.

In this section we:

- Send a clearly factual claim to `/check`.
- Extract the `sources` field from the response.
- Pretty-print each evidence source (index, title, URL, shortened snippet) to show what the RAG generator reads.

If the backend cannot retrieve evidence (e.g., missing Serper API key or network outage), we print a warning instead of failing.'''
        )
    )

    cells.append(
        make_code_cell(
            '''claim_text = "Elon Musk bought Twitter for $44 billion in 2022"

print("Sending claim to /check for evidence retrieval demo:")
print(claim_text)

resp = post_json("/check", {"post": claim_text}, timeout=90.0)

if resp is None:
    print("Request to /check failed; cannot demonstrate evidence retrieval.")
else:
    try:
        data = resp.json()
    except ValueError:
        print("/check did not return valid JSON; cannot parse sources.")
        data = {}

    sources = data.get("sources") or []

    if not isinstance(sources, list) or not sources:
        print("No sources returned by backend for this claim.")
    else:
        print("\nRetrieved sources:")
        for i, src in enumerate(sources):
            title = src.get("title") or "(no title)"
            url = src.get("url") or "(no url)"
            snippet = src.get("snippet") or ""
            short_snippet = (snippet[:200] + "...") if len(snippet) > 200 else snippet

            print(f"[{i}] {title}")
            print(f"    URL: {url}")
            if short_snippet:
                print(f"    Snippet: {short_snippet}")
'''
        )
    )

    # SECTION 7 - Demonstrate RAG generation
    cells.append(
        make_md_cell(
            '''# SECTION 7 - Demonstrate RAG generation

The RAG (Retrieval-Augmented Generation) component is implemented in [`rag_generator`](fact-check-bot/backend/rag_generator.py:52). It takes as input:

- The original post
- The extracted factual claim
- A list of evidence sources (titles, URLs, snippets)

Using OpenAI GPT-3.5-turbo, it returns a JSON object with:

- `verdict`: one of `"TRUE"`, `"FALSE"`, or `"UNVERIFIABLE"`
- `response`: a short natural-language explanation (2–4 sentences)
- `confidence`: a 0.0–1.0 confidence score
- `used_source_indices`: which evidence items were most influential

The `/check` endpoint integrates this RAG layer and may also emit `"NOT_A_CLAIM"` for non-claim inputs, based on the upstream claim detector.

In this section we probe three scenarios via `/check`:

1. A **TRUE** claim
2. A **FALSE** claim
3. An **UNVERIFIABLE** / conspiracy-style claim

We then display, for each post:

- `verdict`
- `confidence`
- `response` (truncated for readability)
- Number of sources and up to the first two sources (title + URL)

Because this uses a live model and live web search, the exact verdicts may differ from the expected labels; the goal is to illustrate behavior, not enforce a fixed ground truth here.'''
        )
    )

    cells.append(
        make_code_cell(
            '''import textwrap


scenario_posts = [
    {
        "label": "TRUE (expected)",
        "post": "Elon Musk bought Twitter for $44 billion in 2022",
    },
    {
        "label": "FALSE (expected)",
        "post": "The Great Wall of China is visible from space",
    },
    {
        "label": "UNVERIFIABLE (expected)",
        "post": "The government is hiding evidence of alien contact",
    },
]


def short_response(text: str, max_chars: int = 320) -> str:
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


for scenario in scenario_posts:
    print("\n=== Scenario:", scenario["label"], "===")
    print("Post:", scenario["post"])

    resp = post_json("/check", {"post": scenario["post"]}, timeout=90.0)
    if resp is None:
        print("Request failed; skipping this scenario.")
        continue

    try:
        data = resp.json()
    except ValueError:
        print("Invalid JSON from /check; skipping.")
        continue

    verdict = data.get("verdict")
    confidence = data.get("confidence")
    response_text = data.get("response") or ""
    sources = data.get("sources") or []

    print(f"verdict: {verdict}")
    print(f"confidence: {confidence}")
    print("response:")
    print(textwrap.indent(short_response(response_text), prefix="  "))

    if isinstance(sources, list):
        print(f"sources returned: {len(sources)}")
        for i, src in enumerate(sources[:2]):
            title = src.get("title") or "(no title)"
            url = src.get("url") or "(no url)"
            print(f"  [{i}] {title} -> {url}")
    else:
        print("sources field is not a list; backend schema may have changed.")
'''
        )
    )

    # SECTION 8 - Run all 15 test cases
    cells.append(
        make_md_cell(
            '''# SECTION 8 - Run all 15 test cases

This section evaluates the **live API** on a canonical suite of 15 test cases drawn from the project assessment and encoded in [`test_cases.py`](fact-check-bot/test_cases.py:1). The cases span four categories:

- `FALSE` — clearly false factual claims
- `TRUE` — clearly true factual claims (under reasonable assumptions like sea level)
- `UNVERIFIABLE` — conspiracy-like or underspecified claims that the system should not over-confidently label TRUE/FALSE
- `NOT_A_CLAIM` — opinions, questions, and jokes that should be filtered out by the claim detector

We hardcode the same 15 texts and their expected verdicts, send each to `/check`, and compute:

- Per-case pass/fail based on whether `verdict == expected`
- Overall accuracy across all 15 cases
- Per-category accuracy where possible

Finally, we build a markdown table string (no external libraries) summarizing results so that assessors can easily inspect the live system behavior directly from Colab.'''
        )
    )

    cells.append(
        make_code_cell(
            '''test_cases = [
    {"id": 1, "text": "COVID vaccines contain microchips that track your location", "expected": "FALSE"},
    {"id": 2, "text": "The Great Wall of China is visible from space", "expected": "FALSE"},
    {"id": 3, "text": "Einstein failed math in school", "expected": "FALSE"},
    {"id": 4, "text": "Napoleon was only 5 feet 2 inches tall", "expected": "FALSE"},
    {"id": 5, "text": "Humans only use 10% of their brain", "expected": "FALSE"},
    {"id": 6, "text": "Elon Musk bought Twitter for $44 billion in 2022", "expected": "TRUE"},
    {"id": 7, "text": "The Amazon River is the largest river by discharge", "expected": "TRUE"},
    {"id": 8, "text": "Mount Everest is the tallest mountain above sea level", "expected": "TRUE"},
    {"id": 9, "text": "Water boils at 100 degrees Celsius at sea level", "expected": "TRUE"},
    {"id": 10, "text": "The US has won the most Olympic gold medals in history", "expected": "TRUE"},
    {"id": 11, "text": "5G towers are causing health problems in nearby residents", "expected": "UNVERIFIABLE"},
    {"id": 12, "text": "The government is hiding evidence of alien contact", "expected": "UNVERIFIABLE"},
    {"id": 13, "text": "omg this pizza is so good i cant even rn", "expected": "NOT_A_CLAIM"},
    {"id": 14, "text": "what time does the library close on sundays?", "expected": "NOT_A_CLAIM"},
    {"id": 15, "text": "Monday should be illegal lmao", "expected": "NOT_A_CLAIM"},
]


per_case_results = []
category_stats = {}


for case in test_cases:
    print(f"\n--- Test case {case['id']} ---")
    print(case["text"])
    resp = post_json("/check", {"post": case["text"]}, timeout=90.0)
    if resp is None:
        print("Request failed; marking as failed.")
        actual_verdict = None
    else:
        try:
            data = resp.json()
        except ValueError:
            print("Invalid JSON; marking as failed.")
            data = {}
        actual_verdict = data.get("verdict")

    expected = case["expected"]
    passed = actual_verdict == expected
    print(f"expected={expected}, actual={actual_verdict}, pass={passed}")

    per_case_results.append(
        {
            "id": case["id"],
            "text": case["text"],
            "expected": expected,
            "actual": actual_verdict,
            "passed": passed,
        }
    )

    category_stats.setdefault(expected, {"total": 0, "passed": 0})
    category_stats[expected]["total"] += 1
    if passed:
        category_stats[expected]["passed"] += 1


total_cases = len(per_case_results)
total_passed = sum(1 for r in per_case_results if r["passed"])
overall_accuracy = (total_passed / total_cases * 100.0) if total_cases else 0.0


print("\n=== Per-case summary ===")
header = f"{'id':<3} {'text':<70} {'expected':<13} {'actual':<13} {'pass':<5}"
print(header)
print("-" * len(header))

for r in per_case_results:
    short_text = truncate(r["text"], max_len=70)
    print(
        f"{r['id']:<3} {short_text:<70} {r['expected']:<13} {str(r['actual']):<13} {str(r['passed']):<5}"
    )


print("\n=== Aggregate stats ===")
print(f"Total cases: {total_cases}")
print(f"Passed: {total_passed} ({overall_accuracy:.2f}% accuracy)")

for category, stats in category_stats.items():
    cat_total = stats["total"]
    cat_passed = stats["passed"]
    cat_acc = (cat_passed / cat_total * 100.0) if cat_total else 0.0
    print(f"Category {category}: {cat_passed}/{cat_total} passed ({cat_acc:.2f}% accuracy)")


# Build a markdown table string summarizing all results
lines = []
lines.append("| id | text | expected | actual | pass |")
lines.append("|---|------|----------|--------|------|")

for r in per_case_results:
    short_text = truncate(r["text"], max_len=60).replace("|", "\\|")
    lines.append(
        f"| {r['id']} | {short_text} | {r['expected']} | {r['actual']} | {r['passed']} |"
    )

markdown_table = "\n".join(lines)

print("\n=== Markdown table (copy-pastable) ===")
print(markdown_table)
'''
        )
    )

    # SECTION 9 - Evaluation metrics
    cells.append(
        make_md_cell(
            '''# SECTION 9 - Evaluation metrics

The `/evaluate` endpoint computes metrics from logged runs using the evaluation module described in [`evaluator`](fact-check-bot/backend/evaluator.py:1) and documented in [`EVALUATION.md`](fact-check-bot/EVALUATION.md:1). These metrics include:

- Claim detection metrics: precision, recall, F1, accuracy
- Retrieval metrics: MRR, Recall@K (K = 1, 3, 5)
- Generation & factuality metrics: BLEU, ROUGE, FEVER score
- Latency metrics: mean, min, max, percentiles (p50, p95, p99), and percentage of requests under 5s
- Robustness breakdowns: performance by category and noise level

In this section we call `GET /evaluate` on the live backend and:

1. Pretty-print the full JSON response with indentation.
2. Extract key latency metrics if present (e.g., `mean_ms`, `p50_ms`, `p95_ms`, `p99_ms`, `under_5s_pct`).

If the backend has not yet accumulated logs (common just after deployment), `/evaluate` may return an `error` field (e.g., "No logs found"); we surface that clearly instead of failing.'''
        )
    )

    cells.append(
        make_code_cell(
            '''eval_resp = get("/evaluate", timeout=60.0)

if eval_resp is None:
    print("Failed to reach /evaluate endpoint.")
else:
    try:
        eval_data = eval_resp.json()
    except ValueError:
        print("/evaluate did not return valid JSON.")
        eval_data = None

    if isinstance(eval_data, dict) and eval_data.get("error"):
        print("/evaluate error:")
        print(eval_data.get("error"))
    elif isinstance(eval_data, dict):
        print("Full /evaluate JSON:")
        print(json.dumps(eval_data, indent=2))

        # Try to extract latency metrics from common keys
        latency = (
            eval_data.get("latency_ms")
            or eval_data.get("latency")
            or eval_data.get("latency_stats")
            or {}
        )

        if isinstance(latency, dict):
            keys_of_interest = [
                "mean_ms",
                "min_ms",
                "max_ms",
                "p50_ms",
                "p95_ms",
                "p99_ms",
                "under_5s_pct",
            ]

            print("\nLatency metrics (if available):")
            for k in keys_of_interest:
                if k in latency:
                    print(f"  {k}: {latency[k]}")
        else:
            print("Latency metrics not found in /evaluate response.")
    else:
        print("/evaluate returned an unexpected response structure.")
'''
        )
    )

    # SECTION 10 - Architecture explanation in markdown (markdown-only)
    cells.append(
        make_md_cell(
            '''# SECTION 10 - Architecture explanation

This section summarizes the overall **FactCheckBot** architecture and pipeline, tying together the components referenced throughout the notebook. It is intended as a self-contained explanation for assessors reviewing the system.

## 1. Ingestion & normalization

Incoming social media posts (from APIs, Reddit, RSS feeds, or the chat UI) are first passed through the ingestion layer in [`ingestion.py`](fact-check-bot/backend/ingestion.py:1). The key function [`normalize_text()`](fact-check-bot/backend/ingestion.py:37) performs:

- Removal of URLs, @mentions, and conversion of hashtags to plain tokens
- Emoji stripping using a Unicode range-based regex
- Slang expansion via `SLANG_MAP` (e.g., `omg` → `oh my god`, `idk` → `I do not know`)
- Soft normalization of SHOUTING words (e.g., `COVID` vs. `covid`)
- Cleanup of repeated punctuation and whitespace

Normalized posts are represented as `SocialPost` dataclass instances in [`SocialPost`](fact-check-bot/backend/ingestion.py:10), which capture the raw text, normalized text, platform, author, timestamp, and additional metadata. A caching layer `PostCache` in [`ingestion`](fact-check-bot/backend/ingestion.py:70) avoids reprocessing identical normalized posts by storing hashed results on disk.

## 2. Claim detection

Claim detection is implemented as a **two-stage process** orchestrated in [`claim_detector`](fact-check-bot/backend/claim_detector.py:61):

1. **Zero-shot NLI classifier (BART layer)** — The [`ZeroShotClassifier`](fact-check-bot/backend/zero_shot_classifier.py:20) wraps a Hugging Face `zero-shot-classification` pipeline using `cross-encoder/nli-MiniLM2-L6-H768`. It predicts among candidate labels such as `"factual claim"`, `"personal opinion"`, `"question"`, and `"joke or sarcasm"`, and exposes a helper `is_factual_claim` to decide whether the top label and score exceed a configurable threshold.
2. **GPT-based extractor** — For borderline cases and to obtain a clean claim span, the GPT-based extractor in [`claim_detector`](fact-check-bot/backend/claim_detector.py:61) rewrites the input into a focused, search-friendly factual claim text.

This yields fields like `is_claim`, `bart_label`, `bart_score`, `extracted_claim`, and `detection_method` (e.g., `"bart+gpt"` vs `"gpt-only"`). Non-claims are filtered early and ultimately receive the `"NOT_A_CLAIM"` verdict at the API level.

## 3. Hybrid retrieval

For detected factual claims, the system uses a **hybrid retrieval pipeline** implemented under [`backend/retrieval`](fact-check-bot/backend/retrieval/__init__.py:1) and orchestrated by [`hybrid_retrieve()`](fact-check-bot/backend/retrieval/hybrid_retriever.py:61):

1. **Live web search** — [`retrieve_evidence()`](fact-check-bot/backend/retriever.py:12) queries Serper.dev with an entity-augmented query built from [`extract_entities`](fact-check-bot/backend/ingestion.py:204). This returns top web results (URLs, titles, snippets).
2. **Article ingestion & chunking** — Full articles are fetched using [`article_fetcher`](fact-check-bot/backend/retrieval/article_fetcher.py:1), split into manageable segments via [`chunk_text()`](fact-check-bot/backend/retrieval/chunker.py:14), and stored in a [`DocumentStore`](fact-check-bot/backend/retrieval/document_store.py:22).
3. **Vector indexing & semantic search** — Text chunks are embedded with [`embed_texts()`](fact-check-bot/backend/retrieval/embedder.py:25) and inserted into a FAISS-based [`VectorIndex`](fact-check-bot/backend/retrieval/vector_index.py:11) to enable fast semantic similarity search over evidence.
4. **Cross-encoder reranking** — Candidate chunks are reranked using a cross-encoder scorer in [`rerank()`](fact-check-bot/backend/retrieval/reranker.py:25), which evaluates claim–chunk pairs for fine-grained relevance.

The **key design choice** is to rely on **live web search instead of a pure pre-built vector database**:

- Ensures **freshness** for breaking news and evolving facts.
- Provides coverage for **long-tail claims** that would be impractical to pre-index.
- Avoids the need to embed and store "all of the web" in advance.
- Still leverages a **lightweight vector index** for high-value retrieved pages, enabling precise semantic matching within those documents.

## 4. RAG generation

Once evidence is retrieved, the RAG generator in [`rag_generator`](fact-check-bot/backend/rag_generator.py:52) constructs a prompt summarizing:

- The original social media post
- The extracted claim
- A formatted list of evidence snippets (numbered with titles and URLs)

The OpenAI GPT-3.5-based component then produces structured JSON with:

- `verdict` ∈ {`"TRUE"`, `"FALSE"`, `"UNVERIFIABLE"`}
- `response` — a concise natural-language explanation
- `confidence` — a real-valued confidence score
- `used_source_indices` — which evidence entries were most influential

At the API level, non-claim posts are assigned `"NOT_A_CLAIM"` without invoking the RAG generator. This separation keeps latency low for opinions/questions and focuses OpenAI usage on genuine factual claims.

## 5. Evaluation & logging

The system records each fact-check request and response into JSON logs using the logging utilities in [`logger`](fact-check-bot/backend/logger.py:1). The evaluation module in [`evaluator`](fact-check-bot/backend/evaluator.py:34), described in detail in [`EVALUATION.md`](fact-check-bot/EVALUATION.md:1), consumes these logs to compute:

- Claim detection accuracy and F1
- Retrieval metrics such as MRR and Recall@K
- RAG generation metrics like BLEU, ROUGE, and FEVER score
- Latency distributions (mean, percentiles, and SLA-style thresholds)

The `/logs` and `/evaluate` endpoints exposed by the FastAPI app in [`main.py`](fact-check-bot/backend/main.py:1) provide live visibility into these metrics, making it easy to monitor real-world performance and regressions.

Overall, the architecture combines **fast, cheap signal** (BART-based zero-shot classification and Serper.dev web search) with **slower but more precise reasoning** (GPT-3.5 RAG generation) to deliver transparent, evidence-grounded fact-checks for social media content.'''
        )
    )

    # SECTION 11 - Conclusion (markdown-only)
    cells.append(
        make_md_cell(
            '''# SECTION 11 - Conclusion

This Colab notebook demonstrated the complete **FactCheckBot** pipeline against the **live deployed API** at `https://midhunpa-fact-check-bot.hf.space`, without running any backend services locally.

**What we covered:**

- Verified backend health via `/health` and configured lightweight `requests`-based helpers for HTTP calls.
- Illustrated ingestion and normalization with a local mirror of [`normalize_text()`](fact-check-bot/backend/ingestion.py:37), compared against the server-side `/simulate` endpoint, and showed that noisy posts (emojis, slang, URLs) are still correctly processed by `/check`.
- Explored the two-stage claim detection pipeline (BART NLI + GPT extractor) via `/check`, including `is_claim`, `bart_label`, `bart_score`, and `detection_method` fields.
- Inspected hybrid evidence retrieval outputs (titles, URLs, snippets) for a sample factual claim, showing how Serper.dev + vector search + reranking feed into RAG.
- Examined RAG-generated verdicts and explanations for TRUE, FALSE, and UNVERIFIABLE-style claims.
- Ran the canonical 15-case evaluation suite directly against the live backend and computed simple accuracy and per-category breakdowns, mirroring the behavior of [`test_cases.py`](fact-check-bot/test_cases.py:1).
- Queried `/evaluate` to surface end-to-end metrics, with an emphasis on latency.

**Known limitations and caveats:**

- The system depends on external services (OpenAI, Serper.dev, Hugging Face Spaces, Vercel) and network connectivity; outages or quota limits will impact responses and may cause some notebook cells to print error messages instead of results.
- Live behavior may drift from earlier evaluation snapshots documented in [`EVALUATION.md`](fact-check-bot/EVALUATION.md:1) and [`TECHNICAL_REPORT.md`](fact-check-bot/TECHNICAL_REPORT.md:1), especially as upstream models or the web change.
- Complex, long-tail, or ambiguous claims may incur higher latency and occasionally receive UNVERIFIABLE or incorrect labels, particularly when retrieval surfaces mixed or low-quality evidence.

**Relevant submission links:**

- Source code & documentation: [`fact-check-bot README`](fact-check-bot/README.md:1)
- Technical design report: [`TECHNICAL_REPORT.md`](fact-check-bot/TECHNICAL_REPORT.md:1)
- Live backend (API + docs): https://midhunpa-fact-check-bot.hf.space
- Live frontend (chat UI): https://social-media-ai-agent-bice.vercel.app

This notebook is intended as a single, self-contained artifact for assessors to understand and manually exercise the end-to-end fact-checking system using only a browser and a Colab runtime.'''
        )
    )

    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.10",
                "mimetype": "text/x-python",
                "codemirror_mode": {"name": "ipython", "version": 3},
                "pygments_lexer": "ipython3",
                "nbconvert_exporter": "python",
                "file_extension": ".py",
            },
        },
        "cells": cells,
    }

    return notebook


def main() -> None:
    nb = build_notebook()
    output_path = os.path.join(os.path.dirname(__file__), "FactCheckBot_Colab.ipynb")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=2)
    print(f"Wrote notebook to {output_path}")


if __name__ == "__main__":
    main()

