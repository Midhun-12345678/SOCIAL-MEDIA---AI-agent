import asyncio
import logging
import random
from abc import ABC, abstractmethod
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.social.queue_manager import QueueManager
    from backend.social.dedup import DedupTracker
    from backend.ingestion import SocialPost

logger = logging.getLogger(__name__)


class BaseListener(ABC):
    """
    Abstract base class for all platform listeners.
    Subclasses implement poll() to fetch posts from their platform.
    The base handles the polling loop, dedup gating, enqueue, and jittered backoff.
    """

    def __init__(
        self,
        queue_manager: "QueueManager",
        dedup: "DedupTracker",
        poll_interval: int = 60,
    ):
        self.queue_manager = queue_manager
        self.dedup = dedup
        self.poll_interval = poll_interval
        self._task: asyncio.Task | None = None
        self._running = False

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return platform identifier, e.g. 'reddit', 'rss'."""
        ...

    @abstractmethod
    async def poll(self) -> List["SocialPost"]:
        """
        Fetch new posts from the platform.
        Must return a list of SocialPost objects.
        Dedup and enqueue are handled by the base class.
        """
        ...

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(f"{self.platform_name} listener started (interval={self.poll_interval}s)")

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(f"{self.platform_name} listener stopped")

    async def _loop(self) -> None:
        retry_count = 0

        while self._running:
            try:
                posts = await self.poll()

                for post in posts:
                    if self.dedup.is_seen(post.platform, post.id):
                        continue
                    self.dedup.mark_seen(post.platform, post.id)
                    await self.queue_manager.enqueue(post)

                retry_count = 0
                await asyncio.sleep(self.poll_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                retry_count += 1
                backoff = min(30 * (2 ** retry_count), 300)
                jitter = random.uniform(0, backoff * 0.25)
                sleep_time = backoff + jitter
                logger.error(
                    f"{self.platform_name} listener error (retry #{retry_count}, "
                    f"backoff {sleep_time:.1f}s): {e}"
                )
                await asyncio.sleep(sleep_time)
