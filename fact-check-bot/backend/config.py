import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-3.5-turbo")
LOG_FILE = os.getenv("LOG_FILE", "logs/checks.json")

# ── CORS ──
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

# ── Social Media Ingestion ──
INGESTION_ENABLED = os.getenv("INGESTION_ENABLED", "false").lower() == "true"

# Reddit
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "fact-check-bot/1.0")
REDDIT_SUBREDDITS = os.getenv("REDDIT_SUBREDDITS", "worldnews+science+technology").split("+")
REDDIT_POLL_INTERVAL = int(os.getenv("REDDIT_POLL_INTERVAL", "60"))
REDDIT_FETCH_LIMIT = int(os.getenv("REDDIT_FETCH_LIMIT", "100"))

# RSS
RSS_FEEDS = os.getenv("RSS_FEEDS", "").split(",")
RSS_POLL_INTERVAL = int(os.getenv("RSS_POLL_INTERVAL", "300"))

# Queue / Consumer
QUEUE_MAX_SIZE = int(os.getenv("QUEUE_MAX_SIZE", "1000"))
QUEUE_BATCH_SIZE = int(os.getenv("QUEUE_BATCH_SIZE", "1"))
MAX_CONCURRENT_CHECKS = int(os.getenv("MAX_CONCURRENT_CHECKS", "3"))
DEDUP_TTL_HOURS = float(os.getenv("DEDUP_TTL_HOURS", "24"))

# ── Retrieval System ──
FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "faiss_index.bin"))
DOCUMENT_STORE_PATH = os.getenv("DOCUMENT_STORE_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "document_store.json"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
VECTOR_SEARCH_TOP_K = int(os.getenv("VECTOR_SEARCH_TOP_K", "5"))
RERANKER_TOP_K = int(os.getenv("RERANKER_TOP_K", "5"))