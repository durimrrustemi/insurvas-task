"""English quality signals: country baseline, keyword claims, client evidence."""

from __future__ import annotations

import re

from app.config import AppConfig
from app.scoring import SignalResult

CRITERION = "english"

NATIVE_ENGLISH_PATTERNS = [
    r"native[\s-]english",
    r"neutral[\s-]accent",
    r"american[\s-]accent",
    r"british[\s-]accent",
    r"fluent[\s-]english",
    r"english[\s-]fluency",
    r"c[12][\s-]english",
    r"ielts",
]

US_UK_AU_CLIENT_PATTERNS = [
    r"us[\s-](?:based\s+)?clients?",
    r"uk[\s-](?:based\s+)?clients?",
    r"australian[\s-]clients?",
    r"american[\s-](?:companies|clients|customers)",
    r"north[\s-]american[\s-](?:clients|market)",
    r"served?\s+(?:us|uk|australian)\s+(?:companies|clients)",
    r"fortune[\s-]\d+",
    r"(?:us|uk|australia)\s+market",
]


def extract_english_signals(
    texts: dict[str, str],
    country_code: str,
    config: AppConfig,
) -> list[SignalResult]:
    signals: list[SignalResult] = []
    signal_config = config.signals.get(CRITERION, {})

    # 1. Country baseline
    country = config.get_country(country_code)
    baseline_cfg = signal_config.get("english_baseline")
    if country and baseline_cfg:
        signals.append(
            SignalResult(
                criterion=CRITERION,
                key="english_baseline",
                value=country.english_baseline,
                weight=baseline_cfg.weight,
                matched_text=f"Country baseline for {country.name}: {country.english_baseline}",
            )
        )

    # 2. Site language is English (check if page text is predominantly English)
    site_lang_cfg = signal_config.get("site_language_english")
    if site_lang_cfg and texts:
        for url, text in texts.items():
            if _is_english_text(text):
                signals.append(
                    SignalResult(
                        criterion=CRITERION,
                        key="site_language_english",
                        value=1.0,
                        weight=site_lang_cfg.weight,
                        source_url=url,
                        matched_text="Website content is in English",
                    )
                )
                break

    # 3. Native English claims
    native_cfg = signal_config.get("native_english_claim")
    if native_cfg:
        for url, text in texts.items():
            match = _find_pattern(text, NATIVE_ENGLISH_PATTERNS)
            if match:
                signals.append(
                    SignalResult(
                        criterion=CRITERION,
                        key="native_english_claim",
                        value=0.8,
                        weight=native_cfg.weight,
                        source_url=url,
                        matched_text=match,
                    )
                )
                break

    # 4. US/UK/AU client evidence
    client_cfg = signal_config.get("us_uk_au_clients")
    if client_cfg:
        for url, text in texts.items():
            match = _find_pattern(text, US_UK_AU_CLIENT_PATTERNS)
            if match:
                signals.append(
                    SignalResult(
                        criterion=CRITERION,
                        key="us_uk_au_clients",
                        value=0.9,
                        weight=client_cfg.weight,
                        source_url=url,
                        matched_text=match,
                    )
                )
                break

    return signals


def _is_english_text(text: str) -> bool:
    """Simple heuristic: check for common English words."""
    if not text or len(text) < 50:
        return False
    text_lower = text.lower()
    english_words = ["the", "and", "our", "with", "for", "that", "this", "are", "have", "from"]
    word_count = sum(1 for w in english_words if f" {w} " in text_lower)
    return word_count >= 4


def _find_pattern(text: str, patterns: list[str]) -> str:
    """Return the first matching snippet (with context) or empty string."""
    if not text:
        return ""
    text_lower = text.lower()
    for pattern in patterns:
        m = re.search(pattern, text_lower)
        if m:
            start = max(0, m.start() - 30)
            end = min(len(text), m.end() + 30)
            return text[start:end].strip()
    return ""
