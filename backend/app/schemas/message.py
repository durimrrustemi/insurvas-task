from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.message import Channel, MessageStatus


class MessageRead(BaseModel):
    id: uuid.UUID
    partner_id: uuid.UUID
    channel: Channel
    sequence: int
    subject: str | None
    body: str
    angle: str | None
    evidence_ids: list | None
    status: MessageStatus
    send_after: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageUpdate(BaseModel):
    subject: str | None = None
    body: str | None = None
    status: MessageStatus | None = None
