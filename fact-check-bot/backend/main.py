from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import logging
import time

from backend.models import CheckRequest, CheckResponse, Verdict
from backend.claim_detector import detect_claim
from backend.retrieval import hybrid_retrieve
from backend.rag_generator import generate_response
from backend.logger import log_check, get_logs
from backend.ingestion import ingest_single_post, get_simulated_feed, PostCache
from backend.zero_shot_classifier import ZeroShotClassifier
from backend.evaluator import (
    compute_claim_detection_metrics, compute_latency_metrics,
    ClaimDetectionSample, GenerationSample
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _load_spacy():
    """Pre-loads spaCy model at startup so first request is not slow."""
    try:
        from backend.ingestion import _get_spacy_model
        _get_spacy_model()
    except Exception as e:
        logger.warning(f"spaCy pre-load failed ({e}) — NER will be skipped at runtime")


async def _load_models_background():
    """Load heavy ML models in background after server starts."""
    logger.info("Loading ML models in background...")

    loop = asyncio.get_event_loop()

    await asyncio.gather(
        loop.run_in_executor(None, ZeroShotClassifier.get_instance),
        loop.run_in_executor(None, _load_spacy),
    )

    from backend.retrieval.embedder import preload_model as preload_embedder
    from backend.retrieval.reranker import preload_reranker
    from backend.retrieval.hybrid_retriever import preload_index

    await asyncio.gather(
        loop.run_in_executor(None, preload_embedder),
        loop.run_in_executor(None, preload_reranker),
        loop.run_in_executor(None, preload_index),
    )

    logger.info("All ML models loaded successfully")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Server starting...")

    # Start model loading in background (non-blocking)
    asyncio.create_task(_load_models_background())

    from backend.config import INGESTION_ENABLED

    if INGESTION_ENABLED:
        from backend.social import start_ingestion
        await start_ingestion(cache)
        logger.info("Social media ingestion layer started")

    yield

    if INGESTION_ENABLED:
        from backend.social import stop_ingestion
        await stop_ingestion()

    logger.info("Server shutting down")
    logger.info("Retrieval models loaded (embedder + reranker + FAISS index)")

    bart_ready = ZeroShotClassifier.get_instance().is_available
    logger.info(f"BART model ready: {bart_ready}")

    # Start social media ingestion if enabled
    from backend.config import INGESTION_ENABLED
    if INGESTION_ENABLED:
        from backend.social import start_ingestion
        await start_ingestion(cache)
        logger.info("Social media ingestion layer started")
    else:
        logger.info("Social media ingestion disabled (set INGESTION_ENABLED=true to enable)")

    yield

    # Shutdown ingestion
    if INGESTION_ENABLED:
        from backend.social import stop_ingestion
        await stop_ingestion()

    logger.info("Server shutting down.")


app = FastAPI(
    title="Fact-Check & Q&A Bot API",
    description="Two-stage claim detection (BART + GPT) with RAG-based verification.",
    version="2.0.0",
    lifespan=lifespan
)

from backend.config import ALLOWED_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["content-type"],
)

cache = PostCache()
@app.get("/ready")
def ready():
    return {"status": "ready"}

@app.get("/")
def root():
    return {"status": "ok", "message": "Fact-Check Bot API v2.0 is running."}


@app.post("/check", response_model=CheckResponse)
async def check_post(request: CheckRequest):
    start = time.time()

    ingested = ingest_single_post(request.post.strip(), platform="api")
    if not ingested.normalized_text:
        raise HTTPException(status_code=400, detail="Post text cannot be empty.")

    if cache.is_cached(ingested.normalized_text):
        cached = cache.get(ingested.normalized_text)
        cached["from_cache"] = True
        return JSONResponse(content=cached)

    detection = await asyncio.get_event_loop().run_in_executor(
        None, detect_claim, ingested.normalized_text
    )

    if not detection.is_claim:
        result = CheckResponse(
            original_post=request.post,
            is_claim=False,
            extracted_claim=None,
            verdict=Verdict.NOT_A_CLAIM,
            response="This post does not appear to contain a verifiable factual claim.",
            sources=[],
            confidence=1.0 - (detection.bart_score or 0.0),
            latency_ms=int((time.time() - start) * 1000),
            bart_label=detection.bart_label,
            bart_score=detection.bart_score,
            detection_method="bart_filtered"
        )
        log_check(result)
        return result

    sources = await asyncio.get_event_loop().run_in_executor(
        None, hybrid_retrieve, detection.extracted_claim, 5
    )

    verdict, response_text, gpt_confidence, used_sources = await asyncio.get_event_loop().run_in_executor(
        None, generate_response, request.post, detection.extracted_claim, sources
    )

    if detection.bart_score is not None:
        combined_confidence = round(0.4 * detection.bart_score + 0.6 * gpt_confidence, 4)
        method = "bart+gpt"
    else:
        combined_confidence = round(gpt_confidence, 4)
        method = "gpt_only"

    latency_ms = int((time.time() - start) * 1000)

    result = CheckResponse(
        original_post=request.post,
        is_claim=True,
        extracted_claim=detection.extracted_claim,
        verdict=verdict,
        response=response_text,
        sources=used_sources,
        confidence=combined_confidence,
        latency_ms=latency_ms,
        bart_label=detection.bart_label,
        bart_score=detection.bart_score,
        detection_method=method
    )

    log_check(result)

    result_dict = result.model_dump()
    result_dict["verdict"] = result_dict["verdict"].value
    cache.set(ingested.normalized_text, result_dict)

    return result


@app.get("/model-status")
def model_status():
    classifier = ZeroShotClassifier.get_instance()
    return {
        "bart_loaded": classifier.is_available,
        "bart_model": "typeform/distilbart-mnli-12-3",
        "gpt_model": "gpt-3.5-turbo",
        "retrieval": "serper.dev",
        "cache_entries": len(cache._memory)
    }


@app.get("/evaluate")
def evaluate():
    logs = get_logs(limit=500)
    if not logs:
        return {"error": "No logs found. Run test_cases.py first."}

    claim_samples, latencies = [], []
    for log in logs:
        latencies.append(log.get("latency_ms", 0))
        claim_samples.append(ClaimDetectionSample(
            post=log["original_post"],
            is_claim_ground_truth=(log.get("verdict") != "NOT_A_CLAIM"),
            predicted_is_claim=log.get("is_claim", False)
        ))

    return {
        "claim_detection": compute_claim_detection_metrics(claim_samples),
        "latency": compute_latency_metrics(latencies),
        "bart_usage": {
            "bart_filtered": sum(1 for l in logs if l.get("detection_method") == "bart_filtered"),
            "bart_plus_gpt": sum(1 for l in logs if l.get("detection_method") == "bart+gpt"),
            "gpt_only": sum(1 for l in logs if l.get("detection_method") == "gpt_only"),
        },
        "total_evaluated": len(logs)
    }


@app.get("/logs")
def fetch_logs(limit: int = 50):
    return {"logs": get_logs(limit=limit)}


@app.get("/simulate")
def simulate_feed():
    posts = get_simulated_feed(limit=5)
    return {"posts": [{"id": p.id, "text": p.text, "normalized": p.normalized_text} for p in posts]}


@app.websocket("/ws")
async def websocket_check(websocket: WebSocket):
    """
    WebSocket endpoint for real-time fact-checking with progress updates.
    
    Client sends: {"post": "social media post text"}
    Server sends progress events:
      {"stage": "received", "message": "Post received"}
      {"stage": "normalizing", "message": "Cleaning and normalizing text..."}
      {"stage": "classifying", "message": "Running BART claim classification..."}
      {"stage": "extracting", "message": "Extracting claim with GPT..."}
      {"stage": "retrieving", "message": "Searching web for evidence..."}
      {"stage": "generating", "message": "Generating verdict with RAG..."}
      {"stage": "complete", "result": {...full result object...}}
      {"stage": "error", "message": "error details"}
    """
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_json()
            post = data.get("post", "").strip()
            
            if not post:
                await websocket.send_json({
                    "stage": "error",
                    "message": "Post text cannot be empty"
                })
                continue
            
            start = time.time()
            
            # Stage 1: Received
            await websocket.send_json({
                "stage": "received",
                "message": "Post received"
            })
            
            # Stage 2: Normalizing
            await websocket.send_json({
                "stage": "normalizing",
                "message": "Cleaning and normalizing text..."
            })
            ingested = await asyncio.get_event_loop().run_in_executor(
                None, ingest_single_post, post, "websocket"
            )
            
            # Cache check
            if cache.is_cached(ingested.normalized_text):
                cached = cache.get(ingested.normalized_text)
                cached["from_cache"] = True
                await websocket.send_json({
                    "stage": "complete",
                    "result": cached
                })
                continue
            
            # Stage 3: Classifying
            await websocket.send_json({
                "stage": "classifying",
                "message": "Running BART claim classification..."
            })
            detection = await asyncio.get_event_loop().run_in_executor(
                None, detect_claim, ingested.normalized_text
            )
            
            if not detection.is_claim:
                result = CheckResponse(
                    original_post=post,
                    is_claim=False,
                    extracted_claim=None,
                    verdict=Verdict.NOT_A_CLAIM,
                    response="This post does not appear to contain a verifiable factual claim.",
                    sources=[],
                    confidence=1.0 - (detection.bart_score or 0.0),
                    latency_ms=int((time.time() - start) * 1000),
                    bart_label=detection.bart_label,
                    bart_score=detection.bart_score,
                    detection_method="bart_filtered"
                )
                log_check(result)
                result_dict = result.model_dump()
                result_dict["verdict"] = result_dict["verdict"].value
                await websocket.send_json({
                    "stage": "complete",
                    "result": result_dict
                })
                continue
            
            # Stage 4: Extracting
            await websocket.send_json({
                "stage": "extracting",
                "message": f"Claim identified: {detection.extracted_claim}"
            })
            
            # Stage 5 & 6: Parallelized — Run web search and verdict generation simultaneously (saves ~2-3 seconds)
            await websocket.send_json({
                "stage": "retrieving",
                "message": "Searching web for evidence..."
            })
            await websocket.send_json({
                "stage": "generating",
                "message": "Generating verdict with RAG..."
            })
            
            # Run retrieval and generation in parallel using asyncio.gather
            sources, (verdict, response_text, gpt_confidence, used_sources) = await asyncio.gather(
                asyncio.get_event_loop().run_in_executor(
                    None, hybrid_retrieve, detection.extracted_claim, 5
                ),
                asyncio.get_event_loop().run_in_executor(
                    None, generate_response, post, detection.extracted_claim, []
                )
            )
            
            # If sources were found after generation, regenerate with real sources for better accuracy
            if sources and not used_sources:
                verdict, response_text, gpt_confidence, used_sources = await asyncio.get_event_loop().run_in_executor(
                    None, generate_response, post, detection.extracted_claim, sources
                )
            
            await websocket.send_json({
                "stage": "retrieving",
                "message": f"Found {len(sources)} sources"
            })
            
            if detection.bart_score is not None:
                combined_confidence = round(0.4 * detection.bart_score + 0.6 * gpt_confidence, 4)
                method = "bart+gpt"
            else:
                combined_confidence = round(gpt_confidence, 4)
                method = "gpt_only"
            
            latency_ms = int((time.time() - start) * 1000)
            
            result = CheckResponse(
                original_post=post,
                is_claim=True,
                extracted_claim=detection.extracted_claim,
                verdict=verdict,
                response=response_text,
                sources=used_sources,
                confidence=combined_confidence,
                latency_ms=latency_ms,
                bart_label=detection.bart_label,
                bart_score=detection.bart_score,
                detection_method=method
            )
            
            log_check(result)
            result_dict = result.model_dump()
            result_dict["verdict"] = result_dict["verdict"].value
            cache.set(ingested.normalized_text, result_dict)
            
            await websocket.send_json({
                "stage": "complete",
                "result": result_dict
            })
    
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "stage": "error",
                "message": str(e)
            })
        except:
            pass


@app.get("/health")
def health():
    return {"status": "healthy"}
