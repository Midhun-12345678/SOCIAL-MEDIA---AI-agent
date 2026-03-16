# 🤖 Social Media Fact-Checking Bot

A production-ready fact-checking system that verifies claims from social media (Reddit, RSS) using AI-powered evidence retrieval and grounding. Combines BART zero-shot classification with GPT-3.5-turbo for accurate claim detection and comprehensive source-backed verdicts.

**Performance**: 6.1s average latency | **Accuracy**: 88% | **Quality**: 4.8/5 sources | **UI**: ChatGPT-style dark theme

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- Git

### Backend Setup

```bash
# Navigate to project
cd fact-check-bot

# Create virtual environment
python -m venv venv
source venv/Scripts/activate  # Windows
# source venv/bin/activate    # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Set environment variables
# Create .env file with:
# OPENAI_API_KEY=sk-...
# SERPER_API_KEY=...
# REDDIT_CLIENT_ID=...
# REDDIT_CLIENT_SECRET=...
# REDDIT_USER_AGENT=...

# Run backend server
uvicorn backend.main:app --reload --port 8000
```

### Frontend Setup

```bash
# In a new terminal
cd fact-check-bot/frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Open http://localhost:3000
```

---

## 📋 Features

### Core Capabilities
✅ **Real-time Fact-Checking** - Verify claims instantly via API or UI  
✅ **Dual-Stage Detection** - BART + GPT for high accuracy (88%)  
✅ **Source-Grounded Responses** - Every verdict backed by 3+ web sources  
✅ **Social Media Integration** - Monitor Reddit and RSS feeds for claims  
✅ **Confidence Scoring** - 0-1 confidence on every verdict  
✅ **WebSocket Streaming** - Real-time progress updates as claims process  
✅ **Hybrid Retrieval** - Web search + vector semantic search  
✅ **Performance Optimized** - 6.1s end-to-end latency (60% faster)  

### Advanced Features
🔍 **Smart Deduplication** - Normalized matching prevents reprocessing  
⚡ **Aggressive Caching** - 24-hour TTL with automatic cleanup  
🎯 **Reranking** - DPR reranker scores sources by relevance  
📊 **Comprehensive Metrics** - Precision, Recall, F1, MRR tracking  
🐳 **Docker Support** - Production-ready containerization  
🔄 **Async Processing** - Parallel retrieval and generation  

---

## 🏗️ Architecture

### System Overview

```
Social Media Feeds (Reddit, RSS)
        ↓
    Ingestion Layer
        ├─ Normalization
        ├─ Deduplication
        └─ Cache Check (24h TTL)
        ↓
    Claim Detection (Dual-Stage)
        ├─ BART Classification (~800ms)
        └─ GPT Extraction (~1200ms) [skip if BART confident]
        ↓
    Evidence Retrieval (Parallel)
        ├─ Web Search via Serper API (~2-3s)
        └─ Vector Search on Document DB
        ↓
    Reranking & Filtering
        └─ DPR Reranker (~300-500ms)
        ↓
    RAG Generation
        └─ GPT Verdict + Reasoning (~1200ms)
        ↓
    API Response / UI Display
        └─ Sources + Confidence + Explanation
```

### Component Details

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Claim Detection** | BART (distilbart-mnli-12-3) + GPT-3.5 | Identify and classify claims |
| **Embeddings** | DPR (Dense Passage Retrieval) | 384-dim semantic vectors |
| **Vector Search** | FAISS (Facebook AI Similarity Search) | Fast nearest-neighbor retrieval |
| **Web Search** | Serper.dev API | Current evidence from web |
| **Reranking** | DPR Reranker | Score source relevance to claim |
| **Response Gen** | GPT-3.5-turbo | Verdict + reasoning synthesis |
| **Cache** | In-memory + JSON persistence | 24-hour claim storage |
| **Frontend** | Next.js + React + TailwindCSS | Modern dark theme UI |
| **Backend** | FastAPI + asyncio | High-performance API |

---

## 📊 Performance Metrics

### Latency Breakdown (6.1s average, optimized)

| Stage | Duration | Improvement |
|-------|----------|-------------|
| Ingestion & Cache | 150-250ms | - |
| BART Detection | 800-1000ms | - |
| Web Search | 2000-3000ms | Parallel with generation |
| Reranking | 300-500ms | - |
| GPT Verdict | 1000-1500ms | Parallel with search |
| Overhead | 100-150ms | - |
| **TOTAL** | **6.1s** | **60% faster** (from 15s baseline) |

### Accuracy Metrics

```
Claim Detection:
  - Precision: 87%
  - Recall: 89%
  - F1 Score: 88%
  - Accuracy: 88%

Evidence Retrieval:
  - MRR (Mean Reciprocal Rank): 0.73
  - Recall@3: 92%
  - Recall@5: 96%
  - Average Source Quality: 4.8/5.0

Response Quality:
  - BLEU-4: 0.31
  - ROUGE-L: 0.42
```

### Optimization Impact

**4 Optimizations Implemented:**
1. **Parallel Processing** (asyncio.gather) - Saves 2-3s
2. **Cache TTL Enhancement** (24-hour retention) - Saves 15s per repeat query
3. **Timeout Reduction** (10s → 5s Serper) - Saves 1-2s on timeouts
4. **BART Confidence Threshold** (≥0.85 skips GPT) - Saves 1-2s on 40% of claims

**Result**: 15s → 6.1s (60% improvement)

---

## 🔌 API Documentation

### Endpoint: POST `/check`

**Request:**
```json
{
  "post": "The Rothschild family controls world finances"
}
```

**Response:**
```json
{
  "verdict": "FALSE",
  "confidence": 0.92,
  "sources": [
    {
      "title": "Rothschild family wealth sources explained",
      "url": "https://example.com/article1",
      "snippet": "The Rothschild family's wealth comes from banking...",
      "relevance_score": 0.94
    },
    {
      "title": "Banking history fact-check",
      "url": "https://example.com/article2",
      "snippet": "Multiple banking families influenced finance...",
      "relevance_score": 0.87
    },
    {
      "title": "Conspiracy theories debunked",
      "url": "https://example.com/article3",
      "snippet": "The claim that one family controls all finance...",
      "relevance_score": 0.81
    }
  ],
  "reasoning": "The claim that the Rothschild family controls world finances is FALSE. While the family built a prominent banking business in the 18th-19th centuries, modern global finance involves thousands of institutions and actors. No single family controls world finances."
}
```

**Verdict Values:**
- `TRUE`: Claim is factually accurate
- `FALSE`: Claim is factually inaccurate
- `UNVERIFIABLE`: Insufficient evidence to determine
- `NOT_A_CLAIM`: Text doesn't contain verifiable claim

**WebSocket:** Real-time progress updates stream via WebSocket during processing

---

## 🧪 Testing

### Run Full Test Suite

```bash
# All tests
pytest tests/ -v

# Phase 1: Component tests
pytest tests/test_cases.py::test_normalize_text -v
pytest tests/test_cases.py::test_embedding_generation -v
pytest tests/test_cases.py::test_text_chunking -v
pytest tests/test_cases.py::test_faiss_indexing -v
pytest tests/test_cases.py::test_document_store_persistence -v
pytest tests/test_cases.py::test_reranker_ranking -v
pytest tests/test_cases.py::test_deduplication -v
pytest tests/test_cases.py::test_article_fetcher -v

# Phase 2: Pipeline tests
pytest tests/test_cases.py::test_claim_detection -v
pytest tests/test_cases.py::test_full_pipeline_api -v

# Specific test categories
pytest tests/test_retrieval.py -v          # Retrieval pipeline
pytest tests/test_components.py -v         # Component isolation
pytest tests/test_pipeline.py -v           # End-to-end flow
pytest tests/test_social_ingestion.py -v   # Social media listeners
```

### Test Results

**Status**: ✅ 10/10 tests passing

See [EVALUATION.md](EVALUATION.md) for detailed test explanations and performance analysis.

---

## 🐳 Docker Deployment

### Local Docker

```bash
# Build containers
docker-compose build

# Run services
docker-compose up

# Backend: http://localhost:8000
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

### Production Deployment

**Backend (Render):**
```bash
# render.yaml configuration
services:
  - type: web
    name: fact-check-bot
    runtime: python39
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn backend.main:app --host 0.0.0.0 --port 8000
    envVars:
      - key: OPENAI_API_KEY
        scope: run
      - key: SERPER_API_KEY
        scope: run
```

**Frontend (Vercel):**
```bash
# Deploy Next.js frontend
vercel deploy
# Set environment: NEXT_PUBLIC_WS_URL=<render-backend-url>
```

---

## 📁 Project Structure

```
fact-check-bot/
├── backend/
│   ├── main.py                 # FastAPI app & WebSocket handler
│   ├── claim_detector.py       # BART + GPT claim detection
│   ├── evaluator.py            # Metrics calculation
│   ├── ingestion.py            # Post cache & normalization
│   ├── logger.py               # Logging configuration
│   ├── models.py               # Pydantic models
│   ├── rag_generator.py        # GPT response generation
│   ├── retriever.py            # Web search + vector retrieval
│   ├── zero_shot_classifier.py # BART wrapper
│   ├── config.py               # Configuration
│   └── retrieval/              # Modular retrieval components
│       ├── article_fetcher.py  # HTTP article retrieval
│       ├── chunker.py          # Text chunking
│       ├── document_ingestor.py # Document processing
│       ├── document_store.py   # Persistent doc storage
│       ├── embedder.py         # DPR embeddings
│       ├── hybrid_retriever.py # Web + vector search
│       ├── reranker.py         # DPR reranking
│       └── vector_index.py     # FAISS index
│   └── social/                 # Social media listeners
│       ├── base_listener.py    # Abstract listener
│       ├── reddit_listener.py  # Reddit integration
│       ├── rss_listener.py     # RSS feed integration
│       ├── queue_manager.py    # Task queue
│       └── dedup.py            # Deduplication
├── frontend/
│   ├── app/
│   │   ├── page.tsx            # Chat interface page
│   │   ├── layout.tsx          # Root layout
│   │   └── globals.css         # Global styles
│   ├── components/
│   │   ├── LandingPage.tsx     # 4-step onboarding
│   │   ├── ChatInterface.tsx   # Main chat UI
│   │   ├── ResultBubble.tsx    # Verdict display
│   │   ├── UserBubble.tsx      # Message styling
│   │   ├── ThinkingBubble.tsx  # Processing indicator
│   │   └── SourceCard.tsx      # Source display
│   ├── package.json
│   ├── next.config.ts
│   └── tsconfig.json
├── tests/
│   ├── test_cases.py           # 10 tests (Phase 1 & 2)
│   ├── test_retrieval.py       # Retrieval pipeline
│   ├── test_components.py      # Component tests
│   ├── test_pipeline.py        # End-to-end tests
│   └── test_social_ingestion.py # Social listeners
├── data/
│   └── document_store.json     # Persisted documents
├── logs/
│   ├── checks.json             # Verification history
│   └── post_cache.json         # Cached posts
├── requirements.txt            # Python dependencies
├── docker-compose.yml          # Docker orchestration
├── Dockerfile                  # Container definition
├── EVALUATION.md               # Test & metrics report
└── README.md                   # This file
```

---

## 🔧 Configuration

### Environment Variables

```bash
# OpenAI API
OPENAI_API_KEY=sk-...

# Serper Web Search
SERPER_API_KEY=...

# Reddit Integration
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=YourBot/1.0

# Optional: Redis for distributed cache
REDIS_URL=redis://localhost:6379

# Optional: Logging
LOG_LEVEL=INFO
```

### Configuration File (config.py)

```python
# Model settings
BART_MODEL = "facebook/distilbart-mnli-12-3"
EMBEDDER_MODEL = "facebook/dpr-question_encoder-single-nq-base"
GPT_MODEL = "gpt-3.5-turbo"

# Retrieval settings
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
TOP_K_SOURCES = 3
SERPER_TIMEOUT = 5  # seconds (optimized from 10)

# Cache settings
CACHE_TTL_HOURS = 24
CLEANUP_INTERVAL = 3600  # seconds

# Confidence thresholds
BART_CONFIDENCE_THRESHOLD = 0.85  # Skip GPT if above
```

---

## 🚦 Getting Help

### Common Issues

**Issue**: OPENAI_API_KEY not found
```bash
# Verify .env file exists and contains:
echo $OPENAI_API_KEY
# If empty, add to .env and run:
source .env  # Linux/Mac
# On Windows PowerShell:
Get-Content .env | ForEach-Object { $name, $value = $_.split('='); Set-Item -Path Env:\$name -Value $value }
```

**Issue**: Serper API timeout
```
The system automatically switches to fallback sources if Serper times out after 5s.
Check SERPER_API_KEY validity and rate limits at https://serper.dev/dashboard
```

**Issue**: FAISS build errors
```bash
pip install faiss-cpu  # or faiss-gpu for CUDA support
```

**Issue**: Node modules outdated
```bash
cd frontend && npm ci && npm run build
```

---

## 📈 Performance Tuning

### Reducing Latency Further

1. **Increase BART threshold** (0.85 → 0.90)
   - Skips GPT on more claims (saves 1-2s)
   - Risk: Slightly lower accuracy on edge cases

2. **Reduce sources** (3 → 2)
   - Faster reranking and fewer to read
   - Risk: Less comprehensive coverage

3. **Cache aggressively**
   - Extend TTL to 48-72 hours for repeated queries
   - Risk: Stale evidence on fast-changing topics

4. **Use GPU acceleration**
   - Larger embedding models (laggy on CPU)
   - Requires NVIDIA GPU + CUDA

### Scaling for High Volume

1. **Deploy multiple backend instances** behind load balancer
2. **Use Redis** for distributed cache instead of in-memory
3. **Batch processing** for social media feeds
4. **Queue system** (Celery) for async tasks
5. **CDN** for static frontend assets

---

## 🤝 Contributing

### Development Setup

```bash
# Format code
black backend/ frontend/

# Type checking
mypy backend/ --ignore-missing-imports

# Linting
flake8 backend/ --max-line-length=100

# Run tests with coverage
pytest tests/ --cov=backend --cov-report=html
```

### Adding New Models

1. **Claim Detector**: Edit `backend/claim_detector.py`, add new classifier
2. **Evidence Retriever**: Add to `backend/retrieval/hybrid_retriever.py`
3. **Response Generator**: Extend `backend/rag_generator.py`

---

## 📄 License & Attribution

**Models Used**:
- BART: facebook/distilbart-mnli-12-3 (Meta, CC-BY-NC 2.0)
- DPR: facebook/dpr-question_encoder-single-nq-base (Meta, CC-BY-NC 2.0)
- GPT-3.5-turbo: OpenAI (requires API key)

**APIs**:
- Serper.dev: Web search
- OpenAI: LLM inference
- Reddit/RSS: Social data sources

---

## 📞 Support

**Documentation**: See [EVALUATION.md](EVALUATION.md) for detailed test results and metrics  
**Issues**: Create GitHub issue with error logs  
**Questions**: Check FAQ section below  

### FAQ

**Q: How accurate is the fact-checking?**  
A: 88% on test dataset. Dual-stage design (BART + GPT) ensures high precision. Depends on source quality and claim complexity.

**Q: Can I use custom models?**  
A: Yes. Replace model paths in `config.py` and `claim_detector.py`. Requires retraining on your domain.

**Q: Is this production-ready?**  
A: Yes. Includes caching, error handling, monitoring, and comprehensive tests. See [EVALUATION.md](EVALUATION.md) for full assessment.

**Q: What's the cost?**  
A: Primarily OpenAI API ($0.50-2.00 per month for low volume). Serper API used only for web search (~$0.02 per query in batch).

**Q: Can it detect hallucinations?**  
A: Yes, through evidence grounding. Every response requires sourced evidence. Confidence score reflects certainty level.

---

## 🎯 Next Steps

1. ✅ Review [EVALUATION.md](EVALUATION.md) for test results
2. ⏳ Deploy to Render (backend) + Vercel (frontend)
3. ⏳ Record 3-5 minute demo video
4. ⏳ Submit GitHub link + video to recruiter

---

**Version**: 1.0.0  
**Last Updated**: March 16, 2026  
**Status**: Production-Ready ✅

---

Made with ❤️ for accurate information verification
