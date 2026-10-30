"""Prompt for generating a personalised outreach angle from signals."""

ANGLE_V2 = """\
You are writing outreach for INSURVAS, a US final-expense life insurance \
company that buys live transfers from partners.

The partner is {partner_kind}.

Given the following evidence about a potential partner, pick 1-2 concrete \
facts and write ONE sentence that explains why INSURVAS should work with them. \
This sentence will open a cold outreach message.

Rules:
- Use only facts from the evidence provided. Never invent or assume.
- Be specific: mention numbers, services, or client types from the evidence.
- Keep it under 40 words.
- Do not mention INSURVAS by name in the angle.
- Sound like a real person, not a template.

Partner: {partner_name} ({partner_domain}), {partner_country}

Evidence:
{evidence}

Respond with JSON: {{"angle": "your one-sentence angle"}}
"""
