"""Scoring service: loads page texts, runs signal extraction, persists results."""

from __future__ import annotations

import json
import logging
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import app_config
from app.discovery.extract import extract_text
from app.discovery.fetch import CACHE_DIR
from app.models.page import Page
from app.models.partner import Partner
from app.models.signal import Signal
from app.scoring import ScoreResult, SignalResult
from app.scoring.extract_signals import extract_all_signals
from app.scoring.gates import GATE_CRITERION
from app.scoring.score import compute_scores
from app.services.partners import get_partner

logger = logging.getLogger(__name__)


async def score_partner(
    session: AsyncSession,
    partner_id: uuid.UUID,
) -> ScoreResult:
    """Score a single partner: extract signals from cached pages, compute scores, persist."""
    partner = await get_partner(session, partner_id)

    # Load page texts from cache
    texts = await _load_partner_texts(session, partner)

    # Extract signals (pure function)
    signal_results = extract_all_signals(texts, partner.country, app_config)

    # Compute scores (pure function)
    score_result = compute_scores(signal_results, app_config)

    # Persist: replace extracted signals; manual gate decisions survive a rescore
    await session.execute(
        delete(Signal).where(Signal.partner_id == partner_id, Signal.criterion != GATE_CRITERION)
    )

    for sr in signal_results:
        signal = Signal(
            partner_id=partner_id,
            criterion=sr.criterion,
            key=sr.key,
            value=sr.value,
            weight=sr.weight,
            source_url=sr.source_url or None,
            matched_text=sr.matched_text or None,
        )
        session.add(signal)

    _apply_scores(partner, score_result)
    await session.flush()

    logger.info(
        "Scored partner %s (%s): total=%s signals=%d",
        partner.name,
        partner.domain,
        score_result.total,
        len(signal_results),
    )
    return score_result


def _apply_scores(partner: Partner, result: ScoreResult) -> None:
    partner.score_total = result.total
    partner.score_english = _criterion_score(result, "english")
    partner.score_insurance = _criterion_score(result, "insurance")
    partner.score_size = _criterion_score(result, "size")
    partner.score_compliance = _criterion_score(result, "compliance")


async def recompute_scores(session: AsyncSession, country: str | None = None) -> int:
    """Re-run the formula on stored evidence with the current config weights.

    No fetching or extraction: use after editing scoring.yaml. Signal weights are
    refreshed from config for known keys so the evidence UI shows what was used.
    """
    q = select(Partner)
    if country:
        q = q.where(Partner.country == country)
    partners = list((await session.execute(q)).scalars().all())

    for partner in partners:
        rows = (
            await session.execute(
                select(Signal).where(
                    Signal.partner_id == partner.id, Signal.criterion != GATE_CRITERION
                )
            )
        ).scalars()
        results = []
        for row in rows:
            cfg = app_config.signals.get(row.criterion, {}).get(row.key)
            if cfg:
                row.weight = cfg.weight
            results.append(
                SignalResult(
                    criterion=row.criterion,
                    key=row.key,
                    value=row.value,
                    weight=row.weight,
                    source_url=row.source_url or "",
                    matched_text=row.matched_text or "",
                )
            )
        _apply_scores(partner, compute_scores(results, app_config))

    await session.flush()
    return len(partners)


async def score_all_partners(
    session: AsyncSession,
    country: str | None = None,
) -> int:
    """Score all partners (optionally filtered by country). Returns count scored."""
    q = select(Partner)
    if country:
        q = q.where(Partner.country == country)

    result = await session.execute(q)
    partners = list(result.scalars().all())

    count = 0
    for partner in partners:
        try:
            await score_partner(session, partner.id)
            count += 1
        except Exception:
            logger.exception("Failed to score partner %s", partner.domain)

    return count


async def _load_partner_texts(
    session: AsyncSession,
    partner: Partner,
) -> dict[str, str]:
    """Load cached page texts for a partner."""
    result = await session.execute(select(Page).where(Page.partner_id == partner.id))
    pages = list(result.scalars().all())

    texts: dict[str, str] = {}
    for page in pages:
        text = _read_cached_text(page.url)
        if text:
            texts[page.url] = text

    # If no pages in DB, try the partner website directly
    if not texts and partner.website:
        text = _read_cached_text(partner.website)
        if text:
            texts[partner.website] = text

    return texts


def _read_cached_text(url: str) -> str:
    """Read text from the page cache."""
    import hashlib

    cache_path = CACHE_DIR / f"{hashlib.sha1(url.encode()).hexdigest()}.json"
    if not cache_path.exists():
        return ""
    try:
        data = json.loads(cache_path.read_text())
        html = data.get("html", "")
        if html:
            return extract_text(html)
    except (json.JSONDecodeError, OSError):
        pass
    return ""


def _criterion_score(result: ScoreResult, criterion: str) -> float | None:
    cs = result.criteria.get(criterion)
    if cs and cs.coverage > 0:
        return round(cs.score, 4)
    return None
