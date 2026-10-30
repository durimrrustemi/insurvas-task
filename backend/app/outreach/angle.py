"""Generate a personalised outreach angle from partner signals."""

from __future__ import annotations

from app.prompts.angle_v2 import ANGLE_V2
from app.prompts.draft_v2 import PARTNER_KINDS
from app.scoring import SignalResult
from app.services.llm import AngleResponse, complete_json


def format_evidence(signals: list[SignalResult]) -> str:
    """Format signal list into readable evidence text for prompts."""
    if not signals:
        return "(no evidence available)"
    lines = []
    for s in signals:
        line = f"- [{s.criterion}] {s.key}: value={s.value:.2f}"
        if s.matched_text:
            line += f' — "{s.matched_text}"'
        if s.source_url:
            line += f" (source: {s.source_url})"
        lines.append(line)
    return "\n".join(lines)


async def generate_angle(
    partner_name: str,
    partner_domain: str,
    partner_country: str,
    signals: list[SignalResult],
    partner_type: str = "bpo",
) -> str:
    """Generate a one-sentence angle using LLM."""
    evidence = format_evidence(signals)
    variables = {
        "partner_name": partner_name,
        "partner_domain": partner_domain,
        "partner_country": partner_country,
        "partner_kind": PARTNER_KINDS[partner_type],
        "evidence": evidence,
    }
    result = await complete_json(
        prompt_name="ANGLE_V2",
        prompt=ANGLE_V2,
        variables=variables,
        schema=AngleResponse,
    )
    return result.angle
