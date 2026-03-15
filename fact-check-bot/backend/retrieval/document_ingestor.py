import logging
from backend.retrieval.chunker import chunk_text
from backend.retrieval.embedder import embed_texts
from backend.retrieval.vector_index import VectorIndex
from backend.retrieval.document_store import DocumentStore, StoredDocument
from backend.retrieval.article_fetcher import fetch_article

logger = logging.getLogger(__name__)

MAX_CHUNKS_PER_ARTICLE = 50


def ingest_article(
    article: dict,
    index: VectorIndex,
    store: DocumentStore,
) -> int:
    """
    Chunk, embed, and store a fetched article in FAISS + document store.
    Returns the number of chunks ingested.
    """
    text = article.get("text", "")
    url = article.get("url", "")
    title = article.get("title", "")
    source = article.get("source", "")

    if not text:
        return 0

    metadata = {"url": url, "title": title, "source": source}
    chunks = chunk_text(text, metadata)

    if not chunks:
        return 0

    chunks = chunks[:MAX_CHUNKS_PER_ARTICLE]

    chunk_texts = [c.text for c in chunks]
    embeddings = embed_texts(chunk_texts)

    docs = [
        StoredDocument(
            chunk_text=c.text,
            source=source,
            url=url,
            title=title,
        )
        for c in chunks
    ]

    store.add_documents(docs)
    index.add(embeddings)

    logger.info(f"Ingested {len(chunks)} chunks from {url}")
    return len(chunks)


def ingest_from_url(
    url: str,
    index: VectorIndex,
    store: DocumentStore,
) -> int:
    """
    Fetch an article from URL, then ingest into the vector DB.
    Returns chunk count, or 0 on failure.
    """
    if store.has_url(url):
        logger.debug(f"URL already ingested, skipping: {url}")
        return 0

    article = fetch_article(url)
    if article is None:
        return 0

    return ingest_article(article, index, store)
