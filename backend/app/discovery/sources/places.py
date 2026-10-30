from __future__ import annotations

import logging

import httpx

from app.discovery import Candidate
from app.discovery.dedupe import normalise_domain

logger = logging.getLogger(__name__)

PLACES_TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"


class PlacesSource:
    """Discovery source using Google Places API."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def search(self, query: str, country: str) -> list[Candidate]:
        if not self.api_key:
            logger.warning("GOOGLE_PLACES_KEY not set, skipping Places search")
            return []

        params = {
            "query": query,
            "key": self.api_key,
        }
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(PLACES_TEXT_SEARCH_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            logger.error("Places text search failed: %s", e)
            return []

        candidates = []
        for place in data.get("results", [])[:10]:
            name = place.get("name", "")
            address = place.get("formatted_address", "")
            place_id = place.get("place_id")

            website = await self._get_website(place_id) if place_id else None
            if not website:
                continue

            domain = normalise_domain(website)
            if domain:
                candidates.append(
                    Candidate(
                        url=website,
                        domain=domain,
                        name=name,
                        snippet=address,
                        source="places",
                        country=country,
                        extra={
                            "place_id": place_id,
                            "address": address,
                        },
                    )
                )

        logger.info(
            "Places: query=%r country=%s results=%d",
            query,
            country,
            len(candidates),
        )
        return candidates

    async def _get_website(self, place_id: str) -> str | None:
        params = {
            "place_id": place_id,
            "fields": "website",
            "key": self.api_key,
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(PLACES_DETAILS_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                return data.get("result", {}).get("website")
        except httpx.HTTPError:
            return None
