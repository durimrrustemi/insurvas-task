"""Pipeline rules: allowed stage transitions and readiness checks. Pure, no DB.

The frontend renders what these return; it never re-implements them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.config import GateConfig
from app.scoring import SignalResult
from app.scoring.gates import GateStatus, evaluate_gates, gates_required_for

# Forward order of the funnel. `lost` sits outside it: reachable from anywhere, never gated.
STAGE_ORDER = ["found", "contacted", "replied", "in_talks", "test_calls", "signed"]

ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    "found": ["contacted", "lost"],
    "contacted": ["replied", "lost"],
    "replied": ["in_talks", "lost"],
    "in_talks": ["test_calls", "lost"],
    "test_calls": ["signed", "lost"],
    "signed": ["lost"],
    "lost": ["found"],
}

# Terms that must be agreed before entering a stage (keys in partners.engagement_terms).
REQUIRED_TERMS: dict[str, list[str]] = {
    "test_calls": ["test_batch_size"],
    "signed": ["price_per_transfer", "daily_volume", "hours", "quality_threshold"],
}

TERM_LABELS = {
    "test_batch_size": "Test batch size agreed",
    "price_per_transfer": "Price per transfer agreed",
    "daily_volume": "Daily volume agreed",
    "hours": "Hours agreed",
    "quality_threshold": "Quality threshold agreed",
}

# Stages that need a named person on the other side.
NEEDS_CONTACT = {"in_talks", "test_calls", "signed"}


@dataclass(frozen=True)
class Check:
    key: str
    label: str
    ok: bool


@dataclass(frozen=True)
class Readiness:
    to: str
    checks: list[Check] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return all(c.ok for c in self.checks)

    @property
    def failed(self) -> list[Check]:
        return [c for c in self.checks if not c.ok]


def is_allowed(from_stage: str, to_stage: str) -> bool:
    return to_stage in ALLOWED_TRANSITIONS.get(from_stage, [])


def readiness(
    to_stage: str,
    *,
    gates: dict[str, GateConfig],
    signals: list[SignalResult],
    contact_names: list[str],
    terms: dict[str, Any] | None,
) -> Readiness:
    """Checks that must pass before a partner may enter `to_stage`."""
    if to_stage == "lost":
        return Readiness(to=to_stage)

    checks: list[Check] = []
    if to_stage in NEEDS_CONTACT:
        checks.append(
            Check("contact", "Has a named contact", any(n.strip() for n in contact_names))
        )

    statuses = evaluate_gates(gates, signals)
    for name in gates_required_for(gates, to_stage, STAGE_ORDER):
        checks.append(
            Check(
                f"gate:{name}",
                f"Gate confirmed: {gates[name].description}",
                statuses[name] == GateStatus.CONFIRMED,
            )
        )

    terms = terms or {}
    for key in REQUIRED_TERMS.get(to_stage, []):
        value = terms.get(key)
        checks.append(Check(f"terms:{key}", TERM_LABELS[key], value not in (None, "")))

    return Readiness(to=to_stage, checks=checks)
