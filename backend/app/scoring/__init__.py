"""Scoring module: pure functions, no DB or HTTP."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SignalResult:
    """A single detected signal from page text."""

    criterion: str
    key: str
    value: float  # 0–1
    weight: float
    source_url: str = ""
    matched_text: str = ""


@dataclass
class CriterionScore:
    """Computed score for one criterion."""

    criterion: str
    score: float  # weighted mean of signal values
    coverage: float  # fraction of possible signal weight found
    signals: list[SignalResult]


@dataclass
class ScoreResult:
    """Full scoring result for a partner."""

    total: float | None  # None if no criteria have coverage
    confidence: float  # weighted mean of coverage across criteria
    criteria: dict[str, CriterionScore]
    signals: list[SignalResult]
