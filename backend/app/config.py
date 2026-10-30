from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class CountryConfig:
    code: str
    name: str
    english_baseline: float
    timezone: str
    preferred_channels: list[str]
    cities: list[str]


@dataclass(frozen=True)
class SignalConfig:
    weight: float
    description: str


@dataclass(frozen=True)
class GateConfig:
    description: str
    evidence_keywords: list[str]
    required_before: str


@dataclass(frozen=True)
class CadenceConfig:
    follow_up_days: list[int]
    intents: list[dict[str, Any]]
    channel_limits: dict[str, dict[str, Any]]
    reminder_days: int
    stale_stage_days: int
    max_follow_ups: int


@dataclass(frozen=True)
class AppConfig:
    countries: list[CountryConfig] = field(default_factory=list)
    criterion_weights: dict[str, float] = field(default_factory=dict)
    signals: dict[str, dict[str, SignalConfig]] = field(default_factory=dict)
    gates: dict[str, GateConfig] = field(default_factory=dict)
    cadence: CadenceConfig | None = None
    query_templates: list[str] = field(default_factory=list)
    vendor_query_templates: list[str] = field(default_factory=list)
    max_queries_per_country: int = 25
    exclude_domains: list[str] = field(default_factory=list)
    exclude_title_patterns: list[str] = field(default_factory=list)

    def get_country(self, code: str) -> CountryConfig | None:
        for c in self.countries:
            if c.code == code:
                return c
        return None


def _config_dir() -> Path:
    explicit = os.environ.get("CONFIG_DIR")
    if explicit:
        return Path(explicit)
    # In Docker: /app/config (mounted). Locally: ../config relative to backend/
    candidates = [Path("config"), Path(__file__).resolve().parent.parent.parent / "config"]
    for p in candidates:
        if (p / "countries.yaml").is_file():
            return p
    return Path("config")


def load_config() -> AppConfig:
    config_dir = _config_dir()

    with open(config_dir / "countries.yaml") as f:
        countries_data = yaml.safe_load(f)
    countries = [CountryConfig(**c) for c in countries_data["countries"]]

    with open(config_dir / "scoring.yaml") as f:
        scoring_data = yaml.safe_load(f)
    criterion_weights = scoring_data["criterion_weights"]
    signals = {}
    for criterion, sigs in scoring_data["signals"].items():
        signals[criterion] = {k: SignalConfig(**v) for k, v in sigs.items()}

    with open(config_dir / "gates.yaml") as f:
        gates_data = yaml.safe_load(f)
    gates = {k: GateConfig(**v) for k, v in gates_data["gates"].items()}

    with open(config_dir / "cadence.yaml") as f:
        cadence_data = yaml.safe_load(f)
    cadence = CadenceConfig(
        follow_up_days=cadence_data["follow_up_days"],
        intents=cadence_data["intents"],
        channel_limits=cadence_data["channel_limits"],
        reminder_days=cadence_data["reminder_days"],
        stale_stage_days=cadence_data["stale_stage_days"],
        max_follow_ups=cadence_data["max_follow_ups"],
    )

    with open(config_dir / "queries.yaml") as f:
        queries_data = yaml.safe_load(f)

    return AppConfig(
        countries=countries,
        criterion_weights=criterion_weights,
        signals=signals,
        gates=gates,
        cadence=cadence,
        query_templates=queries_data["templates"],
        vendor_query_templates=queries_data.get("vendor_templates", []),
        max_queries_per_country=queries_data.get("max_queries_per_country", 25),
        exclude_domains=queries_data.get("exclude_domains", []),
        exclude_title_patterns=queries_data.get("exclude_title_patterns", []),
    )


app_config = load_config()
