"""Scores must trace back to stored evidence, and follow config weight changes."""

from __future__ import annotations

import dataclasses
import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import app_config
from app.models.partner import Partner
from app.models.signal import Signal
from app.scoring import SignalResult
from app.scoring.score import compute_scores
from app.seed import _synthetic_signals, seed_partners
from app.services import scoring as scoring_service


async def _rows(session: AsyncSession, partner: Partner) -> list[SignalResult]:
    rows = (await session.execute(select(Signal).where(Signal.partner_id == partner.id))).scalars()
    return [SignalResult(r.criterion, r.key, r.value, r.weight) for r in rows]


async def test_seed_scores_match_their_evidence(session: AsyncSession):
    partners = await seed_partners(session)
    assert len(partners) == 30
    for p in partners:
        expected = compute_scores(await _rows(session, p), app_config)
        assert p.score_total == expected.total, p.name
        assert p.score_total is not None


def test_seed_evidence_is_deterministic():
    # Same RNG seed -> same demo pipeline on every fresh setup.
    p = Partner(name="X", domain="x.test", country="PH")
    first = _synthetic_signals(random.Random(42), p)
    second = _synthetic_signals(random.Random(42), p)
    assert first == second
    assert first[0].key == "english_baseline"
    assert all(s.key in app_config.signals[s.criterion] for s in first)


async def test_seed_spreads_scores(session: AsyncSession):
    totals = [p.score_total for p in await seed_partners(session)]
    assert len(set(totals)) > 10


async def test_recompute_follows_criterion_weight_change(session: AsyncSession, monkeypatch):
    english = Partner(name="English BPO", domain="en.test", country="PH")
    insurance = Partner(name="Insurance BPO", domain="ins.test", country="PH")
    session.add_all([english, insurance])
    await session.flush()
    session.add_all(
        [
            Signal(partner_id=english.id, criterion="english", key="x", value=1.0, weight=1.0),
            Signal(partner_id=english.id, criterion="insurance", key="x", value=0.2, weight=1.0),
            Signal(partner_id=insurance.id, criterion="english", key="x", value=0.2, weight=1.0),
            Signal(partner_id=insurance.id, criterion="insurance", key="x", value=1.0, weight=1.0),
        ]
    )
    await session.flush()

    def with_weights(english_w: float, insurance_w: float) -> None:
        weights = {**app_config.criterion_weights, "english": english_w, "insurance": insurance_w}
        cfg = dataclasses.replace(app_config, criterion_weights=weights)
        monkeypatch.setattr(scoring_service, "app_config", cfg)

    with_weights(0.9, 0.1)
    await scoring_service.recompute_scores(session)
    assert english.score_total > insurance.score_total

    with_weights(0.1, 0.9)
    await scoring_service.recompute_scores(session)
    assert insurance.score_total > english.score_total


async def test_recompute_refreshes_signal_weight_from_config(session: AsyncSession, monkeypatch):
    p = Partner(name="Seats BPO", domain="seats.test", country="PH")
    session.add(p)
    await session.flush()
    row = Signal(partner_id=p.id, criterion="size", key="stated_seats", value=0.8, weight=3.0)
    session.add(row)
    await session.flush()

    size = dict(app_config.signals["size"])
    size["stated_seats"] = dataclasses.replace(size["stated_seats"], weight=5.0)
    cfg = dataclasses.replace(app_config, signals={**app_config.signals, "size": size})
    monkeypatch.setattr(scoring_service, "app_config", cfg)

    await scoring_service.recompute_scores(session)
    assert row.weight == 5.0
