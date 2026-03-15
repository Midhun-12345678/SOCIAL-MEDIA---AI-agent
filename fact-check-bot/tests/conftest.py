"""
Shared pytest fixtures for the Fact-Check Bot test suite.
"""

import sys
import os
import pytest

# Ensure the project root is on sys.path so 'backend' imports work
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture(scope="session")
def sample_claims():
    """Standard test claims with expected properties."""
    return [
        {"text": "The Great Wall of China is visible from space", "is_claim": True},
        {"text": "Elon Musk bought Twitter for 44 billion dollars", "is_claim": True},
        {"text": "Drinking water cures cancer", "is_claim": True},
        {"text": "The Earth is flat", "is_claim": True},
        {"text": "COVID vaccines cause infertility", "is_claim": True},
        {"text": "I love pizza", "is_claim": False},
        {"text": "what time does the library close on sundays", "is_claim": False},
        {"text": "can't believe how good this pizza is omg", "is_claim": False},
        {"text": "lmao that's hilarious", "is_claim": False},
        {"text": "honestly idk what to think anymore", "is_claim": False},
    ]


@pytest.fixture(scope="session")
def sample_article_urls():
    """URLs likely to contain substantial article text."""
    return [
        "https://en.wikipedia.org/wiki/Eli_Whitney",
        "https://en.wikipedia.org/wiki/Great_Wall_of_China",
    ]
