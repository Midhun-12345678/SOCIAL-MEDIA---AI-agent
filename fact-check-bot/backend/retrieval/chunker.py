import logging
from typing import List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    text: str
    metadata: dict


def chunk_text(
    text: str,
    metadata: dict,
    chunk_size: int = 500,
    overlap: int = 50,
) -> List[Chunk]:
    """
    Split text into overlapping word-level chunks.
    Each chunk inherits the parent document's metadata.
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunk_text_str = " ".join(chunk_words)

        chunks.append(Chunk(
            text=chunk_text_str,
            metadata={**metadata},
        ))

        if end >= len(words):
            break
        start += chunk_size - overlap

    return chunks
