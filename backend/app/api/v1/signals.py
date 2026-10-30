from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.signal import Signal
from app.schemas.signal import SignalCreate, SignalRead, SignalUpdate

router = APIRouter(tags=["signals"])


@router.get("/partners/{partner_id}/signals", response_model=list[SignalRead])
async def list_signals(
    partner_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Signal).where(Signal.partner_id == partner_id).order_by(Signal.criterion, Signal.key)
    )
    return [SignalRead.model_validate(s) for s in result.scalars().all()]


@router.post("/partners/{partner_id}/signals", response_model=SignalRead, status_code=201)
async def create_signal(
    partner_id: uuid.UUID,
    data: SignalCreate,
    session: AsyncSession = Depends(get_session),
):
    signal = Signal(partner_id=partner_id, **data.model_dump())
    session.add(signal)
    await session.commit()
    return SignalRead.model_validate(signal)


@router.patch("/signals/{signal_id}", response_model=SignalRead)
async def update_signal(
    signal_id: uuid.UUID,
    data: SignalUpdate,
    session: AsyncSession = Depends(get_session),
):
    signal = await session.get(Signal, signal_id)
    if not signal:
        from app.errors import NotFound

        raise NotFound(f"Signal {signal_id} not found")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(signal, key, value)
    await session.commit()
    return SignalRead.model_validate(signal)
