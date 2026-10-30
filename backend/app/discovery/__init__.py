from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Candidate:
    """A potential partner discovered from a source."""

    url: str
    domain: str
    name: str
    snippet: str = ""
    source: str = ""  # e.g. "serper", "places"
    country: str = ""
    city: str = ""
    extra: dict = field(default_factory=dict)


class Source(Protocol):
    """Protocol for discovery sources."""

    async def search(self, query: str, country: str) -> list[Candidate]: ...
