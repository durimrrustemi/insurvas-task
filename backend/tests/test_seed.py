"""The demo seed must obey the same rules as the app, or the demo contradicts itself."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import rules
from app.config import app_config
from app.models.contact import Contact
from app.models.partner import Stage
from app.models.signal import Signal
from app.scoring import SignalResult
from app.seed import seed_partners


async def test_every_seed_partner_could_have_reached_its_stage(session: AsyncSession):
    partners = await seed_partners(session)
    for p in partners:
        rows = (
            await session.execute(
                select(Signal).where(Signal.partner_id == p.id).order_by(Signal.created_at)
            )
        ).scalars()
        signals = [
            SignalResult(r.criterion, r.key, r.value, r.weight, "", r.matched_text or "")
            for r in rows
        ]
        names = (
            await session.execute(select(Contact.name).where(Contact.partner_id == p.id))
        ).scalars()
        check = rules.readiness(
            p.stage.value,
            gates=app_config.gates,
            signals=signals,
            contact_names=list(names),
            terms=p.engagement_terms,
        )
        assert check.ready, (p.name, p.stage, [c.key for c in check.failed])


async def test_blockers_only_on_open_deals(session: AsyncSession):
    partners = await seed_partners(session)
    blocked = [p for p in partners if p.blocker]
    assert len(blocked) == 2
    assert all(p.stage not in (Stage.FOUND, Stage.SIGNED, Stage.LOST) for p in blocked)


async def test_gated_partners_show_compliance_evidence(session: AsyncSession):
    partners = await seed_partners(session)
    for p in partners:
        if p.stage in (Stage.TEST_CALLS, Stage.SIGNED):
            assert p.score_compliance is not None, p.name


async def test_attention_has_overdue_partners(client: AsyncClient, session: AsyncSession):
    await seed_partners(session)
    items = (await client.get("/api/v1/attention")).json()["items"]
    overdue = [i for i in items if any(r.startswith("no touch") for r in i["reasons"])]
    assert len(overdue) >= 3


async def test_seed_has_vendors_in_the_us_only(session: AsyncSession):
    from app.models.partner import PartnerType

    partners = await seed_partners(session)
    vendors = [p for p in partners if p.type == PartnerType.VENDOR]
    assert vendors
    assert all(p.country == "US" for p in vendors)
