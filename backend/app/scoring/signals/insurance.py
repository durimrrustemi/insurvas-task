"""Insurance experience signals: keywords, final expense, live transfers, case studies."""

from __future__ import annotations

import re

from app.config import AppConfig
from app.scoring import SignalResult

CRITERION = "insurance"

INSURANCE_KEYWORDS = [
    "insurance",
    "life insurance",
    "health insurance",
    "medicare",
    "medicaid",
    "underwriting",
    "insurance campaign",
    "insurance leads",
    "insurance sales",
    "insurance agent",
]

FINAL_EXPENSE_KEYWORDS = [
    "final expense",
    "funeral insurance",
    "burial insurance",
    "senior life",
    "final expense leads",
    "funeral cost",
]

LIVE_TRANSFER_KEYWORDS = [
    "live transfer",
    "warm transfer",
    "live call transfer",
    "transfer leads",
    "inbound transfer",
]

CARRIER_NAMES = [
    "aetna",
    "mutual of omaha",
    "globe life",
    "american general",
    "transamerica",
    "colonial penn",
    "gerber life",
    "cigna",
    "humana",
    "united healthcare",
    "anthem",
    "prudential",
    "metlife",
    "aflac",
]

CASE_STUDY_PATTERNS = [
    r"(?:insurance|insurer)\s+(?:case\s+study|testimonial|success\s+story)",
    r"(?:case\s+study|testimonial|client\s+story).*?insurance",
    r"insurance\s+(?:client|partner|customer)\s+(?:review|feedback)",
]

JOB_POSTING_PATTERNS = [
    r"(?:hiring|career|job|position|vacancy).*?insurance",
    r"insurance.*?(?:hiring|career|job|position|vacancy)",
    r"(?:insurance\s+)?(?:agent|representative|advisor)\s+(?:wanted|needed|position)",
]


def extract_insurance_signals(
    texts: dict[str, str],
    config: AppConfig,
) -> list[SignalResult]:
    signals: list[SignalResult] = []
    signal_config = config.signals.get(CRITERION, {})
    all_text = " ".join(texts.values()).lower()

    # 1. General insurance keywords
    kw_cfg = signal_config.get("insurance_keywords")
    if kw_cfg:
        matches = _count_keyword_matches(all_text, INSURANCE_KEYWORDS)
        if matches:
            value = min(1.0, len(matches) / 3)
            best_url, best_match = _find_best_match(texts, INSURANCE_KEYWORDS)
            signals.append(
                SignalResult(
                    criterion=CRITERION,
                    key="insurance_keywords",
                    value=value,
                    weight=kw_cfg.weight,
                    source_url=best_url,
                    matched_text=best_match,
                )
            )

    # 2. Final expense specific
    fe_cfg = signal_config.get("final_expense_specific")
    if fe_cfg:
        best_url, best_match = _find_best_match(texts, FINAL_EXPENSE_KEYWORDS)
        if best_match:
            signals.append(
                SignalResult(
                    criterion=CRITERION,
                    key="final_expense_specific",
                    value=1.0,
                    weight=fe_cfg.weight,
                    source_url=best_url,
                    matched_text=best_match,
                )
            )

    # 3. Live transfer experience
    lt_cfg = signal_config.get("live_transfer_experience")
    if lt_cfg:
        best_url, best_match = _find_best_match(texts, LIVE_TRANSFER_KEYWORDS)
        if best_match:
            signals.append(
                SignalResult(
                    criterion=CRITERION,
                    key="live_transfer_experience",
                    value=1.0,
                    weight=lt_cfg.weight,
                    source_url=best_url,
                    matched_text=best_match,
                )
            )

    # 4. Insurance case studies
    cs_cfg = signal_config.get("insurance_case_study")
    if cs_cfg:
        for url, text in texts.items():
            match = _find_regex(text, CASE_STUDY_PATTERNS)
            if match:
                signals.append(
                    SignalResult(
                        criterion=CRITERION,
                        key="insurance_case_study",
                        value=0.8,
                        weight=cs_cfg.weight,
                        source_url=url,
                        matched_text=match,
                    )
                )
                break

    # 5. Insurance job postings
    jp_cfg = signal_config.get("insurance_job_postings")
    if jp_cfg:
        for url, text in texts.items():
            match = _find_regex(text, JOB_POSTING_PATTERNS)
            if match:
                signals.append(
                    SignalResult(
                        criterion=CRITERION,
                        key="insurance_job_postings",
                        value=0.7,
                        weight=jp_cfg.weight,
                        source_url=url,
                        matched_text=match,
                    )
                )
                break

    # 6. Named carriers
    cn_cfg = signal_config.get("carrier_names")
    if cn_cfg:
        found_carriers = [c for c in CARRIER_NAMES if c in all_text]
        if found_carriers:
            value = min(1.0, len(found_carriers) / 2)
            best_url = _find_url_with_keyword(texts, found_carriers[0])
            signals.append(
                SignalResult(
                    criterion=CRITERION,
                    key="carrier_names",
                    value=value,
                    weight=cn_cfg.weight,
                    source_url=best_url,
                    matched_text=f"Carriers mentioned: {', '.join(found_carriers[:5])}",
                )
            )

    return signals


def _count_keyword_matches(text: str, keywords: list[str]) -> list[str]:
    return [kw for kw in keywords if kw in text]


def _find_best_match(texts: dict[str, str], keywords: list[str]) -> tuple[str, str]:
    for url, text in texts.items():
        text_lower = text.lower()
        for kw in keywords:
            idx = text_lower.find(kw)
            if idx >= 0:
                start = max(0, idx - 30)
                end = min(len(text), idx + len(kw) + 30)
                return url, text[start:end].strip()
    return "", ""


def _find_url_with_keyword(texts: dict[str, str], keyword: str) -> str:
    for url, text in texts.items():
        if keyword in text.lower():
            return url
    return ""


def _find_regex(text: str, patterns: list[str]) -> str:
    text_lower = text.lower()
    for pattern in patterns:
        m = re.search(pattern, text_lower)
        if m:
            start = max(0, m.start() - 30)
            end = min(len(text), m.end() + 30)
            return text[start:end].strip()
    return ""
