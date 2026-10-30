from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import Conflict, InvalidTransition, NotFound
from app.models.activity import Activity, ActivityKind
from app.models.partner import Blocker, Partner, Stage
from app.schemas.partner import PartnerCreate, PartnerUpdate

ALLOWED_TRANSITIONS: dict[Stage, list[Stage]] = {
    Stage.FOUND: [Stage.CONTACTED, Stage.LOST],
    Stage.CONTACTED: [Stage.REPLIED, Stage.LOST],
    Stage.REPLIED: [Stage.IN_TALKS, Stage.LOST],
    Stage.IN_TALKS: [Stage.TEST_CALLS, Stage.LOST],
    Stage.TEST_CALLS: [Stage.SIGNED, Stage.LOST],
    Stage.SIGNED: [Stage.LOST],
    Stage.LOST: [Stage.FOUND],
}


def normalise_domain(raw: str) -> str:
    d = raw.lower().strip()
    for prefix in ("https://", "http://", "www."):
        if d.startswith(prefix):
            d = d[len(prefix) :]
    return d.rstrip("/")


async def list_partners(
    session: AsyncSession,
    *,
    country: str | None = None,
    stage: Stage | None = None,
    blocker: Blocker | None = None,
    min_score: float | None = None,
    sort: str = "score_total",
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Partner], int]:
    q = select(Partner)
    count_q = select(func.count()).select_from(Partner)

    if country:
        q = q.where(Partner.country == country)
        count_q = count_q.where(Partner.country == country)
    if stage:
        q = q.where(Partner.stage == stage)
        count_q = count_q.where(Partner.stage == stage)
    if blocker:
        q = q.where(Partner.blocker == blocker)
        count_q = count_q.where(Partner.blocker == blocker)
    if min_score is not None:
        q = q.where(Partner.score_total >= min_score)
        count_q = count_q.where(Partner.score_total >= min_score)

    if sort == "score_total":
        q = q.order_by(Partner.score_total.desc().nulls_last())
    elif sort == "created_at":
        q = q.order_by(Partner.created_at.desc())
    elif sort == "updated_at":
        q = q.order_by(Partner.updated_at.desc())
    else:
        q = q.order_by(Partner.created_at.desc())

    total = (await session.execute(count_q)).scalar_one()
    result = await session.execute(q.limit(limit).offset(offset))
    return list(result.scalars().all()), total


async def get_partner(session: AsyncSession, partner_id: uuid.UUID) -> Partner:
    partner = await session.get(Partner, partner_id)
    if not partner:
        raise NotFound(f"Partner {partner_id} not found")
    return partner


async def create_partner(session: AsyncSession, data: PartnerCreate) -> Partner:
    domain = normalise_domain(data.domain)
    existing = await session.execute(select(Partner).where(Partner.domain == domain))
    if existing.scalar_one_or_none():
        raise Conflict(f"Partner with domain {domain} already exists")

    now = datetime.now(timezone.utc)
    partner = Partner(
        name=data.name,
        domain=domain,
        website=data.website or f"https://{domain}",
        country=data.country,
        city=data.city,
        timezone=data.timezone,
        type=data.type,
        stage=Stage.FOUND,
        stage_entered_at=now,
    )
    session.add(partner)
    await session.flush()
    return partner


async def update_partner(
    session: AsyncSession, partner_id: uuid.UUID, data: PartnerUpdate
) -> Partner:
    partner = await get_partner(session, partner_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(partner, key, value)
    await session.flush()
    return partner


async def delete_partner(session: AsyncSession, partner_id: uuid.UUID) -> None:
    partner = await get_partner(session, partner_id)
    await session.delete(partner)
    await session.flush()


async def transition(
    session: AsyncSession,
    partner_id: uuid.UUID,
    to_stage: Stage,
    reason: str | None = None,
) -> Partner:
    partner = await get_partner(session, partner_id)
    allowed = ALLOWED_TRANSITIONS.get(partner.stage, [])
    if to_stage not in allowed:
        raise InvalidTransition(
            f"Cannot transition from {partner.stage.value} to {to_stage.value}",
            details={
                "from": partner.stage.value,
                "to": to_stage.value,
                "allowed": [s.value for s in allowed],
            },
        )

    now = datetime.now(timezone.utc)
    old_stage = partner.stage
    partner.stage = to_stage
    partner.stage_entered_at = now

    activity = Activity(
        partner_id=partner.id,
        kind=ActivityKind.STAGE_CHANGE,
        body=f"{old_stage.value} -> {to_stage.value}" + (f": {reason}" if reason else ""),
        at=now,
    )
    session.add(activity)
    await session.flush()
    return partner
