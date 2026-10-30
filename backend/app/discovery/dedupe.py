from __future__ import annotations

from urllib.parse import urlparse

from app.discovery import Candidate


def normalise_domain(url_or_domain: str) -> str:
    """Extract and normalise a domain: lowercase, no scheme, no www., no trailing slash."""
    d = url_or_domain.lower().strip()
    if "://" in d:
        parsed = urlparse(d)
        d = parsed.hostname or d
    else:
        # Might be "www.example.com/path"
        d = d.split("/")[0]
    if d.startswith("www."):
        d = d[4:]
    return d.rstrip(".")


def dedupe_candidates(candidates: list[Candidate]) -> list[Candidate]:
    """Merge candidates by normalised domain, keeping the first occurrence's data."""
    seen: dict[str, Candidate] = {}
    for c in candidates:
        domain = normalise_domain(c.url)
        if not domain or domain in _BLACKLIST:
            continue
        c.domain = domain
        if domain not in seen:
            seen[domain] = c
        else:
            existing = seen[domain]
            # Merge: prefer longer snippet, accumulate extras
            if len(c.snippet) > len(existing.snippet):
                existing.snippet = c.snippet
            if c.city and not existing.city:
                existing.city = c.city
    return list(seen.values())


_BLACKLIST = frozenset(
    {
        "google.com",
        "facebook.com",
        "linkedin.com",
        "twitter.com",
        "x.com",
        "youtube.com",
        "instagram.com",
        "wikipedia.org",
        "yelp.com",
        "glassdoor.com",
        "indeed.com",
        "bbb.org",
        "crunchbase.com",
        "bloomberg.com",
        "reddit.com",
        "quora.com",
        "amazon.com",
        "maps.google.com",
        "play.google.com",
        "apps.apple.com",
    }
)
