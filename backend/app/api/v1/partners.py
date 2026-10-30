from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.partner import Blocker, PartnerType, Stage
from app.schemas.message import MessageRead, OutreachRequest
from app.schemas.partner import (
    PartnerCreate,
    PartnerList,
    PartnerRead,
    PartnerReadiness,
    PartnerUpdate,
    StageTransition,
)
from app.services import outreach as outreach_service
from app.services import partners as partner_service
from app.services import scoring as scoring_service

router = APIRouter(prefix="/partners", tags=["partners"])


@router.get("", response_model=PartnerList)
async def list_partners(
    session: AsyncSession = Depends(get_session),
    country: str | None = Query(None),
    stage: Stage | None = Query(None),
    blocker: Blocker | None = Query(None),
    type: PartnerType | None = Query(None),
    min_score: float | None = Query(None),
    sort: str = Query("score_total"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    items, total = await partner_service.list_partners(
        session,
        country=country,
        stage=stage,
        blocker=blocker,
        partner_type=type,
        min_score=min_score,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return PartnerList(
        items=[PartnerRead.model_validate(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=PartnerRead, status_code=201)
async def create_partner(
    data: PartnerCreate,
    session: AsyncSession = Depends(get_session),
):
    partner = await partner_service.create_partner(session, data)
    await session.commit()
    return PartnerRead.model_validate(partner)


@router.get("/{partner_id}", response_model=PartnerRead)
async def get_partner(
    partner_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    partner = await partner_service.get_partner(session, partner_id)
    return PartnerRead.model_validate(partner)


@router.patch("/{partner_id}", response_model=PartnerRead)
async def update_partner(
    partner_id: uuid.UUID,
    data: PartnerUpdate,
    session: AsyncSession = Depends(get_session),
):
    partner = await partner_service.update_partner(session, partner_id, data)
    await session.commit()
    return PartnerRead.model_validate(partner)


@router.delete("/{partner_id}", status_code=204)
async def delete_partner(
    partner_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    await partner_service.delete_partner(session, partner_id)
    await session.commit()


@router.post("/{partner_id}/score", response_model=PartnerRead)
async def score_partner(
    partner_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    await scoring_service.score_partner(session, partner_id)
    await session.commit()
    partner = await partner_service.get_partner(session, partner_id)
    return PartnerRead.model_validate(partner)


@router.post(
    "/{partner_id}/outreach",
    response_model=list[MessageRead],
    status_code=201,
)
async def generate_outreach(
    partner_id: uuid.UUID,
    data: OutreachRequest | None = None,
    session: AsyncSession = Depends(get_session),
):
    channels = [c.value for c in data.channels] if data and data.channels else None
    messages = await outreach_service.generate_outreach(session, partner_id, channels)
    await session.commit()
    return [MessageRead.model_validate(m) for m in messages]


@router.get("/{partner_id}/readiness", response_model=PartnerReadiness)
async def get_readiness(
    partner_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    return await partner_service.get_readiness(session, partner_id)


@router.post("/{partner_id}/stage", response_model=PartnerRead)
async def transition_stage(
    partner_id: uuid.UUID,
    data: StageTransition,
    session: AsyncSession = Depends(get_session),
):
    partner = await partner_service.transition(session, partner_id, data.to, data.reason)
    await session.commit()
    return PartnerRead.model_validate(partner)
