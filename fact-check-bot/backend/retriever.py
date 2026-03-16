import logging
import requests
from backend.config import SERPER_API_KEY
from backend.models import Source
from typing import List

logger = logging.getLogger(__name__)

SERPER_URL = "https://google.serper.dev/search"


def retrieve_evidence(claim: str, num_results: int = 5) -> List[Source]:
    if not SERPER_API_KEY or SERPER_API_KEY.startswith("xxxx"):
        logger.warning("SERPER_API_KEY not configured — skipping retrieval")
        return []

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    from backend.ingestion import extract_entities
    ner_result = extract_entities(claim)
    entity_boost = ner_result.get("entity_string", "")
    if entity_boost:
        query = f"{claim} {entity_boost} fact check"
    else:
        query = f"{claim} fact check"

    payload = {
        "q": query,
        "num": num_results,
        "gl": "us",
        "hl": "en"
    }

    try:
        # Reduced timeout from 10s to 5s for faster fallback (optimization: saves ~1-2 seconds)
        response = requests.post(SERPER_URL, headers=headers, json=payload, timeout=5)
        response.raise_for_status()
    except requests.Timeout:
        logger.warning("Serper timeout (5s) — continuing without sources, RAG will generate verdict with limited info")
        return []
    except Exception as e:
        logger.warning(f"Serper retrieval failed ({e}) — continuing without sources")
        return []

    data = response.json()
    sources = []

    for result in data.get("organic", [])[:num_results]:
        sources.append(Source(
            title=result.get("title", "No title"),
            url=result.get("link", ""),
            snippet=result.get("snippet", "No description available.")
        ))

    answer_box = data.get("answerBox", {})
    if answer_box.get("snippet"):
        sources.insert(0, Source(
            title=answer_box.get("title", "Featured Answer"),
            url=answer_box.get("link", ""),
            snippet=answer_box.get("snippet", "")
        ))

    return sources[:num_results]
