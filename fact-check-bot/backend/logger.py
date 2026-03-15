import json
import os
from datetime import datetime, timezone
from backend.models import CheckResponse
from backend.config import LOG_FILE


def log_check(
    result: CheckResponse,
    platform: str | None = None,
    platform_post_id: str | None = None,
    author: str | None = None,
    source_url: str | None = None,
) -> None:
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            try:
                logs = json.load(f)
            except json.JSONDecodeError:
                logs = []
    else:
        logs = []

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "original_post": result.original_post,
        "is_claim": result.is_claim,
        "extracted_claim": result.extracted_claim,
        "verdict": result.verdict.value if result.verdict else None,
        "response": result.response,
        "confidence": result.confidence,
        "latency_ms": result.latency_ms,
        "bart_label": result.bart_label,
        "bart_score": result.bart_score,
        "detection_method": result.detection_method,
        "sources": [
            {"title": s.title, "url": s.url, "snippet": s.snippet}
            for s in result.sources
        ],
        "platform": platform,
        "platform_post_id": platform_post_id,
        "author": author,
        "source_url": source_url,
    }

    logs.append(entry)

    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)


def get_logs(limit: int = 50) -> list:
    if not os.path.exists(LOG_FILE):
        return []

    with open(LOG_FILE, "r") as f:
        try:
            logs = json.load(f)
        except json.JSONDecodeError:
            return []

    return logs[-limit:]
