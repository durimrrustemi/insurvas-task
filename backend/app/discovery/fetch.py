from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger(__name__)

CACHE_DIR = Path(".cache/pages")
CONCURRENCY = 8
TIMEOUT = 10
MAX_CONTENT_LENGTH = 2_000_000  # 2MB
CACHE_MAX_AGE_DAYS = 30
USER_AGENT = "Mozilla/5.0 (compatible; InsurvasBot/1.0; +https://insurvas.com)"


def _cache_path(url: str) -> Path:
    h = hashlib.sha1(url.encode()).hexdigest()
    return CACHE_DIR / f"{h}.json"


def _cache_is_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text())
        fetched_at = data.get("fetched_at", 0)
        age_days = (time.time() - fetched_at) / 86400
        return age_days < CACHE_MAX_AGE_DAYS
    except (json.JSONDecodeError, OSError):
        return False


def _read_cache(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _write_cache(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False))


async def _check_robots(client: httpx.AsyncClient, base_url: str) -> bool:
    """Check if we're allowed to fetch. Permissive: allow on error."""
    try:
        parsed = urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        resp = await client.get(robots_url, timeout=5)
        if resp.status_code != 200:
            return True
        text = resp.text.lower()
        # Simple check: if we see "disallow: /" for all user-agents, skip
        in_wildcard = False
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("user-agent:"):
                agent = line.split(":", 1)[1].strip()
                in_wildcard = agent == "*"
            elif in_wildcard and line == "disallow: /":
                return False
        return True
    except (httpx.HTTPError, httpx.InvalidURL, ValueError):
        return True


async def fetch_page(
    url: str,
    *,
    force: bool = False,
    semaphore: asyncio.Semaphore | None = None,
) -> dict:
    """Fetch a single page, respecting cache and robots.txt.

    Returns dict with keys: url, status, html, fetched_at, from_cache.
    """
    cache_path = _cache_path(url)

    if not force and _cache_is_fresh(cache_path):
        cached = _read_cache(cache_path)
        if cached:
            cached["from_cache"] = True
            return cached

    sem = semaphore or asyncio.Semaphore(CONCURRENCY)
    async with sem:
        try:
            async with httpx.AsyncClient(
                timeout=TIMEOUT,
                follow_redirects=True,
                headers={"User-Agent": USER_AGENT},
            ) as client:
                if not await _check_robots(client, url):
                    logger.info("Blocked by robots.txt: %s", url)
                    result = {
                        "url": url,
                        "status": 403,
                        "html": "",
                        "fetched_at": time.time(),
                        "from_cache": False,
                    }
                    _write_cache(cache_path, result)
                    return result

                resp = await client.get(url)
                content_type = resp.headers.get("content-type", "").lower()
                if "text/html" not in content_type:
                    result = {
                        "url": url,
                        "status": resp.status_code,
                        "html": "",
                        "fetched_at": time.time(),
                        "from_cache": False,
                    }
                    _write_cache(cache_path, result)
                    return result

                # Decode only the first MAX_CONTENT_LENGTH bytes; huge or
                # mis-declared pages must not blow up memory or decoding.
                html = resp.content[:MAX_CONTENT_LENGTH].decode(
                    resp.encoding or "utf-8", errors="replace"
                )
                result = {
                    "url": url,
                    "status": resp.status_code,
                    "html": html,
                    "fetched_at": time.time(),
                    "from_cache": False,
                }
                _write_cache(cache_path, result)
                return result

        except (httpx.HTTPError, httpx.InvalidURL, ValueError, LookupError) as e:
            # Bad sites are normal in cold discovery: DNS failures, TLS errors,
            # malformed URLs, unknown charsets. Record and move on.
            logger.warning("Fetch failed %s: %s", url, e)
            return {
                "url": url,
                "status": 0,
                "html": "",
                "fetched_at": time.time(),
                "from_cache": False,
                "error": str(e),
            }


async def fetch_pages(urls: list[str], *, force: bool = False) -> list[dict]:
    """Fetch multiple pages with concurrency control."""
    semaphore = asyncio.Semaphore(CONCURRENCY)
    tasks = [fetch_page(url, force=force, semaphore=semaphore) for url in urls]
    return await asyncio.gather(*tasks)


def find_inner_urls(html: str, base_url: str, max_pages: int = 3) -> list[str]:
    """Find inner page URLs by keyword in link text/href.

    Looks for services, about, careers, clients, industries pages.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    keywords = [
        "about",
        "service",
        "career",
        "client",
        "industr",
        "insurance",
        "contact",
        "team",
        "pricing",
        "rates",
    ]
    found: list[str] = []
    seen: set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = (a.get_text() or "").lower()
        href_lower = href.lower()

        if any(kw in text or kw in href_lower for kw in keywords):
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)
            # Same domain only
            base_parsed = urlparse(base_url)
            if parsed.netloc != base_parsed.netloc:
                continue
            if full_url not in seen:
                seen.add(full_url)
                found.append(full_url)
                if len(found) >= max_pages:
                    break

    return found
