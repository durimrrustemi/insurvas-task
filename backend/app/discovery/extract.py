from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


def extract_text(html: str) -> str:
    """Extract clean text from HTML using trafilatura, falling back to BS4."""
    if not html:
        return ""
    try:
        import trafilatura

        text = trafilatura.extract(html, include_comments=False)
        if text:
            return _clean(text)
    except Exception:
        logger.debug("trafilatura failed, falling back to BS4")

    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return _clean(text)
    except Exception:
        logger.warning("Both trafilatura and BS4 failed")
        return ""


def extract_title(html: str) -> str:
    """Extract the <title> from HTML."""
    if not html:
        return ""
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text(strip=True)
    except Exception:
        pass
    return ""


def _clean(text: str) -> str:
    """Collapse whitespace, remove control chars."""
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
