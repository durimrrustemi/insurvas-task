"""LLM service: the only place the Anthropic SDK is imported.

Exposes complete_json() which returns parsed Pydantic models.
MOCK_LLM=1 (default) returns deterministic canned responses.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from pydantic import BaseModel

from app.errors import ExternalServiceError
from app.settings import settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
TIMEOUT = 30
BACKOFF_SECONDS = 1.0


class AngleResponse(BaseModel):
    angle: str


class DraftResponse(BaseModel):
    subject: str | None = None
    body: str


# Mock responses keyed by prompt_name
_MOCK_RESPONSES: dict[str, dict[str, Any]] = {
    "ANGLE_V1": {
        "angle": (
            "Your 200+ agent team with live transfer experience"
            " and TCPA compliance makes you a strong fit for"
            " our US final-expense campaigns."
        ),
    },
    "DRAFT_V1_email_0": {
        "subject": "Partnership opportunity — live transfer test batch",
        "body": (
            "Hi there,\n\n"
            "I came across your company and was impressed by your"
            " insurance campaign experience and compliance posture.\n\n"
            "We're looking for call center partners who can generate"
            " live transfers for final-expense life insurance to"
            " US seniors. We buy transfers at competitive rates"
            " and start with a small test batch.\n\n"
            "A few quick questions:\n"
            "- Do you operate during US business hours?\n"
            "- Have you run insurance campaigns before?\n"
            "- What's your current seat count?\n"
            "- How do you handle lead sourcing and consent?\n\n"
            "Would love to explore this. Happy to jump on a call"
            " whenever works for you.\n\n"
            "Best regards"
        ),
    },
    "DRAFT_V1_email_1": {
        "subject": "Quick follow-up — live transfer partnership",
        "body": (
            "Hi,\n\n"
            "Just following up on my previous note. The final-expense"
            " market is growing — US seniors are an underserved"
            " segment and quality live transfers are in high demand.\n\n"
            "We'd be happy to share more about our rates and"
            " what a test batch looks like.\n\n"
            "Worth a quick chat?"
        ),
    },
    "DRAFT_V1_email_2": {
        "subject": "Still interested?",
        "body": (
            "Hi,\n\n"
            "Just checking in — I sent a couple of notes about a"
            " live transfer partnership for final-expense insurance.\n\n"
            "If the timing isn't right, no worries at all. Just let"
            " me know and I'll follow up later.\n\n"
            "Thanks"
        ),
    },
    "DRAFT_V1_email_3": {
        "subject": "Last note — happy to reconnect anytime",
        "body": (
            "Hi,\n\n"
            "I'll keep this short — I've reached out a few times"
            " about buying live transfers for US final-expense"
            " insurance.\n\n"
            "If it's not a fit right now, completely understand."
            " Feel free to reach out anytime if things change.\n\n"
            "All the best"
        ),
    },
    "DRAFT_V1_linkedin_0": {
        "subject": None,
        "body": (
            "Hi — I noticed your team's insurance campaign"
            " experience and wanted to reach out. We're buying"
            " live transfers for US final-expense insurance and"
            " looking for quality call center partners. Would you"
            " be open to a quick conversation about a test batch?"
        ),
    },
    "DRAFT_V1_linkedin_1": {
        "subject": None,
        "body": (
            "Hi again — just following up on my earlier message"
            " about live transfer partnerships. Happy to share"
            " more details if you're interested."
        ),
    },
    "DRAFT_V1_linkedin_2": {
        "subject": None,
        "body": (
            "Quick follow-up — still interested in exploring a partnership? No pressure either way."
        ),
    },
    "DRAFT_V1_linkedin_3": {
        "subject": None,
        "body": (
            "Last note — feel free to connect anytime if a live"
            " transfer partnership makes sense down the road."
        ),
    },
    "DRAFT_V1_whatsapp_0": {
        "subject": None,
        "body": (
            "Hi! I saw your BPO handles insurance campaigns."
            " We buy live transfers for US final-expense insurance"
            " — interested in a test batch? Happy to share details."
        ),
    },
    "DRAFT_V1_whatsapp_1": {
        "subject": None,
        "body": (
            "Hi — following up on my earlier message about buying"
            " live transfers. Would love to chat if you're open to it."
        ),
    },
    "DRAFT_V1_whatsapp_2": {
        "subject": None,
        "body": (
            "Quick check-in — still interested in a live transfer partnership? No worries if not."
        ),
    },
    "DRAFT_V1_whatsapp_3": {
        "subject": None,
        "body": (
            "Last note — happy to reconnect whenever a live transfer"
            " partnership makes sense. All the best!"
        ),
    },
}


async def complete_json[M: BaseModel](
    prompt_name: str,
    prompt: str,
    variables: dict[str, Any],
    schema: type[M],
) -> M:
    """Call LLM and return parsed response.

    With MOCK_LLM=1, returns canned responses from _MOCK_RESPONSES.
    """
    if settings.mock_llm:
        return _mock_response(prompt_name, schema)

    return await _real_llm_call(prompt_name, prompt, variables, schema)


def _mock_response[M: BaseModel](prompt_name: str, schema: type[M]) -> M:
    data = _MOCK_RESPONSES.get(prompt_name)
    if data is None:
        logger.warning("No mock for prompt %s, using empty", prompt_name)
        data = _MOCK_RESPONSES.get("ANGLE_V1", {"angle": "mock angle"})
    return schema.model_validate(data)


async def _real_llm_call[M: BaseModel](
    prompt_name: str,
    prompt: str,
    variables: dict[str, Any],
    schema: type[M],
) -> M:
    """Real Anthropic API call with retries."""
    import anthropic

    filled = prompt.format(**variables)
    client = anthropic.AsyncAnthropic(
        api_key=settings.anthropic_api_key,
        timeout=TIMEOUT,
    )

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        start = time.time()
        try:
            response = await client.messages.create(
                model=settings.llm_model,
                max_tokens=1024,
                messages=[{"role": "user", "content": filled}],
            )
            latency = time.time() - start
            text = "".join(b.text for b in response.content if b.type == "text")

            # Parse JSON from response
            parsed = json.loads(text)
            result = schema.model_validate(parsed)

            logger.info(
                "LLM %s: %dms, %d input + %d output tokens",
                prompt_name,
                int(latency * 1000),
                response.usage.input_tokens,
                response.usage.output_tokens,
            )
            return result

        except json.JSONDecodeError as e:
            last_error = e
            logger.warning(
                "LLM %s attempt %d: JSON parse failed: %s",
                prompt_name,
                attempt + 1,
                e,
            )
        except Exception as e:
            last_error = e
            logger.warning(
                "LLM %s attempt %d failed: %s",
                prompt_name,
                attempt + 1,
                e,
            )
        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(BACKOFF_SECONDS * 2**attempt)

    raise ExternalServiceError(
        f"LLM call {prompt_name} failed after {MAX_RETRIES} attempts: {last_error}"
    )
