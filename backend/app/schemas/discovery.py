from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class DiscoveryRunCreate(BaseModel):
    country: str
    limit: int = 30


class DiscoveryRunRead(BaseModel):
    id: uuid.UUID
    country: str
    queries: list[str]
    started_at: datetime
    finished_at: datetime | None
    found: int
    new: int

    model_config = {"from_attributes": True}
