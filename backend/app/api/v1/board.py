"""Board and attention endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import app_config
from app.db import get_session
from app.models.activity import Activity
from app.models.partner import Partner, Stage
from app.schemas.partner import PartnerRead

router = APIRouter(tags=["board"])

STAGES_ORDER = [
    Stage.FOUND,
    Stage.CONTACTED,
    Stage.REPLIED,
    Stage.IN_TALKS,
    Stage.TEST_CALLS,
    Stage.SIGNED,
    Stage.LOST,
]


@router.get("/board")
async def get_board(
    session: AsyncSession = Depends(get_session),
):
    """Partners grouped by stage for kanban view."""
    result = await session.execute(
        select(Partner).order_by(Partner.score_total.desc().nulls_last())
    )
    partners = list(result.scalars().all())

    columns: dict[str, list[dict]] = {}
    for stage in STAGES_ORDER:
        columns[stage.value] = []

    for p in partners:
        columns[p.stage.value].append(PartnerRead.model_validate(p).model_dump(mode="json"))

    return {"columns": columns}


@router.get("/attention")
async def get_attention(
    session: AsyncSession = Depends(get_session),
):
    """Partners needing attention, sorted by urgency.

    Priority order:
    1. Replied + gates look good but not in test calls
    2. In test calls past expected end date
    3. No touch >= reminder_days
    4. Stale in stage >= stale_stage_days
    5. New high-score candidates not yet contacted
    """
    now = datetime.now(timezone.utc)
    cadence = app_config.cadence
    reminder_days = cadence.reminder_days if cadence else 3
    stale_days = cadence.stale_stage_days if cadence else 7

    result = await session.execute(
        select(Partner).where(Partner.stage != Stage.LOST, Partner.stage != Stage.SIGNED)
    )
    partners = list(result.scalars().all())

    # Get last touch per partner
    activities_result = await session.execute(select(Activity).order_by(Activity.at.desc()))
    all_activities = list(activities_result.scalars().all())
    last_touch: dict[str, datetime] = {}
    for a in all_activities:
        pid = str(a.partner_id)
        if pid not in last_touch:
            last_touch[pid] = a.at

    items: list[dict] = []
    for p in partners:
        pid = str(p.id)
        reasons: list[str] = []
        priority = 99

        touch_at = last_touch.get(pid)
        days_since_touch = (now - touch_at).days if touch_at else 999
        days_in_stage = (now - p.stage_entered_at).days if p.stage_entered_at else 999

        # 1. Replied but not in test calls
        if p.stage == Stage.REPLIED:
            reasons.append("replied — ready to advance?")
            priority = min(priority, 1)

        # 2. In test calls — check if stale
        if p.stage == Stage.TEST_CALLS and days_in_stage >= stale_days:
            reasons.append(f"in test calls for {days_in_stage}d")
            priority = min(priority, 2)

        # 3. No touch >= reminder_days
        if days_since_touch >= reminder_days and p.stage not in (Stage.FOUND,):
            reasons.append(f"no touch for {days_since_touch}d")
            priority = min(priority, 3)

        # 4. Stale in stage
        if days_in_stage >= stale_days:
            reasons.append(f"stale in {p.stage.value} for {days_in_stage}d")
            priority = min(priority, 4)

        # 5. High-score found, not contacted
        if p.stage == Stage.FOUND and p.score_total and p.score_total > 0.5:
            reasons.append(f"high score ({p.score_total:.0%}) not contacted")
            priority = min(priority, 5)

        # Blockers always show
        if p.blocker:
            reasons.append(f"blocker: {p.blocker.value.replace('_', ' ')}")
            priority = min(priority, 3)

        if reasons:
            items.append(
                {
                    "partner": PartnerRead.model_validate(p).model_dump(mode="json"),
                    "reasons": reasons,
                    "priority": priority,
                    "days_since_touch": days_since_touch,
                    "days_in_stage": days_in_stage,
                }
            )

    items.sort(key=lambda x: (x["priority"], -x["days_since_touch"]))
    return {"items": items}
