from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import rules
from app.config import app_config
from app.discovery.dedupe import normalise_domain
from app.errors import Conflict, GateBlocked, InvalidTransition, NotFound
from app.models.activity import Activity, ActivityKind
from app.models.contact import Contact
from app.models.partner import Blocker, Partner, PartnerType, Stage
from app.models.signal import Signal
from app.schemas.partner import PartnerCreate, PartnerUpdate
from app.scoring import SignalResult
from app.scoring.gates import GATE_CRITERION, GateStatus, evaluate_gates


async def list_partners(
    session: AsyncSession,
    *,
    country: str | None = None,
    stage: Stage | None = None,
    blocker: Blocker | None = None,
    partner_type: PartnerType | None = None,
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
    if partner_type:
        q = q.where(Partner.type == partner_type)
        count_q = count_q.where(Partner.type == partner_type)
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
    if "blocker" in update_data and update_data["blocker"] != partner.blocker:
        new = update_data["blocker"]
        session.add(
            Activity(
                partner_id=partner.id,
                kind=ActivityKind.BLOCKER,
                body=f"blocker: {new.value if new else 'cleared'}",
                at=datetime.now(timezone.utc),
            )
        )
    for key, value in update_data.items():
        setattr(partner, key, value)
    await session.flush()
    return partner


async def delete_partner(session: AsyncSession, partner_id: uuid.UUID) -> None:
    partner = await get_partner(session, partner_id)
    await session.delete(partner)
    await session.flush()


async def _signal_results(session: AsyncSession, partner_id: uuid.UUID) -> list[SignalResult]:
    result = await session.execute(
        select(Signal).where(Signal.partner_id == partner_id).order_by(Signal.created_at, Signal.id)
    )
    return [
        SignalResult(
            criterion=s.criterion,
            key=s.key,
            value=s.value,
            weight=s.weight,
            source_url=s.source_url or "",
            matched_text=s.matched_text or "",
        )
        for s in result.scalars().all()
    ]


async def _readiness(session: AsyncSession, partner: Partner, to_stage: str) -> rules.Readiness:
    contacts = await session.execute(select(Contact.name).where(Contact.partner_id == partner.id))
    return rules.readiness(
        to_stage,
        gates=app_config.gates,
        signals=await _signal_results(session, partner.id),
        contact_names=[n or "" for n in contacts.scalars().all()],
        terms=partner.engagement_terms,
    )


async def get_readiness(session: AsyncSession, partner_id: uuid.UUID) -> dict:
    """Gate statuses plus readiness for every stage the partner can move to next."""
    partner = await get_partner(session, partner_id)
    signals = await _signal_results(session, partner.id)
    next_stages = rules.ALLOWED_TRANSITIONS.get(partner.stage.value, [])
    return {
        "gates": {k: v.value for k, v in evaluate_gates(app_config.gates, signals).items()},
        "transitions": [
            _readiness_dict(await _readiness(session, partner, to)) for to in next_stages
        ],
    }


def _readiness_dict(r: rules.Readiness) -> dict:
    return {"to": r.to, "ready": r.ready, "checks": [asdict(c) for c in r.checks]}


async def transition(
    session: AsyncSession,
    partner_id: uuid.UUID,
    to_stage: Stage,
    reason: str | None = None,
) -> Partner:
    partner = await get_partner(session, partner_id)
    if not rules.is_allowed(partner.stage.value, to_stage.value):
        allowed = rules.ALLOWED_TRANSITIONS.get(partner.stage.value, [])
        raise InvalidTransition(
            f"Cannot transition from {partner.stage.value} to {to_stage.value}",
            details={"from": partner.stage.value, "to": to_stage.value, "allowed": allowed},
        )

    check = await _readiness(session, partner, to_stage.value)
    if not check.ready:
        raise GateBlocked(
            f"Not ready for {to_stage.value}: " + ", ".join(c.label for c in check.failed),
            details={"to": to_stage.value, "failed": [c.key for c in check.failed]},
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


async def set_gate(
    session: AsyncSession,
    partner_id: uuid.UUID,
    gate: str,
    confirmed: bool,
    source: str | None = None,
) -> Signal:
    """Record a manual gate decision. A `no` moves the partner to lost with reason gate:<name>."""
    if gate not in app_config.gates:
        raise NotFound(f"Gate {gate} not found", details={"known": list(app_config.gates)})
    partner = await get_partner(session, partner_id)

    signal = Signal(
        partner_id=partner.id,
        criterion=GATE_CRITERION,
        key=gate,
        value=1.0 if confirmed else 0.0,
        weight=0.0,
        source_url=source,
        matched_text=f"manual: {GateStatus.CONFIRMED if confirmed else GateStatus.NO}",
    )
    session.add(signal)
    session.add(
        Activity(
            partner_id=partner.id,
            kind=ActivityKind.NOTE,
            body=f"gate {gate}: {'confirmed' if confirmed else 'no'}"
            + (f" (source: {source})" if source else ""),
            at=datetime.now(timezone.utc),
        )
    )
    await session.flush()

    if not confirmed and partner.stage != Stage.LOST:
        await transition(session, partner.id, Stage.LOST, reason=f"gate:{gate}")
    return signal
