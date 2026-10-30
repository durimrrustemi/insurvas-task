"""Tests for scoring module: formula, signal extraction, edge cases."""

from __future__ import annotations

import pytest

from app.config import AppConfig, CountryConfig, SignalConfig
from app.scoring import SignalResult
from app.scoring.extract_signals import extract_all_signals
from app.scoring.score import compute_scores
from app.scoring.signals.compliance import extract_compliance_signals
from app.scoring.signals.english import extract_english_signals
from app.scoring.signals.insurance import extract_insurance_signals
from app.scoring.signals.size import (
    _extract_seat_count,
    _extract_years,
    _seats_to_value,
    extract_size_signals,
)


@pytest.fixture
def config() -> AppConfig:
    """Minimal config for testing scoring."""
    return AppConfig(
        countries=[
            CountryConfig(
                code="PH",
                name="Philippines",
                english_baseline=0.75,
                timezone="Asia/Manila",
                preferred_channels=["email"],
                cities=["Manila"],
            ),
        ],
        criterion_weights={
            "insurance": 0.35,
            "english": 0.30,
            "size": 0.20,
            "compliance": 0.15,
        },
        signals={
            "english": {
                "english_baseline": SignalConfig(weight=1.0, description=""),
                "site_language_english": SignalConfig(weight=2.0, description=""),
                "llm_english_grade": SignalConfig(weight=3.0, description=""),
                "native_english_claim": SignalConfig(weight=1.5, description=""),
                "us_uk_au_clients": SignalConfig(weight=2.0, description=""),
            },
            "insurance": {
                "insurance_keywords": SignalConfig(weight=3.0, description=""),
                "final_expense_specific": SignalConfig(weight=4.0, description=""),
                "live_transfer_experience": SignalConfig(weight=4.0, description=""),
                "insurance_case_study": SignalConfig(weight=3.0, description=""),
                "insurance_job_postings": SignalConfig(weight=1.5, description=""),
                "carrier_names": SignalConfig(weight=2.0, description=""),
            },
            "size": {
                "stated_seats": SignalConfig(weight=3.0, description=""),
                "multiple_locations": SignalConfig(weight=1.5, description=""),
                "years_in_business": SignalConfig(weight=1.0, description=""),
                "twenty_four_seven": SignalConfig(weight=1.5, description=""),
                "careers_page_depth": SignalConfig(weight=1.0, description=""),
            },
            "compliance": {
                "tcpa_mention": SignalConfig(weight=4.0, description=""),
                "dnc_compliance": SignalConfig(weight=2.0, description=""),
                "consent_recording": SignalConfig(weight=2.0, description=""),
                "pci_hipaa_iso": SignalConfig(weight=1.5, description=""),
                "licensed_mention": SignalConfig(weight=2.0, description=""),
            },
        },
    )


# --- Score formula tests ---


class TestComputeScores:
    def test_no_signals(self, config: AppConfig):
        result = compute_scores([], config)
        assert result.total is None
        assert result.confidence == 0.0
        assert all(cs.coverage == 0.0 for cs in result.criteria.values())

    def test_country_baseline_alone_has_no_total(self, config: AppConfig):
        # The baseline is a prior about the country, not evidence about the company.
        signals = [
            SignalResult(criterion="english", key="english_baseline", value=0.75, weight=1.0),
        ]
        result = compute_scores(signals, config)
        assert result.total is None
        assert result.criteria["english"].score == pytest.approx(0.75, abs=0.01)
        assert result.criteria["english"].coverage > 0
        assert result.criteria["insurance"].coverage == 0.0

    def test_single_company_signal(self, config: AppConfig):
        signals = [
            SignalResult(criterion="english", key="english_baseline", value=0.75, weight=1.0),
            SignalResult(criterion="english", key="native_english_claim", value=1.0, weight=1.5),
        ]
        result = compute_scores(signals, config)
        assert result.total == pytest.approx((0.75 * 1.0 + 1.0 * 1.5) / 2.5, abs=0.01)

    def test_multiple_criteria(self, config: AppConfig):
        signals = [
            SignalResult(
                criterion="english",
                key="english_baseline",
                value=0.8,
                weight=1.0,
            ),
            SignalResult(
                criterion="english",
                key="site_language_english",
                value=1.0,
                weight=2.0,
            ),
            SignalResult(
                criterion="insurance",
                key="insurance_keywords",
                value=0.5,
                weight=3.0,
            ),
        ]
        result = compute_scores(signals, config)
        assert result.total is not None

        # English: (1.0*0.8 + 2.0*1.0) / (1.0+2.0) = 2.8/3.0
        eng = result.criteria["english"].score
        assert eng == pytest.approx(0.9333, abs=0.01)

        # Insurance: (3.0*0.5) / 3.0 = 0.5
        ins = result.criteria["insurance"].score
        assert ins == pytest.approx(0.5, abs=0.01)

        # Total: (0.30*eng + 0.35*ins) / (0.30+0.35)
        expected = (0.30 * eng + 0.35 * ins) / (0.30 + 0.35)
        assert result.total == pytest.approx(expected, abs=0.01)

    def test_all_criteria_full(self, config: AppConfig):
        signals = [
            SignalResult(
                criterion="english",
                key="english_baseline",
                value=1.0,
                weight=1.0,
            ),
            SignalResult(
                criterion="insurance",
                key="insurance_keywords",
                value=1.0,
                weight=3.0,
            ),
            SignalResult(
                criterion="size",
                key="stated_seats",
                value=1.0,
                weight=3.0,
            ),
            SignalResult(
                criterion="compliance",
                key="tcpa_mention",
                value=1.0,
                weight=4.0,
            ),
        ]
        result = compute_scores(signals, config)
        assert result.total == pytest.approx(1.0, abs=0.01)
        assert result.confidence > 0

    def test_coverage_calculation(self, config: AppConfig):
        # English total possible weight = 1+2+3+1.5+2 = 9.5
        signals = [
            SignalResult(
                criterion="english",
                key="english_baseline",
                value=0.75,
                weight=1.0,
            ),
        ]
        result = compute_scores(signals, config)
        expected_cov = 1.0 / 9.5
        assert result.criteria["english"].coverage == pytest.approx(expected_cov, abs=0.01)

    def test_confidence_is_weighted_mean_of_coverage(self, config: AppConfig):
        signals = [
            SignalResult(
                criterion="english",
                key="english_baseline",
                value=0.75,
                weight=1.0,
            ),
            SignalResult(
                criterion="insurance",
                key="insurance_keywords",
                value=0.5,
                weight=3.0,
            ),
        ]
        result = compute_scores(signals, config)

        eng_cov = result.criteria["english"].coverage
        ins_cov = result.criteria["insurance"].coverage
        total_w = 0.30 + 0.35 + 0.20 + 0.15
        expected = (0.30 * eng_cov + 0.35 * ins_cov) / total_w
        assert result.confidence == pytest.approx(expected, abs=0.001)


# --- English signal tests ---


class TestEnglishSignals:
    def test_country_baseline(self, config: AppConfig):
        signals = extract_english_signals({}, "PH", config)
        baselines = [s for s in signals if s.key == "english_baseline"]
        assert len(baselines) == 1
        assert baselines[0].value == 0.75

    def test_site_english(self, config: AppConfig):
        texts = {
            "https://example.com": (
                "We are the leading BPO company and our services"
                " have been helping clients from around the world"
            ),
        }
        signals = extract_english_signals(texts, "PH", config)
        site_eng = [s for s in signals if s.key == "site_language_english"]
        assert len(site_eng) == 1
        assert site_eng[0].value == 1.0

    def test_native_english_claim(self, config: AppConfig):
        texts = {
            "https://example.com": (
                "Our agents have neutral accent training and fluent English skills"
            ),
        }
        signals = extract_english_signals(texts, "PH", config)
        native = [s for s in signals if s.key == "native_english_claim"]
        assert len(native) == 1

    def test_us_clients(self, config: AppConfig):
        texts = {
            "https://example.com": ("We serve Fortune 500 US-based clients with premium support"),
        }
        signals = extract_english_signals(texts, "PH", config)
        clients = [s for s in signals if s.key == "us_uk_au_clients"]
        assert len(clients) == 1

    def test_no_text_still_gets_baseline(self, config: AppConfig):
        signals = extract_english_signals({}, "PH", config)
        assert len(signals) == 1
        assert signals[0].key == "english_baseline"


# --- Insurance signal tests ---


class TestInsuranceSignals:
    def test_insurance_keywords(self, config: AppConfig):
        texts = {
            "https://bpo.test": ("We handle life insurance and medicare campaigns for our clients"),
        }
        signals = extract_insurance_signals(texts, config)
        kw = [s for s in signals if s.key == "insurance_keywords"]
        assert len(kw) == 1
        assert kw[0].value > 0

    def test_final_expense(self, config: AppConfig):
        texts = {
            "https://bpo.test": (
                "Specializing in final expense leads and burial insurance campaigns"
            ),
        }
        signals = extract_insurance_signals(texts, config)
        fe = [s for s in signals if s.key == "final_expense_specific"]
        assert len(fe) == 1
        assert fe[0].value == 1.0

    def test_live_transfers(self, config: AppConfig):
        texts = {
            "https://bpo.test": (
                "We generate high quality live transfer leads for insurance agents"
            ),
        }
        signals = extract_insurance_signals(texts, config)
        lt = [s for s in signals if s.key == "live_transfer_experience"]
        assert len(lt) == 1

    def test_carrier_names(self, config: AppConfig):
        texts = {
            "https://bpo.test": ("We work with Aetna and Mutual of Omaha for insurance campaigns"),
        }
        signals = extract_insurance_signals(texts, config)
        cn = [s for s in signals if s.key == "carrier_names"]
        assert len(cn) == 1
        assert "aetna" in cn[0].matched_text.lower()

    def test_no_insurance_text(self, config: AppConfig):
        texts = {
            "https://bpo.test": (
                "We are a general technology consulting firm specializing in software development"
            ),
        }
        signals = extract_insurance_signals(texts, config)
        assert len(signals) == 0


# --- Size signal tests ---


class TestSizeSignals:
    def test_seat_extraction(self):
        assert _extract_seat_count("We have 500 agents working") == 500
        assert _extract_seat_count("Team of 200 employees") == 200
        assert _extract_seat_count("Over 1,000 seats in Manila") == 1000
        assert _extract_seat_count("No numbers here") is None

    def test_seats_to_value(self):
        assert _seats_to_value(500) == 1.0
        assert _seats_to_value(200) == 0.9
        assert _seats_to_value(100) == 0.8
        assert _seats_to_value(50) == 0.6
        assert _seats_to_value(20) == 0.4
        assert _seats_to_value(10) == 0.2

    def test_years_extraction(self):
        assert _extract_years("Founded in 2010 in Manila") == 16
        assert _extract_years("Over 15 years of experience") == 15
        assert _extract_years("No year info here") is None

    def test_size_signals_full(self, config: AppConfig):
        texts = {
            "https://bpo.test": (
                "We have 300 agents and 3 offices in Manila,"
                " Cebu, and Davao. Operating 24/7 since 2005."
            ),
            "https://bpo.test/careers": (
                "Join our team! We are hiring customer service"
                " representatives. Apply now for open positions."
            ),
        }
        signals = extract_size_signals(texts, config)
        keys = {s.key for s in signals}
        assert "stated_seats" in keys
        assert "twenty_four_seven" in keys
        assert "years_in_business" in keys


def test_pricing_page_signal():
    from app.config import load_config

    config = load_config()
    found = extract_size_signals({"https://bpo.test/pricing": "Our rates"}, config)
    missing = extract_size_signals({"https://bpo.test/about": "About us"}, config)
    assert [s.key for s in found] == ["has_pricing_page"]
    assert found[0].source_url == "https://bpo.test/pricing"
    assert missing == []


# --- Compliance signal tests ---


class TestComplianceSignals:
    def test_tcpa(self, config: AppConfig):
        texts = {
            "https://bpo.test": (
                "All our campaigns are TCPA compliant with proper consent management"
            ),
        }
        signals = extract_compliance_signals(texts, config)
        tcpa = [s for s in signals if s.key == "tcpa_mention"]
        assert len(tcpa) == 1

    def test_multiple_compliance(self, config: AppConfig):
        texts = {
            "https://bpo.test": (
                "We maintain TCPA and DNC compliance."
                " We offer call recording and quality assurance."
                " PCI-DSS certified. State licensed agents."
            ),
        }
        signals = extract_compliance_signals(texts, config)
        keys = {s.key for s in signals}
        assert "tcpa_mention" in keys
        assert "dnc_compliance" in keys
        assert "consent_recording" in keys
        assert "pci_hipaa_iso" in keys
        assert "licensed_mention" in keys

    def test_no_compliance(self, config: AppConfig):
        texts = {
            "https://bpo.test": ("We are a general BPO handling customer support calls"),
        }
        signals = extract_compliance_signals(texts, config)
        assert len(signals) == 0


# --- Integration: extract_all_signals ---


class TestExtractAllSignals:
    def test_full_extraction(self, config: AppConfig):
        texts = {
            "https://bpo.test": (
                "We are a leading BPO in Manila with 200 agents. "
                "Our team specializes in life insurance campaigns"
                " and live transfer leads. "
                "We maintain TCPA compliance and all calls are"
                " recorded. "
                "Our agents have neutral accent training and"
                " serve US-based clients."
            ),
        }
        signals = extract_all_signals(texts, "PH", config)
        criteria = {s.criterion for s in signals}
        assert "english" in criteria
        assert "insurance" in criteria
        assert "compliance" in criteria

    def test_empty_texts(self, config: AppConfig):
        signals = extract_all_signals({}, "PH", config)
        # Should still get English baseline
        assert len(signals) == 1
        assert signals[0].key == "english_baseline"
