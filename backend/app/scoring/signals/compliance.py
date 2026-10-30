"""Compliance signals: TCPA, DNC, consent/recording, PCI/HIPAA/ISO, licensing."""

from __future__ import annotations

import re

from app.config import AppConfig
from app.scoring import SignalResult

CRITERION = "compliance"

TCPA_PATTERNS = [
    r"tcpa",
    r"telephone\s+consumer\s+protection",
]

DNC_PATTERNS = [
    r"\bdnc\b",
    r"do[\s-]not[\s-]call",
    r"national[\s-]do[\s-]not[\s-]call",
]

CONSENT_PATTERNS = [
    r"(?:call|consent)\s+recording",
    r"recorded?\s+(?:calls?|lines?)",
    r"consent[\s-]based",
    r"prior[\s-]express[\s-]consent",
    r"call\s+monitoring",
    r"quality\s+(?:assurance|monitoring)",
]

CERT_PATTERNS = [
    r"\bpci[\s-]?dss?\b",
    r"\bhipaa\b",
    r"\biso[\s-]?\d{4,5}",
    r"\bsoc[\s-]?[12]\b",
    r"\bgdpr\b",
]

LICENSED_PATTERNS = [
    r"licensed",
    r"regulatory\s+complian",
    r"state[\s-]licensed",
    r"licensed\s+(?:agents?|representatives?)",
    r"complian(?:ce|t)\s+(?:with|to)\s+(?:all|federal|state)",
]


def extract_compliance_signals(
    texts: dict[str, str],
    config: AppConfig,
) -> list[SignalResult]:
    signals: list[SignalResult] = []
    signal_config = config.signals.get(CRITERION, {})

    # 1. TCPA mention
    tcpa_cfg = signal_config.get("tcpa_mention")
    if tcpa_cfg:
        url, match = _find_first_match(texts, TCPA_PATTERNS)
        if match:
            signals.append(
                SignalResult(
                    criterion=CRITERION,
                    key="tcpa_mention",
                    value=1.0,
                    weight=tcpa_cfg.weight,
                    source_url=url,
                    matched_text=match,
                )
            )

    # 2. DNC compliance
    dnc_cfg = signal_config.get("dnc_compliance")
    if dnc_cfg:
        url, match = _find_first_match(texts, DNC_PATTERNS)
        if match:
            signals.append(
                SignalResult(
                    criterion=CRITERION,
                    key="dnc_compliance",
                    value=1.0,
                    weight=dnc_cfg.weight,
                    source_url=url,
                    matched_text=match,
                )
            )

    # 3. Consent/recording
    consent_cfg = signal_config.get("consent_recording")
    if consent_cfg:
        url, match = _find_first_match(texts, CONSENT_PATTERNS)
        if match:
            signals.append(
                SignalResult(
                    criterion=CRITERION,
                    key="consent_recording",
                    value=0.8,
                    weight=consent_cfg.weight,
                    source_url=url,
                    matched_text=match,
                )
            )

    # 4. PCI/HIPAA/ISO
    cert_cfg = signal_config.get("pci_hipaa_iso")
    if cert_cfg:
        url, match = _find_first_match(texts, CERT_PATTERNS)
        if match:
            signals.append(
                SignalResult(
                    criterion=CRITERION,
                    key="pci_hipaa_iso",
                    value=0.9,
                    weight=cert_cfg.weight,
                    source_url=url,
                    matched_text=match,
                )
            )

    # 5. Licensed mention
    lic_cfg = signal_config.get("licensed_mention")
    if lic_cfg:
        url, match = _find_first_match(texts, LICENSED_PATTERNS)
        if match:
            signals.append(
                SignalResult(
                    criterion=CRITERION,
                    key="licensed_mention",
                    value=0.8,
                    weight=lic_cfg.weight,
                    source_url=url,
                    matched_text=match,
                )
            )

    return signals


def _find_first_match(texts: dict[str, str], patterns: list[str]) -> tuple[str, str]:
    for url, text in texts.items():
        if not text:
            continue
        text_lower = text.lower()
        for pattern in patterns:
            m = re.search(pattern, text_lower)
            if m:
                start = max(0, m.start() - 30)
                end = min(len(text), m.end() + 30)
                return url, text[start:end].strip()
    return "", ""
