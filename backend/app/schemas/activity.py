from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.activity import ActivityKind


class ActivityCreate(BaseModel):
    kind: ActivityKind
    channel: str | None = None
    body: str | None = None


class ActivityRead(BaseModel):
    id: uuid.UUID
    partner_id: uuid.UUID
    kind: ActivityKind
    channel: str | None
    body: str | None
    at: datetime

    model_config = {"from_attributes": True}
