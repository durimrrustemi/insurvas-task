"""Tests for outreach module: cadence dates, length enforcement, angle formatting."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.config import CadenceConfig
from app.outreach.angle import format_evidence
from app.outreach.draft import (
    _enforce_limits,
    _enforce_subject,
    compute_send_dates,
)
from app.scoring import SignalResult


@pytest.fixture
def cadence() -> CadenceConfig:
    return CadenceConfig(
        follow_up_days=[0, 3, 7, 14],
        intents=[
            {"sequence": 0, "intent": "intro", "description": "Introduction"},
            {"sequence": 1, "intent": "value_add", "description": "Value add"},
            {"sequence": 2, "intent": "nudge", "description": "Nudge"},
            {"sequence": 3, "intent": "close_loop", "description": "Close loop"},
        ],
        channel_limits={
            "email": {"max_words": 120, "max_subject_chars": 60},
            "linkedin": {"max_chars": 300},
            "whatsapp": {"max_chars": 300},
        },
        reminder_days=3,
        stale_stage_days=7,
        max_follow_ups=2,
    )


# --- Cadence date computation ---


class TestComputeSendDates:
    def test_send_dates_with_max_follow_ups(self, cadence: CadenceConfig):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        dates = compute_send_dates(cadence, start=start)
        # max_follow_ups=2, so 3 messages total (intro + 2 follow-ups)
        assert len(dates) == 3
        assert dates[0] == start  # day 0
        assert dates[1] == datetime(2026, 1, 4, tzinfo=timezone.utc)  # day 3
        assert dates[2] == datetime(2026, 1, 8, tzinfo=timezone.utc)  # day 7

    def test_send_dates_respects_follow_up_days(self, cadence: CadenceConfig):
        cadence = CadenceConfig(
            follow_up_days=[0, 5, 10],
            intents=cadence.intents[:3],
            channel_limits=cadence.channel_limits,
            reminder_days=3,
            stale_stage_days=7,
            max_follow_ups=4,
        )
        start = datetime(2026, 6, 1, tzinfo=timezone.utc)
        dates = compute_send_dates(cadence, start=start)
        assert len(dates) == 3
        assert dates[1] == datetime(2026, 6, 6, tzinfo=timezone.utc)
        assert dates[2] == datetime(2026, 6, 11, tzinfo=timezone.utc)


# --- Length enforcement ---


class TestEnforceLimits:
    def test_email_truncation(self):
        body = " ".join(["word"] * 150)
        result = _enforce_limits(body, "email", {"max_words": 120})
        assert len(result.split()) == 120

    def test_email_no_truncation(self):
        body = " ".join(["word"] * 50)
        result = _enforce_limits(body, "email", {"max_words": 120})
        assert len(result.split()) == 50

    def test_whatsapp_truncation(self):
        body = "a" * 400
        result = _enforce_limits(body, "whatsapp", {"max_chars": 300})
        assert len(result) <= 300

    def test_linkedin_truncation(self):
        body = "word " * 80  # 400 chars
        result = _enforce_limits(body, "linkedin", {"max_chars": 300})
        assert len(result) <= 300

    def test_subject_truncation(self):
        subject = "A" * 80
        result = _enforce_subject(subject, {"max_subject_chars": 60})
        assert result is not None
        assert len(result) <= 60

    def test_subject_none(self):
        assert _enforce_subject(None, {"max_subject_chars": 60}) is None


# --- Evidence formatting ---


class TestFormatEvidence:
    def test_empty_signals(self):
        result = format_evidence([])
        assert "no evidence" in result.lower()

    def test_formats_signals(self):
        signals = [
            SignalResult(
                criterion="insurance",
                key="final_expense_specific",
                value=1.0,
                weight=4.0,
                source_url="https://bpo.test/services",
                matched_text="final expense leads",
            ),
            SignalResult(
                criterion="english",
                key="english_baseline",
                value=0.75,
                weight=1.0,
            ),
        ]
        result = format_evidence(signals)
        assert "insurance" in result
        assert "final_expense_specific" in result
        assert "final expense leads" in result
        assert "bpo.test" in result
        assert "english_baseline" in result

    def test_signal_without_url(self):
        signals = [
            SignalResult(
                criterion="english",
                key="baseline",
                value=0.75,
                weight=1.0,
            ),
        ]
        result = format_evidence(signals)
        assert "source:" not in result
