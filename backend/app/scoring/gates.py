"""Gate evaluation: hard requirements, kept out of the weighted score.

A gate is `confirmed` by a manual tick or by any evidence row whose matched text
contains one of the gate's keywords. A manual `no` always wins. Everything else
is `unknown`.
"""

from __future__ import annotations

import re
from enum import StrEnum

from app.config import GateConfig
from app.scoring import SignalResult

# Manual gate decisions are stored as signals with this criterion and key=<gate name>.
GATE_CRITERION = "gate"


class GateStatus(StrEnum):
    CONFIRMED = "confirmed"
    UNKNOWN = "unknown"
    NO = "no"


def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    # Whole-word match so "est" doesn't hit "best" or "established".
    return re.compile(rf"(?<!\w){re.escape(keyword)}(?!\w)", re.IGNORECASE)


def evaluate_gate(name: str, gate: GateConfig, signals: list[SignalResult]) -> GateStatus:
    """Status of one gate. Signals are expected oldest first; the last manual tick wins."""
    manual = [s for s in signals if s.criterion == GATE_CRITERION and s.key == name]
    if manual:
        return GateStatus.CONFIRMED if manual[-1].value >= 0.5 else GateStatus.NO

    patterns = [_keyword_pattern(k) for k in gate.evidence_keywords]
    for s in signals:
        if s.criterion == GATE_CRITERION or not s.matched_text:
            continue
        if any(p.search(s.matched_text) for p in patterns):
            return GateStatus.CONFIRMED
    return GateStatus.UNKNOWN


def evaluate_gates(
    gates: dict[str, GateConfig], signals: list[SignalResult]
) -> dict[str, GateStatus]:
    return {name: evaluate_gate(name, gate, signals) for name, gate in gates.items()}


def gates_required_for(
    gates: dict[str, GateConfig], to_stage: str, stage_order: list[str]
) -> list[str]:
    """Gates that must be confirmed before entering `to_stage`.

    A gate with required_before=test_calls also applies to every later stage except lost.
    """
    if to_stage not in stage_order:
        return []
    target = stage_order.index(to_stage)
    return [
        name
        for name, gate in gates.items()
        if gate.required_before in stage_order and stage_order.index(gate.required_before) <= target
    ]
