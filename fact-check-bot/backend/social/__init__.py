"""
Social Media Ingestion Package.

Orchestrates platform listeners and queue consumer.
Call start_ingestion(cache) during FastAPI lifespan startup,
and stop_ingestion() during shutdown.
"""

import logging
from typing import Optional

from backend.ingestion import PostCache
from backend.social.dedup import DedupTracker
from backend.social.queue_manager import QueueManager
from backend.social.base_listener import BaseListener

logger = logging.getLogger(__name__)

_queue_manager: Optional[QueueManager] = None
_listeners: list[BaseListener] = []


async def start_ingestion(cache: PostCache) -> None:
    """Start all configured listeners and the queue consumer."""
    global _queue_manager, _listeners

    from backend.config import (
        REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT,
        REDDIT_SUBREDDITS, REDDIT_POLL_INTERVAL, REDDIT_FETCH_LIMIT,
        RSS_FEEDS, RSS_POLL_INTERVAL,
        QUEUE_MAX_SIZE, QUEUE_BATCH_SIZE, MAX_CONCURRENT_CHECKS,
        DEDUP_TTL_HOURS,
    )

    dedup = DedupTracker(ttl_hours=DEDUP_TTL_HOURS)

    _queue_manager = QueueManager(
        cache=cache,
        max_size=QUEUE_MAX_SIZE,
        max_concurrent=MAX_CONCURRENT_CHECKS,
        batch_size=QUEUE_BATCH_SIZE,
    )
    await _queue_manager.start()

    # Reddit listener
    if REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET:
        from backend.social.reddit_listener import RedditListener

        reddit = RedditListener(
            queue_manager=_queue_manager,
            dedup=dedup,
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
            subreddits=REDDIT_SUBREDDITS,
            poll_interval=REDDIT_POLL_INTERVAL,
            fetch_limit=REDDIT_FETCH_LIMIT,
        )
        await reddit.start()
        _listeners.append(reddit)
    else:
        logger.warning("Reddit credentials not set — Reddit listener disabled")

    # RSS listener
    active_feeds = [f for f in RSS_FEEDS if f.strip()]
    if active_feeds:
        from backend.social.rss_listener import RSSListener

        rss = RSSListener(
            queue_manager=_queue_manager,
            dedup=dedup,
            feed_urls=active_feeds,
            poll_interval=RSS_POLL_INTERVAL,
        )
        await rss.start()
        _listeners.append(rss)
    else:
        logger.info("No RSS feeds configured — RSS listener disabled")

    logger.info(
        f"Ingestion started: {len(_listeners)} listener(s), "
        f"queue_max={QUEUE_MAX_SIZE}, concurrency={MAX_CONCURRENT_CHECKS}"
    )


async def stop_ingestion() -> None:
    """Stop all listeners and the queue consumer."""
    global _queue_manager, _listeners

    for listener in _listeners:
        await listener.stop()
    _listeners.clear()

    if _queue_manager:
        await _queue_manager.stop()
        _queue_manager = None

    logger.info("Ingestion stopped")
