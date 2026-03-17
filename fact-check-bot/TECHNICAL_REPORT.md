# Technical Report: Fact-Check & Q&A Social Media Bot

## 1. System Overview

This system is an automated fact-checking pipeline for social 
media posts. It combines transformer-based NLP models, 
real-time web retrieval, and large language model generation 
to detect factual claims, retrieve supporting evidence, and 
produce grounded verdicts with cited sources.

Two operating modes:
- Reactive: User submits a post via WebSocket, gets verdict
- Proactive: RSS and Reddit listeners continuously ingest 
  posts and queue them for automatic fact-checking

## 2. Architecture

Five modular stages: ingestion, claim detection, evidence 
retrieval, response generation, output delivery.

### 2.1 Ingestion (ingestion.py, social/)

Text normalization pipeline:
- URLs, @mentions, #hashtags removed
- Emojis stripped via Unicode range patterns
- Slang expanded: u→you, tbh→to be honest, omg→oh my god
- Excessive caps normalized, repeated punctuation collapsed

spaCy en_core_web_sm extracts named entities (PERSON, ORG, 
GPE, MONEY, DATE) and dependency relationships. Entities 
enhance search query precision in retrieval.

SHA-256 cache prevents re-processing identical posts.
Cache lookup under 1ms, bypasses full pipeline.

Proactive ingestion: RedditListener polls subreddits via 
asyncpraw. RSSListener fetches RSS feeds at configurable 
intervals. Both feed QueueManager with deduplication.

### 2.2 Claim Detection (claim_detector.py)

Two-stage pipeline:

Stage 1 — NLI Zero-Shot Classification:
Model: cross-encoder/nli-MiniLM2-L6-H768 (33M parameters)
Classification as Natural Language Inference. For each 
candidate label, forms hypothesis: "This text is a {label}"
and computes entailment probability against input text.

Labels: factual claim, personal opinion, question, 
joke or sarcasm, emotional expression

Threshold: score >= 0.40 for factual claim label.

Stage 2 — GPT Claim Extraction:
Model: gpt-3.5-turbo, temperature=0.1, max_tokens=150
Extracts precise claim text in clean searchable language.
Returns confidence score 0.0-1.0.

Combined confidence: 0.4 x BART + 0.6 x GPT

Model loads once at startup via singleton pattern.

### 2.3 Evidence Retrieval (retriever.py, retrieval/)

Hybrid three-layer approach:

Web Search: Serper.dev queries Google in real time.
Query enriched with spaCy NER entities.
Top 5 organic results plus answer box retrieved.
Full articles fetched via newspaper3k.

Vector Indexing: Articles chunked into 512-token segments 
with 50-token overlap. Chunks embedded using 
sentence-transformers/all-MiniLM-L6-v2.
Stored in FAISS IndexFlatL2 for semantic search.

Reranking: cross-encoder/ms-marco-MiniLM-L-6-v2 scores 
each chunk against the original claim. Top 5 most relevant 
chunks selected for generation.

This hybrid approach combines keyword precision with 
semantic relevance and discriminative reranking.

### 2.4 Response Generation (rag_generator.py)

RAG prompt structure:
- System: Role and verdict rules
- User: Original post + claim + top 5 evidence chunks
- GPT reads ONLY retrieved evidence, not training memory

Model: gpt-3.5-turbo, temperature=0.2, max_tokens=250

Verdict logic:
- TRUE: Evidence clearly supports the claim
- FALSE: Evidence clearly refutes the claim  
- UNVERIFIABLE: Evidence conflicting or inconclusive
- NOT_A_CLAIM: No verifiable factual claim detected

### 2.5 Logging and Explainability (logger.py)

Every check logged to logs/checks.json:
timestamp, post, claim, verdict, confidence, latency,
sources used, detection method, BART label and score.

/evaluate endpoint computes live metrics from logs:
Precision, Recall, F1, MRR, Recall@K, BLEU, ROUGE, FEVER.

## 3. Modeling Decisions

### 3.1 Why Zero-Shot Classification

No large-scale labeled social media claim dataset exists 
publicly. NLI approach generalizes to any claim type 
without training data — satisfying the zero-shot / 
few-shot constraint explicitly.

Cross-encoder architecture processes premise and hypothesis 
jointly, giving higher accuracy than bi-encoder for short 
social media texts.

### 3.2 Why Live Web Search Instead of Vector Database

A pre-built vector index cannot contain current events.
Fact-checking requires current information — a post about 
today's news cannot be verified against yesterday's index.

Serper.dev retrieves fresh evidence at query time.
RAG pattern preserved: retrieve then generate.
Retrieval source is web search rather than static corpus.

### 3.3 Why Hybrid Retrieval

Web search returns ranked URLs but not always the most 
semantically relevant passage within an article. Fetching 
full articles, chunking, and cross-encoder reranking 
ensures most relevant passages reach the generation model.
Reduces hallucination risk vs. using article summaries.

## 4. Integration

### 4.1 FastAPI WebSocket

/ws endpoint sends real-time progress events:
received → normalizing → classifying → extracting → 
retrieving → generating → complete

Frontend shows each stage as it executes.

### 4.2 Deployment

Backend: HuggingFace Spaces Docker (16GB RAM free tier)
- All models baked into image at build time
- No cold-start download on each request
- Port 7860, auto-discovered by HF Spaces

Frontend: Vercel (Next.js)
- NEXT_PUBLIC_WS_URL points to HuggingFace
- Automatic deploy on GitHub push

## 5. Evaluation

### 5.1 Test Results (15 Live API Tests)

| Category | Tests | Passed | Rate |
|---|---|---|---|
| FALSE claims | 5 | 4 | 80% |
| TRUE claims | 5 | 3 | 60% |
| UNVERIFIABLE | 2 | 0 | 0% |
| NOT A CLAIM | 3 | 3 | 100% |
| Overall | 15 | 10 | 66.67% |

FEVER Score: 0.67
Average Latency: 6,122ms
Latency target: under 5,000ms

### 5.2 Metrics Implementation (evaluator.py)

All metrics implemented from scratch, no external libraries:
- Precision, Recall, F1, Accuracy
- MRR, Recall@K (K=1,3,5)  
- BLEU-4 with brevity penalty
- ROUGE-1, ROUGE-2, ROUGE-L
- FEVER score (SUPPORTS/REFUTES/NOT ENOUGH INFO)
- Latency: mean, P50, P95, P99, % under 5s
- Robustness by category and noise level

### 5.3 Known Limitations

1. UNVERIFIABLE verdict underused — prompt fix applied
2. Latency exceeds 5s on HuggingFace free CPU tier
3. Some TRUE facts marked FALSE due to nuanced retrieval

## 6. Software Engineering

- Modular: 15+ single-responsibility modules
- Singleton: Models load once, reuse across all requests
- Async: All blocking calls in thread pool executor
- Graceful degradation: BART failure falls back to GPT
- No hardcoded credentials: all via environment variables
- Full audit trail: every check traceable in logs

## 7. Conclusion

The system demonstrates end-to-end fact-checking using 
publicly available models and APIs with zero training data.
Hybrid retrieval combining live web search, vector similarity, 
and cross-encoder reranking represents a production-grade 
architecture. Main limitation is latency on CPU free tier —
addressable with GPU inference.

