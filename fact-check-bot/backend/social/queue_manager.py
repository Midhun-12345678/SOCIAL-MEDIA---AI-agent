import asyncio
import logging
import time

from backend.ingestion import SocialPost, ingest_single_post, PostCache
from backend.claim_detector import detect_claim
from backend.retrieval import hybrid_retrieve
from backend.rag_generator import generate_response
from backend.logger import log_check
from backend.models import CheckResponse, Verdict

logger = logging.getLogger(__name__)


class QueueManager:
    """
    Owns the asyncio.Queue and concurrency semaphore.
    Producers call enqueue() — blocking put propagates backpressure.
    Consumer loop is batch-ready and runs the full fact-check pipeline.
    """

    def __init__(
        self,
        cache: PostCache,
        max_size: int = 1000,
        max_concurrent: int = 3,
        batch_size: int = 1,
    ):
        self._queue: asyncio.Queue[SocialPost] = asyncio.Queue(maxsize=max_size)
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._cache = cache
        self._batch_size = batch_size
        self._task: asyncio.Task | None = None
        self._running = False

    async def enqueue(self, post: SocialPost) -> None:
        """Blocking put — waits if queue full. Backpressure propagates to listeners."""
        await self._queue.put(post)
        logger.debug(f"Enqueued {post.platform}:{post.id} (queue size: {self._queue.qsize()})")

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._consume_loop())
        logger.info("Queue consumer started")

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(f"Queue consumer stopped ({self._queue.qsize()} items remaining)")

    async def _consume_loop(self) -> None:
        loop = asyncio.get_event_loop()

        while self._running:
            try:
                batch = await self._get_batch()

                tasks = [
                    self._process_post(post, loop)
                    for post in batch
                ]
                await asyncio.gather(*tasks, return_exceptions=True)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Queue consumer error: {e}")

    async def _get_batch(self) -> list[SocialPost]:
        """Pull up to batch_size posts. Always awaits at least one."""
        first = await self._queue.get()
        batch = [first]

        for _ in range(self._batch_size - 1):
            try:
                post = self._queue.get_nowait()
                batch.append(post)
            except asyncio.QueueEmpty:
                break

        return batch

    async def _process_post(self, post: SocialPost, loop: asyncio.AbstractEventLoop) -> None:
        async with self._semaphore:
            try:
                start = time.time()

                ingested = await loop.run_in_executor(
                    None, ingest_single_post, post.text, post.platform
                )

                if self._cache.is_cached(ingested.normalized_text):
                    logger.info(f"Skipping cached post {post.platform}:{post.id}")
                    return

                detection = await loop.run_in_executor(
                    None, detect_claim, ingested.normalized_text
                )

                if not detection.is_claim:
                    result = CheckResponse(
                        original_post=post.text,
                        is_claim=False,
                        extracted_claim=None,
                        verdict=Verdict.NOT_A_CLAIM,
                        response="This post does not appear to contain a verifiable factual claim.",
                        sources=[],
                        confidence=1.0 - (detection.bart_score or 0.0),
                        latency_ms=int((time.time() - start) * 1000),
                        bart_label=detection.bart_label,
                        bart_score=detection.bart_score,
                        detection_method="bart_filtered",
                    )
                    log_check(
                        result,
                        platform=post.platform,
                        platform_post_id=post.id,
                        author=post.author,
                        source_url=post.metadata.get("source_url") or post.metadata.get("permalink"),
                    )
                    return

                sources = await loop.run_in_executor(
                    None, hybrid_retrieve, detection.extracted_claim, 5
                )

                verdict, response_text, gpt_confidence, used_sources = await loop.run_in_executor(
                    None, generate_response, post.text, detection.extracted_claim, sources
                )

                if detection.bart_score is not None:
                    combined_confidence = round(0.4 * detection.bart_score + 0.6 * gpt_confidence, 4)
                    method = "bart+gpt"
                else:
                    combined_confidence = round(gpt_confidence, 4)
                    method = "gpt_only"

                latency_ms = int((time.time() - start) * 1000)

                result = CheckResponse(
                    original_post=post.text,
                    is_claim=True,
                    extracted_claim=detection.extracted_claim,
                    verdict=verdict,
                    response=response_text,
                    sources=used_sources,
                    confidence=combined_confidence,
                    latency_ms=latency_ms,
                    bart_label=detection.bart_label,
                    bart_score=detection.bart_score,
                    detection_method=method,
                )

                log_check(
                    result,
                    platform=post.platform,
                    platform_post_id=post.id,
                    author=post.author,
                    source_url=post.metadata.get("source_url") or post.metadata.get("permalink"),
                )

                result_dict = result.model_dump()
                result_dict["verdict"] = result_dict["verdict"].value
                self._cache.set(ingested.normalized_text, result_dict)

                logger.info(
                    f"Processed {post.platform}:{post.id} → {verdict.value} "
                    f"({latency_ms}ms)"
                )

            except Exception as e:
                logger.error(f"Pipeline failed for {post.platform}:{post.id}: {e}")

    @property
    def queue_size(self) -> int:
        return self._queue.qsize()
