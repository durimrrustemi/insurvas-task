"""Outreach service: generates angle + drafts, persists messages."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import app_config
from app.models.message import Channel, Message, MessageStatus
from app.models.signal import Signal
from app.outreach.angle import format_evidence, generate_angle
from app.outreach.draft import generate_drafts
from app.scoring import SignalResult
from app.services.partners import get_partner

logger = logging.getLogger(__name__)


async def generate_outreach(
    session: AsyncSession,
    partner_id: uuid.UUID,
    channels: list[str] | None = None,
) -> list[Message]:
    """Generate outreach messages for a partner.

    1. Load signals
    2. Generate angle from signals
    3. Draft messages per channel × sequence
    4. Persist as draft messages
    """
    partner = await get_partner(session, partner_id)

    # Determine channels
    if channels is None:
        country_cfg = app_config.get_country(partner.country)
        if country_cfg:
            channels = country_cfg.preferred_channels
        else:
            channels = ["email"]

    # Load signals
    result = await session.execute(select(Signal).where(Signal.partner_id == partner_id))
    db_signals = list(result.scalars().all())

    signal_results = [
        SignalResult(
            criterion=s.criterion,
            key=s.key,
            value=s.value,
            weight=s.weight,
            source_url=s.source_url or "",
            matched_text=s.matched_text or "",
        )
        for s in db_signals
    ]

    # Generate angle
    angle = await generate_angle(
        partner_name=partner.name,
        partner_domain=partner.domain,
        partner_country=partner.country,
        signals=signal_results,
    )

    # Generate drafts
    evidence_text = format_evidence(signal_results)
    cadence = app_config.cadence
    if cadence is None:
        raise ValueError("Cadence config not loaded")

    drafted = await generate_drafts(
        partner_name=partner.name,
        partner_domain=partner.domain,
        partner_country=partner.country,
        angle=angle,
        evidence_text=evidence_text,
        channels=channels,
        cadence=cadence,
    )

    # Collect signal IDs for evidence linking
    signal_ids = [str(s.id) for s in db_signals]

    # Persist messages
    messages: list[Message] = []
    for draft in drafted:
        msg = Message(
            partner_id=partner_id,
            channel=Channel(draft.channel),
            sequence=draft.sequence,
            subject=draft.subject,
            body=draft.body,
            angle=draft.angle,
            evidence_ids=signal_ids,
            status=MessageStatus.DRAFT,
            send_after=draft.send_after,
        )
        session.add(msg)
        messages.append(msg)

    await session.flush()

    logger.info(
        "Generated %d outreach messages for %s (%s)",
        len(messages),
        partner.name,
        ", ".join(channels),
    )
    return messages
