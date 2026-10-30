from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.partner import Blocker, PartnerType, Stage


class PartnerCreate(BaseModel):
    name: str
    domain: str
    website: str | None = None
    country: str
    city: str | None = None
    timezone: str | None = None
    type: PartnerType = PartnerType.BPO


class PartnerUpdate(BaseModel):
    name: str | None = None
    website: str | None = None
    city: str | None = None
    timezone: str | None = None
    owner_note: str | None = None
    blocker: Blocker | None = None
    engagement_terms: dict | None = None


class PartnerRead(BaseModel):
    id: uuid.UUID
    name: str
    domain: str
    website: str | None
    country: str
    city: str | None
    timezone: str | None
    type: PartnerType
    stage: Stage
    stage_entered_at: datetime | None
    owner_note: str | None
    blocker: Blocker | None
    score_total: float | None
    score_english: float | None
    score_insurance: float | None
    score_size: float | None
    score_compliance: float | None
    engagement_terms: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StageTransition(BaseModel):
    to: Stage
    reason: str | None = None


class PartnerList(BaseModel):
    items: list[PartnerRead]
    total: int
    limit: int
    offset: int
