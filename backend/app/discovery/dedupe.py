from __future__ import annotations

import re
from collections.abc import Iterable
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


def is_excluded(domain: str, exclude_domains: Iterable[str]) -> bool:
    """True if domain equals an excluded domain or is a subdomain of one."""
    return any(domain == d or domain.endswith("." + d) for d in exclude_domains)


def dedupe_candidates(
    candidates: list[Candidate],
    exclude_domains: Iterable[str] = (),
    exclude_title_patterns: Iterable[str] = (),
) -> list[Candidate]:
    """Merge candidates by normalised domain, keeping the first occurrence's data.

    Drops directories, social sites and listicles ("Top 40 call centers ...")
    configured in queries.yaml: they mention BPOs but aren't one.
    """
    excluded = [d.lower() for d in exclude_domains]
    title_res = [re.compile(p, re.IGNORECASE) for p in exclude_title_patterns]
    seen: dict[str, Candidate] = {}
    for c in candidates:
        domain = normalise_domain(c.url)
        if not domain or is_excluded(domain, excluded):
            continue
        if any(r.search(c.name or "") for r in title_res):
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
