"""
PART 6 — Social Ingestion Tests.
Tests the social media ingestion components (dedup, queue, listeners).
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import asyncio
import time
import json
from unittest.mock import patch


class TestDedupTracker:

    def test_basic_dedup(self):
        from backend.social.dedup import DedupTracker
        d = DedupTracker(ttl_hours=1)
        assert d.is_seen("reddit", "post1") is False
        d.mark_seen("reddit", "post1")
        assert d.is_seen("reddit", "post1") is True
        assert d.is_seen("rss", "post1") is False  # different platform

    def test_ttl_eviction(self):
        from backend.social.dedup import DedupTracker
        d = DedupTracker(ttl_hours=0.0001)
        d.mark_seen("reddit", "old")
        time.sleep(0.5)
        assert d.is_seen("reddit", "old") is False


class TestQueueManager:

    @pytest.mark.asyncio
    async def test_enqueue_dequeue(self):
        from backend.social.queue_manager import QueueManager
        from backend.ingestion import PostCache, SocialPost
        cache = PostCache(cache_file="logs/test_cache_qm.json")
        qm = QueueManager(cache=cache, max_size=10, max_concurrent=1, batch_size=1)

        post = SocialPost(
            id="test_001",
            text="Test post",
            normalized_text="test post",
            platform="test",
            author="tester",
            timestamp="2026-03-15T00:00:00+00:00",
        )
        await qm.enqueue(post)
        assert qm.queue_size == 1

        # Clean up test cache file
        if os.path.exists("logs/test_cache_qm.json"):
            os.remove("logs/test_cache_qm.json")


class TestLogPlatformMetadata:
    """Verify that logs from social ingestion contain platform metadata."""

    def test_log_check_with_metadata(self, tmp_path):
        from backend.models import CheckResponse, Verdict
        from backend.logger import log_check

        log_file = str(tmp_path / "test_log.json")

        with patch("backend.logger.LOG_FILE", log_file):
            result = CheckResponse(
                original_post="test post",
                is_claim=False,
                verdict=Verdict.NOT_A_CLAIM,
                response="Not a claim.",
                sources=[],
                confidence=0.9,
            )
            log_check(
                result,
                platform="reddit",
                platform_post_id="reddit_abc123",
                author="u/testuser",
                source_url="https://reddit.com/r/test",
            )

        with open(log_file, "r") as f:
            logs = json.load(f)

        assert len(logs) == 1
        entry = logs[0]
        assert entry["platform"] == "reddit"
        assert entry["platform_post_id"] == "reddit_abc123"
        assert entry["author"] == "u/testuser"
        assert entry["source_url"] == "https://reddit.com/r/test"
