import asyncio
import logging
from datetime import datetime, timezone
from typing import List

from backend.ingestion import SocialPost
from backend.social.base_listener import BaseListener
from backend.social.queue_manager import QueueManager
from backend.social.dedup import DedupTracker

logger = logging.getLogger(__name__)


class RedditListener(BaseListener):
    """
    Polls Reddit subreddits for new submissions using asyncpraw.
    Tracks last_seen_utc to avoid re-processing and to catch all posts
    even on high-traffic subreddits.
    """

    def __init__(
        self,
        queue_manager: QueueManager,
        dedup: DedupTracker,
        client_id: str,
        client_secret: str,
        user_agent: str,
        subreddits: list[str],
        poll_interval: int = 60,
        fetch_limit: int = 100,
    ):
        super().__init__(queue_manager, dedup, poll_interval)
        self._client_id = client_id
        self._client_secret = client_secret
        self._user_agent = user_agent
        self._subreddits = subreddits
        self._fetch_limit = fetch_limit
        self._last_seen_utc: float = 0.0
        self._reddit = None

    @property
    def platform_name(self) -> str:
        return "reddit"

    async def start(self) -> None:
        import asyncpraw

        self._reddit = asyncpraw.Reddit(
            client_id=self._client_id,
            client_secret=self._client_secret,
            user_agent=self._user_agent,
        )
        logger.info(f"Reddit client initialized for subreddits: {self._subreddits}")
        await super().start()

    async def stop(self) -> None:
        await super().stop()
        if self._reddit:
            await self._reddit.close()
            self._reddit = None

    async def poll(self) -> List[SocialPost]:
        if not self._reddit:
            return []

        posts: list[SocialPost] = []
        subreddit_str = "+".join(self._subreddits)
        subreddit = await self._reddit.subreddit(subreddit_str)

        newest_utc = self._last_seen_utc

        async for submission in subreddit.new(limit=self._fetch_limit):
            if submission.created_utc <= self._last_seen_utc:
                break

            if submission.created_utc > newest_utc:
                newest_utc = submission.created_utc

            text_parts = [submission.title]
            if submission.selftext:
                text_parts.append(submission.selftext)
            text = " ".join(text_parts).strip()

            if not text:
                continue

            author_name = str(submission.author) if submission.author else None

            post = SocialPost(
                id=f"reddit_{submission.id}",
                text=text,
                normalized_text="",  # will be normalized by queue consumer
                platform="reddit",
                author=f"u/{author_name}" if author_name else None,
                timestamp=datetime.fromtimestamp(
                    submission.created_utc, tz=timezone.utc
                ).isoformat(),
                metadata={
                    "subreddit": str(submission.subreddit),
                    "score": submission.score,
                    "permalink": f"https://reddit.com{submission.permalink}",
                    "source_url": submission.url if submission.url != submission.permalink else None,
                    "num_comments": submission.num_comments,
                },
            )
            posts.append(post)

        if newest_utc > self._last_seen_utc:
            self._last_seen_utc = newest_utc

        if posts:
            logger.info(f"Reddit poll: {len(posts)} new posts from r/{subreddit_str}")

        return posts
