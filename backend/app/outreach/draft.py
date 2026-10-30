"""Draft outreach messages per channel and sequence, with length enforcement."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import CadenceConfig
from app.prompts.draft_v1 import DRAFT_V1
from app.services.llm import DraftResponse, complete_json


@dataclass
class DraftedMessage:
    """A drafted message ready for persistence."""

    channel: str
    sequence: int
    intent: str
    subject: str | None
    body: str
    angle: str
    send_after: datetime


async def generate_drafts(
    partner_name: str,
    partner_domain: str,
    partner_country: str,
    angle: str,
    evidence_text: str,
    channels: list[str],
    cadence: CadenceConfig,
) -> list[DraftedMessage]:
    """Generate message drafts for each channel and sequence."""
    now = datetime.now(timezone.utc)
    drafts: list[DraftedMessage] = []

    max_sequences = min(
        len(cadence.follow_up_days),
        cadence.max_follow_ups + 1,  # +1 for the intro
    )

    for channel in channels:
        limits = cadence.channel_limits.get(channel, {})

        for intent_info in cadence.intents[:max_sequences]:
            seq = intent_info["sequence"]
            intent = intent_info["intent"]
            intent_desc = intent_info["description"]

            if seq < len(cadence.follow_up_days):
                day_offset = cadence.follow_up_days[seq]
            else:
                day_offset = seq * 3
            send_after = now + timedelta(days=day_offset)

            prompt_name = f"DRAFT_V1_{channel}_{seq}"
            variables = {
                "channel": channel,
                "sequence": seq,
                "intent": intent,
                "intent_description": intent_desc,
                "partner_name": partner_name,
                "partner_domain": partner_domain,
                "partner_country": partner_country,
                "angle": angle,
                "evidence": evidence_text,
                "max_words": limits.get("max_words", 120),
                "max_subject_chars": limits.get("max_subject_chars", 60),
                "max_chars": limits.get("max_chars", 300),
            }

            result = await complete_json(
                prompt_name=prompt_name,
                prompt=DRAFT_V1,
                variables=variables,
                schema=DraftResponse,
            )

            # Enforce hard length limits
            body = _enforce_limits(result.body, channel, limits)
            subject = _enforce_subject(result.subject, limits)

            drafts.append(
                DraftedMessage(
                    channel=channel,
                    sequence=seq,
                    intent=intent,
                    subject=subject,
                    body=body,
                    angle=angle,
                    send_after=send_after,
                )
            )

    return drafts


def _enforce_limits(body: str, channel: str, limits: dict[str, Any]) -> str:
    """Enforce hard length limits on message body."""
    if channel == "email":
        max_words = limits.get("max_words", 120)
        words = body.split()
        if len(words) > max_words:
            body = " ".join(words[:max_words])
    else:
        max_chars = limits.get("max_chars", 300)
        if len(body) > max_chars:
            body = body[:max_chars].rsplit(" ", 1)[0]
    return body


def _enforce_subject(subject: str | None, limits: dict[str, Any]) -> str | None:
    if subject is None:
        return None
    max_chars = limits.get("max_subject_chars", 60)
    if len(subject) > max_chars:
        subject = subject[:max_chars].rsplit(" ", 1)[0]
    return subject


def compute_send_dates(
    cadence: CadenceConfig,
    start: datetime | None = None,
) -> list[datetime]:
    """Compute send-after dates from cadence config."""
    base = start or datetime.now(timezone.utc)
    max_seq = min(
        len(cadence.follow_up_days),
        cadence.max_follow_ups + 1,
    )
    return [base + timedelta(days=cadence.follow_up_days[i]) for i in range(max_seq)]
