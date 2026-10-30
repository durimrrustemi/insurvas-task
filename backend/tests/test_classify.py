"""Lead vendor vs BPO classification from site text."""

from __future__ import annotations

import pytest

from app.discovery.classify import classify_partner_type
from app.models.partner import PartnerType


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Exclusive final expense leads for sale. Pay per call, aged leads.", PartnerType.VENDOR),
        ("Buy live transfers today. Lead provider for insurance agencies.", PartnerType.VENDOR),
        ("Call center outsourcing with 300 seats and agents in Cebu.", PartnerType.BPO),
        ("Nearshore contact center, inbound and outbound.", PartnerType.BPO),
        # Ties and silence go to BPO: a wrongly typed vendor is cheaper to fix by hand.
        ("We sell leads. Contact center.", PartnerType.BPO),
        ("", PartnerType.BPO),
        # Vendors talk about the buyer's agents a lot; that isn't BPO language.
        (
            "Final expense leads for sale, sent live to your agents. Our agents "
            "screen every call so your agents only talk to qualified seniors.",
            PartnerType.VENDOR,
        ),
        # Whole phrases only: "seats" in "seatsbelt" doesn't count.
        ("Buy leads now from seatsbelt.", PartnerType.VENDOR),
    ],
)
def test_classify(text: str, expected: PartnerType) -> None:
    assert classify_partner_type(text) is expected
