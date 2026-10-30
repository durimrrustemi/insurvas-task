"""Prompt for drafting outreach messages per channel and sequence."""

DRAFT_V2 = """\
You are writing a {intent} outreach message for INSURVAS, a US final-expense \
life insurance company, to a potential partner: {partner_kind}.

Channel: {channel}
Sequence: {sequence} (0=first contact, 1+=follow-up)
Intent: {intent_description}

Partner: {partner_name} ({partner_domain}), {partner_country}
Angle: {angle}

Evidence:
{evidence}

Rules:
- Ground every claim in the evidence provided. Never fabricate facts.
- The first message (sequence 0) should ask these qualifying questions: \
{qualifying_questions}.
- Follow-ups should be shorter and reference the prior message.
- Sound like a knowledgeable person, not a sales template.
- INSURVAS buys live transfers for final-expense insurance to US seniors 60+.
- The pitch: "we buy your live transfers; start with a test batch."
- Do NOT promise anything not in evidence.

Length limits (HARD — you will be truncated if exceeded):
- Email: max {max_words} words body + subject line max {max_subject_chars} chars
- LinkedIn: max {max_chars} chars total
- WhatsApp: max {max_chars} chars total

Respond with JSON:
{{"subject": "subject line or null if not email", "body": "message body"}}
"""

# Who the partner is and what we need to learn first, per partner type.
PARTNER_KINDS = {
    "bpo": "a BPO call center that could run final-expense campaigns with its own leads",
    "vendor": "a lead vendor that sells live transfers and data leads",
}

QUALIFYING_QUESTIONS = {
    "bpo": "US hours, insurance lines done before, seat count, own lead sourcing, "
    "consent (TCPA) process",
    "vendor": "lead sources and how consent (TCPA) is captured, daily transfer volume, "
    "price per transfer, final-expense experience, return policy for bad transfers",
}
