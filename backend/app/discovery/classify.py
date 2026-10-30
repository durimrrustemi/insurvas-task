"""Tell lead vendors from BPO call centers by what their site says. Pure."""

from __future__ import annotations

import re

from app.models.partner import PartnerType

# Phrases a lead vendor uses to describe what it sells.
VENDOR_PHRASES = [
    "live transfers for sale",
    "buy live transfers",
    "buy leads",
    "leads for sale",
    "lead vendor",
    "lead provider",
    "lead generation company",
    "pay per call",
    "pay-per-call",
    "aged leads",
    "data leads",
    "exclusive leads",
    "cost per lead",
    "price per transfer",
    "live transfer leads",
    "final expense leads",
    "insurance leads",
    "life insurance leads",
]

# Phrases a BPO uses to describe the operation it runs for clients. Not "agents":
# vendors talk about the buyer's agents ("transfers to your agents") all the time.
BPO_PHRASES = [
    "call center outsourcing",
    "contact center",
    "bpo",
    "outsourcing",
    "seats",
    "nearshore",
    "offshore",
    "inbound and outbound",
]


def _count(text: str, phrases: list[str]) -> int:
    return sum(len(re.findall(rf"(?<!\w){re.escape(p)}(?!\w)", text)) for p in phrases)


def classify_partner_type(text: str) -> PartnerType:
    """Vendor if vendor language clearly outweighs BPO language; BPO otherwise.

    Ties go to BPO: many call centers also mention 'leads', and a wrongly typed
    vendor is cheaper to fix by hand than a missed BPO.
    """
    t = text.lower()
    vendor, bpo = _count(t, VENDOR_PHRASES), _count(t, BPO_PHRASES)
    return PartnerType.VENDOR if vendor > bpo else PartnerType.BPO


# Broader than the type phrases: any sign the site is a call center or lead seller.
PARTNER_SITE_PHRASES = [
    *VENDOR_PHRASES,
    *BPO_PHRASES,
    "call center",
    "call centre",
    "telemarketing",
    "live transfer",
]


def is_partner_site(text: str) -> bool:
    """False for pages that never mention call centers or leads (articles, guides).

    Search results include "cost of living in the Philippines" style pages; with
    good English and a few generic words they would otherwise score high.
    """
    return _count(text.lower(), PARTNER_SITE_PHRASES) > 0
