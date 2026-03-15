import json
import os
import logging
from typing import List
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

STORE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "document_store.json")


@dataclass
class StoredDocument:
    chunk_text: str
    source: str
    url: str
    title: str
    doc_id: int = 0
    extra: dict = field(default_factory=dict)


class DocumentStore:
    """Manages stored document chunks and their metadata, persisted to JSON."""

    def __init__(self, store_path: str = STORE_PATH):
        self._store_path = os.path.abspath(store_path)
        self._documents: List[StoredDocument] = []
        self._load()

    def _load(self) -> None:
        if os.path.exists(self._store_path):
            try:
                with open(self._store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._documents = [StoredDocument(**d) for d in data]
                logger.info(f"DocumentStore loaded {len(self._documents)} chunks from disk")
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"DocumentStore load failed: {e}")
                self._documents = []
        else:
            self._documents = []

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
        with open(self._store_path, "w", encoding="utf-8") as f:
            json.dump([asdict(d) for d in self._documents], f, indent=2, ensure_ascii=False)

    def add_documents(self, docs: List[StoredDocument]) -> List[int]:
        """Add documents and return their assigned IDs (indices)."""
        start_id = len(self._documents)
        for i, doc in enumerate(docs):
            doc.doc_id = start_id + i
            self._documents.append(doc)
        self._save()
        logger.info(f"DocumentStore: added {len(docs)} chunks (total: {len(self._documents)})")
        return list(range(start_id, start_id + len(docs)))

    def get_by_ids(self, ids: List[int]) -> List[StoredDocument]:
        """Retrieve documents by their IDs."""
        results = []
        for i in ids:
            if 0 <= i < len(self._documents):
                results.append(self._documents[i])
        return results

    def has_url(self, url: str) -> bool:
        """Check if any document with this URL is already stored."""
        return any(d.url == url for d in self._documents)

    def get_all_texts(self) -> List[str]:
        return [d.chunk_text for d in self._documents]

    @property
    def size(self) -> int:
        return len(self._documents)
