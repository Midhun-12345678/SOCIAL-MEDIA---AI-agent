import logging
from typing import List
import numpy as np

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    """Singleton loader for the SentenceTransformer embedding model."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        logger.info("Embedding model loaded: all-MiniLM-L6-v2")
    return _model


def preload_model() -> None:
    """Called at startup to warm up the model."""
    _get_model()


def embed_texts(texts: List[str]) -> np.ndarray:
    """Embed a list of texts. Returns (N, 384) float32 array."""
    model = _get_model()
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return embeddings.astype(np.float32)


def embed_query(query: str) -> np.ndarray:
    """Embed a single query. Returns (384,) float32 array."""
    return embed_texts([query])[0]


EMBEDDING_DIM = 384
