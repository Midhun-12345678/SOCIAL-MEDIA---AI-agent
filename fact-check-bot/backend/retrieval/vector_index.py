import os
import logging
import numpy as np
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

INDEX_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "faiss_index.bin")


class VectorIndex:
    """FAISS flat L2 index for semantic similarity search."""

    def __init__(self, dim: int = 384, index_path: str = INDEX_PATH):
        import faiss
        self._dim = dim
        self._index_path = os.path.abspath(index_path)
        self._index: Optional[faiss.IndexFlatL2] = None
        self._load_or_create()

    def _load_or_create(self) -> None:
        import faiss
        if os.path.exists(self._index_path):
            try:
                self._index = faiss.read_index(self._index_path)
                logger.info(f"FAISS index loaded: {self._index.ntotal} vectors")
            except Exception as e:
                logger.warning(f"FAISS index load failed ({e}), creating new")
                self._index = faiss.IndexFlatL2(self._dim)
        else:
            self._index = faiss.IndexFlatL2(self._dim)
            logger.info("FAISS index created (empty)")

    def add(self, embeddings: np.ndarray) -> None:
        """Add embeddings to the index. Shape: (N, dim)."""
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        self._index.add(embeddings.astype(np.float32))
        self._save()
        logger.info(f"FAISS index: added {embeddings.shape[0]} vectors (total: {self._index.ntotal})")

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Tuple[int, float]]:
        """Search for top_k nearest neighbors. Returns [(doc_id, distance), ...]."""
        if self._index.ntotal == 0:
            return []
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        distances, indices = self._index.search(
            query_embedding.astype(np.float32),
            min(top_k, self._index.ntotal),
        )
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx >= 0:
                results.append((int(idx), float(dist)))
        return results

    def _save(self) -> None:
        import faiss
        os.makedirs(os.path.dirname(self._index_path), exist_ok=True)
        faiss.write_index(self._index, self._index_path)

    @property
    def total_vectors(self) -> int:
        return self._index.ntotal if self._index else 0
