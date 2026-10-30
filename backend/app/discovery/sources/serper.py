from __future__ import annotations

import logging

import httpx

from app.discovery import Candidate
from app.discovery.dedupe import normalise_domain

logger = logging.getLogger(__name__)

SERPER_URL = "https://google.serper.dev/search"


class SerperSource:
    """Discovery source using Serper.dev (Google search API)."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def search(self, query: str, country: str) -> list[Candidate]:
        if not self.api_key:
            logger.warning("SERPER_API_KEY not set, skipping Serper search")
            return []

        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "q": query,
            "num": 10,
        }
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(SERPER_URL, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            logger.error("Serper request failed: %s", e)
            return []

        candidates = []
        for result in data.get("organic", []):
            link = result.get("link", "")
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            domain = normalise_domain(link)
            if domain:
                candidates.append(
                    Candidate(
                        url=link,
                        domain=domain,
                        name=title,
                        snippet=snippet,
                        source="serper",
                        country=country,
                    )
                )
        logger.info(
            "Serper: query=%r country=%s results=%d",
            query,
            country,
            len(candidates),
        )
        return candidates
