# Fact-Check Bot — End-to-End Project Documentation

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Diagram](#2-architecture-diagram)
3. [Tech Stack](#3-tech-stack)
4. [Directory Structure](#4-directory-structure)
5. [Data Flow — Step by Step](#5-data-flow--step-by-step)
6. [Backend Deep Dive](#6-backend-deep-dive)
   - 6.1 [Entry Point & Server Lifecycle (`main.py`)](#61-entry-point--server-lifecycle-mainpy)
   - 6.2 [Data Models (`models.py`)](#62-data-models-modelspy)
   - 6.3 [Text Ingestion & Normalization (`ingestion.py`)](#63-text-ingestion--normalization-ingestionpy)
   - 6.4 [Stage 1 — BART Zero-Shot Classification (`zero_shot_classifier.py`)](#64-stage-1--bart-zero-shot-classification-zero_shot_classifierpy)
   - 6.5 [Stage 2 — GPT Claim Extraction (`claim_detector.py`)](#65-stage-2--gpt-claim-extraction-claim_detectorpy)
   - 6.6 [Stage 3 — Evidence Retrieval via Serper (`retriever.py`)](#66-stage-3--evidence-retrieval-via-serper-retrieverpy)
   - 6.7 [Stage 4 — RAG Verdict Generation (`rag_generator.py`)](#67-stage-4--rag-verdict-generation-rag_generatorpy)
   - 6.8 [Logging (`logger.py`)](#68-logging-loggerpy)
   - 6.9 [Evaluation Framework (`evaluator.py`)](#69-evaluation-framework-evaluatorpy)
   - 6.10 [Configuration (`config.py`)](#610-configuration-configpy)
7. [Frontend Deep Dive](#7-frontend-deep-dive)
   - 7.1 [WebSocket Connection](#71-websocket-connection)
   - 7.2 [Real-Time Progress Pipeline](#72-real-time-progress-pipeline)
   - 7.3 [UI Components](#73-ui-components)
8. [API Endpoints Reference](#8-api-endpoints-reference)
9. [Caching Strategy](#9-caching-strategy)
10. [Evaluation Metrics Explained](#10-evaluation-metrics-explained)
11. [Production Readiness Assessment](#11-production-readiness-assessment)
12. [How to Run](#12-how-to-run)
13. [Environment Variables](#13-environment-variables)

---

## 1. Project Overview

This is an **AI-powered Fact-Check Bot** that takes social media posts as input, detects whether they contain verifiable factual claims, retrieves real-time web evidence, and delivers a verdict (**TRUE**, **FALSE**, or **UNVERIFIABLE**) with cited sources.

The system uses a **two-stage claim detection pipeline** (local BART model → OpenAI GPT), a **Retrieval-Augmented Generation (RAG)** architecture for verdict generation, and a **real-time WebSocket** interface to stream progress steps to a Next.js chat frontend.

**Core Workflow in One Sentence:**  
`User Post → Normalize → BART Classification → GPT Claim Extraction → Web Evidence Retrieval → RAG Verdict Generation → Streamed Result`

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (Next.js 16)                         │
│                                                                             │
│   ┌─────────────┐    WebSocket (ws://127.0.0.1:8000/ws)    ┌────────────┐  │
│   │  User Input  │ ──────────────────────────────────────▶  │  Send JSON │  │
│   └─────────────┘                                           └────────────┘  │
│         ▲                                                                   │
│         │  Real-time progress events (received → normalizing →              │
│         │  classifying → extracting → retrieving → generating → complete)   │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  ThinkingBubble (animated steps)  →  ResultBubble (verdict card)   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          BACKEND (FastAPI + Uvicorn)                        │
│                                                                             │
│  ┌──────────────┐     ┌──────────────────────────────────────────────────┐  │
│  │  ingestion.py │     │              CLAIM DETECTION PIPELINE           │  │
│  │               │     │                                                  │  │
│  │ • URL removal │     │  ┌─────────────────┐    ┌────────────────────┐  │  │
│  │ • @mention    │────▶│  │  BART Zero-Shot  │───▶│  GPT-3.5 Turbo    │  │  │
│  │   stripping   │     │  │  (Local Model)   │    │  (Claim Extractor)│  │  │
│  │ • Emoji clean │     │  │                  │    │                    │  │  │
│  │ • Slang map   │     │  │ Confident reject │    │ Extract clean claim│  │  │
│  │ • Normalize   │     │  │ if score > 0.65  │    │ + confidence score │  │  │
│  └──────────────┘     │  └─────────────────┘    └────────────────────┘  │  │
│                        └──────────────┬───────────────────────────────────┘  │
│                                       │                                      │
│                                       ▼                                      │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                        EVIDENCE RETRIEVAL                              │  │
│  │                                                                        │  │
│  │  ┌──────────────┐    ┌───────────────┐    ┌────────────────────────┐  │  │
│  │  │ spaCy NER    │───▶│ Query Builder │───▶│ Serper.dev Google API  │  │  │
│  │  │ (en_core_web │    │ claim + NER   │    │ Top-5 organic results  │  │  │
│  │  │  _sm)        │    │ + "fact check"│    │ + Answer Box           │  │  │
│  │  └──────────────┘    └───────────────┘    └────────────────────────┘  │  │
│  └────────────────────────────────────┬───────────────────────────────────┘  │
│                                       │                                      │
│                                       ▼                                      │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                    RAG VERDICT GENERATION                              │  │
│  │                                                                        │  │
│  │  GPT-3.5 Turbo receives:                                              │  │
│  │  • Original post                                                       │  │
│  │  • Extracted claim                                                     │  │
│  │  • Retrieved evidence (title + URL + snippet for each source)          │  │
│  │                                                                        │  │
│  │  Returns: verdict (TRUE/FALSE/UNVERIFIABLE) + explanation + confidence │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────────┐  │
│  │  PostCache    │    │  Logger      │    │  Evaluator                  │  │
│  │  (SHA-256)    │    │  (JSON file) │    │  (BLEU, ROUGE, FEVER, etc.) │  │
│  └──────────────┘    └──────────────┘    └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend Framework** | FastAPI 0.111+ | Async HTTP + WebSocket server |
| **Server** | Uvicorn | ASGI server for FastAPI |
| **Local ML Model** | `cross-encoder/nli-MiniLM2-L6-H768` via HuggingFace `transformers` | Zero-shot claim classification (BART-based NLI) |
| **LLM** | OpenAI GPT-3.5 Turbo | Claim extraction + RAG verdict generation |
| **NER / NLP** | spaCy `en_core_web_sm` | Named Entity Recognition, dependency parsing, query enhancement |
| **Web Search** | Serper.dev (Google Search API) | Real-time evidence retrieval |
| **Frontend Framework** | Next.js 16.1.6 (React 19) | Chat-based UI |
| **Styling** | Tailwind CSS 4 | Dark-themed responsive design |
| **Communication** | WebSocket (native) | Real-time bidirectional streaming |
| **Validation** | Pydantic v2 | Request/response schema validation |
| **Containerization** | Docker (Dockerfile present, not yet configured) | Deployment packaging |

---

## 4. Directory Structure

```
fact-check-bot/
├── backend/
│   ├── __init__.py                 # Package marker
│   ├── config.py                   # Environment variable loader
│   ├── models.py                   # Pydantic schemas (request/response/enums)
│   ├── main.py                     # FastAPI app, endpoints, WebSocket handler, lifespan
│   ├── ingestion.py                # Text normalization, NER extraction, simulated feed, PostCache
│   ├── zero_shot_classifier.py     # BART zero-shot classification singleton
│   ├── claim_detector.py           # Two-stage claim detection (BART → GPT)
│   ├── retriever.py                # Serper.dev web search for evidence
│   ├── rag_generator.py            # RAG-based GPT verdict generation
│   ├── evaluator.py                # Evaluation metrics (BLEU, ROUGE, FEVER, latency, etc.)
│   └── logger.py                   # JSON file-based check logging
├── frontend/
│   ├── app/
│   │   ├── page.tsx                # Main chat UI (WebSocket client, all components)
│   │   ├── layout.tsx              # Root layout with Geist fonts
│   │   └── globals.css             # Tailwind imports + theme variables
│   ├── package.json                # Next.js 16, React 19, Tailwind 4
│   └── ...config files
├── logs/
│   ├── checks.json                 # Persisted fact-check results
│   └── post_cache.json             # SHA-256 keyed response cache
├── requirements.txt                # Python dependencies
├── DockerFile                      # (Empty — not yet configured)
├── test_cases.py                   # (Empty — not yet configured)
└── .env                            # API keys (not committed)
```

---

## 5. Data Flow — Step by Step

Here is the exact journey of a user query through the entire system, from keystroke to verdict:

### Step 0: Server Startup (Lifespan)

When the FastAPI server starts (`uvicorn backend.main:app`):

1. **BART model loads** — `ZeroShotClassifier.get_instance()` downloads/loads `cross-encoder/nli-MiniLM2-L6-H768` onto GPU (if available) or CPU. This is a **singleton** — loaded once, reused forever.
2. **spaCy model loads** — `en_core_web_sm` is loaded via `_get_spacy_model()` singleton. Prevents 500ms reload penalty on each request.
3. Both load in parallel using `asyncio.gather` with `run_in_executor` (non-blocking).

### Step 1: User Sends a Post (Frontend → Backend)

1. User types/pastes a social media post in the Next.js chat input.
2. On Enter, the frontend sends `{"post": "user text"}` via **WebSocket** to `ws://127.0.0.1:8000/ws`.
3. A `ThinkingBubble` component appears showing animated progress dots.

### Step 2: Text Ingestion & Normalization (`ingestion.py`)

The raw post goes through `ingest_single_post()`:

| Transformation | Example |
|---|---|
| URL removal | `https://t.co/abc` → *(removed)* |
| @mention stripping | `@elonmusk` → *(removed)* |
| Hashtag cleaning | `#Breaking` → `Breaking` |
| Emoji removal | 🔥😂 → *(removed)* |
| Slang expansion | `u`, `ur`, `idk`, `tbh`, `omg`, `ngl`, `fr` → full English |
| ALL-CAPS normalization | `BREAKING` → `Breaking` (words > 4 chars) |
| Excessive punctuation | `!!!???` → `!`, `....` → `...` |
| Whitespace collapse | Multiple spaces → single space |

The result is a `SocialPost` dataclass with a unique `id` (SHA-256 hash of raw text).

**WebSocket progress:** `{"stage": "normalizing", "message": "Cleaning and normalizing text..."}`

### Step 3: Cache Check

Before any AI processing, the normalized text is hashed (SHA-256, first 16 chars) and checked against `PostCache`:
- **Cache HIT** → immediately returns the cached result with `from_cache: true`. Skips all AI stages.
- **Cache MISS** → proceeds to claim detection.

### Step 4: BART Zero-Shot Classification (`zero_shot_classifier.py`)

**Model:** `cross-encoder/nli-MiniLM2-L6-H768` (a DistilBART-based cross-encoder fine-tuned on MultiNLI)

**How it works:**
1. The normalized text is classified against 5 candidate labels via Natural Language Inference (NLI):
   - `"factual claim"`
   - `"personal opinion"`
   - `"question"`
   - `"joke or sarcasm"`
   - `"emotional expression"`
2. The model computes entailment scores for each label. The label with the highest score wins.
3. Decision logic:
   - If top label = `"factual claim"` AND score ≥ 0.40 → **is_claim = True**
   - If top label ≠ `"factual claim"` BUT `factual_claim` score ≥ 0.50 → **is_claim = True** (secondary check)
   - Otherwise → **is_claim = False**

**Fast-reject gate (BART_CONFIDENT_REJECT = 0.65):**
- If BART says NOT a claim with score ≥ 0.65 → **skip GPT entirely**, return `NOT_A_CLAIM` immediately.
- This saves API costs and latency for obvious non-claims like "I love pizza" or "What time is it?"

**WebSocket progress:** `{"stage": "classifying", "message": "Running BART claim classification..."}`

### Step 5: GPT Claim Extraction (`claim_detector.py`)

**Model:** OpenAI GPT-3.5 Turbo (`temperature=0.1`, `max_tokens=150`)

When BART either:
- Classifies the post as a claim, OR
- Is borderline (not confident enough to reject)

...GPT is called as the **second stage**:

1. A system prompt instructs GPT to act as a fact-checking assistant.
2. GPT receives the post and must return structured JSON:
   ```json
   {
     "is_claim": true/false,
     "extracted_claim": "clean, concise, searchable text",
     "reasoning": "one sentence explanation",
     "gpt_confidence": 0.0-1.0
   }
   ```
3. The extracted claim is a **clean, searchable version** of the original messy social media text.

**Confidence fusion:**
- If BART said claim: `combined = 0.4 × bart_score + 0.6 × gpt_confidence`
- If BART was borderline: `combined = gpt_confidence` (GPT gets final say)
- If BART unavailable: `combined = gpt_confidence` (GPT-only fallback)

**WebSocket progress:** `{"stage": "extracting", "message": "Claim identified: <extracted claim>"}`

### Step 6: Evidence Retrieval (`retriever.py`)

**API:** Serper.dev (Google Search API)

1. **spaCy NER runs** on the extracted claim via `extract_entities()`:
   - Extracts named entities (PERSON, ORG, GPE, LOC, DATE, MONEY, etc.)
   - Extracts subject and root verb via dependency parsing
   - Extracts key nouns and proper nouns
2. **Query construction:**
   ```
   query = "{extracted_claim} {entity_names} fact check"
   ```
   The entity names boost search precision (e.g., "Elon Musk bought Twitter" → adds "Elon Musk Twitter" as entity boost).
3. **Serper.dev API call** with `num=5`, `gl=us`, `hl=en`.
4. Up to 5 organic results are extracted as `Source` objects (title, URL, snippet).
5. If an **Answer Box** exists (Google's featured snippet), it gets inserted at position 0 for priority.

**Fallback:** If SERPER_API_KEY is missing or the API call fails, an empty source list is returned and the system continues (RAG proceeds without evidence).

**WebSocket progress:** `{"stage": "retrieving", "message": "Found 5 sources"}`

### Step 7: RAG Verdict Generation (`rag_generator.py`)

**Model:** OpenAI GPT-3.5 Turbo (`temperature=0.2`, `max_tokens=250`)

This is the **Retrieval-Augmented Generation** step — the core of the fact-checking logic:

1. GPT receives a structured prompt containing:
   - The original social media post
   - The extracted claim (from Step 5)
   - All retrieved evidence formatted as numbered blocks:
     ```
     [0] Source Title
     URL: https://...
     Snippet: relevant text from the page
     ```
2. GPT must return structured JSON:
   ```json
   {
     "verdict": "TRUE" | "FALSE" | "UNVERIFIABLE",
     "response": "2-4 sentence natural language explanation",
     "confidence": 0.0-1.0,
     "used_source_indices": [0, 1, 2]
   }
   ```
3. Only the sources GPT actually references (`used_source_indices`) are included in the final response.

**Rules enforced by the system prompt:**
- Verdict must be grounded in the provided evidence only
- If evidence is conflicting → acknowledge honestly
- If evidence is insufficient → return `UNVERIFIABLE`
- Response must be direct and factual, not preachy

**Final confidence calculation:**
```
if bart_score exists:
    final_confidence = 0.4 × bart_score + 0.6 × gpt_confidence
else:
    final_confidence = gpt_confidence
```

**WebSocket progress:** `{"stage": "generating", "message": "Generating verdict with RAG..."}`

### Step 8: Response Delivery

1. The `CheckResponse` Pydantic model is constructed with all fields.
2. The result is **logged** to `logs/checks.json` (append-only JSON array).
3. The result is **cached** in `PostCache` (SHA-256 key → result dict).
4. The result is sent to the frontend:
   ```json
   {"stage": "complete", "result": { ...full CheckResponse... }}
   ```

### Step 9: Frontend Renders Result

1. The `ThinkingBubble` is replaced with a `ResultBubble`.
2. The `ResultBubble` displays:
   - **Verdict badge** (color-coded: green=TRUE, red=FALSE, amber=UNVERIFIABLE, gray=NOT_A_CLAIM)
   - **Confidence percentage**
   - **Cache indicator** (⚡ if from cache)
   - **Natural language response**
   - **Extracted claim** in a highlighted box
   - **Clickable source cards** with title + snippet
   - **Meta footer:** latency, BART label/score, detection method

---

## 6. Backend Deep Dive

### 6.1 Entry Point & Server Lifecycle (`main.py`)

- **Framework:** FastAPI with async lifespan context manager
- **CORS:** Fully open (`allow_origins=["*"]`) — all frontend origins allowed
- **Lifespan:** Pre-loads BART and spaCy models in parallel at startup using `asyncio.gather` + thread pool executors. This ensures the first user request isn't slow.
- **Endpoints:** REST (`/check`, `/evaluate`, `/logs`, `/simulate`, `/model-status`) + WebSocket (`/ws`)
- **Blocking ops:** All ML inference and I/O runs via `run_in_executor` to avoid blocking the async event loop.
- **WebSocket handler:** Full 6-stage progress streaming with error handling and graceful disconnect.

### 6.2 Data Models (`models.py`)

| Model | Role |
|-------|------|
| `Verdict` (Enum) | `TRUE`, `FALSE`, `UNVERIFIABLE`, `NOT_A_CLAIM` |
| `CheckRequest` | Input schema: `{ post: str }` |
| `Source` | Evidence source: `{ title, url, snippet }` |
| `ClaimDetectionResult` | Internal result from claim_detector: `{ is_claim, extracted_claim, reasoning, bart_label, bart_score, combined_confidence }` |
| `CheckResponse` | Full output: `{ original_post, is_claim, extracted_claim, verdict, response, sources[], confidence, latency_ms, bart_label, bart_score, detection_method }` |

All models use **Pydantic v2** for automatic validation and serialization.

### 6.3 Text Ingestion & Normalization (`ingestion.py`)

**Purpose:** Transform messy social media text into clean, model-friendly input.

**Key classes/functions:**

| Component | What It Does |
|-----------|-------------|
| `normalize_text()` | URL/mention/hashtag/emoji removal, slang expansion, caps normalization, punctuation cleanup |
| `SocialPost` (dataclass) | Structured post object with `id`, `text`, `normalized_text`, `platform`, `author`, `timestamp`, `metadata` |
| `PostCache` | SHA-256 based in-memory + file-persisted cache (`logs/post_cache.json`) |
| `extract_entities()` | spaCy NER + dependency parsing → entities, subject, verb, key_terms, entity_string for search |
| `get_simulated_feed()` | Returns 10 hardcoded example posts for testing |
| `ingest_single_post()` | Normalizes raw text and creates a `SocialPost` |

**Slang Map (12 terms):**
`u→you`, `ur→your`, `r→are`, `w/→with`, `idk→I do not know`, `imo→in my opinion`, `tbh→to be honest`, `omg→oh my god`, `lmao→laughing`, `smh→shaking my head`, `ngl→not going to lie`, `fr→for real`

**spaCy Entity Types Extracted:**
`PERSON`, `ORG`, `GPE`, `LOC`, `MONEY`, `DATE`, `PERCENT`, `PRODUCT`, `EVENT`

### 6.4 Stage 1 — BART Zero-Shot Classification (`zero_shot_classifier.py`)

**Model:** `cross-encoder/nli-MiniLM2-L6-H768` (default, configurable via `BART_MODEL` env var)

**Pattern:** Singleton — `ZeroShotClassifier.get_instance()` loads the model once and reuses it.

**Candidate Labels:**
1. `"factual claim"` — verifiable statement about the world
2. `"personal opinion"` — subjective preference
3. `"question"` — interrogative sentence
4. `"joke or sarcasm"` — humor/irony
5. `"emotional expression"` — feelings/reactions

**Decision Logic:**

```
CLAIM_THRESHOLD = 0.40

if top_label == "factual claim" AND top_score >= 0.40:
    return is_claim=True
elif factual_claim_score >= 0.50:        # secondary check
    return is_claim=True
else:
    return is_claim=False
```

**Why this model?**
- Runs locally (no API cost per classification)
- Fast inference (~50-200ms per post)
- Good at filtering obvious non-claims before expensive GPT calls
- Cross-encoder architecture provides better accuracy than bi-encoders for NLI tasks

### 6.5 Stage 2 — GPT Claim Extraction (`claim_detector.py`)

**Two-stage decision tree:**

```
                    BART Classification
                           │
              ┌────────────┼────────────┐
              │            │            │
         NOT a claim   Borderline    IS a claim
         score ≥ 0.65  (uncertain)  score ≥ 0.40
              │            │            │
         STOP ─ return  Call GPT     Call GPT
         NOT_A_CLAIM    (GPT has     (confirm +
         (no GPT cost)  final say)   extract claim)
```

**Weights:**
- `BART_WEIGHT = 0.4` — local model contributes 40% to final confidence
- `GPT_WEIGHT = 0.6` — GPT contributes 60% to final confidence
- `BART_CONFIDENT_REJECT = 0.65` — threshold to skip GPT entirely

**Fallback:** If BART model fails to load or crashes, the system falls back to GPT-only mode. No downtime.

### 6.6 Stage 3 — Evidence Retrieval via Serper (`retriever.py`)

**Search pipeline:**

1. `extract_entities(claim)` → spaCy NER + dependency parsing
2. Build search query: `"{claim} {entity_names} fact check"`
3. POST to `https://google.serper.dev/search` with top-5 results
4. Parse organic results into `Source` objects
5. Prioritize Google Answer Box (inserted at index 0 if present)

**Why Serper.dev?**
- Clean Google SERP JSON API
- Fast (< 1s response)
- Returns structured titles, URLs, and snippets
- Answer Box extraction built-in

**Entity-boosted search example:**
- Claim: `"Einstein failed math in school"`
- spaCy extracts: `PERSON: Einstein`
- Final query: `"Einstein failed math in school Einstein fact check"`

### 6.7 Stage 4 — RAG Verdict Generation (`rag_generator.py`)

**RAG = Retrieval-Augmented Generation**

The key insight: instead of asking GPT to fact-check from its training data (which may be wrong or outdated), we **retrieve fresh evidence from the web** and feed it as context. GPT then acts as a **reasoning engine**, not a knowledge base.

**Prompt structure:**
```
SYSTEM: You are a fact-checking bot. Assess if the claim is TRUE, FALSE,
        or UNVERIFIABLE based ONLY on the provided evidence.

USER:   Original Post: "..."
        Extracted Claim: "..."
        Retrieved Evidence:
        [0] Title - URL - Snippet
        [1] Title - URL - Snippet
        ...
```

**Source attribution:** GPT returns `used_source_indices` — only the sources it actually referenced are included in the response. This prevents source spam.

### 6.8 Logging (`logger.py`)

- Every fact-check result is appended to `logs/checks.json`
- Each entry includes: timestamp, original post, is_claim, extracted_claim, verdict, response, confidence, latency_ms, bart_label, bart_score, detection_method, sources
- `get_logs(limit)` returns the most recent N entries
- Used by the `/evaluate` endpoint to compute aggregate metrics

### 6.9 Evaluation Framework (`evaluator.py`)

A comprehensive evaluation suite with multiple metric families:

| Metric Category | Metrics | Purpose |
|----------------|---------|---------|
| **Claim Detection** | Precision, Recall, F1, Accuracy, TP/FP/FN/TN | How well the system identifies claims vs non-claims |
| **Retrieval** | MRR (Mean Reciprocal Rank), Recall@K (K=1,3,5) | How well evidence retrieval finds relevant sources |
| **Generation — Text Quality** | BLEU (1-4 gram), ROUGE-1, ROUGE-2, ROUGE-L | How well generated responses match reference answers |
| **Generation — Verdict Accuracy** | FEVER Score (SUPPORTS/REFUTES/NOT ENOUGH INFO mapping) | Compatibility with the FEVER benchmark standard |
| **Latency** | Mean, Min, Max, P50, P95, P99, % under 5s | End-to-end response time distribution |
| **Robustness** | Accuracy by category, Accuracy by noise level | Performance across different post types and noise levels |

**FEVER score mapping:**
- `TRUE` → `SUPPORTS`
- `FALSE` → `REFUTES`
- `UNVERIFIABLE` / `NOT_A_CLAIM` → `NOT ENOUGH INFO`

### 6.10 Configuration (`config.py`)

Loads from a `.env` file in the project root:

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENAI_API_KEY` | *(required)* | OpenAI API authentication |
| `SERPER_API_KEY` | *(required)* | Serper.dev search API authentication |
| `GPT_MODEL` | `gpt-3.5-turbo` | Which GPT model to use |
| `LOG_FILE` | `logs/checks.json` | Path to the log file |
| `BART_MODEL` | `cross-encoder/nli-MiniLM2-L6-H768` | HuggingFace model for zero-shot classification |
| `BART_THRESHOLD` | `0.40` | Minimum score for a "factual claim" classification |

---

## 7. Frontend Deep Dive

### 7.1 WebSocket Connection

The frontend establishes a persistent WebSocket connection on mount:

```
ws://127.0.0.1:8000/ws  (configurable via NEXT_PUBLIC_WS_URL)
```

**Auto-reconnect:** On disconnect, the frontend retries every 3 seconds automatically. A green/red dot in the header indicates connection status.

**Protocol:**
- **Client → Server:** `{"post": "user text"}`
- **Server → Client:** Multiple JSON events per request (progress streaming)

### 7.2 Real-Time Progress Pipeline

Each fact-check triggers a sequence of WebSocket events the frontend renders as an animated step-by-step pipeline:

| Stage | Icon | Message |
|-------|------|---------|
| `received` | 📥 | "Post received" |
| `normalizing` | 🧹 | "Cleaning and normalizing text..." |
| `classifying` | 🧠 | "Running BART claim classification..." |
| `extracting` | 🔎 | "Claim identified: {claim}" |
| `retrieving` | 🌐 | "Found {N} sources" |
| `generating` | ✍️ | "Generating verdict with RAG..." |
| `complete` | ✅ | Full result object |
| `error` | ❌ | Error message |

As each stage arrives, the previous step gets a green checkmark (✓) and the new step shows an animated blue pulse. This gives users visibility into what the AI is doing in real-time.

### 7.3 UI Components

| Component | Description |
|-----------|-------------|
| `UserBubble` | Blue right-aligned bubble showing the user's input post |
| `ThinkingBubble` | Gray left-aligned bubble with animated step progression (or bouncing dots if no steps yet) |
| `ResultBubble` | Rich verdict card with color-coded border, badge, response text, extracted claim box, source cards, and meta footer |
| `Home` (page) | Main chat container with header (connection status), scrollable message area, example buttons for empty state, and input area |

**Verdict Colors:**
- `TRUE` → Green border + badge
- `FALSE` → Red border + badge
- `UNVERIFIABLE` → Amber border + badge
- `NOT_A_CLAIM` → Gray border + badge

**Empty State:** Shows 3 clickable example posts to try:
1. "Einstein failed math in school"
2. "The Great Wall of China is visible from space"
3. "Elon Musk bought Twitter for $44 billion"

---

## 8. API Endpoints Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health check — returns `{"status": "ok"}` |
| `POST` | `/check` | Synchronous fact-check (same pipeline, no progress streaming). Body: `{"post": "text"}` |
| `GET` | `/model-status` | Returns BART loaded status, model names, cache entry count |
| `GET` | `/evaluate` | Computes metrics (claim detection, latency, BART usage) from logged results |
| `GET` | `/logs?limit=50` | Returns recent fact-check logs |
| `GET` | `/simulate` | Returns 5 simulated social media posts for testing |
| `WS` | `/ws` | WebSocket endpoint for real-time fact-checking with progress events |

---

## 9. Caching Strategy

**Where:** `PostCache` class in `ingestion.py`

**How:**
1. Normalized text → SHA-256 → first 16 hex chars = cache key
2. On each successful fact-check, the full result dict is stored in-memory AND written to `logs/post_cache.json`
3. On subsequent requests with the same normalized text, the cached result is returned **instantly** with `from_cache: true`

**Benefits:**
- Zero latency for repeated queries
- Zero API costs for cached queries
- Survives server restarts (file-persisted)

**Limitation:** Cache is never invalidated — a claim checked today returns the same result forever. For production, a TTL-based expiry would be needed.

---

## 10. Evaluation Metrics Explained

### Claim Detection Metrics
- **Precision:** Of all posts the system labeled as claims, how many actually are? (Avoids false alarms)
- **Recall:** Of all actual claims, how many did the system catch? (Avoids missed claims)
- **F1 Score:** Harmonic mean of precision and recall (balanced measure)
- **True/False Positives/Negatives:** Confusion matrix values

### Retrieval Metrics
- **MRR (Mean Reciprocal Rank):** How high does the first relevant source appear? (1.0 = always first)
- **Recall@K:** What fraction of relevant sources appear in the top K results?

### Generation Quality Metrics
- **BLEU:** N-gram precision overlap between generated response and reference
- **ROUGE-1/2:** Unigram/bigram overlap (precision + recall + F1)
- **ROUGE-L:** Longest Common Subsequence-based overlap

### Verdict Accuracy
- **FEVER Score:** Compatibility with the FEVER benchmark (SUPPORTS/REFUTES/NOT ENOUGH INFO)

### Latency Metrics
- **P50/P95/P99:** Percentile latencies — P95 means 95% of requests are faster than this value
- **Under 5s %:** Percentage of requests completing in under 5 seconds

---

## 11. Production Readiness Assessment

### What's Done Well (Production-Quality)

| Area | Implementation | Assessment |
|------|---------------|------------|
| **Two-stage claim detection** | Local BART model + GPT for verification | ✅ Cost-efficient, reduces unnecessary API calls |
| **Graceful fallbacks** | BART failure → GPT-only; Serper failure → continue without sources | ✅ No single point of failure |
| **Model pre-loading** | Async parallel loading at startup via lifespan | ✅ First request is fast |
| **Singleton models** | BART and spaCy loaded once globally | ✅ No memory leaks from reloading |
| **SHA-256 caching** | In-memory + file-persisted result cache | ✅ Zero-cost repeated queries |
| **Real-time WebSocket** | 6-stage progress streaming | ✅ Excellent UX |
| **Auto-reconnect** | Frontend retries WebSocket on disconnect | ✅ Resilient connection |
| **Structured logging** | Full result JSON logged with timestamp | ✅ Auditable |
| **Pydantic validation** | Strong request/response schemas | ✅ Input validation at boundary |
| **Comprehensive evaluator** | BLEU, ROUGE, FEVER, MRR, latency percentiles | ✅ Research-grade metrics |
| **NER-enhanced retrieval** | spaCy entity extraction for query boosting | ✅ Better search quality |
| **Text normalization** | Slang, emoji, URL, caps handling | ✅ Social media-ready preprocessing |
| **Async execution** | `run_in_executor` for all blocking operations | ✅ Non-blocking event loop |

### What Needs Work for Production

| Area | Current State | What's Needed | Priority |
|------|--------------|---------------|----------|
| **Authentication** | None — all endpoints are open | API key / JWT auth on all endpoints | 🔴 Critical |
| **Rate limiting** | None | Per-IP or per-user rate limits to prevent abuse | 🔴 Critical |
| **CORS policy** | `allow_origins=["*"]` (wide open) | Restrict to specific frontend domain(s) | 🔴 Critical |
| **Input sanitization** | Basic Pydantic validation only | Max length, content filtering, injection protection | 🟠 High |
| **Cache TTL** | Cache never expires | Add time-based expiry (e.g., 24h) for evolving facts | 🟠 High |
| **Docker** | Dockerfile is empty | Multi-stage build, health checks, non-root user | 🟠 High |
| **Test suite** | `test_cases.py` is empty | Unit tests, integration tests, edge case coverage | 🟠 High |
| **Error handling** | Basic try/catch with fallbacks | Structured error responses, retry logic with backoff for API calls | 🟠 High |
| **Database** | JSON file logging | PostgreSQL / Redis for logs and cache; JSON files don't scale | 🟡 Medium |
| **Secret management** | `.env` file on disk | Use a secret manager (Vault, AWS Secrets Manager, etc.) | 🟡 Medium |
| **Monitoring / Observability** | `logging.info()` calls | Structured logging (JSON), APM integration, health dashboards | 🟡 Medium |
| **Horizontal scaling** | Single-process Uvicorn | Multi-worker, load balancer, external cache (Redis) | 🟡 Medium |
| **GPT prompt injection** | No protection | Validate/sanitize user input before injecting into prompts | 🟡 Medium |
| **Model versioning** | Hardcoded model names | Configurable per-environment, A/B testing support | 🟢 Low |
| **CI/CD** | None | GitHub Actions pipeline for lint, test, build, deploy | 🟢 Low |
| **Frontend metadata** | Default "Create Next App" title | Proper SEO, OG tags, favicon | 🟢 Low |

### Overall Verdict

> **This is a strong proof-of-concept / MVP with well-structured architecture, clear separation of concerns, and intelligent design decisions (two-stage detection, RAG, NER-enhanced retrieval, caching, real-time streaming).** It demonstrates solid ML engineering and full-stack capabilities.
>
> **It is NOT production-ready** due to the absence of authentication, rate limiting, proper error handling, tests, database storage, and containerization. These are the standard gaps between a PoC and production deployment.
>
> **Estimated effort to production-grade:** The architecture is sound — the gaps are infrastructure and security hardening, not fundamental design issues. The codebase is clean and modular enough that adding these features would be additive, not a rewrite.

---

## 12. How to Run

### Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI API key
- Serper.dev API key

### Backend

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Create .env file in project root
# OPENAI_API_KEY=sk-...
# SERPER_API_KEY=...

# Start the server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:3000
```

### Usage

1. Open `http://localhost:3000` in your browser
2. Paste any social media post or claim
3. Watch the real-time pipeline stages execute
4. View the verdict with sources

---

## 13. Environment Variables

Create a `.env` file in the project root (`fact-check-bot/.env`):

```env
OPENAI_API_KEY=sk-your-openai-key-here
SERPER_API_KEY=your-serper-key-here
GPT_MODEL=gpt-3.5-turbo
LOG_FILE=logs/checks.json
BART_MODEL=cross-encoder/nli-MiniLM2-L6-H768
BART_THRESHOLD=0.40
```

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | — | OpenAI API key for GPT calls |
| `SERPER_API_KEY` | Yes | — | Serper.dev API key for web search |
| `GPT_MODEL` | No | `gpt-3.5-turbo` | OpenAI model to use |
| `LOG_FILE` | No | `logs/checks.json` | Path for persisted logs |
| `BART_MODEL` | No | `cross-encoder/nli-MiniLM2-L6-H768` | HuggingFace model ID |
| `BART_THRESHOLD` | No | `0.40` | Minimum score for claim classification |
| `NEXT_PUBLIC_WS_URL` | No | `ws://127.0.0.1:8000/ws` | WebSocket URL for frontend |
