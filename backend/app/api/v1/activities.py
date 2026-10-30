from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.activity import Activity
from app.schemas.activity import ActivityCreate, ActivityRead

router = APIRouter(tags=["activities"])


@router.get("/partners/{partner_id}/activities", response_model=list[ActivityRead])
async def list_activities(
    partner_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Activity).where(Activity.partner_id == partner_id).order_by(Activity.at.desc())
    )
    return [ActivityRead.model_validate(a) for a in result.scalars().all()]


@router.post("/partners/{partner_id}/activities", response_model=ActivityRead, status_code=201)
async def create_activity(
    partner_id: uuid.UUID,
    data: ActivityCreate,
    session: AsyncSession = Depends(get_session),
):
    activity = Activity(partner_id=partner_id, **data.model_dump())
    session.add(activity)
    await session.commit()
    return ActivityRead.model_validate(activity)
