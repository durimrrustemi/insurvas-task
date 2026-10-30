from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class SignalCreate(BaseModel):
    criterion: str
    key: str
    value: float
    weight: float
    source_url: str | None = None
    matched_text: str | None = None


class SignalRead(BaseModel):
    id: uuid.UUID
    partner_id: uuid.UUID
    criterion: str
    key: str
    value: float
    weight: float
    source_url: str | None
    matched_text: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SignalUpdate(BaseModel):
    value: float | None = None
    weight: float | None = None
