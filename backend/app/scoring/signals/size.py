"""Size signals: seats/agents, locations, years, 24/7, careers depth."""

from __future__ import annotations

import re

from app.config import AppConfig
from app.scoring import SignalResult

CRITERION = "size"

SEAT_PATTERNS = [
    r"(\d[\d,]*)\+?\s*(?:seats?|agents?|employees?|staff|representatives?|associates?)",
    r"(?:over|more than|exceed)\s*(\d[\d,]*)\s*(?:seats?|agents?|employees?|staff)",
    r"(?:team of|workforce of|staff of)\s*(\d[\d,]*)",
]

LOCATION_PATTERNS = [
    r"(\d+)\s*(?:offices?|locations?|sites?|centers?|centres?)",
    r"(?:offices?\s+in|locations?\s+in|present\s+in)\s+\w+(?:\s*,\s*\w+)+",
    r"global\s+(?:presence|footprint|reach)",
    r"multiple\s+(?:offices?|locations?|sites?)",
]

YEARS_PATTERNS = [
    r"(?:since|founded\s+in|established\s+in|founded|established|operating\s+since)\s+(\d{4})",
    r"(\d+)\+?\s*years?\s+(?:of\s+)?(?:experience|in\s+business|operating)",
    r"over\s+(\d+)\s*years?",
]

TWENTY_FOUR_SEVEN_PATTERNS = [
    r"24\s*/?\s*7",
    r"24\s*hours",
    r"round[\s-]the[\s-]clock",
    r"always[\s-]on",
    r"24x7",
]

PRICING_URL_KEYWORDS = ["pricing", "rates", "plans"]

CAREERS_KEYWORDS = [
    "career",
    "job opening",
    "we are hiring",
    "join our team",
    "work with us",
    "open position",
    "vacancy",
    "apply now",
]


def extract_size_signals(
    texts: dict[str, str],
    config: AppConfig,
) -> list[SignalResult]:
    signals: list[SignalResult] = []
    signal_config = config.signals.get(CRITERION, {})

    # 1. Stated seats/agents
    seats_cfg = signal_config.get("stated_seats")
    if seats_cfg:
        for url, text in texts.items():
            seats = _extract_seat_count(text)
            if seats is not None:
                value = _seats_to_value(seats)
                signals.append(
                    SignalResult(
                        criterion=CRITERION,
                        key="stated_seats",
                        value=value,
                        weight=seats_cfg.weight,
                        source_url=url,
                        matched_text=f"~{seats} seats/agents mentioned",
                    )
                )
                break

    # 2. Multiple locations
    loc_cfg = signal_config.get("multiple_locations")
    if loc_cfg:
        for url, text in texts.items():
            match = _find_pattern(text, LOCATION_PATTERNS)
            if match:
                signals.append(
                    SignalResult(
                        criterion=CRITERION,
                        key="multiple_locations",
                        value=0.7,
                        weight=loc_cfg.weight,
                        source_url=url,
                        matched_text=match,
                    )
                )
                break

    # 3. Years in business
    years_cfg = signal_config.get("years_in_business")
    if years_cfg:
        for url, text in texts.items():
            years = _extract_years(text)
            if years is not None:
                value = min(1.0, years / 15)  # 15+ years = 1.0
                signals.append(
                    SignalResult(
                        criterion=CRITERION,
                        key="years_in_business",
                        value=value,
                        weight=years_cfg.weight,
                        source_url=url,
                        matched_text=f"~{years} years in business",
                    )
                )
                break

    # 4. 24/7 operations
    tfs_cfg = signal_config.get("twenty_four_seven")
    if tfs_cfg:
        for url, text in texts.items():
            match = _find_pattern(text, TWENTY_FOUR_SEVEN_PATTERNS)
            if match:
                signals.append(
                    SignalResult(
                        criterion=CRITERION,
                        key="twenty_four_seven",
                        value=0.9,
                        weight=tfs_cfg.weight,
                        source_url=url,
                        matched_text=match,
                    )
                )
                break

    # 5. Careers page depth
    careers_cfg = signal_config.get("careers_page_depth")
    if careers_cfg:
        careers_count = _count_careers_signals(texts)
        if careers_count > 0:
            value = min(1.0, careers_count / 3)
            url = _find_careers_url(texts)
            signals.append(
                SignalResult(
                    criterion=CRITERION,
                    key="careers_page_depth",
                    value=value,
                    weight=careers_cfg.weight,
                    source_url=url,
                    matched_text=f"{careers_count} careers-related signals found",
                )
            )

    # 6. Pricing page
    pricing_cfg = signal_config.get("has_pricing_page")
    if pricing_cfg:
        url = _pricing_url(texts)
        if url:
            signals.append(
                SignalResult(
                    criterion=CRITERION,
                    key="has_pricing_page",
                    value=1.0,
                    weight=pricing_cfg.weight,
                    source_url=url,
                    matched_text="Pricing page found",
                )
            )

    return signals


def _pricing_url(texts: dict[str, str]) -> str:
    for url in texts:
        if any(kw in url.lower() for kw in PRICING_URL_KEYWORDS):
            return url
    return ""


def _extract_seat_count(text: str) -> int | None:
    text_lower = text.lower()
    for pattern in SEAT_PATTERNS:
        m = re.search(pattern, text_lower)
        if m:
            num_str = m.group(1).replace(",", "")
            try:
                num = int(num_str)
                if 5 <= num <= 100000:  # reasonable range
                    return num
            except ValueError:
                continue
    return None


def _seats_to_value(seats: int) -> float:
    """Map seat count to 0-1 value. More seats = higher value for BPO."""
    if seats >= 500:
        return 1.0
    if seats >= 200:
        return 0.9
    if seats >= 100:
        return 0.8
    if seats >= 50:
        return 0.6
    if seats >= 20:
        return 0.4
    return 0.2


def _extract_years(text: str) -> int | None:
    text_lower = text.lower()
    for pattern in YEARS_PATTERNS:
        m = re.search(pattern, text_lower)
        if m:
            num_str = m.group(1)
            try:
                num = int(num_str)
                if num > 1900:  # "since 2005" -> years = 2026 - 2005
                    return 2026 - num
                if 1 <= num <= 50:
                    return num
            except ValueError:
                continue
    return None


def _find_pattern(text: str, patterns: list[str]) -> str:
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


def _count_careers_signals(texts: dict[str, str]) -> int:
    count = 0
    for text in texts.values():
        text_lower = text.lower()
        for kw in CAREERS_KEYWORDS:
            if kw in text_lower:
                count += 1
                break
    return count


def _find_careers_url(texts: dict[str, str]) -> str:
    for url, text in texts.items():
        text_lower = text.lower()
        if any(kw in text_lower for kw in CAREERS_KEYWORDS):
            return url
    return ""
