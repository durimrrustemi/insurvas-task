"""Discovery service: orchestrates discovery runs and persists results."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import app_config
from app.discovery.classify import classify_partner_type
from app.discovery.dedupe import normalise_domain
from app.discovery.runner import DiscoveryResult, run_discovery
from app.models.discovery_run import DiscoveryRun
from app.models.page import Page
from app.models.partner import Partner, Stage
from app.services.scoring import score_partner
from app.settings import settings

logger = logging.getLogger(__name__)


async def start_discovery(
    session: AsyncSession,
    country: str,
    limit: int = 30,
) -> DiscoveryRun:
    """Create a discovery run record and execute the pipeline."""
    run = DiscoveryRun(
        country=country,
        queries=[],
        found=0,
        new=0,
    )
    session.add(run)
    await session.flush()

    result = await run_discovery(
        config=app_config,
        country_code=country,
        limit=limit,
        serper_key=settings.serper_api_key,
        places_key=settings.google_places_key,
    )

    new_count, partner_ids = await _persist_results(session, result)

    # Score right away so new candidates show up ranked, with their evidence.
    for pid in partner_ids:
        try:
            await score_partner(session, pid)
        except Exception:
            logger.exception("Scoring failed for discovered partner %s", pid)

    run.queries = result.queries_used
    run.found = result.total_found
    run.new = new_count
    run.finished_at = result.finished_at
    await session.flush()

    logger.info(
        "Discovery run %s: country=%s found=%d new=%d",
        run.id,
        country,
        run.found,
        run.new,
    )
    return run


async def _persist_results(
    session: AsyncSession,
    result: DiscoveryResult,
) -> tuple[int, list[uuid.UUID]]:
    """Upsert partners and pages from discovery results. Returns new count."""
    new_count = 0
    partner_ids: list[uuid.UUID] = []
    now = datetime.now(timezone.utc)

    for enriched in result.candidates:
        c = enriched.candidate
        domain = normalise_domain(c.url)
        if not domain:
            continue

        # Check if partner already exists
        existing = await session.execute(select(Partner).where(Partner.domain == domain))
        partner = existing.scalar_one_or_none()

        if partner is None:
            name = enriched.title or c.name or domain
            # Clean up name: remove " - Home", " | Official Site", etc.
            for suffix in [
                " - Home",
                " | Home",
                " - Official",
                " | Official",
            ]:
                if name.endswith(suffix):
                    name = name[: -len(suffix)]

            partner = Partner(
                name=name.strip()[:255],
                domain=domain,
                website=c.url,
                country=c.country or result.country,
                city=c.city or None,
                timezone=(
                    app_config.get_country(result.country).timezone
                    if app_config.get_country(result.country)
                    else None
                ),
                type=classify_partner_type(
                    " ".join([name, c.snippet, enriched.homepage_text[:5000]])
                ),
                stage=Stage.FOUND,
                stage_entered_at=now,
            )
            session.add(partner)
            await session.flush()
            new_count += 1

        partner_ids.append(partner.id)

        # Store homepage page record
        page = Page(
            partner_id=partner.id,
            url=c.url,
            status=200 if enriched.homepage_text else 0,
            text_path=None,  # text stored in cache on disk
        )
        session.add(page)

        # Store inner pages
        for inner_url in enriched.inner_urls:
            inner_page = Page(
                partner_id=partner.id,
                url=inner_url,
                status=200 if inner_url in enriched.inner_texts else 0,
                text_path=None,
            )
            session.add(inner_page)

    await session.flush()
    return new_count, partner_ids


async def get_discovery_run(session: AsyncSession, run_id: uuid.UUID) -> DiscoveryRun | None:
    return await session.get(DiscoveryRun, run_id)


async def list_discovery_runs(
    session: AsyncSession,
) -> list[DiscoveryRun]:
    result = await session.execute(select(DiscoveryRun).order_by(DiscoveryRun.started_at.desc()))
    return list(result.scalars().all())
