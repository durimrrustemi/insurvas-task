from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import NotFound
from app.models.message import Message
from app.schemas.message import MessageRead, MessageUpdate

router = APIRouter(tags=["messages"])


@router.get("/partners/{partner_id}/messages", response_model=list[MessageRead])
async def list_messages(
    partner_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Message)
        .where(Message.partner_id == partner_id)
        .order_by(Message.channel, Message.sequence)
    )
    return [MessageRead.model_validate(m) for m in result.scalars().all()]


@router.patch("/messages/{message_id}", response_model=MessageRead)
async def update_message(
    message_id: uuid.UUID,
    data: MessageUpdate,
    session: AsyncSession = Depends(get_session),
):
    message = await session.get(Message, message_id)
    if not message:
        raise NotFound(f"Message {message_id} not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(message, key, value)
    await session.commit()
    return MessageRead.model_validate(message)
