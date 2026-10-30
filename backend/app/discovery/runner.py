from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.config import AppConfig
from app.discovery import Candidate
from app.discovery.dedupe import dedupe_candidates
from app.discovery.extract import extract_text, extract_title
from app.discovery.fetch import fetch_pages, find_inner_urls
from app.discovery.queries import build_queries_from_config
from app.discovery.sources.places import PlacesSource
from app.discovery.sources.serper import SerperSource

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryResult:
    """Result of a discovery run."""

    country: str
    queries_used: list[str]
    candidates: list[EnrichedCandidate]
    started_at: datetime
    finished_at: datetime
    total_found: int
    new_count: int = 0


@dataclass
class EnrichedCandidate:
    """A candidate with fetched page text."""

    candidate: Candidate
    homepage_text: str = ""
    inner_texts: dict[str, str] = field(default_factory=dict)
    title: str = ""
    inner_urls: list[str] = field(default_factory=list)


async def run_discovery(
    config: AppConfig,
    country_code: str,
    limit: int = 30,
    serper_key: str = "",
    places_key: str = "",
) -> DiscoveryResult:
    """Run the full discovery pipeline for a country.

    1. Build queries from config
    2. Search via Serper + Places
    3. Deduplicate by domain
    4. Fetch homepage + inner pages
    5. Extract text
    """
    started_at = datetime.now(timezone.utc)

    # 1. Build queries
    queries = build_queries_from_config(config, country_code)
    logger.info(
        "Discovery %s: %d queries, limit %d",
        country_code,
        len(queries),
        limit,
    )

    # 2. Search
    sources = []
    if serper_key:
        sources.append(SerperSource(serper_key))
    if places_key:
        sources.append(PlacesSource(places_key))

    all_candidates: list[Candidate] = []
    for source in sources:
        for query in queries:
            try:
                results = await source.search(query, country_code)
            except Exception:
                # One broken source/query must not kill the whole run.
                logger.exception("Source %s failed on query %r", type(source).__name__, query)
                continue
            all_candidates.extend(results)
            # Stop on usable candidates, not raw hits: directories and listicles
            # are filtered out, so raw counts overestimate what a run will yield.
            usable = dedupe_candidates(
                all_candidates, config.exclude_domains, config.exclude_title_patterns
            )
            if len(usable) >= limit:
                break

    logger.info(
        "Discovery %s: %d raw candidates from %d sources",
        country_code,
        len(all_candidates),
        len(sources),
    )

    # 3. Deduplicate
    unique = dedupe_candidates(
        all_candidates, config.exclude_domains, config.exclude_title_patterns
    )[:limit]
    logger.info(
        "Discovery %s: %d unique after dedupe (capped at %d)",
        country_code,
        len(unique),
        limit,
    )

    # 4. Fetch homepages
    urls = [c.url for c in unique]
    pages = await fetch_pages(urls)
    page_map = {p["url"]: p for p in pages}

    # 5. Extract text, find inner pages, fetch them
    enriched: list[EnrichedCandidate] = []
    for candidate in unique:
        page_data = page_map.get(candidate.url, {})
        html = page_data.get("html", "")

        try:
            title = extract_title(html)
            if _is_bot_challenge(title):
                # Cloudflare & co. served a check page, not the site: nothing to score.
                logger.info("Bot challenge for %s, skipping its text", candidate.url)
                html, title = "", ""
            homepage_text = extract_text(html)

            # Find and fetch inner pages
            inner_urls = find_inner_urls(html, candidate.url, max_pages=3)
            inner_texts: dict[str, str] = {}

            if inner_urls:
                inner_pages = await fetch_pages(inner_urls)
                for ip in inner_pages:
                    if ip.get("html"):
                        inner_texts[ip["url"]] = extract_text(ip["html"])
        except Exception:
            # Keep the candidate with what we have; scoring shows the gaps.
            logger.exception("Enrichment failed for %s", candidate.url)
            homepage_text, title, inner_urls, inner_texts = "", "", [], {}

        enriched.append(
            EnrichedCandidate(
                candidate=candidate,
                homepage_text=homepage_text,
                inner_texts=inner_texts,
                title=title or candidate.name,
                inner_urls=inner_urls,
            )
        )

    finished_at = datetime.now(timezone.utc)
    return DiscoveryResult(
        country=country_code,
        queries_used=queries,
        candidates=enriched,
        started_at=started_at,
        finished_at=finished_at,
        total_found=len(enriched),
    )


BOT_CHALLENGE_TITLES = ("just a moment", "attention required", "access denied", "are you a robot")


def _is_bot_challenge(title: str) -> bool:
    return title.strip().lower().startswith(BOT_CHALLENGE_TITLES)
