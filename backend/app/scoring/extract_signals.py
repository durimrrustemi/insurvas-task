"""Orchestrate signal extraction from page texts. Pure function."""

from __future__ import annotations

from app.config import AppConfig
from app.scoring import SignalResult
from app.scoring.signals.compliance import extract_compliance_signals
from app.scoring.signals.english import extract_english_signals
from app.scoring.signals.insurance import extract_insurance_signals
from app.scoring.signals.size import extract_size_signals


def extract_all_signals(
    texts: dict[str, str],
    country_code: str,
    config: AppConfig,
) -> list[SignalResult]:
    """Run all signal extractors against page texts.

    Args:
        texts: mapping of URL -> extracted text content
        country_code: two-letter country code
        config: app configuration

    Returns:
        list of all detected signals
    """
    signals: list[SignalResult] = []
    signals.extend(extract_english_signals(texts, country_code, config))
    signals.extend(extract_insurance_signals(texts, config))
    signals.extend(extract_size_signals(texts, config))
    signals.extend(extract_compliance_signals(texts, config))
    return signals
