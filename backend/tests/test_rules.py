"""Tests for pipeline rules: transitions, gates, readiness. Pure, no DB."""

from __future__ import annotations

import pytest

from app import rules
from app.config import GateConfig
from app.scoring import SignalResult
from app.scoring.gates import GATE_CRITERION, GateStatus, evaluate_gate, gates_required_for

GATES = {
    "us_hours": GateConfig(
        description="US hours",
        evidence_keywords=["us hours", "est", "24/7"],
        required_before="test_calls",
    ),
    "compliance": GateConfig(
        description="Compliance",
        evidence_keywords=["tcpa", "compliance"],
        required_before="test_calls",
    ),
}

ALL_TERMS = {
    "test_batch_size": 50,
    "price_per_transfer": 18,
    "daily_volume": 40,
    "hours": "9-17 EST",
    "quality_threshold": "60% contact rate",
}


def evidence(text: str, criterion: str = "compliance") -> SignalResult:
    return SignalResult(criterion=criterion, key="k", value=1.0, weight=1.0, matched_text=text)


def manual(gate: str, ok: bool) -> SignalResult:
    return SignalResult(criterion=GATE_CRITERION, key=gate, value=1.0 if ok else 0.0, weight=0.0)


GOOD_SIGNALS = [evidence("We are TCPA compliant"), evidence("Agents work US hours", "size")]


class TestTransitions:
    @pytest.mark.parametrize(
        ("frm", "to", "allowed"),
        [
            ("found", "contacted", True),
            ("found", "lost", True),
            ("found", "replied", False),
            ("found", "signed", False),
            ("contacted", "replied", True),
            ("replied", "in_talks", True),
            ("in_talks", "test_calls", True),
            ("test_calls", "contract_review", True),
            ("contract_review", "signed", True),
            ("test_calls", "signed", False),
            ("signed", "lost", True),
            ("signed", "found", False),
            ("lost", "found", True),
            ("lost", "contacted", False),
            ("test_calls", "in_talks", False),
        ],
    )
    def test_allowed(self, frm: str, to: str, allowed: bool) -> None:
        assert rules.is_allowed(frm, to) is allowed

    def test_rules_cover_every_stage_enum_value(self) -> None:
        # Guards the "add a stage" change: the enum and rules.py must move together.
        from app.models.partner import Stage

        assert set(rules.STAGE_ORDER) | {"lost"} == {s.value for s in Stage}
        assert set(rules.ALLOWED_TRANSITIONS) == {s.value for s in Stage}

    def test_every_stage_can_be_lost_except_lost(self) -> None:
        for stage in rules.STAGE_ORDER:
            assert rules.is_allowed(stage, "lost")


class TestGateEvaluation:
    @pytest.mark.parametrize(
        ("signals", "expected"),
        [
            ([], GateStatus.UNKNOWN),
            ([evidence("Full TCPA compliance")], GateStatus.CONFIRMED),
            ([evidence("We value our clients")], GateStatus.UNKNOWN),
            ([manual("compliance", True)], GateStatus.CONFIRMED),
            ([manual("compliance", False)], GateStatus.NO),
            # Contradictory: site claims compliance, human checked and said no. Human wins.
            ([evidence("TCPA compliant"), manual("compliance", False)], GateStatus.NO),
            # Last manual tick wins.
            ([manual("compliance", False), manual("compliance", True)], GateStatus.CONFIRMED),
            # A tick on a different gate doesn't count.
            ([manual("us_hours", True)], GateStatus.UNKNOWN),
        ],
    )
    def test_compliance_gate(self, signals: list[SignalResult], expected: GateStatus) -> None:
        assert evaluate_gate("compliance", GATES["compliance"], signals) is expected

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("Open 9am-5pm EST", GateStatus.CONFIRMED),
            ("Support 24/7", GateStatus.CONFIRMED),
            ("Established in 2009", GateStatus.UNKNOWN),
            ("The best team", GateStatus.UNKNOWN),
        ],
    )
    def test_keywords_match_whole_words(self, text: str, expected: GateStatus) -> None:
        assert evaluate_gate("us_hours", GATES["us_hours"], [evidence(text, "size")]) is expected

    @pytest.mark.parametrize(
        ("to", "expected"),
        [
            ("contacted", []),
            ("in_talks", []),
            ("test_calls", ["us_hours", "compliance"]),
            ("signed", ["us_hours", "compliance"]),
            ("lost", []),
        ],
    )
    def test_required_for(self, to: str, expected: list[str]) -> None:
        assert gates_required_for(GATES, to, rules.STAGE_ORDER) == expected


class TestReadiness:
    def check(self, to: str, **kw: object) -> rules.Readiness:
        args: dict[str, object] = {
            "gates": GATES,
            "signals": GOOD_SIGNALS,
            "contact_names": ["Maria Santos"],
            "terms": ALL_TERMS,
        }
        args.update(kw)
        return rules.readiness(to, **args)  # type: ignore[arg-type]

    def test_all_evidence_is_ready(self) -> None:
        for to in ["contacted", "replied", "in_talks", "test_calls", "signed"]:
            assert self.check(to).ready, to

    def test_no_evidence_blocks_test_calls(self) -> None:
        r = self.check("test_calls", signals=[], contact_names=[], terms=None)
        assert not r.ready
        assert {c.key for c in r.failed} == {
            "contact",
            "gate:us_hours",
            "gate:compliance",
            "terms:test_batch_size",
        }

    def test_early_stages_need_nothing(self) -> None:
        r = self.check("contacted", signals=[], contact_names=[], terms=None)
        assert r.ready
        assert r.checks == []

    def test_gate_blocked(self) -> None:
        r = self.check("test_calls", signals=[evidence("TCPA compliant")])
        assert [c.key for c in r.failed] == ["gate:us_hours"]

    def test_contradictory_evidence_blocks(self) -> None:
        r = self.check("test_calls", signals=[*GOOD_SIGNALS, manual("compliance", False)])
        assert [c.key for c in r.failed] == ["gate:compliance"]

    def test_signed_needs_all_terms(self) -> None:
        r = self.check("signed", terms={"price_per_transfer": 18, "hours": ""})
        assert {c.key for c in r.failed} == {
            "terms:daily_volume",
            "terms:hours",
            "terms:quality_threshold",
        }

    def test_blank_contact_name_does_not_count(self) -> None:
        r = self.check("in_talks", contact_names=["  "])
        assert [c.key for c in r.failed] == ["contact"]

    def test_lost_is_never_blocked(self) -> None:
        assert self.check("lost", signals=[], contact_names=[], terms=None).ready
