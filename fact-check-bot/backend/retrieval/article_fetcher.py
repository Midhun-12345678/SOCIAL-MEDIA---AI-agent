import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

MAX_ARTICLE_LENGTH = 100_000


def fetch_article(url: str) -> dict | None:
    """
    Download and extract readable article text from a URL.
    Returns structured article data, or None on failure.
    """
    if not url or not url.startswith(("http://", "https://")):
        return None

    try:
        from newspaper import Article

        article = Article(url)
        article.download()
        article.parse()

        text = (article.text or "").strip()
        title = (article.title or "").strip()

        if len(text) < 300:
            logger.debug(f"Article too short ({len(text)} chars), skipping: {url}")
            return None

        if len(text) > MAX_ARTICLE_LENGTH:
            text = text[:MAX_ARTICLE_LENGTH]

        domain = urlparse(url).netloc.removeprefix("www.")

        return {
            "title": title or domain,
            "text": text,
            "url": url,
            "source": domain,
        }

    except Exception as e:
        logger.warning(f"Article fetch failed ({url}): {e}")
        return None
