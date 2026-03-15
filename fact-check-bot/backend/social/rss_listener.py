import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from typing import List

from backend.ingestion import SocialPost
from backend.social.base_listener import BaseListener
from backend.social.queue_manager import QueueManager
from backend.social.dedup import DedupTracker

logger = logging.getLogger(__name__)


class RSSListener(BaseListener):
    """
    Polls configured RSS/Atom feed URLs using feedparser.
    feedparser.parse() is synchronous, so it runs in an executor
    to avoid blocking the event loop.
    """

    def __init__(
        self,
        queue_manager: QueueManager,
        dedup: DedupTracker,
        feed_urls: list[str],
        poll_interval: int = 300,
    ):
        super().__init__(queue_manager, dedup, poll_interval)
        self._feed_urls = [u.strip() for u in feed_urls if u.strip()]

    @property
    def platform_name(self) -> str:
        return "rss"

    async def poll(self) -> List[SocialPost]:
        import feedparser

        if not self._feed_urls:
            return []

        loop = asyncio.get_event_loop()
        posts: list[SocialPost] = []

        for url in self._feed_urls:
            try:
                feed = await loop.run_in_executor(None, feedparser.parse, url)

                feed_title = feed.feed.get("title", url) if feed.feed else url

                for entry in feed.entries:
                    entry_id = entry.get("id") or entry.get("link")
                    if not entry_id:
                        continue

                    post_id = hashlib.sha256(entry_id.encode()).hexdigest()[:16]

                    title = entry.get("title", "")
                    summary = entry.get("summary", "")
                    text_parts = [title]
                    if summary and summary != title:
                        text_parts.append(summary)
                    text = " ".join(text_parts).strip()

                    if not text:
                        continue

                    published = entry.get("published", "")
                    try:
                        from email.utils import parsedate_to_datetime
                        ts = parsedate_to_datetime(published).isoformat() if published else None
                    except (ValueError, TypeError):
                        ts = None
                    if not ts:
                        ts = datetime.now(timezone.utc).isoformat()

                    post = SocialPost(
                        id=f"rss_{post_id}",
                        text=text,
                        normalized_text="",  # normalized by queue consumer
                        platform="rss",
                        author=entry.get("author"),
                        timestamp=ts,
                        metadata={
                            "feed_title": feed_title,
                            "feed_url": url,
                            "source_url": entry.get("link"),
                        },
                    )
                    posts.append(post)

            except Exception as e:
                logger.warning(f"RSS feed error ({url}): {e}")
                continue

        if posts:
            logger.info(f"RSS poll: {len(posts)} entries from {len(self._feed_urls)} feeds")

        return posts
