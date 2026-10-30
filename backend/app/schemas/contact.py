from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ContactCreate(BaseModel):
    name: str
    role: str | None = None
    email: str | None = None
    linkedin_url: str | None = None
    whatsapp: str | None = None
    source_url: str | None = None


class ContactRead(BaseModel):
    id: uuid.UUID
    partner_id: uuid.UUID
    name: str
    role: str | None
    email: str | None
    linkedin_url: str | None
    whatsapp: str | None
    source_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ContactUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    email: str | None = None
    linkedin_url: str | None = None
    whatsapp: str | None = None
