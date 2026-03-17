---
title: Fact Check Bot
emoji: 🔍
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---

# 🔍 Fact-Check & Q&A Social Media Bot

An intelligent social media monitoring bot that detects factual claims in posts, verifies them through real-time web search, and responds with AI-generated verdicts grounded in retrieved evidence.

**Performance**: 6.1s average latency | **FEVER Score**: 0.67 | **NOT A CLAIM accuracy**: 100% | **UI**: ChatGPT-style dark theme

---

## 🔗 Live Demo
- **Frontend**: https://social-media-ai-agent-bice.vercel.app
- **Backend API**: https://midhunpa-fact-check-bot.hf.space
- **API Docs**: https://midhunpa-fact-check-bot.hf.space/docs

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

### Backend Setup
```bash
cd fact-check-bot
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python -m spacy download en_core_web_sm
cp .env.example .env
# Add your API keys to .env
uvicorn backend.main:app --reload --port 8000
```

### Frontend Setup
```bash
cd fact-check-bot/frontend
npm install
npm run dev
# Open http://localhost:3000
```

---

## 📋 Features

### Core Capabilities
✅ **Real-time Fact-Checking** — Verify claims instantly via WebSocket UI  
✅ **Two-Stage Claim Detection** — NLI transformer + GPT for high accuracy  
✅ **Hybrid Evidence Retrieval** — Web search + FAISS vector index + reranker  
✅ **RAG-Grounded Responses** — GPT reads retrieved evidence, not memory  
✅ **Social Media Ingestion** — Reddit and RSS feed listeners  
✅ **Confidence Scoring** — 0-1 confidence on every verdict  
✅ **WebSocket Streaming** — Real-time thinking steps shown in UI  
✅ **NER + Dependency Parsing** — spaCy enriches search queries  
✅ **Full Evaluation Suite** — BLEU, ROUGE, FEVER, MRR, F1 all implemented  

### Advanced Features
🔍 **Smart Deduplication** — SHA-256 normalized cache prevents reprocessing  
⚡ **Request Caching** — Repeated claims return in under 1ms  
🎯 **Cross-Encoder Reranking** — Scores chunks by relevance to claim  
📊 **Live Metrics Endpoint** — /evaluate computes metrics from real logs  
🐳 **Docker Deployment** — Models baked into image, no cold-start downloads  
🔄 **Async Throughout** — All blocking calls in thread pool executor  

---

## 🏗️ Architecture
```
Social Media Post (or Reddit/RSS feed)
        ↓
┌─────────────────────────────────────┐
│  INGESTION (ingestion.py)           │
│  • Remove URLs, emojis, mentions    │
│  • Expand slang, normalize caps     │
│  • spaCy NER: extract PERSON, ORG  │
│  • SHA-256 cache check              │
└─────────────────────────────────────┘
        ↓
┌─────────────────────────────────────┐
│  CLAIM DETECTION (claim_detector)   │
│  Stage 1: NLI zero-shot (BART)      │
│    → "factual claim" vs opinion     │
│  Stage 2: GPT extraction            │
│    → clean searchable claim text    │
│  Combined confidence: 0.4×BART      │
│                      + 0.6×GPT      │
└─────────────────────────────────────┘
        ↓
┌─────────────────────────────────────┐
│  HYBRID RETRIEVAL (retrieval/)      │
│  • Serper.dev → top 5 web results  │
│  • Fetch full articles              │
│  • Chunk → embed → FAISS index      │
│  • Cross-encoder rerank top 5       │
└─────────────────────────────────────┘
        ↓
┌─────────────────────────────────────┐
│  RAG GENERATION (rag_generator.py)  │
│  GPT reads evidence chunks only     │
│  → TRUE / FALSE / UNVERIFIABLE      │
│  → Natural language response        │
│  → Cited source indices             │
└─────────────────────────────────────┘
        ↓
   WebSocket → Frontend UI
   Logging → logs/checks.json
   Cache → logs/post_cache.json
```

---

## 🧠 Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| LLM | OpenAI GPT-3.5-turbo | Claim extraction + verdict generation |
| NLI Classifier | cross-encoder/nli-MiniLM2-L6-H768 | Zero-shot claim classification |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 | Semantic chunk embeddings |
| Reranker | cross-encoder/ms-marco-MiniLM-L-6-v2 | Evidence relevance scoring |
| Vector Search | FAISS IndexFlatL2 | Fast semantic retrieval |
| NER + Parsing | spaCy en_core_web_sm | Named entity extraction |
| Web Search | Serper.dev (Google Search API) | Real-time evidence retrieval |
| Backend | FastAPI + WebSocket | Async REST + streaming API |
| Frontend | Next.js + Tailwind CSS | Conversational UI |
| Deployment | HuggingFace Spaces + Vercel | Free production hosting |

---

## 📊 Evaluation Results

### Live API Test Results (15 Tests)

| Category | Tests | Passed | Pass Rate |
|---|---|---|---|
| FALSE claim detection | 5 | 4 | 80% |
| TRUE claim detection | 5 | 3 | 60% |
| UNVERIFIABLE detection | 2 | 0 | 0% |
| NOT A CLAIM detection | 3 | 3 | 100% |
| **Overall** | **15** | **10** | **66.67%** |

### Key Metrics
```
FEVER Score:        0.67
Average Latency:    6,122ms
Latency Target:     under 5,000ms
NOT A CLAIM:        100% accurate
FALSE detection:    80% accurate
```

### Evaluation Metrics Implemented (evaluator.py)
- Claim Detection: Precision, Recall, F1, Accuracy
- Retrieval: MRR, Recall@K (K=1,3,5)
- Generation: BLEU-4, ROUGE-1/2/L, FEVER Score
- Latency: Mean, P50, P95, P99, % under 5s
- Robustness: Accuracy by category and noise level

See [EVALUATION.md](EVALUATION.md) for full report.

---

## 🔌 API Reference

### POST `/check`
Fact-check a social media post.

**Request:**
```json
{"post": "Einstein failed math in school"}
```

**Response:**
```json
{
  "original_post": "Einstein failed math in school",
  "is_claim": true,
  "extracted_claim": "Einstein failed math in school",
  "verdict": "FALSE",
  "response": "Einstein did not fail math. He mastered calculus by age 15.",
  "sources": [
    {
      "title": "Did Einstein Really Fail Math?",
      "url": "https://www.ripleys.com/stories/einstein-fail-math",
      "snippet": "The common rumor that he failed a math test is simply untrue."
    }
  ],
  "confidence": 0.74,
  "latency_ms": 6194,
  "bart_label": "factual claim",
  "bart_score": 0.36,
  "detection_method": "bart+gpt"
}
```

### WebSocket `/ws`
Real-time pipeline with progress events.

Sends stage events as processing occurs:
```
{"stage": "normalizing", "message": "Cleaning text..."}
{"stage": "classifying", "message": "Running BART classification..."}
{"stage": "extracting", "message": "Claim identified: Einstein failed math"}
{"stage": "retrieving", "message": "Searching web for evidence..."}
{"stage": "generating", "message": "Generating verdict with RAG..."}
{"stage": "complete", "result": {...}}
```

### Other Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | /health | Health check |
| GET | /model-status | BART loaded, cache entries |
| GET | /evaluate | Compute metrics from logs |
| GET | /logs | Recent check history |
| GET | /simulate | 5 simulated demo posts |
| GET | /docs | Swagger UI |

---

## 🧪 Testing

### Run Live API Tests (15 posts)
```bash
cd fact-check-bot
python test_cases.py
```

Tests cover: FALSE claims, TRUE claims, UNVERIFIABLE claims,
opinions, questions — including noisy social media text
with emojis, slang, and caps.

### Run Component Tests
```bash
pytest tests/ -v
```

---

## 🌐 Deployment

### Backend — HuggingFace Spaces (Docker)
All ML models baked into Docker image at build time.
No cold-start downloads. 16GB RAM free tier.
```bash
git remote add hfspace https://huggingface.co/spaces/midhunpa/fact-check-bot
git push hfspace main --force
```

Live at: https://midhunpa-fact-check-bot.hf.space

### Frontend — Vercel
```bash
cd frontend
vercel deploy
```

Set environment variables in Vercel:
```
NEXT_PUBLIC_WS_URL  = wss://midhunpa-fact-check-bot.hf.space/ws
NEXT_PUBLIC_API_URL = https://midhunpa-fact-check-bot.hf.space
```

Live at: https://social-media-ai-agent-bice.vercel.app

### Local Docker
```bash
docker-compose up --build
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

---

## 🔧 Environment Variables
```bash
OPENAI_API_KEY=sk-...
SERPER_API_KEY=...
GPT_MODEL=gpt-3.5-turbo
LOG_FILE=logs/checks.json

# Optional — social ingestion
INGESTION_ENABLED=false
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=fact-check-bot/1.0
REDDIT_SUBREDDITS=worldnews+science+technology
RSS_FEEDS=https://feeds.arstechnica.com/arstechnica/index
```

---

## 📁 Project Structure
```
fact-check-bot/
├── backend/
│   ├── main.py                  # FastAPI app + WebSocket endpoint
│   ├── claim_detector.py        # Two-stage BART + GPT detection
│   ├── zero_shot_classifier.py  # NLI model singleton loader
│   ├── retriever.py             # Serper.dev web search
│   ├── rag_generator.py         # RAG verdict generation
│   ├── ingestion.py             # Text normalization + spaCy NER
│   ├── evaluator.py             # All evaluation metrics
│   ├── logger.py                # JSON audit logging
│   ├── models.py                # Pydantic request/response schemas
│   ├── config.py                # Environment configuration
│   ├── retrieval/               # Hybrid retrieval pipeline
│   │   ├── hybrid_retriever.py  # Web + vector search combined
│   │   ├── embedder.py          # Sentence transformer embeddings
│   │   ├── vector_index.py      # FAISS index management
│   │   ├── reranker.py          # Cross-encoder reranking
│   │   ├── article_fetcher.py   # Full article retrieval
│   │   ├── chunker.py           # 512-token document chunking
│   │   ├── document_store.py    # Persistent chunk storage
│   │   └── document_ingestor.py # Article processing pipeline
│   └── social/                  # Proactive ingestion
│       ├── reddit_listener.py   # asyncpraw Reddit polling
│       ├── rss_listener.py      # RSS feed polling
│       ├── queue_manager.py     # Async task queue
│       ├── dedup.py             # Normalized deduplication
│       └── base_listener.py     # Abstract listener base
├── frontend/                    # Next.js conversational UI
│   └── app/
│       ├── page.tsx             # WebSocket chat interface
│       └── components/          # ResultBubble, ThinkingBubble etc
├── tests/                       # Test suite
├── test_cases.py                # 15 live API tests
├── EVALUATION.md                # Full evaluation report
├── TECHNICAL_REPORT.md          # System design report
├── Dockerfile                   # HuggingFace Spaces deployment
├── docker-compose.yml           # Local development
└── requirements.txt             # Python dependencies
```

---

## 💡 Solution Approach

**Why NLI Zero-Shot Classification?**
No large labeled social media claim dataset exists publicly.
NLI generalizes to any claim type without training data —
satisfying the zero-shot constraint in the requirements.

**Why Live Web Search Instead of Vector Database?**
Fact-checking requires current information. A pre-built
vector index cannot contain today's news. Serper.dev
retrieves fresh evidence at query time. RAG pattern
preserved — retrieve then generate.

**Why Hybrid Retrieval?**
Web search alone returns ranked URLs. Fetching full articles,
chunking, and cross-encoder reranking ensures the most
relevant passages reach GPT. This reduces hallucination
compared to using article summaries alone.

**Why WebSocket Instead of REST for UI?**
WebSocket allows the UI to show each pipeline stage as it
executes — normalizing, classifying, retrieving, generating.
This provides transparency into the pipeline and better
perceived performance.

---

## ⚠️ Known Limitations

1. **Latency** — 6.1s average exceeds 5s target on CPU free tier
2. **UNVERIFIABLE** — System underuses this verdict, defaults to FALSE
3. **Nuanced facts** — Some TRUE claims marked FALSE due to retrieval
   of articles with caveats (e.g. "technically Mauna Kea is taller")

---

## 📄 License

MIT License

**Models**: cross-encoder/nli-MiniLM2-L6-H768, 
sentence-transformers/all-MiniLM-L6-v2,
cross-encoder/ms-marco-MiniLM-L-6-v2 (Apache 2.0)

**APIs**: OpenAI GPT-3.5-turbo, Serper.dev

---

**Version**: 1.0.0 | **Last Updated**: March 17, 2026 | **Status**: Production ✅
```

---